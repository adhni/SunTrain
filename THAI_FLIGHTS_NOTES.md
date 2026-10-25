# Thailand domestic and international flights

## Domestic release

Choose **Thailand · Flights** for the **2 November 2026** dated schedule snapshot.
The midnight-to-midnight timeline and airport boards use **Asia/Bangkok, ICT
(UTC+7)**. Fares are the lowest returned positive **USD** quotes for one adult,
economy, one-way, with original capture timestamps. Missing offers remain
unavailable; THB prices are never relabelled or converted. Paths are illustrative,
not recorded flight tracks, and the app performs no live searches or refreshes.

**BKK (Suvarnabhumi) and DMK (Don Mueang) stay separate**, including searches,
filters, boards and flight identities. The release reuses moving planes, airline
codes and exact-airport filters, departure/arrival boards, fullscreen/back and
pagination, Destinations, fare previews without implicit seeking, frequency
lines, airport visibility, themes, English/Indonesian and mobile layout.
Domestic remains the default. International and Both include captured connections
to the other existing SunTrain flight countries and DXB/AUH/DOH. Airport boards
use each airport’s local zone; the Thai replay clock remains ICT. Existing Thailand
SRT and Bangkok rail views retain their original source periods and data.

The manifest contains **30 airports and 112 directional search candidates**:

| Region | Selected airports |
| --- | --- |
| Central | BKK, DMK, HHQ |
| North | CNX, CEI, LPT, NNT, PHS, MAQ, THS |
| Northeast | UTH, UBP, KKC, KOP, SNO, ROI, BFV, LOE |
| East | UTP, TDX |
| South | HKT, KBV, USM, URT, NST, HDY, TST, NAW, CJM, UNN |

Smaller/commuter services such as HGN and PRH are deferred. This is a selected
domestic network, not a claim that all Thai airports, airlines or flights are covered.
No BKK–DMK flights or all-pairs regional searches are invented.

## Sources and preparation

