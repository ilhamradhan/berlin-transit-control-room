# VBB source register

TransitOps Berlin uses official VBB static GTFS for planned schedules and identifiers, and official VBB GTFS-Realtime production for current observations. `v6.vbb.transport.rest` remains a non-authoritative diagnostic comparison only.

| Source | Contracted role | Stage 1 verdict |
|---|---|---|
| [VBB static GTFS](https://unternehmen.vbb.de/digitale-services/datensaetze) | Planned schedule and identifier baseline | Pass with caveats: required files and scoped modes were present; no `feed_info.txt`. |
| [VBB GTFS-Realtime production](https://production.gtfsrt.vbb.de) | Realtime source after parse, freshness, and output-commit checks | Pass with caveats: parseable, with an active limited-coverage notice. |
| [VBB GTFS-Realtime staging](https://staging.gtfsrt.vbb.de) | Development endpoint only | Limited: the observed sample was stale and empty. |
| [`v6.vbb.transport.rest`](https://v6.vbb.transport.rest/) | Bounded diagnostic comparison | Diagnostics only; two of three requests timed out and identifier mapping was not proven. |

See [`SOURCE_CONTRACTS.md`](SOURCE_CONTRACTS.md) for identifiers, validation, retention, attribution, and prohibited uses. See [`stages/01-harness-source-validation.md`](stages/01-harness-source-validation.md) for measured evidence and the final source verdict.
