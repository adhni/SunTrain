# Oman, Kuwait, Bahrain and Jordan flights

Four separate country views extend the Saudi branch. **Egypt is not expanded**: its existing Africa snapshot remains unchanged. Saudi Arabia retains its own prepared view and archive.

All four additions use **2 November 2026 departures in each origin airport's local time**, including dated overnight arrivals. New offers use **USD, one adult, economy, one-way**, selecting the cheapest verified returned offer per exact nonstop flight. Reused USD/EUR/MYR offers retain their original amount, currency, timestamp and context. Missing/unverified prices remain unavailable. Schedules and prices are dated captures, not live availability or observed operations.

| View | Reviewed national airports | Replay zone | Scope |
| --- | --- | --- | --- |
| Oman | MCT, SLL, KHS, DQM, OHS, MSH | Asia/Muscat, UTC+4 | Published domestic and worldwide international candidates |
| Kuwait | KWI | Asia/Kuwait, UTC+3 | Worldwide international candidates; no invented domestic flights |
| Bahrain | BAH | Asia/Bahrain, UTC+3 | Worldwide international candidates; no invented domestic flights |
| Jordan | AMM, AQJ, ADJ | Asia/Amman, UTC+3 | Published domestic and worldwide international candidates |

AMM/OJAI (Queen Alia), ADJ/OJAM (Marka) and AQJ/OJAQ (Aqaba) remain separate. Pinned OurAirports identities and identity-matched OpenFlights zones are retained. Jordan uses year-round UTC+3, including the replay date. Foreign airport clocks remain local. Paths are illustrative. Reuses airline/airport/country filters, compact planes, local departure/arrival boards, Destinations, fullscreen, frequency lines, themes and English/Indonesian copy.

## Route evidence and gaps

