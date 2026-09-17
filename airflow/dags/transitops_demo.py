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
            "--runtime-root /demo-data --root data --state-root state "
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
            "--runtime-root /demo-data --root data --state-root state "
            "--scheduler airflow --data-origin synthetic --namespace demo "
            "--campaign-start 2026-01-01T00:00:00Z "
            "--slot 2026-09-02T12:00:00Z "
            "--now 2026-09-02T12:00:00Z "
            "--realtime-url file:///opt/airflow/fixtures/realtime.pb"
        ),
    )
    demo_static >> demo_realtime
