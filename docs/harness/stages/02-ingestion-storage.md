# Stage 2 ingestion and storage

## Task 1: minimal ingestion runtime

**Status:** passed on Ubuntu `/usr/bin/python3` 3.12.3.

The production requirements contain only the parser and Parquet libraries required by the approved plan:

- `gtfs-realtime-bindings==2.2.0`
- `pyarrow==25.0.1`

The install resolved the binding's transitive dependency to `protobuf==7.36.1`. No other application dependency was added.

## Verification evidence

`/usr/bin/python3 -m venv .venv` initially failed because this host lacks `ensurepip`. The local environment was therefore created without pip and bootstrapped from PyPA's `get-pip.py`; the temporary bootstrap file was removed. The resulting interpreter remained Python 3.12.3 and pip resolved to 26.2.1.

```text
$ /usr/bin/python3 -m venv --clear --without-pip .venv
$ .venv/bin/python /tmp/transitops-get-pip.py
Successfully installed pip-26.2.1

$ .venv/bin/python -m pip install -r requirements-stage2.txt
Successfully installed gtfs-realtime-bindings-2.2.0 protobuf-7.36.1 pyarrow-25.0.1

$ .venv/bin/python -c 'from google.transit import gtfs_realtime_pb2; import pyarrow'
import check exit: 0

$ .venv/bin/python -m pip check
No broken requirements found.
```

The local `.venv/` is ignored by Git. This task did not fetch transit data, install cron, run Airflow, commit, or push.

## Task 2: storage and isolation boundary

**Status:** passed with standard-library-only runtime controls.

`scripts/transitops.py` now validates one canonical runtime root before creating
anything beneath distinct `data` and `state` descendants. Absolute paths,
`..`, nested/equal roots, and symlink traversal are rejected. Counted storage
includes regular files only. Writes use a temporary file beside the target,
check projected usage for every chunk against the fixed `4 * 1024**3` byte
production cap, `fsync`, and publish with `os.replace`; refusal removes the
temporary file without changing the target. Lock files use non-following,
mode-0600, nonblocking `flock`. Campaign status is explicit: `active`,
`paused`, or `stopped` at 28 elapsed days. A trust boundary is validated before
any filesystem access: a real data origin is only allowed in the `production`
namespace, and the synthetic `airflow` scheduler may never collect real data.
The CLI contract uses `--root` and `--state-root` under a required
`--runtime-root`, with required `--scheduler`, `--data-origin`, and
`--namespace` flags.

The cap override is keyword-only and private to the internal Python test API;
the production CLI exposes no cap option.

### Witnessed RED

```text
$ .venv/bin/python -m unittest tests.test_transitops.RuntimePathsTest.test_accepts_distinct_descendants_of_canonical_runtime_root -v
FileNotFoundError: [Errno 2] No such file or directory: '.../scripts/transitops.py'
exit: 1
```

The focused test failed because the Task 2 module did not exist, as expected.
Subsequent vertical slices were also witnessed failing for missing path
rejection, byte accounting, cap refusal, locking, campaign status, and CLI
boundary behavior before their minimal implementations were added.

### Witnessed GREEN

```text
$ .venv/bin/python -m unittest tests.test_transitops -v
test_campaign_starts_active_stops_at_28_days_and_can_pause ... ok
test_cli_requires_runtime_boundary_without_cap_override ... ok
test_lock_is_nonfollowing_private_and_nonblocking ... ok
test_lock_rejects_symlink_without_touching_target ... ok
test_accepts_distinct_descendants_of_canonical_runtime_root ... ok
test_rejects_non_descendants_equal_paths_and_symlink_traversal ... ok
test_rejects_symlink_runtime_root ... ok
test_atomic_write_refuses_projected_cap_without_partial_target ... ok
test_atomic_write_rejects_symlink_escape ... ok
test_atomic_write_replaces_target_under_cap ... ok
test_counts_only_regular_files_without_following_symlinks ... ok

Ran 11 tests in 0.043s

OK
```

### Full verification

