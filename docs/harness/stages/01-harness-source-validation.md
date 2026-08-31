# Stage 1 harness source validation

Inspection window: 2026-08-31T09:05:40Z to 2026-08-31T09:07:34Z UTC.

This is the final synthesis for the Stage 1 source-validation spike. It combines the official VBB GTFS/GTFS-Realtime validation, the source contracts/glossary, and the bounded three-stop `v6.vbb.transport.rest` comparison.

## Verdict

Overall verdict: `pass with caveats`.

TransitOps Berlin can proceed with official VBB static GTFS as the planned-service baseline and official VBB GTFS-Realtime production as the realtime observation source. The caveats are real: GTFS-RT production was reachable and parseable but had an active VBB limited-coverage notice; staging had zero entities and is not representative; the static ZIP had no `feed_info.txt`; and the REST comparison did not prove entity-level identifier mapping.

REST verdict: `diagnostics only / inconclusive for mapping`.

`v6.vbb.transport.rest` is acceptable only for the bounded Stage 1 diagnostic comparison already performed and for documenting possible future questions. It is not acceptable as an authoritative source, official collection-slot fallback, historical archive, completeness oracle, or bounded incident-enrichment input on the current evidence. Before any future incident-enrichment use, the project needs a new decision covering response-data terms, tighter latency/retry limits, and explicit mappings against retained official GTFS and GTFS-RT slices.

## Source roles

| Source | Role in this project | Stage 1 result |
|---|---|---|
| VBB static GTFS | Authoritative planned schedule and identifier baseline: stops, routes, trips, stop times, services, shapes when present. | `pass with caveats`: current ZIP was reachable, parseable, had required files, and covered U-Bahn/S-Bahn/tram scope; no `feed_info.txt`, so version identity must use hash/download/HTTP metadata. |
| VBB GTFS-Realtime production | Authoritative current realtime observation source for collection-slot success after parse, freshness, and normalization checks pass. | `pass with caveats`: reachable and parseable as GTFS-Realtime `2.0` with 9,507 `TripUpdate` entities, but VBB status reported limited data coverage. Do not treat absent entities as proof of no service while that incident remains open. |
| VBB GTFS-Realtime staging | Development/test endpoint for client behavior. | `limited`: reachable and parseable but observed sample had zero entities and an old timestamp, so it cannot validate normal entity parsing or coverage. |
| `v6.vbb.transport.rest` | Non-authoritative bounded comparison source. | `diagnostics only`: one tram stop returned useful JSON; two approved stops timed out at 30 s; identifier mapping to official entities remains unproven. |

## Identifier mapping register

Mapping labels follow the source contract: `exact`, `derived`, `ambiguous`, or `unmapped`. This synthesis also uses `not observed` for cases where the bounded sample timed out before a value existed.

### Official GTFS static to GTFS-Realtime

| Official GTFS / GTFS-RT entity | Mapping verdict | Evidence and handling |
|---|---|---|
| GTFS `trip_id` to GTFS-RT `TripDescriptor.trip_id` | `exact when present, not sample-proven here` | The GTFS-Realtime contract resolves trip descriptors against an active GTFS feed. Stage 1 production sample parsed `TripUpdate` entities, but retained aggregate evidence does not include entity-level trip IDs, so no specific trip pair is proven in this note. |
| GTFS `route_id` to GTFS-RT `TripDescriptor.route_id` | `exact when present, not sample-proven here` | Same contract basis as `trip_id`; no retained parsed entity slice is available for a concrete route match. |
| GTFS `stop_id` to GTFS-RT `StopTimeUpdate.stop_id` | `exact when present, not sample-proven here` | GTFS-RT stop references are interpreted against the static feed. The raw GTFS-RT sample was not retained with stop-time update slices, so no concrete stop pair is proven. |
| GTFS static version to GTFS-RT `schedule_sha256=605f2b3a` | `ambiguous` | Production GTFS-RT served `content-type: application/protobuf; schedule_sha256=605f2b3a`. This likely identifies the schedule snapshot, but the exact algorithm and scope were not proven. Treat it as an observed hint, not a verified foreign key. |
| GTFS `feed_info.feed_version` | `unmapped / unavailable` | Observed static ZIP did not include `feed_info.txt`; versioning must use sample SHA-256, download timestamp, and HTTP metadata instead. |

### Approved stops and REST stop IDs

