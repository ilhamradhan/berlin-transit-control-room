#!/usr/bin/env python3
import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.error
import urllib.request
import zipfile
from contextlib import contextmanager
from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError
import pyarrow
import pyarrow.parquet
import duckdb


PRODUCTION_CAP_BYTES = 4 * 1024**3
CAMPAIGN_DAYS = 28
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def validate_namespace(namespace):
    if not isinstance(namespace, str) or not SAFE_COMPONENT.fullmatch(namespace):
        raise ValueError("namespace must be one safe path component")
    return namespace


def validate_digest(digest):
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError("static digest must be a lowercase SHA-256 hex value")
    return digest


def build_metrics(data_root, state_root, *, namespace, start, end):
    validate_namespace(namespace)
    data = Path(data_root)
    data.mkdir(parents=True, exist_ok=True)
    data = data.resolve(strict=True)
    state = Path(state_root)
    state.mkdir(parents=True, exist_ok=True)
    state = state.resolve(strict=True)
    start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
    expected = int((end_time - start_time).total_seconds() // (15 * 60))
    records = list((state / "runs" / namespace / "realtime").glob("*.json"))
    attempted = successful = stale = unchanged = entities = 0
    for path in records:
        try:
            run_time = datetime.strptime(path.stem, "%Y-%m-%dT%H-%M").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if not start_time <= run_time < end_time:
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        attempted += 1
        if record.get("status") in ("success", "already_complete"):
            successful += 1
        if record.get("failure_kind") == "stale":
            stale += 1
        if record.get("unchanged_payload"):
            unchanged += 1
        entities += record.get("rows", 0) or 0
    counted = sum(
        regular_file_bytes(data / name) if (data / name).exists() else 0
        for name in ("raw", "quarantine", "static", "parquet")
    )
    return {
        "expected_slots": expected,
        "attempted_slots": attempted,
        "successful_slots": successful,
        "slot_coverage": successful / expected if expected else None,
        "stale_slots": stale,
        "unchanged_payloads": unchanged,
        "entity_completeness": entities,
        "counted_bytes": counted,
    }


def compact_completed_day(data_root, *, date, _cap_bytes=PRODUCTION_CAP_BYTES):

    data = Path(data_root).resolve(strict=True)
    day = data / "parquet" / "observations" / f"date={date}"
    slots = sorted(path for path in day.glob("*.parquet") if path.name != "observations.parquet")
    if not slots:
        return {"rows": 0, "status": "unchanged"}
    tables = [pyarrow.parquet.read_table(path) for path in slots]
    candidate = pyarrow.concat_tables(tables)
    sink = pyarrow.BufferOutputStream()
    pyarrow.parquet.write_table(candidate, sink)
    guarded_atomic_write(
        data,
        Path(f"parquet/observations/date={date}/observations.parquet"),
        [sink.getvalue().to_pybytes()],
        _cap_bytes=_cap_bytes,
    )
    written = pyarrow.parquet.read_table(day / "observations.parquet")
    if written.num_rows != candidate.num_rows or written.schema != candidate.schema:
        raise ValueError("compacted candidate verification failed")
    for slot in slots:
        slot.unlink()
    return {"rows": candidate.num_rows, "status": "compacted"}


def maintain_retention(data_root, *, now):
    data = Path(data_root)
    data.mkdir(parents=True, exist_ok=True)
    data = data.resolve(strict=True)
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=48)
    removed = 0
    for base_name in ("raw", "quarantine"):
        base = _safe_target(data, Path(base_name))
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                timestamp = datetime.strptime(
                    f"{path.parent.name} {path.stem}", "%Y-%m-%d %H-%M"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if timestamp < cutoff:
                path.unlink()
                removed += 1
    return {"removed": removed}


def validate_slot(slot):
    slot = slot.astimezone(timezone.utc)
    if slot.second or slot.microsecond or slot.minute % 15:
        raise ValueError("slot must align to a UTC 15-minute boundary")
    return slot


def validate_feed_freshness(feed_timestamp, now):
    age = now - datetime.fromtimestamp(feed_timestamp, timezone.utc)
    if age > timedelta(minutes=15):
        raise ValueError("feed is older than 15 minutes")
    if age < -timedelta(minutes=5):
        raise ValueError("feed is more than 5 minutes in the future")
    return True


VBB_MODE_BY_ROUTE_TYPE = {"400": "subway", "109": "rail", "900": "tram", "0": "tram", "1": "subway", "2": "rail"}


def load_static_trip_lookup(extracted_root):
    routes = {}
    with (Path(extracted_root) / "routes.txt").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            mode = VBB_MODE_BY_ROUTE_TYPE.get(row.get("route_type", ""))
            if mode:
                routes[row["route_id"]] = mode
    lookup = {}
    with (Path(extracted_root) / "trips.txt").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            mode = routes.get(row.get("route_id"))
            if mode:
                lookup[row["trip_id"]] = {
                    "route_id": row.get("route_id"),
                    "mode": mode,
                    "start_date": row.get("start_date") or None,
                    "start_time": row.get("start_time") or None,
                    "stop_times": {},
                }
    stop_times_path = Path(extracted_root) / "stop_times.txt"
    if stop_times_path.is_file():
        with stop_times_path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                trip = lookup.get(row.get("trip_id"))
                if trip is None:
                    continue
                key = (row.get("stop_id"), row.get("stop_sequence"))
                trip["stop_times"][key] = {
                    "arrival_time": row.get("arrival_time") or None,
                    "departure_time": row.get("departure_time") or None,
                }
    return lookup


def _scheduled_event_utc(lookup, stop_update, event_kind, start_date):
    stop_times = lookup.get("stop_times", {})
    schedule = stop_times.get((stop_update.stop_id or None, str(stop_update.stop_sequence or "")))
    value = schedule.get(f"{event_kind}_time") if schedule else None
    if not value or not start_date:
        return None
    try:
        date = datetime.strptime(start_date, "%Y%m%d").date()
        hours, minutes, seconds = (int(part) for part in value.split(":"))
        return datetime.combine(date, datetime.min.time(), timezone.utc) + timedelta(
            hours=hours, minutes=minutes, seconds=seconds
        )
    except (TypeError, ValueError):
        return None


def normalize_realtime_feed(payload, *, slot, static_lookup, now=None):
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(payload)
    except DecodeError as error:
        raise ValueError("invalid GTFS-Realtime protobuf") from error
    now = now or slot
    validate_feed_freshness(feed.header.timestamp, now)
    feed_timestamp = _utc_iso(feed.header.timestamp)
    rows = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        update = entity.trip_update
        trip_id = update.trip.trip_id or None
        lookup = static_lookup.get(trip_id, {})
        if static_lookup and not lookup:
            continue
        if lookup.get("mode") and lookup["mode"] not in {"tram", "subway", "rail"}:
            continue
        for stop_update in update.stop_time_update:
            base = {
                "slot_utc": slot.astimezone(timezone.utc).isoformat(),
                "feed_timestamp_utc": feed_timestamp,
                "entity_id": entity.id,
                "trip_id": trip_id,
                "static_version": lookup.get("static_version"),
                "route_id": update.trip.route_id or lookup.get("route_id"),
                "start_date": update.trip.start_date or None,
                "start_time": update.trip.start_time or None,
                "stop_id": stop_update.stop_id or None,
                "stop_sequence": stop_update.stop_sequence or None,
                "mode": lookup.get("mode"),
                "schedule_relationship": gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship.Name(update.trip.schedule_relationship) if update.trip.HasField("schedule_relationship") else None,
                "arrival": stop_update.arrival,
                "departure": stop_update.departure,
            }
            for kind in ("arrival", "departure"):
                event = base[kind]
                if event.HasField("time"):
                    scheduled = _scheduled_event_utc(
                        lookup, stop_update, kind, update.trip.start_date or lookup.get("start_date")
                    )
                    rows.append({
                        **{key: value for key, value in base.items() if key not in ("arrival", "departure")},
                        "event_kind": kind,
                        "scheduled_event_utc": scheduled.isoformat() if scheduled else None,
                        "predicted_event_utc": _utc_iso(event.time),
                        "delay_seconds": event.delay if event.HasField("delay") else None,
                    })
    return rows


from datetime import datetime, timedelta, timezone
from pathlib import Path


def _utc_iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _restore_raw_snapshot(data_root, relative_target, payload):
    restore_cap = regular_file_bytes(Path(data_root).resolve(strict=True)) + len(payload) + 1
    guarded_atomic_write(data_root, relative_target, [payload], _cap_bytes=restore_cap)


def collect_realtime_slot(data_root, state_root, url, *, slot, static_lookup, now=None, scheduler="cron", data_origin="real", namespace="production", _cap_bytes=PRODUCTION_CAP_BYTES, _timeout=30):
    slot = validate_slot(slot)
    validate_trust_boundary(scheduler, data_origin, namespace)
    validate_namespace(namespace)
    data = Path(data_root).resolve(strict=True)
    state = Path(state_root).resolve(strict=True)
    static_lookup = static_lookup or {}
    active_metadata = state / "static" / namespace / "active.json"
    if active_metadata.is_file():
        digest = validate_digest(json.loads(active_metadata.read_text())["sha256"])
        static_lookup = load_static_trip_lookup(data / "static" / "extracted" / digest)
    request = urllib.request.Request(url, headers={"User-Agent": "TransitOps-Berlin/1"})
    try:
        with urllib.request.urlopen(request, timeout=min(_timeout, 30)) as response:
            payload = response.read(64 * 1024 * 1024 + 1)
            if len(payload) > 64 * 1024 * 1024:
                raise ValueError("realtime response exceeds size limit")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        result = {
            "status": "failed",
            "failure_kind": "size" if "size limit" in str(error) else "network",
            "error": str(error),
            "scheduler": scheduler,
            "data_origin": data_origin,
            "namespace": namespace,
        }
        run_root = state / "runs" / namespace / "realtime"
        run_root.mkdir(parents=True, exist_ok=True)
        guarded_atomic_write(
            run_root,
            Path(f"{slot.astimezone(timezone.utc):%Y-%m-%dT%H-%M}.json"),
            [json.dumps(result, sort_keys=True).encode()],
            _cap_bytes=_cap_bytes,
        )
        return result
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError("realtime response exceeds size limit")
    if data_origin == "real" and not static_lookup:
        feed = gtfs_realtime_pb2.FeedMessage()
        try:
            feed.ParseFromString(payload)
        except DecodeError:
            pass
        else:
            result = {
                "status": "failed",
                "failure_kind": "static_mapping",
                "error": "active static lookup is required for real collection",
                "scheduler": scheduler,
                "data_origin": data_origin,
                "namespace": namespace,
            }
            run_root = state / "runs" / namespace / "realtime"
            run_root.mkdir(parents=True, exist_ok=True)
            guarded_atomic_write(
                run_root,
                Path(f"{slot.astimezone(timezone.utc):%Y-%m-%dT%H-%M}.json"),
                [json.dumps(result, sort_keys=True).encode()],
                _cap_bytes=_cap_bytes,
            )
            return result
    raw_relative = Path(
        f"raw/realtime/{slot.astimezone(timezone.utc).date().isoformat()}/"
        f"{slot.astimezone(timezone.utc):%H-%M}.pb"
    )
    payload_digest = hashlib.sha256(payload).hexdigest()
    digest_file = state / "realtime" / "last_payload.sha256"
    previous_digest = digest_file.read_text().strip() if digest_file.is_file() else None
    raw_path = _safe_target(data, raw_relative)
    previous_raw = raw_path.read_bytes() if raw_path.is_file() else None
    raw_written = False
    try:
        guarded_atomic_write(data, raw_relative, [payload], _cap_bytes=_cap_bytes)
        raw_written = True
        result = write_realtime_slot(
            data,
            payload,
            slot=slot,
            static_lookup=static_lookup,
            now=now,
            _cap_bytes=_cap_bytes,
        )
    except StorageCapExceeded as error:
        if raw_written:
            if previous_raw is None:
                raw_path.unlink(missing_ok=True)
            else:
                _restore_raw_snapshot(data, raw_relative, previous_raw)
        result = {
            "status": "failed",
            "failure_kind": "storage_cap",
            "error": str(error),
            "scheduler": scheduler,
            "data_origin": data_origin,
            "namespace": namespace,
        }
        run_root = state / "runs" / namespace / "realtime"
        run_root.mkdir(parents=True, exist_ok=True)
        guarded_atomic_write(
            run_root,
            Path(f"{slot.astimezone(timezone.utc):%Y-%m-%dT%H-%M}.json"),
            [json.dumps(result, sort_keys=True).encode()],
        )
        return result
    except ValueError as error:
        raw_path = data / raw_relative
        if previous_raw is None:
            raw_path.unlink(missing_ok=True)
        else:
            _restore_raw_snapshot(data, raw_relative, previous_raw)
        quarantine_relative = Path(
            f"quarantine/realtime/{slot.astimezone(timezone.utc).date().isoformat()}/"
            f"{slot.astimezone(timezone.utc):%H-%M}.pb"
        )
        quarantine_error = None
        try:
            guarded_atomic_write(data, quarantine_relative, [payload], _cap_bytes=_cap_bytes)
        except StorageCapExceeded as quarantine_failure:
            quarantine_error = str(quarantine_failure)
        failure_kind = "stale" if "older" in str(error) or "future" in str(error) else "parse"
        result = {
            "status": "failed",
            "failure_kind": failure_kind,
            "error": str(error),
            "scheduler": scheduler,
            "data_origin": data_origin,
            "namespace": namespace,
            "raw_path": str(raw_relative),
            "quarantine_path": str(quarantine_relative),
        }
        if quarantine_error:
            result["quarantine_error"] = quarantine_error
        run_root = state / "runs" / namespace / "realtime"
        run_root.mkdir(parents=True, exist_ok=True)
        guarded_atomic_write(
            run_root,
            Path(f"{slot.astimezone(timezone.utc):%Y-%m-%dT%H-%M}.json"),
            [json.dumps(result, sort_keys=True).encode()],
        )
        return result
    unchanged_payload = previous_digest == payload_digest
    result["unchanged_payload"] = unchanged_payload
    guarded_atomic_write(
        state,
        Path("realtime/last_payload.sha256"),
        [payload_digest.encode()],
    )
    metrics_path = state / "metrics" / "production.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.is_file() else {"unchanged_payloads": 0}
    metrics["unchanged_payloads"] = metrics.get("unchanged_payloads", 0) + int(unchanged_payload)
    guarded_atomic_write(
        state,
        Path("metrics/production.json"),
        [json.dumps(metrics, sort_keys=True).encode()],
    )
    result["unchanged_payload"] = unchanged_payload
    result["raw_path"] = str(raw_relative)
    result["scheduler"] = scheduler
    result["data_origin"] = data_origin
    result["namespace"] = namespace
    result["payload_sha256"] = payload_digest
    result["parquet_path"] = result["path"]
    run_root = state / "runs" / namespace / "realtime"
    run_root.mkdir(parents=True, exist_ok=True)
    guarded_atomic_write(
        run_root,
        Path(f"{slot.astimezone(timezone.utc):%Y-%m-%dT%H-%M}.json"),
        [json.dumps(result, sort_keys=True).encode()],
        _cap_bytes=_cap_bytes,
    )
    return result


def write_realtime_slot(data_root, payload, *, slot, static_lookup, now=None, _cap_bytes=PRODUCTION_CAP_BYTES):
    slot = validate_slot(slot)
    relative = Path(
        f"parquet/observations/date={slot.astimezone(timezone.utc).date().isoformat()}/"
        f"{slot.astimezone(timezone.utc):%H-%M}.parquet"
    )
    target = _safe_target(data_root, relative)
    if target.is_file():
        return {"status": "already_complete", "rows": None, "path": str(relative)}
    rows = normalize_realtime_feed(payload, slot=slot, static_lookup=static_lookup, now=now)
    if not rows:
        raise ValueError("realtime feed contains no usable stop-time events")
    schema = pyarrow.schema([
        pyarrow.field("slot_utc", pyarrow.string()),
        pyarrow.field("feed_timestamp_utc", pyarrow.string()),
        pyarrow.field("static_version", pyarrow.string()),
        pyarrow.field("entity_id", pyarrow.string()),
        pyarrow.field("trip_id", pyarrow.string()),
        pyarrow.field("route_id", pyarrow.string()),
        pyarrow.field("start_date", pyarrow.string()),
        pyarrow.field("start_time", pyarrow.string()),
        pyarrow.field("stop_id", pyarrow.string()),
        pyarrow.field("stop_sequence", pyarrow.int32()),
        pyarrow.field("event_kind", pyarrow.string()),
        pyarrow.field("scheduled_event_utc", pyarrow.string()),
        pyarrow.field("predicted_event_utc", pyarrow.string()),
        pyarrow.field("delay_seconds", pyarrow.int32()),
        pyarrow.field("schedule_relationship", pyarrow.string()),
        pyarrow.field("mode", pyarrow.string()),
    ])
    table = pyarrow.Table.from_pylist(rows, schema=schema)
    sink = pyarrow.BufferOutputStream()
    pyarrow.parquet.write_table(table, sink)
    guarded_atomic_write(data_root, relative, [sink.getvalue().to_pybytes()], _cap_bytes=_cap_bytes)
    return {"status": "success", "rows": len(rows), "path": str(relative)}


class StorageCapExceeded(RuntimeError):
    pass


def campaign_status(started_at, now, *, paused=False):
    if now >= started_at + timedelta(days=CAMPAIGN_DAYS):
        return "stopped"
    return "paused" if paused else "active"


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("campaign start must include a timezone")
    return parsed


def _safe_target(root, relative_target):
    supplied_root = Path(root)
    canonical_root = supplied_root.resolve(strict=True)
    if supplied_root != canonical_root or supplied_root.is_symlink():
        raise ValueError("root must be canonical")
    relative = Path(relative_target)
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ValueError("target must be a relative descendant")
    target = canonical_root / relative
    if any(path.is_symlink() for path in (target, *target.parents) if path != canonical_root):
        raise ValueError("target may not traverse symlinks")
    return target


def regular_file_bytes(root):
    total = 0
    with os.scandir(root) as entries:
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
            elif stat.S_ISDIR(metadata.st_mode):
                total += regular_file_bytes(entry.path)
    return total


@contextmanager
def _storage_lock(root):
    lock_path = root.parent / f".{root.name}.storage.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def guarded_atomic_write(data_root, relative_target, chunks, *, _cap_bytes=PRODUCTION_CAP_BYTES):
    root = Path(data_root).resolve(strict=True)
    with _storage_lock(root):
        return _guarded_atomic_write_unlocked(
            data_root, relative_target, chunks, _cap_bytes=_cap_bytes
        )


def _guarded_atomic_write_unlocked(data_root, relative_target, chunks, *, _cap_bytes=PRODUCTION_CAP_BYTES):
    root = Path(data_root).resolve(strict=True)
    target = _safe_target(data_root, relative_target)
    target.parent.mkdir(parents=True, exist_ok=True)
    replaced_bytes = target.lstat().st_size if target.exists() and target.is_file() else 0
    projected = regular_file_bytes(root) - replaced_bytes
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            for chunk in chunks:
                projected += len(chunk)
                if projected > _cap_bytes:
                    raise StorageCapExceeded("projected storage exceeds 4 GiB cap")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def acquire_lock(state_root, relative_target):
    target = _safe_target(state_root, relative_target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def validate_runtime_paths(runtime_root, data_path, state_path):
    supplied_root = Path(runtime_root)
    root = supplied_root.resolve(strict=True)
    if not supplied_root.is_absolute() or supplied_root != root or supplied_root.is_symlink():
        raise ValueError("runtime root must be an absolute canonical directory")
    requested = []
    for value in (data_path, state_path):
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
            raise ValueError("runtime paths must be relative descendants")
        candidate = root / relative
        for parent in (candidate, *candidate.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError("runtime paths may not traverse symlinks")
        if not candidate.resolve(strict=False).is_relative_to(root):
            raise ValueError("runtime path escapes runtime root")
        requested.append(candidate)
    data, state = requested
    if data == state or data.is_relative_to(state) or state.is_relative_to(data):
        raise ValueError("data and state paths must be distinct")
    return root, data, state


def validate_trust_boundary(scheduler, data_origin, namespace):
    validate_namespace(namespace)
    if data_origin == "real" and namespace != "production":
        raise ValueError("real data origin requires the production namespace")
    if scheduler == "airflow" and data_origin == "real":
        raise ValueError("airflow may not collect real data")
    return scheduler, data_origin, namespace


def write_status_artifact(status_root, *, task, status, scheduler, data_origin, namespace):
    validate_trust_boundary(scheduler, data_origin, namespace)
    validate_namespace(task)
    root = _validated_path(status_root, "status root")
    root.mkdir(parents=True, exist_ok=True)
    artifact = root / f"{task}.json"
    payload = {
        "data_origin": data_origin,
        "namespace": namespace,
        "scheduler": scheduler,
        "status": status,
        "task": task,
    }
    temporary = artifact.with_name(f".{artifact.name}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, artifact)
    return artifact


REQUIRED_STATIC_FILES = {
    "agency.txt": {"agency_id", "agency_name", "agency_url", "agency_timezone"},
    "stops.txt": {"stop_id", "stop_name", "stop_lat", "stop_lon"},
    "routes.txt": {"route_id", "route_type"},
    "trips.txt": {"route_id", "service_id", "trip_id"},
    "stop_times.txt": {"trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"},
    "calendar.txt": {"service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"},
}
SCOPED_ROUTE_TYPES = {"0", "1", "2", "109", "400", "900"}
STATIC_RESPONSE_LIMIT = 512 * 1024**2


class ReleaseBuildError(RuntimeError):
    pass


def _validated_path(value, label):
    supplied = Path(value)
    if ".." in supplied.parts:
        raise ValueError(f"{label} may not contain traversal")
    for parent in (supplied, *supplied.parents):
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"{label} may not traverse symlinks")
    return supplied.resolve()


def publish_manifest(manifest_path, payload):
    manifest = _validated_path(manifest_path, "manifest")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest.parent / f".{manifest.name}.{uuid.uuid4().hex}.tmp"
    try:
        guarded_atomic_write(
            manifest.parent,
            temporary.name,
            [json.dumps(payload, sort_keys=True).encode()],
        )
        os.replace(temporary, manifest)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def active_release_reader(active_readers_root, release_path):
    readers = _validated_path(active_readers_root, "active readers root")
    readers.mkdir(parents=True, exist_ok=True)
    release = _validated_path(release_path, "active release")
    releases = release.parent.parent
    with _storage_lock(releases):
        if (
            not release.is_file()
            or release.name != "transitops.duckdb"
            or not release.parent.name.startswith("release-")
        ):
            raise ValueError("active reader must reference a verified release")
        marker = readers / f"reader-{uuid.uuid4().hex}"
        marker.write_text(str(release), encoding="utf-8")
        try:
            yield release
        finally:
            marker.unlink(missing_ok=True)


def _retain_releases_unlocked(releases_root, manifest_path, *, active_readers_root=None):
    releases = _validated_path(releases_root, "release root")
    manifest = _validated_path(manifest_path, "manifest")
    if not releases.is_dir() or not manifest.is_file():
        return {"removed": 0}
    current = Path(json.loads(manifest.read_text())["path"]).resolve()
    if not current.is_relative_to(releases) or current.name != "transitops.duckdb":
        raise ValueError("manifest release path must be inside the release root")
    active = {current}
    if active_readers_root:
        readers = _validated_path(active_readers_root, "active readers root")
        if readers.is_dir():
            for marker in readers.iterdir():
                if marker.is_file():
                    try:
                        candidate = Path(marker.read_text().strip()).resolve()
                        if candidate.is_relative_to(releases):
                            active.add(candidate)
                    except (OSError, ValueError):
                        continue
    verified = [
        path for path in releases.iterdir()
        if path.is_dir() and path.name.startswith("release-")
        and (path / "transitops.duckdb").is_file()
    ]
    verified.sort(key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
    current_release = current.parent
    previous = [path for path in verified if path != current_release][:1]
    keep = active | {current} | {path / "transitops.duckdb" for path in previous}
    victims = [path for path in verified if path / "transitops.duckdb" not in keep]
    if not victims:
        return {"removed": 0}
    staging = releases / f".retention-{uuid.uuid4().hex}"
    moved = []
    try:
        staging.mkdir()
        for path in victims:
            target = staging / path.name
            os.replace(path, target)
            moved.append((path, target))
        shutil.rmtree(staging)
    except Exception:
        for original, staged in reversed(moved):
            if staged.exists():
                os.replace(staged, original)
        staging.rmdir()
        raise
    return {"removed": len(victims)}


def retain_releases(releases_root, manifest_path, *, active_readers_root=None):
    releases = _validated_path(releases_root, "release root")
    with _storage_lock(releases):
        return _retain_releases_unlocked(
            releases, manifest_path, active_readers_root=active_readers_root
        )


def _run_bounded_subprocess(arguments, *, cwd, env, timeout, output_limit):
    if output_limit <= 0:
        raise ValueError("output limit must be positive")
    process = subprocess.Popen(
        arguments,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise subprocess.TimeoutExpired(arguments, timeout)
            for key, _ in selector.select(remaining):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                del output[:-output_limit]
        return process.wait(), bytes(output)
    finally:
        selector.close()
        process.stdout.close()


def _restore_manifest(manifest, previous):
    if previous is None:
        manifest.unlink(missing_ok=True)
        return
    temporary = manifest.parent / f".{manifest.name}.{uuid.uuid4().hex}.rollback"
    try:
        temporary.write_bytes(previous)
        os.replace(temporary, manifest)
    finally:
        temporary.unlink(missing_ok=True)


def build_and_publish_release(releases_root, manifest_path, *, project_dir, dbt_bin, _timeout=300, _output_limit=64 * 1024):
    releases = _validated_path(releases_root, "release root")
    manifest = _validated_path(manifest_path, "manifest")
    releases.mkdir(parents=True, exist_ok=True)
    candidate = releases / f".candidate-{uuid.uuid4().hex}"
    release = None
    database = candidate / "transitops.duckdb"
    try:
        candidate.mkdir()
        env = os.environ | {"DBT_DUCKDB_PATH": str(database)}
        commands = (
            ("parse",),
            ("seed", "--full-refresh"),
            ("run",),
            ("test",),
        )
        for command in commands:
            try:
                completed_code, bounded_output = _run_bounded_subprocess(
                    [
                        str(dbt_bin), *command, "--project-dir", str(project_dir),
                        "--profiles-dir", str(project_dir), "--target-path", str(candidate / "target"),
                    ], cwd=project_dir, env=env, timeout=_timeout, output_limit=_output_limit,
                )
                command_output = bounded_output.decode("utf-8", errors="replace")
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ReleaseBuildError(f"dbt {' '.join(command)} did not complete: {error}") from error
            if completed_code:
                raise ReleaseBuildError(
                    f"dbt {' '.join(command)} failed ({completed_code}): {command_output}"
                )
        connection = duckdb.connect(str(database))
        try:
            connection.execute("CHECKPOINT")
        finally:
            connection.close()
        connection = duckdb.connect(str(database), read_only=True)
        try:
            tables = {row[0] for row in connection.execute("show tables from main_marts").fetchall()}
            if "mart_reliability" not in tables:
                raise ReleaseBuildError("candidate is missing main_marts.mart_reliability")
            columns = {row[0] for row in connection.execute("describe main_marts.mart_reliability").fetchall()}
            required = {"observation_count", "on_time_rate", "severe_delay_rate"}
            if not required <= columns:
                raise ReleaseBuildError("candidate mart schema is incomplete")
        finally:
            connection.close()
        release = releases / f"release-{uuid.uuid4().hex}"
        os.replace(candidate, release)
        candidate = None
        database = release / "transitops.duckdb"
        try:
            with _storage_lock(releases):
                previous_manifest = manifest.read_bytes() if manifest.is_file() else None
                try:
                    publish_manifest(manifest, {"path": str(database), "verified_read_only": True})
                    _retain_releases_unlocked(
                        releases,
                        manifest,
                        active_readers_root=releases.parent / "active-readers",
                    )
                except Exception:
                    _restore_manifest(manifest, previous_manifest)
                    shutil.rmtree(release, ignore_errors=True)
                    release = None
                    raise
        except Exception as error:
            raise ReleaseBuildError(f"release publication failed: {error}") from error
        result = {"path": str(database), "verified_read_only": True}
        release = None
        return result
    except (OSError, duckdb.Error) as error:
        raise ReleaseBuildError(str(error)) from error
    finally:
        if candidate is not None and candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)
        if release is not None and release.exists():
            shutil.rmtree(release, ignore_errors=True)


def _validated_static_archive(payload):
    archive = zipfile.ZipFile(io.BytesIO(payload))
    members = {member.filename: member for member in archive.infolist()}
    for member in members.values():
        path = Path(member.filename)
        if path.is_absolute() or ".." in path.parts or member.is_dir():
            raise ValueError("static archive contains an unsafe member")
    missing = REQUIRED_STATIC_FILES.keys() - members.keys()
    if missing:
        raise ValueError(f"static archive missing required files: {sorted(missing)}")
    for name, required_headers in REQUIRED_STATIC_FILES.items():
        with archive.open(name) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
            if not required_headers.issubset(reader.fieldnames or []):
                raise ValueError(f"{name} is missing required columns")
    return archive


def _activate_static_transaction(data, state, namespace, digest, payload, metadata, extracted_files=None):
    data = _validated_path(data, "data root")
    state = _validated_path(state, "state root")
    validate_namespace(namespace)
    active = data / "static" / "active"
    extracted = data / "static" / "extracted" / digest
    namespace_state = state / "static" / namespace
    stage = data / "static" / f".activation-{uuid.uuid4().hex}"
    moved = []
    try:
        stage.mkdir(parents=True)
        (stage / "archive.zip").write_bytes(payload)
        for name, content in (extracted_files or {}).items():
            target = stage / "extracted" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        active.mkdir(parents=True, exist_ok=True)
        os.replace(stage / "archive.zip", active / f"{digest}.zip")
        moved.append(active / f"{digest}.zip")
        if extracted_files is not None:
            extracted.mkdir(parents=True, exist_ok=True)
            for name in extracted_files:
                target = extracted / name
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage / "extracted" / name, target)
                moved.append(target)
        namespace_state.mkdir(parents=True, exist_ok=True)
        guarded_atomic_write(namespace_state, Path("active.json"), [json.dumps(metadata, sort_keys=True).encode()])
    except Exception:
        for path in reversed(moved):
            path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def refresh_static_feed(
    data_root,
    state_root,
    url,
    *,
    namespace,
    scheduler,
    data_origin,
    now,
    _cap_bytes=PRODUCTION_CAP_BYTES,
    _timeout=30,
):
    validate_trust_boundary(scheduler, data_origin, namespace)
    data = _validated_path(data_root, "data root")
    state = _validated_path(state_root, "state root")
    request = urllib.request.Request(url, headers={"User-Agent": "TransitOps-Berlin/1"})
    previous_handler = signal.signal(
        signal.SIGALRM,
        lambda signum, frame: (_ for _ in ()).throw(TimeoutError("response deadline exceeded")),
    )
    signal.setitimer(signal.ITIMER_REAL, _timeout)
    try:
        with urllib.request.urlopen(request, timeout=min(_timeout, 30)) as response:
            payload = response.read(STATIC_RESPONSE_LIMIT + 1)
            if len(payload) > STATIC_RESPONSE_LIMIT:
                raise ValueError("static response exceeds size limit")
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        run_root = state / "runs" / namespace / "static"
        run_root.mkdir(parents=True, exist_ok=True)
        result = {"status": "failed", "failure_kind": "size" if "size limit" in str(error) else "network", "error": str(error)}
        guarded_atomic_write(
            run_root,
            Path(f"{now.astimezone(timezone.utc).date().isoformat()}.json"),
            [json.dumps(result, sort_keys=True).encode()],
            _cap_bytes=_cap_bytes,
        )
        return result
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    digest = hashlib.sha256(payload).hexdigest()
    run_root = state / "runs" / namespace / "static"
    run_root.mkdir(parents=True, exist_ok=True)
    try:
        archive = _validated_static_archive(payload)
    except (ValueError, zipfile.BadZipFile, UnicodeError, csv.Error) as error:
        date = now.astimezone(timezone.utc).date().isoformat()
        guarded_atomic_write(
            data,
            Path(f"quarantine/static/{date}/{digest}.zip"),
            [payload],
            _cap_bytes=_cap_bytes,
        )
        result = {"status": "failed", "sha256": digest, "error": str(error)}
        guarded_atomic_write(
            run_root,
            Path(f"{now.astimezone(timezone.utc).date().isoformat()}.json"),
            [json.dumps(result, sort_keys=True).encode()],
        )
        return result
    namespace_state = state / "static" / namespace
    active_metadata = namespace_state / "active.json"
    previous_digest = (
        validate_digest(json.loads(active_metadata.read_text())["sha256"])
        if active_metadata.is_file()
        else None
    )
    unchanged = previous_digest == digest
    status = "unchanged" if unchanged else "updated"
    if not unchanged:
        projected = regular_file_bytes(data) + len(payload)
        projected += sum(archive.getinfo(name).file_size for name in REQUIRED_STATIC_FILES)
        if projected > _cap_bytes:
            result = {
                "status": "failed",
                "failure_kind": "storage_cap",
                "error": "projected static activation exceeds 4 GiB cap",
            }
            guarded_atomic_write(
                run_root,
                Path(f"{now.astimezone(timezone.utc).date().isoformat()}.json"),
                [json.dumps(result, sort_keys=True).encode()],
                _cap_bytes=_cap_bytes,
            )
            return result
        active_root = data / "static" / "active"
        extracted_files = {}
        for name in REQUIRED_STATIC_FILES:
            with archive.open(name) as stream:
                extracted_files[name] = b"".join(iter(lambda: stream.read(1024 * 1024), b""))
        with archive.open("routes.txt") as stream:
            routes = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
            scoped_types = set()
            route_ids = []
            for row in routes:
                if row["route_type"] in SCOPED_ROUTE_TYPES:
                    scoped_types.add(row["route_type"])
                    route_ids.append(row["route_id"])
        metadata = {
            "sha256": digest,
            "activated_at": now.astimezone(timezone.utc).isoformat(),
            "etag": etag,
            "last_modified": last_modified,
            "route_types": sorted(scoped_types),
            "route_ids": sorted(route_ids),
        }
        _activate_static_transaction(
            data, state, namespace, digest, payload, metadata, extracted_files
        )
        if previous_digest:
            previous_zip = active_root / f"{previous_digest}.zip"
            referenced = any(
                json.loads(record.read_text()).get("sha256") == previous_digest
                for record in run_root.glob("*.json")
            )
            if previous_zip.is_file():
                if referenced:
                    archive_root = _safe_target(data, Path("static/archive"))
                    archive_root.mkdir(parents=True, exist_ok=True)
                    os.replace(previous_zip, archive_root / previous_zip.name)
                else:
                    previous_zip.unlink()
                    shutil.rmtree(data / "static" / "extracted" / previous_digest)
    run_record = {
        "status": status,
        "sha256": digest,
        "scheduler": scheduler,
        "data_origin": data_origin,
        "namespace": namespace,
    }
    guarded_atomic_write(
        run_root,
        Path(f"{now.astimezone(timezone.utc).date().isoformat()}.json"),
        [json.dumps(run_record, sort_keys=True).encode()],
    )
    return {"status": status, "sha256": digest}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=("static", "realtime", "maintain", "metrics", "release", "status"))
    parser.add_argument("--runtime-root", default=Path("."), type=Path)
    parser.add_argument("--root", default=Path("data"), type=Path)
    parser.add_argument("--state-root", default=Path("state"), type=Path)
    parser.add_argument("--scheduler", default="cron")
    parser.add_argument("--data-origin", default="real")
    parser.add_argument("--namespace", default="production")
    parser.add_argument("--campaign-start", type=parse_timestamp)
    parser.add_argument("--paused", action="store_true")
    parser.add_argument("--static-url")
    parser.add_argument("--realtime-url")
    parser.add_argument("--slot", type=parse_timestamp)
    parser.add_argument("--slot-now", action="store_true")
    parser.add_argument("--now", type=parse_timestamp)
    parser.add_argument("--metrics-start", type=parse_timestamp)
    parser.add_argument("--metrics-end", type=parse_timestamp)
    parser.add_argument("--release-root", default=Path("warehouse/releases"), type=Path)
    parser.add_argument("--manifest", default=Path("warehouse/current.json"), type=Path)
    parser.add_argument("--dbt-bin", default=Path(".venv/bin/dbt"), type=Path)
    parser.add_argument("--project-dir", default=Path("."), type=Path)
    parser.add_argument("--status-root", default=Path("state/status"), type=Path)
    parser.add_argument("--task")
    parser.add_argument("--status")
    args = parser.parse_args(argv)
    if args.command == "status":
        if not args.task or not args.status:
            parser.error("status requires --task and --status")
        artifact = write_status_artifact(
            args.status_root,
            task=args.task,
            status=args.status,
            scheduler=args.scheduler,
            data_origin=args.data_origin,
            namespace=args.namespace,
        )
        print(json.dumps({"status": "ok", "artifact": str(artifact)}, sort_keys=True))
        return 0
    if args.command == "release":
        result = build_and_publish_release(
            args.release_root,
            args.manifest,
            project_dir=args.project_dir,
            dbt_bin=args.dbt_bin,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command in ("static", "realtime") and args.campaign_start is None:
        parser.error("collection commands require --campaign-start")
    if args.campaign_start is None:
        args.campaign_start = datetime.now(timezone.utc)
    campaign_now = args.now or datetime.now(timezone.utc)
    if args.command in ("static", "realtime"):
        campaign = campaign_status(args.campaign_start, campaign_now, paused=args.paused)
        if campaign != "active":
            print(json.dumps({"status": campaign, "campaign": campaign}, sort_keys=True))
            return 0
    scheduler, data_origin, namespace = validate_trust_boundary(
        args.scheduler, args.data_origin, args.namespace
    )
    root, data, state = validate_runtime_paths(
        args.runtime_root, args.root, args.state_root
    )
    data.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    data = data.resolve(strict=True)
    state = state.resolve(strict=True)
    validate_trust_boundary(scheduler, data_origin, namespace)

    if args.command == "static":
        if not args.static_url:
            parser.error("static requires --static-url")
        result = refresh_static_feed(
            data,
            state,
            args.static_url,
            namespace=namespace,
            scheduler=scheduler,
            data_origin=data_origin,
            now=campaign_now,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("updated", "unchanged") else 1
    if args.command == "maintain":
        result = maintain_retention(data, now=campaign_now)
        result["status"] = "ok"
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "metrics":
        if not args.metrics_start or not args.metrics_end:
            parser.error("metrics requires --metrics-start and --metrics-end")
        result = build_metrics(
            data,
            state,
            namespace=namespace,
            start=args.metrics_start.isoformat(),
            end=args.metrics_end.isoformat(),
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "realtime":
        if not args.realtime_url:
            parser.error("realtime requires --realtime-url")
        if args.slot_now:
            current = datetime.now(timezone.utc)
            args.slot = current.replace(minute=current.minute - current.minute % 15, second=0, microsecond=0)
        if not args.slot:
            parser.error("realtime requires --slot or --slot-now")
        result = collect_realtime_slot(
            data,
            state,
            args.realtime_url,
            slot=args.slot,
            now=campaign_now,
            static_lookup={},
            scheduler=scheduler,
            data_origin=data_origin,
            namespace=namespace,
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("success", "already_complete") else 1
    print(
        json.dumps(
            {
                "runtime_root": str(root),
                "data_root": str(data),
                "state_root": str(state),
                "scheduler": scheduler,
                "data_origin": data_origin,
                "namespace": namespace,
                "campaign": campaign_status(
                    args.campaign_start, datetime.now(timezone.utc), paused=args.paused
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
