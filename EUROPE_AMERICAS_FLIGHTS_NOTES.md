# Europe–Americas flights

## Efficient scope

**Zero new Google Flights searches.** The existing European group cache already contains all **444** sourced directional queries needed for this first connection view, on **2 November 2026**. Reuse those exact captures rather than searching every possible airport combination or repeating a query per airline/date.

The manifest intersects the **explicit published airport pairs** in `europe_groups_routes.json` with the existing 77-airport Americas catalogue. This yields **14 European gateways and 58 Americas airports: 72 catalogued airports**. It does not create combinations from a hub's destination list or assume that every European airport connects to every Americas airport.

The route evidence remains the pinned [Great Circle Pro](https://www.gcpromap.com/) airline route maps and earlier dated candidate supplements documented in [Europe group notes](EUROPE_GROUPS_NOTES.md). `data/sources/europe_americas_flights_routes.json` records the exact directional pairs, discovery brands, source URLs, original document hashes, input manifest hashes, airport identities and zones. Its route hash covers normalized evidence and input hashes, not an unrecorded fresh webpage download. The maps' July 2026–June 2027 period can contain seasonal or future routes; it supplies candidates, not dated service proof.

The initial footprint follows the existing nine flag-carrier discovery maps. It therefore omits other routes and gateways, including routes discoverable only through airlines outside those maps. **It is not comprehensive Europe–Americas coverage.** The original route-discovery airline roster restricts candidates, not the airlines retained from each dated query.

## All returned airlines, original prices

The older Europe view retains twelve selected airline brands. Its underlying Google captures also contain other airlines. This new connection view retains **all valid returned airlines on the selected routes**, including American, United, Delta, Air Canada, LATAM, Virgin Atlantic and others, without inferring airline ownership or codeshares.

The new view has **748 flights / 31 source carrier codes**. **743 verified EUR prices**, **5 unavailable prices**. Prices are reused original one-adult, economy, one-way quotes, with the cheapest returned quote for the exact source flight. No currency conversion, USD relabelling, live fare claim or fresh price request. Unknown aircraft remain unknown; distinct source flight numbers remain distinct.

Of the 444 cached queries, **336** returned flights and **108** returned no direct records. **Zero failed/missing queries, rejected records or unverified fare contexts**. **68 airports returned flights**. CTG, GEO, PUJ and YEG remain in the catalogue, map and airport choices with explicit capture-gap boards. Empty means not returned for the sourced network/date, never no service.

Source captures retain their original timestamps: **26 October 2026, 20:40:31–21:39:05 UTC**. Each prepared query includes the original capture context, source page hash, reused cache path and raw capture byte hash. The raw query caches are read without modification.

## Dates and airport identity

Only the origin-local departure date **2 November 2026** is included. No adjacent-date searches or automatic refresh. The UTC replay spans every selected origin-local day and all dated overnight arrivals; boards display the airport's own local date/time. This includes valid late departures that fell outside the older Europe view's midnight-to-midnight UTC window.

The previous Europe view contains **314** of these same flight identities. Their timings, airline codes, aircraft and quotes are preserved. The difference comes from other returned airlines and the wider origin-local-day replay boundary, rather than new searches. The original Europe, Americas, North America, South America, country views and shared International network retain their existing archives and behavior.

Exact airport identities must agree in ICAO, country and coordinates across the source catalogues. LHR/LGW and JFK/EWR remain separate; LGA and other unlisted city airports are not substituted. This view retains the original European captures' IANA parser/board zones, including Canadian airports. It does not reinterpret those timestamps using the separate North America view's dated Canadian replay-zone overrides.

## Experience

Choose **Europe–Americas · Flights**. This is an international connection view, so there is no empty Domestic toggle. Existing country, airline/code and exact-airport filters, moving planes, airport visibility toggle, departures/arrivals, Destinations, fullscreen pagination/back, frequency lines, themes and English/Indonesian copy are reused. The initial map fits the selected endpoints on both sides of the Atlantic. Paths are illustrative, not recorded flight tracks.

## Offline preparation

```bash
# Build only the evidenced candidate intersection; no network requests.
.venv/bin/python scripts/prepare_europe_americas_routes.py

# Audit exact-date compatible captures before preparation.
.venv/bin/python scripts/prepare_europe_americas_flights.py --dry-run

# Prepare offline from existing cached captures.
.venv/bin/python scripts/prepare_europe_americas_flights.py
```

Main cache: `.cache/google-flights-europe-groups-eur-v1/`; compatible legacy fallback: `.cache/google-flights-europe-eur-v1/`. The preparation command has **no network collector**. If caches are missing it records exact uncollected queries; a future recollection should request only those sourced directions and the same single date.

Preparation validates exact query and segment identities, successful result status, absence of parser rejections, source-aware timestamps, original parser/duration context, origin-local dates and verified EUR fare context. Incompatible captures fail rather than silently becoming usable or being relabelled. Temporary reconstructed query files are removed after preparation; source caches are untouched.

Prepared reference: `data/reference/europe_americas_flights/2026-11-02.json.gz`, **78,600 bytes**, SHA256 `2a41a0ca0369d3b6b080a0f9bb60f7cfa76c1fca883bda731314cb6ef2698f33`. Gzip output is deterministic and published atomically. `SUNTRAIN_EUROPE_AMERICAS_FLIGHTS_REFERENCE` can override it for tests.

Deleting raw caches leaves the committed replay working, but offline reconstruction then needs the retained captures or a deliberate, bounded recollection. No additional raw-cache copy is stored for this feature.

## European gateway coverage

Each flight is counted once at its European endpoint. Counts describe this captured shortlist/date, not the airport's full timetable.

| European airport | Cached directions | Directions returning flights | Flights | EUR prices |
| --- | ---: | ---: | ---: | ---: |
| AMS | 66 | 44 | 74 | 74 |
| BCN | 14 | 7 | 11 | 11 |
| BRU | 4 | 3 | 3 | 3 |
| CDG | 68 | 54 | 128 | 128 |
| DUB | 34 | 19 | 43 | 43 |
| FRA | 48 | 40 | 74 | 74 |
| GVA | 2 | 2 | 2 | 2 |
| LGW | 10 | 4 | 5 | 5 |
| LHR | 64 | 56 | 212 | 212 |
| MAD | 60 | 48 | 115 | 110 |
| MUC | 34 | 27 | 39 | 39 |
| SNN | 4 | 4 | 4 | 4 |
| VIE | 14 | 8 | 8 | 8 |
| ZRH | 22 | 20 | 30 | 30 |

## Validation

**314 Python regressions** and **105 JavaScript tests** passed. Browser checks passed for all **72 exact-airport departure/arrival boards**, country and airline filters, international-only controls, EUR quotes, fullscreen pagination/back, Destinations, frequency counts, all five themes, Indonesian and 390px mobile layout. Existing Europe, Americas (11,783 services), North America (9,668), South America (1,629), Australian flights and Melbourne transit smoke checks passed.

Offline reconstruction is byte-identical. Original Europe and Americas archives remain unchanged. Audit logs and screenshots are local under `.cache/europe-americas-flights-audit/`.
