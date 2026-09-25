# Stage 4 — Static public product and bounded read-only RAG

## Status

Plan revised after the Stage 4 grill. **Implementation complete; Kanban
reconciled in `t_4511ff90`.**
Production collection remains stopped.

## Red line

Stage 4 is a finite, static public evidence product—not an operational system.
It turns the accepted seven-day campaign into compact public aggregates and a
small, locally evaluated, cited read-only RAG demonstration.

## In scope

- Static **Transit Reliability** page.
- Static **System Documentation** page.
- Existing Stage 3 metrics only: median/P90 predicted delay, on-time rate,
  severe-delay rate, cancellation rate, realtime coverage, and schedule-match
  rate.
- Public aggregate granularity: mode/route/day.
- Build-time export from the private verified DuckDB release.
- Local or CLI/demo-bound RAG over approved documentation, metric definitions,
  limitations, and cited runbook guidance.
- Local retrieval evaluation with citation checks and explicit insufficiency;
  external provider integration is deferred and not required for Stage 4.
- Cloudflare Pages/R2/Workers feasibility measurements with synthetic artifacts
  only; adoption remains optional and reversible.

## Out of scope

- Control Room and Incident Detail.
- SQLite control-plane state, recovery controls, and synthetic incident UI.
- Live or continuously updating dashboards.
- Stop-level, event-level, trip-level, raw, or private operational data in
  public artifacts.
- Public interactive RAG or browser-held provider credentials.
- VPS/Streamlit as the delivery runtime.
- Uploading the private collection archive to Cloudflare.
- Restarting collection or changing accepted Stage 3 evidence.

## Public artifact contract

The exporter reads a verified release read-only and emits compact, sanitized
artifacts containing only:

- release identifier and generated-at timestamp;
- source/campaign provenance and coverage status;
- mode/route/day aggregate rows;
- the seven accepted metric values and their definitions;
- visible low-coverage qualifications and limitations.

Artifacts must not contain raw payloads, event rows, trip identifiers, private
paths, secrets, unrestricted logs, or operational controls. Real campaign
artifacts are generated during a build and are not committed to Git.

## Execution tasks

### 1. Documentation and contract checks

Align `PLAN.md`, `EVALUATION.md`, `ARCHITECTURE.md`, `DECISIONS.md`, and this
stage record. Verify that the accepted seven-day campaign, stopped collection,
static delivery, public boundary, RAG boundary, and optional Cloudflare path
are stated consistently.

### 2. Public-artifact exporter

Write tests first for the artifact schema, provenance, metric definitions,
coverage warning, release identifier, generated-at timestamp, private-field
rejection, and deterministic sanitized output. Export only from a verified
read-only DuckDB release.

### 3. Static pages

Select the smallest existing or standard static stack. Build the two pages
against synthetic artifacts first. Add nearby metric definitions, coverage
caveats, no-causal-language safeguards, and visible handling for missing or
stale artifacts. Do not add operational controls.

### 4. Bounded RAG evaluation

Sanitize the approved corpus. Test retrieval metadata, source/section
citations, supported questions, unsupported-question insufficiency, and the
prohibition on metric calculation, command execution, recovery claims, and
unrestricted filesystem context. Keep provider configuration and credentials
outside artifacts and Git.

### 5. Cloudflare feasibility

Measure the locally reproducible synthetic artifact size and request shape.
Provider-specific limits, latency, failure behavior, and rollback/unpublish
remain deferred because no external provider or account may be contacted in
this stage. Do not upload the private archive or make Pages/R2/Workers adoption
an acceptance prerequisite.

### 6. Stage gate

Run documentation/link checks, focused and full tests, static build, browser QA,
artifact/privacy scans, RAG evaluation, Cloudflare measurements, independent
correctness/security review, and `ponytail:ponytail-review`. Record evidence in
the stage record before requesting approval.

## Acceptance gate

- Two static pages build and navigate without visible errors.
- Dashboard reads compact artifacts only and never requests the private release.
- Metrics match the verified Stage 3 release and have nearby definitions and
  coverage caveats.
- Public artifacts contain no raw, event, trip, secret, private path, or
  unrestricted operational content.
- RAG answers cite approved source sections; unsupported questions produce
  explicit insufficiency.
- RAG cannot calculate metrics, execute commands, or claim recovery.
- Local synthetic delivery shape is measured; provider-specific feasibility
  remains optional, deferred, and reversible.
- Collection remains stopped and no Control Room scope is implemented.

## Stop conditions

Stop if the dashboard requires the full archive, the public artifact boundary
cannot be enforced, the RAG provider cannot support citations and insufficiency,
Cloudflare requires unsafe or unjustified commitment, or implementation would
restart collection or alter accepted Stage 3 evidence.

## Implementation checkpoint — public artifact and static pages

Completed without restarting collection or making an external deployment:

- `scripts/export_public_artifacts.py` emits deterministic mode/route/day JSON
  from a read-only verified DuckDB release and rejects non-regular release
  paths.
- `scripts/build_static_site.py` copies only the two static pages, shared
  assets, and the sanitized public artifact.
- Synthetic tests cover the artifact schema, low-coverage warning,
  deterministic output, private-field rejection, and static build boundary.
- Browser QA loaded both pages from a local static server; navigation, summary
  metrics, aggregate table, documentation, and no-console-error behavior
  passed.

Evidence:

```text
$ .venv/bin/python -m unittest discover -s tests -q
Ran 107 tests in 101.105s — OK

$ .venv/bin/python -m py_compile scripts/export_public_artifacts.py scripts/build_static_site.py tests/test_public_artifacts.py tests/test_static_site.py
exit: 0

$ git diff --check
exit: 0
```

Additional checkpoint evidence:

- `rag/retrieval.py` sanitizes an approved corpus and returns source/section
  citations or explicit insufficiency without commands, metrics, or recovery
  behavior.
- The approved corpus and evaluation fixture cover supported documentation
  questions and an unsupported weather question.
- Native file-size/request-shape checks measured the synthetic site at 9,780
  bytes total, 1,901 artifact bytes, four dashboard-load requests, and two
  documentation-load requests; the check made no network request and uploaded
  no private archive.
- Added-scope security scan found no hardcoded credentials, shell execution,
  eval/exec, pickle deserialization, or interpolated SQL. The only shell use
  found is the pre-existing fixed-command Airflow test harness.
- Browser QA was rerun after escaping artifact values before HTML insertion;
  both pages rendered, stale data was visibly qualified, cancellation was
  visibly represented as unavailable, and the browser console reported zero
  messages/errors.
- The independent review findings were remediated: verified-manifest binding,
  strict artifact allowlisting, Berlin service-day conversion, stale-artifact
  warning, cancellation display, output-directory isolation, 75% coverage
  minimum, strict finite scalar validation, and RAG source/metadata allowlisting
  were added with focused regression tests.
- Full verification requires the Stage 3 dependency environment from
  `requirements-stage3.txt`; this run reused that environment through a
  temporary ignored `.venv` symlink, which was removed after verification.

```text
$ .venv/bin/python -m unittest discover -s tests -q
Ran 121 tests in 100.835s — OK

$ .venv/bin/python -m py_compile scripts/export_public_artifacts.py scripts/build_static_site.py rag/retrieval.py tests/test_public_artifacts.py tests/test_static_site.py tests/test_rag_retrieval.py
exit: 0
```

The Stage 4 red-line is complete and reconciled in Kanban task `t_4511ff90`. No
external provider or Cloudflare account was contacted; provider integration is
explicitly deferred beyond this red-line stage.
