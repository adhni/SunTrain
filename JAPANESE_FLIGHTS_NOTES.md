# Japanese flights

## Scope and rollout

Add **Japan · Flights** for **2 November 2026**, with an **Asia/Tokyo (JST, UTC+9)** timeline and airport-local boards. Captured prices use **USD**, one adult, economy, one-way. This remains a schedule replay: paths illustrate connections and do not represent recorded aircraft tracks.

The user's narrowed scope is **major airports and city routes first**. Small island and commuter networks are deferred. The existing Japan rail and Tokyo transport views stay separate.

### Domestic now

- Search **302 directional route candidates across 45 airports**, drawn from published ANA, JAL/J-AIR, Peach, Skymark and airport route information. Search both origin-local **1 and 2 November**, producing **604 queries** and retaining previous-day flights that overlap the selected JST day. Published route entries, including seasonal or historical entries, are candidates; only dated returned segments become replay flights.
- Keep exact airport identities: **HND/NRT**, **ITM/KIX/UKB**, **NGO/NKM**, **CTS/OKD** and **MMY/SHI** are separate. No TYO, OSA, SPK or other metropolitan queries. The 47-airport source catalogue retains NKM and OKD identities for later work, but their commuter-focused routes are not queried or displayed in this release.
- Cover Hokkaido, Honshu, Shikoku, Kyushu and the major Okinawa gateways. Remote island hops, New Central, First Flying, HAC/JAC commuter networks and dedicated FDA regional expansion are out of scope for now. This is not a nationwide-complete timetable.
- Scope is defined by airport pairs, not an inferred aircraft-capacity cutoff. Regional airlines can still appear on an included city route.
- Use the existing compact planes, airport-label collision handling, visibility toggle, airline-code/airport filters, departures/arrivals, Destinations, fullscreen pagination/back, captured fare previews, explicit seeking and frequency lines. International/Both controls stay hidden until a future international bundle exists. New copy supports English and Indonesian.
- Keep two collector workers, resumable normalized query caches and original source timestamps. Stop on access challenges; preserve successful captures and report failed/missing searches. Empty results mean “not returned”, never “no service”. No automatic refresh runs in the app.
- Validate source duration against UTC timestamps, with the shared one-minute minimum and eight-hour domestic maximum. Deduplicate exact repeated source identities while retaining distinct flight numbers. Matching times do not prove a codeshare. Unknown aircraft remain unknown.
- Capture the cheapest returned positive USD quote for the **exact flight identity**, with verified one-adult/economy/one-way context. Do not substitute connecting-trip minima, infer unavailable fares, convert JPY or relabel prices. Required source-reported taxes/fees are included; baggage and optional services may cost extra. Captured prices can change.

### International later (planned only)

1. Add a separate `japan_international_routes.json` manifest and `2026-11-02-international.json.gz` bundle in the same location view. Keep domestic the default; add Domestic / International / Both once both scopes are validated.
2. Prioritise **HND, NRT, KIX, NGO, FUK, CTS and OKA**, then verified overseas links from regional gateways such as SDJ, HIJ, KMQ and KOJ. **ITM is domestic-only**; do not create international candidates merely because of its historical English name. Preserve every exact airport, including the two Tokyo airports and the three Kansai airports.
3. Build focused bidirectional candidates from official airport passenger route lists and airline nonstop networks, including foreign carriers. Separate cargo-only destinations, connecting itineraries, seasonal candidates and future announcements. Do not brute-force a Japan × world matrix or treat every airport-directory destination as a passenger nonstop service.
4. Reuse compatible raw **USD** captures from India, Singapore and Gulf collections only for matching origin, destination, date, adult count, cabin and one-way context; keep their original capture timestamps. Re-filter raw flights against the **JST** day. Other prepared country bundles use different UTC windows and cannot be merged directly. MYR/unpriced collections can supply candidates, not USD fare evidence.
5. Validate nearby Asia, Southeast Asia, Gulf/Europe and trans-Pacific examples first. Assign every airport an explicit IANA zone, use a 24-hour duration ceiling and derive origin-local search dates from the UTC replay window and maximum duration. Handle overnight/date-line flights continuously. Boards own events in half-open day windows and display local times; timeline stays JST.
6. Report actual coverage by Japanese gateway and overseas region, priced/unpriced records, missing/failed queries, rejected segments, unreturned candidates and unresolved airports. Completed searches do not imply all international services were captured.

A later small-airport domestic pass is separate work, not silently added here. It can include Komaki/Okadama, FDA, HAC, JAC and remote-island routes after the user wants that expansion. Chofu, Niijima and Kozushima lack IATA identities in the pinned catalogue; do not invent codes or substitute other Tokyo airports. Helicopter services and extra schedule-source adapters are outside this release.

## Sources and rebuilding

