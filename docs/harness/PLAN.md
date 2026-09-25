# TransitOps Berlin implementation plan

**Goal:** Build a verified Berlin transit data reliability platform while preserving reproducible evidence of harnessing an AI agent.

**Approach:** Deliver five runnable stage increments. Every stage begins with a self-contained execution prompt and ends only after acceptance evidence and review. Implementation details and exact versions are refined at the start of the relevant stage rather than guessed in advance.

## Stage 1: Harness and source validation

**Status:** passed. Airflow's failed VPS spike established the accepted trust boundary, the cron production-readiness checks pass, and independent correctness, security, evidence, complexity, and architecture reviews found no remaining blockers.

**Deliverables**

- Repository and documentation baseline
- Pinned environment proposal
- Lightweight Airflow resource spike
- Non-destructive preflight
- Verified static and realtime source samples
- Captured VBB feed-status or Atom notice alongside source samples
- Bounded `v6.vbb.transport.rest` comparison spike with an identifier, coverage, and data-use verdict
- Source contracts and domain glossary
- Dark HTML/SVG architecture diagram
- Stage record

**Gate**

- Existing VPS services remain healthy.
- One cron-triggered real-source smoke run completes without overlapping another run.
- Idle/active memory and disk projections are recorded.
- Source formats and failure behavior are verified.
- The REST comparison records whether stop, line, and trip identifiers map to GTFS; it does not alter official collection-slot success or provide an automatic fallback.
- Any Stage 1 code was produced with `ponytail:ponytail` active at `full`, includes the smallest runnable check required by the guardrail, and passes a separate complexity review before Stage 2 begins.
- No secret or dataset is committed.

**Suggested skills:** `plan` for the executable Stage 1 task plan; `spike` for the disposable Airflow resource and REST comparison experiments; `domain-modeling` if terminology remains ambiguous; `systematic-debugging` only if a spike fails unexpectedly; `architecture-diagram` for the accepted dark diagram.

**Next action:** plan Stage 2 from the accepted Stage 1 records. Do not repeat the Airflow feasibility spike; the Dockerized Airflow demo belongs to Stage 2 and does not count as production evidence.

## Stage 2: Ingestion and storage

**Status:** passed with a bounded seven-day campaign and documented storage constraint.

**Campaign decision:** the minimum usable campaign is seven elapsed days with
at least 90% successful collection slots. The 4 GiB storage cap remains the
hard stop. Decision D-034 records the storage-driven change from the original
14-day baseline.

**Status:** closed with the accepted seven-day campaign. Stage 3 is complete
and merged to `main` at `926e674`.

**Deliverables**

- Fifteen-minute realtime cron job
- Daily static GTFS cron job
- Shared idempotent pipeline commands used by both schedulers
- Dockerized Airflow demo DAGs using synthetic fixtures and isolated demo state
- Parsing and Berlin mode filtering
- Raw retention and quarantine policy
- Date-partitioned Parquet writing and daily compaction
- Coverage and storage-budget metrics
- 24-hour storage pilot

**Gate**

