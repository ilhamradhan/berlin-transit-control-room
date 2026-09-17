from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


with DAG(
    dag_id="transitops_demo",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:
    demo_static = BashOperator(
        task_id="demo_static",
        bash_command=(
            "python /opt/airflow/scripts/transitops.py static "
            "--runtime-root /demo-data --root /demo-data/data --state-root /demo-data/state "
            "--scheduler airflow --data-origin synthetic --namespace demo "
            "--campaign-start 2026-01-01T00:00:00Z "
            "--now 2026-09-02T12:00:00Z "
            "--static-url file:///opt/airflow/fixtures/static.zip"
        ),
    )
    demo_realtime = BashOperator(
        task_id="demo_realtime",
        bash_command=(
            "python /opt/airflow/scripts/transitops.py realtime "
            "--runtime-root /demo-data --root /demo-data/data --state-root /demo-data/state "
            "--scheduler airflow --data-origin synthetic --namespace demo "
            "--campaign-start 2026-01-01T00:00:00Z "
            "--slot 2026-09-02T12:00:00Z "
            "--now 2026-09-02T12:00:00Z "
            "--realtime-url file:///opt/airflow/fixtures/realtime.pb"
        ),
    )
    dbt_parse = BashOperator(
        task_id="dbt_parse",
        bash_command=(
            "dbt parse --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt "
            "--target-path /demo-data/dbt-target && "
            "python /opt/airflow/scripts/transitops.py status "
            "--status-root /demo-data/status --task dbt_parse --status success "
            "--scheduler airflow --data-origin synthetic --namespace demo"
        ),
    )
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=(
            "DBT_DUCKDB_PATH=/demo-data/dbt-target/transitops.duckdb "
            "dbt seed --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt "
            "--target-path /demo-data/dbt-target && "
            "python /opt/airflow/scripts/transitops.py status "
            "--status-root /demo-data/status --task dbt_seed --status success "
            "--scheduler airflow --data-origin synthetic --namespace demo"
        ),
    )
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "DBT_DUCKDB_PATH=/demo-data/dbt-target/transitops.duckdb "
            "dbt run --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt "
            "--target-path /demo-data/dbt-target && "
            "python /opt/airflow/scripts/transitops.py status "
            "--status-root /demo-data/status --task dbt_run --status success "
            "--scheduler airflow --data-origin synthetic --namespace demo"
        ),
    )
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "DBT_DUCKDB_PATH=/demo-data/dbt-target/transitops.duckdb "
            "dbt test --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt "
            "--target-path /demo-data/dbt-target && "
            "python /opt/airflow/scripts/transitops.py status "
            "--status-root /demo-data/status --task dbt_test --status success "
            "--scheduler airflow --data-origin synthetic --namespace demo"
        ),
    )
    demo_static >> demo_realtime >> dbt_parse >> dbt_seed >> dbt_run >> dbt_test
