"""Build the two-page static public product from a sanitized artifact."""

from __future__ import annotations

import json
import math
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parents[1]
SITE = ROOT / "site"
ARTIFACT_KEYS = {
    "schema_version", "release_id", "generated_at", "provenance",
    "summary", "metric_definitions", "aggregates",
}
SUMMARY_KEYS = {
    "observation_count", "entity_count", "slot_count", "covered_slot_count",
    "median_delay_seconds", "p90_delay_seconds", "realtime_coverage_rate",
    "on_time_rate", "severe_delay_rate", "schedule_match_rate", "cancellation_rate",
}
PROVENANCE_KEYS = {"source", "data_origin", "campaign_days", "coverage_status", "realtime_coverage_rate"}
METRIC_KEYS = {
    "median_delay_seconds", "p90_delay_seconds", "on_time_rate", "severe_delay_rate",
    "cancellation_rate", "realtime_coverage_rate", "schedule_match_rate",
}
METRIC_DEFINITIONS = {
    "median_delay_seconds": "Median predicted delay in seconds.",
    "p90_delay_seconds": "90th percentile predicted delay in seconds.",
    "on_time_rate": "Share of observations at most five minutes late.",
    "severe_delay_rate": "Share of observations more than fifteen minutes late.",
    "cancellation_rate": "Source-provided cancellation rate; unavailable in this release when no cancellation field exists.",
    "realtime_coverage_rate": "Share of expected collection slots represented by the verified release.",
    "schedule_match_rate": "Share of observations with a validated static schedule match.",
}
FORBIDDEN_FIELDS = {"private_path", "trip_id", "stop_id", "entity_id", "payload"}
AGGREGATE_KEYS = {
    "service_date", "mode", "route_id", "observation_count", "median_delay_seconds",
    "p90_delay_seconds", "on_time_rate", "severe_delay_rate", "schedule_match_rate",
}


def build_static_site(artifact_path: str | Path, output_dir: str | Path) -> None:
    artifact_source = Path(artifact_path)
    output = Path(output_dir)
    parent = output.parent
    while parent != parent.parent:
        if parent.is_symlink():
            raise ValueError("output directory has a symlinked parent")
        parent = parent.parent
    if not artifact_source.is_file() or artifact_source.is_symlink():
        raise ValueError("artifact must be a regular file")
    artifact = json.loads(artifact_source.read_text(encoding="utf-8"))
    if set(artifact) != ARTIFACT_KEYS or not isinstance(artifact["summary"], dict) or not isinstance(artifact["provenance"], dict):
        raise ValueError("artifact does not match the public contract")
    if set(artifact["summary"]) != SUMMARY_KEYS or set(artifact["provenance"]) != PROVENANCE_KEYS:
        raise ValueError("artifact metadata does not match the public contract")
    if set(artifact["metric_definitions"]) != METRIC_KEYS:
        raise ValueError("artifact metric definitions do not match the public contract")
    if artifact["metric_definitions"] != METRIC_DEFINITIONS:
        raise ValueError("artifact metric definitions are not approved")
    provenance = artifact["provenance"]
    if provenance["source"] != "VBB GTFS-Realtime" or provenance["data_origin"] != "accepted_finite_campaign" or provenance["campaign_days"] != 7:
        raise ValueError("artifact provenance is not approved")
    coverage = provenance["realtime_coverage_rate"]
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool) or not math.isfinite(coverage) or not 0 <= coverage <= 1:
        raise ValueError("artifact provenance coverage is invalid")
    expected_coverage_status = "complete" if coverage >= 0.9 else "low"
    if provenance["coverage_status"] != expected_coverage_status:
        raise ValueError("artifact coverage status does not match coverage")
    if not all(isinstance(artifact[key], str) and artifact[key].strip() for key in ("release_id", "generated_at")):
        raise ValueError("artifact identifiers must be non-empty strings")
    if "/" in artifact["release_id"] or "\\" in artifact["release_id"]:
        raise ValueError("artifact release_id must be a simple identifier")
    try:
        generated_at = datetime.fromisoformat(artifact["generated_at"].replace("Z", "+00:00"))
        if "T" not in artifact["generated_at"] or generated_at.tzinfo is None:
            raise ValueError
    except ValueError as exc:
        raise ValueError("artifact generated_at must be an ISO timestamp") from exc
    encoded = json.dumps(artifact, sort_keys=True).lower()
    if any(field in encoded for field in FORBIDDEN_FIELDS):
        raise ValueError("artifact contains a forbidden private field")
    if not isinstance(artifact["aggregates"], list) or any(
        not isinstance(row, dict) or set(row) != AGGREGATE_KEYS or
        not isinstance(row["service_date"], str) or not row["service_date"] or
        not isinstance(row["mode"], str) or not row["mode"] or
        not isinstance(row["route_id"], str) or not row["route_id"] or
        type(row["observation_count"]) is not int or row["observation_count"] < 0 or
        any(not isinstance(row[key], (int, float)) or isinstance(row[key], bool) or not math.isfinite(row[key]) for key in AGGREGATE_KEYS - {"service_date", "mode", "route_id", "observation_count"}) or
        any(not 0 <= row[key] <= 1 for key in ("on_time_rate", "severe_delay_rate", "schedule_match_rate"))
        for row in artifact["aggregates"]
    ):
        raise ValueError("artifact aggregates do not match the public contract")
    for key in ("observation_count", "entity_count", "slot_count", "covered_slot_count"):
        if type(artifact["summary"][key]) is not int or artifact["summary"][key] < 0:
            raise ValueError("artifact summary counts are invalid")
    for key in ("median_delay_seconds", "p90_delay_seconds", "realtime_coverage_rate", "on_time_rate", "severe_delay_rate", "schedule_match_rate"):
        value = artifact["summary"][key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError("artifact summary metric is invalid")
    for key in ("realtime_coverage_rate", "on_time_rate", "severe_delay_rate", "schedule_match_rate"):
        if not 0 <= artifact["summary"][key] <= 1:
            raise ValueError("artifact summary rate is invalid")
    if not math.isclose(artifact["summary"]["realtime_coverage_rate"], coverage):
        raise ValueError("artifact coverage values disagree")
    cancellation_rate = artifact["summary"]["cancellation_rate"]
    if cancellation_rate is not None and (isinstance(cancellation_rate, bool) or not isinstance(cancellation_rate, (int, float)) or not math.isfinite(cancellation_rate) or not 0 <= cancellation_rate <= 1):
        raise ValueError("artifact cancellation rate is invalid")
    if output.exists():
        if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
            raise ValueError("output directory must be a new or empty regular directory")
    else:
        output.mkdir(parents=True)
    for name in ("index.html", "docs.html", "styles.css", "app.js"):
        shutil.copy2(SITE / name, output / name)
    data = output / "data"
    data.mkdir(exist_ok=True)
    (data / "public_metrics.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("artifact")
    parser.add_argument("output")
    args = parser.parse_args()
    build_static_site(args.artifact, args.output)
