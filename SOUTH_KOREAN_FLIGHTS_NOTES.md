# South Korean flights

## Rollout plan

Domestic first, then international in the same **South Korea · Flights** view. The existing South Korea railway and Seoul transport views remain separate. Both phases use the **2 November 2026** snapshot, **Asia/Seoul (KST, UTC+9)** timeline and captured **USD** quotes for one adult, economy, one-way. This is scheduled replay, not live tracking. Paths illustrate connections rather than recorded aircraft tracks.

### Phase 1 — domestic (this branch)

- Keep all 15 civil airports in the source catalogue, with exact IATA/ICAO identities from pinned OurAirports. Incheon (ICN) and Gimpo (GMP) are never combined into SEL.
- Search 19 published candidate pairs in both directions: 38 directional routes involving 13 airports. Search origin-local 1 and 2 November: 76 queries, including the previous day for flights arriving after midnight. A route listing is only a search candidate; dated returned segments provide the schedule.
- Jeju candidates: GMP, PUS, CJJ, TAE, KWJ, RSU, USN, KPO, HIN, KUV, WJU and YNY. Additional Gimpo candidates: PUS, USN, RSU, HIN, KPO, KWJ and TAE. No indiscriminate all-airport matrix.
- Exclude Muan (MWX): the official tourism guide reports closure until **24 December 2026, 23:59**. Keep its catalogue identity and documented exclusion; do not interpret its absence as an empty search.
- Exclude ICN: international-transfer-only domestic services are unsuitable as normal standalone domestic flights. The guide's historical ICN–CJU listing does not establish a public domestic service on the replay date. ICN–PUS/TAE transit links need separate treatment in a later phase.
- Reuse compact planes, airline-code and airport filters, departure/arrival boards, fullscreen pagination, Destinations, captured fare previews, station visibility, themes, mobile layout and frequency lines. Hide International/Both until international data actually exists.
- Validate busy and regional routes first, then capture with two workers, resumable caches and original UTC timestamps. Stop on an access challenge. Keep successful captures and report missing/failed queries. Empty results mean “not returned”, never “no service”.
- Keep distinct source flight numbers, including airline changes and separate marketing identities. Do not infer codeshares or airline mergers from matching times. Unknown aircraft stay unknown. Select the cheapest exact-flight quote among returned offers; missing or uncertain fare context stays unpriced. Do not use connecting-trip minima, convert KRW to USD or invent prices.

### Phase 2 — international (planned, not collected or enabled here)

1. Build a separate `south_korea_international_routes.json` manifest and `2026-11-02-international.json.gz` bundle. Preserve domestic rebuilding and caches. Enable Domestic / International / Both only with validated data; domestic remains the default.
2. Start with **ICN, GMP, PUS, CJU, CJJ and TAE**. Add YNY or MWX only after official evidence establishes operations for the chosen replay date; airport names alone are insufficient. Muan remains excluded for this date unless the dated closure evidence changes.
3. Use official airport route information and airline nonstop networks: Korean Air's current route viewer, Asiana, Korean low-cost carriers and foreign carriers. Resolve every candidate to exact airports, preserving ICN/GMP, HND/NRT, TPE/TSA, PVG/SHA and PEK/PKX where relevant. Search published pairs in both directions. Avoid an airports-of-the-world Cartesian product.
4. Reuse compatible raw USD captures from India, Singapore and Gulf caches only when origin, destination, date, one adult, economy and one-way context match. Preserve original source timestamps. Re-filter their raw flight records against the **KST** day; never merge prepared foreign-country bundles whose day windows differ. Australia/Indonesia unpriced captures and MYR Malaysian captures supply candidates only, not USD prices.
5. Probe short-haul Japan/China, Southeast Asia, Gulf, European and North American long-haul routes before the full run. Use explicit destination IANA zones and a 24-hour duration ceiling, source-duration validation, and origin-local dates calculated from the UTC replay window and maximum duration. Handle overnight/date-line journeys using timestamps. Airport boards own events within half-open day boundaries, displayed locally; timeline stays KST.
6. Treat ICN–PUS/TAE connections as a separate restricted product if later included. Require verified dated times, an explicit “international transfer only” label and reliable source treatment. Never present a fictitious standalone fare or silently mix them into ordinary domestic choices. This restriction UI and collector work are outside phase 1.
7. Report actual coverage by Korean gateway and foreign region, unreturned candidates, failed/missing queries, rejected records, priced/unpriced flights and unresolved airport/timezone identities. Query completion does not imply nationwide or worldwide completeness.

Free public sources only. No automatic refresh, paid feeds, live tracking or unrelated adapters in either phase. Later replay dates need a separate collection, not relabelling this snapshot.

## Sources and reproducibility

