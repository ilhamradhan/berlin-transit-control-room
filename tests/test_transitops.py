import hashlib
import importlib.util
import io
import json
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "transitops.py"
SPEC = importlib.util.spec_from_file_location("transitops", SCRIPT)
transitops = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transitops)


class RuntimePathsTest(unittest.TestCase):
    def test_rejects_unsafe_namespace_and_digest(self):
        with self.assertRaises(ValueError):
            transitops.validate_namespace("../outside")
        with self.assertRaises(ValueError):
            transitops.validate_digest("../outside")

    def test_accepts_distinct_descendants_of_canonical_runtime_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = transitops.validate_runtime_paths(root, Path("data"), Path("state"))

            self.assertEqual(paths, (root.resolve(), root / "data", root / "state"))

    def test_rejects_non_descendants_equal_paths_and_symlink_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "link").symlink_to(outside, target_is_directory=True)

            invalid = [
                (Path("/tmp/data"), Path("state")),
                (Path("../data"), Path("state")),
                (Path("data"), Path("data")),
                (Path("link/data"), Path("state")),
            ]
            for data, state in invalid:
                with self.subTest(data=data, state=state):
                    with self.assertRaises(ValueError):
                        transitops.validate_runtime_paths(root, data, state)

    def test_rejects_symlink_runtime_root(self):
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual"
            actual.mkdir()
            alias = Path(directory) / "alias"
            alias.symlink_to(actual, target_is_directory=True)

            with self.assertRaises(ValueError):
                transitops.validate_runtime_paths(alias, Path("data"), Path("state"))


class StorageTest(unittest.TestCase):
    def test_realtime_writer_rejects_existing_symlink_target(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            outside = Path(directory) / "outside"
            data.mkdir()
            outside.write_text("keep")
            target = data / "parquet" / "observations" / "date=2026-09-02" / "12-00.parquet"
            target.parent.mkdir(parents=True)
            target.symlink_to(outside)
            with self.assertRaises(ValueError):
                transitops.write_realtime_slot(
                    data, payload, slot=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
                    static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
                )

    def test_static_archive_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            outside = Path(directory) / "outside"
            data.mkdir()
            outside.mkdir()
            (data / "static").mkdir()
            (data / "static" / "archive").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                transitops._safe_target(data, Path("static/archive"))

    def test_counts_only_regular_files_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "one").write_bytes(b"123")
            (root / "nested" / "two").write_bytes(b"4567")
            (root / "link").symlink_to(root / "nested" / "two")

            self.assertEqual(transitops.regular_file_bytes(root), 7)

    def test_atomic_write_refuses_projected_cap_without_partial_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "payload"
            target.write_bytes(b"old")

            with self.assertRaises(transitops.StorageCapExceeded):
                transitops.guarded_atomic_write(
                    root, Path("payload"), [b"12", b"3456"], _cap_bytes=5
                )

            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual([path.name for path in root.iterdir()], ["payload"])

    def test_atomic_write_replaces_target_under_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "nested" / "payload"

            transitops.guarded_atomic_write(
                root, Path("nested/payload"), [b"12", b"34"], _cap_bytes=4
            )

            self.assertEqual(target.read_bytes(), b"1234")

    def test_atomic_write_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "link").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(ValueError):
                transitops.guarded_atomic_write(
                    root, Path("link/payload"), [b"escape"], _cap_bytes=10
                )

            self.assertEqual(list(outside.iterdir()), [])

    def test_storage_cap_counts_files_across_data_subdirectories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "raw").mkdir()
            (root / "raw" / "existing").write_bytes(b"1234")

            with self.assertRaises(transitops.StorageCapExceeded):
                transitops.guarded_atomic_write(
                    root, Path("static/active/feed.zip"), [b"12"], _cap_bytes=5
                )

            self.assertFalse((root / "static" / "active" / "feed.zip").exists())


class LockTest(unittest.TestCase):
    def test_lock_is_nonfollowing_private_and_nonblocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with transitops.acquire_lock(root, Path("collector.lock")):
                self.assertEqual(stat.S_IMODE((root / "collector.lock").stat().st_mode), 0o600)
                with self.assertRaises(BlockingIOError):
                    with transitops.acquire_lock(root, Path("collector.lock")):
                        pass

    def test_lock_rejects_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("keep")
            (root / "collector.lock").symlink_to(target)

            with self.assertRaises(ValueError):
                with transitops.acquire_lock(root, Path("collector.lock")):
                    pass

            self.assertEqual(target.read_text(), "keep")


