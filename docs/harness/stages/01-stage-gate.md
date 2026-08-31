# Stage 1 gate review

**Status:** passed. Stage 2 planning may begin from these accepted records.

## User intent

Validate the Stage 1 gate from real Airflow and source-spike evidence, update measured assumptions, and stop rather than claim success when evidence is missing.

## Rephrased execution prompt

Review both approved Stage 1 spike evidence bundles against every gate criterion. Promote only accepted aggregate documentation, update architecture assumptions disproved by measurements, run correctness and complexity reviews, and keep Stage 2 blocked unless every criterion passes. Do not commit or push.

## Assumptions and constraints

- Baseline commit: `87d8e9d`.
- The first spike and one corrected remediation run were approved. No third retry is authorized.
- Raw transit responses, logs, generated credentials, and disposable runtime state must not enter Git.
- Existing VPS services must remain untouched and healthy.

## Skills used

- `ponytail:ponytail` at `full`: kept the failed runtime out of the repository and reduced the production smoke path to one standard-library command and one test file.
- `agent-harness-project-delivery`: required a curated gate record with observable evidence rather than treating completed cards as proof.
- `ponytail:ponytail-review`: checked the final documentation diff for redundant evidence and speculative runtime files.

`requesting-code-review` found and drove fixes for symlink-safe locking, a total response deadline, JSON CLI failures, structured evidence, test isolation, and stale architecture labels. Final correctness, security, evidence, complexity, and architecture reviews passed.

## Gate results

| Criterion | Evidence | Result |
|---|---|---|
| Existing services remain healthy | All protected services stayed running with unchanged health, zero restarts, and no OOM events. | Pass |
| Cron-triggered real-source smoke succeeds | User cron invoked `/usr/bin/python3 scripts/stage1_smoke.py`; it fetched an 11,626,434-byte protobuf response and exited `0` in 0.45 seconds. | Pass |
| Concurrent runs cannot overlap | The integration test held the production-style `flock`; a second process exited `75` with `overlap_blocked` before any network request. | Pass |
| Runtime stays within the accepted production boundary | Peak process RSS was 35,651,584 bytes with zero process swaps. Host available memory was 2,080,219,136 bytes before and 2,076,860,416 bytes after; host swap decreased by 262,144 bytes. | Pass |
| Idle/active memory and disk projections are recorded | Root availability was 27,517,075,456 bytes before and 27,516,780,544 bytes after. The measured 48-hour raw peak plus eight 80,429,936-byte static versions projects to 2,875,714,816 bytes, leaving 1,419,252,480 bytes under the 4 GiB cap for Parquet and quarantine. | Pass |
| Source formats and failure behavior are verified | Static GTFS and production GTFS-RT parsed; current source caveats and REST timeouts are recorded. | Pass with caveats |
| REST comparison preserves official-source authority | Two of three requests timed out; the one response remained diagnostics-only, with no authoritative/fallback role. | Pass |
| Cleanup and Git hygiene | Disposable Airflow/source resources were removed; no raw payload, dataset, secret, commit, or push was retained. | Pass |
| Credential handling follows the approved plan | The corrected run verified mode `0600` before startup and removed the credential during cleanup. | Pass |
| Measured storage-pilot procedure is ready | The command reports pre-run disk capacity. Stage 2 will measure one day of normalized output, project the 28-day retained total, and pause before a write whenever counted storage would exceed 4 GiB. The 31,251,854,592-byte 28-day raw download total is not retained because raw payloads expire after 48 hours. | Pass |
| Stage 1 code has a runnable check and complexity review | Five standard-library integration tests pass. Independent correctness/security review passed, and the final Ponytail verdict was `Lean already. Ship.` | Pass |
| Pinned environment proposal | Production scheduling uses active host cron and Ubuntu's `/usr/bin/python3` 3.12.3 with no added dependency or service. Airflow remains isolated to a later synthetic Docker demo. | Pass |
| Non-destructive preflight | The retained command checks available memory, project-filesystem capacity, exclusive-lock availability, response size, non-empty content, and protobuf media type without stopping or restarting any service. | Pass |
| Architecture diagram | The accepted diagram separates cron production collection from the isolated synthetic Airflow demo. | Pass |

