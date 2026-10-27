# Africa flights plan

Status: proposed scope only; no new flight collection or implementation started.

## Recommendation

Build one **Africa · Flights** explorer with domestic, cross-border African and worldwide international connections. Focus new collection on **30 initial African airports**, selected for geographic balance and useful domestic links rather than claiming a definitive continental traffic ranking. Retain additional valid African airports already present in reusable captures without searching all their possible routes.

Keep the existing Domestic / International / Both and From country / To country controls. International includes both cross-border African flights and flights outside Africa; report those as separate coverage buckets internally. There is no need for multiple new bridge views in the first release.

## Existing material already inspected

- The committed Europe replay contains **526** flights involving African-country or separately labelled African-territory airports, across **50 African endpoints**. **516** use the 2 November source departure date; ten use 1 November and must not silently enter a one-local-day replay.
- The narrower European group route manifest supplies **226** exact directional Africa candidates. **All 226 are already cached**: 214 in `.cache/google-flights-europe-groups-eur-v1/`, twelve compatible legacy captures in `.cache/google-flights-europe-eur-v1/`.
- Those 226 raw captures contain **299 dated flights across 29 returned carriers**, all with verified EUR quotes. This includes airlines excluded from the old Europe brand roster.
- The existing shared International network has eight African-endpoint flights across four directions involving ADD/JNB, and Singapore's standalone reference contains three involving ADD/JNB. These can overlap other archives and are not additive coverage totals.
- Audit remaining Gulf, Asian and Australian references/caches, including nested hub archives, before estimating new requests. Deduplicate exact query keys and flight identities before reporting any combined count.

These are snapshot/cache observations, not evidence that every African route is covered. No new Google Flights search was used to prepare this plan.

## Initial new-collection footprint

**24 core airports:**

| Region | Proposed airports |
| --- | --- |
| North | CAI Cairo, HRG Hurghada, CMN Casablanca, RAK Marrakech, ALG Algiers, TUN Tunis |
| West | LOS Lagos, ABV Abuja, ACC Accra, DSS Dakar, ABJ Abidjan |
| Central | FIH Kinshasa, DLA Douala |
| East | ADD Addis Ababa, NBO Nairobi, DAR Dar es Salaam, EBB Entebbe, KGL Kigali |
| South | JNB Johannesburg, CPT Cape Town, DUR Durban, WDH Windhoek |
| Indian Ocean | MRU Mauritius, SEZ Seychelles |

**Six domestic additions:** GRJ George, SSH Sharm el-Sheikh, AGA Agadir, MBA Mombasa, ZNZ Zanzibar and BJR Bahir Dar. These provide domestic destinations in South Africa, Egypt, Morocco, Kenya, Tanzania and Ethiopia; LOS/ABV already provides a Nigerian domestic pair candidate. Actual dated flights still require capture.

Prioritise new domestic route discovery in South Africa, Nigeria and Egypt, then Ethiopia, Kenya, Morocco and Tanzania. Only collect published exact-airport connections within the selected footprint. This is a starter, not complete domestic timetables or coverage of all African countries. Further regional/country gateways can be added later from evidence.

## Route discovery and efficient collection

1. Audit reusable captured queries and records, dates, original fare currencies, parser limits and airport identities. Keep original timestamps and source hashes.
2. Read actual airport-pair route maps, airline/airport destination lists and dated announcements. Start with Ethiopian, Kenya Airways, EgyptAir/Air Cairo, Royal Air Maroc, Airlink, FlySafair, South African Airways, Air Peace and other relevant domestic/regional carriers. These identify candidates; all returned carriers are eligible for dated flights.
3. Include published domestic pairs inside the starter footprint, published connections between selected African airports, and published **worldwide** international destinations from the initial African collection airports. International destinations are not restricted to countries already represented by a SunTrain location. Resolving a foreign endpoint does not mean collecting that country's domestic network.
4. Resolve exact airports. A city-only destination list is insufficient evidence for every airport in a city. Exclude cargo, connecting offers, ambiguous airport labels and services explicitly starting after 2 November. A hub's destination list must never become every destination-to-destination pair.
5. Deduplicate directional airport/date queries across airlines and discovery sources. Include both directional candidates when supported by the route evidence, but never infer a reverse-day schedule from the outbound capture.
6. Produce a dry-run report with sourced directional pairs, compatible captures, incompatible/missing queries and the exact new-request count. Set the collection footprint from that report; no guessed search count in advance and no blind Cartesian fallback.
7. Search only missing compatible **2 November 2026 origin-local departure-date** queries, two concurrent searches, all returned airlines. No adjacent dates, weekly sweeps or per-airline duplicate requests. Keep resumable atomic caches and stop on access challenges.

### Route-source entry points

