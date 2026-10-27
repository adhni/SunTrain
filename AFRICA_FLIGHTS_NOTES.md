# Africa flights

This documents the original starter. The later [cached recovery and deferred-route expansion](AFRICA_EXPANSION_NOTES.md) adds domestic/regional depth while preserving the original records.

One independent **Africa · Flights** explorer for departures on **2 November 2026 in each origin airport’s local time**, including dated overnight arrivals. Domestic, intra-African and intercontinental services share the existing planes, airline/code and exact-airport filters, From/To countries, local airport boards, Destinations, fullscreen boards and frequency lines. The timeline is UTC. The starting map stays over Africa; **Fit selection** reaches overseas endpoints.

## Footprint and discovery

This is a geographically balanced starter, not an airport ranking or a claim to cover the continent:

| Area | Starter airports |
| --- | --- |
| North | CAI, HRG, SSH, CMN, RAK, AGA, ALG, TUN |
| West | LOS, ABV, ACC, DSS, ABJ |
| Central | FIH, DLA |
| East | ADD, BJR, NBO, MBA, DAR, ZNZ, EBB, KGL |
| Southern | JNB, CPT, DUR, GRJ, WDH |
| Indian Ocean islands | MRU, SEZ |

New domestic and intra-African searches stay within those 30 airports. Sourced international candidates from them can reach **any country**, not just existing SunTrain locations. Additional valid African captures already available locally are retained without expanding their searches. Canary airports remain labelled Spain; geographic proximity does not change country classification.