- OurAirports pinned commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
  `a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies exact
  airport codes, identities and coordinates; every selected airport explicitly uses
  Asia/Bangkok.
- [AirAsia's 1 October 2026 BKK reopening and domestic hub list](https://newsroom.airasia.com/news/airasia-is-back-at-suvarnabhumi-direct-flights-resume-oct-1-to-chiang-mai-krabi-and-phuket)
  distinguishes BKK/DMK and lists Chiang Mai's cross-country routes. A small set of
  additional DMK regional and BKK/HKT probes is labelled **supplemental**, not
  represented as published route pairs or proof of current service.
- [Thai Airways' official domestic destination directory](https://www.thaiairways.com/en-bd/content/where-we-fly/thailand/)
  supplies the core BKK network. Unofficial lookalike booking sites are not sources.
- [Bangkok Airways' older Airpass route table](https://www.bangkokair.com/eng/discovery-airpass/route-fare)
  supplies historical Samui, Trat, Sukhothai, Lampang and regional route candidates.
  It is not evidence of November operation. Product prices and timetable assumptions
  are never copied. Bangkok Airways' Bangkok endpoint is explicitly BKK.
- [U-Tapao's domestic timetable page](https://www.utapao.com/apps/domestic.php)
  supplies UTP candidates. Its undated clocks/frequencies never create replay flights.
- Exact-IATA Google Flights captures supply dated nonstop segments and verified
  fare context. Published lists, historical routes and empty searches never create
  flight timings. Empty results mean **not returned**, not **no service**.

Source evidence records each candidate's provenance and whether it is published,
historical or a supplemental probe. The curated evidence hash is not a raw-page
hash. Raw AirAsia/U-Tapao HTML pins are in the manifest; Thai Airways/Bangkok
Airways returned 403 to the local download client and were reviewed through the
web tool, without claiming raw-download hashes or bypassing access checks.

The two-worker collector searches **1 and 2 November**, keeping adjacent-day
flights overlapping the ICT day. Only dated departure/arrival records validated
against the source duration survive. The duration range is one minute to eight
hours. Repeated exact flight identities are deduplicated; distinct flight numbers
remain distinct without guessing codeshares. Unknown aircraft remain unknown.
Access challenges stop collection and retain captures/missing-query diagnostics.
Gzip uses stable ordering, fixed mtime and atomic replacement.

```bash
.venv/bin/python scripts/prepare_thai_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_thai_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_thai_flights.py
.venv/bin/python scripts/prepare_thai_flights.py --prepare-only
```

Runtime reads `data/reference/thailand_flights/2026-11-02.json.gz`, overridable with
`SUNTRAIN_THAILAND_FLIGHTS_REFERENCE`. Normalized resumable queries live in
`.cache/google-flights-thailand/`; deleting those saves local storage but requires
new searches to rebuild. The committed replay continues working. OurAirports is
reused from `.cache/australia-flights-audit/` and can be re-downloaded from its pinned
URL. Curated manifest rebuilding needs no official-page downloads. Audit HTML,
test logs and browser screenshots stay in `.cache/thailand-flights-audit/` and
`.cache/thai-flights-*.png`. Generated replay HTTP caches regenerate.

## International release: selected SunTrain flight locations

The international scope connects Thailand with Australia, Indonesia, Malaysia,
Singapore, India, mainland China, Japan, South Korea and DXB/AUH/DOH. It also
appears in **International network · Flights**. This is selected-country coverage,
not worldwide coverage. BKK/DMK remain separate and exactly one endpoint of each
Thai international record is in Thailand. Domestic data is unchanged.

`data/sources/thailand_international_routes.json` contains **264 directional
candidates across 64 airports**, starting with **176 directions** from existing
international manifests. Thai candidate endpoints are BKK, DMK, HKT, CNX, CEI,
HDY, KBV, URT and USM. Focused East Asian additions use:

- [Thai Airways’ Bangkok–China exact-airport offer directory](https://www.thaiairways.com/flights/en/flights-from-bangkok-to-china).
  The offers are discovery candidates, not proof of nonstop operation or a source
  of November 2 timings/fares.
- [AirAsia’s December 2025 China announcement](https://newsroom.airasia.com/news/nihao-china-airasia-welcomes-the-new-year-with-special-fares),
  whose promotion ends before this replay. Historical city candidates are labelled
  accordingly; Chengdu/Shanghai resolve to TFU/PVG probes, not claimed airport labels.
- [AirAsia’s September 2026 winter expansion](https://newsroom.airasia.com/news/airasia-gears-up-for-high-season-with-major-international-expansion)
  for DMK–Japan/Delhi candidates. Later-November launches do not create Nov 2 flights.
- Official [Narita](https://www.narita-airport.jp/en/discover/citylist/),
  [Haneda](https://tokyo-haneda.com/en/flight/city_list.html?tab=intFlight),
  [Kansai summer 2026](https://assets.kansai-airports.co.jp/551f6859-e_20260324_pressrelease_s26.pdf),
  [Centrair](https://www.centrair.jp/en/),
  [Asiana](https://m.flyasiana.com/C/KR/KO/booking/route) and
  [Air Busan](https://en.airbusan.com/content/individual/booking/route) route lists.
  Bangkok city entries at HND/PUS resolve to BKK candidates. Seasonal lists are
  discovery evidence, not dated schedules.
- Limited China/Korea–HKT/CNX/DMK gateway probes, explicitly marked supplemental.
  The AOT directory provides airport identity context, not published-route evidence.

Both directions are searched, with exact IATA and required adjacent origin-local
dates. The shared collector unions the UTC network window and all country-local
windows with a 24-hour duration ceiling. **452 saved captures were reused and 472
new searches were required**; all 4,313 previous shared queries remain untouched.
New searches request USD. Valid reused USD/MYR quotes keep their original currency,
context and capture timestamp; there is no conversion or numerical comparison
between currencies. Missing prices remain unavailable. Dated nonstop captures
alone establish replay records. Empty results mean not returned, not no service.

```bash
.venv/bin/python scripts/prepare_thai_international_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
.venv/bin/python scripts/prepare_international_network.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

International data is stored once in
`data/reference/international_network/2026-11-02.json.gz`, independently projected
into Thailand’s ICT day and the shared UTC day. No redundant Thai international
bundle is stored. The Thai HTTP revision fingerprints both domestic and shared
references. Older shared archives without a Thai consumer entry leave the overlay
disabled. Custom Thai fixtures remain isolated unless an explicit shared reference
is also supplied. Resumable captures live in `.cache/google-flights-international-network/`;
audit logs and screenshots live in `.cache/thailand-international-audit/`. Deleting
captures requires new searches for rebuilding; committed replays continue working.

## Actual domestic coverage and validation

Captured **25 October 2026**, for **2 November 2026 ICT**:

- **615 dated flights**, **29 airports**, **88 directional routes**, **6 carriers**.
  All 615 depart inside this ICT day; no previous-day flight overlaps the window.
  All **615 have positive captured USD quotes**; this is snapshot availability,
  not a promise that fares remain available or every service was captured.
- **224/224 airport/date queries captured**, **112/112 directional candidates**
  searched across **30 airports**. **170 queries returned flights**, **54 returned
  no matching direct flights**. **100 directions** returned flights on at least one
  searched date; **88** appear within the replay day's window.
