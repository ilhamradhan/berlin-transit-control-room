# Stage 3 — Transformation and Quality

## Status

Stage 3 remediation integration is complete on top of `origin/main` (`2aa0d90`).
The three remediation snapshots were integrated without starting Stage 4:

- Airflow demo: isolated synthetic DAG execution and committed fixtures.
- Contract: static `stop_times.txt` schedule mapping populates `scheduled_event_utc` for realtime events.
- Release: path/symlink validation, bounded dbt execution output and timeout, read-only candidate reopen, transactional static activation, and reader-aware retention.

Production collection remains cron-only. No production collector, cron installation,
Airflow service, commit, or push was run.

## Remediation evidence

- Airflow demo uses only `/demo-data`, synthetic `static.zip` and `realtime.pb`,
  and the exact `demo_static` → `demo_realtime` → `dbt_parse` → `dbt_seed` →
  `dbt_run` → `dbt_test` dependency chain.
- Realtime normalization reads the active static feed's `stop_times.txt` and
  combines GTFS service date plus scheduled arrival/departure time into UTC;
  unmapped trips or malformed schedule values remain null.
- Release and active-reader paths reject traversal and symlink traversal.
- dbt subprocesses have a 300-second timeout and bounded tail output.
- Static activation stages files before publishing metadata and removes files
  moved by a failed activation.
- Failed release candidates never replace the current manifest; successful
  candidates are reopened read-only before publication.
- Retention keeps the current release, the previous verified release, and any
  release referenced by an active-reader marker.

## Verification

All commands ran in this worktree with synthetic fixtures or temporary paths.

```text
$ .venv/bin/python -m unittest tests.test_stage3 tests.test_release tests.test_airflow_demo tests.test_transitops -v
Ran 90 tests — OK

$ .venv/bin/python -m unittest discover -s tests -q
Ran 97 tests — OK

$ .venv/bin/dbt parse --project-dir . --profiles-dir . --target-path /tmp/transitops-stage3-gate/target
exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-gate/transitops.duckdb .venv/bin/dbt seed ...
PASS=1; exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-gate/transitops.duckdb .venv/bin/dbt run ...
PASS=3; exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-gate/transitops.duckdb .venv/bin/dbt test ...
PASS=53; exit: 0

$ .venv/bin/python -m unittest tests.test_airflow_demo -v
Ran 5 tests — OK; exact executable demo command sequence completed in a temporary demo root

$ docker compose config
exit: 0

$ .venv/bin/python -m py_compile scripts/transitops.py tests/test_stage3.py tests/test_release.py tests/test_airflow_demo.py airflow/dags/transitops_demo.py
exit: 0

$ git diff --check
exit: 0
```

Added-line security scanning found no hardcoded secrets, production shell
injection, eval/exec, unsafe pickle deserialization, or interpolated SQL. The
Airflow test harness uses `shell=True` only with fixed commands assembled from
repository literals. Independent correctness/security review and Ponytail
review both passed; this task performs no commit or push.
