# North America flights: US 30 + Canada 5 + Mexico 5

This single explorer covers domestic and cross-border nonstop flights between forty exact airports, departing **2 November 2026 in each origin airport's local time**, with all returned airlines. **All captured fares use USD**, including Canadian and Mexican domestic flights. Paths are illustrative and fares are captured quotes rather than live availability.

## Selection and sources

The US thirty remain the [FAA final CY2025 top thirty by passenger boardings](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx). Canada uses the latest reviewed [Transport Canada national table's 2024 enplaned/deplaned revenue passenger counts](https://tdih-cdit.tc.canada.ca/en/addendum-tables/2024/table-a14-top-20-busiest-canadian-airports-terms-enplaneddeplaned-revenue-0). Mexico uses [SICT's preliminary 2025 total passenger ranking, PDF pages 32–33](https://micrs.sct.gob.mx/images/DireccionesGrales/DGP/estadistica/Principales-Estadisticas/PE_2025.pdf). These are separate national selections with different published metrics, not a uniform continent-wide top forty ranking.

| Country | Rank | Airport | IANA identity | Dated board offset |
| --- | ---: | --- | --- | --- |
| CA | 1 | YYZ | America/Toronto | UTC-5 |
| CA | 2 | YVR | America/Vancouver | UTC-7 |
| CA | 3 | YUL | America/Toronto | UTC-5 |
| CA | 4 | YYC | America/Edmonton | UTC-6 |
| CA | 5 | YEG | America/Edmonton | UTC-6 |
| MX | 1 | MEX | America/Mexico_City | UTC-6 |
| MX | 2 | CUN | America/Cancun | UTC-5 |
| MX | 3 | GDL | America/Mexico_City | UTC-6 |
| MX | 4 | MTY | America/Monterrey | UTC-6 |
| MX | 5 | TIJ | America/Tijuana | UTC-8 |

The normalized, reviewed Canadian and Mexican selection is committed in `data/sources/north_america_airport_selection.json`, with source URLs, years, metrics, ranks and time-zone evidence. Its SHA256 is included in the generated route manifest. The Canadian source PDF has its own byte hash; Mexico's hash basis is the committed normalized facts, not an unrecorded raw PDF hash. Airport names, coordinates, countries and ICAO identifiers use the existing immutable OurAirports CSV pin. MEX is separate from NLU/TLC; YYZ is separate from YTZ. Those secondary airports are outside this selection. JFK/EWR/LGA, IAD/DCA/BWI and SAN/TIJ remain separate too.

## Scope and search policy

There are **40 × 39 = 1,560 directional airport/date queries**: **910 domestic candidates** (870 US, 20 Canadian, 20 Mexican) and **650 cross-border candidates** (300 US–Canada, 300 US–Mexico, 50 Canada–Mexico). Each query includes all returned airlines. These are search candidates, not proof of service.

Only the origin-local departure date of **2 November** is queried. The expansion reuses the **870 earlier US captures and 7,178 flight records unchanged**, adding **690 new unique directions**. Six new pilots belong to those 690 and are reused by bulk collection. Two concurrent searches remain the maximum. Successful captures are resumable; challenges stop collection without bypasses. No paid source, live tracking, automatic refresh, invented schedules or additional dates.

Quotes retain their source capture timestamp and page hash. Existing fare parsing selects the cheapest verified USD quote for each exact flight, for one adult, economy, one-way. Missing or unverified fares remain **Price unavailable**. No CAD/MXN amounts are relabelled or converted to USD. Distinct flight numbers remain distinct; codeshares are not inferred from matching times.

## Replay and filters

The location is now **North America · Flights**, opening on **Both**. **Domestic** means both endpoints are in the same country, including Canada–Canada and Mexico–Mexico. **International** means different endpoint countries. Existing From country / To country selectors combine with airline/code, exact-airport and traffic-direction filters. Coverage summaries distinguish the selected domestic/international scope. Airport boards, Destinations, fullscreen pagination, flight previews, explicit seeking, station visibility and frequency lines are reused. The initial map includes Hawaii, the selected Canadian airports and Mexico.

The clock uses Eastern time; airports show local dates and times. The timeline extends through the final overnight arrival so late local 2 November departures remain visible. The 16-hour ceiling admits long Hawaii routes and retains source-duration validation. Other domestic profiles retain their previous limits.

### November 2026 Canadian clock changes

[B.C. remains at UTC−7](https://www2.gov.bc.ca/gov/content/governments/celebrating-british-columbia/daylight-saving-time) and [Alberta remains at UTC−6 from November 2026](https://www.alberta.ca/albertas-new-time-system-abt). Vancouver, Calgary and Edmonton preserve their IANA geographic identities and carry separate, validated fixed replay zones for this dated snapshot. Collection, local-day validation, board clocks and flight previews use those dated offsets even on machines or browsers with older time-zone databases. Toronto and Montreal use America/Toronto; Cancun remains UTC−5, central Mexican airports UTC−6 and Tijuana follows border DST (UTC−8 on this replay date).

## Preparation and compatibility

Historical internal identifiers remain compatible: city `united_states_flights`, `scripts/prepare_us_flight_airports.py`, `scripts/prepare_us_flights.py`, `data/sources/united_states_flights_routes.json`, `data/reference/united_states_flights/2026-11-02.json.gz`, `SUNTRAIN_UNITED_STATES_FLIGHTS_REFERENCE`, and `.cache/google-flights-us-usd-v1/`. The user-facing name and metadata describe the regional scope. This standalone explorer does not expand or modify the separate shared International network's route inventory or archived records.

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flight_airports.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --dry-run
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --validate-only
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --prepare-only
```

Preparation from cached captures is deterministic gzip (`mtime=0`). Removing capture caches requires fresh public searches; removing the airport-data caches requires re-downloading the pinned FAA workbook and OurAirports CSV. The reviewed CA/MX selection facts are committed and do not require live site access to rebuild the manifest.

## Captured coverage

| Measure | Result |
| --- | ---: |
| Airports planned / searched / returned | 40 / 40 / 40 |
| Unique directional queries | 1,560 |
| Directions returning flights | 1,169 |
| Directions not returned | 391 |
| Failed or missing queries | 0 |
| Retained flight identities | 8,838 |
| Verified USD quotes | 8,740 |
| Price unavailable | 98 |
| Unverified fare-context queries | 3 |

| Country pair | Queries | Directions returning flights | Records | USD fares |
| --- | ---: | ---: | ---: | ---: |
| US → US | 870 | 792 | 7,178 | 7,178 |
| US → CA | 150 | 86 | 305 | 305 |
| US → MX | 150 | 72 | 209 | 201 |
| CA → US | 150 | 86 | 303 | 303 |
| CA → CA | 20 | 20 | 289 | 289 |
| CA → MX | 25 | 10 | 31 | 31 |
| MX → US | 150 | 71 | 201 | 191 |
| MX → CA | 25 | 12 | 35 | 35 |
| MX → MX | 20 | 20 | 287 | 207 |

| Carrier | Code | Records |
| --- | --- | ---: |
| American | AA | 2,101 |
| Delta | DL | 1,776 |
| United | UA | 1,710 |
| Southwest Airlines | WN | 852 |
| Air Canada | AC | 436 |
| Frontier Airlines | F9 | 411 |
| JetBlue | B6 | 393 |
| Alaska Airlines | AS | 390 |
| Aeromexico | AM | 174 |
| WestJet | WS | 162 |
| Volaris | Y4 | 137 |
| Viva | VB | 137 |
| Porter Airlines | PD | 63 |
| Flair Airlines | F8 | 44 |
| Sun Country Airlines | SY | 35 |
| Air Transat | TS | 6 |
| Breeze Airways | MX | 4 |
| JSX | XE | 4 |
| Allegiant Air | G4 | 2 |
| Air North | 4N | 1 |

The 690 new directions initially had 335 empty captures. A single bounded pass rechecked only the 31 new directions whose reverse query returned flights, recovering 93 records across 22 directions. That is **721 new page requests** across **690 new unique queries**. Earlier captures were not repeated or modified. The retained-query capture range is **2026-10-26T22:00:11.634536+00:00–2026-10-26T23:19:28.047211+00:00 UTC**. Original empty responses, rechecks and logs remain under `.cache/us-flights-audit/`.

Empty responses mean **not returned**, not no service. Query completion does not prove all flights on a direction were captured; an entire direction or individual flight/fare can be missing. The earlier SFO → EWR gap remains unchanged. Directions outside the forty-airport catalogue, connecting itineraries, flights departing on other local dates and routes to other countries remain outside this release. No timings, prices or codeshares are invented. Record totals refer to returned flight identities, not guaranteed physical-aircraft totals.

The replay window is **2026-11-02T05:00:00+00:00 → 2026-11-03T15:41:01+00:00**, including every captured departure and arrival. Archive size is **401,256 bytes**; SHA256 **`f5e117132b590bfa6c3e7b4d32142e32230811fcc89fc9ed6ee8f610a90a1165`**. Rebuilding from the retained capture cache is byte-for-byte identical.

## Verification

The Python flight, international-network, replay, HTTP and translation regression suite passed **288 tests** before final targeted checks. The final focused suite passes **22 tests**, including foreign domestic/cross-border classification, USD-only fare validation, lowest returned quote selection, frozen Canadian offsets, Mexican border time, source-time validation, overnight flights, exact airports, partial-query coverage, compressed HTTP caching and date rejection. JavaScript passes **102 tests**, including fixed November Canadian clock formatting.

Browser checks cover all forty airport boards, every returned carrier, all three scopes, CA → CA / MX → MX domestic USD fares, cross-border country pairs, exact airport/direction filtering, fixed Vancouver/Alberta board offsets, departures/arrivals/Destinations, fullscreen pagination and back behavior, flight previews and explicit seeking, frequency totals, station visibility, themes, Indonesian and 390px mobile layout. Australia flights and Melbourne transit still load with their original windows. Previous US queries, flight records, airport identities and unrelated working files are preserved.
