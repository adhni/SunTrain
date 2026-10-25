# International network between SunTrain flight locations

## Scope and experience

The **International network · Flights** replay connects Australia, Indonesia,
Malaysia, Singapore, India, Thailand, mainland China, Japan and South Korea, plus the Gulf
hubs **DXB, AUH and DOH**. It covers **2 November 2026, 00:00–24:00 UTC**.
Moving planes is the default; frequency lines remain available. Directional
From country / To country filters combine with airline codes and exact airports.
Airport boards retain local dates/zones and explicitly show the converted day
window, which can cross two local calendar dates.

Country views retain their own clocks and day windows. China, Japan and South
Korea and Thailand now offer Domestic / International / Both, defaulting to domestic. Their
new international scope covers this selected group, not every foreign country.
Other flight views retain existing worldwide routes outside the shared group.
Indonesia's dates after 2 November and all original domestic bundles are unchanged.
The combined map contains cross-country flights only; it adds no DXB–AUH domestic
service, Hong Kong/Macau/Taiwan, transport-only countries, connecting itineraries,
live tracking, paid sources or automatic refresh.

## Candidate evidence

The manifest includes **1,530 directional candidates across 154 airports**. The
original 1,266 directions are preserved. Thailand adds **264 directions**, including
176 reused candidates and focused East Asian route discovery/probes documented in
[Thai flight notes](THAI_FLIGHTS_NOTES.md). The builder imports 1,242 directions
from existing country manifests and adds 288 original East Asian directions. These are search targets, never a claim
that every route operates. This is a major-gateway release; regional gaps remain.

New discovery uses China's existing 30 major airports; HND/NRT/KIX/NGO/FUK/CTS/OKA
in Japan; and ICN/GMP/PUS/CJU/CJJ/TAE in Korea. Existing regional candidates survive.
ITM remains domestic-only, MWX retains its documented closure exclusion, and
restricted ICN domestic transfer products are not ordinary international flights.
PEK/PKX, SHA/PVG, CTU/TFU, HND/NRT, ICN/GMP, BKK/DMK, MEL/AVV, KUL/SZB and SIN/XSP stay separate.

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
mainland Chinese schedules use Asia/Shanghai, including Ürümqi.

## Collection, ownership and fares

One queue contains **5,237 unique airport/date queries**, the union needed by the
UTC network day and each endpoint country's local day. Dates are calculated in
the origin airport's zone with a conservative 24-hour international duration cap;
this includes necessary adjacent dates rather than assuming every search is Nov 2.
The initial release reused **2,691 captures**, leaving **1,622 searches**. The Thai
extension preserves those 4,313 captures, reuses another 452 and needs 472 new searches.

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
reported separately. China/Japan/Korea/Thailand expose coverage by Domestic/International/Both.
The combined network reports coverage for each selected country pair.

## Rebuild and local storage

