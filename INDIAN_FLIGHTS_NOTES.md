# Indian flights

Bismillah, **India · Flights** adds domestic and international flight schedule captures for **2 November 2026**, with captured **USD** fares. Domestic opens first; use **Domestic / International / Both** to change scope. India’s transport views stay separate.

Airline and exact airport-code filters apply to the map, airport boards and frequency lines. Airport selection hides unrelated traffic. Departures, arrivals, Destinations, fullscreen pagination, flight previews, explicit seeking, five themes and English/Indonesian reuse the shared flight explorer. Plane paths illustrate scheduled travel; they are not recorded tracks.

## Clock and airport identity

The timeline is midnight to midnight in **Asia/Kolkata (IST, UTC+5:30)**. Airport boards show their own local time and the replay window in local dates. Domestic searches include 1 November to retain overnight carry-ins. International searches include each origin-local date that can overlap the Indian day for a flight up to 24 hours. Only dated departures and arrivals with source-validated durations are retained. Boards own events in the half-open selected day; a flight crossing midnight can remain visible in motion on both days without duplicating a board event.

**BOM/NMI**, **DEL/DXN** and **GOI/GOX** are separate identities, coordinates and exact-airport queries. City labels never silently substitute one for another. Coordinates use the existing pinned OurAirports snapshot; zones use the pinned OpenFlights source with IATA/ICAO matching, verified existing country catalogues, and explicit Asia/Kolkata for Indian airports. Modern foreign-airport zones have explicit overrides.

## Route candidates and sources

The search manifest contains **1,632 domestic directions across 127 Indian airport identities** and **908 international directions across 140 airport identities**. Both directions are searched. This is a candidate list, not a claim that every route currently operates or is nonstop.

