# TransitOps Berlin implementation plan

**Goal:** Build a verified Berlin transit data reliability platform while preserving reproducible evidence of harnessing an AI agent.

**Approach:** Deliver six runnable stage increments. Every stage begins with a self-contained execution prompt and ends only after acceptance evidence and review. Implementation details and exact versions are refined at the start of the relevant stage rather than guessed in advance.

## Stage 1: Harness and source validation

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
- Sample DAG completes.
- Idle/active memory and disk projections are recorded.
- Source formats and failure behavior are verified.
- The REST comparison records whether stop, line, and trip identifiers map to GTFS; it does not alter official collection-slot success or provide an automatic fallback.
- Any Stage 1 code was produced with `ponytail:ponytail` active at `full`, includes the smallest runnable check required by the guardrail, and passes a separate complexity review before Stage 2 begins.
- No secret or dataset is committed.

**Suggested skills:** `plan` for the executable Stage 1 task plan; `spike` for the disposable Airflow resource and REST comparison experiments; `domain-modeling` if terminology remains ambiguous; `systematic-debugging` only if a spike fails unexpectedly; `architecture-diagram` for the accepted dark diagram.

## Stage 2: Ingestion and storage

**Deliverables**

- Fifteen-minute realtime DAG
- Daily static GTFS change check
- Parsing and Berlin mode filtering
- Raw retention and quarantine policy
- Date-partitioned Parquet writing and daily compaction
- Coverage and storage-budget metrics
- 24-hour storage pilot

**Gate**

- Synthetic tests pass before live collection.
- Duplicate/idempotent runs do not duplicate observations.
- Raw and quarantined payloads expire after 48 hours; only sanitized test fixtures persist.
- A slot succeeds only after protobuf parsing, freshness validation, and normalized-output commit; unchanged payloads and entity completeness are separate metrics.
- Before each write, projected counted storage is checked and collection pauses instead of exceeding 4 GB.

**Suggested skills:** `test-driven-development`; `systematic-debugging` only for unexplained failures; `requesting-code-review` at the gate.

## Stage 3: Transformation and quality

**Deliverables**

- dbt staging, intermediate, and mart layers
- Source, schema, relationship, and business-rule tests
- Reliability and coverage metrics
- Explicit dbt CLI Airflow tasks
- Candidate DuckDB build, test gate, atomic publication, and rollback retention
- dbt artifact parsing for operational status

**Gate**

- Known fixtures produce expected metrics.
- Failed tests block publication.
- The writer checkpoints and closes the candidate before an independent read-only reopen check.
- The manifest is replaced atomically on the same filesystem.
- Streamlit can read the current release while a candidate builds.
- Current and previous releases are retained; cleanup waits until older releases have no active readers.

## Stage 4: Control Room

**Deliverables**

- SQLite control-plane schema in WAL mode
- Control Room and Incident Detail pages
- Three isolated synthetic failure scenarios
- Three approved demo reset/retry controls
- Post-action health checks and audit history

**Gate**

- Each scenario is detected by the real pipeline path.
- Healthy collected data remains unchanged.
- No arbitrary command execution is possible.
- Browser QA proves that an operator can inspect evidence, open cited guidance, run the approved demo control, and see the post-action health check.

**Suggested skills:** `test-driven-development`, `requesting-code-review`, then `dogfood` once runnable.

## Stage 5: RAG operations assistant

**Deliverables**

- Approved corpus and sanitizer
- Compact embedding-model spike
- LanceDB index
- Verified and pinned Gemini model ID at the start of Stage 5
- Retrieval with source/section metadata
- Gemini answer contract with citations and insufficiency behavior
- Formal evaluation dataset

**Gate**

- Expected documents are retrieved for known questions.
- Citations support generated claims.
- Unsupported questions are refused or qualified.
- The assistant never claims to have executed recovery.
- Excluded operational information is not exposed.
- Installed model, corpus, and index stay below 1 GB.

## Stage 6: Portfolio presentation

**Deliverables**

- Transit Reliability explorer
- System Documentation page
- Completed dark architecture diagram
- Browser QA and screenshots
- Recorded real application demonstration
- Branded public case study planned for `ilrama.com/p/transitops-berlin`
- Final curated harness records and AI collaboration disclosure

**Gate**

- All four pages are navigable and free of visible errors.
- Metrics have nearby definitions and coverage caveats.
- Demo follows the complete operational journey.
- Public materials contain no secrets or real collected archive.

## Cross-stage rules

- One stage in progress at a time.
- Kanban task dependencies mirror stage gates; a downstream stage stays blocked until its parent gate is done.
- `ponytail:ponytail` at `full` is required before planning, writing, refactoring, debugging, or reviewing code.
- Use skills by need, not by checklist.
- Code behavior uses test-first development where practical.
- Every external state change is read back.
- No push occurs unless explicitly requested; repository creation and initial push are explicitly authorized in this session.
- Weather, cloud storage, local generation models, and arbitrary recovery controls are out of scope.
