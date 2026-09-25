import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_static_site import build_static_site


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "public_metrics.json"


class StaticSiteTest(unittest.TestCase):
    def test_build_copies_only_public_artifact_and_two_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build_static_site(FIXTURE, output)

            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "docs.html").is_file())
            self.assertEqual(
                json.loads((output / "data" / "public_metrics.json").read_text())["schema_version"],
                "1",
            )
            html = "\n".join(path.read_text() for path in output.glob("*.html"))
            self.assertNotIn("duckdb", html.lower())
            self.assertNotIn("parquet", html.lower())
            self.assertNotIn("execute", html.lower())
            app = (output / "app.js").read_text()
            self.assertIn("may be stale", app)
            self.assertIn("Source cancellations", app)
            self.assertIn("P90 predicted delay", app)
            self.assertIn("Realtime coverage", app)
            docs = (output / "docs.html").read_text()
            for heading in ("Metric definitions", "Architecture", "Source contracts", "Runbook guidance"):
                self.assertIn(f"<h2>{heading}</h2>", docs)

    def test_synthetic_delivery_shape_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build_static_site(FIXTURE, output)
            self.assertEqual(len(list(output.glob("*.html"))), 2)
            self.assertEqual((output / "data" / "public_metrics.json").stat().st_size, 1901)
            self.assertEqual({"index.html", "docs.html", "styles.css", "app.js", "data"}, {path.name for path in output.iterdir()})
            self.assertFalse((output / "private_archive").exists())

    def test_rejects_artifact_with_private_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "bad.json"
            artifact.write_text(json.dumps({"schema_version": "1", "private_path": "/tmp/release"}))
            with self.assertRaises(ValueError):
                build_static_site(artifact, root / "site")

    def test_rejects_malformed_aggregate_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = json.loads(FIXTURE.read_text())
            artifact["aggregates"] = [{"route_id": "M1"}]
            path = root / "bad.json"
            path.write_text(json.dumps(artifact))
            with self.assertRaises(ValueError):
                build_static_site(path, root / "site")

    def test_rejects_extra_top_level_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = json.loads(FIXTURE.read_text())
            artifact["private_notes"] = "internal"
            path = root / "bad.json"
            path.write_text(json.dumps(artifact))
            with self.assertRaises(ValueError):
                build_static_site(path, root / "site")

    def test_rejects_nonempty_or_symlink_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "site"
            output.mkdir()
            (output / "stale.json").write_text("private")
            with self.assertRaises(ValueError):
                build_static_site(FIXTURE, output)
            linked = root / "linked"
            linked.symlink_to(output, target_is_directory=True)
            with self.assertRaises(ValueError):
                build_static_site(FIXTURE, linked)
            parent = root / "parent"
            parent.mkdir()
            linked_parent = root / "parent-link"
            linked_parent.symlink_to(parent, target_is_directory=True)
            with self.assertRaises(ValueError):
                build_static_site(FIXTURE, linked_parent / "site")

    def test_rejects_boolean_or_nonfinite_metric_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (True, float("nan")):
                artifact = json.loads(FIXTURE.read_text())
                artifact["aggregates"][0]["observation_count"] = value
                path = root / f"bad-{value}.json"
                path.write_text(json.dumps(artifact))
                with self.assertRaises(ValueError):
                    build_static_site(path, root / f"site-{value}")

    def test_rejects_naive_generated_at_and_boolean_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, value in (("generated_at", "2026-09-03"), ("cancellation_rate", True)):
                artifact = json.loads(FIXTURE.read_text())
                if key == "generated_at":
                    artifact[key] = value
                else:
                    artifact["summary"][key] = value
                path = root / f"bad-{key}.json"
                path.write_text(json.dumps(artifact))
                with self.assertRaises(ValueError):
                    build_static_site(path, root / f"site-{key}")

    def test_rejects_unapproved_metadata_and_inconsistent_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mutate in (lambda artifact: artifact["provenance"].update(coverage_status="complete", realtime_coverage_rate=0.8), lambda artifact: artifact["provenance"].update(source="/private/secret"), lambda artifact: artifact["metric_definitions"].update(on_time_rate="private")):
                artifact = json.loads(FIXTURE.read_text())
                mutate(artifact)
                path = root / "bad.json"
                path.write_text(json.dumps(artifact))
                with self.assertRaises(ValueError):
                    build_static_site(path, root / "site")


if __name__ == "__main__":
    unittest.main()
