# International network between SunTrain flight locations

## Scope and experience

The **International network · Flights** replay connects Australia, Indonesia,
Malaysia, Singapore, India, Thailand, the Philippines, Vietnam, Brunei, Cambodia, Laos, Myanmar,
Timor-Leste, New Zealand, Taiwan, Hong Kong, mainland China, Japan and South Korea, plus the Gulf
hubs **DXB, AUH and DOH**, plus **worldwide international connections from Taiwan and Hong Kong**. Foreign endpoints are included without creating unrelated national views or expanding every older country’s worldwide search manifest. It covers **2 November 2026, 00:00–24:00 UTC**.
Moving planes is the default; frequency lines remain available. Directional
From country / To country filters combine with airline codes and exact airports.
Airport boards retain local dates/zones and explicitly show the converted day
window, which can cross two local calendar dates.

Country views retain their own clocks and day windows. China, Japan and South
Korea, Thailand, the Philippines, Vietnam, Laos, Myanmar, New Zealand and Taiwan offer Domestic / International / Both, defaulting to domestic. Cambodia and Timor-Leste default to International and retain an empty Domestic scope with explicit coverage gaps. Brunei and Hong Kong have only International. Their
international scope covers the selected group, except Taiwan and Hong Kong whose scope is worldwide.
Other flight views retain existing worldwide routes outside the shared group.
Indonesia's dates after 2 November and all original domestic bundles are unchanged.
The combined map contains cross-country flights only; it adds no DXB–AUH domestic
service, unrelated foreign-country routes, connecting itineraries,
live tracking, paid sources or automatic refresh.

## Candidate evidence

The manifest contains **2,792 directional candidates across 289 airports**. It
preserves the previous 2,102 directions and adds **690 worldwide Taiwan/Hong Kong
directions**. The builder imports 2,504 directions from country manifests and adds
the original 288 East Asian directions. Sources and exact airport resolutions are
documented in [Taiwan and Hong Kong flight notes](TAIWAN_HONG_KONG_FLIGHTS_NOTES.md),
[New Zealand flight notes](NEW_ZEALAND_FLIGHTS_NOTES.md),
[ASEAN flight notes](ASEAN_FLIGHTS_NOTES.md),
[Vietnam flight notes](VIETNAM_FLIGHTS_NOTES.md),
[Philippine flight notes](PHILIPPINE_FLIGHTS_NOTES.md) and
[Thai flight notes](THAI_FLIGHTS_NOTES.md). These are search targets, never proof
that every pair operates. Regional gaps remain.

New discovery uses China's existing 30 major airports; HND/NRT/KIX/NGO/FUK/CTS/OKA
in Japan; and ICN/GMP/PUS/CJU/CJJ/TAE in Korea. Existing regional candidates survive.
ITM remains domestic-only, MWX retains its documented closure exclusion, and
restricted ICN domestic transfer products are not ordinary international flights.
PEK/PKX, SHA/PVG, CTU/TFU, HND/NRT, ICN/GMP, BKK/DMK, MNL/CRK, HAN/SGN/DAD/DLI/CXR, MEL/AVV, KUL/SZB and SIN/XSP stay separate.

The builder retains input-manifest paths/hashes and evidence per candidate:

