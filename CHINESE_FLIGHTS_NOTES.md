# Mainland Chinese flights

## First-pass scope

**China · Flights** replays domestic schedules for **2 November 2026**, using **China standard time, UTC+8 (`Asia/Shanghai`)**, including Ürümqi. Airport board/capture labels use **CST** in this explicitly Chinese context; the replay clock and explanatory copy spell out **China time (UTC+8)**. Do not replace Ürümqi's airline schedule zone with `Asia/Urumqi` (UTC+6).

This pass searches **30 major mainland airports** and **276 directional route candidates**, with both **1 and 2 November** searched to retain flights arriving after midnight: **552 planned queries**. Small airports and international/regional connections are deferred. Airport groups are:

| Group | Airports |
| --- | --- |
| North | PEK, PKX, TSN |
| Northeast | SHE, DLC, HRB |
| East | SHA, PVG, HGH, NKG, XMN, FOC, TAO, TNA |
| Central | WUH, CSX, CGO |
| South | CAN, SZX, NNG, HAK, SYX |
| Southwest | CTU, TFU, CKG, KMG, KWE |
| Northwest | XIY, URC, LHW |

**PEK/PKX, SHA/PVG and CTU/TFU remain separate exact airports.** No BJS/metropolitan queries, closed Nanyuan substitutions, same-city airport-to-airport searches or inferred service between every pair of selected airports. Historical city-pair entries are explicitly expanded to the selected exact airports as search candidates; that does not assert every combination operates. Cross-border/regional destinations such as HKG, MFM and TPE are outside this domestic manifest.

The view reuses compact planes, airline-code/airport filters, departures/arrivals, Destinations, fullscreen pagination/back, fare previews, explicit timeline seeking, frequency lines, airport visibility, themes, English/Indonesian copy and mobile layout. International/Both stays hidden until a later validated dataset exists. Paths illustrate connections, not recorded aircraft tracks.

## Evidence and price limitations

Only dated returned segments with departure and arrival timestamps become flights. Published route tables are search candidates. Historical route/frequency caps, product fare tables and advertised airline networks never create replay timings, present-day frequency or prices.