- [Ethiopian passenger destinations](https://corporate.ethiopianairlines.com/AboutEthiopian/Destinations) separates domestic, African and intercontinental passenger lists from freighter lists. Destination membership alone does not prove a nonstop from ADD or another selected airport.
- [Airlink travel / route map](https://www.flyairlink.com/plan-your-travel) supplies southern African discovery and schedule links.
- [FlySafair route list](https://flysafair.zendesk.com/hc/en-us/articles/203205741-Where-we-fly) lists specific domestic and regional pairs, but some Lanseria labels incorrectly show JNB; resolve Lanseria as its own exact airport, HLA, rather than copying that code.
- [Royal Air Maroc route map](https://www.royalairmaroc.com/en/route-map) supplies Moroccan/regional/worldwide discovery.
- [Air Peace routes](https://flyairpeace.com/routes/) and [terminal information](https://flyairpeace.com/departure-arrivals/) supply Nigerian/regional candidates. Their marketing lists can mix domestic and overseas destinations; only dated exact nonstop segments enter the replay.
- [Air Cairo destinations](https://aircairo.com/ar-eg/route-map) labels airports and some codeshares; distinguish candidates from independently verified operating flights.

Sources were inspected on 27 October 2026. Capture/pin the precise discovery documents and normalized facts during implementation. Historical or seasonal material remains labelled candidate evidence. Do not infer a current schedule from a route map.

## International policy

- Include routes within Africa and worldwide connections from the starter airports from the first release. Expect discovery to cover Europe, Gulf/Middle East (including destinations outside the existing three Gulf hubs), Asia, the Americas and Australia where published nonstop evidence exists; do not assert any particular route operates on the replay date before capture.
- Reuse compatible existing EUR/USD and other verified original-currency quotes without conversion. **New missing queries request USD**, choosing the cheapest verified exact-flight quote. Do not repeat a valid schedule query solely to make every displayed price USD. If a later release requires uniform USD, treat that as a separate deliberate recollection.
- Only flights with dated departure/arrival timestamps and validated nonstop durations. Support up to 24 hours for long intercontinental flights, validated against source duration; keep the one-minute minimum for short regional flights. Do not loosen existing countries' validation globally.
- Preserve exact source flight identities and distinct flight numbers. Do not infer codeshare equivalence or invent aircraft/times/prices.
- Keep the shared International network's current footprint unchanged initially. Adding an African projection later must be explicit, reuse this archive, deduplicate overlapping identities/currencies and report UTC-window gaps; it must not trigger its old multi-day global collection plan.

## Airport/date handling and experience

- Explicit airport-level IANA zones. Test Cairo/Morocco seasonal clock behavior and countries spanning zones. Never assign every airport a national default without verification.
- Keep JNB/HLA, CAI/SPX and other city airports distinct. Resolve relocated/current airports against dated sources, including Luanda LAD/NBJ, before adding their routes. Airport renaming alone must not merge different physical airports.
- Use a UTC timeline spanning the selected origin-local departure days and overnight arrivals. Boards display local airport dates/times; no extra-day collection is implied by a flight arriving the next day.
- Initial map fits Africa, with compact planes, airport-label collision handling, the airport visibility toggle, selection-only route arcs and existing frequency lines. Fit selection can reach foreign endpoints.
- Reuse airline/code, exact-airport and country filters, local departure/arrival boards, Destinations, fullscreen/back, fare previews and explicit timeline seeking. Translate new copy into English and Indonesian; test themes and mobile.

## Delivery order and checks

1. Reusable-capture inventory, exact airport catalogue and sourced route manifest, with a dry-run search budget.
2. Validate representative domestic, intra-African, overnight and long-haul routes using reusable captures first, then a small pilot only where needed.
3. Collect the deduplicated missing queries and prepare one deterministic compressed Africa reference. Rebuild offline byte-for-byte.
4. Browser-check airports across every included African region, all board modes, filters, frequency counts, themes and mobile. Re-run existing flight and Melbourne transit regressions.
5. Publish actual coverage by African region and by domestic / intra-African / intercontinental bucket, separating planned, cached, returned, failed and unattempted queries. Unreturned airports remain selectable with capture-gap messages.

No fixed promise of continental completeness. Small commuter/charter services, frequency-only schedules, airports outside the starter footprint and uncaptured routes remain documented gaps. PR creation/merging is a later request after implementation.

## Implemented snapshot

Implemented on `codex/africa-flights`: 2,468 dated flights from 1,927 captured Google directions (422 reused), plus 94 directions from the existing official Ryanair archive with no new searches. See [Africa flight notes](AFRICA_FLIGHTS_NOTES.md) for actual geographic coverage, source gaps, prices and offline preparation. The shared International network is unchanged. PR creation and merging remain a later request.
