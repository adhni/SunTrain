# Saudi Arabia flights

Saudi Arabia · Flights replays departures on **2 November 2026 in each origin airport's local time**, including dated overnight arrivals. The timeline uses **Asia/Riyadh / UTC+3**; foreign airport boards retain airport-local time. This is a partial dated schedule capture, not live tracking.

## Sourced footprint

- **Domestic:** 140 published candidate directions across 28 civilian airports, including regional destinations, Neom Bay (NUM) and Red Sea International (RSI). Both directions are searched separately; no Cartesian airport expansion.
- **International:** sourced worldwide nonstop candidates from **RUH, JED, DMM and MED**, across all returned airlines. Other Saudi international routes are retained when compatible existing captures are available; they do not trigger new searches.
- **One date only:** no adjacent-day searches, weekly collection or per-airline searches. Initial budget: **880 directions**, **159 compatible captures reused**, **721 new searches**. Of the 880 directions, **854** permit new collection; the other **26** are reuse-only.
- Initial map fits Saudi Arabia. Reuses compact planes, exact airport and airline filters, country filters, Domestic/International/Both, departures/arrivals, Destinations, fullscreen boards, fare previews, frequency lines, themes, and English/Indonesian copy. Selecting an airport fits its connections; clearing it restores the country view.

## Discovery and identity

