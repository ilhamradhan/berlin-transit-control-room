# TransitOps Berlin

> A learning project about data engineering and working effectively with an AI coding agent.

**Current state:** the design is documented, but the pipeline and app do not exist yet.

I am building TransitOps Berlin to learn two things together:

1. how to build a small data platform with Airflow, dbt, DuckDB, Parquet, and Streamlit;
2. how to direct an AI agent with clear constraints, phase gates, selected skills, and checks that prove the work is correct.

The dataset comes from VBB, Berlin-Brandenburg's public transport authority. The planned pipeline samples static GTFS and GTFS-Realtime data for Berlin U-Bahn, S-Bahn, and tram services. The app will show both transit reliability and the health of the pipeline that produced those numbers.

## What I plan to build

The app has four pages:

- **Control Room:** source freshness, collection coverage, Airflow and dbt runs, test results, incidents, and the age of the current data release.
- **Incident Detail:** evidence for a failure, the relevant runbook, one safe recovery control, and a separate verification step.
- **Transit Reliability:** predicted-delay and coverage metrics by route, mode, stop, and time.
- **System Documentation:** architecture, source contracts, metric definitions, limitations, and runbooks.

A small RAG assistant will answer operational questions from approved project documentation. It will cite its sources and stay read-only. Recovery actions remain ordinary application controls, not LLM tool calls.

## Data collection limits

| Setting | Decision |
|---|---|
| Realtime interval | 15 minutes |
| Minimum useful run | 14 elapsed days with at least 90% successful collection slots |
| Hard stop | 28 calendar days or 4 GB of collected data, whichever comes first |
| Raw payload retention | 48 hours, including invalid or quarantined payloads |
| Static GTFS | Check daily; keep each compressed version referenced by retained observations |
| Initial storage | Local Parquet and DuckDB |

The 4 GB limit covers raw, quarantined, static, and Parquet collection files. A useful sanitized failure sample can move into the small test fixtures; the original payload still expires.

These are samples of realtime predictions, not measured passenger arrival times. Low-coverage periods will be marked, and the analysis will not claim that one factor caused a delay.

## Planned stack

| Job | Tool |
|---|---|
| Scheduling | Apache Airflow |
| SQL models and tests | dbt Core |
| Files and analytics | Parquet and DuckDB |
| Incident state | SQLite |
| App | Streamlit |
| Retrieval | LanceDB with local embeddings |
| Answer generation | Gemini 2.5 Flash-Lite |

## How the agent work is documented

I make the product and architecture decisions. Hermes Agent helps with research, planning, implementation, documentation, and verification. The repository keeps a short record for each stage: my intent, the agent's rephrased prompt, skills actually used, acceptance criteria, commands run, results, and deviations.

This is curated evidence, not a raw chat export. See [`HARNESS.md`](HARNESS.md), [`PROMPT.md`](PROMPT.md), and [`SKILLS.md`](SKILLS.md).

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md): system boundaries and data flow
- [`PLAN.md`](PLAN.md): six implementation stages
- [`SETUP.md`](SETUP.md): VPS constraints and the first Airflow spike
- [`EVALUATION.md`](EVALUATION.md): acceptance tests
- [`DECISIONS.md`](DECISIONS.md): accepted tradeoffs
- [`DEPLOY.md`](DEPLOY.md): private runtime and public case-study plan
- [`RUNBOOKS.md`](RUNBOOKS.md): planned incident procedures
- [`docs/harness/stages/`](docs/harness/stages/): curated stage records

## License and data attribution

Project code, documentation, and synthetic fixtures use the MIT license. The repository excludes the collected transit archive, databases, model files, vector indexes, secrets, and raw logs.

Transit data is provided by **VBB Verkehrsverbund Berlin-Brandenburg GmbH** under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Sources: [VBB datasets](https://unternehmen.vbb.de/en/digital-services/datasets/) and [VBB GTFS-Realtime](https://production.gtfsrt.vbb.de/). This project samples, filters, and transforms the source data into derived metrics. VBB does not endorse this project.
