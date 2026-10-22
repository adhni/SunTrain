# South Korea — Seoul subway and national KORAIL rail

## Included

**Seoul** opens from Home with metropolitan subway **Lines 1–9**, including source express/local variants, branches, short workings and the Line 2 loop. The replay reuses existing playback, filters, Overview, themes and details. Original train numbers and station calls remain intact. Operator is labelled “Seoul metropolitan subway” because the bulk file includes metropolitan through-running services; this is not a claim that Seoul Metro alone operates every included section. Initial zoom covers Seoul/Incheon; **Fit selection** includes outer termini.

The source is the official **30 September 2025 bulk timetable**, applied to **20–26 October 2025 as a reference week**, in **Asia/Seoul**. The file has weekday/Saturday/Sunday-holiday tags, not exact effective-date calendars. These dates demonstrate the dated source snapshot; they do not establish that every train actually ran that week or capture historical disruptions. No 2026 schedule is backdated to 2025. This reference week has no South Korean national holidays.

| Calendar | Daily departures |
| --- | ---: |
| Monday–Friday | 4,715 |
| Saturday | 3,903 |
| Sunday | 3,901 |

The compact week contains **31,379 departures**, **1,143 shared timing patterns**, in about **480 KB gzip**. The selected day is sent to the browser. Home downloads no schedule data. There is no runtime API call or new runtime dependency. No individual passenger counts are available.

## Sources and access