[Frozen route-map discovery](data/sources/saudi_flights_discovery.json) records exact IATA labels, document URLs and SHA256 hashes. Published maps were available for [Riyadh](https://www.gcpromap.com/airports/ruh/), [Jeddah](https://www.gcpromap.com/airports/jed/), [Dammam](https://www.gcpromap.com/airports/dmm/), [Madinah](https://www.gcpromap.com/airports/med/) and [Abha](https://www.gcpromap.com/airports/ahb/). Their schedule period is July 2026–June 2027, updated 12 October 2026. These secondary seasonal maps are candidates, not dated flight evidence.

The other **23 airport-map pages returned HTTP 404**. All 28 civilian airport candidates nevertheless appear in sourced domestic routes from the available hub maps; the absence of a smaller airport's own map leaves potential additional routes unverified. This is explicitly reported, not treated as an empty schedule or proof of no service. Military airports are excluded from the 28-airport discovery list.

The official [Madinah Airport route directory](https://madinahairport.com/en-EN/passenger/flight/page/airport-route-map) and [flynas route map](https://www.flynas.com/en/route-map) were inspected as network cross-checks. City lists do not substitute for exact-airport dated searches. Older published routes and seasonal service do not establish operation on our chosen Monday.

The [route manifest](data/sources/saudi_flights_routes.json) pins candidate evidence, compatible reusable capture paths, source hashes, airport identities, time zones and deferred international directions. Airports use pinned OurAirports and identity-matched OpenFlights data, with explicit IANA overrides. Saudi airports use **Asia/Riyadh year-round**, including the newer RSI/OERS and NUM/OENN. RUH/OERK, JED/OEJN, DMM/OEDF and MED/OEMA remain distinct. Foreign exceptions include HMB/Africa/Cairo, KSQ/Asia/Samarkand and NMA/Asia/Tashkent. ALY cannot be resolved to a unique active airport and is omitted; it is never silently replaced with HBE.

## Capture, prices and replay

Public Google Flights searches use exact airport codes, **one adult, economy, one way**, with **USD for new captures**. The lowest verified returned offer for an exact nonstop flight is selected. Connecting itinerary totals are excluded. Missing/unverified quotes remain unavailable. Reused USD/EUR/MYR quotes retain their original currency, amount, timestamp and context; no conversion or relabelling. Fares are captured offers and may exclude optional charges.

Only dated departure/arrival records are retained. Duration must agree with airport-local clocks and source duration, between one minute and 24 hours. All departures must belong to 2 November locally at the origin. Flight identities include date, number and exact airport pair; repeated identical records collapse, conflicts fail, and distinct flight numbers remain distinct without inferred codeshares. Unknown aircraft stay unknown. Paths are illustrative.

The shared sourced-route builder and collector preserve Türkiye's CLI defaults and snapshots. Saudi Arabia is a standalone view; the shared International network and other countries' snapshots are unchanged. Previous-day arrivals, other weekdays, seasonal flights, source omissions and routes absent from the reviewed maps remain gaps. Completing candidate queries is not nationwide completeness. Empty results always mean **not returned**, never **no service**.

## Rebuilding and caches

```bash
# Refresh route-map evidence only when intentionally reviewing sources:
.venv/bin/python scripts/discover_saudi_flights.py

# Build candidates from frozen evidence and pinned airport catalogues:
.venv/bin/python scripts/prepare_saudi_routes.py

# Reuse compatible captures, then inspect the remaining one-date budget:
.venv/bin/python scripts/prepare_saudi_flights.py --seed --dry-run

# Resume missing queries at two concurrent searches:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_saudi_flights.py

# Reproduce the prepared gzip offline:
.venv/bin/python scripts/prepare_saudi_flights.py --prepare-only
```

Source documents live in `.cache/saudi-flights-audit/`; captures in `.cache/google-flights-saudi-usd-v1/`, with new USD captures in `new-usd/`. Original source caches are copied intact. Access challenges stop collection and preserve completed captures without retrying the challenge. Failed/missing queries, rejected records and unresolved airports remain reported. Deterministic gzip (`mtime=0`) is validated before atomic publication to `data/reference/saudi_flights/2026-11-02.json.gz`. Runtime reads that bundled file; it performs no searches.

## Actual coverage and validation

The prepared snapshot contains **1,153 unique flight identities across 51 carrier codes**:

| Scope | Flights | Directions returning flights | Priced flights |
| --- | ---: | ---: | ---: |
| Domestic | 396 | 91 | 396 |
| International | 757 | 290 | 701 |
| Total | 1,153 | 381 | 1,097 |

- **880/880 directional queries captured:** 159 reused and 721 newly collected unique queries. **499** returned no matching flights; zero failed, rejected or unattempted queries/records.
- Domestic flights returned at **24 of 28 airport candidates** and on **91 of 140 directions**. **EJH, HOF, NUM and TUI** returned no domestic flights. These are recorded capture gaps, not proof of no service. Regional-to-regional routes absent from the five available airport maps remain unverified.
- **103 of 202 catalogued airports** returned flights, across **45 countries/territories**. The catalogue retains unreturned airports for explicit selection and coverage accounting.
- Prices: **1,078 USD**, **10 EUR**, **9 MYR**; **56 flights** have no verified quote. All **396 domestic flights** have verified USD fares.
- One targeted verification pass made **8 additional searches** for empty domestic captures whose reverse returned flights. Seven yielded **11 additional flights**: ABT→RUH (2), AHB→MED (1), AQI→JED (1), EAM→DMM (1), RUH→ULH (1), TUU→DMM (2), TUU→MED (3). TUU→AHB remained empty. Other empty results were not repeatedly searched.
- Superseded query captures are preserved in `.cache/saudi-flights-audit/domestic-rechecks/originals/`; verification captures are beside that folder. Snapshot query metadata records original capture timestamps, hashes and counts, plus verification hashes/counts, in `domestic_recheck`.
- Gzip: **113,671 bytes / about 111 KiB**, with deterministic SHA256 `97a66a2ac2a7b4dc89af5cb4651c6b58a87962180dd65b34c2e88083cbd4cfa6`.

Validation covers exact civilian airport identities and sourced footprint, all 28 Saudi airport candidates, year-round UTC+3, airport-local origin dates, overnight and long-haul duration checks, original fare currencies, deterministic offline preparation, missing queries, gzip/ETag/date rejection, translated notes, and distinct SV/XY/F3 colours. The prior Türkiye snapshot rebuilds byte-for-byte unchanged through the shared collector.

Validation passed: **111 Python tests** (Saudi, Türkiye, Africa, shared Google parsing/prices, Europe, Australia and replay HTTP) and **105 JavaScript tests**. Offline Saudi preparation reproduced the gzip byte-for-byte. The existing Europe snapshot's dated Saudi flight identity is retained; other reference snapshots are unchanged.

The complete browser check covers all four main hubs plus returned AHB/GIZ/RSI boards, scopes, countries, carriers, departures/arrivals, Destinations, USD fares, fullscreen/back, frequency counts, airport visibility, all five themes, Indonesian, mobile and existing Türkiye/Africa/Europe/Americas/Australia/Melbourne views. Visual review found the shared airport-board clock hint fell back to Melbourne for Saudi Arabia and Türkiye; the two UTC+3 zones now show their correct English and Indonesian clock labels.