```text
$ .venv/bin/python -m unittest discover -s tests -v
test_fetch_emits_aggregate_status_without_retaining_payload ... ok
test_invalid_argument_emits_json_error ... ok
test_second_run_is_blocked_while_lock_is_held ... ok
test_symlink_lock_does_not_truncate_target ... ok
test_trickling_response_hits_wall_clock_deadline ... ok
test_campaign_starts_active_stops_at_28_days_and_can_pause ... ok
test_cli_requires_runtime_boundary_without_cap_override ... ok
test_lock_is_nonfollowing_private_and_nonblocking ... ok
test_lock_rejects_symlink_without_touching_target ... ok
test_accepts_distinct_descendants_of_canonical_runtime_root ... ok
test_rejects_non_descendants_equal_paths_and_symlink_traversal ... ok
test_rejects_symlink_runtime_root ... ok
test_atomic_write_refuses_projected_cap_without_partial_target ... ok
test_atomic_write_rejects_symlink_escape ... ok
test_atomic_write_replaces_target_under_cap ... ok
test_counts_only_regular_files_without_following_symlinks ... ok

Ran 16 tests in 1.051s

OK

$ .venv/bin/python -m py_compile scripts/transitops.py tests/test_transitops.py
exit: 0 (no output)

$ git diff --check
exit: 0 (no output)

$ git status --short --ignored
?? docs/harness/stages/02-ingestion-storage.md
?? requirements-stage2.txt
?? scripts/transitops.py
?? tests/test_transitops.py
!! .venv/
!! scripts/__pycache__/
!! tests/__pycache__/
```

No runtime data was created or tracked. This task did not fetch transit data,
install cron, run Airflow, implement later ingestion stages, commit, or push.

### Corrections after first review

Two acceptance gaps remained after the first review pass and were closed with
separate vertical RED→GREEN slices.

1. **Trust boundary before I/O.** Added `validate_trust_boundary(scheduler,
   data_origin, namespace)`: rejects a real data origin outside the
   `production` namespace and rejects `airflow` with a real origin; returns the
   validated triple otherwise.
2. **CLI contract.** Renamed `--data-root` to `--root` and added required
   `--scheduler`, `--data-origin`, and `--namespace` flags. The boundary is
   validated before `validate_runtime_paths`, the first filesystem access.

Witnessed RED (focused):

```text
$ .venv/bin/python -m unittest tests.test_transitops.TrustBoundaryTest -v
AttributeError: module 'transitops' has no attribute 'validate_trust_boundary'
FAILED (errors=4)

$ .venv/bin/python -m unittest tests.test_transitops.CampaignTest.test_cli_uses_root_and_trust_boundary_flags -v
AssertionError: '--root' not found in 'usage: transitops.py [-h] --runtime-root ... [--data-root DATA_ROOT] ...'
FAILED (failures=1)
```

Witnessed GREEN (focused), then the full suite:

```text
$ .venv/bin/python -m unittest tests.test_transitops.TrustBoundaryTest -v
OK

$ .venv/bin/python -m unittest tests.test_transitops.CampaignTest.test_cli_uses_root_and_trust_boundary_flags -v
OK

$ .venv/bin/python -m unittest discover -s tests -v
Ran 20 tests in 1.086s
OK

$ .venv/bin/python -m py_compile scripts/transitops.py tests/test_transitops.py
exit: 0
```

End-to-end CLI smoke:

```text
$ .venv/bin/python scripts/transitops.py --runtime-root <tmp> --scheduler cron \
    --data-origin real --namespace production --campaign-start 2026-09-01T00:00:00Z
{"runtime_root": "<tmp>", "data_root": "<tmp>/data", "state_root": "<tmp>/state",
 "scheduler": "cron", "data_origin": "real", "namespace": "production", "campaign": "active"}
exit: 0

$ .venv/bin/python scripts/transitops.py --runtime-root <tmp> --scheduler airflow \
    --data-origin real --namespace production --campaign-start 2026-09-01T00:00:00Z
ValueError: airflow may not collect real data
exit: 1

$ .venv/bin/python scripts/transitops.py --runtime-root <tmp> --scheduler cron \
    --data-origin real --namespace demo --campaign-start 2026-09-01T00:00:00Z
ValueError: real data origin requires the production namespace
exit: 1
```

