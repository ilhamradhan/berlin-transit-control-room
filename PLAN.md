# TransitOps Berlin Implementation Plan

**Goal:** Build a verified Berlin transit data reliability platform while preserving reproducible evidence of harnessing an AI agent.

**Approach:** Deliver six runnable stage increments. Every stage begins with a self-contained execution prompt and ends only after acceptance evidence and review. Implementation details and exact versions are refined at the start of the relevant stage rather than guessed in advance.

## Stage 1 — Harness and source validation

**Deliverables**

- Repository and documentation baseline
- Pinned environment proposal
- Lightweight Airflow resource spike
- Non-destructive preflight
- Verified static and realtime source samples
- Source contracts and domain glossary
- Dark HTML/SVG architecture diagram
- Stage record

**Gate**

- Existing VPS services remain healthy.
- Sample DAG completes.
- Idle/active memory and disk projections are recorded.
- Source formats and failure behavior are verified.
- No secret or dataset is committed.

**Suggested skills:** `domain-modeling` if terminology remains ambiguous; `plan` for the executable Stage 1 task plan; `systematic-debugging` only if the spike fails unexpectedly; `architecture-diagram` for the accepted dark diagram.

## Stage 2 — Ingestion and storage

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
- Raw cleanup preserves required incident evidence.
- Projected collection remains below the 4 GB cap or collection pauses safely.

**Suggested skills:** `test-driven-development`; `systematic-debugging` only for unexplained failures; `requesting-code-review` at the gate.

## Stage 3 — Transformation and quality

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
- Streamlit can read the current release while a candidate builds.
- Current and previous releases are retained; older releases are removed.

## Stage 4 — Control Room

**Deliverables**

- SQLite control-plane schema in WAL mode
- Control Room and Incident Detail pages
- Three isolated synthetic failure scenarios
- Three allowlisted recovery actions
- Deterministic recovery verification and audit history

**Gate**

- Each scenario is detected by the real pipeline path.
- Healthy collected data remains unchanged.
- No arbitrary command execution is possible.
- Browser QA proves Detect → diagnose → recover → verify.

**Suggested skills:** `test-driven-development`, `requesting-code-review`, then `dogfood` once runnable.

## Stage 5 — RAG operations assistant

**Deliverables**

- Approved corpus and sanitizer
- Compact embedding-model spike
- LanceDB index
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

## Stage 6 — Portfolio presentation

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
- Use skills by need, not by checklist.
- Code behavior uses test-first development where practical.
- Every external state change is read back.
- No push occurs unless explicitly requested; repository creation and initial push are explicitly authorized in this session.
- Weather, cloud storage, local generation models, and arbitrary recovery controls are out of scope.