## Execution summary

The official VBB sources are suitable for Stage 2 design with explicit parse, freshness, coverage, and static-version caveats. The REST wrapper is excluded from the production path on current evidence.

The corrected Airflow 3.3.1 standalone run remains valid evidence that Airflow cannot be the production scheduler on this VPS. The accepted cron path has measured preflight, overlap, resource, storage, real-source, cleanup, and service-health evidence. Independent review passed after all blocking findings were corrected.

## Verification evidence

- Corrected Airflow image: `apache/airflow:3.3.1`, resolved digest `sha256:0c4bcc0370e526de1b7892a3bf4343d260c6c82359c66f77155b53cd773d6339`.
- Container memory samples were 46.59 MiB, 756 MiB, and 600.1 MiB at 0, 30, and 60 seconds.
- Host available memory remained above 951,435,264 bytes, but swap rose across all three samples and triggered the mandatory stop.
- Cleanup restored 1,749,880,832 bytes of available memory, reduced swap to 672,051,200 bytes, freed port `18080`, and removed all disposable resources.
- Static GTFS: 80,429,936-byte ZIP, required files present, 5,918,856 stop-time rows checked, and U-Bahn/S-Bahn/tram scope present.
- Production GTFS-RT: version `2.0`, 9,507 `TripUpdate` entities, with an active limited-coverage notice.
- REST: U Mehringdamm and S Savignyplatz timed out at 30 seconds; Hufelandstr. returned eight M4 departures in 13,281.5 ms.
- `git diff --check`, relative documentation links, forbidden-artifact checks, and added-line security scans passed.
- Independent correctness/security review found unsupported gate results, incomplete blocker summaries, and stale architecture labels; all were corrected before the final re-review.
- Ponytail review removed a duplicate 95-line source contract and two redundant 187-line evidence notes; the final diff keeps one source register, one contract, and one source synthesis.
- Curated machine-readable evidence: [`../evidence/stage1-cron-smoke.json`](../evidence/stage1-cron-smoke.json).
- Corrected cron smoke timestamp: `2026-08-31T13:10:01.717202+00:00`; content type `application/protobuf`; response size 11,626,434 bytes; stderr empty; exit status `0`.
- `/usr/bin/time -v` recorded 0.45 seconds elapsed, 35,651,584 bytes peak RSS, and zero swaps.
- Protected-service state matched before and after the run. Health was unchanged, with zero restarts and no OOM events.
- Five tests cover aggregate-only success output, overlap blocking, symlink-safe locking, JSON argument errors, and a total response deadline.
- `python3 -m unittest discover -s tests -v`, Python compilation, and `git diff --check` passed before the corrected live smoke run.
- Final independent review found no remaining security concern, logic error, documentation mismatch, or unnecessary complexity.
- Focused SVG/HTML review confirmed that both architecture assets show cron for real VBB production and Airflow for isolated synthetic demos; XML, HTML, and embedded SVG parsing passed.

## Deviations

- The failed Airflow run is retained as boundary evidence rather than repaired or repeated. It is no longer a production gate criterion.
- The Stage 1 smoke validates reachability, bounded response handling, and media type. Full protobuf parsing, freshness validation, normalization, and committed slot state remain Stage 2 work.
- The storage projection uses the measured realtime payload and eight retained static versions. Stage 2 must replace the unknown normalized-output term with its 24-hour pilot measurement.
- Exact entity-level GTFS/GTFS-RT/REST identifier correspondence was not retained; REST remains diagnostics-only and inconclusive for mapping.

## Lessons and next decision

Cron is the production scheduler on this host. Dockerized Airflow remains an isolated synthetic learning demo in Stage 2. Stage 1 passes; Stage 2 planning is the next gated activity.
