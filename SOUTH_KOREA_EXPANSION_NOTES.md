# South Korea — Seoul subway, KORAIL and SRT

## Included

**Seoul** opens from Home with metropolitan subway **Lines 1–9** plus KORAIL **Gyeongui–Jungang (including the Seoul branch), Suin–Bundang and Gyeongchun**, plus **AREX express and all-stop**. Source express/local stopping patterns, branches, short workings and the Line 2 loop are retained. Transport can select subway or suburban/airport rail, and Operator can select the original metropolitan source, KORAIL or AREX. The replay reuses existing playback, filters, Overview, themes and details. Original train numbers and station calls remain intact. Operator is labelled “Seoul metropolitan subway” because the bulk file includes metropolitan through-running services; this is not a claim that Seoul Metro alone operates every included section. Initial zoom covers Seoul/Incheon; **Fit selection** includes outer termini.

The source is the official **30 September 2025 bulk timetable**, applied to **5–11 January 2026 as a reference week**, in **Asia/Seoul**. The file has weekday/Saturday/Sunday-holiday tags, not exact effective-date calendars. KORAIL suburban workbooks effective 30 December 2025 are applied to the same week. These dates demonstrate the distinct dated source snapshots; they do not establish that every train actually ran that week or capture historical disruptions. AREX is an October 2026 timetable explicitly matched by weekday to this reference week, not a January reconstruction. Existing subway and KORAIL occurrences are unchanged. The expanded reference week has no South Korean national holidays. The old October bundle is replaced, so subway schedules are not stored twice.

| Calendar | Daily departures |
| --- | ---: |
| Monday–Friday | 5,950 |
| Saturday | 4,902 |
| Sunday | 4,900 |

The compact week contains **39,552 departures**, **1,602 shared timing patterns**, in **677,197 bytes (661 KB) gzip**. The selected day is sent to the browser. Home downloads no schedule data. There is no runtime API call or new runtime dependency. No individual passenger counts are available.

## Sources and access

