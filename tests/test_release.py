import json
import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts import transitops


ROOT = Path(__file__).parents[1]
DBT = ROOT / ".venv" / "bin" / "dbt"


class ReleasePublicationTest(unittest.TestCase):
    def test_failed_build_preserves_current_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            releases = Path(directory) / "releases"
            releases.mkdir()
            manifest = Path(directory) / "current.json"
            manifest.write_text('{"release": "old.duckdb"}\n')

            with self.assertRaises(transitops.ReleaseBuildError):
                transitops.build_and_publish_release(
                    releases,
                    manifest,
                    project_dir=ROOT / "missing-dbt-project",
                    dbt_bin=DBT,
                )

            self.assertEqual(manifest.read_text(), '{"release": "old.duckdb"}\n')
            self.assertEqual(list(releases.iterdir()), [])

    def test_successful_build_reopens_read_only_before_manifest_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            releases = root / "releases"
            manifest = root / "current.json"

            result = transitops.build_and_publish_release(
                releases,
                manifest,
                project_dir=ROOT,
                dbt_bin=DBT,
            )

            published = Path(result["path"])
            self.assertTrue(published.is_file())
            self.assertEqual(json.loads(manifest.read_text())["path"], str(published))
            connection = duckdb.connect(str(published), read_only=True)
            try:
                self.assertEqual(
                    connection.sql("select observation_count from main_marts.mart_reliability").fetchone()[0],
                    3,
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
