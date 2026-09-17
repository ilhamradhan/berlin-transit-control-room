import csv
from datetime import datetime
from pathlib import Path
import unittest


FIXTURE = Path(__file__).parent / "fixtures" / "stage3_observations.csv"
CANONICAL_COLUMNS = {
    "slot_utc",
    "feed_timestamp_utc",
    "static_version",
    "entity_id",
    "trip_id",
    "route_id",
    "start_date",
    "start_time",
    "stop_id",
    "stop_sequence",
    "event_kind",
    "scheduled_event_utc",
    "predicted_event_utc",
    "delay_seconds",
    "schedule_relationship",
    "mode",
}
PROVENANCE_COLUMNS = {"scheduler", "data_origin", "namespace"}
SCOPED_MODES = {"rail", "subway", "tram"}


def load_fixture():
    with FIXTURE.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class Stage3FixtureContractTest(unittest.TestCase):
    def test_fixture_has_canonical_observation_columns_and_provenance(self):
        with FIXTURE.open(newline="", encoding="utf-8") as stream:
            columns = set(csv.DictReader(stream).fieldnames or ())

        self.assertEqual(columns, CANONICAL_COLUMNS | PROVENANCE_COLUMNS)

    def test_fixture_contains_only_scoped_modes(self):
        rows = load_fixture()

        self.assertTrue(rows)
        self.assertTrue({row["mode"] for row in rows} <= SCOPED_MODES)
        self.assertEqual({row["mode"] for row in rows}, SCOPED_MODES)

    def test_timestamps_are_utc_and_event_order_is_preserved(self):
        rows = load_fixture()

        for row in rows:
            for column in (
                "slot_utc",
                "feed_timestamp_utc",
                "scheduled_event_utc",
                "predicted_event_utc",
            ):
                timestamp = datetime.fromisoformat(row[column].replace("Z", "+00:00"))
                self.assertEqual(timestamp.utcoffset().total_seconds(), 0)
            self.assertLessEqual(row["feed_timestamp_utc"], row["slot_utc"])

    def test_delay_and_schedule_relationship_values_are_deterministic(self):
        rows = load_fixture()

        delays = {row["trip_id"]: int(row["delay_seconds"]) for row in rows}
        relationships = {row["trip_id"]: row["schedule_relationship"] for row in rows}
        self.assertEqual(delays, {"synthetic-subway-trip": 120, "synthetic-rail-trip": -60, "synthetic-tram-trip": 960})
        self.assertEqual(relationships, {trip: "SCHEDULED" for trip in delays})

    def test_rows_identify_synthetic_source_provenance(self):
        rows = load_fixture()

        self.assertEqual(
            {(row["scheduler"], row["data_origin"], row["namespace"]) for row in rows},
            {("airflow", "synthetic", "demo")},
        )


if __name__ == "__main__":
    unittest.main()
