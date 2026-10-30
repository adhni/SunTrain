# South America flights: top twenty plus every country’s busiest airport

**Current expansion:** Argentina, Peru and Chile domestic captures now supplement this original airport collection. See [the domestic expansion notes](SOUTH_AMERICA_DOMESTIC_NOTES.md) for current counts, coverage gaps and validation. The selection and results below document the original 27-airport pass.

A separate **South America · Flights** explorer for **2 November 2026 origin-local departures**, with all returned airlines and USD quotes. It covers nonstop flights **between 27 selected airports**, including domestic and international pairs. It is not a complete timetable for any airport or country; other airports and intercontinental flights are excluded.

## Selection and evidence

The original top ten follow the South American subset of [ACI-LAC's consolidated 2025 passenger ranking, announced 17 July 2026](https://aci-lac.aero/noticias/?sg=aci-lac-publica-datos-consolidados-del-trafico-aereo-en-america-latina-y-el-caribe-en-2025). The full numeric table was transcribed from [Panrotas's reproduction](https://www.panrotas.com.br/aviacao/pesquisas-e-estatisticas/2026/07/america-latina-movimenta-440-milhoes-de-passageiros-em-2025-veja-ranking-dos-aeroportos_230465.html): the original linked ACI ranking image returned HTTP 404 on review. The primary announcement confirms the ranking's year, scope and leading airports, but is not claimed as independent verification of every transcribed number.

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

The original ten retain their original ACI-LAC figures and airport identities. The expanded selection combines published operator/government traffic reports; metrics and rounding differ. The ranking places CNF ahead of VCP (12,826,553) and EZE (12,002,179). Operator reports can differ: [BH Airport reports about 13.3 million](https://site.bh-airport.com.br/pt-BR/press-room/releases?news=bh-airport-participa-do-festival-de-educacao-liga-da-gide-ampliando-oportunidades-de-aprendizagem-para-a-comunidade), while [Viracopos reports 12,826,553](https://www.viracopos.com/pt_br/noticias/com-12-8-milhoes-de-passageiros-2025-viracopos-atinge-novo-recorde-anual-e-mira-novas-rotas-em-2026.htm), supporting the cutoff choice. Exact airport identities use the existing immutable OurAirports CSV pin. GRU/CGH, AEP/EZE and MDE/EOH are not merged into city codes. VCP, EZE and SDU are now included separately; EOH remains outside the selection.

The reviewed facts are committed in `data/sources/south_america_airport_selection.json`. The manifest stores their SHA256 as both `additional_selection_sha256` and `route_source_sha256`; **these hash normalized committed facts, not the ACI webpage or unavailable image**. `route_source_hash_basis` records that distinction. The OurAirports source has its own existing byte hash.

## Expanded top twenty and national gateways

The reviewed traffic set adds **VCP, EZE, REC, SSA, CTG, POA, CLO, SDU, FOR and CWB**. New 2025 evidence comes from [Viracopos](https://www.viracopos.com/pt_br/noticias/com-12-8-milhoes-de-passageiros-2025-viracopos-atinge-novo-recorde-anual-e-mira-novas-rotas-em-2026.htm), [Aena's Recife report](https://www.aena.es/doc/pressdetail/260113-aena-estadisticas-2025en.pdf), [Salvador's operator](https://www.salvador-airport.com.br/pt-br/noticia/salvador-bahia-airport-encerra-2025-com-aumento-de-63-no-trafego-de-passageiros), [Cartagena's operator](https://aeropuertocartagena.com.co/historico-aeropuerto-internacional-rafael-nunez-de-cartagena-supero-los-7-7-millones-de-pasajeros-movilizados-en-2025/), [Fraport's Brazilian airports](https://www.fraport.com/en/newsroom/press-releases/2026/traffic-figures/fraport-traffic-figures-2025.html), [Cali's government](https://www.cali.gov.co/boletines/publicaciones/193534/la-conectividad-aerea-impulsa-a-cali-como-destino-internacional/), and [Motiva](https://aeroportos.motiva.com.br/noticias/). EZE retains the earlier ACI/Panrotas figure. Some numeric totals are explicitly secondary transcriptions, not claimed as independently verified primary figures. Salvador's operator reports a rounded 8.1 million. The committed selection marks source status and precision per airport.

| Reviewed traffic order | Airport | Country | Published 2025 passengers |
| --- | --- | --- | ---: |
| 11 | VCP · Campinas–Viracopos | BR | 12,826,553 |
| 12 | EZE · Buenos Aires–Ezeiza | AR | 12,002,179 |
| 13 | REC · Recife | BR | 9,938,051 |
| 14 | SSA · Salvador | BR | ~8.1 million |
| 15 | CTG · Cartagena | CO | 7,756,298 |
| 16 | POA · Porto Alegre | BR | 7,512,942, transcribed |
| 17 | CLO · Cali | CO | 6,903,591, transcribed |
| 18 | SDU · Rio de Janeiro–Santos Dumont | BR | 6,201,200, transcribed |
| 19 | FOR · Fortaleza | BR | 6,166,329, transcribed |
| 20 | CWB · Curitiba | BR | 6,082,222, transcribed |

This is a reviewed top-twenty selection using available published 2025 traffic, **not a perfectly harmonized census**. Recent comparable figures are incomplete for some countries, especially Venezuela. The national-gateway requirement ensures those countries are included regardless of their uncertain continental rank. No invented continental ranks or annual totals are assigned to the seven extra gateways.

All **twelve sovereign South American countries** have their busiest national airport in the catalogue:

| Country | Gateway | Selection |
| --- | --- | --- |
| Argentina | AEP · Aeroparque | Top twenty; EZE also included separately |
| Bolivia | VVI · Santa Cruz–Viru Viru | Additional gateway |
| Brazil | GRU · Guarulhos | Top twenty |
| Chile | SCL · Santiago | Top twenty |
| Colombia | BOG · Bogotá | Top twenty |
| Ecuador | UIO · Quito | Additional gateway |
| Guyana | GEO · Cheddi Jagan | Additional gateway |
| Paraguay | ASU · Asunción | Additional gateway |
| Peru | LIM · Lima | Top twenty |
| Suriname | PBM · Johan Adolf Pengel | Additional gateway |
| Uruguay | MVD · Montevideo | Additional gateway |
| Venezuela | CCS · Caracas–Maiquetía | Additional gateway |

Gateway evidence includes [Quito's government report](https://www.quitoinforma.gob.ec/2026/01/09/el-aeropuerto-de-quito-movilizo-a-5-4-millones-de-pasajeros-en-2025/), [Uruguay's operator statistics](https://investors.corporacionamericaairports.com/files/doc_news/2026/Jan/20/CAAP-Passenger-Traffic-December-2025.pdf), [Paraguay's DINAC annual report](https://www.dinac.gov.py/estadisticas/ResumenEstadisticoTransporteAereoComercial-2025_Enero-Diciembre.pdf), [NAABOL's Viru Viru account](https://naabol.gob.bo/naabol-consolida-avances-estrategicos-en-el-hub-de-viru-viru-en-sus-primeros-100-dias-de-gestion/), [Guyana's statistics bureau](https://statisticsguyana.gov.gy/subjects/demography-vital-and-social-statistics/arrivals-and-departures-cheddi-jagan-international-airport-guyana-2013-to-2026/) and [Suriname's government naming JAP its largest airport](https://gov.sr/thema/luchthaven/). CCS is supported by [published reporting identifying it as Venezuela's principal airport](https://elpais.com/america/2026-09-01/el-aeropuerto-internacional-de-caracas-vuelve-a-operar-dos-meses-despues-del-terremoto.html); its operator site timed out, so no current annual traffic total is claimed. Some national-gateway evidence describes the main airport rather than a fully comparable annual ranking. French Guiana and overseas island territories are outside the twelve-country guarantee.

## Search and fare policy

**27 × 26 = 702 unique directional queries**, all on the origin-local departure date of **2 November 2026**. The original 90 captures and all 537 records are reused unchanged. The expansion adds 612 unique directions; six new pilots belong to that set and are reused by bulk collection. There are **146 domestic** candidate directions (132 Brazilian, 12 Colombian and 2 Argentine) and **556 international** directions. Candidates do not imply service.

Two concurrent public Google Flights searches, exact IATA queries, resumable atomic captures, source timestamps and page hashes. Stop on access challenges; successful captures remain usable. No extra dates, paid sources, live tracking, automatic refresh, connecting itineraries or invented times. Any bounded follow-up of empty directions is reported below rather than silently counted as more unique directions.

All captured fares are **USD**, one adult, economy, one-way. Select the cheapest verified returned quote for the exact flight. Missing/unverified quotes remain **Price unavailable**; no relabelling or implicit conversion of BRL/COP/CLP/PEN/ARS. Repeated exact source identities are deduplicated; distinct flight numbers remain distinct, without inferred codeshares. Unspecified aircraft stay unknown. Durations must be 1 minute–8 hours and match the source.

## Replay and experience

National gateways remain in the airport catalogue and country selector even when no selected flights are returned. Their empty boards remain usable; coverage totals count only airports present in actual captured flights. This prevents unreturned service from silently removing a country or inflating its coverage.

The shared regional implementation supplies Domestic / International / Both, airline/code and exact-airport filters, From country / To country, airport traffic direction, local departure/arrival and Destinations boards, fullscreen pagination/back, previews without implicit seeking, explicit timeline seeking, station visibility and frequency lines. Domestic/international classification uses actual airport countries. The map initially fits South America; route arcs use a western-hemisphere anchor. New copy is translated into Indonesian.

The timeline uses **UTC** and spans all selected airports' complete origin-local departure days plus captured overnight arrivals. It starts at **03:00 UTC on 2 November** (midnight in Brazil/Argentina/Chile), rather than displaying three empty UTC hours. Brazil, Argentina, Suriname, Uruguay and Paraguay are UTC−3; Santiago is UTC−3 in November and UTC−4 in July. Colombia, Peru and Ecuador are UTC−5. Bolivia, Guyana and Venezuela are UTC−4. Paraguay uses America/Asuncion with its permanent UTC−3 rule. Airport boards display local dates and times. No adjacent-day departure searches are needed for this defined origin-local-day scope; departures on other local dates are excluded even if arriving on 2 November.

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
| Airports catalogued / searched / returning flights | 27 / 27 / 25 |
| Countries catalogued / returning flights | 12 / 10 |
| Unique directional queries | 702 |
| Returning directions / not returned | 225 / 477 |
| Failed / missing queries | 0 / 0 |
| Rejected source records | 0 |
| Flight identities | 1,629 |
| Added records / preserved original records | 1,092 / 537 |
| Domestic / international records | 1,272 / 357 |
| Airlines | 12 |
| USD quotes / price unavailable | 1,611 / 18 |
| Unverified fare-context queries | 0 |

**GEO (Guyana) and PBM (Suriname) returned no flights involving the other selected airports on this date.** They remain in the map, airport selector, country filters and departure/arrival boards. Their boards explicitly say no flights were captured in this snapshot. This is a source/network/date gap, not evidence of no service. All twelve countries are represented in the catalogue; only ten have captured flights. Country presence must never be presented as complete country timetables.

| Scope | Queries | Returning directions | Not returned |
| --- | ---: | ---: | ---: |
| Domestic | 146 | 117 | 29 |
| International | 556 | 108 | 448 |

Each airport was queried against all 26 other selected airports. The following totals cover this bounded network, not complete airport timetables.

| Airport | Country | Returning departure directions | Departures | Arrivals | USD departure quotes |
| --- | --- | ---: | ---: | ---: | ---: |
| AEP | AR | 13 | 55 | 51 | 50 |
| ASU | PY | 7 | 13 | 11 | 12 |
| BOG | CO | 14 | 160 | 156 | 160 |
| BSB | BR | 14 | 110 | 103 | 110 |
| CCS | VE | 1 | 4 | 4 | 4 |
| CGH | BR | 9 | 174 | 177 | 174 |
| CLO | CO | 4 | 44 | 53 | 44 |
| CNF | BR | 11 | 93 | 89 | 93 |
| CTG | CO | 4 | 47 | 49 | 47 |
| CWB | BR | 9 | 61 | 62 | 61 |
| EZE | AR | 6 | 16 | 16 | 15 |
| FOR | BR | 9 | 42 | 44 | 42 |
| GEO | GY | 0 | 0 | 0 | 0 |
| GIG | BR | 17 | 100 | 102 | 98 |
| GRU | BR | 17 | 154 | 157 | 153 |
| LIM | PE | 15 | 51 | 49 | 47 |
| MDE | CO | 7 | 80 | 77 | 80 |
| MVD | UY | 6 | 16 | 16 | 16 |
| PBM | SR | 0 | 0 | 0 | 0 |
| POA | BR | 12 | 75 | 76 | 75 |
| REC | BR | 10 | 66 | 65 | 66 |
| SCL | CL | 11 | 51 | 53 | 47 |
| SDU | BR | 6 | 86 | 90 | 86 |
| SSA | BR | 7 | 50 | 57 | 50 |
| UIO | EC | 3 | 11 | 10 | 11 |
| VCP | BR | 9 | 62 | 55 | 62 |
| VVI | BO | 4 | 8 | 7 | 8 |

| Carrier code | Records |
| --- | ---: |
| LA | 609 |
| G3 | 332 |
| AD | 322 |
| AV | 189 |
| JA | 74 |
| AR | 36 |
| P5 | 30 |
| H2 | 16 |
| OB | 9 |
| FO | 6 |
| VE | 4 |
| TK | 2 |

The expansion made **612 new unique searches**, including six new pilots. A single follow-up checked **14** new empty directions with a returned reverse, recovering **40 flights across 7 directions**. Total new page requests: **626**, without extra dates or repeated baseline queries. All **90 original captures**, **537 original flight records** and **10 original airport identities** are unchanged. The bounded follow-up did not retry every empty query or invent service for unreturned gateways.

Retained captures span **2026-10-27T00:19:28.996200+00:00–2026-10-27T01:08:41.453496+00:00 UTC**. Replay window: **2026-11-02T03:00:00+00:00 → 2026-11-03T11:20:01+00:00**, containing every captured departure and arrival. Bundle size: **93,541 bytes** (about 91 KiB), SHA256 **`6b030c340b283b10b9f7c04e3026fdf49b23fb3714afa0663cbe31e476d5a241`**. Rebuilding from retained captures is byte-for-byte identical. The North American reference also rebuilds with its previous byte hash.

**294 Python regression tests passed**, plus **28 focused regional/collector/localisation tests**, including the final snapshot. They cover all twelve country gateways, top-twenty membership, distinct city airports, all local zones and Chilean summer time, one-date ownership, USD-only/cheapest quotes, overnight arrivals, missing/empty queries, retained unreturned airports without inflated coverage, deterministic preparation, HTTP caching and date rejection. **105 JavaScript tests passed**, including retained gateway markers, geographic-filter behavior, airport choices without captured flights, and distinct missing-capture versus filtered/elapsed-event messages.

Browser checks passed for all **27 airport boards**, all **12 country filters**, all **12 returned carriers**, domestic/international scopes, USD fares, departures/arrivals/Destinations, exact-airport traffic directions, fullscreen pagination/back, preview without implicit seeking, frequency totals, station visibility, themes, Indonesian and 390px mobile layout. Unreturned GEO/PBM boards retain their local clocks, selected airport and all 27 airport choices; empty filtered boards retain map markers. The unfiltered map contains all 27 airports. North America still loads all 9,668 services; Australia flights and Melbourne transit preserve their original windows. No browser page errors. Unrelated working files remain unchanged.
