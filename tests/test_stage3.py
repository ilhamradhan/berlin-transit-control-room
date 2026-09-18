import csv
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from google.transit import gtfs_realtime_pb2

from scripts.transitops import load_static_trip_lookup, normalize_realtime_feed


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
    def test_realtime_events_use_static_stop_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "routes.txt").write_text(
                "route_id,route_type\nroute-u2,400\n", encoding="utf-8"
            )
            (root / "trips.txt").write_text(
                "route_id,trip_id\nroute-u2,trip-u2\n",
                encoding="utf-8",
            )
            (root / "stop_times.txt").write_text(
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "trip-u2,08:10:00,08:11:00,stop-alex,1\n",
                encoding="utf-8",
            )
            lookup = load_static_trip_lookup(root)

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        feed.header.timestamp = int(datetime(2026, 9, 17, 7, 59, tzinfo=timezone.utc).timestamp())
        entity = feed.entity.add()
        entity.id = "entity-u2"
        update = entity.trip_update
        update.trip.trip_id = "trip-u2"
        update.trip.start_date = "20260917"
        stop = update.stop_time_update.add()
        stop.stop_id = "stop-alex"
        stop.stop_sequence = 1
        stop.departure.time = int(datetime(2026, 9, 17, 8, 12, tzinfo=timezone.utc).timestamp())

        rows = normalize_realtime_feed(
            feed.SerializeToString(),
            slot=datetime(2026, 9, 17, 8, tzinfo=timezone.utc),
            static_lookup=lookup,
        )

        self.assertEqual(rows[0]["scheduled_event_utc"], "2026-09-17T08:11:00+00:00")

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