class CampaignTest(unittest.TestCase):
    def test_collection_requires_campaign_start(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "realtime",
                    "--runtime-root", directory,
                    "--scheduler", "cron", "--data-origin", "real",
                    "--namespace", "production", "--realtime-url", "https://example.invalid/feed",
                    "--slot-now",
                ], text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("require --campaign-start", result.stderr)

    def test_cli_stops_collection_after_campaign_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "realtime",
                    "--runtime-root", directory,
                    "--root", "data", "--state-root", "state",
                    "--scheduler", "cron", "--data-origin", "real",
                    "--namespace", "production",
                    "--campaign-start", "2026-09-01T00:00:00Z",
                    "--now", "2026-10-01T00:00:00Z",
                    "--realtime-url", "https://example.invalid/feed", "--slot-now",
                ], text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["status"], "stopped")

    def test_campaign_starts_active_stops_at_28_days_and_can_pause(self):
        started = datetime(2026, 9, 1, tzinfo=timezone.utc)

        self.assertEqual(transitops.campaign_status(started, started), "active")
        self.assertEqual(
            transitops.campaign_status(started, started + timedelta(days=1), paused=True),
            "paused",
        )
        self.assertEqual(
            transitops.campaign_status(started, started + timedelta(days=28)),
            "stopped",
        )

    def test_cli_requires_runtime_boundary_without_cap_override(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], text=True, capture_output=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--runtime-root", result.stdout)
        self.assertIn("--campaign-start", result.stdout)
        self.assertNotIn("cap", result.stdout.lower())

    def test_cli_runs_metrics_command_with_json_result(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "metrics",
                    "--runtime-root", directory,
                    "--root", "data",
                    "--state-root", "state",
                    "--scheduler", "cron",
                    "--data-origin", "real",
                    "--namespace", "production",
                    "--campaign-start", "2026-09-01T00:00:00Z",
                    "--now", "2026-09-02T12:00:00Z",
                    "--metrics-start", "2026-09-02T00:00:00Z",
                    "--metrics-end", "2026-09-02T00:15:00Z",
                ], text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("expected_slots", json.loads(result.stdout))

    def test_cli_runs_maintain_command_with_json_result(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "maintain",
                    "--runtime-root", directory,
                    "--root", "data",
                    "--state-root", "state",
                    "--scheduler", "cron",
                    "--data-origin", "real",
                    "--namespace", "production",
                    "--campaign-start", "2026-09-01T00:00:00Z",
                    "--now", "2026-09-02T12:00:00Z",
                ], text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_cli_runs_realtime_command_with_json_result(self):
        fixture = ROOT / "tests" / "fixtures" / "realtime.pb"
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "realtime",
                    "--runtime-root", directory,
                    "--root", "data",
                    "--state-root", "state",
                    "--scheduler", "test",
                    "--data-origin", "synthetic",
                    "--namespace", "test",
                    "--campaign-start", "2026-09-01T00:00:00Z",
                    "--realtime-url", fixture.as_uri(),
                    "--slot", "2026-09-02T12:00:00Z",
                    "--now", "2026-09-02T12:00:00Z",
                ], text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "success")
            record = state / "runs" / "test" / "realtime" / "2026-09-02T12-00.json"
            saved = json.loads(record.read_text())
            self.assertEqual(saved["scheduler"], "test")
            self.assertEqual(saved["data_origin"], "synthetic")
            self.assertEqual(saved["namespace"], "test")
            self.assertEqual(saved["rows"], 2)

    def test_cli_uses_root_and_trust_boundary_flags(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], text=True, capture_output=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--root", result.stdout)
        self.assertIn("--scheduler", result.stdout)
        self.assertIn("--data-origin", result.stdout)
        self.assertIn("--namespace", result.stdout)
        self.assertNotIn("--data-root", result.stdout)