- Domestic and international 2026 city pairs with positive reported passenger traffic come from the [DGCA/Ministry-derived community dataset](https://github.com/Vonter/india-aviation-traffic/tree/e197170f131e43169620e4f8aa520350d4cbcba9). The mirror is pinned to that commit and each CSV is SHA256 checked. It is statistical search evidence, **not an official current timetable**. The upstream authorities are [DGCA](https://www.dgca.gov.in/) and the [Ministry of Civil Aviation](https://www.civilaviation.gov.in/).
- [Air India’s March 2026 international map](https://www.airindia.com/content/dam/air-india/newsroom/press-kits/pdfs/Air-India-International-Route-Map-March-2026.pdf) supplies additional exact-airport candidates. Its listed routes do not establish service on the selected date.
- [Abu Dhabi Airports’ August 2026 announcement](https://www.adairports.ae/en/pressrelease/2026/08/air-india-express-expands-network-at-zayed-international-airport) adds NMI/IDR/LKO/GAU–AUH candidates. Air India Express’s Navi Mumbai destination page supplies DXB/BKK probes (which may include connections). [Noida’s destination directory](https://www.niairport.in/en/passengers/fly/flightinformation/destinations) cross-checks DXN candidates.
- Reciprocal India pairs from the Gulf, Singapore, Malaysia, Indonesia and Australia manifests cover Indian and foreign carriers. Explicit domestic validation probes include regional links such as COK–AGX and GAU–TEI; [Alliance Air’s schedule](https://plone.allianceair.in/allianceair/en/pages/schedule) supplies background for those regional candidates, not invented dated timings.
- Ambiguous international statistical labels expand into separate airport candidates: Goa GOI/GOX, London LHR/LGW, Moscow SVO/DME/VKO and Tokyo HND/NRT. Empty exact-airport results mean **not returned**, never “no service”. Foreign-to-foreign statistical rows are excluded and listed in the international manifest.

The statistical inputs cover **January–July 2026 domestically** and **Q1–Q2 2026 internationally**. Later official announcements supplement those candidates; only the dated November captures establish retained flights.

The domestic source names **Mundra, Pithoragarh and Purnea** cannot be resolved safely in the pinned airport catalogue. They remain documented unresolved gaps. No nearest-airport replacement is made. Regional services absent from Google Flights also remain gaps; there is no frequency-only schedule adapter or fabricated timing.

The manifests retain per-pair evidence, source URLs, source hashes, candidate year and review date. Route hashes cover the original pinned CSV bytes; supplements are retained explicitly in the evidence list.

## USD fares and reuse

Every new query requests **USD, one adult, economy, one-way**. The displayed context must be verified before assigning a price. Each exact dated flight receives its cheapest positive returned single-flight quote; connecting itinerary totals and page-wide minima are excluded. Missing or uncertain quotes display **Price unavailable**. Optional baggage and charges can cost extra. These are dated captured quotes, not live fares.

Compatible full origin-local day captures are reused from the Gulf and Singapore caches only when their exact query/date belongs to India’s manifest and their query and retained fare context are USD. Original timestamps and fare diagnostics stay intact. The records are filtered afresh against the Indian replay window. Existing MYR captures and unpriced queries without verified USD query currency are not relabelled or converted.

Repeated exact source identities are deduplicated; distinct flight numbers stay separate even at the same times. Codeshares are not inferred. Unknown aircraft stay unspecified. The loader rejects conflicting airport/flight identities, unrelated foreign-to-foreign flights, wrong scope and non-USD quotes.

## Rebuilding and local storage

```sh
.venv/bin/python scripts/prepare_indian_flight_airports.py
# Validate busy, regional, new-airport and long-haul routes first:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_indian_flights.py --validate-only
# Resume both scopes, at most two concurrent searches:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_indian_flights.py
# Rebuild deterministic gzip bundles from cached captures without searching:
.venv/bin/python scripts/prepare_indian_flights.py --prepare-only
```

Use `--scope domestic` or `--scope international` for one scope. The shared `prepare_google_flights.py --country IN --scope ...` CLI is also supported. Existing Australian defaults and Malaysian MYR behavior remain unchanged.

Raw normalized captures live in ignored `.cache/google-flights-india/` and `.cache/google-flights-india-international/`. Pinned candidate inputs live in `.cache/india-flights-audit/`. These caches are resumable; deleting them means re-downloading or re-searching to rebuild. The app only reads the compact `data/reference/india_flights/2026-11-02.json.gz` and `2026-11-02-international.json.gz` bundles. It makes no flight searches at runtime. HTTP replay payloads are separately regenerated in the ignored replay cache.

Access challenges stop collection without retrying the challenge. Successful captures remain available. The bundles report planned/searched/returned routes and airports, failed and unattempted queries, source timestamps and unresolved source airports. Query completion never means nationwide flight completeness.

## Captured coverage for 2 November 2026

These are overlapping scheduled flight identities within the Indian replay day, including carry-ins and flights continuing beyond midnight. They are not a nationwide completeness claim. All planned queries were captured; there were no failed or unattempted queries and no rejected source timing records.

| Measure | Domestic | International |
| --- | ---: | ---: |
| Candidate directions | 1,632 | 908 |
| Directions searched | 1,632 | 908 |
| Directions with retained flights | 886 | 558 |
| Planned origin-local date queries | 3,264 | 2,259 |
| Captured queries | 3,264 | 2,259 |
| Queries not returning direct flights | 1,507 | 948 |
| Overlapping flights | 3,102 | 1,395 |
| USD fares | 2,846 | 1,288 |
| Unavailable fares | 256 | 107 |
| Returned airports | 103 | 107 |
| Queries with unverified fare context | 6 | 7 |

Combined: **4,497 flights**, **180 airports** (103 Indian and 77 overseas), **4,134 USD fares**, and **363 unavailable prices**. The two deterministic bundles total **478,431 bytes (467.2 KiB)**. No prices are assigned from queries whose fare context is unverified.

Domestic capture timestamps span **25 October 2026, 04:35–05:44 UTC**. International timestamps span **24 October 2026, 23:38 UTC – 25 October 2026, 06:24 UTC**, including **350 reused USD captures**. Per-query and per-price timestamps remain in the bundles.

### Geographic audit

The grouping below is for this coverage audit. Domestic flights touching two groups appear in both rows; those flight counts are not additive. An airport not returned for this day is a coverage gap, not proof of no service.

| Group | Domestic candidate airports | Domestic airports returned | Domestic flights touching group | International Indian gateways returned |
| --- | ---: | ---: | ---: | ---: |
| North | 25 | 20 | 1,339 | 5 |
| West | 34 | 26 | 1,462 | 8 |
| Central | 10 | 7 | 182 | 1 |
| East | 15 | 10 | 616 | 3 |
| Northeast | 14 | 13 | 182 | 1 |
| South | 27 | 25 | 1,458 | 12 |
| Islands | 2 | 2 | 38 | 0 |

Domestic candidate airports not represented in retained flights: **AHA, AVR, BUP, COH, GDB, HSS, IXK, IXW, IXX, IXY, JGB, KJB, KQH, KUU, LUH, NMB, PAB, PBD, PYB, RRK, RUP, SDW, SLV, UKE**. The additional unresolved source names are **Mundra, Pithoragarh and Purnea**. Smaller regional schedules remain a material gap, even where a query completed successfully.

## Validation

The final run passed **142 Python tests** covering India, all existing flight countries, replay HTTP caching/date rejection, international/overnight clocks, cheapest exact-flight fares, and Melbourne/transit behavior; **87 JavaScript tests** passed. Browser validation covered domestic/international/both, isolated NMI/DXN/GOI/GOX traffic, IST in English and Indonesian, London local-time boards, USD previews without implicit seeking, fullscreen/back, arrivals, Destinations pagination, airline/airport filters, frequency counts, all five themes and mobile layout. Desktop and mobile screenshots were inspected.

Both pinned manifests and both gzip bundles rebuilt **byte for byte** from cached inputs. Replay cache format **12** regenerates existing responses with the shared Indian airline colour presets. Australian legacy CLI defaults, existing snapshots and Malaysian MYR pricing remain unchanged.
