"""Export a small, sanitized public artifact from a verified DuckDB release."""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


METRIC_DEFINITIONS = {
    "median_delay_seconds": "Median predicted delay in seconds.",
    "p90_delay_seconds": "90th percentile predicted delay in seconds.",
    "on_time_rate": "Share of observations at most five minutes late.",
    "severe_delay_rate": "Share of observations more than fifteen minutes late.",
    "cancellation_rate": "Source-provided cancellation rate; unavailable in this release when no cancellation field exists.",
    "realtime_coverage_rate": "Share of expected collection slots represented by the verified release.",
    "schedule_match_rate": "Share of observations with a validated static schedule match.",
}


def _coverage_status(rate: float) -> str:
    if rate < 0.75:
        raise ValueError("coverage is below the 75% public minimum")
    return "complete" if rate >= 0.9 else "low"


def _require_release(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("database must be a regular file")


def _require_verified_manifest(database: Path, manifest: Path) -> None:
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("manifest must be a regular file")
    try:
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        manifest_path = Path(metadata["path"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest is invalid") from exc
    if not metadata.get("verified_read_only"):
        raise ValueError("manifest does not identify a verified read-only release")
    if not manifest_path.is_absolute():
        manifest_path = manifest.parent / manifest_path
    if manifest_path.resolve() != database.resolve():
        raise ValueError("manifest does not reference the selected release")


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("metric values cannot be boolean")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("metric values must be finite")
    return result


def _as_count(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("count values must be non-negative integers")
    return value


def _as_rate(value: Any) -> float:
    result = _as_float(value)
    if result is None or not 0 <= result <= 1:
        raise ValueError("rate values must be finite numbers from 0 to 1")
    return result


def export_public_artifacts(
    database: str | os.PathLike[str],
    output: str | os.PathLike[str],
    *,
    release_id: str,
    generated_at: str | None = None,
    manifest: str | os.PathLike[str],
) -> None:
    """Write deterministic, compact aggregates without exposing private columns."""
    database_path = Path(database)
    output_path = Path(output)
    _require_release(database_path)
    _require_verified_manifest(database_path, Path(manifest))
    if not release_id or "/" in release_id or "\\" in release_id:
        raise ValueError("release_id must be a non-empty identifier")
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if "T" not in generated_at or parsed_generated_at.tzinfo is None:
            raise ValueError
    except (AttributeError, ValueError) as exc:
        raise ValueError("generated_at must be an ISO timestamp") from exc

    try:
        connection = duckdb.connect(str(database_path), read_only=True)
    except Exception as exc:
        raise ValueError(f"could not open verified release: {exc}") from exc
    try:
        summary = connection.execute(
            """
            select observation_count, entity_count, slot_count,
                   covered_slot_count, slot_coverage_rate, median_delay_seconds,
                   p90_delay_seconds, on_time_rate, severe_delay_rate,
                   schedule_match_rate
            from main_marts.mart_reliability
            limit 1
            """
        ).fetchone()
        if summary is None:
            raise ValueError("verified release has no reliability summary")
        columns = [
            "observation_count", "entity_count", "slot_count", "covered_slot_count",
            "realtime_coverage_rate", "median_delay_seconds", "p90_delay_seconds",
            "on_time_rate", "severe_delay_rate", "schedule_match_rate",
        ]
        summary_data = dict(zip(columns, summary, strict=True))
        coverage = _as_rate(summary_data["realtime_coverage_rate"])
        aggregates = connection.execute(
            """
            select cast(slot_utc at time zone 'UTC' at time zone 'Europe/Berlin' as date) as service_date,
                   mode,
                   route_id,
                   count(*) as observation_count,
                   quantile_cont(delay_seconds, 0.5) as median_delay_seconds,
                   quantile_cont(delay_seconds, 0.9) as p90_delay_seconds,
                   count(*) filter (where is_on_time)::double / nullif(count(*), 0) as on_time_rate,
                   count(*) filter (where is_severe_delay)::double / nullif(count(*), 0) as severe_delay_rate,
                   count(*) filter (where schedule_relationship = 'SCHEDULED')::double / nullif(count(*), 0) as schedule_match_rate
            from main_intermediate.int_reliability_observations
            group by service_date, mode, route_id
            order by service_date, mode, route_id
            """
        ).fetchall()
    except duckdb.Error as exc:
        raise ValueError(f"verified release is missing the public export contract: {exc}") from exc
    finally:
        connection.close()

    rows = [
        {
            "service_date": str(row[0]),
            "mode": row[1],
            "route_id": row[2],
            "observation_count": int(row[3]),
            "median_delay_seconds": _as_float(row[4]),
            "p90_delay_seconds": _as_float(row[5]),
            "on_time_rate": _as_rate(row[6]),
            "severe_delay_rate": _as_rate(row[7]),
            "schedule_match_rate": _as_rate(row[8]),
        }
        for row in aggregates
    ]
    if any(not isinstance(row["mode"], str) or not row["mode"] or not isinstance(row["route_id"], str) or not row["route_id"] for row in rows):
        raise ValueError("aggregate dimensions must be non-empty strings")
    artifact = {
        "schema_version": "1",
        "release_id": release_id,
        "generated_at": generated_at,
        "provenance": {
            "source": "VBB GTFS-Realtime",
            "data_origin": "accepted_finite_campaign",
            "campaign_days": 7,
            "coverage_status": _coverage_status(coverage),
            "realtime_coverage_rate": coverage,
        },
        "summary": {
            "observation_count": _as_count(summary_data["observation_count"]),
            "entity_count": _as_count(summary_data["entity_count"]),
            "slot_count": _as_count(summary_data["slot_count"]),
            "covered_slot_count": _as_count(summary_data["covered_slot_count"]),
            "median_delay_seconds": _as_float(summary_data["median_delay_seconds"]),
            "p90_delay_seconds": _as_float(summary_data["p90_delay_seconds"]),
            "realtime_coverage_rate": coverage,
            "on_time_rate": _as_rate(summary_data["on_time_rate"]),
            "severe_delay_rate": _as_rate(summary_data["severe_delay_rate"]),
            "schedule_match_rate": _as_rate(summary_data["schedule_match_rate"]),
            "cancellation_rate": None,
        },
        "metric_definitions": METRIC_DEFINITIONS,
        "aggregates": rows,
    }
    parent = output_path.parent
    while parent != parent.parent:
        if parent.is_symlink():
            raise ValueError("output has a symlinked parent")
        parent = parent.parent
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=output_path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(artifact, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, output_path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
