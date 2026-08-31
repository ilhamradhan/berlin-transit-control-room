# VBB source contracts

This note defines how TransitOps Berlin treats each official or comparison source during Stage 1 and later implementation. It is a contract for implementers, not proof that ingestion has already been built.

## Scope and authority

TransitOps Berlin has two authoritative operating sources: VBB static GTFS for planned service structure and schedules, and VBB GTFS-Realtime for current realtime observations. VBB publishes GTFS datasets covering timetable, stop, and color data, and the GTFS static dataset contains VBB-area schedules in the GTFS format.[1][3] VBB publishes GTFS RT for realtime information at `https://production.gtfsrt.vbb.de`, with the feed data URL exposed as `https://production.gtfsrt.vbb.de/data`.[1][2]

`v6.vbb.transport.rest` is a bounded comparison source only. It is a JSON REST API for Berlin and Brandenburg public transport that wraps VBB/HAFAS-style app data and can include realtime delays and disruptions when its upstream provides them.[5][6] It must not replace static GTFS or GTFS-Realtime, must not count toward official collection-slot success, and must not become an automatic fallback.

## Source contract: VBB static GTFS

| Contract field | Definition |
|---|---|
| Role | Planned service reference: agencies, stops, routes, trips, stop times, calendars, shapes when present, and feed metadata. |
| Authority | Authoritative schedule and identifier baseline for this project. Realtime identifiers are interpreted relative to the active static GTFS version because GTFS-Realtime resolves entity IDs against an existing GTFS feed.[4] |
| Update cadence | VBB lists the current GTFS downloads as ZIP files updated twice weekly.[1] TransitOps checks daily and stores only compressed versions referenced by retained observations, per project decision D-010. |
| Primary identifiers | `stop_id` from `stops.txt`; `route_id` from `routes.txt`; `trip_id` from `trips.txt`; `service_id` from `calendar.txt`/`calendar_dates.txt`; `shape_id` when `shapes.txt` is present; `feed_version` from `feed_info.txt` when supplied. |
| Required fields for Stage 1 validation | ZIP must open; CSV files must parse; `agency.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, and either `stops.txt` or a valid alternative demanded by the GTFS spec must be available for this project's fixed-route scope.[3] The validation path must confirm that Berlin U-Bahn, S-Bahn, and tram records can be selected without writing real data to Git. |
| Optional fields to preserve when present | `feed_info.txt`, `calendar.txt`, `calendar_dates.txt`, `shapes.txt`, `transfers.txt`, `pathways.txt`, `levels.txt`, `translations.txt`, `attributions.txt`, route colors, wheelchair/accessibility fields, platform-related stop fields, and any other spec-valid files used by later metrics. |
| Permitted use | Download the current ZIP during approved source-validation or collection runs; parse and normalize the fixed-route subset; keep active extracted data and referenced compressed versions outside Git; use it to validate GTFS-RT mappings and reproduce retained observations. |
| Non-permitted use | Do not commit the GTFS ZIP, extracted CSVs, real Parquet history, DuckDB files, raw logs, or broad derived archives. Do not treat a static schedule row as proof that a realtime vehicle operated. |

## Source contract: VBB GTFS-Realtime samples

| Contract field | Definition |
|---|---|
| Role | Current realtime observation source for trip updates, source freshness, and pipeline health. |
| Authority | Authoritative realtime source for official collection-slot success. The project may report source gaps separately, because the VBB feed page explicitly flags limited data coverage and states that the feed can lack some data when the upstream source has problems.[2] |
| Update cadence | Not promised as a fixed cadence by the retrieved VBB feed page. The project samples every 15 minutes by decision, but feed freshness must be judged from the parsed `FeedHeader.timestamp`, not from the scheduler's wall clock alone. |
| Primary identifiers | GTFS-RT `FeedEntity.id` for feed-entity identity; `TripDescriptor.trip_id`, `route_id`, `start_date`, and `start_time` when present; stop references in `StopTimeUpdate.stop_id` or `stop_sequence`; `VehicleDescriptor.id` when present; `Alert` selectors when present. |
| Required fields for Stage 1 validation | HTTP response from the data URL must be captured as a bounded sample; payload must parse as a GTFS-Realtime `FeedMessage`; `FeedHeader.gtfs_realtime_version`, `FeedHeader.incrementality`, and `FeedHeader.timestamp` are required by the GTFS-Realtime reference.[4] Each non-deleted `FeedEntity` should carry exactly one active content type such as `trip_update`, `vehicle`, `alert`, `shape`, `stop`, or `trip_modifications` as allowed by the reference.[4] |
| Optional fields to preserve when present | `feed_version`, trip schedule relationship, stop-time arrival/departure delay and time fields, vehicle position fields, alert text and informed entities, occupancy/accessibility fields, and experimental fields only if clearly labeled in downstream docs. |
| Permitted use | Poll the production feed on the approved 15-minute collection cadence; store raw and quarantined payloads for the 48-hour debugging window; normalize current observations to Parquet/DuckDB outside Git; record parse result, freshness verdict, entity counts, and mapping verdict. |
| Non-permitted use | Do not crawl the endpoint outside the approved cadence. Do not retain raw protobuf history beyond the 48-hour raw/quarantine window. Do not claim a collection slot succeeded until parse, freshness, and normalized-output commit all pass. Do not hide upstream limited coverage by fabricating completeness. |

## Source contract: `v6.vbb.transport.rest` comparison data

| Contract field | Definition |
|---|---|
| Role | Diagnostic comparison source for Stage 1 only: compare current REST stop/departure/trip/location records against static GTFS and GTFS-RT samples at one U-Bahn, one S-Bahn, and one tram stop. |
| Authority | Non-authoritative for the collection metric. It may support an evidence note about identifier mapping or possible incident enrichment, but it does not override VBB static GTFS or VBB GTFS-Realtime. |
| Update cadence | On demand only for the bounded spike. The service documents a rate limit of 100 requests/minute with burst 200 requests/minute, but this project must stay far below that and must not run a crawler.[6] |
| Primary identifiers | REST stop/location `id`; station `id`; departure/arrival `tripId`; line `id`, `name`, `mode`, and `product`; `when`/`plannedWhen`; `delay`; `remarks`; `realtimeDataUpdatedAt` when returned. `/locations` can return stops/stations, POIs, and addresses, so Stage 1 must request stops only for identifier checks.[6][7] |
| Required fields for Stage 1 comparison | For each selected representative stop: request a bounded location/stop lookup and a bounded departure or arrival query; record whether REST stop IDs map to GTFS `stop_id`, whether line names/products map to selected modes, whether `tripId` maps to GTFS or GTFS-RT trip identifiers, what disruption/remark fields appear, and whether response behavior supports or rejects future use. |
| Optional fields to preserve when present | `remarks`, warning/hint IDs and summaries, platform/planned platform, `realtimeDataUpdatedAt`, products, sub-stops, entrances, and journey-leg fields if a journey query is explicitly part of the bounded spike. |
| Permitted use | Store sanitized fixtures and aggregate evidence from the three-stop comparison. A later accepted decision may allow bounded on-demand incident enrichment, but only after data-use and identifier-mapping verdicts are documented. |
| Non-permitted use | Do not archive REST responses historically. Do not crawl stops, stations, lines, journeys, maps, radar, or trips. Do not use REST availability as an automatic fallback when GTFS-RT is stale or unavailable. Do not include REST calls in the official 15-minute collection-slot success metric. |

## Cross-source validation rules

1. Static GTFS is the schedule baseline; GTFS-RT is current observation data; REST is comparison evidence only.
2. A source sample is valid evidence only when the request URL, retrieval time, parser outcome, source timestamp if available, selected identifiers, and verdict are recorded.
3. Identifier mapping must be explicit: `exact`, `derived`, `unmapped`, or `ambiguous`. A similar name is not a mapping.
4. Mode filtering uses project scope first: U-Bahn, S-Bahn, and tram. Bus, ferry, regional, and long-distance records may appear in VBB/REST sources but are out of version-one analytics scope unless needed to explain a transfer or mismatch.
5. Data-retention defaults are conservative: raw and quarantined realtime payloads expire after 48 hours; static versions are retained only when referenced by retained observations; REST fixtures are sanitized and bounded.
6. No source-health workaround may silently turn a failed source contract into success. Stale realtime, parse failure, missing static mapping, and REST mismatch are separate verdicts.
7. Public repository contents may include code, documentation, synthetic fixtures, and sanitized examples only. Real collected transit archives, raw protobuf, extracted GTFS, Parquet, DuckDB, vector indexes, secrets, and unfiltered logs stay out of Git.

## Data-use constraints

VBB states that the listed datasets are provided under Creative Commons Attribution 4.0 International (CC BY 4.0), and the VBB GTFS-RT feed page also states CC-BY 4.0.[1][2] Project code and synthetic fixtures may be MIT-licensed, but VBB data remains under its source terms and requires attribution.

The project may sample, filter, transform, and publish derived aggregate metrics with clear VBB attribution. The project must not redistribute bulk VBB archives from this repository, must not publish raw or reconstructable historical movement logs, and must not imply VBB endorsement. The project must also respect service behavior: use the official static ZIP and GTFS-RT feed for their intended roles, avoid unnecessary repeated requests, and keep the REST spike bounded even though the REST API is unauthenticated.[6]

Network crawling and historical REST archiving are prohibited. Specifically: do not enumerate all REST stops/stations/lines/trips; do not page indefinitely through journeys; do not poll REST on a schedule to create a shadow realtime archive; do not preserve raw REST responses beyond the accepted sanitized Stage 1 fixtures; and do not expand the three-stop comparison without a new decision.

## Implementation handoff

Future implementers should place source-sample scripts, parser checks, and sanitized fixtures under a Stage 1 evidence path, not under this note. If a sample contradicts this contract, update the contract and decision record instead of patching ingestion logic around an undocumented exception.

## Sources

[1] https://unternehmen.vbb.de/digitale-services/datensaetze: VBB offene Datensätze
[2] https://production.gtfsrt.vbb.de: VBB GTFS Realtime Feed
[3] https://gtfs.org/documentation/schedule/reference: GTFS Schedule Reference
[4] https://gtfs.org/documentation/realtime/reference: GTFS Realtime Reference
[5] https://v6.vbb.transport.rest: v6.vbb.transport.rest documentation
[6] https://v6.vbb.transport.rest/api.html: v6.vbb.transport.rest API documentation
[7] https://v6.vbb.transport.rest/getting-started.html: Getting Started with v6.vbb.transport.rest
