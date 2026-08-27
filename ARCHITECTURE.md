# Architecture

**Status:** accepted target architecture; implementation is pending.

## System flow

```text
VBB static GTFS (daily change check) ───────────────┐
                                                    ├─ Airflow ingestion and validation
VBB GTFS-Realtime (every 15 minutes) ──────────────┘
                         │
             raw protobuf, 48-hour retention
                         │
              parse, filter, validate, compact
                         │
            date-partitioned Parquet observations
                         │
                 dbt CLI executed by Airflow
                         │
              candidate DuckDB release + tests
                         │ success only
                 atomic current.json publication
                         │
          Streamlit reads current verified release
```

A separate SQLite control-plane database stores incidents, acknowledgements, approved demo actions, outcomes, and post-action health checks.

## Analytical data model boundaries

The historical observation layer stores only fields required by the product, including collection time, trip/route/stop identifiers, scheduled and predicted event times, delay, schedule relationship, and static-feed version. Descriptive GTFS data is normalized rather than copied into every observation.

Metrics are calculated deterministically by dbt and DuckDB. The RAG assistant does not calculate or override metrics.

## Versioned publication

1. dbt builds a candidate DuckDB file.
2. Tests run against the candidate.
3. The writer checkpoints and closes the file.
4. An independent process reopens it read-only and checks the expected marts.
5. Failed candidates never replace the current healthy release.
6. A temporary manifest is written beside the current manifest and replaced atomically on the same filesystem.
7. Streamlit opens the manifest’s verified release read-only.
8. Current and previous releases are retained; cleanup waits until older releases have no active readers.

This avoids unsafe concurrent writes and provides simple rollback and publication-age measurement.

## Application pages

- **Control Room:** overall state, source freshness, collection coverage, Airflow/dbt outcomes, quality tests, schedule match rate, mart age, incidents, and latest verified recovery.
- **Incident Detail:** diagnostic evidence, cited guidance, recovery control, and verification state.
- **Transit Reliability:** median and P90 predicted delay, on-time observation rate (≤5 minutes late), severe-delay rate (>15 minutes late), source-provided cancellation rate, realtime coverage, matching rate, and route/mode/time breakdowns.
- **System Documentation:** architecture, source contracts, metric definitions, limitations, and runbooks.

Reliability filters include date range, transport mode, route, stop, weekday, and hour range.

## Controlled failures

Demo mode isolates synthetic fixtures and incidents from real collection:

1. Stale or unavailable realtime source
2. Static/realtime schedule mismatch
3. dbt quality-test failure blocking publication

Only the corresponding demo controls are executable. They do not guarantee recovery from an external outage, and the assistant cannot trigger them.

## RAG boundary

```text
Approved Markdown and generated metadata
             │ sanitize before indexing/context assembly
             ▼
Compact local embeddings + LanceDB
             │ retrieve top supporting passages
             ├── sanitized structured incident context
             ▼
Gemini 2.5 Flash-Lite
             │
Cited read-only explanation or explicit insufficiency
```

Allowed context: sanitized project documentation, dbt/Airflow metadata, and redacted error summaries.

Forbidden context: secrets, environment variables, connection strings, unfiltered logs, unrestricted filesystem contents, or arbitrary commands.

## Storage lifecycle

- Raw and quarantined payloads: 48 hours; sanitized failures may become small test fixtures
- Static GTFS: every compressed version referenced by retained observations
- Parquet observations: bounded campaign history
- DuckDB: current and previous verified release
- Collection-file hard cap: 4 GB across raw, quarantine, static, and Parquet
- RAG total target: below 1 GB
- Campaign hard stop: 28 calendar days or 4 GB, whichever comes first

Cloud object storage, Supabase, MotherDuck, and BigQuery are outside version one. Cloud storage may be reconsidered only after measured local growth justifies it.
