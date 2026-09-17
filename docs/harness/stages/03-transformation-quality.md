# Stage 3 — Transformation and Quality

## Status

Stage 3 Tasks 1-6 are complete on the upstream Task 6 branch. Task 7 adds the
isolated Airflow learning demo and its explicit dbt status artifacts.

## Preconditions verified

- `origin/main` is the merged Stage 2 release at `2aa0d90`.
- Production cron remains stopped.
- The Stage 2 seven-day campaign criterion and storage cap are accepted under
  Decision D-034.
- The Stage 3 worktree contains no `data/`, `state/`, Parquet archives, raw
  protobufs, static archives, DuckDB releases, or manifests.
- The Stage 2 collector files and runtime paths are unchanged in this step.

## Task 1 evidence: dependency feasibility

Checked before installation:

- DuckDB: absent
- dbt: absent
- dbt-duckdb: absent
- uv: absent
- Python 3.12 venv support: available

Installed only into the ignored `.venv/` of this Stage 3 worktree:

- `duckdb==1.5.5`
- `dbt-duckdb==1.11.0`

The resolver installed dbt-duckdb's pinned transitive dependencies into the
isolated environment. The production collector environment was not changed.

Verification completed:

- `duckdb` imports successfully and reports `1.5.5`.
- dbt imports successfully and reports core `1.12.5`.
- `dbt --version` succeeds.
- `pip check` succeeds.
- A temporary in-memory DuckDB query succeeds.
- `git diff --check` succeeds.

## Task 7 scope

Do not use real campaign data in the demo or run Airflow as a production VPS
service. Production collection and the collector runtime remain unchanged.

## Task 7 evidence: isolated Airflow dbt demo

**Status:** passed for the synthetic learning demo. Production scheduling and
collection remain cron-only; Airflow was not run as a VPS service.

The demo DAG now sequences `demo_static` → `demo_realtime` → `dbt_parse` →
`dbt_seed` → `dbt_run` → `dbt_test`. Collection writes and dbt artifacts are
under `/demo-data`; inputs are the committed synthetic fixtures, and every dbt
status artifact records `scheduler=airflow`, `data_origin=synthetic`, and
`namespace=demo`. Compose mounts no production data, state, warehouse, or URL.

Verification:

```text
$ .venv/bin/python -m unittest tests.test_airflow_demo -v
Ran 4 tests in 0.144s — OK

$ .venv/bin/python -m unittest discover -s tests -q
Ran 92 tests in 61.424s — OK

$ .venv/bin/dbt parse --project-dir . --profiles-dir . --target-path /tmp/transitops-task7-dbt-target
exit: 0

$ .venv/bin/dbt seed && .venv/bin/dbt run && .venv/bin/dbt test
seed PASS=1; run PASS=3; test PASS=53; exit: 0

$ docker compose config
exit: 0

$ .venv/bin/python -m py_compile scripts/transitops.py tests/test_airflow_demo.py airflow/dags/transitops_demo.py
exit: 0

$ git diff --check
exit: 0
```

No production collector, cron installation, Airflow service, commit, or push
was performed. Runtime output remained in ignored local paths or temporary
directories.
