# US domestic flights: top twenty airports

The US domestic snapshot captures nonstop flights departing **2 November 2026 in each origin airport's local time**, between twenty exact airports. It includes every returned airline without an airline filter. This is a dated schedule replay, with illustrative paths and captured fares, rather than live tracking.

## Airport selection

The [FAA's final CY2025 commercial-service passenger boarding ranking](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx), updated 24 September 2026, supplies the top twenty. This ranking counts **total passenger boardings**, including international passengers; it is not a domestic-only ranking.

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
| 11 | CLT | 25,873,555 | America/New_York |
| 12 | SEA | 25,417,071 | America/Los_Angeles |
| 13 | PHX | 25,094,817 | America/Phoenix |
| 14 | EWR | 23,464,492 | America/New_York |
| 15 | IAH | 23,265,028 | America/Chicago |
| 16 | BOS | 21,021,153 | America/New_York |
| 17 | MSP | 17,488,261 | America/Chicago |
| 18 | DTW | 16,294,768 | America/Detroit |
| 19 | LGA | 16,278,532 | America/New_York |
| 20 | FLL | 15,646,752 | America/New_York |

Coordinates, names and ICAO identifiers use the existing pinned OurAirports CSV. Exact IATA identities remain separate: JFK does not include EWR/LGA, ORD does not include MDW, DFW does not include DAL, and LAX/SFO do not include nearby airports.

`scripts/prepare_us_flight_airports.py` verifies the pinned FAA workbook SHA256 and OurAirports SHA256, resolves unique active US airports, assigns explicit time zones, and deterministically generates `data/sources/united_states_flights_routes.json`. The manifest contains the ranking, source hashes and all **20 × 19 = 380 directional candidate pairs**. The ranking is selection evidence, not evidence that a route operates.

## Captured coverage

| Measure | Result |
| --- | ---: |
| Airports planned / searched / returned | 20 / 20 / 20 |
| Unique directional airport/date queries | 380 |
| Directions returning flights | 361 |
| Directions with no matching returned flights | 19 |
| Missing, failed or rejected queries | 0 |
| Retained flight identities | 4,179 |
| Flights with verified USD quotes | 4,179 |
| Unverified fare contexts | 0 |

| Returned carrier | Code | Records |
| --- | --- | ---: |
| American | AA | 1,168 |
| Delta | DL | 1,037 |
| United | UA | 984 |
| JetBlue | B6 | 276 |
| Frontier Airlines | F9 | 257 |
| Southwest Airlines | WN | 232 |
| Alaska Airlines | AS | 187 |
| Sun Country Airlines | SY | 32 |
| JSX | XE | 4 |
| Allegiant Air | G4 | 2 |

Final source captures span **2026-10-26T22:00:11.634536+00:00–2026-10-26T22:31:09.788134+00:00** (UTC). Each query retains its URL, capture timestamp, embedded-script SHA256 and status. The snapshot retains these fields and any missing-query diagnostics.

Only **one departure date** was searched. The top-twenty expansion reused all **90 original captures and 1,328 original flight records unchanged**, and collected **290 new directions**. One bounded pass rechecked **19 nonlocal empty directions**, recovering **91 records across eight directions**. The eight intra-metro New York and Miami/Fort Lauderdale probes were not repeated. One additional isolated SFO → EWR check still returned no matching records. This expansion made **310 new page requests** across **290 new unique queries**, with no extra dates. The earlier top-ten audit used 90 unique queries, six bounded rechecks and one diagnostic page visit. The collector uses two workers and waits for DOM readiness; no access challenge was encountered or bypassed.

The **19 directions not returned** are: EWR → JFK, EWR → LGA, FLL → MIA, JFK → EWR, JFK → LGA, LAS → LGA, LAX → LGA, LGA → EWR, LGA → JFK, LGA → LAS, LGA → LAX, LGA → PHX, LGA → SEA, LGA → SFO, MIA → FLL, PHX → LGA, SEA → LGA, SFO → EWR, SFO → LGA. These are source gaps, not assertions that no service exists. **SFO → EWR remains an explicit gap**, despite the reverse direction returning flights. Recheck captures, original empty responses and collection logs remain under `.cache/us-flights-audit/`.

All returned fares use the existing verified **one adult, economy, one-way, USD** parser, retaining the cheapest returned quote for each exact flight and its original capture timestamp. No currency conversion or inferred prices. Unknown aircraft remain unspecified. Duplicate source identities collapse; different flight numbers remain distinct, without inferring codeshares.

## Replay and limits

The replay uses **Eastern time**, with each airport board displaying airport-local dates and times. The twenty airports use six explicit IANA zones and four UTC offsets on 2 November: EST/CST/MST/PST. Phoenix uses America/Phoenix and does not observe DST; Detroit uses America/Detroit. The other selected airports follow the DST change on 1 November. The timeline starts at **2 November 00:00 EST** and extends through the final overnight arrival, ending **3 November 08:30:01 EST**. This includes every captured local 2 November departure and arrival without extra adjacent-day searches. It does not include flights departing locally on 1 November.

The US view reuses plane markers, station visibility, airline-code and exact-airport filters, selection arcs, Destinations, departures/arrivals, fullscreen pagination, flight previews, explicit seeking and frequency lines. US paths use the Americas world copy. It has no international scope selector and does not expand the shared international network's footprint or query manifest. Existing US international endpoints in the Taiwan/Hong Kong network remain valid.

Coverage is limited to these twenty airports. All other airports, connecting itineraries and international flights are excluded. A successful query is not proof that Google returned every scheduled flight or airline. Empty results mean **not returned**, not no service. Counts describe returned source flight identities, not guaranteed counts of physical aircraft. Captured fares can change and may have extra baggage/optional charges.

## Preparation

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flight_airports.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --dry-run
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --validate-only
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --prepare-only
```

Two concurrent public Google Flights searches are the default and maximum. Successful captures resume from `.cache/google-flights-us-usd-v1/`. Collection stops on access challenges, keeps completed captures, records the stop reason and prepares an explicitly partial archive. `--prepare-only` performs no searches. If caches are removed, the FAA workbook and pinned OurAirports CSV can be fetched again through the airport-preparation script; Google capture caches require fresh public searches. There is no automatic refresh or runtime flight search.

Archive: `data/reference/united_states_flights/2026-11-02.json.gz` (**159,286 bytes**).

SHA256: `57c79a05ef7cf26a6fa72151d75f25b3fbe54867eb0be79b73317a985d1b8d39`.

## Verification

The top-twenty Python flight, international-network, Melbourne replay, HTTP and translation regression suite passed **284 tests**, with the prepared-snapshot test deferred until collection completed. The final **19 targeted tests** include that prepared-snapshot check and the new JFK/EWR/LGA identity check. The existing JavaScript suite passed **101 tests** for the unchanged JS implementation. US-specific checks cover exact airports, all six IANA zones, four November UTC offsets and Phoenix summer/DST behavior, early Eastern and late Pacific departures, overnight arrivals, repeated and distinct flight identities, cheapest USD quotes, missing versus empty queries, invalid cached identity, incorrect national/time-zone identity, compressed HTTP caching and date rejection. Preparation from cached captures and the airport manifest rebuild are byte-for-byte reproducible.

The browser check exercises all twenty airport boards and all returned carrier filters, departure/arrival/Destinations modes, fullscreen pagination and preview/back behavior, USD prices, extended timeline, frequency totals, station visibility, themes, Indonesian translation and a 390px mobile viewport. It also checks Australia flights and Melbourne transit still load with their original 24-hour windows.
