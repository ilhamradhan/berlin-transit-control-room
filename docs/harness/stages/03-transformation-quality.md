# Stage 3 — Transformation and Quality

## Status

Stage 3 baseline and dependency feasibility complete. Synthetic transformation
implementation has not started.

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

## Next gate

Proceed to Task 2: write the failing synthetic fixture contract tests first.
Do not use real campaign data in fixtures or begin release publication code.