| Approved sample | Official intended identifier | REST observed identifier | Mapping verdict | Evidence and handling |
|---|---:|---:|---|---|
| U Mehringdamm | `900017101` | not observed | `not observed` | REST departure request timed out before `2026-08-31T09:06:50Z`; no JSON, headers, name, coordinates, products, or departures were parsed. Static aggregate evidence says U-Bahn scope exists, but retained official stop slice was unavailable. |
| S Savignyplatz | `900024203` | not observed | `not observed` | REST request timed out after 30,056.0 ms at `2026-08-31T09:07:20Z`; no entity-level comparison possible. Static aggregate evidence says S-Bahn scope exists, but retained official stop slice was unavailable. |
| Hufelandstr. | `900110521` | `900110521` | `ambiguous / likely exact, not proven` | REST returned stop ID `900110521`, name `Hufelandstr. (Berlin)`, coordinates `52.53252, 13.428787`, tram product flags, and 8 M4 departures. The REST ID matches the approved VBB-like identifier, but the official `stops.txt` row was not retained, so this note cannot prove an exact GTFS `stop_id` match. |

### REST line, route, trip, and realtime fields

| REST field | Candidate official mapping | Mapping verdict | Evidence and handling |
|---|---|---|---|
| REST `line.name` = `M4` | GTFS `routes.route_short_name` | `ambiguous / inferred` | Hufelandstr. returned 8 tram M4 departures and official static aggregate evidence proved tram scope exists. No retained `routes.txt` slice proves the exact route row. |
| REST `line.id` = `de-vbb-11000000-tram-m4` | GTFS `routes.route_id` | `unmapped` | The REST line ID is not proven to equal a GTFS `route_id`. Treat as REST/HAFAS identifier until matched against retained static GTFS. |
| REST `line.product` / product flags = `tram` | Project mode scope and GTFS route type | `derived / inferred` | Product agrees with the approved tram sample and the static aggregate says tram routes exist. Exact GTFS route-type row was not retained. |
| REST `tripId` | GTFS `trips.trip_id` or GTFS-RT `TripDescriptor.trip_id` | `unmapped` | Observed values were HAFAS-style IDs. No retained `trips.txt`, `stop_times.txt`, or parsed GTFS-RT entity slice proves a match. Do not store them as official trip IDs. |
| REST `plannedWhen`, `when`, and `delay` | GTFS scheduled times plus GTFS-RT stop-time update delay/time | `ambiguous` | REST exposed one +180 s delay and one -120 s early departure among the 8 Hufelandstr. departures. No parsed official GTFS-RT stop-time update was retained for correspondence. |
| REST `cancelled`, `platform`, `plannedPlatform` | GTFS-RT schedule relationship / stop-time properties or static stop/platform data | `not proven` | Hufelandstr. returned null cancellation and platform fields. There is no official parsed comparison slice. |
| REST `remarks` | GTFS-RT alerts or HAFAS notices | `ambiguous` | Each Hufelandstr. departure carried remarks counts, but the retained note did not preserve raw remarks or official alert entities. Do not infer alert equivalence. |

## Feed-status evidence

Static GTFS evidence:

- Official VBB source exposed a current GTFS ZIP at `https://unternehmen.vbb.de/gtfs` / `https://www.vbb.de/vbbgtfs`.
- `HEAD` returned `HTTP/2 200`, `application/zip`, `content-length: 80429936`, and `content-disposition: attachment; filename="gtfs.zip"`.
- Temporary ZIP size was 80,429,936 bytes with SHA-256 `8be67438f653fe8e090e609ef29ec9db62986652d9811f0c2b98e6ec2e714909`.
- ZIP inspection found `agency.txt`, `calendar.txt`, `calendar_dates.txt`, `frequencies.txt`, `levels.txt`, `pathways.txt`, `routes.txt`, `shapes.txt`, `stop_times.txt`, `stops.txt`, `transfers.txt`, and `trips.txt`.
- Observed row counts included 38 agencies, 1,254 routes, 42,104 stops, 267,013 trips, and 5,918,856 stop-time rows.
- Scope included route types sufficient for Stage 1 U-Bahn, S-Bahn, and tram filtering.

GTFS-RT production evidence:

- Official VBB feed data URL: `https://production.gtfsrt.vbb.de/data`.
- `HEAD --http1.1` returned `HTTP/1.1 204 No Content`, `application/protobuf; schedule_sha256=605f2b3a`, ETag, and `last-modified: Mon, 31 Aug 2026 09:06:22 GMT`.
- Temporary protobuf SHA-256 was `05a76f331ea6bab5348dae6b219e2f037206f1b29f94e7b31995071b23c29b16`.
- Parsed feed header: GTFS-Realtime `2.0`, `FULL_DATASET`, timestamp `2026-08-31T09:06:21Z`, 9,507 `TripUpdate` entities.
- VBB production status reported `limited data coverage` since 2026-06-04 16:00 with no recovery estimate.

