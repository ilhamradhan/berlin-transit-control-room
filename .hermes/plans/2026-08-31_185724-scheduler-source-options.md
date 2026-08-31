# Scheduler and realtime-source decision plan

**Goal:** Record the accepted scheduler architecture and finish the remaining source and production-readiness checks without running another scheduler service.

**Status:** complete. The official VBB source pair remains primary, the REST comparison is diagnostics-only, and Stage 1 cron production-readiness evidence and independent review pass. No commit or push is authorized.

## Accepted scheduler decision

Cron will schedule real VBB collection on the VPS. Dockerized Airflow DAGs will run synthetic learning demos. Both call the same idempotent pipeline commands, but production and demo inputs, state, and output paths remain isolated. The canonical boundary is documented in `docs/harness/ARCHITECTURE.md#scheduler-and-data-trust-boundary`.

## Why Airflow failed on this VPS

The issue is not that Airflow can never run here. It failed the project's co-location safety gate:

- The VPS has 3.6 GiB RAM and already runs Hermes plus unrelated production containers.
- The corrected standalone test peaked at 756 MiB for Airflow.
- Swap increased in every 30-second sample: 898,924,544, 1,057,411,072, then 1,183,494,144 bytes.
- The safety stop fired at 60 seconds before the scheduled DAG completed.
- Existing services did not crash or restart, and cleanup restored the host.

Conclusion: Airflow is not accepted beside the current services on this VPS. It may still work on a separate always-on device or a larger VPS.

## Accepted deployment split

- Cron schedules real collection on the current VPS: realtime every 15 minutes and static GTFS daily.
- Each cron entry calls one shared idempotent pipeline command with overlap prevention, bounded logging, and explicit status output.
- Dockerized Airflow runs synthetic fixtures in an isolated demo namespace and storage path.
- Airflow remains a learning artifact for dependencies, retries, failure handling, dbt gates, and publication flow; it is not production evidence.
- A second Airflow host and systemd timers are deferred because neither is required by the accepted design.

The remaining Stage 1 work is to record idle/active resource and 28-day storage projections, define and run the non-destructive preflight, prove one cron-triggered real-source smoke run cannot overlap, and verify any retained Stage 1 code. The failed Airflow spike must not be repeated.

## Can `gtfs.de` provide the realtime data?

Yes, with important limits.

The free `gtfs.de` stream includes VBB coverage for Berlin and Brandenburg. It is updated every 10 seconds and contains `TripUpdates` and `ServiceAlerts`.[1] That supports predicted delays, cancellations, and disruption notices. It does not advertise `VehiclePositions`, so it cannot support a live vehicle-position feature from this feed alone.[1]

The stream is beta, CC BY-SA 4.0, and has no guarantee of correctness, availability, or completeness.[1] The matching free static feeds are Germany-wide, generated daily, and cover only the next 30 days.[2]

Critical constraint: `gtfs.de` says its realtime stream matches the static feeds offered by `gtfs.de`.[1] We must not assume its IDs match the official VBB static GTFS. If we use `gtfs.de` realtime, we should pair it with the matching `gtfs.de` static feed or prove identifier compatibility first.

The official VBB GTFS-Realtime feed remains CC BY 4.0, unauthenticated, cache-friendly, and currently reports limited data coverage.[3] VBB also publishes its static GTFS twice weekly under CC BY 4.0.[4]

### Recommended source role

Keep official VBB static GTFS and GTFS-Realtime as the primary pair for now. Evaluate `gtfs.de` as a bounded comparison source because:

- it may fill some VBB coverage gaps;
- it adds ServiceAlerts;
- it may aggregate the same upstream VBB data, so independence is unproven;
- its Germany-wide payload may be much larger than the VBB-only feed;
- its share-alike license and matching-static requirement change publication and storage decisions.

Do not make it an automatic fallback. A fallback must not silently mix identifiers or turn an official-feed outage into a successful collection slot.

## Future bounded checks

Run these only if the diagnostics-only source decision is revisited:

1. Fetch headers and one `gtfs.de` realtime sample. Record bytes, ETag/cache behavior, parse result, entity counts, and VBB share.
2. Identify the exact free `gtfs.de` static feed that matches the realtime stream.
3. Compare a small VBB trip/route/stop sample across `gtfs.de` static/realtime and official VBB static/realtime.
4. Estimate download and retained-storage cost at the 15-minute cadence.
5. Record one updated verdict.
6. Delete raw spike files after aggregate evidence is recorded.

## Remaining decision sequence

1. Record the missing resource and 28-day storage projections.
2. Implement and verify the non-destructive preflight and overlap protection.
3. Run one cron-triggered real-source smoke job and verify its status and cleanup.
4. Close the Stage 1 gate only if all retained code and evidence checks pass.
5. Plan the Dockerized Airflow demo separately in Stage 2 with synthetic fixtures. Its result does not count as real collection evidence.

## Current direction

Keep the official VBB feed pair primary. Keep REST and `gtfs.de` out of the production path unless a later bounded decision explicitly changes their role.

## Sources

[1] https://gtfs.de/de/realtime
[2] https://gtfs.de/de/feeds
[3] https://production.gtfsrt.vbb.de
[4] https://unternehmen.vbb.de/digitale-services/datensaetze