- [Korea Tourism Organization domestic flight guide](https://english.visitkorea.or.kr/svc/contents/infoHtmlView.do?vcontsId=171992), updated 19 June 2026, reviewed 25 October 2026: civil airports, domestic route candidates and Muan closure.
- [Jin Air 2026 guide](https://files.jinair.com/documents/%EC%A7%84%EC%97%90%EC%96%B4%20%EC%83%81%EC%9A%A9%EC%9A%B0%EB%8C%80%20%EC%9D%B4%EC%9A%A9%EC%95%88%EB%82%B4%EC%84%9C%282026%29.pdf): additional GMP–TAE candidate; not a dated timetable.
- [Incheon Airport transit-exclusive domestic guidance](https://www.airport.kr/ap_en/1467/subview.do): transfer restrictions.
- [Korean Air nonstop route viewer](https://www.koreanair.com/contents/whatsnew/route-map): international planning source, not collected flight evidence in this release.
- Airport source: OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256 `a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`. Builder checks the pin; curated route evidence has a separate deterministic hash, explicitly not a raw-page hash.
- Schedule and fare evidence: exact-IATA Google Flights results. Each normalized query stores its URL, origin-local date, capture timestamp, status, flight records, fare context failures and rejected source records. Prices are captured quotes and may change; optional baggage/services may cost extra.

```bash
.venv/bin/python scripts/prepare_south_korean_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_south_korean_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_south_korean_flights.py
# Offline rebuild from successful normalized captures:
.venv/bin/python scripts/prepare_south_korean_flights.py --prepare-only
```

The wrapper defaults to two workers and `.cache/google-flights-south-korea/`. The generic collector also supports `--country KR` for domestic only, using the same default cache. The runtime only reads `data/reference/south_korea_flights/2026-11-02.json.gz` and selected-day HTTP caches. Prepared gzip has fixed `mtime=0` and deterministic ordering. Deleting captures saves local space but requires new searches to rebuild; the checked-in gzip continues working. The pinned CSV can be downloaded again by the catalogue builder.

## Captured coverage and validation

Captured **25 October 2026**, for the KST replay day on **2 November 2026**:

| Measure | Actual coverage |
| --- | --- |
| Catalogue / searched / returned airports | 15 / 13 / 12 |
| Planned / searched / returned directional routes | 38 / 38 / 32 |
| Planned / captured queries | 76 / 76 |
| Queries with no matching direct flights returned | 12 |
| Failed / missing queries; unresolved airports | 0 / 0; 0 |
| Rejected source flight records | 0 |
| Retained flights / carriers | 357 / 8 |
| Flights with / without captured USD quotes | 309 / 48 |
| Prepared gzip size | 14,370 bytes |

Returned airports: **GMP, CJU, PUS, CJJ, TAE, KWJ, RSU, USN, KPO, HIN, KUV and WJU**. Returned carriers: Korean Air, Asiana Airlines, Jeju Air, Jin Air, Air Busan, Air Seoul, Eastar Jet and Aero K. Returned flight identities are preserved separately; this is not an inferred list of operating codeshares.

Both searched dates returned no matching direct flights for **CJU↔YNY, GMP↔TAE and GMP↔KPO**. Yangyang remains a searched candidate, not a fabricated map airport with services. These results do not establish that no service exists. ICN/MWX were deliberately excluded before searching, for the documented reasons above.

**44 Eastar and 4 Aero K flights** have no returned exact-flight quote and remain unpriced. All captured query fare contexts were verified; absence of a quote is not a zero fare. Captured fares include required taxes/fees as reported by the source, with optional charges potentially extra. Query completion is not a claim of complete national coverage, and no frequency-only schedules were invented.

Validation covers exact airport identity, excluded routes, KST midnight, previous-day arrivals, one-minute parser lower bound, duplicate flight identities, cheapest USD offers, uncertain/missing quotes, invalid currency/endpoints, missing queries, deterministic gzip and HTTP date rejection/ETag caching. Browser validation covers Gimpo, Jeju, Busan, Wonju and Sacheon, departure/arrival ownership, airline and airport filters, fullscreen pagination/back, fare preview without seeking, Destinations, frequency lines, five themes, Indonesian copy, mobile layout and existing Seoul transit. Shared flight, Melbourne replay and Korean transit regressions are included.

Release checks: **165 Python tests and 88 JavaScript tests passed**. South Korea and Melbourne browser suites passed with no page errors, including the airport/station visibility toggles and fullscreen return. The starting map now waits until the location controls finish layout before fitting its bounds, avoiding a zoom based on the previous container height. Both the catalogue and prepared flight gzip reproduce byte-for-byte from pinned/cached inputs. Snapshot SHA-256: `97e011f6682095d614f7b0582250ed93451a3cedf3733d0a5375937e0100579d`.
