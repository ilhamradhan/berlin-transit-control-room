# Runbook index

**Status:** index only. Individual runbooks will be implemented and tested with their corresponding failure scenario.

| Incident | Planned runbook | Deterministic action | Verification |
|---|---|---|---|
| Stale or unavailable realtime source | `docs/runbooks/recover-stale-source.md` | Retry ingestion with validated source/fixture | Fresh validated collection slot exists |
| Static/realtime schedule mismatch | `docs/runbooks/refresh-static-schedule.md` | Refresh/realign validated static schedule, then rematch | Match rate returns to accepted range |
| dbt quality-test failure | `docs/runbooks/recover-failed-dbt-build.md` | Rerun corrected synthetic dbt build | Tests pass and verified candidate publishes |

## Runbook requirements

Each runbook must include:

- Detection condition
- User-visible impact
- Evidence to inspect
- Known safe causes
- Preconditions
- Exact allowlisted recovery control
- Expected audit event
- Deterministic verification
- Escalation/insufficient-evidence behavior
- Synthetic-demo isolation statement

The RAG assistant may retrieve and cite these runbooks. It cannot invoke their controls or claim that a recovery occurred.