The invalid invocations rejected before any `data/` or `state/` path was created.

### Task 3: static GTFS ingestion

**Status:** implementation complete locally; production VBB fetch and pilot remain deferred.

Implemented and tested with synthetic local HTTP feeds:

- bounded download with a total wall-clock deadline and response-size limit;
- required GTFS files and headers, including `calendar.txt`;
- safe ZIP member validation and quarantine on invalid archives;
- route-type filtering for tram, subway, and rail (`0`, `1`, `2`);
- hash-versioned activation metadata and daily run records;
- unchanged-feed idempotency;
- referenced-version archival and unreferenced-version removal;
- whole-data-root storage-cap accounting;
- streaming extraction of `stop_times.txt`.

Task 3 RED→GREEN checks included missing fixture, non-streamed `stop_times.txt`,
unchanged rerun, invalid/missing files, traversal, version lifecycle, total
deadline, and cross-directory storage-cap behavior.

Final verification:

```text
$ .venv/bin/python -m unittest discover -s tests -v
Ran 31 tests in 6.715s
OK

$ .venv/bin/python -m py_compile scripts/transitops.py tests/test_transitops.py
exit: 0

$ git diff --check
exit: 0
```

The committed synthetic fixture is `tests/fixtures/static.zip` (1,053 bytes),
explicitly unignored despite the general `*.zip` runtime rule. No production
data was fetched, cron was installed, Airflow was run, or commit/push was done.

## Task 4 checkpoint: realtime normalization

**Status:** partial implementation checkpoint; realtime collection is not yet complete.

Completed TDD slices:

- committed 74-byte synthetic `tests/fixtures/realtime.pb`;
- protobuf parsing and separate arrival/departure normalization;
- date-partitioned Parquet slot writing;
- repeated-slot idempotency;
- 15-minute stale and 5-minute future freshness bounds;
- malformed payload rejection before Parquet output.

Focused and regression verification currently passes alongside the existing
suite. Remaining Task 4 work is the integrated collector path: HTTP fetch,
quarantine/failure records for stale or malformed live payloads, complete
normalized schema fields, unchanged-payload metrics, and atomic success-record
commit.

### Task 4 continuation checkpoint

Added a synthetic realtime fixture and verified the first integrated collector
slice. `collect_realtime_slot()` now fetches a bounded protobuf response, writes
the slot raw payload under `raw/realtime/YYYY-MM-DD/HH-MM.pb`, and delegates to
the normalized Parquet writer. The collector forwards an explicit observation
time so the 15-minute stale and 5-minute future checks apply to the integrated
path. Repeated Parquet writes remain idempotent.

Focused RED→GREEN checks covered the missing collector, stale collector input,
and missing realtime fixture. The full suite currently passes with 43 tests.
This remains a checkpoint, not a completed Task 4 gate: quarantine/failure
records, full schema fields, and atomic success records still need implementation.

The collector continuation now also quarantines stale and malformed payloads,
writes slot-specific failed records, and counts repeated payloads in
`state/metrics/production.json`. The full suite currently passes with 45 tests.
The schema continuation now supplies all planned normalized fields, including
static version, trip start values, schedule relationship, delay, and explicit
scheduled/predicted event columns. Focused and full verification currently
passes with 47 tests. Remaining Task 4 work is a broader production-shaped
collector/CLI integration check before closing the gate.

The collector and direct writer now enforce fixed UTC 15-minute slot alignment (`00`, `15`, `30`, `45`). Misaligned slots fail before filesystem access. Focused RED→GREEN checks and the full 50-test suite pass.

The normalized Parquet writer now uses the exact planned column order and
explicit PyArrow types, including `int32` for `stop_sequence` and
`delay_seconds`. Focused schema RED→GREEN verification and the full 48-test
suite pass. No production collection has started.

### Task 4 CLI checkpoint

Added the `realtime` CLI command with explicit runtime, scheduler, origin,
namespace, slot, URL, and deterministic `--now` controls. It emits one JSON
result and returns success for `success` or `already_complete`; failed slot
validation returns a nonzero status. A production-shaped synthetic invocation
now fetches the fixture through the CLI and produces the expected raw and
Parquet outputs.

