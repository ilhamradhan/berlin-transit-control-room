# Evaluation plan

## Principle

Acceptance requires real, recorded evidence. A generated answer, successful write call, or completed checklist is not proof by itself.

For every code-producing stage, record that `ponytail:ponytail` was active at `full`, run the smallest relevant check for non-trivial logic, and run `ponytail:ponytail-review` on the final diff. A lean diff still must pass all correctness, security, and stage-specific checks.

## Optional REST source comparison

- Query a small fixed sample covering one U-Bahn, one S-Bahn, and one tram stop. Do not crawl the network.
- Compare current delay, cancellation, platform, and disruption fields with official GTFS-Realtime for the same observation window.
- Record stop, line, and trip identifier mapping results against static GTFS. Do not assume HAFAS trip IDs are GTFS trip IDs.
- Record response status, latency, cache headers, payload size, and documented rate limits.
- Confirm acceptable data-use and attribution terms before retaining or publishing returned data. The wrapper's software license is not evidence of a license for its transit responses.
- Store only sanitized fixtures and aggregate comparison results. Do not start a second historical archive.
- A wrapper outage or mismatch never changes official collection-slot success and never triggers an automatic fallback.
- End with one verdict: reject, use only for diagnostics, or allow bounded on-demand incident enrichment.

References: [`v6.vbb.transport.rest` documentation](https://v6.vbb.transport.rest/), [API routes](https://v6.vbb.transport.rest/api.html), and the [official VBB API access process](https://unternehmen.vbb.de/digitale-services/api/).

## Ingestion and storage

- Expect 96 slots per 24 elapsed hours. Generate the denominator from UTC schedule intervals so Europe/Berlin daylight-saving days can contain 92 or 100 slots.
- Minimum usable campaign: at least 7 elapsed days and at least 90% successful collection slots.
- A slot succeeds only when the response parses as GTFS-Realtime, passes the source-contract freshness check, and commits normalized output.
- Unchanged payloads and entity-level completeness are tracked separately from slot success.
- Any result below 90% fails campaign acceptance.
- A 75–89.9% result may still be displayed as an incomplete dataset with a low-coverage warning.
- Below 75% is too incomplete for the reliability explorer.
- Campaign stops after 28 calendar days or 4 GB, whichever comes first.
- Before every counted write, current bytes plus projected output are checked; collection pauses rather than overshooting 4 GB.
- Idempotency tests prove reruns do not duplicate observations.
- Cleanup tests prove raw and quarantined payloads expire after 48 hours.
- Daily compaction produces queryable Parquet and bounded file counts.

Entity-level realtime coverage within successful snapshots is evaluated separately from collection-slot coverage.

## dbt and DuckDB

- Static/realtime identifiers and time fields satisfy source contracts.
- Known synthetic fixtures produce expected delay, coverage, and match metrics.
- Failed dbt tests prevent manifest publication.
- The candidate is checkpointed and closed, then reopened independently in read-only mode before publication.
- The manifest replacement occurs atomically on the same filesystem.
- A reader can continue using the current release while a candidate builds.
- Cleanup does not remove a release still referenced by an active reader.
- Atomic publication selects only a verified candidate.
- Retention keeps current and previous releases.

## Controlled incidents

For each scenario (stale source, schedule mismatch, and dbt quality failure), verify:

1. Safe synthetic trigger
2. Visible health degradation
3. Diagnostic evidence
4. Relevant cited runbook
5. Correct approved demo control or an unresolved/escalated outcome
6. Audit record in SQLite
7. Separate post-action health check
8. No mutation of healthy collected data

## Dashboard

Browser QA verifies:

- Four intended pages and labels
- No traceback or broken navigation
- Required Control Room health fields
- Filters and metric definitions
- Clear distinction between prediction observations and actual arrivals
- Prominent low-coverage qualifications
- No causal language
- Read-only assistant boundary

## RAG evaluation

The evaluation set contains known questions, expected source documents/sections, and prohibited claims.

Required checks:

- Expected source appears in retrieved top results.
- Answer cites the correct file and section.
- Every material claim is supported by its citation.
- Unsupported questions produce explicit insufficiency rather than invention.
- The assistant never claims it ran, retried, fixed, acknowledged, or verified an incident.
- Secrets and excluded operational content never enter the index or generation context.
- Current incident metadata is sanitized and supplied per request rather than embedded as permanent knowledge.
- Embedding model, corpus, metadata, and index remain below 1 GB.

## Resource evaluation

Record before and after starting TransitOps:

- Host available memory
- Swap use and change
- Per-container memory
- Restart counts
- Idle and sample-DAG active load
- Project disk use and projected 28-day growth

The lightweight topology fails the spike if it destabilizes existing services, enters restart loops, or produces unsafe sustained swap pressure. The exact numeric threshold will be selected from measured evidence.
