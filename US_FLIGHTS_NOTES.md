# US domestic flights: top ten airports

The first US flight snapshot captures nonstop flights departing **2 November 2026 in each origin airport's local time**, between ten exact airports. It includes every returned airline without an airline filter. This is a dated schedule replay, with illustrative paths and captured fares, rather than live tracking.

## Airport selection

The [FAA's final CY2025 commercial-service passenger boarding ranking](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx), updated 24 September 2026, supplies the top ten. This ranking counts **total passenger boardings**, including international passengers; it is not a domestic-only ranking.

| Rank | Airport | CY2025 boardings | IANA time zone |
| --- | --- | ---: | --- |
| 1 | ATL | 51,459,786 | America/New_York |
| 2 | DFW | 41,297,009 | America/Chicago |
| 3 | ORD | 40,680,735 | America/Chicago |
| 4 | DEN | 39,976,695 | America/Denver |
| 5 | LAX | 36,497,303 | America/Los_Angeles |
| 6 | JFK | 30,792,806 | America/New_York |
| 7 | MCO | 27,999,709 | America/New_York |
| 8 | LAS | 26,531,765 | America/Los_Angeles |
| 9 | MIA | 26,450,972 | America/New_York |
| 10 | SFO | 26,251,850 | America/Los_Angeles |

Coordinates, names and ICAO identifiers use the existing pinned OurAirports CSV. Exact IATA identities remain separate: JFK does not include EWR/LGA, ORD does not include MDW, DFW does not include DAL, and LAX/SFO do not include nearby airports.

`scripts/prepare_us_flight_airports.py` verifies the pinned FAA workbook SHA256 and OurAirports SHA256, resolves unique active US airports, assigns explicit time zones, and deterministically generates `data/sources/united_states_flights_routes.json`. The manifest contains the ranking, source hashes and all **10 × 9 = 90 directional candidate pairs**. The ranking is selection evidence, not evidence that a route operates.

## Captured coverage

| Measure | Result |
| --- | ---: |
| Airports planned / searched / returned | 10 / 10 / 10 |
| Unique directional airport/date queries | 90 |
| Directions returning flights | 90 |
| Missing, failed or rejected queries | 0 |
| Retained flight identities | 1,328 |
| Flights with verified USD quotes | 1,328 |
| Unverified fare contexts | 0 |

| Returned carrier | Code | Records |
| --- | --- | ---: |
| American | AA | 440 |
| United | UA | 280 |
| Delta | DL | 270 |
| Frontier | F9 | 117 |
| Southwest | WN | 111 |
| JetBlue | B6 | 68 |
| Alaska | AS | 38 |
| JSX | XE | 4 |

Final source captures span **26 October 2026, 22:00:11–22:06:11 UTC** (27 October in Melbourne). Each query retains its URL, capture timestamp, embedded-script SHA256 and status. The snapshot retains these fields and any missing-query diagnostics.

Only **one departure date** was searched. Three pilot directions were included in the 90, then reused. Five initially empty directions were rechecked once; four recovered. A separate ATL–DEN diagnostic returned 14 flights, and a final capture after DOM readiness recovered them. That is 90 unique queries, six bounded rechecks and one diagnostic page visit. The US collector now waits for `domcontentloaded` before reading the embedded schedule data; other collectors retain their existing setting. Original empty captures and diagnostics remain in `.cache/us-flights-audit/`; no access challenge was encountered or bypassed.

All returned fares use the existing verified **one adult, economy, one-way, USD** parser, retaining the cheapest returned quote for each exact flight and its original capture timestamp. No currency conversion or inferred prices. Unknown aircraft remain unspecified. Duplicate source identities collapse; different flight numbers remain distinct, without inferring codeshares.

## Replay and limits

The replay uses **Eastern time**, with each airport board displaying airport-local dates and times. On 2 November the four zones use EST/CST/MST/PST, following the DST change on 1 November. The timeline starts at **2 November 00:00 EST** and extends through the final overnight arrival, ending **3 November 08:30:01 EST**. This includes every captured local 2 November departure and arrival without extra adjacent-day searches. It does not include flights departing locally on 1 November.

The US view reuses plane markers, station visibility, airline-code and exact-airport filters, selection arcs, Destinations, departures/arrivals, fullscreen pagination, flight previews, explicit seeking and frequency lines. US paths use the Americas world copy. It has no international scope selector and does not expand the shared international network's footprint or query manifest. Existing US international endpoints in the Taiwan/Hong Kong network remain valid.

Coverage is limited to these ten airports. All other airports, connecting itineraries and international flights are excluded. A successful query is not proof that Google returned every scheduled flight or airline. Empty results mean **not returned**, not no service. Counts describe returned source flight identities, not guaranteed counts of physical aircraft. Captured fares can change and may have extra baggage/optional charges.

## Preparation

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flight_airports.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --dry-run
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --validate-only
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --prepare-only
```

Two concurrent public Google Flights searches are the default and maximum. Successful captures resume from `.cache/google-flights-us-usd-v1/`. Collection stops on access challenges, keeps completed captures, records the stop reason and prepares an explicitly partial archive. `--prepare-only` performs no searches. If caches are removed, the FAA workbook and pinned OurAirports CSV can be fetched again through the airport-preparation script; Google capture caches require fresh public searches. There is no automatic refresh or runtime flight search.

Archive: `data/reference/united_states_flights/2026-11-02.json.gz` (**44,804 bytes**).

SHA256: `933953160751141f1b8e175d033ea619e9965db6498e6e8bdc35fb5f3ba96f9e`.

## Verification

The existing Python flight, international-network, Melbourne replay, HTTP and translation regression suite passed **284 tests** before the final **18 targeted tests**. JavaScript passed **101 tests**. US-specific checks cover exact airports, all four zones after DST, early Eastern and late Pacific departures, overnight arrivals, repeated and distinct flight identities, cheapest USD quotes, missing versus empty queries, invalid cached identity, incorrect national/time-zone identity, compressed HTTP caching and date rejection. Preparation from cached captures and the airport manifest rebuild are byte-for-byte reproducible.

The browser check exercises all ten airport boards and all returned carrier filters, departure/arrival/Destinations modes, fullscreen pagination and preview/back behavior, USD prices, extended timeline, frequency totals, station visibility, themes, Indonesian translation and a 390px mobile viewport. It also checks Australia flights and Melbourne transit still load with their original 24-hour windows.