[Discovery facts](data/sources/africa_flights_discovery.json) pin exact destination labels and document hashes from public [Great Circle Pro airport maps](https://www.gcpromap.com/airports/jnb/). The inspected maps describe **July 2026–June 2027** schedules. They establish seasonal outbound candidates, not proof of a flight on 2 November. Reverse searches are candidates too; reverse operation is never inferred. Existing sourced SunTrain manifests supplement the maps. The discovery facts and [route manifest](data/sources/africa_flights_routes.json) record source URLs, input hashes and normalized candidate evidence; prepared query metadata records reused capture hashes.

The Google discovery/reuse stage supplied **1,927 directional candidates** in a 306-airport catalogue, rather than every airport pair. A final audit reused **105 additional dated Ryanair flights** from the pinned Europe archive, adding **94 archive-only directions and six airports** without new searches. The combined manifest has **2,021 directions and 312 airports**. Compatible captures supplied **422 query results**, including **394 directions returning flights**; only the remaining **1,505 queries** needed new collection. One exact-airport query includes every returned airline; no per-airline repetition or extra dates.

## Known discovery gaps

Dedicated Great Circle Pro pages/maps returned HTTP 404 for **AGA, DSS, ABJ, FIH, DLA, BJR, MBA, KGL, GRJ, WDH, MRU and SEZ**. They remain in the catalogue and receive sourced reverse-map/previous-manifest candidates where available. Their worldwide destination lists are **not complete**. Other missing/ambiguous exact airport identities or time zones are listed under `unresolved_airports`; their routes are omitted rather than guessed. African endpoints outside the starter are deferred unless an existing positive capture can be reused. Small commuter/charter flights and frequency-only schedules are not filled with invented times.

CAI/SPX retain separate exact identities, as do any other city airports. HLA is not substituted for JNB. Luanda is outside the new-search starter: neither LAD nor NBJ was returned by compatible reusable captures in this release. They are not silently exchanged. Future Luanda work must use the dated relocation notices: [Airlink moved to NBJ from 1 March 2026](https://www.flyairlink.com/news/airlink-luanda-new-airport), [Qatar moved from 5 December 2025](https://www.qatarairways.com/tradeportal/en-ae/news-updates/2025/Airport-Change-for-Luanda-Operations-LAD-to-NBJ.html), and [TAAG from 19 October 2025](https://flytaag.com/en/Info/Transfer-of-international-flights-to-AIAAN).

## Dates, clocks and fares

Airports use pinned OurAirports identities/coordinates and explicit, identity-matched OpenFlights IANA zones, supplemented by existing exact-airport manifests. Source URLs and hashes are committed. Source-local dated clocks must match the published duration; the Africa parser accepts one minute through 24 hours without changing other locations' limits. Flight IDs include source date, flight number and exact airports. Repeated identical IDs collapse; conflicting identities fail. Distinct flight numbers remain distinct, without invented codeshare relationships. Unspecified aircraft stay unknown.

Both Python and browser clocks were checked for the replay date. Cairo uses UTC+2; Morocco uses **UTC+0**, following its September 2026 change ([IANA](https://www.iana.org/time-zones), [Moroccan government notice](https://www.maroc.ma/en/news/morocco-return-gmt-time-starting-end-summer)). Do not assume Morocco still uses UTC+1 for this snapshot. Airport boards display local dates as well as times for overnight arrivals.

New quotes request **USD, one adult, economy, one way**, selecting the lowest returned verified offer for the exact nonstop flight. Reused EUR/USD/MYR quotes keep their original amount, currency, capture time and source context; no conversion or relabelling. A compatible source query is reused intact, selecting the latest compatible capture rather than mixing different schedule captures. Preparation also reads the pinned Europe archive in temporary staging. Overlapping official timetable identities keep the Google record, with no transfer of its fare to another timing record. Missing dated identities retain their official source URL, capture time and timestamps, and remain unpriced. Original Google statuses and source files are preserved separately from the combined coverage counts. Missing/unverified prices stay unavailable. Quotes are captured offers, not live prices, and optional baggage/charges can cost extra.

The shared **International network remains unchanged**. Adding Africa to that view later should project this archive explicitly, deduplicate overlaps and report UTC-window gaps; it must not run its older multi-day global collector.

## Preparation and resuming

```bash
# Discovery refresh only when intentionally reviewing public source changes:
.venv/bin/python scripts/discover_africa_flights.py

# Rebuild the sourced manifest from pinned discovery/catalogues and existing caches:
.venv/bin/python scripts/prepare_africa_routes.py

# Seed compatible captures and inspect the remaining one-date budget:
.venv/bin/python scripts/prepare_africa_flights.py --seed --dry-run

# Resume only missing routes; two concurrent browser searches, new quotes USD:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_africa_flights.py

# Offline deterministic rebuild after collection:
.venv/bin/python scripts/prepare_africa_flights.py --prepare-only
```

`PYTHONPATH` is only needed when Playwright is installed in the existing local browser-tools directory instead of the environment. The route builder requires the pinned OurAirports CSV in `.cache/australia-flights-audit/` and OpenFlights data in `.cache/gulf-flights-audit/`; their download URLs and expected SHA256 hashes are in the manifest.

Caches are resumable at `.cache/google-flights-africa-usd-v1/`. Original reused captures remain unchanged; their source paths and byte hashes accompany seeded records. New captures live in `new-usd/`, with a separate compatible parser/fare context, and are copied to the preparation cache on completion/stop. Access challenges stop collection without retries; successful captures and a stop reason remain available. Empty results mean **not returned**, never “no service.” Failed, rejected and unattempted queries are reported separately. The final reference is validated before atomic publication as deterministic gzip with `mtime=0` at `data/reference/africa_flights/2026-11-02.json.gz`.

## Captured coverage and validation

The prepared reference records exact query/source timestamps, capture hashes, queries reused, unreturned/missing/failed queries, rejected records, flight/price counts and separate domestic / intra-African / intercontinental totals. `coverage_by_african_region` reports North, West, Central, East and Southern Africa; Indian Ocean island countries are in East for these mutually exclusive country groups. Routes touching two African regions appear in both regional incidence totals, so regional rows must not be summed as unique flights. Nationwide or continental completeness is not implied by completing the candidate queries.

### Frozen snapshot

- **2,468 flight identities across 123 carrier codes**, on **1,112 directions**.
- **1,927/1,927 Google directional queries captured**: 422 reused, 1,505 newly collected. **917** Google queries did not return flights; eight of those directions have dated official timetable records in the reused archive.
- The official archive adds **105 flights** and **94 directions without a Google capture**. Its 95 overlapping identities keep the Google record. All **516** dated African-endpoint identities in the existing Europe snapshot are represented.
- Combined: **2,021 directional source captures**, **909** directions without returned flights, **zero** failed, rejected or unattempted queries/records.
- **211 airports returned flights** out of the 312-airport catalogue. All **65 African airports** in the catalogue returned a flight: the 30 starter airports plus 35 from reused captures, spanning **35 African country/territory codes**. This is not all African airports or countries.
- **2,183 flights have verified quotes**: **1,678 USD**, **504 EUR**, **1 MYR**. **285** have no verified price, including the 105 added official timetable records.
- **263,018 bytes / about 257 KiB gzip**. Offline preparation was repeated byte-for-byte, SHA256 `c3d262fbf264ef34f5cd9b42e4c6d5f84f84e9aa7922be37c6930d3e53e240c3`.

| Capture bucket | Flights | Directions | Priced flights |
| --- | ---: | ---: | ---: |
| Domestic | 445 | 29 | 324 |
| Intra-African | 265 | 115 | 228 |
| Intercontinental | 1,758 | 968 | 1,631 |

| African region | African airports returned | Directional source captures | Directions returning flights | Directions not returning flights | Flights touching region |
| --- | ---: | ---: | ---: | ---: | ---: |
| North | 26 | 1,412 | 710 | 702 | 1,449 |
| West | 11 | 182 | 104 | 78 | 210 |
| Central | 7 | 43 | 25 | 18 | 28 |
| East, including Indian Ocean islands | 16 | 392 | 246 | 146 | 541 |
| Southern | 5 | 128 | 93 | 35 | 347 |

Regional flight/query rows overlap for cross-region African routes. Central Africa is especially sparse, and the 12 dedicated discovery-map gaps remain. Query completion does not establish nationwide or continental completeness.

Validation: offline source/date/identity/currency/overnight/short-duration/missing-query tests; HTTP gzip, ETag and date rejection; byte-identical preparation; all existing dated Europe/Africa identities retained; browser checks for all 30 starter boards, all scopes, country and carrier filters, departures/arrivals, Destinations, fare preview, fullscreen/back, themes, Indonesian, mobile, frequency counts, regional reset and airport visibility. Existing Europe, Americas, Australia and Melbourne browser regressions are included. Final validation passed: **336 Python tests**, **105 JavaScript tests**, and the complete Africa plus existing-view browser checks.
