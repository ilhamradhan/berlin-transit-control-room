FROM apache/airflow:3.3.1
COPY requirements-stage2.txt /tmp/requirements-stage2.txt
RUN pip install --no-cache-dir -r /tmp/requirements-stage2.txt
COPY requirements-stage3.txt /tmp/requirements-stage3.txt
RUN pip install --no-cache-dir -r /tmp/requirements-stage3.txt
COPY dbt_project.yml profiles.yml /opt/airflow/dbt/
COPY models /opt/airflow/dbt/models
COPY tests /opt/airflow/dbt/tests
