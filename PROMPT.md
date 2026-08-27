# Prompt record

## User intent

Create a learning project that combines harness engineering (setup, planning, implementation, deployment, and reproducible agent use) with a data-engineering stack based on DuckDB, Airflow, and dbt. Add an AI capability only where it helps the product. Preserve the prompt, its rephrasing, skills used, decisions, setup, plan, deployment, and verification in separate Markdown files for future reference.

The selected product is a Berlin transit reliability and data-pipeline Control Room using VBB data.

## Rephrased reusable execution prompt

> Build **TransitOps Berlin**, a public portfolio and learning project that demonstrates my ability to harness an AI agent to produce a verified data-engineering system.
>
> Use VBB static GTFS and GTFS-Realtime for Berlin U-Bahn, S-Bahn, and tram. Collect realtime snapshots every 15 minutes on an always-on but resource-constrained VPS. Require at least 14 elapsed days with 90% successful collection-slot coverage. Stop automatically after 28 calendar days or 4 GB of collection files, whichever occurs first. Count raw, quarantined, static, and Parquet files toward that limit. Expire all raw and quarantined payloads after 48 hours unless a sanitized sample is deliberately promoted into the test fixtures. Compact the required observations into date-partitioned Parquet. Check static GTFS daily and retain each compressed version referenced by retained observations.
>
> Orchestrate with a measured lightweight Apache Airflow topology. Airflow must run explicit dbt CLI commands. Use dbt and DuckDB for deterministic transformations, quality tests, and reliability marts. Publish marts as versioned DuckDB database files: test a candidate, atomically update a manifest only after success, and retain the current and previous verified release. Store low-volume incident and recovery state in a separate SQLite database using WAL mode.
>
> Build a Streamlit application with Control Room, Incident Detail, Transit Reliability, and System Documentation pages. Demonstrate the journey Detect → diagnose → retrieve grounded guidance → recover → verify. Include three isolated synthetic failure scenarios: stale realtime source, static/realtime schedule mismatch, and dbt quality-test failure. Expose only three corresponding allowlisted deterministic recovery actions. Record actions and require deterministic recovery verification.
>
> Add a read-only RAG operations assistant. Index only an approved local documentation corpus with a compact local embedding model and LanceDB. Send Gemini 2.5 Flash-Lite only selected passages plus sanitized structured incident context. Never send secrets, environment variables, connection strings, or unfiltered logs. Require citations, admit insufficient evidence, and prohibit claims that the assistant executed recovery. Keep the RAG footprint below 1 GB and formally evaluate retrieval, citation support, refusals, and prohibited claims.
>
> Develop through six phase gates. Preserve curated stage records containing my intent, the agent’s self-contained rephrasing, assumptions, skills actually used, acceptance criteria, execution summary, real verification evidence, deviations, and lessons. Do not publish raw chat transcripts. Clearly distinguish planned behavior from verified implementation.
>
> Keep the public repository small. Exclude real collected transit data, DuckDB files, Parquet history, raw protobuf, local models, vector indexes, secrets, and unfiltered logs. Include only tiny synthetic test fixtures. Use an MIT license and provide VBB attribution. Do not add weather enrichment, a local generative model, Supabase, BigQuery, Cosmos, dbt Cloud, or cloud object storage in version one. Cloud storage remains a measured future option.

## Prompt ownership and disclosure

The user defines goals, constraints, and architecture decisions. Hermes Agent may rephrase instructions into self-contained execution prompts and assist with implementation and verification. Curated records expose that collaboration rather than presenting generated work as unaided.