- [Air China 2025 two-city product route table](https://webresource.airchina.com.cn/zh-CN/content/marketing/yxhdymjh/2025scck/) provides explicit airport pairs. Its product expired before this replay date; it is candidate evidence only. Reviewed HTML SHA-256: `0d9e3261fccd255474e935b53d118fc777e49402c6f819c4b7c794d0883b3450`.
- [CAAC's historical domestic-route table](https://www.caac.gov.cn/XXGK/XXGK/TZTG/201811/P020181115387162391198.pdf), in a 2018 regulatory publication, supplies a focused city-pair list. Historical city entries are expanded explicitly to PEK/PKX, SHA/PVG and CTU/TFU where applicable. These later airports are search targets, not a claim that they appeared in the historical table. Do not use the publication's weekly limits as flight frequencies.
- [CAAC's June 2026 Guangzhou–Ürümqi–Frankfurt announcement](https://www.caac.gov.cn/English/BeltAndRoad/202606/t20260604_230981.html) supplies a CAN–URC domestic-leg candidate. Exact domestic dated results, not the announcement, establish retained standalone segments.
- [China Eastern January 2026 report](https://www.ceair.com/global/static/AboutChinaEasternAirlines/intoEasternAirlines/InvestorRelations/announcement/ShanghaiExchangeReleased/shExcReleased2026/202601/P020260115596082764942.pdf) supplies SHA–LHW; [Spring's Shanghai–Lanzhou route page](https://flights.ch.com/flight-date/SHA-LHW/) explicitly identifies **Pudong**, despite its SHA city slug, and supplies PVG–LHW. Older displayed dates remain candidates only. Do not infer an aircraft type from a route announcement.
- Exact airport coordinates/identities use OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256 `a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`. All selected airport schedules explicitly use `Asia/Shanghai`.
- Public exact-IATA Google Flights searches provide dated segment and fare evidence. Queries retain their URLs, dates, UTC capture timestamps, statuses, rejection diagnostics and fare-context failures. The curated route-evidence hash is deterministic and explicitly not a raw-page hash.

Prices are **the cheapest returned positive USD quote per exact flight**, for **one adult, economy, one-way**, with verified currency/cabin/passenger context. Do not relabel CNY, invent quotes, substitute connecting-trip minima or apply the expired Air China product discounts. Required source-reported taxes/fees are included; baggage and optional services can cost extra. Captured fares can change.

China has a material source limitation: many schedules appear on Google Flights with **“Price unavailable”**. Representative PEK–SHA inspection confirmed unavailable Air China and China Eastern quotes on the page itself; the parser was not simply omitting displayed prices. Keep these flights visible with an unavailable fare. A complete query run is not complete fare coverage or a complete national schedule.

The collector keeps two workers, resumable normalized captures, original source timestamps, a one-minute/eight-hour duration range and validation against the source duration. It deduplicates repeated exact identities while preserving distinct flight numbers; matching times alone do not establish codeshares or physical aircraft movements. Unknown aircraft stay unknown. Stop on access challenges, retaining successful captures and recording missing/failed queries. Empty results mean “not returned”, never “no service”.

## Rebuilding and local storage

```bash
.venv/bin/python scripts/prepare_chinese_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_chinese_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_chinese_flights.py
# Offline, deterministic preparation from successful normalized captures:
.venv/bin/python scripts/prepare_chinese_flights.py --prepare-only
```

The wrapper and generic `--country CN` domestic collector use `.cache/google-flights-china/`. Probe captures never publish a misleading small-manifest snapshot. Runtime reads `data/reference/china_flights/2026-11-02.json.gz` and generated selected-day HTTP caches. Preparation uses fixed gzip `mtime=0`, stable ordering and atomic replacement. No search or automatic refresh runs in the app.

`.cache/china-flights-audit/` holds source evidence, the representative fare-page inspection, tests and screenshots. The OurAirports CSV is reused from `.cache/australia-flights-audit/`; the builder can re-download its pinned source. Curated route manifest rebuilding needs no raw website fetch. Deleting normalized flight captures saves local space but requires new public searches for later preparation; the committed replay continues working.

## Later expansion

After this domestic first pass, add further published domestic pairs and smaller airports only when requested. International/regional work should use a separate manifest/cache/bundle in the same country view, enabling Domestic / International / Both only after actual data exists. Prioritise verified passenger routes from the major gateways; separate cargo routes, announced future service and connecting itineraries. Reuse compatible raw USD captures from other country collections only for matching airport/date/adult/cabin/one-way context, preserving timestamps and re-filtering to the UTC+8 replay window. Use explicit overseas IANA zones, a 24-hour international duration ceiling, adjacent origin-local dates and half-open board event windows. Do not merge prepared country bundles with different day windows or silently reuse MYR/CNY/unpriced records as USD quotes.

## Actual coverage and validation

Captured **25 October 2026**, for the **2 November 2026** UTC+8 replay window:

- **3,246 dated flight records**, **31 carriers**, **30 airports**, **261 directional routes** overlapping the window. This includes **183 previous-day departures** still airborne after midnight and **3,063 departures on 2 November**. Distinct flight numbers are retained without inferring physical aircraft or codeshares.
- **1,312 priced records** (40.4%); **1,934 without a returned price**. Of departures on 2 November, **1,239** have USD quotes. Missing prices remain explicitly unavailable.
- **552/552 queries captured**, covering **276/276 planned directional routes** and **30/30 selected airports**. **521 queries returned results**; **31 returned no matching direct flights**, spanning 15 routes without retained results. This is not evidence those routes have no service.
- **Zero failed/missing queries, rejected records, fare-context failures or unresolved selected airports**. The deliberately limited route manifest leaves many mainland routes and smaller airports unsearched. Nationwide completeness is not a release claim.

Counts below are **2 November departures by origin region**, excluding the 183 previous-day overlapping flights:

| Origin region | Airports returned / selected | Departures | With USD fare |
| --- | --- | ---: | ---: |
| North | 3 / 3 | 614 | 258 |
| Northeast | 3 / 3 | 124 | 52 |
| East | 8 / 8 | 915 | 323 |
| Central | 3 / 3 | 108 | 40 |
| South | 5 / 5 | 658 | 359 |
| Southwest | 5 / 5 | 505 | 149 |
| Northwest | 3 / 3 | 139 | 58 |

Prepared gzip: **117,752 bytes**, SHA-256 `dc3e7c64c8b678d65021cc4dca556c9e438523ddef68fc55d914f1675e461c22`. Rebuilding the manifest and preparing from normalized cached captures both reproduce byte-for-byte output.

Validation: **179 Python tests** passed across China, existing flight countries, Melbourne/shared replay, HTTP caching/date rejection, Japan rail and app/i18n; **90 JavaScript tests** passed. Local Chrome checked exact PEK/PKX, SHA/PVG, CTU/TFU, CAN and URC departure/arrival boards; China UTC+8 clocks and captured-fare timestamps; priced/unpriced previews; combined airport/carrier filters and empty intersections; visibility; fullscreen/back/pagination; Destinations; stable frequency totals during seeking; all five themes; Indonesian; mobile width; one cached replay download; no page errors; and switching back to Japan's separate JST view. Desktop/map/mobile screenshots were visually inspected. Logs and screenshots remain under `.cache/china-flights-audit/` and `.cache/china-flights-*.png`.