class RealtimeFeedTest(unittest.TestCase):
    def test_loads_static_trip_lookup_with_vbb_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extracted = root / "static" / "extracted" / "version"
            extracted.mkdir(parents=True)
            (extracted / "routes.txt").write_text(
                "route_id,route_type\nU,400\nS,109\nT,900\nB,700\n"
            )
            (extracted / "trips.txt").write_text(
                "route_id,service_id,trip_id,start_date,start_time\n"
                "U,WK,u1,20260902,12:00:00\n"
                "S,WK,s1,,\n"
                "T,WK,trip-1,,\n"
                "B,WK,b1,,\n"
            )
            lookup = transitops.load_static_trip_lookup(extracted)
            self.assertEqual(lookup["u1"]["mode"], "subway")
            self.assertEqual(lookup["s1"]["mode"], "rail")
            self.assertEqual(lookup["trip-1"]["mode"], "tram")
            self.assertNotIn("b1", lookup)

    def test_collector_uses_active_static_lookup_for_mode_filtering(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            extracted = data / "static" / "extracted" / "version"
            extracted.mkdir(parents=True)
            state.mkdir()
            (state / "static" / "production").mkdir(parents=True)
            (state / "static" / "production" / "active.json").write_text(json.dumps({"sha256": "version"}))
            (extracted / "routes.txt").write_text("route_id,route_type\nroute-1,900\nroute-bus,700\n")
            (extracted / "trips.txt").write_text("route_id,trip_id\nroute-1,trip-1\nroute-bus,trip-bus\n")
            payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
            lookup = transitops.load_static_trip_lookup(extracted)
            rows = transitops.normalize_realtime_feed(
                payload,
                slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
                static_lookup=lookup,
            )
            self.assertEqual(lookup["trip-1"]["mode"], "tram")
            self.assertNotIn("trip-bus", lookup)
            self.assertTrue(all(row["mode"] == "tram" for row in rows))

    def test_normalization_filters_out_of_scope_modes(self):
        feed = transitops.gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp())
        for trip_id, route_id in (("trip-tram", "route-tram"), ("trip-bus", "route-bus")):
            entity = feed.entity.add()
            entity.id = trip_id
            entity.trip_update.trip.trip_id = trip_id
            entity.trip_update.trip.route_id = route_id
            stop = entity.trip_update.stop_time_update.add()
            stop.stop_id = "stop-1"
            stop.arrival.time = int(datetime(2026, 9, 2, 12, 1, tzinfo=timezone.utc).timestamp())

        rows = transitops.normalize_realtime_feed(
            feed.SerializeToString(),
            slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            static_lookup={
                "trip-tram": {"route_id": "route-tram", "mode": "tram"},
                "trip-bus": {"route_id": "route-bus", "mode": "bus"},
            },
        )

        self.assertEqual([row["trip_id"] for row in rows], ["trip-tram"])

    def test_unknown_trips_are_excluded_when_static_lookup_is_present(self):
        feed = transitops.gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp())
        for trip_id in ("known", "unknown"):
            entity = feed.entity.add()
            entity.id = trip_id
            entity.trip_update.trip.trip_id = trip_id
            stop = entity.trip_update.stop_time_update.add()
            stop.stop_id = "stop-1"
            stop.arrival.time = int(datetime(2026, 9, 2, 12, 1, tzinfo=timezone.utc).timestamp())

        rows = transitops.normalize_realtime_feed(
            feed.SerializeToString(),
            slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            static_lookup={"known": {"route_id": "route-1", "mode": "tram"}},
        )

        self.assertEqual([row["trip_id"] for row in rows], ["known"])

    def test_rejects_slot_not_aligned_to_15_minutes(self):
        with self.assertRaises(ValueError):
            transitops.validate_slot(datetime(2026, 9, 2, 12, 7, tzinfo=timezone.utc))

    def test_accepts_utc_quarter_hour_slot(self):
        slot = datetime(2026, 9, 2, 12, 15, tzinfo=timezone.utc)
        self.assertEqual(transitops.validate_slot(slot), slot)

    @contextmanager
    def serve(self, payload):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/protobuf")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/realtime.pb"
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_rejects_feed_older_than_15_minutes(self):
        now = datetime(2026, 9, 2, 12, 16, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            transitops.validate_feed_freshness(
                int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp()), now
            )

    def test_rejects_feed_more_than_5_minutes_in_the_future(self):
        now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            transitops.validate_feed_freshness(
                int(datetime(2026, 9, 2, 12, 6, tzinfo=timezone.utc).timestamp()), now
            )

    def test_accepts_feed_within_freshness_bounds(self):
        now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(
            transitops.validate_feed_freshness(
                int(datetime(2026, 9, 2, 11, 59, tzinfo=timezone.utc).timestamp()), now
            )
        )
        self.assertTrue(
            transitops.validate_feed_freshness(
                int(datetime(2026, 9, 2, 12, 5, tzinfo=timezone.utc).timestamp()), now
            )
        )

    def test_committed_realtime_fixture_is_valid(self):
        fixture = ROOT / "tests" / "fixtures" / "realtime.pb"
        self.assertTrue(fixture.is_file())
        feed = transitops.gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(fixture.read_bytes())
        self.assertEqual(feed.header.gtfs_realtime_version, "2.0")
        self.assertEqual(len(feed.entity), 1)

    def test_writes_normalized_slot_to_date_partitioned_parquet(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            data.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            result = transitops.write_realtime_slot(
                data,
                payload,
                slot=slot,
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
            )
            output = data / "parquet" / "observations" / "date=2026-09-02" / "12-00.parquet"
            self.assertEqual(result["status"], "success")
            self.assertTrue(output.is_file())
            table = transitops.pyarrow.parquet.read_table(output)
            self.assertEqual(table.column_names, [
                "slot_utc", "feed_timestamp_utc", "static_version", "entity_id",
                "trip_id", "route_id", "start_date", "start_time", "stop_id",
                "stop_sequence", "event_kind", "scheduled_event_utc",
                "predicted_event_utc", "delay_seconds", "schedule_relationship", "mode",
            ])
            self.assertEqual(table.schema.field("stop_sequence").type, transitops.pyarrow.int32())
            self.assertEqual(table.schema.field("delay_seconds").type, transitops.pyarrow.int32())
            self.assertEqual(table.column("event_kind").to_pylist(), ["arrival", "departure"])

    def test_malformed_payload_is_rejected_without_parquet_output(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            data.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            with self.assertRaises(ValueError):
                transitops.write_realtime_slot(
                    data,
                    b"not protobuf",
                    slot=slot,
                    static_lookup={},
                )
            self.assertFalse((data / "parquet").exists())

    def test_fetches_realtime_slot_and_writes_raw_and_parquet(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

            result = transitops.collect_realtime_slot(
                data,
                state,
                url,
                slot=slot,
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(
                (data / "raw" / "realtime" / "2026-09-02" / "12-00.pb").read_bytes(),
                payload,
            )
            self.assertTrue(
                (data / "parquet" / "observations" / "date=2026-09-02" / "12-00.parquet").is_file()
            )

    def test_network_failure_writes_failed_run_record(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            result = transitops.collect_realtime_slot(
                data, state, "http://127.0.0.1:1/realtime.pb",
                slot=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
                _timeout=1,
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "network")
            self.assertTrue((state / "runs" / "production" / "realtime" / "2026-09-02T12-00.json").is_file())

    def test_oversized_realtime_response_writes_failed_run_record(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            response = mock.MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = b"x" * (64 * 1024 * 1024 + 1)
            with mock.patch.object(transitops.urllib.request, "urlopen", return_value=response):
                result = transitops.collect_realtime_slot(
                    data, state, "https://example.invalid/realtime.pb",
                    slot=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
                    static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
                )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "size")

    def test_collector_rejects_stale_feed_before_parquet_write(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

            result = transitops.collect_realtime_slot(
                data,
                state,
                url,
                slot=slot,
                now=datetime(2026, 9, 2, 12, 16, tzinfo=timezone.utc),
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
            )

            self.assertEqual(result["status"], "failed")
            self.assertFalse((data / "parquet").exists())

    def test_collector_quarantines_stale_feed_with_failure_record(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            result = transitops.collect_realtime_slot(
                data,
                state,
                url,
                slot=slot,
                now=datetime(2026, 9, 2, 12, 16, tzinfo=timezone.utc),
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "stale")
            self.assertFalse((data / "parquet").exists())
            self.assertTrue((data / "quarantine" / "realtime" / "2026-09-02" / "12-00.pb").is_file())
            record = state / "runs" / "production" / "realtime" / "2026-09-02T12-00.json"
            self.assertEqual(json.loads(record.read_text())["status"], "failed")

    def test_collector_quarantines_malformed_feed_with_failure_record(self):
        payload = b"not a protobuf"
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            result = transitops.collect_realtime_slot(
                data,
                state,
                url,
                slot=slot,
                now=slot,
                static_lookup={},
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "parse")
            self.assertFalse((data / "parquet").exists())
            self.assertTrue((data / "quarantine" / "realtime" / "2026-09-02" / "12-00.pb").is_file())
            record = state / "runs" / "production" / "realtime" / "2026-09-02T12-00.json"
            self.assertEqual(json.loads(record.read_text())["status"], "failed")

    def test_unchanged_payload_in_new_slot_is_successful_and_counted(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            lookup = {"trip-1": {"route_id": "route-1", "mode": "tram"}}
            first = transitops.collect_realtime_slot(
                data, state, url,
                slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
                now=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
                static_lookup=lookup,
            )
            second = transitops.collect_realtime_slot(
                data, state, url,
                slot=datetime(2026, 9, 2, 12, 15, tzinfo=timezone.utc),
                now=datetime(2026, 9, 2, 12, 15, tzinfo=timezone.utc),
                static_lookup=lookup,
            )
            self.assertEqual(first["status"], "success")
            self.assertEqual(second["status"], "success")
            self.assertTrue(second["unchanged_payload"])
            metrics = json.loads((state / "metrics" / "production.json").read_text())
            self.assertEqual(metrics["unchanged_payloads"], 1)

    def test_successful_collector_writes_atomic_slot_success_record(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            data.mkdir()
            state.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            result = transitops.collect_realtime_slot(
                data, state, url, slot=slot, now=slot,
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
            )
            self.assertEqual(result["status"], "success")
            record = state / "runs" / "production" / "realtime" / "2026-09-02T12-00.json"
            saved = json.loads(record.read_text())
            self.assertEqual(saved["status"], "success")
            self.assertEqual(saved["scheduler"], "cron")
            self.assertEqual(saved["data_origin"], "real")
            self.assertEqual(saved["namespace"], "production")
            self.assertEqual(saved["rows"], 2)
            self.assertEqual(saved["payload_sha256"], __import__("hashlib").sha256(payload).hexdigest())
            self.assertEqual(saved["parquet_path"], result["path"])

    def test_repeated_slot_write_is_already_complete(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            data.mkdir()
            slot = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
            arguments = {
                "slot": slot,
                "static_lookup": {"trip-1": {"route_id": "route-1", "mode": "tram"}},
            }
            first = transitops.write_realtime_slot(data, payload, **arguments)
            output = data / first["path"]
            before = output.read_bytes()
            second = transitops.write_realtime_slot(data, payload, **arguments)
            self.assertEqual(first["status"], "success")
            self.assertEqual(second["status"], "already_complete")
            self.assertEqual(output.read_bytes(), before)

    def test_normalize_rejects_stale_feed_timestamp(self):
        payload = (ROOT / "tests" / "fixtures" / "realtime.pb").read_bytes()
        with self.assertRaises(ValueError):
            transitops.normalize_realtime_feed(
                payload,
                slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
                static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
                now=datetime(2026, 9, 2, 12, 16, tzinfo=timezone.utc),
            )

    def test_normalizes_arrival_and_departure_events(self):
        feed = transitops.gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp())
        entity = feed.entity.add()
        entity.id = "entity-1"
        update = entity.trip_update
        update.trip.trip_id = "trip-1"
        update.trip.route_id = "route-1"
        stop_update = update.stop_time_update.add()
        stop_update.stop_id = "stop-1"
        stop_update.stop_sequence = 1
        stop_update.arrival.time = int(datetime(2026, 9, 2, 12, 1, tzinfo=timezone.utc).timestamp())
        stop_update.departure.time = int(datetime(2026, 9, 2, 12, 2, tzinfo=timezone.utc).timestamp())

        rows = transitops.normalize_realtime_feed(
            feed.SerializeToString(),
            slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            static_lookup={"trip-1": {"route_id": "route-1", "mode": "tram"}},
        )

        self.assertEqual([row["event_kind"] for row in rows], ["arrival", "departure"])
        self.assertEqual(rows[0]["entity_id"], "entity-1")
        self.assertEqual(rows[0]["stop_id"], "stop-1")
        self.assertEqual(rows[1]["predicted_event_utc"], "2026-09-02T12:02:00+00:00")
        for field in (
            "static_version",
            "start_date",
            "start_time",
            "scheduled_event_utc",
            "delay_seconds",
            "schedule_relationship",
        ):
            self.assertIn(field, rows[0])
        self.assertIsNone(rows[0]["scheduled_event_utc"])
        self.assertIsNone(rows[0]["delay_seconds"])
        self.assertIsNone(rows[0]["schedule_relationship"])
        self.assertIsNone(rows[0]["static_version"])
        self.assertIsNone(rows[0]["start_date"])
        self.assertIsNone(rows[0]["start_time"])

        self.assertEqual(set(rows[0]), {
            "slot_utc", "feed_timestamp_utc", "static_version", "entity_id",
            "trip_id", "route_id", "start_date", "start_time", "stop_id",
            "stop_sequence", "event_kind", "scheduled_event_utc",
            "predicted_event_utc", "delay_seconds", "schedule_relationship", "mode",
        })

    def test_normalizes_schedule_relationship_and_delay(self):
        feed = transitops.gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = int(datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc).timestamp())
        entity = feed.entity.add()
        entity.id = "entity-2"
        update = entity.trip_update
        update.trip.trip_id = "trip-2"
        update.trip.route_id = "route-2"
        update.trip.start_date = "20260902"
        update.trip.start_time = "12:00:00"
        update.trip.schedule_relationship = transitops.gtfs_realtime_pb2.TripDescriptor.CANCELED
        stop_update = update.stop_time_update.add()
        stop_update.stop_id = "stop-2"
        stop_update.arrival.time = int(datetime(2026, 9, 2, 12, 1, tzinfo=timezone.utc).timestamp())
        stop_update.arrival.delay = 90
        rows = transitops.normalize_realtime_feed(
            feed.SerializeToString(),
            slot=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc),
            static_lookup={},
        )
        self.assertEqual(rows[0]["start_date"], "20260902")
        self.assertEqual(rows[0]["start_time"], "12:00:00")
        self.assertEqual(rows[0]["delay_seconds"], 90)
        self.assertEqual(rows[0]["schedule_relationship"], "CANCELED")



class StaticFeedTest(unittest.TestCase):
    @staticmethod
    def synthetic_static_zip():
        files = {
            "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nA,Demo,https://example.test,Europe/Berlin\n",
            "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Demo Stop,52.5,13.4\n",
            "routes.txt": "route_id,agency_id,route_short_name,route_long_name,route_type\nT,A,M1,Tram,0\nU,A,U1,Subway,1\nR,A,S1,Rail,2\nB,A,B1,Bus,3\n",
            "trips.txt": "route_id,service_id,trip_id\nT,WK,T1\nU,WK,U1\nR,WK,R1\nB,WK,B1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,S1,1\nU1,08:05:00,08:05:00,S1,1\nR1,08:10:00,08:10:00,S1,1\nB1,08:15:00,08:15:00,S1,1\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWK,1,1,1,1,1,0,0,20260901,20260930\n",
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output.getvalue()

    @contextmanager
    def serve(self, payload, *, delay_between_bytes=0):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("ETag", '"synthetic-v1"')
                self.end_headers()
                try:
                    if delay_between_bytes:
                        for byte in payload:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            threading.Event().wait(delay_between_bytes)
                    else:
                        self.wfile.write(payload)
                except BrokenPipeError:
                    pass

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/static.zip"
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_committed_static_fixture_is_valid_and_synthetic(self):
        fixture = ROOT / "tests" / "fixtures" / "static.zip"

        self.assertTrue(fixture.is_file())
        archive = transitops._validated_static_archive(fixture.read_bytes())
        self.assertEqual(set(transitops.REQUIRED_STATIC_FILES), set(archive.namelist()))
        self.assertLess(fixture.stat().st_size, 10_000)

    def test_static_refresh_streams_stop_times_to_disk(self):
        payload = self.synthetic_static_zip()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()
            original = zipfile.ZipFile.read

            def reject_stop_times_read(archive, name, *args, **kwargs):
                if name == "stop_times.txt":
                    raise AssertionError("stop_times.txt must be streamed")
                return original(archive, name, *args, **kwargs)

            with mock.patch.object(zipfile.ZipFile, "read", reject_stop_times_read):
                result = transitops.refresh_static_feed(
                    data,
                    state,
                    url,
                    namespace="test",
                    scheduler="test",
                    data_origin="synthetic",
                    now=datetime(2026, 9, 2, tzinfo=timezone.utc),
                )

            self.assertEqual(result["status"], "updated")

    def test_trickling_static_response_hits_total_deadline(self):
        payload = self.synthetic_static_zip()
        with tempfile.TemporaryDirectory() as directory, self.serve(
            payload, delay_between_bytes=0.01
        ) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()

            result = transitops.refresh_static_feed(
                data,
                state,
                url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
                _timeout=0.05,
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "network")

    def test_first_static_run_stores_extracts_filters_and_activates_feed(self):
        payload = self.synthetic_static_zip()
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()

            result = transitops.refresh_static_feed(
                data,
                state,
                url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
            )

            self.assertEqual(result["status"], "updated")
            self.assertEqual(result["sha256"], digest)
            self.assertEqual((data / "static" / "active" / f"{digest}.zip").read_bytes(), payload)
            extracted = data / "static" / "extracted" / digest
            self.assertTrue((extracted / "routes.txt").is_file())
            active = json.loads((state / "static" / "test" / "active.json").read_text())
            self.assertEqual(active["sha256"], digest)
            self.assertEqual(active["route_types"], ["0", "1", "2"])
            self.assertEqual(active["route_ids"], ["R", "T", "U"])

    def test_static_refresh_counts_existing_files_across_the_data_root(self):
        payload = self.synthetic_static_zip()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            (data / "raw").mkdir(parents=True)
            (data / "raw" / "existing").write_bytes(b"1234")
            state.mkdir()

            result = transitops.refresh_static_feed(
                data,
                state,
                url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
                _cap_bytes=len(payload) + 3,
            )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_kind"], "storage_cap")

            active = data / "static" / "active"
            self.assertEqual(list(active.iterdir()) if active.exists() else [], [])

    def test_identical_static_run_is_unchanged_without_new_files(self):
        payload = self.synthetic_static_zip()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()
            arguments = {
                "namespace": "test",
                "scheduler": "test",
                "data_origin": "synthetic",
                "now": datetime(2026, 9, 2, tzinfo=timezone.utc),
            }

            first = transitops.refresh_static_feed(data, state, url, **arguments)
            files_after_first = sorted(
                path.relative_to(runtime) for path in runtime.rglob("*") if path.is_file()
            )
            second = transitops.refresh_static_feed(data, state, url, **arguments)
            files_after_second = sorted(
                path.relative_to(runtime) for path in runtime.rglob("*") if path.is_file()
            )

            self.assertEqual(first["status"], "updated")
            self.assertEqual(second["status"], "unchanged")
            self.assertEqual(files_after_second, files_after_first)
            run_record = json.loads(
                (state / "runs" / "test" / "static" / "2026-09-02.json").read_text()
            )
            self.assertEqual(run_record["status"], "unchanged")
            self.assertEqual(run_record["sha256"], first["sha256"])

    def test_replaced_static_version_is_archived_when_a_retained_run_references_it(self):
        first_payload = self.synthetic_static_zip()
        first_digest = hashlib.sha256(first_payload).hexdigest()
        second_payload = first_payload + b"replacement"
        with tempfile.TemporaryDirectory() as directory, self.serve(first_payload) as first_url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()
            first = transitops.refresh_static_feed(
                data,
                state,
                first_url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
            )

            with self.serve(second_payload) as second_url:
                second = transitops.refresh_static_feed(
                    data,
                    state,
                    second_url,
                    namespace="test",
                    scheduler="test",
                    data_origin="synthetic",
                    now=datetime(2026, 9, 3, tzinfo=timezone.utc),
                )

            self.assertEqual(first["status"], "updated")
            self.assertEqual(second["status"], "updated")
            self.assertFalse((data / "static" / "active" / f"{first_digest}.zip").exists())
            self.assertEqual(
                (data / "static" / "archive" / f"{first_digest}.zip").read_bytes(),
                first_payload,
            )

    def test_replaced_unreferenced_static_version_is_removed(self):
        first_payload = self.synthetic_static_zip()
        first_digest = hashlib.sha256(first_payload).hexdigest()
        second_payload = first_payload + b"replacement"
        with tempfile.TemporaryDirectory() as directory, self.serve(first_payload) as first_url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()
            transitops.refresh_static_feed(
                data,
                state,
                first_url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
            )
            (state / "runs" / "test" / "static" / "2026-09-02.json").unlink()

            with self.serve(second_payload) as second_url:
                transitops.refresh_static_feed(
                    data,
                    state,
                    second_url,
                    namespace="test",
                    scheduler="test",
                    data_origin="synthetic",
                    now=datetime(2026, 9, 3, tzinfo=timezone.utc),
                )

            self.assertFalse((data / "static" / "active" / f"{first_digest}.zip").exists())
            self.assertFalse((data / "static" / "archive" / f"{first_digest}.zip").exists())
            self.assertFalse((data / "static" / "extracted" / first_digest).exists())

    def test_missing_required_file_is_quarantined_without_activation(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("agency.txt", "agency_id,agency_name,agency_url,agency_timezone\n")
        payload = output.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()

            result = transitops.refresh_static_feed(
                data,
                state,
                url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
            )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["sha256"], digest)
            self.assertIn("missing required files", result["error"])
            quarantine = data / "quarantine" / "static" / "2026-09-02" / f"{digest}.zip"
            self.assertEqual(quarantine.read_bytes(), payload)
            self.assertFalse((state / "static" / "test" / "active.json").exists())
            run_record = json.loads(
                (state / "runs" / "test" / "static" / "2026-09-02.json").read_text()
            )
            self.assertEqual(run_record["status"], "failed")

    def test_traversal_member_is_quarantined_without_writing_outside_data(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("../escape.txt", "no")
        payload = output.getvalue()
        with tempfile.TemporaryDirectory() as directory, self.serve(payload) as url:
            runtime = Path(directory)
            data = runtime / "data"
            state = runtime / "state"
            data.mkdir()
            state.mkdir()

            result = transitops.refresh_static_feed(
                data,
                state,
                url,
                namespace="test",
                scheduler="test",
                data_origin="synthetic",
                now=datetime(2026, 9, 2, tzinfo=timezone.utc),
            )

            self.assertEqual(result["status"], "failed")
            self.assertIn("unsafe member", result["error"])
            self.assertFalse((runtime / "escape.txt").exists())


class MetricsTest(unittest.TestCase):
    def test_metrics_separate_slot_coverage_and_entity_completeness(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state = Path(directory) / "state"
            (data / "raw").mkdir(parents=True)
            (data / "raw" / "sample.pb").write_bytes(b"1234")
            (state / "runs" / "production" / "realtime").mkdir(parents=True)
            records = {
                "2026-09-02T12-00.json": {"status": "success", "rows": 2},
                "2026-09-02T12-15.json": {"status": "failed", "failure_kind": "stale", "rows": 0},
                "2026-09-02T12-30.json": {"status": "success", "rows": 0, "unchanged_payload": True},
                "2026-09-03T12-00.json": {"status": "success", "rows": 99},
            }
            for name, record in records.items():
                (state / "runs" / "production" / "realtime" / name).write_text(json.dumps(record))

            result = transitops.build_metrics(data, state, namespace="production", start="2026-09-02T12:00:00Z", end="2026-09-02T12:45:00Z")

            self.assertEqual(result["expected_slots"], 3)
            self.assertEqual(result["attempted_slots"], 3)
            self.assertEqual(result["successful_slots"], 2)
            self.assertEqual(result["slot_coverage"], 2 / 3)
            self.assertEqual(result["stale_slots"], 1)
            self.assertEqual(result["unchanged_payloads"], 1)
            self.assertEqual(result["entity_completeness"], 2)
            self.assertEqual(result["counted_bytes"], 4)


class AirflowDemoTest(unittest.TestCase):
    def test_airflow_demo_is_synthetic_and_isolated(self):
        compose = (ROOT / "compose.yaml").read_text()
        dag = (ROOT / "airflow" / "dags" / "transitops_demo.py").read_text()
        self.assertIn("apache/airflow:3.3.1", compose)
        self.assertIn("/demo-data", compose)
        self.assertNotIn("production/data", compose)
        self.assertNotIn("production/state", compose)
        self.assertIn("data-origin synthetic", dag)
        self.assertIn("namespace demo", dag)
        self.assertIn("--runtime-root /demo-data", dag)
        self.assertIn("--campaign-start", dag)
        self.assertIn("--slot", dag)
        self.assertNotIn("production", dag)


class CronInstallerTest(unittest.TestCase):
    def test_installer_refuses_unmatched_marker_without_dropping_jobs(self):
        installer = ROOT / "scripts" / "install_cron.sh"
        existing = "# unrelated\n0 1 * * * /usr/bin/true\n# BEGIN TRANSITOPS BERLIN\n"
        result = subprocess.run(
            ["bash", str(installer), "--repo", str(ROOT), "--input", "/dev/stdin", "--dry-run"],
            input=existing, text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_installer_refuses_reversed_markers(self):
        installer = ROOT / "scripts" / "install_cron.sh"
        existing = "# END TRANSITOPS BERLIN\n0 1 * * * /usr/bin/true\n# BEGIN TRANSITOPS BERLIN\n"
        result = subprocess.run(
            ["bash", str(installer), "--repo", str(ROOT), "--input", "/dev/stdin", "--dry-run"],
            input=existing, text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_installer_replaces_only_its_marker_block(self):
        installer = ROOT / "scripts" / "install_cron.sh"
        existing = "# unrelated\n0 1 * * * /usr/bin/true\n"
        result = subprocess.run(
            ["bash", str(installer), "--repo", str(ROOT), "--input", "/dev/stdin", "--dry-run"],
            input=existing,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# unrelated\n0 1 * * * /usr/bin/true", result.stdout)
        self.assertEqual(result.stdout.count("# BEGIN TRANSITOPS BERLIN"), 1)
        self.assertEqual(result.stdout.count("# END TRANSITOPS BERLIN"), 1)
        self.assertIn(f"--runtime-root {ROOT}", result.stdout)
        self.assertIn("scripts/transitops.py realtime", result.stdout)
        self.assertIn("mkdir -p state", result.stdout)
        self.assertIn("scripts/transitops.py maintain", result.stdout)
        self.assertIn("--scheduler cron --data-origin real", result.stdout)


class MaintenanceTest(unittest.TestCase):
    def test_compacts_completed_day_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            completed = data / "parquet" / "observations" / "date=2026-09-02"
            completed.mkdir(parents=True)
            current = data / "parquet" / "observations" / "date=2026-09-04"
            current.mkdir(parents=True)
            schema = transitops.pyarrow.schema([
                transitops.pyarrow.field("event_kind", transitops.pyarrow.string()),
                transitops.pyarrow.field("stop_sequence", transitops.pyarrow.int32()),
            ])
            for name, rows in (("12-00", [{"event_kind": "arrival", "stop_sequence": 1}]), ("12-15", [{"event_kind": "departure", "stop_sequence": 2}])):
                transitops.pyarrow.parquet.write_table(
                    transitops.pyarrow.Table.from_pylist(rows, schema=schema), completed / f"{name}.parquet"
                )
            transitops.pyarrow.parquet.write_table(
                transitops.pyarrow.Table.from_pylist([{"event_kind": "arrival", "stop_sequence": 3}], schema=schema),
                current / "12-00.parquet",
            )

            result = transitops.compact_completed_day(data, date="2026-09-02")

            self.assertEqual(result["rows"], 2)
            daily = completed / "observations.parquet"
            self.assertTrue(daily.is_file())
            self.assertFalse((completed / "12-00.parquet").exists())
            self.assertFalse((completed / "12-15.parquet").exists())
            self.assertTrue((current / "12-00.parquet").exists())
            self.assertEqual(
                transitops.pyarrow.parquet.read_table(daily).column("stop_sequence").to_pylist(), [1, 2]
            )

    def test_removes_only_raw_and_quarantine_files_older_than_48_hours(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
            old = data / "raw" / "realtime" / "2026-09-01" / "12-00.pb"
            live = data / "quarantine" / "realtime" / "2026-09-03" / "12-00.pb"
            old.parent.mkdir(parents=True)
            live.parent.mkdir(parents=True)
            old.write_bytes(b"old")
            live.write_bytes(b"live")

            result = transitops.maintain_retention(data, now=now)

            self.assertEqual(result["removed"], 1)
            self.assertFalse(old.exists())
            self.assertTrue(live.exists())


class TrustBoundaryTest(unittest.TestCase):
    def test_rejects_real_origin_outside_production_namespace(self):
        for scheduler, origin, namespace in [
            ("cron", "real", "demo"),
            ("cron", "real", "test"),
        ]:
            with self.subTest(scheduler=scheduler, origin=origin, namespace=namespace):
                with self.assertRaises(ValueError):
                    transitops.validate_trust_boundary(scheduler, origin, namespace)

    def test_rejects_airflow_with_real_origin(self):
        with self.assertRaises(ValueError):
            transitops.validate_trust_boundary("airflow", "real", "production")

    def test_accepts_valid_combinations(self):
        self.assertEqual(
            transitops.validate_trust_boundary("cron", "real", "production"),
            ("cron", "real", "production"),
        )
        self.assertEqual(
            transitops.validate_trust_boundary("airflow", "synthetic", "demo"),
            ("airflow", "synthetic", "demo"),
        )


if __name__ == "__main__":
    unittest.main()
