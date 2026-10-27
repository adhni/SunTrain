# Americas flights

## Search strategy

The existing views cover 50 North American, Central American and Caribbean airports and 27 South American airports. Searching every cross-region pair in both directions would add **2,700 queries**.

The new connection shortlist has **169 airport pairs / 338 directional queries**, avoiding **2,362 searches (87.5%)**. Every southern airport has a recorded discovery review, including airports with no in-scope candidates. Search each direction once for **2 November 2026 in its origin's local time**, requesting all airlines, nonstop, one adult, economy, one-way, **USD**. No extra dates or airline-by-airline searches.

The **Americas · Flights** view combines those captures with both unchanged regional references: **3,152 existing query results and 11,297 existing flight records** are reused offline. North America and South America remain independent views with their original archives. The combined search plan contains **3,490 directions**, rather than all ordered pairs among 77 airports.

## Discovery evidence and limits

Normalized reviewed facts and source URLs are committed in `data/sources/americas_route_evidence.json`. They generate `americas_connections_routes.json` and `americas_flights_routes.json`. Hashes identify those committed facts and the original regional manifests/snapshots; they are **not hashes of original webpage bytes**. Web-tool text extracts remain locally in `.cache/americas-routes/`; raw HTML was not pinned. Direct HTTP reads of some sources were denied and were not retried around access controls.