- [ANA winter timetable](https://www.ana.co.jp/guide/plan/airinfo/dom-timetable/pdf/timetable_all_20261025_20270131.pdf): valid **25 October 2026–31 January 2027**, published 25 August 2026. Curated route headings form the main candidate list, filtered to this release's airport set. Reviewed PDF SHA-256: `db3f438961d14e13a6275b21b8ce5cbcb5f09cf828c46b166e623c06f449d223`. The PDF is preparation evidence, not an extra runtime schedule adapter.
- [Haneda domestic destination selector](https://tokyo-haneda.com/en/flight/monthlyFlightSchedule.html), [Narita passenger destinations](https://www.narita-airport.jp/en/discover/citylist/), [Narita–Hakodate announcement](https://www.narita-airport.jp/files/3a7f642590e6b43238a824febdcc3d359b4d6efa4dea8211b674fc4b1e9b4303), [Naha destinations](https://www.naha-airport.co.jp/flight/city_list/).
- [J-AIR network](https://www.jair.co.jp/area/), [JAL second-half 2026 network changes](https://press.jal.co.jp/ja/release/202608/009668.html), [Peach routes](https://www.flypeach.com/en/lm/st/routemap), [Skymark routes](https://www.skymark.co.jp/en/dom_network/). Seasonal/network listings do not guarantee service on 2 November.
- OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256 `a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies exact identities and coordinates. All domestic airports explicitly use `Asia/Tokyo`. Curated candidate evidence has its own deterministic hash, explicitly not a raw-webpage hash.
- Exact-IATA public Google Flights queries supply dated segment and fare evidence. Each normalized query retains its URL, source-local date, UTC capture timestamp, status, rejected-record diagnostics and fare-context failures.

```bash
.venv/bin/python scripts/prepare_japanese_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_japanese_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_japanese_flights.py
# Offline rebuild, using the successful normalized captures:
.venv/bin/python scripts/prepare_japanese_flights.py --prepare-only
```

The wrapper and generic `--country JP` collector both use `.cache/google-flights-japan/`; the wrapper limits concurrency to two. Probes never publish a misleading partial-manifest snapshot. Runtime reads only `data/reference/japan_flights/2026-11-02.json.gz` and generated selected-day HTTP caches. Gzip uses fixed `mtime=0`, deterministic ordering and atomic replacement.

Local `.cache/japan-flights-audit/` holds preparation evidence and test logs/screenshots. The optional ANA source PDF is about 7 MB and is re-downloadable from the pinned URL/hash above; it is unnecessary for rebuilding the curated manifest. The airport CSV is reused from `.cache/australia-flights-audit/` and can be downloaded again by the builder. Deleting normalized flight captures saves local space but requires new public searches for future preparation; the checked-in snapshot keeps working.

## Capture and verification

Captured **25 October 2026** for **2 November 2026 JST**:

| Measure | Actual coverage |
| --- | --- |
| Catalogue / searched / returned airports | 47 / 45 / 44 |
| Planned / searched directional candidates | 302 / 302 |
| Routes returning flights on either searched date / retained replay routes | 288 / 283 |
| Planned / captured queries | 604 / 604 |
| Queries with no matching direct flight returned | 43 |
| Failed / missing queries; unresolved airports | 0 / 0; 0 |
| Rejected source flight records | 0 |
| Retained flights / returned carriers | 1,932 / 14 |
| Flights with / without captured USD quotes | 1,920 / 12 |
| Prepared gzip | 95,083 bytes |

| Region | Catalogue airports | Searched airports | Returned airports | Captured departures |
| --- | ---: | ---: | ---: | ---: |
| Hokkaido | 7 | 6 | 6 | 225 |
| Honshu | 24 | 23 | 22 | 1,078 |
| Shikoku | 4 | 4 | 4 | 78 |
| Kyushu | 8 | 8 | 8 | 354 |
| Okinawa gateways | 4 | 4 | 4 | 197 |

Okadama (OKD) and Komaki (NKM) are retained identities but deliberately unsearched. Shizuoka (FSZ) was searched only against the historical Naha candidate and returned no flights; its other regional links were not collected in this pass. Its absence is not a claim that the airport has no service.

No flights were returned for the replay day on **FSZ↔OKA, FUK↔SHI, HKD↔NRT, ISG↔ITM, ITM↔MMY, KIJ↔OKA, KKJ↔NRT and NGS↔OKA**, or **FUK→TKS, KOJ→OKA and UKB→KOJ**. Seasonal, suspended and unreturned candidates remain gaps. Five directional routes returned flights on 1 November but not within the selected 2 November replay window, explaining the difference between 288 routes with search results and 283 retained routes. Search completion does not establish national completeness.

All **12 unpriced flights are FDA (JH)** records with no returned exact-flight USD offer. The single unverified fare-context query is the **empty 2 November KOJ→OKA result**; it attached no uncertain price to a flight. Missing prices remain unavailable, not zero or converted JPY fares.

Returned source carrier codes are **JL, NH, BC, MM, GK, HD, 6J, 7G, IJ, NU, FW, JH, OC and MZ**. A regional airline can appear on an included city route; this does not add its small-airport network. Source flight numbers remain distinct and should not be interpreted as deduplicated physical aircraft movements.

The catalogue/manifest rebuild identically, and rebuilding the gzip from successful normalized captures produces the same bytes. Snapshot SHA-256: `c30cde30a787131f45f55448088835ddfc5579d100ae9341474a94a34cdfb98d`.

Validation: **173 Python tests and 89 JavaScript tests passed**. The final Japan browser suite passed for HND, NRT, ITM, KIX, CTS, NGO, OKA and SHI: exact-airport/airline filtering, departures/arrivals, USD fare previews without implicit seeking, JST clocks, fullscreen/back and pagination, Destinations, frequency totals, airport visibility, five themes, Indonesian copy, mobile layout and HTTP cache reuse. Existing Tokyo transit remained functional and separate. Shared flight-country, Melbourne replay/HTTP, Japan rail and app regressions also passed. Tests cover domestic-only selection, deferred airports, overnight JST boundaries, source-duration validation, distinct flight identities, lowest exact-flight offers, invalid currency/foreign endpoints, missing queries, deterministic preparation and compressed HTTP/ETag/date validation.
