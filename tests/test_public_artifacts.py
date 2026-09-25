import json
import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts.export_public_artifacts import export_public_artifacts


class PublicArtifactTest(unittest.TestCase):
    def make_database(self, root: Path, coverage: float = 1.0) -> Path:
        path = root / "release.duckdb"
        connection = duckdb.connect(str(path))
        try:
            connection.execute("create schema main_intermediate")
            connection.execute("create schema main_marts")
            connection.execute(
                """
                create table main_intermediate.int_reliability_observations (
                    slot_utc timestamp,
                    mode varchar,
                    route_id varchar,
                    delay_seconds integer,
                    is_on_time boolean,
                    is_severe_delay boolean,
                    schedule_relationship varchar
                )
                """
            )
            connection.executemany(
                "insert into main_intermediate.int_reliability_observations values (?, ?, ?, ?, ?, ?, ?)",
                [
                    ("2026-09-01 08:00:00", "tram", "M1", 60, True, False, "SCHEDULED"),
                    ("2026-09-01 08:00:00", "tram", "M1", 1200, False, True, "SCHEDULED"),
                    ("2026-09-01 23:30:00", "subway", "U2", 300, True, False, "SCHEDULED"),
                ],
            )
            connection.execute(
                """
                create table main_marts.mart_reliability (
                    observation_count integer,
                    entity_count integer,
                    slot_count integer,
                    covered_slot_count integer,
                    slot_coverage_rate double,
                    median_delay_seconds double,
                    p90_delay_seconds double,
                    on_time_rate double,
                    severe_delay_rate double,
                    schedule_match_rate double
                )
                """
            )
            connection.execute(
                "insert into main_marts.mart_reliability values (3, 3, 2, 2, ?, 300.0, 1020.0, 0.6666667, 0.3333333, 1.0)",
                [coverage],
            )
        finally:
            connection.close()
        (root / "manifest.json").write_text(json.dumps({"path": str(path), "verified_read_only": True}))
        return path

    def test_exports_sanitized_mode_route_day_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self.make_database(root)
            output = root / "public.json"

            export_public_artifacts(
                database,
                output,
                release_id="release-2026-09-03",
                generated_at="2026-09-03T12:00:00Z",
                manifest=root / "manifest.json",
            )

            artifact = json.loads(output.read_text())
            self.assertEqual(artifact["schema_version"], "1")
            self.assertEqual(artifact["release_id"], "release-2026-09-03")
            self.assertEqual(artifact["generated_at"], "2026-09-03T12:00:00Z")
            self.assertEqual(artifact["provenance"]["coverage_status"], "complete")
            self.assertEqual(len(artifact["aggregates"]), 2)
            self.assertEqual(artifact["aggregates"][0]["route_id"], "M1")
            self.assertEqual(artifact["aggregates"][1]["service_date"], "2026-09-02")
            self.assertEqual(artifact["summary"]["median_delay_seconds"], 300.0)
            self.assertEqual(artifact["summary"]["p90_delay_seconds"], 1020.0)
            self.assertIsNone(artifact["summary"]["cancellation_rate"])
            forbidden = {"trip_id", "stop_id", "entity_id", "payload", "private_path"}
            self.assertFalse(forbidden & set(json.dumps(artifact).split('"')))

    def test_marks_low_coverage_and_writes_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self.make_database(root, coverage=0.8)
            first = root / "first.json"
            second = root / "second.json"

            export_public_artifacts(database, first, release_id="r", generated_at="2026-09-01T00:00:00Z", manifest=root / "manifest.json")
            export_public_artifacts(database, second, release_id="r", generated_at="2026-09-01T00:00:00Z", manifest=root / "manifest.json")

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text())["provenance"]["coverage_status"], "low")

    def test_rejects_database_that_is_not_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                export_public_artifacts(root, root / "public.json", release_id="r", generated_at="2026-09-01T00:00:00Z", manifest=root / "manifest.json")

    def test_rejects_unverified_or_mismatched_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self.make_database(root)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"path": str(database), "verified_read_only": False}))
            with self.assertRaises(ValueError):
                export_public_artifacts(database, root / "public.json", release_id="r", generated_at="2026-09-01T00:00:00Z", manifest=manifest)

    def test_rejects_coverage_below_public_minimum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self.make_database(root, coverage=0.7499)
            with self.assertRaises(ValueError):
                export_public_artifacts(database, root / "public.json", release_id="r", generated_at="2026-09-01T00:00:00Z", manifest=root / "manifest.json")

    def test_rejects_invalid_generated_at(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self.make_database(root)
            with self.assertRaises(ValueError):
                export_public_artifacts(database, root / "public.json", release_id="r", generated_at="not-a-timestamp", manifest=root / "manifest.json")


if __name__ == "__main__":
    unittest.main()