Verification: focused CLI test and the full suite pass with 48 tests; Python
compilation and `git diff --check` pass. Production URLs and live collection
remain unused.

## Task 5 checkpoint: retention and compaction

Implemented the first Task 5 slices:

- remove raw and quarantine files older than 48 hours using UTC timestamps
  encoded in their slot paths;
- compact completed UTC-day slot Parquet files into `observations.parquet`,
  verify row count/schema after reopening, then remove source slot files;
- leave the current day untouched and keep retention limited to raw/quarantine.

Focused RED→GREEN tests and the full suite pass with 52 tests. No production
data, cron, Airflow, commit, or push occurred.

## Task 7 checkpoint: cron installer

Added `scripts/install_cron.sh`, which preserves unrelated crontab entries,
replaces only its marker-delimited block, supports `--dry-run`, and schedules
realtime, static, and maintenance commands with `flock`. The installer test,
full 56-test suite, shell syntax check, Python compilation, and `git diff --check`
pass. The real user crontab has not been modified.

## Task 8 checkpoint: isolated synthetic Airflow demo

Added `compose.yaml`, `airflow/Dockerfile`, and
`airflow/dags/transitops_demo.py`. The demo uses synthetic committed fixtures,
`/demo-data`, namespace `demo`, scheduler `airflow`, and no production mounts or
URLs. The CLI now exposes `static`, `realtime`, `maintain`, and `metrics`
commands required by the demo and cron paths.

Verification passed: Airflow isolation test, `docker compose config`, Python
compilation, shell syntax check, and the full 57-test suite. The Airflow demo
was not started on this VPS because Stage 1 invalidated Airflow as a production
runtime here; it remains a learning artifact for a suitable separate host.

## Task 9 preflight checkpoint

The production preflight and bounded pilot are complete. The installer remains the
only file authorized to change the user crontab and supports `--dry-run`.

### Final checklist

- [x] Tasks 1-8 local artifacts and tests
- [x] Confirm current production VBB static URL and route-type mapping
- [x] Install and read back marked cron block
- [x] Run one manual real static/realtime smoke
- [x] Start and record the 24-hour pilot
- [ ] Close Stage 2 gate and request review

### Final pilot result

The bounded real-data pilot ran from `2026-09-08T07:15:00Z` through
`2026-09-09T07:15:00Z`. Final metrics, filtered to that interval, were:

- 96 expected slots; 96 attempted; 96 successful; 0 stale; 0 failed
- slot coverage: `1.0`
- entity completeness: `15,414,887` normalized rows
- counted collection storage at stop: `2,032,607,918` bytes
- latest observed snapshot: `167,628` rows with modes `rail`, `subway`, `tram`
  and zero null modes
- cron marker removed after the pilot and read back as absent

The earlier September 2 and September 7 smoke records remain local runtime
history only and are not campaign evidence.

### Metrics correction

`build_metrics()` now filters run records to the requested half-open UTC
interval `[start, end)`. A regression test proves historical records do not
inflate attempted slots, successful slots, or entity completeness.

### Campaign status

The 24-hour storage pilot passed, but the plan's minimum usable campaign
requires 14 elapsed days at 90% successful slot coverage. Cron was resumed on
`2026-09-09T09:16:35Z` from the corrected absolute-runtime installer. The first
resumed slot succeeded with `133,504` normalized rows. Continue collection for
13 more elapsed days unless the 4 GiB collection-file cap pauses it first.

### Gate disposition

Implementation and storage-pilot evidence are complete. Stage 2 remains open
until the 14-day campaign reaches its acceptance window and the final
correctness/security/complexity review is recorded. No runtime data or state is
eligible for Git.

No commit or push has occurred.


## Task 6 checkpoint: coverage and storage metrics

Added deterministic `build_metrics()` coverage for expected, attempted, successful,
stale, and unchanged slots, with slot coverage kept separate from entity row
completeness. Counted bytes are limited to raw, quarantine, static, and Parquet
trees. Focused metrics and CLI-label integration tests pass; the full suite now
passes with 53 tests. No production data, cron, Airflow, commit, or push occurred.