- [Narita destinations](https://www.narita-airport.jp/en/discover/citylist/):
  April 2026 network, with explicit Capital/Pudong/Tianfu airport resolution.
- [Haneda destinations](https://tokyo-haneda.com/en/flight/city_list.html?tab=intFlight):
  explicit GMP/ICN, SHA/PVG and PEK/PKX distinctions.
- [Kansai's summer 2026 passenger schedule table](https://assets.kansai-airports.co.jp/551f6859-e_20260324_pressrelease_s26.pdf):
  destination entries, including historical-season columns, are candidates only;
  cargo and via-only entries are not proof of a nonstop passenger service.
- [Centrair's airport destination selector](https://www.centrair.jp/en/),
  [Asiana's ICN-operated route list](https://m.flyasiana.com/C/KR/KO/booking/route),
  and [Air Busan's explicit route pairs](https://en.airbusan.com/content/individual/booking/route).
- [Korean government's 2018 airport tables, PDF pages 169–170](https://www.airportal.go.kr/e-book/catImage/16/2018%20POCKET%20AVIATION%20STATUS.pdf):
  historical regional candidates, not current operation or frequency evidence.
  Beijing city entries expand explicitly to PEK/PKX search targets; this does not
  assert that the then-unopened PKX appeared in the historical source.

Reviewed HTML pins are in the manifest for NRT, HND and ICN. Raw downloads of KIX,
NGO and PUS returned 403, and the historical PDF returned 404 from the local client;
their reviewed web-tool content and curated evidence are documented rather than
claiming raw-download hashes. The route hash covers curated evidence, source pins
and input-manifest hashes; it is not a hash of an entire live route website.

Airport identities reuse pinned OurAirports rows. Three older Indonesian bundles
used stable `ident` instead of `icao_code`: PDG WIPT/WIEE, SRG WARS/WAHS and TJQ
WIOD/WIKT. Only those exact aliases are accepted, with matching IATA, country and
coordinates. Other identity conflicts fail. Indian zones normalize to Asia/Kolkata;
mainland Chinese schedules use Asia/Shanghai, including Ürümqi. Malaysian KTI
entries also accept that pinned row’s internal `KH-0002` versus ICAO `VDTI`, with
matching country and coordinates. PNH and REP candidates migrate explicitly to
KTI and SAI; old flight records are never relabelled. Retired Cambodian commercial
endpoints are suppressed from November views, while raw historical bundles remain
untouched. Myanmar uses Asia/Yangon, UTC+6:30.

## Collection, ownership and fares

The shared archive requires **9,440 unique airport/date queries**, the union needed by the
UTC network day and each endpoint country's local day. Dates are calculated in
the origin airport's zone with a conservative 24-hour international duration cap;
this includes necessary adjacent dates rather than assuming every search is Nov 2.
The initial release reused **2,691 captures**, leaving **1,622 searches**. The Thai
extension preserves those 4,313 captures, reuses another 452 and needs 472 new searches. The Philippine extension
preserves all 5,237 of those queries, reuses another 127 and needs 176 new searches.
Vietnam preserves all 5,540 prior queries, reuses another 203 and needs 450 new searches.
The remaining ASEAN extension preserves all 6,193 prior queries and requires 672
additional query captures, reusing available exact-airport/date captures first.
New Zealand preserves all 6,865 prior queries, reuses another 194 exact captures
and needs only 121 new international searches. Its Pacific/Auckland day uses
NZDT (UTC+13); the shared archive envelope expands two hours earlier, while
existing views retain their own independent windows.
The TW/HK extension preserves all 7,180 prior queries. Its one worldwide capture
queue contains 2,260 new airport/date queries, including the union needed by both
local views, UTC and all existing endpoint-country views. Each query is searched
once, including TW–HK pairs. Public captures are reused before new searches.

Cached successful empty searches are reused too. Latest captures own schedules
for the same exact airport/date query; removed flights are not resurrected from
older results. Older quotes are reused only for matching flight identity and
departure/arrival times. Superseded schedules and reused source timestamps/hashes
remain in query diagnostics. New searches request USD, use two workers and stop
on challenges. Successful captures survive a stop and missing queries remain
explicit. Empty results mean not returned, never no service.

Verified USD/MYR fares retain their original currencies. The cheapest returned
quote within a currency is eligible; if both exist, USD is displayed preferentially.
Amounts in different currencies are never numerically compared or converted.
Unpriced captures are reused without new searches solely for fares. All quotes
require one adult, economy, one-way context; absent offers stay unavailable.
Original quote capture timestamps remain visible. Prices can change.

The shared compressed archive includes the envelope needed by all views and is
projected independently into each view's actual day. It is not a concatenation of
prepared country bundles with incompatible UTC windows. Events use half-open day
ownership; flights arriving exactly at midnight remain available to that day's
arrival board. Frequency totals count captured departure events, not inferred
physical aircraft or occupancy. Distinct flight numbers are preserved without
guessing codeshares. Paths are illustrative, not recorded tracks.

For 2 November country views, successful shared queries replace matching old
international airport/date results, including successful empty queries. Other
worldwide routes and unsuccessful/unsearched old queries remain available.
Original worldwide snapshot coverage and the added shared-network coverage are
reported separately. Country views with a Domestic scope expose coverage by Domestic/International/Both.
The combined network reports coverage for each selected country pair.

## Rebuild and local storage

```bash
.venv/bin/python scripts/prepare_taiwan_hong_kong_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
.venv/bin/python scripts/prepare_international_network.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_taiwan_hong_kong_flights.py
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Prepared data lives once at
`data/reference/international_network/2026-11-02.json.gz`. Existing country bundles
are not rewritten. The app's shared reference override is
`SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE`; custom country fixtures remain isolated
unless that override is explicit too. HTTP revisions include the shared file.
Gzip uses fixed mtime, stable ordering and atomic replacement.

`.cache/google-flights-international-network/` contains resumable normalized queries,
reuse provenance, preflight counts and error/stop diagnostics. Preparation works
offline from these captures. Deleting them saves local storage but later rebuilding
requires searching again; the committed replay still works. Route rebuilding uses
curated pinned evidence without downloading official source websites again.
`.cache/international-network-audit/` contains optional source downloads, tests,
coverage audit and browser screenshots. Generated replay HTTP caches regenerate.

## Actual coverage and validation

The final UTC view contains **6,463 overlapping flight records**, **5,652 departures within 2 November UTC**, **213 airports** and **113 carriers**. **5,164 records have captured quotes** (4,690 USD, 474 MYR); **1,299 remain unpriced**. The archive retains **9,087 records** across all country-local windows. Distinct flight numbers are not inferred physical aircraft movements.

Archive collection: **9,440 / 9,440 queries captured**, **0 missing**, **0 failed**. The UTC projection's own 8,373 queries include 3,188 unreturned results. Empty queries mean not returned, not no service. There are 9 rejected source records, 11 unverified fare-context queries, and 0 unresolved selected airports. Coverage remains partial. The Taiwan/Hong Kong extension preserves all **6,767 previous archive records** and **7,180 previous queries** unchanged, including schedules, fares and provenance. Existing country bundles remain unchanged; their international projections gain relevant TW/HK connections without changing local day ownership.

Gzip: **1,072,844 bytes**, SHA-256 `d62153c15145ea1f14b46821740e601daede2aa698fb64f36dffaea3fd800177`. Offline preparation reproduces the bytes exactly.

The table lists directional routes represented by overlapping records, departures owned by the UTC day, priced overlapping records and captured/planned searches. Gulf endpoints remain DXB/AUH/DOH only. Country-local figures use different windows; see [Taiwan and Hong Kong flight notes](TAIWAN_HONG_KONG_FLIGHTS_NOTES.md).

| Country pair | Routes returned | UTC-day departures | Priced records | Queries |
| --- | ---: | ---: | ---: | ---: |
| AE-AU | 14 | 24 | 41 | 42 / 42 |
| AE-BN | 0 | 0 | 0 | 6 / 6 |
| AE-CN | 14 | 18 | 29 | 48 / 48 |
| AE-HK | 4 | 6 | 9 | 12 / 12 |
| AE-ID | 8 | 16 | 22 | 30 / 30 |
| AE-IN | 80 | 249 | 289 | 318 / 318 |
| AE-JP | 8 | 8 | 16 | 30 / 30 |
| AE-KH | 0 | 0 | 0 | 18 / 18 |
| AE-KR | 4 | 8 | 11 | 12 / 12 |
| AE-MY | 4 | 10 | 14 | 24 / 24 |
| AE-NZ | 2 | 2 | 3 | 12 / 12 |
| AE-PH | 6 | 18 | 26 | 24 / 24 |
| AE-QA | 4 | 36 | 36 | 12 / 12 |
| AE-SG | 4 | 10 | 16 | 12 / 12 |
| AE-TH | 14 | 41 | 54 | 48 / 48 |
| AE-TW | 4 | 4 | 7 | 12 / 12 |
| AE-VN | 6 | 9 | 12 | 24 / 24 |
| AT-TW | 2 | 3 | 3 | 6 / 6 |
| AU-BN | 1 | 1 | 0 | 6 / 6 |
| AU-CN | 32 | 40 | 5 | 210 / 210 |
| AU-HK | 8 | 24 | 6 | 36 / 36 |
| AU-ID | 27 | 82 | 1 | 120 / 120 |
| AU-IN | 5 | 6 | 12 | 24 / 24 |
| AU-JP | 14 | 26 | 6 | 78 / 78 |
| AU-KR | 4 | 10 | 3 | 12 / 12 |
| AU-MY | 10 | 25 | 28 | 30 / 30 |
| AU-NZ | 37 | 128 | 26 | 162 / 162 |
| AU-PH | 6 | 10 | 1 | 24 / 24 |
| AU-QA | 10 | 14 | 25 | 30 / 30 |
| AU-SG | 13 | 69 | 84 | 42 / 42 |
| AU-TH | 7 | 19 | 4 | 66 / 66 |
| AU-TL | 2 | 3 | 0 | 6 / 6 |
| AU-TW | 5 | 7 | 0 | 18 / 18 |
| AU-VN | 10 | 13 | 1 | 36 / 36 |
| BD-HK | 2 | 2 | 2 | 6 / 6 |
| BE-HK | 2 | 2 | 3 | 6 / 6 |
| BN-CN | 1 | 1 | 1 | 18 / 18 |
| BN-HK | 2 | 2 | 2 | 6 / 6 |
| BN-ID | 4 | 4 | 0 | 24 / 24 |
| BN-IN | 0 | 0 | 0 | 6 / 6 |
| BN-JP | 1 | 1 | 1 | 6 / 6 |
| BN-KR | 1 | 1 | 1 | 6 / 6 |
| BN-MY | 3 | 7 | 7 | 24 / 24 |
| BN-PH | 2 | 2 | 2 | 6 / 6 |
| BN-SG | 2 | 5 | 3 | 6 / 6 |
| BN-TH | 0 | 0 | 0 | 6 / 6 |
| BN-TW | 0 | 0 | 0 | 6 / 6 |
| BN-VN | 0 | 0 | 0 | 12 / 12 |
| CA-HK | 4 | 12 | 14 | 12 / 12 |
| CA-TW | 4 | 5 | 8 | 12 / 12 |
| CH-HK | 2 | 4 | 7 | 6 / 6 |
| CN-HK | 55 | 177 | 124 | 354 / 354 |
| CN-ID | 27 | 46 | 0 | 192 / 192 |
| CN-IN | 5 | 6 | 6 | 30 / 30 |
| CN-JP | 59 | 158 | 141 | 390 / 390 |
| CN-KH | 0 | 0 | 0 | 36 / 36 |
| CN-KR | 54 | 193 | 144 | 306 / 306 |
| CN-LA | 4 | 9 | 2 | 18 / 18 |
| CN-MM | 5 | 8 | 4 | 18 / 18 |
| CN-MY | 57 | 158 | 105 | 300 / 300 |
| CN-NZ | 7 | 9 | 9 | 48 / 48 |
| CN-PH | 4 | 21 | 17 | 12 / 12 |
| CN-QA | 11 | 11 | 19 | 48 / 48 |
| CN-SG | 45 | 125 | 67 | 222 / 222 |
| CN-TH | 43 | 138 | 85 | 168 / 168 |
| CN-TL | 0 | 0 | 0 | 6 / 6 |
| CN-TW | 35 | 78 | 60 | 210 / 210 |
| CN-VN | 24 | 98 | 72 | 114 / 114 |
| CZ-TW | 2 | 2 | 3 | 6 / 6 |
| DE-HK | 4 | 6 | 10 | 12 / 12 |
| DE-TW | 3 | 3 | 4 | 12 / 12 |
| ES-HK | 2 | 3 | 2 | 12 / 12 |
| ET-HK | 2 | 2 | 4 | 6 / 6 |
| FI-HK | 2 | 2 | 4 | 6 / 6 |
| FJ-HK | 1 | 1 | 1 | 6 / 6 |
| FR-HK | 2 | 4 | 7 | 6 / 6 |
| FR-TW | 2 | 2 | 3 | 6 / 6 |
| GB-HK | 4 | 13 | 22 | 10 / 10 |
| GB-TW | 1 | 1 | 1 | 5 / 5 |
| GU-TW | 0 | 0 | 0 | 6 / 6 |
| HK-ID | 6 | 14 | 0 | 18 / 18 |
| HK-IL | 0 | 0 | 0 | 6 / 6 |
| HK-IN | 10 | 14 | 19 | 30 / 30 |
| HK-IT | 2 | 2 | 3 | 12 / 12 |
| HK-JP | 18 | 121 | 103 | 108 / 108 |
| HK-KH | 0 | 0 | 0 | 6 / 6 |
| HK-KR | 7 | 48 | 45 | 30 / 30 |
| HK-LA | 0 | 0 | 0 | 12 / 12 |
| HK-LK | 2 | 2 | 3 | 6 / 6 |
| HK-MN | 2 | 2 | 2 | 6 / 6 |
| HK-MP | 0 | 0 | 0 | 6 / 6 |
| HK-MV | 0 | 0 | 0 | 6 / 6 |
| HK-MY | 8 | 24 | 23 | 36 / 36 |
| HK-NL | 2 | 3 | 5 | 6 / 6 |
| HK-NP | 2 | 2 | 2 | 6 / 6 |
| HK-NZ | 3 | 5 | 7 | 12 / 12 |
| HK-PG | 2 | 2 | 2 | 6 / 6 |
| HK-PH | 8 | 41 | 48 | 30 / 30 |
| HK-PW | 0 | 0 | 0 | 6 / 6 |
| HK-QA | 2 | 4 | 6 | 6 / 6 |
| HK-RU | 0 | 0 | 0 | 18 / 18 |
| HK-SA | 0 | 0 | 0 | 6 / 6 |
| HK-SG | 2 | 25 | 27 | 6 / 6 |
| HK-TH | 10 | 51 | 51 | 30 / 30 |
| HK-TR | 2 | 3 | 6 | 6 / 6 |
| HK-TW | 6 | 83 | 84 | 24 / 24 |
| HK-US | 13 | 33 | 48 | 48 / 48 |
| HK-VN | 8 | 30 | 29 | 30 / 30 |
| HK-ZA | 2 | 2 | 3 | 6 / 6 |
| ID-IN | 6 | 9 | 11 | 60 / 60 |
| ID-JP | 6 | 14 | 0 | 30 / 30 |
| ID-KH | 0 | 0 | 0 | 12 / 12 |
| ID-KR | 5 | 15 | 1 | 18 / 18 |
| ID-MY | 38 | 190 | 147 | 186 / 186 |
| ID-NZ | 0 | 0 | 0 | 12 / 12 |
| ID-PH | 4 | 8 | 0 | 12 / 12 |
| ID-QA | 4 | 10 | 13 | 18 / 18 |
| ID-SG | 20 | 114 | 104 | 108 / 108 |
| ID-TH | 10 | 20 | 0 | 30 / 30 |
| ID-TL | 2 | 2 | 0 | 18 / 18 |
| ID-TW | 4 | 11 | 0 | 12 / 12 |
| ID-VN | 6 | 14 | 0 | 24 / 24 |
| IN-JP | 10 | 14 | 16 | 30 / 30 |
| IN-KH | 2 | 1 | 2 | 12 / 12 |
| IN-KR | 2 | 4 | 5 | 6 / 6 |
| IN-MM | 4 | 4 | 0 | 24 / 24 |
| IN-MY | 23 | 51 | 47 | 96 / 96 |
| IN-PH | 2 | 2 | 2 | 6 / 6 |
| IN-QA | 26 | 61 | 81 | 96 / 96 |
| IN-SG | 25 | 72 | 84 | 144 / 144 |
| IN-TH | 40 | 94 | 99 | 228 / 228 |
| IN-VN | 15 | 24 | 26 | 72 / 72 |
| IT-TW | 2 | 2 | 3 | 12 / 12 |
| JP-KR | 48 | 393 | 391 | 156 / 156 |
| JP-MY | 9 | 23 | 23 | 48 / 48 |
| JP-NZ | 2 | 2 | 3 | 6 / 6 |
| JP-PH | 13 | 37 | 43 | 48 / 48 |
| JP-QA | 6 | 8 | 13 | 18 / 18 |
| JP-SG | 11 | 45 | 52 | 42 / 42 |
| JP-TH | 14 | 52 | 55 | 54 / 54 |
| JP-TW | 73 | 254 | 286 | 336 / 336 |
| JP-VN | 17 | 41 | 42 | 78 / 78 |
| KH-KR | 1 | 1 | 0 | 18 / 18 |
| KH-LA | 2 | 2 | 2 | 18 / 18 |
| KH-MY | 4 | 8 | 8 | 18 / 18 |
| KH-PH | 0 | 0 | 0 | 6 / 6 |
| KH-QA | 0 | 0 | 0 | 6 / 6 |
| KH-SG | 4 | 10 | 11 | 12 / 12 |
| KH-TH | 7 | 18 | 18 | 24 / 24 |
| KH-TW | 0 | 0 | 0 | 6 / 6 |
| KH-VN | 6 | 17 | 11 | 36 / 36 |
| KR-LA | 2 | 2 | 2 | 18 / 18 |
| KR-MM | 0 | 0 | 0 | 6 / 6 |
| KR-MY | 4 | 12 | 12 | 42 / 42 |
| KR-NZ | 2 | 2 | 3 | 6 / 6 |
| KR-PH | 6 | 33 | 37 | 30 / 30 |
| KR-QA | 2 | 2 | 4 | 6 / 6 |
| KR-SG | 6 | 19 | 24 | 18 / 18 |
| KR-TH | 7 | 37 | 36 | 42 / 42 |
| KR-TW | 23 | 96 | 93 | 78 / 78 |
| KR-VN | 20 | 91 | 93 | 60 / 60 |
| LA-MY | 1 | 1 | 1 | 6 / 6 |
| LA-SG | 0 | 0 | 0 | 12 / 12 |
| LA-TH | 8 | 11 | 11 | 36 / 36 |
| LA-VN | 6 | 6 | 6 | 24 / 24 |
| MM-MY | 2 | 4 | 0 | 6 / 6 |
| MM-SG | 2 | 7 | 0 | 12 / 12 |
| MM-TH | 10 | 40 | 14 | 30 / 30 |
| MM-VN | 2 | 2 | 0 | 12 / 12 |
| MO-TW | 6 | 31 | 32 | 18 / 18 |
| MY-NZ | 2 | 4 | 4 | 6 / 6 |
| MY-PH | 5 | 17 | 20 | 30 / 30 |
| MY-QA | 2 | 10 | 15 | 18 / 18 |
| MY-SG | 19 | 130 | 128 | 90 / 90 |
| MY-TH | 22 | 81 | 76 | 96 / 96 |
| MY-TL | 1 | 0 | 0 | 6 / 6 |
| MY-TW | 8 | 16 | 17 | 24 / 24 |
| MY-VN | 12 | 46 | 45 | 36 / 36 |
| NL-TW | 2 | 2 | 4 | 6 / 6 |
| NZ-QA | 0 | 0 | 0 | 6 / 6 |
| NZ-SG | 4 | 10 | 14 | 12 / 12 |
| NZ-TW | 1 | 1 | 1 | 6 / 6 |
| PH-QA | 4 | 9 | 14 | 24 / 24 |
| PH-SG | 9 | 32 | 41 | 36 / 36 |
| PH-TH | 8 | 27 | 29 | 24 / 24 |
| PH-TW | 8 | 38 | 43 | 30 / 30 |
| PH-VN | 8 | 26 | 30 | 24 / 24 |
| PW-TW | 2 | 2 | 2 | 6 / 6 |
| QA-SG | 2 | 6 | 9 | 6 / 6 |
| QA-TH | 4 | 14 | 20 | 12 / 12 |
| QA-VN | 4 | 6 | 8 | 12 / 12 |
| SG-TH | 14 | 76 | 79 | 48 / 48 |
| SG-TL | 0 | 0 | 0 | 6 / 6 |
| SG-TW | 2 | 21 | 22 | 12 / 12 |
| SG-VN | 10 | 44 | 48 | 30 / 30 |
| TH-TW | 9 | 44 | 50 | 42 / 42 |
| TH-VN | 16 | 70 | 71 | 60 / 60 |
| TR-TW | 2 | 2 | 5 | 6 / 6 |
| TW-US | 19 | 47 | 67 | 60 / 60 |
| TW-VN | 16 | 56 | 62 | 90 / 90 |

The nine rejected source records are JT133/JT135/JT139 on PEN→KNO for 1–3 November. Google returned 1,495-minute timings (24 hours 55 minutes), exceeding the validated 24-hour international limit. They remain documented gaps; the app does not invent a plausible short-flight timing.

Validation for the country extensions covers exact BKK/DMK identities, ICT versus UTC and adjacent-day overlap, original USD/MYR fares, domestic isolation, duplicate identities, absent queries, old-archive compatibility, Thai/Philippine/Vietnamese airport zones, HTTP ETags and shared-file revision invalidation. Browser checks cover Thailand/the Philippines/Vietnam in the UTC network and all country scopes, airport/carrier filters, foreign local boards, fullscreen/back/pagination, Destinations, frequency, themes, Indonesian, mobile and cache reuse. The five remaining ASEAN country views also cover BNT/ICT/MMT/TLT clocks, empty domestic scopes, KTI identity aliases and retired PNH/REP exclusion. See the latest validation totals in the ASEAN notes.