Official sources include [Panama's direct-flight airport list](https://es.tourismpanama.com/planea-tu-viaje/llegar-aqui/vuelos-directos-america-del-sur/), [San José's airport connectivity list](https://www.sjoairport.com/conectividad/) and [Ecuador's aviation authority on UIO–Mexico City](https://www.aviacioncivil.gob.ec/ecuador-y-mexico-retoman-conexiones-aereas/). The Panama list names exact airports; do not substitute BLB for PTY. San José's airport list adds SJO–CTG to the directory-derived candidates.

Public **FlightConnections** nonstop destination pages supplement those official lists, with a separate source URL for each of the 27 southern airport reviews. They are secondary route-discovery sources, not proof of replay-day service. Only the relevant nonstop sections were reviewed; connecting-destination recommendations are excluded. Seasonal candidates remain eligible when their exact start date is unclear; clearly later starts **GRU–YYC** and **SCL–DFW** are excluded. Both reverse directions are search candidates, not inferred scheduled services.

**CGH, SDU, AEP and CWB** have no cross-region candidates in the reviewed lists. They remain available in the combined view through their existing regional captures. Never copy GRU/VCP routes onto CGH, GIG routes onto SDU, EZE routes onto AEP, or JFK routes onto LGA. PBM–MIA is not added from an itinerary via GEO. Out-of-scope airports, cargo, connecting itineraries and general city-pair marketing offers are excluded.

The shortlist can miss new, omitted or directional routes. Reviewing all 27 airports is not evidence of nationwide or Americas-wide flight completeness. Empty search results mean **not returned**, never **no service**. Future additions require source evidence rather than expanding to a Cartesian airport matrix.

## Capture and replay

Two concurrent searches, resumable atomic captures, source timestamps/page hashes and stop-on-challenge behavior reuse the shared collector. Cache: `.cache/google-flights-americas-usd-v1/`. A dry run rejects incompatible cached route/date/currency identities rather than silently reusing them. No paid source, live tracking, automatic refresh or invented timings.

Prepared reference: `data/reference/americas_flights/2026-11-02.json.gz`. Timeline: **UTC**, covering all origin-local departures and overnight arrivals. Airport boards retain their local clocks, including the existing dated Canadian replay-zone configuration. The regional duration limit is 16 hours; other views retain their limits. Cheapest verified returned USD quote per exact flight, with missing prices explicitly unavailable. Distinct source flight numbers are retained without inferred codeshare merging.

The existing map, airline/code filters, exact-airport filter, From/To countries, Domestic/International/Both, departures/arrivals, Destinations, fullscreen/back, frequency lines, station toggle, themes and Indonesian copy are reused. Puerto Rico remains selectable separately and mainland US–Puerto Rico flights retain domestic classification. Initial map bounds cover all 77 airports; arcs remain illustrative.

Preparation reconstructs regional captures **only in a temporary directory** from the pinned archives, adds the new cached cross-region captures, and publishes a deterministic gzip atomically. It does not copy or modify existing capture caches. Deleting the new cache requires recollecting those searches; the committed regional archives are sufficient for offline reuse.

```bash
.venv/bin/python scripts/prepare_americas_routes.py --dry-run
.venv/bin/python scripts/prepare_americas_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_americas_flights.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_americas_flights.py
.venv/bin/python scripts/prepare_americas_flights.py --prepare-only
```

`SUNTRAIN_AMERICAS_FLIGHTS_REFERENCE` overrides the combined archive for testing. The existing shared International network's footprint is unchanged.

## Validation

Tests cover sourced candidate provenance, exclusions, exact airport identities, fixed search budgets, one-date queries, USD cache identity, inherited Canadian clocks, long overnight flights, missing/failed queries, original-record preservation, reproducible preparation, compressed HTTP caching and invalid dates. Browser checks exercise cross-region country filters, airline filters, all 77 exact-airport departure/arrival boards, Destinations, fullscreen/back, USD previews without implicit seeking, frequency counts, themes, Indonesian and mobile layout, with existing regional/Australian/Melbourne smoke checks.

## Capture results

All **338** planned cross-region queries were captured: **225** directions returned flights and **113** returned no matching records. **486** cross-region flights across **23 carriers**, with **479 verified USD prices** and **7 unavailable prices**. **Zero failed/missing queries and zero rejected records.** These are dated results, not a claim that every published route operates daily.

The combined archive contains **11,783 flights**, **43 carriers**, **11,643 verified USD prices** and **140 unavailable prices**, across **77 airports / 24 country or territory entries**. All **11,297** original regional records are preserved exactly. Six inherited regional query pages have an unverified fare context; their valid dated schedules are retained without unverified prices.

New captures run from **2026-10-27 05:08:32 UTC** to **05:16:12 UTC**. The archive is **640,706 bytes** (about **626 KiB**) with deterministic SHA256 `2f05ef2b38e7230132a4d81865ad1b13e2c8677c749a9cb46f6b2defa7c855be`.

The table counts only the **new cross-region captures**, grouped by their southern endpoint. Each flight appears once. Zero planned directions means no in-scope candidate in the reviewed lists; zero returned flights means none captured for that shortlist/date. Existing regional services remain available for these airports.

| Southern airport | Directions searched | Directions returning flights | Flights | USD prices |
| --- | ---: | ---: | ---: | ---: |
| AEP | 0 | 0 | 0 | 0 |
| ASU | 2 | 2 | 4 | 4 |
| BOG | 54 | 44 | 125 | 125 |
| BSB | 6 | 6 | 6 | 6 |
| CCS | 10 | 4 | 7 | 5 |
| CGH | 0 | 0 | 0 | 0 |
| CLO | 12 | 7 | 17 | 17 |
| CNF | 4 | 2 | 3 | 3 |
| CTG | 26 | 9 | 19 | 19 |
| CWB | 0 | 0 | 0 | 0 |
| EZE | 22 | 6 | 17 | 17 |
| FOR | 4 | 0 | 0 | 0 |
| GEO | 8 | 7 | 10 | 10 |
| GIG | 16 | 8 | 14 | 14 |
| GRU | 34 | 29 | 57 | 57 |
| LIM | 36 | 30 | 75 | 71 |
| MDE | 34 | 26 | 57 | 57 |
| MVD | 6 | 2 | 6 | 6 |
| PBM | 6 | 1 | 1 | 0 |
| POA | 2 | 2 | 2 | 2 |
| REC | 2 | 0 | 0 | 0 |
| SCL | 22 | 17 | 28 | 28 |
| SDU | 0 | 0 | 0 | 0 |
| SSA | 2 | 2 | 2 | 2 |
| UIO | 22 | 14 | 28 | 28 |
| VCP | 4 | 4 | 4 | 4 |
| VVI | 4 | 3 | 4 | 4 |

GEO now contributes **10** cross-region flights and PBM **1**; their separate South America-only snapshot remains unchanged. FOR and REC returned no cross-region flights on the searched date.


Final automated validation: **300 Python regressions passed**, **105 JavaScript tests passed**. Offline cached preparation reproduced the committed gzip byte-for-byte; a repeat dry run reports **338 reusable cross-region captures / zero new searches**.

Browser validation passed for all **77 exact-airport boards**, both traffic directions, cross-region country and airline filters, Domestic/International/Both, fullscreen pagination/back, USD fare previews, Destinations, frequency counts, all five themes, Indonesian and 390px mobile layout. Existing North America (9,668 services), South America (1,629), Australia flights and Melbourne transit smoke checks passed. Screenshots and logs are retained under `.cache/americas-flights-audit/`.
