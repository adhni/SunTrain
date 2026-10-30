# Argentina, Peru and Chile domestic expansion

Bismillah, this pass used **200 new Google Flights searches**, reviewed after each 50, plus **two reusable USD captures**. It adds **909 dated domestic flights** to South America · Flights. Of these, **793 are new identities overlapping World’s UTC day**. World now contains **57,024 flights: 28,691 domestic and 28,333 international**.

| Country | New searches | Reused | Positive directions | Empty directions | Captured flights | With USD fares | New in World |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Argentina | 126 | 0 | 95 | 31 | 355 | 288 | 326 |
| Peru | 44 | 0 | 39 | 5 | 315 | 247 | 254 |
| Chile | 30 | 2 | 29 | 3 | 239 | 187 | 213 |
| Total | **200** | **2** | **163** | **39** | **909** | **722** | **793** |

All 202 query slots have a validated capture. There are **zero failed, rejected or missing queries**. Empty means “not returned,” never proof of no service. Prices are captured one-way economy fares for one adult in USD; the existing parser selects the cheapest compatible returned offer for an exact dated flight. No currency conversion or invented prices.

South America now has **2,538 flights and 99 selectable airports**, retaining all 1,629 original records and all 27 original airports. The additions return flights at **69 airports**: 34 in Argentina, 19 in Peru and 16 in Chile. World has **17,761 directional routes**, 1,577 airports with returned flights and 1,849 catalogue airports. These remain partial collections.

## Selection and remaining gaps

Published airport route maps supplied search candidates; they were not treated as dated flight evidence. Exact IATA pairs were filtered to domestic Argentina, Peru and Chile, with existing South America queries excluded and verified USD caches reused. No Cartesian airport-pair sweep or multi-day sweep was performed. Two concurrent searches and a durable attempt journal enforce the 200-search cap, including failed or interrupted navigations.

Successful discovery maps were AEP, EZE, LIM, SCL and CUZ. Requests for COR, MDZ, BRC, AQP, ANF, PMC and PUQ route maps returned HTTP 404; their absence does not establish a lack of service. Candidates connecting those airports can still appear in the successful hub maps. RLO and MZA could not be resolved to verified exact airport/timezone identities; their four candidate directions were omitted. All 202 resolvable, new directions from this particular discovery set were either searched or reused. This is not a claim to have discovered every domestic route, especially regional flights not linked to these hubs.

Captures cover **departures on 2 November 2026 in each origin airport’s local time**, including overnight arrivals. South America retains that origin-local replay window. World keeps its existing **00:00–24:00 UTC** window and deduplicates exact identities. Some late local departures fall outside World’s UTC day. **No new previous-local-day captures were collected**, so early UTC-day coverage remains incomplete.

Chile uses reviewed explicit IANA regions: CPO/ZCO use America/Santiago, BBA uses America/Coyhaique, PUQ/PNT use America/Punta_Arenas, and IPC retains Pacific/Easter. The [IANA zone table](https://data.iana.org/time-zones/tzdb/zone1970.tab) distinguishes Aysén, Magallanes, Easter Island and mainland Chile. Current OurAirports identities for CPO and ZCO are retained instead of their superseded OpenFlights aerodromes.

## Reproduction and preservation

- Manifest, published route-map hashes, pinned airport evidence, attempts and scorecard: `data/sources/south_america_domestic.json.gz`.
- Additive prepared captures: `data/reference/south_america_domestic/2026-11-02.json.gz` (**53,346 bytes gzip**).
- Rebuilt World: `data/reference/world_flights/2026-11-02.json.gz` (**3,178,819 bytes gzip**).
- Existing South America and international expansion archives are unchanged. All **45 prior source-file hashes**, all **56,231 previous World flight identities**, their fare quotes, airport identities and source-ID provenance were checked for preservation. New domestic captures add a separately validated 46th World input; the international supplement's frozen original-input audit remains enforced.
- `scripts/prepare_south_america_domestic.py collect` resumes up to the next 50 attempts and refuses further searches after 200 or an access challenge. A missing/changed previously published raw capture fails preparation rather than erasing portable records.
- `scripts/prepare_south_america_domestic.py prepare` rebuilds from ignored raw caches with no network searches. `scripts/prepare_world_flights.py` uses the portable prepared archives; normal HTTP requests never collect flights.

Raw Google captures and route-map downloads remain under ignored `.cache/`. Preserve the committed portable archives and source manifest if clearing caches. Rebuilding the domestic layer from raw captures after deleting them would require a separately authorized new capture campaign; opening either replay does not.

## Validation

Final test results and local browser checks are recorded below. Logs, screenshots, intermediate scorecards and preservation evidence are under ignored `.cache/south-america-domestic/`.

**Passed:** 199 relevant Python tests, 78 JavaScript tests and the South America and World browser regressions. Python checks include deterministic byte-for-byte World preparation, input read-once behavior, preservation of the original 40-view union and pre-expansion World, exact route ownership, source hashes, USD fares, local dates, Chilean zones, durable checkpoint limits, HTTP compression/ETags/date rejection, translations and Melbourne replay compatibility.

South America browser validation covered all 27 original airports and eight representative added airports, all returned carriers, each new domestic country filter, departures/arrivals/destinations, fullscreen preview/back, overnight bounds, station visibility, frequency totals, all five themes, Indonesian/mobile layouts, and North America/Australia/Melbourne transitions. World additionally checked new domestic counts and Bariloche/Cusco/Balmaceda boards, global playback, dateline viewport transfer, palette/view transitions, captured quotes, coverage evidence and mobile. Both final browser runs exited normally with no page errors or shutdown failures.

One preservation test initially read the campaign scorecard while offline preparation was rewriting it and failed on a temporarily absent summary key; it passed independently after preparation completed. A newly added browser assertion initially used Buenos Aires as Bariloche's expected zone; the test was corrected to the catalogue's preserved `America/Argentina/Salta` zone, and the complete World browser rerun passed. No captured times or airport identities were changed to satisfy either test.

Warm local gzip HTTP responses measured **5,608,985 bytes for World** and **603,919 bytes for South America**. Three response-download samples were 26.36/13.00/9.31 ms and 7.13/5.91/5.14 ms respectively. These are cached localhost HTTP timings, not first-map, playback, hosted-network or physical-device benchmarks. World's transfer is **5.35 MiB**, above the original 5 MiB target and about 97 KiB larger than before this pass. No performance improvement is claimed.
