# South America flights: top ten airports

A separate **South America · Flights** explorer for **2 November 2026 origin-local departures**, with all returned airlines and USD quotes. It covers nonstop flights **between the selected ten airports**, including domestic and international pairs. It is not a complete timetable for any airport or country; other airports and intercontinental flights are excluded.

## Selection and evidence

Selection follows the South American subset of [ACI-LAC's consolidated 2025 passenger ranking, announced 17 July 2026](https://aci-lac.aero/noticias/?sg=aci-lac-publica-datos-consolidados-del-trafico-aereo-en-america-latina-y-el-caribe-en-2025). The full numeric table was transcribed from [Panrotas's reproduction](https://www.panrotas.com.br/aviacao/pesquisas-e-estatisticas/2026/07/america-latina-movimenta-440-milhoes-de-passageiros-em-2025-veja-ranking-dos-aeroportos_230465.html): the original linked ACI ranking image returned HTTP 404 on review. The primary announcement confirms the ranking's year, scope and leading airports, but is not claimed as independent verification of every transcribed number.

| South American rank | Airport | Country | ACI-reported 2025 passengers | Local zone |
| --- | --- | --- | ---: | --- |
| 1 | GRU · São Paulo–Guarulhos | BR | 47,174,529 | America/Sao_Paulo |
| 2 | BOG · Bogotá–El Dorado | CO | 45,464,526 | America/Bogota |
| 3 | SCL · Santiago | CL | 25,941,576 | America/Santiago |
| 4 | LIM · Lima–Jorge Chávez | PE | 25,496,109 | America/Lima |
| 5 | CGH · São Paulo–Congonhas | BR | 24,491,178 | America/Sao_Paulo |
| 6 | GIG · Rio de Janeiro–Galeão | BR | 17,906,990 | America/Sao_Paulo |
| 7 | AEP · Buenos Aires–Aeroparque | AR | 17,814,653 | America/Argentina/Buenos_Aires |
| 8 | BSB · Brasília | BR | 16,977,287 | America/Sao_Paulo |
| 9 | MDE · Medellín–José María Córdova | CO | 14,242,523 | America/Bogota |
| 10 | CNF · Belo Horizonte–Confins | BR | 13,114,989 | America/Sao_Paulo |

Keep this ranking's metric consistent rather than mixing operator totals. The ranking places CNF ahead of VCP (12,826,553) and EZE (12,002,179). Operator reports can differ: [BH Airport reports about 13.3 million](https://site.bh-airport.com.br/pt-BR/press-room/releases?news=bh-airport-participa-do-festival-de-educacao-liga-da-gide-ampliando-oportunidades-de-aprendizagem-para-a-comunidade), while [Viracopos reports 12,826,553](https://www.viracopos.com/pt_br/noticias/com-12-8-milhoes-de-passageiros-2025-viracopos-atinge-novo-recorde-anual-e-mira-novas-rotas-em-2026.htm), supporting the cutoff choice. Exact airport identities use the existing immutable OurAirports CSV pin. GRU/CGH, AEP/EZE and MDE/EOH are not merged into city codes. VCP, EZE, EOH and SDU are outside this selection.

The reviewed facts are committed in `data/sources/south_america_airport_selection.json`. The manifest stores their SHA256 as both `additional_selection_sha256` and `route_source_sha256`; **these hash normalized committed facts, not the ACI webpage or unavailable image**. `route_source_hash_basis` records that distinction. The OurAirports source has its own existing byte hash.

## Search and fare policy

**10 × 9 = 90 unique directional queries**, all on the origin-local departure date of **2 November 2026**. Six representative pilots belong to the same set and are reused by bulk collection. There are **22 domestic** candidate directions (20 Brazilian and 2 Colombian) and **68 international** directions. Candidates do not imply service.

Two concurrent public Google Flights searches, exact IATA queries, resumable atomic captures, source timestamps and page hashes. Stop on access challenges; successful captures remain usable. No extra dates, paid sources, live tracking, automatic refresh, connecting itineraries or invented times. Any bounded follow-up of empty directions is reported below rather than silently counted as more unique directions.

All captured fares are **USD**, one adult, economy, one-way. Select the cheapest verified returned quote for the exact flight. Missing/unverified quotes remain **Price unavailable**; no relabelling or implicit conversion of BRL/COP/CLP/PEN/ARS. Repeated exact source identities are deduplicated; distinct flight numbers remain distinct, without inferred codeshares. Unspecified aircraft stay unknown. Durations must be 1 minute–8 hours and match the source.

## Replay and experience

The shared regional implementation supplies Domestic / International / Both, airline/code and exact-airport filters, From country / To country, airport traffic direction, local departure/arrival and Destinations boards, fullscreen pagination/back, previews without implicit seeking, explicit timeline seeking, station visibility and frequency lines. Domestic/international classification uses actual airport countries. The map initially fits South America; route arcs use a western-hemisphere anchor. New copy is translated into Indonesian.

The timeline uses **UTC** and spans all selected airports' complete origin-local departure days plus captured overnight arrivals. It starts at **03:00 UTC on 2 November** (midnight in Brazil/Argentina/Chile), rather than displaying three empty UTC hours. Brazil and Argentina are UTC−3; Santiago is UTC−3 in November and UTC−4 in July. Colombia and Peru are UTC−5. Airport boards display local dates and times. No adjacent-day departure searches are needed for this defined origin-local-day scope; departures on other local dates are excluded even if arriving on 2 November.

The internal profile key is `SOUTH_AMERICA`, not the ISO code `SA` (Saudi Arabia). City ID `south_america_flights`, slug `south_america`; it stays separate from North America and the existing shared International network. North America's CLI defaults, archives, coverage and time zones are preserved.

## Preparation

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_south_america_airports.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_south_america_flights.py --dry-run
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_south_america_flights.py --validate-only
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_south_america_flights.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_south_america_flights.py --prepare-only
```

Manifest: `data/sources/south_america_flights_routes.json`. Prepared week/day: `data/reference/south_america_flights/2026-11-02.json.gz`. Capture cache: `.cache/google-flights-south-america-usd-v1/`. Reference override: `SUNTRAIN_SOUTH_AMERICA_FLIGHTS_REFERENCE`. Deterministic gzip uses `mtime=0`. Rebuilding from retained captures is offline; deleted captures require new public searches. Regenerating the catalogue needs the pinned OurAirports cache or the original immutable CSV download and the committed reviewed facts.

## Captured coverage and validation

| Measure | Result |
| --- | ---: |
| Airports planned / searched / returned | 10 / 10 / 10 |
| Unique directional queries | 90 |
| Directions returning flights | 58 |
| Directions not returned | 32 |
| Failed / missing queries | 0 / 0 |
| Rejected source records | 0 |
| Flight identities | 537 |
| Domestic / international records | 330 / 207 |
| Airlines | 10 |
| Verified USD quotes | 523 |
| Price unavailable | 14 |
| Unverified fare-context queries | 0 |

| Scope | Queries | Returning directions | Empty directions |
| --- | ---: | ---: | ---: |
| Domestic | 22 | 20 | 2 |
| International | 68 | 38 | 30 |

Each origin was searched against the other nine airports. Departure/arrival totals below belong to this bounded set only, not complete airport timetables.

| Airport | Returning departure directions | Departures | Arrivals | USD departure quotes |
| --- | ---: | ---: | ---: | ---: |
| GRU | 7 | 71 | 74 | 70 |
| BOG | 7 | 75 | 79 | 75 |
| SCL | 6 | 44 | 45 | 40 |
| LIM | 7 | 38 | 37 | 34 |
| CGH | 3 | 51 | 55 | 51 |
| GIG | 8 | 53 | 50 | 52 |
| AEP | 6 | 41 | 38 | 37 |
| BSB | 7 | 55 | 50 | 55 |
| MDE | 3 | 56 | 55 | 56 |
| CNF | 4 | 53 | 54 | 53 |

| Carrier | Code | Records |
| --- | --- | ---: |
| LATAM | LA | 222 |
| Gol | G3 | 104 |
| Avianca | AV | 80 |
| Azul | AD | 47 |
| JetSMART | JA | 32 |
| Aerolineas Argentinas | AR | 20 |
| Sky Airline | H2 | 16 |
| Wingo | P5 | 12 |
| Flybondi | FO | 2 |
| Turkish Airlines | TK | 2 |

Exactly **90 new page requests**, including six reused pilots. No other-date or cross-continent searches. None of the 32 empty directions had a returned reverse, so no follow-up searches were made. All successful captures, provenance and audit logs are retained in the ignored caches.

Source capture range: **2026-10-27T00:19:28.996200+00:00–2026-10-27T00:22:39.053875+00:00 UTC**. Replay window: **2026-11-02T03:00:00+00:00 → 2026-11-03T11:20:01+00:00**, including every captured departure and arrival. Bundle size **21,653 bytes** (about 21 KiB); SHA256 **`1eaae8a9eafb772c42f4b61181a75ff82e54038ac3ee9c1ce222b28abb6229fc`**. Cached rebuilding is byte-for-byte identical.

**Empty means not returned, never no service.** Query completion is not nationwide or complete airline coverage. The snapshot excludes all other airports and origin-local departure dates. Missing individual flights and fares remain possible even on returned directions. CGH/CNF's lack of returned international flights within this selection does not imply those airports have no international service. Airport rank membership does not guarantee every selected pair has nonstop flights.

**293 Python regressions passed**, including North America, shared flight preparation/replay, International-network isolation, HTTP, localisation and transit. **27 focused tests passed**, including the final South America snapshot, exact city-airport separation, 90 single-date directions, Colombian/Brazilian domestic and cross-border scope accounting, USD-only/lowest quote validation, Chilean summer time, overnight arrivals, UTC boundaries without empty leading hours, missing/empty queries, deterministic gzip, HTTP ETag/304 and rejected dates. **102 JavaScript tests passed**.

Browser checks passed for **all ten airport boards and all ten carriers**, Domestic / International / Both, Brazilian and Colombian domestic filters, international country pairs, local board clocks, USD fares, departure/arrival/Destinations modes, exact-airport traffic directions, fullscreen pagination/back, preview without implicit seeking, frequency totals, station visibility, themes, Indonesian and 390px mobile layout. North America still loads all 9,668 services; Australia flights and Melbourne transit retain their original windows. No browser page errors. The North American archive's byte hash is unchanged.
