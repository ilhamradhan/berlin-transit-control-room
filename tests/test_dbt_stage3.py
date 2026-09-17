import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
DBT = ROOT / ".venv" / "bin" / "dbt"


class DbtStage3Test(unittest.TestCase):
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

    def test_synthetic_observation_staging_builds_and_passes_contract_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            for command in (("parse",), ("seed", "--full-refresh"), ("run",), ("test",)):
                result = self.run_dbt(*command, cwd=cwd)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            self.assertTrue((cwd / "target" / "transitops.duckdb").is_file())

            query = [
                str(DBT),
                "show",
                "--inline",
                "select mode, delay_seconds from main_staging.stg_observations order by mode",
                "--project-dir",
                str(ROOT),
                "--profiles-dir",
                str(ROOT),
            ]
            result = subprocess.run(
                query,
                cwd=cwd,
                env=os.environ
                | {
                    "DBT_PROFILES_DIR": str(ROOT),
                    "DBT_DUCKDB_PATH": str(cwd / "target" / "transitops.duckdb"),
                },
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("rail", result.stdout)
            self.assertIn("960", result.stdout)


if __name__ == "__main__":
    unittest.main()
