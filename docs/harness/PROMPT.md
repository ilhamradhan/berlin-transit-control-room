# Prompt record

## Summary of the user request (not verbatim)

Create a learning project that combines harness engineering (setup, planning, implementation, deployment, and reproducible agent use) with a data-engineering stack based on DuckDB, Airflow, and dbt. Add an AI capability only where it helps the product. Preserve the prompt, its rephrasing, skills used, decisions, setup, plan, deployment, and verification in separate Markdown files for future reference.

The selected product is a Berlin transit reliability and data-pipeline Control Room using VBB data.

## Agent-rephrased implementation brief

Baseline date: 2026-08-27

> Build **TransitOps Berlin** as a public learning project. The finished repository must contain a working data pipeline, tests, deployment instructions, and evidence for every completed stage.
>
> Use VBB static GTFS and GTFS-Realtime for Berlin U-Bahn, S-Bahn, and tram. Collect realtime snapshots every 15 minutes on an always-on but resource-constrained VPS. Require at least seven elapsed days with 90% successful collection-slot coverage. A slot succeeds only when the response parses as GTFS-Realtime, passes the source-contract freshness check, and commits its normalized output; unchanged payloads and entity completeness are separate metrics. Stop automatically after 28 calendar days or before a write would push collection files above 4 GB. Count raw, quarantined, static, and Parquet files toward that limit. Expire all raw and quarantined payloads after 48 hours unless a sanitized sample is deliberately promoted into the test fixtures. Compact the required observations into date-partitioned Parquet. Check static GTFS daily and retain each compressed version referenced by retained observations. The accepted finite campaign is complete; production collection is stopped for the remaining stages.
>
> During Stage 1, run a bounded comparison of `v6.vbb.transport.rest` at one U-Bahn, one S-Bahn, and one tram stop. Measure identifier mapping, added disruption fields, response behavior, and data-use constraints. Do not use it as the historical source, automatic fallback, or part of the official collection-slot metric. Retain only sanitized fixtures and aggregate spike evidence unless a later decision explicitly accepts bounded on-demand incident enrichment.
>
> Record idle and active memory use for the smallest Airflow topology that can run the project safely. Airflow must run explicit dbt CLI commands. Use dbt and DuckDB for transformations, quality tests, and reliability marts. Before publication, checkpoint and close the candidate DuckDB file, reopen it independently in read-only mode, and run publication checks. Replace the manifest atomically on the same filesystem only after those checks pass. Retain the current and previous release, and do not delete a release still held by a reader. Store low-volume incident and action state in a separate SQLite database using WAL mode.
>
> Build a static public product with only Transit Reliability and System Documentation pages. Generate compact mode/route/day aggregates from the private verified release at build time. Show the existing Stage 3 metrics with nearby definitions, provenance, limitations, and low-coverage caveats. Do not expose stop-level, event-level, trip-level, raw, or private operational data. Defer Control Room, Incident Detail, synthetic recovery controls, and live updates.
>
> Add a small local or CLI/demo-bound cited read-only RAG evaluation over approved documentation, metric definitions, limitations, and cited runbook guidance. Select retrieval and a candidate provider only after measuring quality, citations, insufficiency behavior, latency, and cost assumptions. Never send secrets, environment variables, connection strings, unfiltered logs, or unrestricted filesystem contents. The RAG layer must not calculate metrics, execute commands, or claim recovery. Keep the corpus, metadata, and index below 1 GB.
>
> Develop through five phase gates. Preserve curated stage records containing my intent, the agent’s self-contained rephrasing, assumptions, skills actually used, acceptance criteria, execution summary, real verification evidence, deviations, and lessons. Do not publish raw chat transcripts. Clearly distinguish planned behavior from verified implementation.
>
> Before any coding task, load `ponytail:ponytail` at `full`. Reuse existing code, standard-library functions, native platform features, and installed dependencies before adding code or packages. Keep the shortest implementation that satisfies the accepted behavior, trust-boundary validation, security, accessibility, data safety, and a minimal runnable check. Run a separate Ponytail complexity review at each coding-stage gate.
>
> Keep the public repository small. Exclude real collected transit data, DuckDB files, Parquet history, raw protobuf, local models, vector indexes, secrets, and unfiltered logs. Include only tiny synthetic test fixtures. Use an MIT license and provide VBB attribution. Do not add weather enrichment, a local generative model, Supabase, BigQuery, Cosmos, dbt Cloud, recurring cloud compute, or public interactive RAG in version one. Cloudflare Pages/R2/Workers may be measured with synthetic artifacts only; adoption remains optional and reversible.

## Prompt ownership and disclosure

The brief came from an agent-assisted requirements discussion. The user accepted the scope, constraints, and architecture decisions recorded in [`DECISIONS.md`](DECISIONS.md). Implementation and verification may be agent-assisted, but completed work counts only when the repository contains supporting evidence.