1. [Seoul Open Data Plaza bulk timetable OA-22522](https://data.seoul.go.kr/dataList/OA-22522/L/1/datasetView.do), filename `서울교통공사_도시철도열차운행시각표(250930).csv`, about 43 MB. This was actually downloaded and parsed, without an API key. The portal identifies **KOGL Type 1**, allowing reuse with attribution. It describes Lines 1–9, train numbers, direction, express flags and 24/25-hour operating-day clocks.
2. [The originally proposed station API](https://www.data.go.kr/data/15056777/openapi.do) exists, but bulk train-call data avoids unnecessary per-station API requests. Catalogue documentation alone is not treated as proof of a historical feed.
3. Station coordinates come from the pinned [minseok852/subway-etl station inventory](https://raw.githubusercontent.com/minseok852/subway-etl/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/output/station_nodes.csv). Its [README](https://github.com/minseok852/subway-etl/blob/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/README.md) attributes the underlying official Korean station/railway datasets under KOGL Type 1. It is a processed inventory, not original 2025 station geography. Only station facts are reused, not the project's code, edges, travel-time approximations or UI. Its notice is preserved in [STATION_SOURCE_NOTICE.txt](data/reference/seoul/STATION_SOURCE_NOTICE.txt). Inaccurate positions cannot force a synthetic track connector.
4. [OpenStreetMap via Geofabrik South Korea](https://download.geofabrik.de/asia/south-korea.html), replication **21 October 2026, 20:21:46 UTC**, supplies geography separately from the timetable. OSM-derived railway paths are **ODbL 1.0** with attribution. Current geography does not identify actual historical running tracks or platforms. PBF SHA-256: `e683fcb5abf964144d3ff34d1255bb5350aa632f03388d5f07ea122a462f4d10`.

The original bulk timetable, coordinate and graph hashes are pinned in [sources.json](data/reference/seoul/sources.json). New KORAIL workbook hashes are pinned in [suburban-sources.json](data/reference/seoul/suburban-sources.json). The bulk CSV uses the same POST fields as the public portal download form. Its body is recorded in the manifest. No key, login token or credential is stored.

## Source quality and geometry

The raw CSV has **532,832 rows**. **109,110 rows lack service-day tags**, and **371 are blank station rows**. These are excluded; missing running days are never inferred. Three grouped trips are excluded for contradictory dwell/overlapping calls. Single-call templates cannot form replay journeys. The importer groups by calendar, line, train number, direction, express flag and source origin/destination, retains chronological repeated station calls and checks unique departure-window ownership. No train identity changes its express flag in this source, so express grouping does not split a physical source trip into parallel vehicles.

Some arrival/departure cells are blank or have a zero placeholder paired with a daytime clock. For these, the available published companion clock is retained on both sides of that call; no dwell is invented. **32,375 such cells** occur across the three source calendar templates, before final day expansion. Genuine late-night times remain beyond 24:00. Source calls with both clocks missing or contradictory times are not silently joined over. These normalisations are recorded in metadata.

The graph uses native OSM connections on standard-gauge `rail`/`subway` ways, excluding yards, spurs, industrial/military/test and disused tracks. Paths use the original ordered station calls. Detours beyond the existing length guard are rejected. **99.587% of Monday Lines 1–9 journey legs resolve** (638 gaps out of 154,480 legs); unresolved sections hide markers between stops. No straight station-to-station substitute is supplied. The UI retains its normal geometry-gap indicator.

The initial CSV contains linked train identities, unlike Taipei's terminal-anchored estimate: Seoul keeps the published intermediate call clocks. It does not extrapolate headways or create trains from first/last service times.

## Rebuild

Keep raw downloads in ignored `.cache/seoul/`. The prepared reference and source manifest are committed.

```bash
mkdir -p .cache/seoul .cache/seoul-suburban .cache/arex
curl -L 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false' \
  --data 'infId=OA-22522&seq=1&infSeq=2' -o .cache/seoul/timetable.csv
curl -L 'https://raw.githubusercontent.com/minseok852/subway-etl/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/output/station_nodes.csv' \
  -o .cache/seoul/stations.csv
curl -L 'https://download.geofabrik.de/asia/south-korea-latest.osm.pbf' \
  -o .cache/seoul/south-korea.osm.pbf
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202512/23/2025122319b4a5663fe540.xlsx' -o .cache/seoul-suburban/gyeongui.xlsx
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202512/23/2025122319b4a54a35e180.xlsx' -o .cache/seoul-suburban/suin-bundang.xlsx
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202512/23/2025122319b4a57041400.xlsx' -o .cache/seoul-suburban/gyeongchun.xlsx
curl -L -A 'Mozilla/5.0' 'https://www.airportrailroad.com/static/file/%EC%97%B4%EC%B0%A8%EC%8B%9C%EA%B0%81%ED%91%9C_261023.xlsx' -o .cache/arex/timetable-261023.xlsx
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_seoul_geometry.py
.venv/bin/python scripts/prepare_seoul_replay.py
```

Pyosmium is preparation-only. Keep the pinned PBF: the rolling URL changes, and a future graph will fail the existing graph hash until reviewed. Changed source files fail checksum validation. `SUNTRAIN_SEOUL_REFERENCE` overrides the prepared bundle.

## Next

- National KTX/intercity, **SRT and ITX-Cheongchun** are implemented in the South Korea view. Tourist trains remain a possible separate addition.
- Other metropolitan lines: Shinbundang, Incheon, Gyeonggang, Seohae and the light-rail networks require their own validated schedules. Gyeongui–Jungang, Suin–Bundang and Gyeongchun are now included from separate KORAIL files; do not infer other networks from the Lines 1–9 CSV.
- Longer period: obtain another dated bulk snapshot or source effective calendars. The current reference week is not a full historical archive.
- Passenger data remains optional. Station entries would not represent individual train loads.

## Validation

**57 targeted Python checks passed**, including the new suburban matrix/calendar/block parsing, incomplete-trip exclusion, mode isolation and original metro weekday counts. Browser checks opened Seoul from Home, rendered 494 vehicle features, advanced playback, selected the 810-service suburban layer and its 436-service Suin–Bundang route, loaded Sunday and opened Seoul Overview, with zero JavaScript errors and zero Home schedule downloads. AREX operator filtering selected 425 trains and its express route selected 56; combined playback and Sunday were verified without browser errors. Local expanded preview: **http://localhost:8096**.

## National KORAIL and SRT replay

**South Korea** is a separate Home selection, using the existing replay, mode/route filters, details, dark map and Overview. It includes KTX, KTX-Sancheon, KTX-Eum, KTX-Cheongryong, SRT, ITX-Cheongchun, ITX-Maum, ITX-Saemaeul, Saemaeul, Mugunghwa and Nuriro across the country. SR/SRT has a separate operator filter; SRT uses purple and ITX-Cheongchun green. Seoul subway keeps its own view and bundle; no schedules are copied between them. Tourist specials and metropolitan electric services are excluded.

The official downloadable publications are:

- [KTX, effective 1 June 2025](https://www.korail.com/file/cubedata/COMMON/jfile/202504/30/2025043019686017900290.xlsx), published 30 April, official archive item 20163.
- [Conventional trains, effective 14 April 2025](https://www.korail.com/file/cubedata/COMMON/jfile/202503/28/20250328195da7b30dc650.xlsx), published 28 March, official archive item 19761.
- [ITX-Cheongchun, listed effective 1 May 2025](https://www.korail.com/file/cubedata/COMMON/jfile/202511/12/2025111219a76609a86190.xlsx), official archive item 20129. The board records publication on 28 April, but the currently served attachment path is dated 12 November 2025. This is a captured revision, not proof of the unchanged original May file.
- [SRT, effective 1 June 2025](https://www.srail.co.kr/cms/attach/download.do?pageId=TK0402050000&atchNo=23), two-page vector PDF linked from the [official SRT timetable archive](https://etk.srail.kr/cms/archive.do?pageId=TK0402050000). The page's old `www.srail.or.kr` download host is unavailable; the same public attachment is accessible on the current `www.srail.co.kr` corporate host.
- [KORAIL timetable board](https://www.korail.com/ticket/reserve/train-timeTable). Its public list endpoint is `https://www.korail.com/com/userBoard.do?mode=list&schBcid=ticketTable`; original attachments download under `/file/cubedata/COMMON/`.

All three original Excel files and the SRT PDF were actually downloaded and parsed. No account or API key is needed. These dated publications are displayed on a **20–26 October 2025 reference week**. Seoul now uses a separate January 2026 reference week for its newer suburban publications. Their original effective dates are retained; the archive does not establish that all intervening revisions or disruptions are captured. This is a timetable snapshot, not a confirmed reconstruction of every October service. Do not extend it as an exact year-long calendar.

| Business date | Departures |
| --- | ---: |
| 20 October | 822 |
| 21–23 October | 821 each |
| 24 October | 884 |
| 25 October | 911 |
| 26 October | 909 |

The week contains **5,989 departures**, **910 shared timing patterns**, in **732,951 bytes (716 KB) gzip**. The browser loads only its selected day and modes. The 03:00 business-day boundary assigns each occurrence once, including late-night trains arriving beyond midnight. Daily totals can differ from civil-date train totals at that boundary.

### Conversion and geometry

The importer reads original XLSX values using Python's standard library. In the KTX/conventional workbooks, positive clock cells supply published station calls and zero cells are non-stopping placeholders. ITX-Cheongchun instead uses blank arrival cells for passing points, so its numeric 00:00 remains a genuine midnight clock. A formatted Excel value of 1.0 remains **24:00**, rather than becoming midnight on the wrong date. Seconds are preserved. Weekday restrictions are explicit; conventional blank notes mean daily service according to the workbook's guide. Unknown flags are excluded and audited. KTX summary sheets are excluded to avoid duplicate trains and unvalidated SRT entries. Cross-corridor sections merge by category, train number and calendar, deduplicating identical station/time facts. Three source sections have contradictory backward clocks and are excluded; times are not invented to repair them.

KTX, SRT and conventional tables supply one station clock, so separate dwell is not invented for them. ITX-Cheongchun provides paired arrival/departure rows: marked arrivals identify stops; departure-row-only clocks at intermediate stations are passing times and do not become stops. Published dwell, origin departures, terminal arrivals and genuine midnight clocks are retained. Its weekday templates contain 36 daily trains; weekend/holiday templates contain 52. The reference week has no public holidays. Across the week it adds **284 departures**. SRT supplies **122 trains Monday–Thursday and 132 Friday–Sunday**, adding **884 departures**. PDF clocks are extracted from vector text positions against printed station-column centres; ambiguous or duplicate cells fail preparation rather than shifting missing cells across stations. Coupled SRT train portions keep their distinct published numbers and overlap on shared trunks, as shown in the source footnotes. All selected station names resolve to native OSM station candidates, including rail/subway interchanges. Same-name stations are disambiguated: Pangyo in Gyeonggi versus Chungnam, Yangwon on the Yeongdong Line versus Seoul, and Jangheung versus Jeonnam Jangheung. No station is skipped to bridge missing data.

The geometry preparation reuses Seoul's existing pinned South Korea PBF, avoiding another download. The national graph uses native standard-gauge railway connections, excluding yards, spurs, industrial/military/test and disused tracks. Current OSM geography is not proof of actual historical platforms or running tracks. KTX routing favours high-speed alignments using track speed tags as routing costs; published stops still force conventional branches where required. Speeds never generate timetable calls. Detours beyond the existing length guard are rejected. Monday has **8,357 journey legs**, with **4 unresolved legs (99.952% connected)**. All newly added ITX-Cheongchun and SRT legs resolve. The original 4,821 occurrences and their timing patterns are unchanged. Unresolved sections retain empty geometry and hide moving markers between stops; no straight-line substitute is supplied.

### Attribution and reuse

The [KORAIL public-work reuse policy](https://info.korail.com/info/contents.do?key=924) permits reuse without separate permission for website works whose property rights KORAIL owns in full. SunTrain extracts timetable facts from the official attachments and credits **Korea Railroad Corporation (KORAIL)**. It does not reuse page prose, layout, photographs or branding, or assign a Creative Commons licence to the spreadsheets. A restrictive badge on an unrelated KORAIL information page is not treated as the licence for these attachments. Preserve source attribution and review any changed publication's own terms when replacing it. OSM-derived railway geometry is separately **ODbL 1.0**, credited in the replay. The SR PDF is publicly downloadable; no explicit open-content licence was identified on the attachment. SunTrain extracts its timetable facts with SR attribution and source links, and does not redistribute the PDF, page layout, prose or graphics. The KORAIL policy is not presented as a licence for SR material. No passenger-load data is supplied.

### Rebuild national rail

Raw downloads remain in ignored `.cache/korea-rail/`. Actual file hashes are pinned in [the national source manifest](data/reference/south_korea/sources.json). Keep the already pinned South Korea PBF used above.

```bash
mkdir -p .cache/korea-rail
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202504/30/2025043019686017900290.xlsx' -o .cache/korea-rail/ktx.xlsx
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202503/28/20250328195da7b30dc650.xlsx' -o .cache/korea-rail/intercity.xlsx
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202511/12/2025111219a76609a86190.xlsx' -o .cache/korea-rail/cheongchun.xlsx
curl -L -A 'Mozilla/5.0' 'https://www.srail.co.kr/cms/attach/download.do?pageId=TK0402050000&atchNo=23' -o .cache/korea-rail/srt-timetable
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_korea_geometry.py
PYTHONPATH=.cache/pdf-tools .venv/bin/python scripts/prepare_korea_rail.py
```

Pyosmium and pdfplumber are preparation-only; the Excel reader uses the standard library. There is no new runtime dependency. Changed source hashes fail preparation. `SUNTRAIN_SOUTH_KOREA_REFERENCE` overrides the prepared national bundle.

**53 targeted Python checks passed** across national rail, Seoul, app and replay HTTP tests. National validation covers published running days, zero/nonstop and 24+ hour clocks, original train numbers, representative KTX/ITX journeys, same-name station geography, compact patterns, high-speed mode selection, SRT weekday restrictions, ITX weekend calendars and unique business-day ownership. Browser verification opened South Korea from Home, rendered moving vehicles, advanced playback, selected 448 high-speed services, 122 SR/SRT services and 36 ITX-Cheongchun services, loaded Sunday and opened its own Overview with zero JavaScript errors. Home requested no schedule data. Local national preview: **http://localhost:8094**.

## KORAIL suburban additions to Seoul

The three official archived workbooks are all **effective 30 December 2025**, downloaded from KORAIL's timetable board. Original train numbers, intermediate station calls, dwell, partial routes and station-passing clocks are available. No departure is generated from headways. Gyeongui–Jungang also includes its separate Seoul–Sinchon–Gajwa branch. Gyeongchun includes the source's Gwangundae workings. ITX-Cheongchun is not copied into this view.

| Line | Weekday departures | Saturday/Sunday departures |
| --- | ---: | ---: |
| Gyeongui–Jungang and Seoul branch | 245 | 193 |
| Suin–Bundang | 436 | 342 |
| Gyeongchun | 129 | 87 |
| **Additional total** | **810** | **622** |

The additions contain **5,294 occurrences** across the reference week. They are merged at preparation time with the original subway templates into one compact bundle. The original 31,379 subway occurrences retain their weekday, train identity and clock offsets. Home still downloads no replay schedules; selecting only one transport mode sends only that mode's patterns.

Matrix headers can shift by a row or have two train blocks side by side; the importer isolates each block before reading its station calls. Blank intermediate arrivals paired with departure-row clocks are passing points. Genuine 00:00 clocks and overnight rollovers are retained, along with published dwell. Unknown calendars/layouts fail preparation. One weekday Suin–Bundang source trip, **K6043**, declares Gosaek as its destination but has clocks only through Suwon, including a departure there. That entire template is excluded and audited; no Gosaek time is invented.

KORAIL abbreviations such as `효창공`, `홍대입`, `평내호`, `매탄권` and `소래포` are explicitly matched to their full station names. Working names `신인천` and `신수원` match Incheon and Suwon, not invented new stations. The inventory calls Shingil Oncheon `능길`; its existing station coordinate is matched to the source's Shingil Oncheon name. Names are resolved within their own line where available, preserving the separate Gyeongui Sinchon station. All included calls resolve to the pinned station inventory. No station is skipped to join disconnected timetable sections.

Suburban geometry reuses the existing pinned Seoul rail/subway graph. Monday resolves **24,639 of 25,126 suburban journey legs (98.06%)**. Most gaps lie around Mangwoo, Yangwon and Sangbong; they remain empty geometry rather than straight shortcuts. Including Lines 1–9 and AREX, Monday resolves **182,788 of 183,913 legs (99.39%)**. These are inferred paths on current OSM geometry, not a claim of historical track/platform fidelity.

KORAIL timetable facts retain KORAIL attribution and the same public-work reuse-policy reference as national rail; no separate open licence is invented for these workbooks. The station inventory retains its KOGL Type 1 notice and railway geography remains ODbL 1.0. New preparation uses the existing standard-library workbook reader, with no runtime dependency.

## AREX airport rail

Both **AREX express** (orange) and **AREX all-stop** (blue) are included under suburban/airport rail, with an AREX operator filter. The [official station timetable page](https://www.airportrailroad.com/train/normal/info/010) links a [complete Excel train timetable](https://www.airportrailroad.com/static/file/%EC%97%B4%EC%B0%A8%EC%8B%9C%EA%B0%81%ED%91%9C_261023.xlsx). The actually downloaded workbook has 802 weekday/weekend templates, with original A-prefixed train numbers, arrival/departure clocks, terminal times and short workings. Its hash is pinned in [arex-source.json](data/reference/seoul/arex-source.json).

**Date limitation:** the current official page links a filename dated 23 October 2026. Requesting an older `251229` filename returned the identical SHA-256 and an internal August 2026 workbook modification date. The old-looking URL therefore is not accepted as proof of a historical December 2025 timetable. AREX is labelled as an **October 2026 snapshot**, matched by weekday to the Seoul reference week. The exact effective date is not independently confirmed. Metadata records the mapping to the captured 23–29 October source week; it is not portrayed as January airport service.

Weekdays have **369 all-stop + 56 express trains**; weekends have **321 all-stop + 56 express trains**. This adds **2,879 occurrences**. The previous 36,673 metro/KORAIL occurrences are unchanged. Express services retain only Seoul and both airport terminals. All-stop short workings from/to Geomam and Digital Media City remain intact. Passing clocks and the Susaek connection control point do not become passenger stops. Original seconds and dwell are retained. A midnight origin departure remains 24:00 on its source operating day, so it is assigned once to the correct 03:00 business window. Endpoints are checked against the workbook's published terminal clocks.

All added AREX journey legs resolve on the existing pinned railway graph; no new geometry download is required. The station inventory already contains the 14 airport-line stations. There is no new runtime dependency. Preparation publishes the combined bundle atomically after all component conversions finish.

The operator is credited as **Airport Railroad Co., Ltd. (AREX)**. Only timetable facts are extracted; the workbook, website graphics and prose are not redistributed. No explicit open-content licence was identified on the download, so no Creative Commons licence or KORAIL policy is asserted for AREX material. Existing station-inventory and OSM attribution remain in place.
