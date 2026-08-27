# Runbook index

**Status:** index only. Individual runbooks will be implemented and tested with their corresponding failure scenario.

| Incident | Planned runbook | Demo control | Post-action check |
|---|---|---|---|
| Stale or unavailable realtime source | `docs/runbooks/recover-stale-source.md` | Retry once only when the source health check passes; otherwise escalate | Fresh validated slot exists or incident remains unresolved |
| Static/realtime schedule mismatch | `docs/runbooks/refresh-static-schedule.md` | Fetch and validate the matching static feed if available; otherwise quarantine and escalate | Match rate recovers or the mismatch remains isolated |
| dbt quality-test failure | `docs/runbooks/recover-failed-dbt-build.md` | Reset the synthetic failure fixture, then rebuild | Tests pass and a checked candidate publishes |

## Runbook requirements

Each runbook must include:

- Detection condition
- User-visible impact
- Evidence to inspect
- Known safe causes
- Preconditions
- Exact approved demo control and unresolved path
- Expected audit event
- Post-action health check
- Escalation/insufficient-evidence behavior
- Synthetic-demo isolation statement

The RAG assistant may retrieve and cite these runbooks. It cannot invoke their controls or claim that a recovery occurred.
