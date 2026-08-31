# TransitOps glossary

This glossary is extracted from `SOURCE_CONTRACTS.md` so Stage 1 terms can be read directly. Source authority, data-use constraints, and non-permitted uses remain defined in `SOURCE_CONTRACTS.md` / `SOURCES.md`.

## Terms

| Term | Meaning in this project |
|---|---|
| Stop | A routable boarding/alighting point from GTFS `stops.txt`, usually `location_type=0`, or a REST object with `type: "stop"` when comparing against REST. |
| Station | A parent or grouped passenger location. In GTFS this is represented through `stops.txt` location hierarchy; in REST station endpoints may use station IDs such as `de:11000:...` and can contain child stops. |
| `stop_id` | The stable GTFS identifier from `stops.txt` used as the baseline stop key. REST stop IDs may look similar, but they are not accepted as mapped until checked against the active GTFS version. |
| GTFS trip | A scheduled service instance from `trips.txt`, joined to `stop_times.txt`, `routes.txt`, and service calendars. It is the schedule-side object to which trip updates should map. |
| GTFS-RT entity | One `FeedEntity` in a GTFS-Realtime `FeedMessage`; it has a feed-unique `id` and may contain a trip update, vehicle position, alert, or other allowed realtime content. |
| Realtime update | A current GTFS-RT observation or REST current-time field that changes planned service interpretation, such as delay, cancellation, alert, vehicle progress, or updated source timestamp. |
| REST location/result | A JSON object returned by `v6.vbb.transport.rest`, commonly from `/locations`, `/stops/:id`, `/stations`, departures, arrivals, journeys, trips, or lines. It is comparison data unless a later decision narrows an incident-enrichment use. |
| Feed status | The observed health of a source at retrieval time: reachable/unreachable, parseable/unparseable, fresh/stale, complete/limited where measurable, and any upstream notice captured with the sample. |
| Identifier mapping | A documented relationship between identifiers from two sources, recorded as `exact`, `derived`, `unmapped`, or `ambiguous`, with evidence. Names, coordinates, and line labels can support a mapping but cannot replace matching identifiers. |
| Verdict | The implementer's explicit conclusion for a sample or comparison: accepted for its contracted use, rejected, inconclusive, stale, unmapped, ambiguous, or out of scope. A verdict must include the reason and source evidence. |

## Sources

See `SOURCE_CONTRACTS.md` and `SOURCES.md` for the cited source contract.
