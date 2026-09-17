import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
DAG = ROOT / "airflow" / "dags" / "transitops_demo.py"
COMPOSE = ROOT / "compose.yaml"


class AirflowDemoIsolationTest(unittest.TestCase):
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
        self.assertIn("--root /demo-data/data", source)
        self.assertIn("--state-root /demo-data/state", source)
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
