import ast
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
DAG = ROOT / "airflow" / "dags" / "transitops_demo.py"
COMPOSE = ROOT / "compose.yaml"


class AirflowDemoIsolationTest(unittest.TestCase):
    def test_exact_demo_commands_execute_in_order(self):
        tree = ast.parse(DAG.read_text(encoding="utf-8"))
        commands = {
            ast.literal_eval(next(keyword.value for keyword in node.keywords if keyword.arg == "task_id")): ast.literal_eval(
                next(keyword.value for keyword in node.keywords if keyword.arg == "bash_command")
            )
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "BashOperator"
        }
        expected = ["demo_static", "demo_realtime", "dbt_parse", "dbt_seed", "dbt_run", "dbt_test"]
        self.assertEqual(list(commands), expected)

        with self.subTest("command sequence"):
            with tempfile.TemporaryDirectory() as directory:
                demo_root = Path(directory) / "demo-data"
                replacements = {
                    "/demo-data": str(demo_root),
                    "/opt/airflow/scripts/transitops.py": str(ROOT / "scripts" / "transitops.py"),
                    "/opt/airflow/fixtures": str(ROOT / "tests" / "fixtures"),
                    "/opt/airflow/dbt": str(ROOT),
                    "python ": str(ROOT / ".venv" / "bin" / "python") + " ",
                    "dbt ": str(ROOT / ".venv" / "bin" / "dbt") + " ",
                }
                for task in expected:
                    command = commands[task]
                    for old, new in replacements.items():
                        command = command.replace(old, new)
                    result = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, f"{task}: {result.stderr}")

    def test_dag_sequences_synthetic_collection_then_explicit_dbt_tasks(self):
        source = DAG.read_text(encoding="utf-8")
        tree = ast.parse(source)
        dag_ids = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }

        expected = {"demo_static", "demo_realtime", "dbt_parse", "dbt_seed", "dbt_run", "dbt_test"}
        self.assertTrue(expected <= dag_ids)
        self.assertIn("demo_static >> demo_realtime >> dbt_parse >> dbt_seed >> dbt_run >> dbt_test", source)

    def test_dag_uses_only_demo_paths_and_synthetic_inputs(self):
        source = DAG.read_text(encoding="utf-8")

        self.assertNotIn("https://", source)
        self.assertIn("--runtime-root /demo-data", source)
        self.assertIn("--root data", source)
        self.assertIn("--state-root state", source)
        self.assertIn("--scheduler airflow", source)
        self.assertIn("--data-origin synthetic", source)
        self.assertIn("--namespace demo", source)
        self.assertIn("file:///opt/airflow/fixtures/static.zip", source)
        self.assertIn("file:///opt/airflow/fixtures/realtime.pb", source)
        self.assertNotIn("warehouse/", source)
        self.assertNotIn("current.json", source)

    def test_compose_has_no_production_mounts_or_urls(self):
        source = COMPOSE.read_text(encoding="utf-8")

        self.assertIn("demo-data:/demo-data", source)
        self.assertIn("./tests/fixtures:/opt/airflow/fixtures:ro", source)
        self.assertIn("./scripts:/opt/airflow/scripts:ro", source)
        self.assertNotIn("./data", source)
        self.assertNotIn("./state", source)
        self.assertNotIn("https://", source)
        self.assertNotIn("warehouse", source)

    def test_status_artifact_writer_captures_demo_identity(self):
        import importlib.util
        import tempfile

        spec = importlib.util.spec_from_file_location("transitops", ROOT / "scripts" / "transitops.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as directory:
            artifact = module.write_status_artifact(
                Path(directory), task="dbt_test", status="success",
                scheduler="airflow", data_origin="synthetic", namespace="demo",
            )
            self.assertEqual(json.loads(artifact.read_text()), {
                "data_origin": "synthetic",
                "namespace": "demo",
                "scheduler": "airflow",
                "status": "success",
                "task": "dbt_test",
            })


if __name__ == "__main__":
    unittest.main()
