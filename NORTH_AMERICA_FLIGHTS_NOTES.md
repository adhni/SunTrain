# North America flights: 50 selected airports

This single explorer covers domestic and cross-border nonstop flights between fifty exact airports, departing **2 November 2026 in each origin airport's local time**, with all returned airlines. **All captured fares use USD**, including domestic flights. Paths are illustrative and fares are captured quotes rather than live availability.

## Selection and sources

The US thirty remain the [FAA final CY2025 top thirty by passenger boardings](https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx). Canada uses the latest reviewed [Transport Canada national table's 2024 enplaned/deplaned revenue passenger counts](https://tdih-cdit.tc.canada.ca/en/addendum-tables/2024/table-a14-top-20-busiest-canadian-airports-terms-enplaneddeplaned-revenue-0). Mexico uses [SICT's preliminary 2025 total passenger ranking, PDF pages 32–33](https://micrs.sct.gob.mx/images/DireccionesGrales/DGP/estadistica/Principales-Estadisticas/PE_2025.pdf). These are separate national selections with different published metrics, not a uniform continent-wide top fifty ranking.

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

## Central America and Caribbean selection

Ten additional major airports: **PTY, SJU, PUJ, SJO, SDQ, SAL, GUA, MBJ, NAS and AUA**. This is a reviewed top-ten selection from reported 2025 passenger volumes, not a harmonized statistical census. Metrics differ (transfers, commercial passengers, arrivals/departures), some totals are rounded, and comparable current statistics are incomplete, notably for Cuba. Mexico is already included separately. Do not interpret this selection as every airport in the region.

| Regional order | Airport | Country/territory | Reported 2025 passengers | Local zone / November offset |
| --- | --- | --- | ---: | --- |
| 1 | PTY · Panama City | PA | 20,981,855 | America/Panama / UTC−5 |
| 2 | SJU · San Juan | PR | 13,643,686 | America/Puerto_Rico / UTC−4 |
| 3 | PUJ · Punta Cana | DO | >11 million, rounded operator statement | America/Santo_Domingo / UTC−4 |
| 4 | SJO · San José | CR | 6,403,220 | America/Costa_Rica / UTC−6 |
| 5 | SDQ · Santo Domingo | DO | 5,221,168, secondary transcription | America/Santo_Domingo / UTC−4 |
| 6 | SAL · San Salvador | SV | >5.2 million, rounded | America/El_Salvador / UTC−6 |
| 7 | GUA · Guatemala City | GT | 5,129,535, secondary transcription | America/Guatemala / UTC−6 |
| 8 | MBJ · Montego Bay | JM | 4,495,370 | America/Jamaica / UTC−5 |
| 9 | NAS · Nassau | BS | 3,991,820 | America/Nassau / UTC−5 |
| 10 | AUA · Aruba | AW | 3,414,277 | America/Aruba / UTC−4 |

Selection evidence: [Panama government passenger table](https://www.datosabiertos.gob.pa/dataset/4cfac507-e49a-46b5-8811-e5334631c97d/resource/e36f2764-ca5d-45be-b52f-f596d35045a7/download/movimientomensualdepasajerosaitsa2025.pdf), [ASUR's December/year-end statement](https://www.prnewswire.com/news-releases/asur-announces-total-passenger-traffic-for-december-2025-302654211.html), [Punta Cana operator](https://www.puntacanainternationalairport.com/es/about-us/news-projects/item/aeropuerto-de-punta-cana-marca-un-hito-historico-y-cierra-2025-con-record-consecutivo-de-vuelos-y-pasajeros), [San José operator](https://www.sjoairport.com/aeropuerto-juan-santamaria-2025-fue-un-ano-historico-en-la-ejecucion-de-obras-estrategicas-para-fortalecer-su-capacidad-operativa-y-de-trafico-aereo/), [CEPA El Salvador](https://www.cepa.gob.sv/aeropuerto-internacional-de-el-salvador-registra-crecimiento-durante-la-temporada-de-fin-de-ano-y-consolida-resultados-positivos-al-cierre-de-2025/), [Montego Bay operator statistics](https://www.mbjairport.com/history-facts), [Vantage's report, Nassau p.59 and Montego Bay p.61](https://www.vantagegroup.com/wp-content/uploads/2026/07/Vantage_ImpactReport_2025_Final.pdf), and [Aruba's annual report p.13](https://www.airportaruba.com/storage/app/media/PDF/AAA-ANNUAL-REPORT-2025.pdf). Vantage PDF SHA256: `0591589b0884533c761a1e5ca12e077d3d626865846120e864ff02eb096fae4b`.

SDQ's transcribed figure comes from the [Caribbean comparison table](https://en.wikipedia.org/wiki/List_of_the_busiest_airports_in_the_Caribbean), which cites Banco Central. GUA's comes from [La Hora's DGAC report](https://lahora.gt/nacionales/hloarca/2026/01/26/vuelos-se-incrementan-en-aeropuerto-la-aurora-y-se-proyectan-dos-nuevas-rutas/): 2,573,651 arrivals + 2,555,884 departures. Current government sites did not expose those underlying tables in readable form; those two values are explicitly secondary rather than claimed primary verification. The archived OurAirports pin resolves every exact airport independently of ranking evidence.

## Scope and search policy

**50 × 49 = 2,450 unique directional queries**, all airlines returned, on **2 November 2026 in the origin's local time**. There are **972 domestic** and **1,478 international** candidates when mainland US–Puerto Rico routes count as domestic. These are search candidates, not proof of service.

The expansion reuses all **1,560 previous captures and 8,838 records**, adding **890 unique directions**. Six pilots are part of that set and reused by bulk collection. Two concurrent searches, resumable captures, source timestamps and page hashes; stop on access challenges. No additional dates, paid sources, automatic refresh, live tracking, invented schedules or connecting itineraries. One bounded follow-up may recheck only new empty directions whose reverse query returned flights; earlier captures stay untouched.

All new and existing captured quotes are **USD**, including domestic flights, for one adult, economy, one-way. Keep the cheapest verified returned quote for each exact flight. No implicit currency conversion; missing/unverified quotes show **Price unavailable**. Distinct flight numbers remain distinct; matching times do not imply codeshares.

## Replay and filters

**North America · Flights** opens on **Both**, with Domestic / International, airline/code, exact-airport, traffic-direction and From country / To country filters. Puerto Rico retains ISO **PR** in the catalogue and country selector; **PR → US** is an explicit flight-jurisdiction mapping for domestic/international classification and coverage accounting. SJU → DO is international. SJO and SJU are separate airport identities. SDQ and PUJ remain separate too.

The initial map fits Hawaii, Canada, Mexico, Central America and the selected Caribbean islands. Reuses local departures/arrivals, Destinations, fullscreen pagination/back, flight previews, explicit seeking, station visibility and frequency lines. Selection filters must constrain the actual services as well as drawn lines.

The timeline remains Eastern time. It begins at **2026-11-02 04:00 UTC**, midnight at Atlantic-time airports (23:00 EST on 1 November), and extends through every captured overnight arrival and the final origin-local midnight. This preserves early SJU/AUA/DO departures and late Hawaii/West Coast departures. Airport boards show their own local date and zone. The 16-hour source-duration ceiling remains regional only; other domestic profiles are unchanged.

[B.C. remains at UTC−7](https://www2.gov.bc.ca/gov/content/governments/celebrating-british-columbia/daylight-saving-time) and [Alberta remains at UTC−6 from November 2026](https://www.alberta.ca/albertas-new-time-system-abt). Their geographic IANA identities remain; validated fixed `replay_timezone` fields freeze the dated snapshot's offsets for collection, validation, boards and previews on older time-zone databases. These overrides are not general annual aliases.

## Preparation and compatibility

Legacy identifiers remain: city `united_states_flights`, scripts `prepare_us_flight_airports.py` / `prepare_us_flights.py`, manifest `data/sources/united_states_flights_routes.json`, reference `data/reference/united_states_flights/2026-11-02.json.gz`, override `SUNTRAIN_UNITED_STATES_FLIGHTS_REFERENCE`, cache `.cache/google-flights-us-usd-v1/`. This standalone explorer does not expand or modify the separate shared International network.

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flight_airports.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --dry-run
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --validate-only
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_us_flights.py --prepare-only
```

Preparation uses deterministic gzip (`mtime=0`). Ranking facts and evidence URLs are committed in `data/sources/north_america_airport_selection.json`; its byte hash is stored in the generated manifest. Rebuilding the manifest requires only cached pinned FAA/OurAirports downloads and committed reviewed facts, not live ranking-site access. Deleted capture caches require fresh public searches.

## Captured coverage

| Measure | Result |
| --- | ---: |
| Airports planned / searched / returned | 50 / 50 / 50 |
| Unique directional queries | 2,450 |
| Directions returning flights | 1,474 |
| Directions not returned | 976 |
| Failed / missing queries | 0 / 0 |
| Rejected source records | 0 |
| Flight identities | 9,668 |
| Added records | 830 |
| Carriers | 29 |
| Verified USD quotes | 9,553 |
| Price unavailable | 115 |
| Unverified fare-context queries | 6 |

| Scope | Queries | Directions returning flights |
| --- | ---: | ---: |
| Domestic, including US–Puerto Rico | 972 | 866 |
| International | 1,478 | 608 |

For the newly added airports, each origin was searched against all 49 other selected airports. These counts cover this bounded set only; they are not complete airport departure boards.

| Airport | Directions returning departures | Departures | Arrivals | USD departure quotes |
| --- | ---: | ---: | ---: | ---: |
| PTY | 32 | 97 | 98 | 97 |
| SJU | 20 | 88 | 88 | 88 |
| PUJ | 21 | 55 | 56 | 55 |
| SJO | 17 | 41 | 37 | 38 |
| SDQ | 12 | 33 | 32 | 33 |
| SAL | 15 | 40 | 41 | 37 |
| GUA | 12 | 31 | 32 | 29 |
| MBJ | 13 | 28 | 28 | 28 |
| NAS | 13 | 37 | 36 | 36 |
| AUA | 12 | 23 | 22 | 23 |

| Carrier code | Records |
| --- | ---: |
| AA | 2,233 |
| DL | 1,828 |
| UA | 1,808 |
| WN | 894 |
| B6 | 511 |
| AC | 458 |
| F9 | 437 |
| AS | 395 |
| AM | 183 |
| CM | 182 |
| WS | 172 |
| Y4 | 141 |
| VB | 138 |
| PD | 67 |
| AV | 65 |
| F8 | 44 |
| SY | 35 |
| DM | 16 |
| TS | 14 |
| S6 | 10 |
| UP | 10 |
| MX | 6 |
| Q6 | 6 |
| N3 | 5 |
| XE | 4 |
| G4 | 2 |
| WU | 2 |
| 4N | 1 |
| AR | 1 |

The 890 new directions initially returned 295 directions with flights and 595 empty responses. A single follow-up checked **19** new empty directions with a returned reverse, recovering **20 records across 10 directions**. Total new page requests: **909**, across **890 unique queries**. All **1,560 baseline queries**, **8,838 baseline records** and **40 baseline airport identities** remain unchanged. The earlier US-only baseline of 870 captures and 7,178 records is consequently preserved too.

Retained captures span **2026-10-26T22:00:11.634536+00:00–2026-10-26T23:58:39.703162+00:00 UTC**. The final replay window is **2026-11-02T04:00:00+00:00 → 2026-11-03T15:41:01+00:00**. Bundle: **489,193 bytes**, SHA256 **`0e0b687eac238e34ea87df728c9fa42f3d35900c7386565b06451b8dd565d4ef`**. Rebuilding from cached captures produces identical bytes. Original new empty responses, follow-up captures and logs are retained under `.cache/us-flights-audit/`; the earlier CA/MX audit remains there separately.

**Empty means not returned, never no service.** Query completion does not establish all flights were captured. Other airports, other dates, connecting trips, unreturned flights and unreturned quotes remain gaps. Departures on other origin-local dates are excluded, even when they arrive on 2 November. Stable colours are assigned to returned regional carriers; unfamiliar carrier codes retain the deterministic fallback.

## Validation

**289 Python regressions passed**, covering shared flight preparation/replay, international-network compatibility, Melbourne/transit, HTTP and localisation. **23 focused tests passed** for the regional manifest, USD-only/cheapest fares, dates, exact identities, frozen Canadian offsets, Atlantic midnight, Puerto Rico scope accounting, durations, duplicates, partial/failed queries, deterministic preparation, HTTP caching and date rejection. **102 JavaScript tests passed**.

Browser checks passed for **all fifty airport boards and all 29 carriers**, Domestic / International / Both, PR ↔ US country filtering and domestic classification, Central American and Caribbean country pairs, USD fares, local board offsets, exact-airport directions, departures/arrivals/Destinations, fullscreen pagination/back, preview without implicit seeking, frequency totals, station visibility, themes, Indonesian and 390px mobile layout. The map bounds include Panama and San Juan, and the replay begins at Atlantic midnight. Australia flights and Melbourne transit retain their 24-hour windows. No browser page errors. Unrelated working files remain unchanged.
