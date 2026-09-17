import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
DBT = ROOT / ".venv" / "bin" / "dbt"


class DbtMartsTest(unittest.TestCase):
    def run_dbt(self, *args, cwd):
        env = os.environ | {
            "DBT_PROFILES_DIR": str(ROOT),
            "DBT_DUCKDB_PATH": str(cwd / "target" / "transitops.duckdb"),
        }
        (cwd / "target").mkdir(exist_ok=True)
        return subprocess.run(
            [str(DBT), *args, "--project-dir", str(ROOT), "--profiles-dir", str(ROOT)],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
        )

    def test_known_fixture_builds_reliability_mart_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            for command in (("seed", "--full-refresh"), ("run",), ("test",)):
                result = self.run_dbt(*command, cwd=cwd)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            query = [
                str(DBT), "show", "--inline",
                "select observation_count, on_time_rate, severe_delay_rate, schedule_match_rate, slot_coverage_rate from main_marts.mart_reliability",
                "--project-dir", str(ROOT), "--profiles-dir", str(ROOT),
            ]
            result = subprocess.run(
                query, cwd=cwd, env=os.environ | {
                    "DBT_PROFILES_DIR": str(ROOT),
                    "DBT_DUCKDB_PATH": str(cwd / "target" / "transitops.duckdb"),
                }, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("3", result.stdout)
            self.assertIn("0.667", result.stdout)
            self.assertIn("0.333", result.stdout)
            self.assertIn("1", result.stdout)


if __name__ == "__main__":
    unittest.main()
