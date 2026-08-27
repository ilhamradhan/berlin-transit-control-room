# TransitOps Berlin

> A harness-engineered data reliability platform for sampled Berlin public-transport predictions.

**Status:** requirements baseline complete; implementation has not started.

TransitOps Berlin is a learning and portfolio project demonstrating my ability to harness an AI agent to design, build, verify, and document a data-engineering system. It combines a Berlin transit reliability explorer with a pipeline Control Room for detecting, diagnosing, recovering from, and verifying data failures.

## What this project demonstrates

### Data engineering

- VBB static GTFS and GTFS-Realtime ingestion
- Fifteen-minute bounded collection orchestrated by Apache Airflow
- Temporary raw protobuf retention and compacted Parquet history
- dbt transformations and tests executed against DuckDB
- Versioned, test-gated DuckDB releases
- Pipeline freshness, coverage, quality, and publication monitoring
- Controlled failure simulation and deterministic recovery

### Harness engineering

- Requirements grilling before implementation
- Explicit constraints and decisions
- User intent preserved alongside a reusable rephrased prompt
- Phase gates with observable acceptance criteria
- Skills selected for specific phases rather than loaded indiscriminately
- Curated execution and verification records
- Human ownership of product and architecture decisions
- AI-assisted research, implementation, documentation, and verification

## Product journey

> **Detect → diagnose → retrieve grounded guidance → recover → verify**

The primary product persona is a data engineer operating the Berlin transit pipeline. The real portfolio audience is hiring managers and technical reviewers.

## Planned application

1. **Control Room** — freshness, collection coverage, Airflow/dbt runs, tests, mart age, incidents, and recovery history.
2. **Incident Detail** — evidence, citations, allowlisted recovery controls, and deterministic verification.
3. **Transit Reliability** — sampled predicted-delay metrics by route, mode, stop, and time.
4. **System Documentation** — architecture, source contracts, metrics, limitations, and runbooks.

The embedded RAG assistant is read-only. It explains approved project evidence with citations; it cannot execute commands or change pipeline state.

## Core stack

| Layer | Planned technology |
|---|---|
| Orchestration | Apache Airflow |
| Transformation | dbt Core with explicit CLI tasks |
| Analytical storage | Parquet and versioned DuckDB releases |
| Control-plane state | SQLite in WAL mode |
| Application | Streamlit |
| Retrieval | LanceDB with a compact local embedding model |
| Answer generation | Gemini 2.5 Flash-Lite with sanitized context |
| Runtime | Lightweight Docker deployment on a resource-constrained VPS |

## Collection methodology

- Modes: Berlin U-Bahn, S-Bahn, and tram
- Realtime cadence: every 15 minutes
- Minimum campaign: 14 elapsed days with at least 90% successful collection slots
- Hard stop: 28 calendar days or 4 GB of collected project data, whichever occurs first
- Raw realtime retention: 48 hours after successful parsing and validation
- Static GTFS: checked daily; only changed, validated versions are stored
- Weather enrichment: out of version-one scope

The resulting metrics describe **observed realtime predictions**, not verified passenger arrival measurements. The project will not make causal claims.

## Harness records

Curated stage records live in [`docs/harness/stages/`](docs/harness/stages/). Each record preserves:

- User intent
- Rephrased execution prompt
- Assumptions and constraints
- Skills actually used
- Acceptance criteria
- Execution summary
- Verification evidence
- Deviations and lessons

Raw chat transcripts, secrets, and unfiltered logs are not published.

## Documentation

| Document | Purpose |
|---|---|
| [`HARNESS.md`](HARNESS.md) | Phase-gated agent and delivery harness |
| [`PROMPT.md`](PROMPT.md) | Original intent and reusable rephrased prompt |
| [`SKILLS.md`](SKILLS.md) | Actual and planned skill usage by phase |
| [`SETUP.md`](SETUP.md) | Environment constraints and planned setup |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Components, data flow, storage lifecycle, and safety boundaries |
| [`PLAN.md`](PLAN.md) | Six-stage implementation plan and gates |
| [`DEPLOY.md`](DEPLOY.md) | Planned local/VPS and portfolio deployment |
| [`EVALUATION.md`](EVALUATION.md) | Pipeline, failure, dashboard, and RAG acceptance checks |
| [`DECISIONS.md`](DECISIONS.md) | Accepted decisions and tradeoffs |
| [`RUNBOOKS.md`](RUNBOOKS.md) | Planned operational runbook index |

## Publication policy

The repository is public under the MIT license. It excludes real collected transit archives, DuckDB databases, Parquet history, raw protobuf files, embedding indexes, model files, secrets, and unfiltered logs. Tiny synthetic fixtures will be added for reproducible tests.

VBB remains the owner and provider of its source data. VBB open data must be attributed and used according to its published terms, including CC BY 4.0 where applicable. See [VBB Open Data](https://www.vbb.de/vbb-services/api-open-data/datasets/).
