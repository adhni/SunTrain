# World · Flights

**Later expansion:** current World counts and the active international preparation command are in [INTERNATIONAL_LONGHAUL_NOTES.md](INTERNATIONAL_LONGHAUL_NOTES.md). Counts below describe this earlier pass.

World combines the 40 existing flight views for **2 November 2026, 00:00–24:00 UTC**, paused at **10:00 UTC**. It is a dated partial collection, not complete worldwide traffic. Existing country, hub and network views keep their URLs, records and presentation palettes.

## Prepared union

| Measure | Result |
| --- | ---: |
| Entries in validated member views | 88,083 |
| Unique identities before the UTC window | 60,112 |
| Repeated entries removed | 27,971 |
| Unique flights overlapping the UTC day | 53,591 |
| Domestic / international | 27,898 / 25,693 |
| Directional airport pairs | 16,823 |
| Airports with returned flights / in catalogues | 1,476 / 1,743 |
| Peak active flights, 15:00 UTC | 7,584 |
| Flights departing before the UTC day | 2,983 |
| Flights arriving at or after the UTC day ends | 4,116 |

Preparation uses each validated adapter and its existing replay window, preserving source supersession/exclusion rules. It reads 44 source archives once each using a preparation-scoped cache with private copies; ordinary HTTP requests read only the derived World file. No new searches, schedules or fare conversions are performed.

The snapshot is `data/reference/world_flights/2026-11-02.json.gz`. Its metadata includes every input's SHA-256 and size, 40 member-view IDs, per-view collection evidence and unique union counts. Each flight retains source view IDs, original flight IDs, source pages and capture dates. Query totals remain per source because those sources overlap.

Rebuild with existing inputs:

```bash
PYTHONPATH=. PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_world_flights.py
```

The writer sorts canonical JSON, fixes the gzip timestamp, writes atomically and produces a readable snapshot. `--output PATH` supports a comparison build. `SUNTRAIN_WORLD_FLIGHTS_REFERENCE` can override the runtime snapshot path. Rebuilding is an explicit offline action; requests never run preparation.

## Identity, prices and aircraft

Identity includes carrier, flight number, exact origin/destination codes and both UTC timestamps. Distinct flight numbers remain distinct. Reusing a source ID for different identities fails preparation; matching clocks do not imply a codeshare.

Reviewed timezone/ICAO aliases are explicit in `dashboard/world_flights.py`. Unreviewed timezone, country or coordinate conflicts fail. Canadian dated `replay_timezone` overrides remain in airport objects and local boards, including Vancouver's preserved UTC−7 replay offset.

All distinct compatible quotes from the validated views remain in the snapshot. Primary display prefers an existing USD quote, then EUR, then MYR, choosing the cheapest within that currency. The current union has 31,156 primary USD prices, 9,669 EUR, 926 MYR and 11,840 unavailable prices. All 125 flights with multiple quotes have multiple currencies. Details show the cheapest captured quote in each currency and allow expanding every quote, capture timestamp and contributing view. No comparison or conversion between currency amounts is performed.

Specified aircraft take precedence over unknown values. Conflicting specified types retain their alternatives and show “Aircraft differs between captures”. There are no such conflicts in the current union; synthetic preparation tests cover them.

## Browser representation

HTTP format **28** retains the endpoint structure, immutable cache, ETags, gzip negotiation and query-metadata exclusions. World alone uses gzip level 9 to meet the download budget; existing views retain level 3. Services and airport fields retain their normal format.

World adds `flight_geometry: "great_circle_v1"`. Each path contains airport indices, 64 segments and an anchor instead of coordinate/distance arrays. The browser generates and caches the existing illustrative great-circle algorithm only when a flight position, selected route or frequency line requires it. Other views retain their original path arrays.

Individual dots remain below zoom 4.5; nearby planes use 16 CSS px artwork and the selected plane uses 22 px with its ring/route. World paints every 250 ms at wide zooms and 60 ms nearby. Only markers inside the viewport plus 12 px are sent to MapLibre; active counts and identities include all matching flights. World dots avoid unnecessary plane headings. Artwork is requested lazily; World airport code labels appear from zoom 4.5 with the existing collision handling, while hollow airport markers and station visibility remain available at wide zooms. Shared canvases avoid repeated context allocation. Existing views keep their label zoom policy and palettes.

The World board's airport picker searches exact code/name pairs without assembling route strings for every flight. Boards still offer departures, arrivals, destinations, fullscreen, pagination and previews. Events lie inside the half-open UTC window and display airport-local dates/times.

## Coverage limits

Existing views have different local capture dates and some include adjacent days while others do not. Late UTC departures in eastern time zones may require local 3 November captures that were never collected; early UTC departures in western time zones may require local 1 November captures. In-progress flights can also depend on earlier local captures. World retains every available overlapping flight, including the adjacent-day records counted above, and does not invent missing ones. The number of missing flights is unknown.

Each member's search/capture/route evidence remains independently inspectable under Overview → Collection evidence by source. Completion of an existing manifest does not establish full airport, country or global coverage. Additional dates and targeted adjacent-day collection remain separate future work.

## Validation

Final measurements and regression results are recorded in `PERFORMANCE_NOTES.md`. Raw timing samples, CPU profiles, preservation checks and screenshots remain under ignored `.cache/world-flights/`. No PR, merge or deployment is part of this change.