```bash
.venv/bin/python scripts/prepare_thai_international_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
.venv/bin/python scripts/prepare_international_network.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py
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

The final UTC view contains **3,596 overlapping flight records**, **3,122 departures within 2 November UTC**, **121 airports** and **77 carriers**. **2,808 records have captured quotes** (2,449 USD, 359 MYR); **788 remain unpriced**. The archive retains **4,778 records** across the wider envelope needed by all country-local views. Distinct flight numbers are not inferred physical aircraft movements.

Archive collection: **5,237 / 5,237 queries captured**, **0 missing**, **0 failed**. The UTC projection’s own 4,590 required queries include 1,813 unreturned results. Empty queries mean not returned, not no service. There are 9 rejected source records, 9 unverified fare-context queries, and 0 unresolved airports. Coverage remains partial, including within the selected countries. The extension preserves all **3,894 previous archive records**, original quotes and **4,313 previous queries** exactly; the Thai domestic archive is also unchanged byte for byte.

Gzip: **589,209 bytes**, SHA-256 `86598987a334607312b8da479660ffced560e9bcc46ad7830bfa36774fe12213`. Offline preparation from cached captures reproduces the bytes exactly.

The table lists directional routes represented by overlapping records, departures owned by the UTC day, priced overlapping records and captured/planned searches. Gulf endpoints remain DXB/AUH/DOH only. Thailand's country-local figures are documented separately in [Thai flight notes](THAI_FLIGHTS_NOTES.md).

| Country pair | Routes returned | UTC-day departures | Priced records | Queries |
| --- | ---: | ---: | ---: | ---: |
| AE-AU | 14 | 24 | 41 | 42 / 42 |
| AE-CN | 14 | 18 | 29 | 48 / 48 |
| AE-ID | 8 | 16 | 22 | 30 / 30 |
| AE-IN | 80 | 249 | 289 | 318 / 318 |
| AE-JP | 8 | 8 | 16 | 30 / 30 |
| AE-KR | 4 | 8 | 11 | 12 / 12 |
| AE-MY | 4 | 10 | 14 | 24 / 24 |
| AE-QA | 4 | 36 | 36 | 12 / 12 |
| AE-SG | 4 | 10 | 16 | 12 / 12 |
| AE-TH | 14 | 41 | 54 | 48 / 48 |
| AU-CN | 32 | 40 | 5 | 210 / 210 |
| AU-ID | 27 | 82 | 1 | 120 / 120 |
| AU-IN | 5 | 6 | 12 | 24 / 24 |
| AU-JP | 14 | 26 | 6 | 78 / 78 |
| AU-KR | 4 | 10 | 3 | 12 / 12 |
| AU-MY | 10 | 25 | 28 | 30 / 30 |
| AU-QA | 10 | 14 | 25 | 30 / 30 |
| AU-SG | 13 | 69 | 84 | 42 / 42 |
| AU-TH | 7 | 19 | 4 | 66 / 66 |
| CN-ID | 27 | 46 | 0 | 192 / 192 |
| CN-IN | 5 | 6 | 6 | 30 / 30 |
| CN-JP | 59 | 158 | 141 | 390 / 390 |
| CN-KR | 54 | 193 | 144 | 306 / 306 |
| CN-MY | 57 | 158 | 105 | 300 / 300 |
| CN-QA | 11 | 11 | 19 | 48 / 48 |
| CN-SG | 45 | 125 | 67 | 222 / 222 |
| CN-TH | 43 | 138 | 85 | 168 / 168 |
| ID-IN | 6 | 9 | 11 | 60 / 60 |
| ID-JP | 6 | 14 | 0 | 30 / 30 |
| ID-KR | 5 | 15 | 1 | 18 / 18 |
| ID-MY | 38 | 190 | 147 | 186 / 186 |
| ID-QA | 4 | 10 | 13 | 18 / 18 |
| ID-SG | 20 | 114 | 104 | 108 / 108 |
| ID-TH | 10 | 20 | 0 | 30 / 30 |
| IN-JP | 10 | 14 | 16 | 30 / 30 |
| IN-KR | 2 | 4 | 5 | 6 / 6 |
| IN-MY | 23 | 51 | 47 | 96 / 96 |
| IN-QA | 26 | 61 | 81 | 96 / 96 |
| IN-SG | 25 | 72 | 84 | 144 / 144 |
| IN-TH | 40 | 94 | 99 | 228 / 228 |
| JP-KR | 48 | 393 | 391 | 156 / 156 |
| JP-MY | 9 | 23 | 23 | 48 / 48 |
| JP-QA | 6 | 8 | 13 | 18 / 18 |
| JP-SG | 11 | 45 | 52 | 42 / 42 |
| JP-TH | 14 | 52 | 55 | 54 / 54 |
| KR-MY | 4 | 12 | 12 | 42 / 42 |
| KR-QA | 2 | 2 | 4 | 6 / 6 |
| KR-SG | 6 | 19 | 24 | 18 / 18 |
| KR-TH | 7 | 37 | 36 | 42 / 42 |
| MY-QA | 2 | 10 | 15 | 18 / 18 |
| MY-SG | 19 | 130 | 128 | 90 / 90 |
| MY-TH | 22 | 81 | 76 | 96 / 96 |
| QA-SG | 2 | 6 | 9 | 6 / 6 |
| QA-TH | 4 | 14 | 20 | 12 / 12 |
| SG-TH | 14 | 76 | 79 | 48 / 48 |

The nine rejected source records are JT133/JT135/JT139 on PEN→KNO for 1–3 November. Google returned 1,495-minute timings (24 hours 55 minutes), exceeding the validated 24-hour international limit. They remain documented gaps; the app does not invent a plausible short-flight timing.

Validation for the Thailand extension covers exact BKK/DMK identities, ICT versus UTC and adjacent-day overlap, original USD/MYR fares, domestic isolation, duplicate identities, absent queries, old-archive compatibility, Thai airport zones, HTTP ETags and shared-file revision invalidation. Browser checks cover Thailand in the UTC network and all Thai scopes, airport/carrier filters, foreign local boards, fullscreen/back/pagination, Destinations, frequency, themes, Indonesian, mobile and cache reuse. See the final test totals in the Thai notes.