GTFS-RT staging evidence:

- Official staging URL: `https://staging.gtfsrt.vbb.de/data`.
- Observed as reachable and parseable, but temporary sample was 15 bytes, timestamped `2026-08-10T22:44:28Z`, and had zero entities.

REST comparison evidence:

- Endpoint pattern used once per stop: `GET https://v6.vbb.transport.rest/stops/{stop_id}/departures?duration=20&results=8&remarks=true&language=en`.
- User-Agent used: `TransitOpsBerlinStage1/0.1 bounded-rest-comparison contact:local-kanban`.
- U Mehringdamm and S Savignyplatz timed out at the 30 s request bound.
- Hufelandstr. returned `HTTP 200` at `2026-08-31T09:07:34Z`, latency 13,281.5 ms, size 17,082 bytes, `application/json; charset=utf-8`, cache max-age 30 s, and 8 parsed M4 tram departures.

## Data-use constraints

- VBB static GTFS and GTFS-RT remain source data under VBB/Creative Commons Attribution terms; retain attribution as `VBB Verkehrsverbund Berlin-Brandenburg GmbH` where VBB data appears.
- Do not commit real GTFS ZIPs, extracted CSVs, GTFS-RT protobuf files, raw transit archives, Parquet/DuckDB outputs, vector indexes, unfiltered logs, or secrets.
- Raw and quarantined GTFS-RT payloads are allowed only for the project retention window; the source contract states 48 hours for raw/quarantine debugging data.
- Static versions may be retained outside Git only when referenced by retained observations.
- Do not crawl official endpoints. Use approved collection cadence and informative User-Agent behavior.
- Do not crawl REST stops, stations, lines, journeys, maps, radar, or trips.
- Do not create a historical REST archive or schedule REST polling as a shadow realtime feed.
- REST wrapper/software documentation does not settle response-data licensing. Treat response-data terms as unresolved unless a later decision cites an authoritative source.

## Comparison limitations

- The official raw static GTFS archive, parsed static slices, raw GTFS-RT protobuf, and parsed GTFS-RT entity slices were not retained in this task's workspace.
- Therefore, this note cannot prove exact stop-name, coordinate, route-row, trip-row, stop-time, delay, cancellation, platform, or alert correspondence for the REST sample.
- Two of three REST requests timed out, so the comparison is too weak to generalize about REST reliability across U-Bahn/S-Bahn/tram.
- The successful tram sample proves the REST endpoint can expose useful current departure diagnostics, not that it maps cleanly to official identifiers.
- No historical archive was created, so the evidence is a point-in-time bounded observation only.

## Actionable decision

The official VBB static GTFS and GTFS-Realtime evidence is suitable for a future Stage 2 plan built around explicit parse, freshness, and retained non-Git evidence. At the time of this source-validation task, the overall Stage 1 gate remained blocked by separate Airflow and storage-pilot failures; the current gate status is recorded in `01-stage-gate.md`.

Do not build REST into the production path now. If REST is revisited, limit it to a separately approved spike that:

1. Uses a fresh retained official static slice and parsed GTFS-RT slice for the exact same timestamp window.
2. Defines response-data terms before preserving fixtures.
3. Separates REST/HAFAS IDs from GTFS IDs in the schema.
4. Uses strict per-request timeout and retry budgets.
5. Records each mapping as `exact`, `derived`, `ambiguous`, or `unmapped` with evidence.

## Sources

- https://unternehmen.vbb.de/digitale-services/datensaetze: VBB open datasets.
- https://production.gtfsrt.vbb.de: VBB GTFS-Realtime feed.
- https://staging.gtfsrt.vbb.de: VBB GTFS-Realtime staging feed.
- https://gtfs.org/documentation/schedule/reference: GTFS Schedule Reference.
- https://gtfs.org/documentation/realtime/reference: GTFS-Realtime Reference.
- https://v6.vbb.transport.rest: REST wrapper documentation.
- https://v6.vbb.transport.rest/api.html: REST API documentation.

## Evidence incorporated

This synthesis promotes accepted aggregate evidence from the bounded source-validation and REST-comparison spikes. It did not perform new network fetches, create a historical REST archive, retain raw VBB/REST payloads, commit, or push.
