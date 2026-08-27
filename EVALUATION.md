# Evaluation plan

## Principle

Acceptance requires real, recorded evidence. A generated answer, successful write call, or completed checklist is not proof by itself.

## Ingestion and storage

- Expected schedule: 96 slots per full day at 15-minute cadence.
- Minimum usable campaign: at least 14 elapsed days and at least 90% successful collection slots.
- Any result below 90% fails campaign acceptance.
- A 75–89.9% result may still be displayed as an incomplete dataset with a low-coverage warning.
- Below 75% is too incomplete for the reliability explorer.
- Campaign stops after 28 calendar days or 4 GB, whichever comes first.
- Idempotency tests prove reruns do not duplicate observations.
- Cleanup tests prove raw and quarantined payloads expire after 48 hours.
- Daily compaction produces queryable Parquet and bounded file counts.

Entity-level realtime coverage within successful snapshots is evaluated separately from collection-slot coverage.

## dbt and DuckDB

- Static/realtime identifiers and time fields satisfy source contracts.
- Known synthetic fixtures produce expected delay, coverage, and match metrics.
- Failed dbt tests prevent manifest publication.
- A reader can continue using the current release while a candidate builds.
- Atomic publication selects only a verified candidate.
- Retention keeps current and previous releases.

## Controlled incidents

For each scenario (stale source, schedule mismatch, and dbt quality failure), verify:

1. Safe synthetic trigger
2. Visible health degradation
3. Diagnostic evidence
4. Relevant cited runbook
5. Correct allowlisted recovery action
6. Audit record in SQLite
7. Separate deterministic recovery verification
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