- Synthetic tests pass before live collection.
- Duplicate/idempotent runs do not duplicate observations.
- Airflow demo runs cannot read or write production collection paths.
- Stage evidence labels scheduler, data origin, and namespace according to the canonical [scheduler and data trust boundary](ARCHITECTURE.md#scheduler-and-data-trust-boundary).
- Raw and quarantined payloads expire after 48 hours; only sanitized test fixtures persist.
- A slot succeeds only after protobuf parsing, freshness validation, and normalized-output commit; unchanged payloads and entity completeness are separate metrics.
- Before each write, projected counted storage is checked and collection pauses instead of exceeding 4 GB.

**Suggested skills:** `test-driven-development`; `systematic-debugging` only for unexplained failures; `requesting-code-review` at the gate.

## Stage 3: Transformation and quality

**Status:** passed and merged at `926e674`; production collection remains stopped.

**Deliverables**

- dbt staging, intermediate, and mart layers
- Source, schema, relationship, and business-rule tests
- Reliability and coverage metrics
- Explicit dbt CLI commands called by the production release job and Airflow demo tasks
- Candidate DuckDB build, test gate, atomic publication, and rollback retention
- dbt artifact parsing for operational status

**Gate**

- Known fixtures produce expected metrics.
- Failed tests block publication.
- The writer checkpoints and closes the candidate before an independent read-only reopen check.
- The manifest is replaced atomically on the same filesystem.
- The public-artifact build can read the current verified release while a candidate builds.
- Current and previous releases are retained; cleanup waits until older releases have no active readers.

## Stage 4: Static public product and bounded RAG

**Deliverables**

- Static **Transit Reliability** page using compact, sanitized aggregates from the accepted seven-day campaign.
- Static **System Documentation** page with architecture, source contracts, metric definitions, limitations, and coverage caveats.
- Public aggregates limited to mode/route/day; no stop-level, event-level, trip-level, raw, or private operational data.
- Existing Stage 3 metrics only: median/P90 predicted delay, on-time rate, severe-delay rate, cancellation rate, realtime coverage, and schedule-match rate.
- Build-time artifact generation from the private verified release; real campaign artifacts are not committed to Git.
- Local or bounded cited read-only RAG evaluation over approved documentation and runbook guidance.
- Cloudflare Pages/R2/Workers feasibility measurements using synthetic data only; adoption remains optional and reversible.

**Gate**

- The dashboard is static, read-only, and does not download or query the private archive.
- Public artifacts contain only the approved aggregate contract and nearby metric definitions and caveats.
- Browser QA proves both pages, navigation, metric rendering, low-coverage warnings, and absence of operational controls.
- Known RAG questions retrieve the expected document sections and cite them; unsupported questions return explicit insufficiency.
- The RAG layer cannot calculate metrics, execute commands, or claim recovery.
- Cloudflare local synthetic artifact/request-shape checks; provider-specific latency, limits, failure behavior, and rollback remain deferred without external approval.
- Collection remains stopped; no Control Room, Incident Detail, recovery control, or live dashboard is built in this stage.

**Suggested skills:** `test-driven-development`, `requesting-code-review`, then `dogfood` once runnable.

## Stage 5: Portfolio presentation

**Approach:** use the separate `design` profile for an audit-first visual and
content brief, then use the `code` profile to implement only the accepted
brief. The design profile does not write to the TransitOps worktree.

**Deliverables**

- Transit Reliability explorer
- System Documentation page
- Approved visual/content brief covering hierarchy, typography, spacing,
  responsive behavior, accessibility, and truthful product copy
- Completed dark architecture diagram
- Browser QA and screenshots
- Recorded static-product demonstration
- Branded public case study planned for `ilrama.com/p/transitops-berlin`
- Final curated harness records and AI collaboration disclosure

**Gate**

- Both public pages are navigable and free of visible errors.
- Metrics have nearby definitions and coverage caveats.
- Demo follows the finite data-to-artifact-to-dashboard journey.
- Public materials contain no secrets, raw payloads, trip/event rows, or real collected archive.

## Cross-stage rules

- One stage in progress at a time.
- Kanban task dependencies mirror stage gates; a downstream stage stays blocked until its parent gate is done.
- `ponytail:ponytail` at `full` is required before planning, writing, refactoring, debugging, or reviewing code.
- Use skills by need, not by checklist.
- Code behavior uses test-first development where practical.
- Every external state change is read back.
- No push occurs unless explicitly requested; repository creation and initial push are explicitly authorized in this session.
- Weather, recurring cloud compute, public interactive RAG, local generation models, Control Room/recovery controls, and arbitrary commands are out of scope.
- Cloudflare delivery is a measured optional path, not a Stage 4 deployment requirement.
- Scheduler and data provenance follow the canonical [trust boundary](ARCHITECTURE.md#scheduler-and-data-trust-boundary); other documents link to it instead of redefining it.