Published Great Circle Pro airport maps were available for [Muscat](https://www.gcpromap.com/airports/mct/), [Kuwait](https://www.gcpromap.com/airports/kwi/), [Bahrain](https://www.gcpromap.com/airports/bah/) and [Amman](https://www.gcpromap.com/airports/amm/). These secondary maps describe July 2026–June 2027, updated 12 October 2026. They supply candidates, not dated service evidence. The other seven reviewed map pages returned 404; regional routes absent from available maps remain gaps.

Public FlightConnections nonstop destination sections for [Salalah](https://www.flightconnections.com/flights-from-salalah-sll) (16 candidates) and [Aqaba](https://www.flightconnections.com/flights-from-aqaba-aqj) (five candidates) supplement missing maps. Only their nonstop sections were used, including seasonal/zero-frequency destinations; connecting suggestions were excluded. Exact IATA labels were transcribed from successful public web-tool inspections. A later direct HTTP download was access-limited and stopped without retry. The frozen discovery documents explicitly distinguish **normalized fact hashes** from raw document hashes; no original-HTML hash is claimed for these supplements. Discovery refresh preserves these reviewed supplements.

Official [Oman Air destinations](https://services.omanair.com/in/en/oman-air-destinations) and [Royal Jordanian destinations](https://www.rj.com/?tab=4) were inspected as network cross-checks. The [SalamAir schedule page](https://www.salamair.com/en/plan/flight-schedule) also carried an operational cancellation notice affecting Riyadh/Dammam through 8 November 2026. This replay captures returned dated schedules and fares; it does not reconstruct disruptions or establish that a captured flight operated. Frequency-only statements do not become invented dated flights.

Country manifests contain exact airport evidence, source hashes, reusable capture paths, unresolved identities and missing map pages. ALY is unresolved and omitted, never silently changed to HBE. Other countries' existing manifests can contribute candidate pairs, including historical/empty pairs; a completed query is not proof of operation. Compatible positive captures beyond the reviewed national-airport footprint remain reuse-only.

Initial budget: **710 country-direction queries**, **218 captures reused**, **492 missing searches**. Collection runs countries sequentially with **two concurrent searches**, seeding again before each country so overlapping queries captured earlier in the run can be reused. No Cartesian airport, per-airline, adjacent-day or weekly expansion. Empty results mean **not returned**, never **no service**. Source challenges stop collection without retries, preserving successful captures and reporting missing queries. Google collection is preparation-only.

## Rebuilding

```bash
.venv/bin/python scripts/discover_arabia_jordan_flights.py
.venv/bin/python scripts/prepare_arabia_jordan_routes.py
.venv/bin/python scripts/prepare_arabia_jordan_flights.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_arabia_jordan_flights.py
.venv/bin/python scripts/prepare_arabia_jordan_flights.py --prepare-only
```

Frozen discovery and manifests are under `data/sources/{oman,kuwait,bahrain,jordan}_flights_*.json`. Captures live under `.cache/google-flights-{country}-usd-v1/`, with new USD queries in `new-usd/`; original source caches remain intact. Shared airport source downloads and hashes are recorded in each manifest. Prepared deterministic gzip files live at `data/reference/{country}_flights/2026-11-02.json.gz`. Runtime needs only the bundles. The shared International network is unchanged.

## Captured coverage

| View | Flights | Domestic | International | Priced | Captured queries | Reused queries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Oman | 211 | 16 | 195 | 201 | 220 | 66 |
| Kuwait | 167 | 0 | 167 | 166 | 184 | 49 |
| Bahrain | 173 | 0 | 173 | 171 | 112 | 53 |
| Jordan | 179 | 6 | 173 | 168 | 194 | 66 |

These are per-view counts; flights and route queries between these countries can appear in two views and must not be added as unique worldwide totals. All **710 country-direction entries** were captured. After cross-country reuse, collection made **476 new searches**, saving 16 from the initial budget. **234 entries** use compatible reused captures. There were zero failed, rejected or unattempted queries/records.

- Oman returned flights at **MCT, SLL and DQM**. Domestic coverage is four returning directions, with 16 flights; KHS, OHS, MSH and other minor-field candidates did not return flights. This is a capture gap, not proof of no service.
- Kuwait returned **83 directions**; **101** were empty. Bahrain returned **87 directions**; **25** were empty. Both views contain international flights only.
- Jordan returned flights at **AMM, AQJ and ADJ**, with six domestic flights on AMM↔AQJ. AMM and ADJ are kept distinct; no AMM↔ADJ flight was returned. **86 directions** returned flights; **108** were empty.
- Oman returned **114 directions**; **106** were empty. None of the four views had an empty domestic direction whose reverse returned flights, so no extra verification searches were made.
- Captured prices: Oman **197 USD / 4 MYR**, with 10 unpriced flights; Kuwait **166 USD**, one unpriced; Bahrain **168 USD / 3 EUR**, two unpriced; Jordan **162 USD / 6 EUR**, 11 unpriced. All new captures request USD.

- **Oman**: 30,748 bytes, SHA256 `a35159aaa5dc6b2a70f657061f6f0f2314bc7535f85dfed0d4638c0a1626901e`.
- **Kuwait**: 26,157 bytes, SHA256 `a2d12fd84e57f0836cba2200419a9ebdb9c0ca71daa377cec5e9e97412b1ac18`.
- **Bahrain**: 20,270 bytes, SHA256 `0b0318785573558245d56ad378ada6d3400a0308f24433885022f34c757b87e6`.
- **Jordan**: 27,846 bytes, SHA256 `2d82442791bd0e77c80c0161ca8df7f9a6e22913ad186878088f2a59f7686133`.

All four archives reproduce byte-for-byte from cached captures. Saudi's prior archive also rebuilds byte-for-byte; the existing Saudi, Türkiye and Africa reference hashes are unchanged. Validation passed: **125 Python tests** across the new countries, Saudi, Türkiye, Africa, shared Google parsing/fares, Europe, Australia and replay HTTP; **105 JavaScript tests**; and all four offline byte-identical rebuilds. Browser checks cover all four country maps, every returned national airport board (DQM/MCT/SLL, KWI, BAH, ADJ/AMM/AQJ), airport/carrier/scope filters, departures/arrivals, Destinations, fullscreen, frequency totals, all five themes, Indonesian, mobile, and existing Saudi/Türkiye/Africa/Melbourne views.