- **Zero failed/missing queries, rejected records, unverified fare contexts or
  unresolved airport identities**. **NNT (Nan Nakhon)** was searched but did not
  return flights; that is a documented coverage gap, not proof of no service.
  Smaller/commuter services and further regional route pairs remain outside scope.

| Origin region | Airports returned / selected | Departures | With USD fare |
| --- | --- | ---: | ---: |
| Central | 3 / 3 | 274 | 274 |
| North | 6 / 7 | 106 | 106 |
| Northeast | 8 / 8 | 52 | 52 |
| East | 2 / 2 | 4 | 4 |
| South | 10 / 10 | 179 | 179 |

Gzip: **31,054 bytes**, SHA-256
`cbf2018820915a0c7d31f6358743bba3deaf6fecdb2cbbd9c5b976c4438926c5`.
Manifest rebuilding and preparation from cached captures reproduce byte-for-byte output.

Validation: **210 Python tests and 93 JavaScript tests passed**, covering Thai
flights, all existing flight countries/shared network, Melbourne replay/HTTP,
app/i18n, Japan rail and existing Thailand SRT/Bangkok transit. Final Chrome checks
passed exact BKK/DMK, CNX, HKT, USM, HDY and UBP departure/arrival boards, ICT clocks
and fare capture timestamps, USD previews without implicit seeking, combined
carrier/airport filters and empty intersections, fullscreen/back/pagination,
Destinations, frequency totals stable during seeking, airport visibility, all five
themes, Indonesian, mobile viewport coverage, cache reuse and switching back to
Japan's separate JST view. Screenshots were visually inspected; no page errors
occurred. These domestic checks predate the international extension; see the additional validation below.

## Actual international coverage at the initial Thailand release

The figures below describe the initial Thailand release. The Philippine extension
adds 31 overlapping records and Vietnam adds another 72, bringing the current
Thai international view to **782 records**, **680 ICT-day departures** and **644
priced records**. Current
shared-network totals are in [International network notes](INTERNATIONAL_NETWORK_NOTES.md).

Captured **25 October 2026**, for **2 November 2026 ICT**:

- **679 overlapping international records**, **583 departures** and
  **590 arrivals inside the ICT day; **181 directional routes**, **52 airports**
  and **54 carriers**. Records include overnight flights overlapping the selected day.
- **541 priced records** (468 USD, 73 MYR), **138 unpriced**.
  Reused MYR amounts remain MYR; no conversion is performed.
- **657 / 657 Thai-view queries captured**, all **264 directions** searched,
  **201 directions** returned flights on at least one searched date. **224 queries**
  returned no matching direct flights. Zero failed/missing queries, rejected source
  records or unresolved airport identities in the Thai projection.
- Returned Thai airports: **BKK, DMK, CNX, CEI, HKT, KBV, USM and HDY**.
  **URT** was searched but not returned. Additional Thai gateways, other foreign
  countries, regional routes, and uncaptured airlines/flights remain coverage gaps.
  Completing the search manifest does not imply complete international coverage.
- Combined domestic/international Thai view: **1,294 records**; domestic remains the
  initial scope. The shared UTC network uses its own day, containing **3,596 records**
  and **3,122 captured departures**, including **625 overlapping Thai connections**.

| Thai airport | ICT-day departures | ICT-day arrivals |
| --- | ---: | ---: |
| BKK | 178 | 164 |
| CEI | 0 | 1 |
| CNX | 12 | 18 |
| DMK | 43 | 45 |
| HDY | 3 | 3 |
| HKT | 51 | 49 |
| KBV | 6 | 7 |
| USM | 4 | 4 |

International data uses the shared archive and reproducible hash documented in
[International network notes](INTERNATIONAL_NETWORK_NOTES.md). No existing country
bundle was rewritten. All 3,894 previous shared records and 4,313 previous queries
retain their original schedules, fares and provenance.

Final extension validation: **215 Python tests and 93 JavaScript tests passed**,
including all existing flight profiles, Melbourne replay/HTTP, app/i18n, Japan rail,
and Thailand rail. Three Chrome suites passed the domestic regression, Thai
international scopes and the combined network, including BKK/DMK/HKT/CNX/USM,
foreign ICN boards with KST times and an ICT replay clock, airline/airport/country
filters, fullscreen/back/pagination, Destinations, frequency totals, visibility,
all five themes, Indonesian, mobile and cache reuse. Desktop/mobile screenshots
were visually inspected; no page errors occurred. Both manifests and the shared
compressed archive reproduce byte for byte offline from their cached inputs.
