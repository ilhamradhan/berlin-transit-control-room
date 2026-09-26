# Stage 3 — Transformation and Quality

## Status

Stage 3 remediation integration is complete and merged to `main` at `926e674`.
The three remediation snapshots were integrated without starting Stage 4:

- Airflow demo: isolated synthetic DAG execution and committed fixtures.
- Contract: static `stop_times.txt` schedule mapping populates `scheduled_event_utc` for realtime events.
- Release: path/symlink validation, bounded dbt execution output and timeout, read-only candidate reopen, transactional static activation, and reader-aware retention.

Production collection remains cron-only and is stopped. No production collector,
cron installation, or Airflow service was run for this stage.

## Remediation evidence

- Airflow demo uses only `/demo-data`, synthetic `static.zip` and `realtime.pb`,
  and the exact `demo_static` → `demo_realtime` → `dbt_parse` → `dbt_seed` →
  `dbt_run` → `dbt_test` dependency chain.
- Realtime normalization reads the active static feed's `stop_times.txt` and
  combines GTFS service date plus scheduled arrival/departure time into UTC;
  unmapped trips or malformed schedule values remain null.
- Release and active-reader paths reject traversal and symlink traversal.
- dbt subprocesses have a 300-second timeout and retain only bounded output while reading.
- Static activation stages files before publishing metadata and removes files
  moved by a failed activation.
- Failed release candidates never replace the current manifest; successful
  candidates are reopened read-only before publication.
- Post-rename publication and retention failures restore the prior manifest and
  remove the new release.
- Active-reader registration and retention share the release storage lock;
  retention keeps the current release, the previous verified release, and any
  release referenced by an active-reader marker.

## Verification

All commands ran in this worktree with synthetic fixtures or temporary paths.

```text
$ .venv/bin/python -m unittest tests.test_stage3 tests.test_release tests.test_airflow_demo tests.test_transitops -v
Ran 95 tests — OK; retention cleanup failure, current/previous retention, active-reader safety,
bounded dbt output, timeout process containment, and rollback-safe publication covered

$ .venv/bin/python -m unittest discover -s tests -q
Ran 102 tests — OK

$ .venv/bin/dbt parse --project-dir . --profiles-dir . --target-path /tmp/transitops-stage3-final/target
exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-final/transitops.duckdb .venv/bin/dbt seed --project-dir . --profiles-dir . --target-path /tmp/transitops-stage3-final/target
PASS=1; exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-final/transitops.duckdb .venv/bin/dbt run --project-dir . --profiles-dir . --target-path /tmp/transitops-stage3-final/target
PASS=3; exit: 0

$ DBT_DUCKDB_PATH=/tmp/transitops-stage3-final/transitops.duckdb .venv/bin/dbt test --project-dir . --profiles-dir . --target-path /tmp/transitops-stage3-final/target
PASS=53; exit: 0

$ .venv/bin/python -m unittest tests.test_airflow_demo -v
Ran 6 tests — OK; exact executable demo command sequence completed in a temporary demo root

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
