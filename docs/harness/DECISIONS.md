# Decision record

This file summarizes accepted decisions from the requirements grill. Detailed implementation decisions will be appended as dated records.

| ID | Decision | Rationale / tradeoff |
|---|---|---|
| D-001 | Build a new project, TransitOps Berlin | Provides a greenfield orchestration and reliability exercise rather than repeating an existing Steam analytics project. |
| D-002 | Treat harness engineering as both agent and delivery harnesses | Demonstrates controlled agent work and a reproducible runtime system. |
| D-003 | Make the Pipeline Control Room the core product | Transit analytics shows that the data is useful; diagnosis and recovery are the main learning workflow. |
| D-004 | Use VBB static GTFS plus collected GTFS-Realtime | Static supplies schedule context; repeated current feeds create observation history. |
| D-005 | Scope modes to U-Bahn, S-Bahn, and tram | Keeps the first data model and dashboard focused. |
| D-006 | Collect every 15 minutes | Reduces snapshots by two-thirds versus five-minute collection while retaining route-level analytical value. |
| D-007 | Stop after 28 calendar days or 4 GB of collection files | The cap covers raw, quarantine, static, and Parquet files and prevents indefinite growth. |
| D-008 | Original baseline: require 14 days and 90% slot coverage | Historical baseline superseded by D-034 after measured storage evidence. |
| D-009 | Retain raw and quarantined payloads for 48 hours | Supports recent debugging without preserving raw source files indefinitely. |
| D-010 | Check static GTFS daily and retain referenced versions | Historical observations remain reproducible without storing unchanged duplicate downloads. |
| D-011 | Use local Parquet and DuckDB first | Preserves the learning stack and avoids premature cloud complexity. |
| D-012 | Defer R2, MotherDuck, Supabase, and BigQuery | Reconsider only after a measured storage or publication need. |
| D-013 | Use a lightweight Airflow spike | The 3.6 GiB host is below official Docker guidance; fit must be proven. |
| D-014 | Never stop unrelated services automatically | Project lifecycle must not control external production services. |
| D-015 | Execute explicit dbt CLI tasks | Transparent and smaller than Cosmos or dbt Cloud. |
| D-016 | Publish versioned DuckDB releases | Avoids concurrent-write hazards and enables test-gated atomic publication. |
| D-017 | Use separate SQLite control-plane state | Keeps operational writes out of Airflow metadata and read-only analytics releases. |
| D-018 | Use three isolated synthetic failures | Exercises real incident paths without corrupting collected history. |
| D-019 | Allow only three demo reset/retry controls | Prevents arbitrary DAG or shell execution without pretending an external outage is always recoverable. |
| D-020 | Keep the RAG assistant read-only | Natural-language interpretation is separated from authorized side effects. |
| D-021 | Use Gemini 2.5 Flash-Lite with local retrieval | Avoids a multi-gigabyte local generation model on a CPU-only low-memory VPS; Stage 5 must recheck availability and pin the exact model ID. |
| D-022 | Use LanceDB and a compact local embedding model | Provides persistent local semantic retrieval without another database service. |
| D-023 | Require formal RAG evaluation | Citations, refusals, retrieval quality, and prohibited claims must be proven. |
| D-024 | Exclude weather from version one | Avoids extra ingestion and causal-interpretation scope. |
| D-025 | Use phase-gated Hermes development | Code alone does not satisfy a stage; verification evidence is mandatory. |
| D-026 | Publish curated stage records with rephrased prompts | Reproducible evidence is useful; raw transcripts are noisy and risk sensitive disclosure. |
| D-027 | Use a dark HTML/SVG architecture diagram | Matches the selected visual preference; Excalidraw is not required. |
| D-028 | Make the repository public under MIT | Code/docs are shareable; real data and secrets remain excluded. |
| D-029 | Spike `v6.vbb.transport.rest` as an optional diagnostic source | It may add current disruption context, but it will not replace official GTFS sources, count toward collection-slot success, or become an automatic fallback. Identifier mapping and data-use terms must pass a bounded Stage 1 check. |
| D-030 | Use Ponytail at full as the implementation guardrail | Every coding task starts with the existing plugin loaded. Prefer deletion, reuse, standard-library and native features, and the shortest verified implementation without weakening validation, security, or explicit requirements. |
| D-031 | Use a project-scoped Hermes Kanban board | Durable tasks, dependencies, worktrees, and human blocks fit the phase-gated workflow. Curated stage records remain the public evidence; local board rows do not replace them. |
| D-032 | Invalidate Airflow 3.3.1 standalone on the current VPS | A corrected run peaked at 756 MiB while swap increased across all three 30-second samples. The safety stop ruled out Airflow as a production service on this host. |
| D-033 | Use cron for real collection and Dockerized Airflow for the synthetic learning demo | Both paths call shared idempotent pipeline commands. [`ARCHITECTURE.md`](ARCHITECTURE.md#scheduler-and-data-trust-boundary) defines the single canonical trust boundary. |
| D-034 | Use a seven-day minimum campaign with 90% slot coverage | Measured local storage approached the 4 GiB hard cap before 14 days; seven days preserves a bounded, useful dataset without pretending the original target was met. |

## Rejected or deferred alternatives

- Five-minute collection cadence
- Indefinite collection
- Full official Airflow example Compose stack without measurement
- Shared writable DuckDB between Airflow and Streamlit
- PostgreSQL/Supabase as the primary analytical store
- BigQuery as version-one warehouse
- Cosmos and dbt Cloud
- General VPS infrastructure observability in the main product
- Local generative model on the VPS
- Arbitrary LLM-driven recovery commands
- Complete raw Hermes transcripts in Git