1. [Seoul Open Data Plaza bulk timetable OA-22522](https://data.seoul.go.kr/dataList/OA-22522/L/1/datasetView.do), filename `서울교통공사_도시철도열차운행시각표(250930).csv`, about 43 MB. This was actually downloaded and parsed, without an API key. The portal identifies **KOGL Type 1**, allowing reuse with attribution. It describes Lines 1–9, train numbers, direction, express flags and 24/25-hour operating-day clocks.
2. [The originally proposed station API](https://www.data.go.kr/data/15056777/openapi.do) exists, but bulk train-call data avoids unnecessary per-station API requests. Catalogue documentation alone is not treated as proof of a historical feed.
3. Station coordinates come from the pinned [minseok852/subway-etl station inventory](https://raw.githubusercontent.com/minseok852/subway-etl/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/output/station_nodes.csv). Its [README](https://github.com/minseok852/subway-etl/blob/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/README.md) attributes the underlying official Korean station/railway datasets under KOGL Type 1. It is a processed inventory, not original 2025 station geography. Only station facts are reused, not the project's code, edges, travel-time approximations or UI. Its notice is preserved in [STATION_SOURCE_NOTICE.txt](data/reference/seoul/STATION_SOURCE_NOTICE.txt). Inaccurate positions cannot force a synthetic track connector.
4. [OpenStreetMap via Geofabrik South Korea](https://download.geofabrik.de/asia/south-korea.html), replication **21 October 2026, 20:21:46 UTC**, supplies geography separately from the timetable. OSM-derived railway paths are **ODbL 1.0** with attribution. Current geography does not identify actual historical running tracks or platforms. PBF SHA-256: `e683fcb5abf964144d3ff34d1255bb5350aa632f03388d5f07ea122a462f4d10`.

All actual timetable, coordinate and graph hashes are pinned in [sources.json](data/reference/seoul/sources.json). The bulk CSV uses the same POST fields as the public portal download form. Its body is recorded in the manifest. No key, login token or credential is stored.

## Source quality and geometry

The raw CSV has **532,832 rows**. **109,110 rows lack service-day tags**, and **371 are blank station rows**. These are excluded; missing running days are never inferred. Three grouped trips are excluded for contradictory dwell/overlapping calls. Single-call templates cannot form replay journeys. The importer groups by calendar, line, train number, direction, express flag and source origin/destination, retains chronological repeated station calls and checks unique departure-window ownership. No train identity changes its express flag in this source, so express grouping does not split a physical source trip into parallel vehicles.

Some arrival/departure cells are blank or have a zero placeholder paired with a daytime clock. For these, the available published companion clock is retained on both sides of that call; no dwell is invented. **32,375 such cells** occur across the three source calendar templates, before final day expansion. Genuine late-night times remain beyond 24:00. Source calls with both clocks missing or contradictory times are not silently joined over. These normalisations are recorded in metadata.

The graph uses native OSM connections on standard-gauge `rail`/`subway` ways, excluding yards, spurs, industrial/military/test and disused tracks. Paths use the original ordered station calls. Detours beyond the existing length guard are rejected. **99.587% of Monday journey legs resolve** (638 gaps out of 154,480 legs); unresolved sections hide markers between stops. No straight station-to-station substitute is supplied. The UI retains its normal geometry-gap indicator.

The initial CSV contains linked train identities, unlike Taipei's terminal-anchored estimate: Seoul keeps the published intermediate call clocks. It does not extrapolate headways or create trains from first/last service times.

## Rebuild

Keep raw downloads in ignored `.cache/seoul/`. The prepared reference and source manifest are committed.

```bash
mkdir -p .cache/seoul
curl -L 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false' \
  --data 'infId=OA-22522&seq=1&infSeq=2' -o .cache/seoul/timetable.csv
curl -L 'https://raw.githubusercontent.com/minseok852/subway-etl/94d33a0e809f9afbd2f7c3829e88acbae1ca8e6a/output/station_nodes.csv' \
  -o .cache/seoul/stations.csv
curl -L 'https://download.geofabrik.de/asia/south-korea-latest.osm.pbf' \
  -o .cache/seoul/south-korea.osm.pbf
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_seoul_geometry.py
.venv/bin/python scripts/prepare_seoul_replay.py
```

Pyosmium is preparation-only. Keep the pinned PBF: the rolling URL changes, and a future graph will fail the existing graph hash until reviewed. Changed source files fail checksum validation. `SUNTRAIN_SEOUL_REFERENCE` overrides the prepared bundle.

## Next

- **SRT and ITX-Cheongchun:** obtain their own dated complete timetables and calendars. SRT has a separate [official timetable archive](https://etk.srail.kr/cms/archive.do?pageId=TK0402050000). Do not import SRT from KORAIL summary sheets without validating its schedule. Tourist trains remain a possible separate addition.
- Other metropolitan lines: AREX, Gyeongui–Jungang, Suin–Bundang, Gyeongchun, Shinbundang, Incheon and the light-rail networks require their own validated schedules. Do not infer their presence from the Lines 1–9 CSV.
- Longer period: obtain another dated bulk snapshot or source effective calendars. The current reference week is not a full historical archive.
- Passenger data remains optional. Station entries would not represent individual train loads.

## Validation

**46 targeted Python tests passed**, including source clock handling, missing companions, midnight service days, Lines 1–9 scope, express variants, compact patterns, train identity and runtime departure-window ownership. Browser checks opened Seoul from Home, rendered 417 vehicle features at the checked clock, advanced playback, loaded Sunday and opened Seoul Overview, with zero JavaScript errors and zero Home schedule downloads. The default dark theme applies to the site and map. Local preview: **http://localhost:8092**.

## National KORAIL replay

**South Korea** is a separate Home selection, using the existing replay, mode/route filters, details, dark map and Overview. It includes KTX, KTX-Sancheon, KTX-Eum, KTX-Cheongryong, ITX-Maum, ITX-Saemaeul, Saemaeul, Mugunghwa and Nuriro across the country. Seoul subway keeps its own view and bundle; no schedules are copied between them. SRT, ITX-Cheongchun, tourist specials and metropolitan electric services are excluded.

The official downloadable publications are:

- [KTX, effective 1 June 2025](https://www.korail.com/file/cubedata/COMMON/jfile/202504/30/2025043019686017900290.xlsx), published 30 April, official archive item 20163.
- [Conventional trains, effective 14 April 2025](https://www.korail.com/file/cubedata/COMMON/jfile/202503/28/20250328195da7b30dc650.xlsx), published 28 March, official archive item 19761.
- [KORAIL timetable board](https://www.korail.com/ticket/reserve/train-timeTable). Its public list endpoint is `https://www.korail.com/com/userBoard.do?mode=list&schBcid=ticketTable`; original attachments download under `/file/cubedata/COMMON/`.

Both original Excel files were actually downloaded and parsed. No account or API key is needed. These dated publications are displayed on the same **20–26 October 2025 reference week** as Seoul. Their original effective dates are retained; the archive does not establish that all intervening revisions or disruptions are captured. This is a timetable snapshot, not a confirmed reconstruction of every October service. Do not extend it as an exact year-long calendar.

| Business date | Departures |
| --- | ---: |
| 20 October | 664 |
| 21–23 October | 663 each |
| 24 October | 716 |
| 25 October | 727 |
| 26 October | 725 |

The week contains **4,821 departures**, **705 shared timing patterns**, in **605,647 bytes (591 KB) gzip**. The browser loads only its selected day and modes. The 03:00 business-day boundary assigns each occurrence once, including late-night trains arriving beyond midnight. Daily totals can differ from civil-date train totals at that boundary.

### Conversion and geometry

The importer reads original XLSX values using Python's standard library. Positive clock cells supply published station calls; zero cells are non-stopping placeholders. A formatted Excel value of 1.0 remains **24:00**, rather than becoming midnight on the wrong date. Seconds are preserved. Weekday restrictions are explicit; conventional blank notes mean daily service according to the workbook's guide. Unknown flags are excluded and audited. KTX summary sheets are excluded to avoid duplicate trains and unvalidated SRT entries. Cross-corridor sections merge by category, train number and calendar, deduplicating identical station/time facts. Three source sections have contradictory backward clocks and are excluded; times are not invented to repair them.

Only published station clocks are available, so separate arrival/departure dwell is not invented. All selected station names resolve to native OSM station candidates, including rail/subway interchanges. Same-name stations are disambiguated: Pangyo in Gyeonggi versus Chungnam, Yangwon on the Yeongdong Line versus Seoul, and Jangheung versus Jeonnam Jangheung. No station is skipped to bridge missing data.

The geometry preparation reuses Seoul's existing pinned South Korea PBF, avoiding another download. The national graph uses native standard-gauge railway connections, excluding yards, spurs, industrial/military/test and disused tracks. Current OSM geography is not proof of actual historical platforms or running tracks. KTX routing favours high-speed alignments using track speed tags as routing costs; published stops still force conventional branches where required. Speeds never generate timetable calls. Detours beyond the existing length guard are rejected. Monday has **7,286 journey legs**, with **4 unresolved legs (99.945% connected)**. Unresolved sections retain empty geometry and hide moving markers between stops; no straight-line substitute is supplied.

### Attribution and reuse

The [KORAIL public-work reuse policy](https://info.korail.com/info/contents.do?key=924) permits reuse without separate permission for website works whose property rights KORAIL owns in full. SunTrain extracts timetable facts from the official attachments and credits **Korea Railroad Corporation (KORAIL)**. It does not reuse page prose, layout, photographs or branding, or assign a Creative Commons licence to the spreadsheets. A restrictive badge on an unrelated KORAIL information page is not treated as the licence for these attachments. Preserve source attribution and review any changed publication's own terms when replacing it. OSM-derived railway geometry is separately **ODbL 1.0**, credited in the replay. No passenger-load data is supplied.

### Rebuild national rail

Raw downloads remain in ignored `.cache/korea-rail/`. Actual file hashes are pinned in [the national source manifest](data/reference/south_korea/sources.json). Keep the already pinned South Korea PBF used above.

```bash
mkdir -p .cache/korea-rail
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202504/30/2025043019686017900290.xlsx' -o .cache/korea-rail/ktx.xlsx
curl -L 'https://www.korail.com/file/cubedata/COMMON/jfile/202503/28/20250328195da7b30dc650.xlsx' -o .cache/korea-rail/intercity.xlsx
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_korea_geometry.py
.venv/bin/python scripts/prepare_korea_rail.py
```

Pyosmium is preparation-only; the Excel reader adds no dependency. Changed source hashes fail preparation. `SUNTRAIN_SOUTH_KOREA_REFERENCE` overrides the prepared national bundle.

**50 targeted Python checks passed** across national rail, Seoul, app and replay HTTP tests. National validation covers published running days, zero/nonstop and 24+ hour clocks, original train numbers, representative KTX/ITX journeys, same-name station geography, compact patterns, KTX-only mode selection and unique business-day ownership. Browser verification opened South Korea from Home, rendered moving vehicles, advanced playback, selected 326 KTX-only services, loaded Sunday and opened its own Overview with zero JavaScript errors. Home requested no schedule data. Local national preview: **http://localhost:8093**.
