# Australian railway expansion

Work began 17 October 2026 on `codex/australian-cities-replay`, in order: Sydney, Adelaide, Perth, Brisbane. Reuse the existing compact prepared-city replay; no live tracking or new runtime services. API credentials and source downloads stay local. The pre-existing untracked `docs/` directory is unrelated and remains untouched.

## Sydney

The preferred 27 May–30 June 2024 period could not be downloaded through the official historical archive link: the [TfNSW archive catalogue](https://opendata.transport.nsw.gov.au/dataset/historical-gtfs-bundles-and-timetables) is readable through its public CKAN API, but its `https://opendata-gtfs.transport.nsw.gov.au/historical_gtfs` resource returned HTTP 404. The website advertises login for some resources. No account was created or credentials requested.

The permitted fallback is **5–11 October 2026**, one complete week using the [official TfNSW feed archived by MobilityDatabase](https://mobilitydatabase.org/feeds/gtfs/mdb-2449), captured **4 October 2026**. The pinned public ZIP actually downloaded successfully (about 279 MB, containing the whole multimodal network). Exact source URL and SHA-256 are in `scripts/prepare_australian_replay.py` and each prepared reference's metadata. It is never served to browsers.

Scope is explicitly **Sydney Trains** (`agency_id=x0001`, rail type 2) and **Sydney Metro** (`agency_id=SMNW`, type 401). Route variants group under the feed's T1–T9 and M1 line names and colours. Calendar exceptions determine which services appear; a route in the feed does not force trips onto every date. The 2026 Metro and train network must not be relabelled as May–June 2024: the [official station usage catalogue](https://opendata.transport.nsw.gov.au/dataset/train-station-entries-and-exits-data) records the Chatswood–Sydenham Metro extension opening on 19 August 2024, and T3/T6 patterns changed subsequently.

Native stop/shape distance anchors preserve ordered railway paths, including loops and branch services. Every projected station must match within 150 m; unresolved paths remain gaps. Metro's source `routes.txt` marks its timings as indicative (`exact_times=0`); replay positions remain schedule estimates. The feed includes no `frequencies.txt` requiring generated departures.

Prepared reference: **526,111 bytes**, **1,860 shared patterns**, with **no omitted trips or unresolved geometry**. The seven dates have 2,078–3,226 services; the Monday public-holiday date differs from ordinary weekdays. Sydney uses `Australia/Sydney`, including daylight saving. All seven dates loaded successfully, and Chrome checks covered playback, filters, the last date, fullscreen, mobile layout and returning to Melbourne.

**NSW TrainLink remains separate.** The same archive includes intercity agency `X0000` (e.g. BMT, CCN, SCO) and regional trains/coaches under other agencies (including 711 and extended route types). Do not include them via an indiscriminate rail-type filter. Replacement bus agencies and bus types are also excluded even when names resemble train lines.

**Later modes:** the complete archive includes light rail (extended type 900, with Sydney and Newcastle represented separately), many bus operators and ferries. Future additions should retain operator scope, distinguish rail replacement buses, and apply each route's calendars and shapes. Their presence in the archive is confirmed; their complete replay has not been validated or enabled.

**Passenger data:** the [station monthly usage CSV](https://opendata.transport.nsw.gov.au/data/dataset/3977df59-a1fa-422e-91ff-cfaeac355cc9/resource/f8bb2918-0540-4bb3-9ccf-f7aef04d4249/download/entry_exit.csv) actually downloaded with HTTP 200 (1,122,668 bytes, 17,982 rows). Actual months run **October 2024–September 2026**, despite the resource title saying November 2024. Fields are `MonthYear`, `Station`, `Station_Type`, `Entry_Exit`, `Trip`; **786 cells contain “Less than 50”**, not zero. Suitable for a labelled monthly station-use map, not hourly observations or individual train loads. The [monthly Opal train/metro totals](https://opendata.transport.nsw.gov.au/dataset/opal-trips-train) also warn that line/operator/mode aggregates must not be summed across levels after the July 2024 methodology change. Passenger features remain unavailable for this replay.

**Licence:** the official complete-timetable CKAN record labels this [Creative Commons Attribution](https://opendata.transport.nsw.gov.au/dataset/timetables-complete-gtfs). SunTrain acknowledges Transport for NSW, links the source/licence information and remains independent of the operators. No official map artwork or logos are copied.

## Adelaide

The [official GTFS service](https://gtfs.adelaidemetro.com.au/) documents `/v1/static/{version}/google_transit.zip` for historical versions. **Version 1430 actually downloaded successfully**, with `feed_info.txt` dates **24 May–27 September 2024**, and ZIP member timestamps on 24 May. This supports the requested **27 May–30 June 2024**, including the adjoining service dates needed for overnight carry-ins. A probe of version 1400 returned HTTP 403; this did not imply all historical versions were inaccessible. Version 1500 was also accessible but rejected for this task because it represents late December 2024 onward.

The suburban rail scope is agency **2, Adelaide Metro (Keolis Downer)**, route type 2. The prepared period includes Belair, Flinders, Gawler/Gawler Central, Grange, Outer Harbor and Seaford, plus the Glanville, Noarlunga, Osborne and Salisbury short-turn route IDs active in the source calendars. **Port Dock is absent**: the [official opening was 25 August 2024](https://dit.sa.gov.au/news/archive?a=1398955). The version's release notes explicitly include the [1–2 June Outer Harbor closure](https://www.dit.sa.gov.au/news/archive?a=1368879); replay train stop sequences terminate at **Woodville** during the closure, rather than running through the bus-replaced section. On 8 June the corresponding trains reach Outer Harbor again.

Prepared reference: **80,680 bytes**, **106 shared patterns**, 35 days, **no omitted trips or unresolved geometry**. A typical weekday has 605 services and a typical weekend date 394. Native distance anchors retain the original railway geometry. Timezone is **Australia/Adelaide**, including the half-hour UTC offset.

**Later modes:** this same historical archive contains Torrens Connect tram routes `BTANIC`, `FESTVL` and `GLNELG`, with shapes/calendars, and Adelaide Metro buses. O-Bahn is a bus service, not a separate rail mode; a bus extension should use its actual bus shapes through the guided section. These modes were inspected but are not enabled in this rail-first addition.

**Passenger data:** the [official Metrocard validations dataset](https://data.sa.gov.au/data/dataset/adelaide-metrocard-validations) and its 2024 Q2 CSV downloaded successfully. The attempted byte range was ignored by the server, so the local file contains the returned CSV rather than a guaranteed small sample. Fields include validation date, mode, route, direction, GTFS stop ID, media type and **boarding bands/floors**. The downloaded metadata defines bus=1, tram=4 and train=5. It explicitly warns of misallocated routes, under-reported train validations and free-zone tram travel, and provides no individual trip identifier or hourly timestamp. Daily stop/route demand bands may be useful after a careful station/gate/onboard join; band floors are not exact counts and cannot become individual train loads. Passenger controls remain unavailable.

**Licence:** the official Data.SA catalogue labels [Adelaide Metro GTFS](https://data.sa.gov.au/data/dataset/https-gtfs-adelaidemetro-com-au) **CC BY 4.0**. The replay credits Adelaide Metro and the Department for Infrastructure and Transport, Government of South Australia. No official logos or map artwork are copied.

## Perth

The [official spatial data page](https://www.transperth.wa.gov.au/About/Spatial-Data-Access) supplies a current timetable, not an indexed historical ZIP archive. No 2024 ZIP was obtained. The publicly downloadable [MobilityDatabase archive mdb-1086](https://mobilitydatabase.org/feeds/gtfs/mdb-1086), captured **1 October 2026**, has calendars beginning 29 September and supports the fallback **5–11 October 2026**. The ZIP actually downloaded successfully (about 26 MB); its URL and SHA-256 are pinned in the preparation script and bundle.

Scope is the suburban rail agency **WES-RAI**, type 2: Airport, Armadale, Ellenbrook, Fremantle, Mandurah, Midland, Thornlie-Cockburn and Yanchep, plus Stadium Special services only on their active calendar dates. **Transwa regional trains** (agency TRA-TRA) and regional buses are excluded. The names and colours come from that historical feed, rather than a current hard-coded network.

The selected period follows the actual [Yanchep opening in July 2024](https://metronet.wa.gov.au/projects/yanchep-rail-extension), [Ellenbrook opening in December 2024](https://www.metronet.wa.gov.au/news/latest-news/category/gnarla-biddi/ellenbrook-line-officially-open), and [Thornlie–Cockburn opening in June 2025](https://www.metronet.wa.gov.au/news/latest-news/20k-locals-celebrated-thornlie-cockburn-line-opening). These lines must not be backdated into a May–June 2024 replay. A future earlier-period extension must obtain the earlier archive and its closures, not just trim the current map.

The actual `shapes.txt` headers contain leading spaces and native shape distances are absent. Preparation normalizes CSV field names, then reuses the existing whole-journey ordered projection within 150 m. The resulting **92,943-byte** reference has **109 shared patterns**, with **no omitted trips or geometry gaps**. Daily services range from 1,023 to 1,465. Timezone is **Australia/Perth**, without daylight saving.

**Later modes:** the archive includes bus and ferry services. CAT routes are buses; regional operator names in the combined feed require explicit geographic/operator scoping before a bus extension. No buses or ferries are enabled in this rail-first addition.

**Passenger data:** [PTA transport performance](https://www.pta.wa.gov.au/about-us/priorities-and-performance/transport-performance) actually provides historical monthly network/mode/line boarding tables, including 2023–24, 2024–25 and later financial years. These support aggregate trend/line comparisons, not hourly station demand or individual train loads. A matching public station-level historical file was not obtained, so passenger features remain unavailable.

**Licence:** this is the **PTA Spatial Data Licence**, not CC BY. It permits use, reproduction and redistribution subject to its terms. The replay explicitly states that source data is **available free of charge from www.transperth.wa.gov.au**, links the licence and states independence from the data provider. No official branding, logos or map artwork are used. Retain this notice in any exported derivative or future redistribution.

## Brisbane / South East Queensland

The supplied [MobilityDatabase mdb-668](https://mobilitydatabase.org/feeds/gtfs/mdb-668) is **deprecated**, with a documented redirect to **mdb-3048**, whose producer URL is `https://gtfsrt.api.translink.com.au/gtfs/SEQ_SCH_GTFS.zip`. Despite the successor's “SEQ School Services” subtitle, its actual archive includes **rail, light rail, buses and ferries**, not just school buses. The [official Queensland catalogue](https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink) licenses the SEQ data and lists train route-mapping material, but its resource URL still uses the older `GTFS/SEQ_GTFS.zip` path. Inspect the actual files and documented replacement rather than deciding scope from the archive's name.

The public archive captured **3 October 2026** actually downloaded successfully. `feed_info.txt` gives **3 October–2 December 2026**, supporting **5–11 October 2026** and adjoining service dates. A 2024 historical ZIP was not obtained from the public sources checked, so this is an explicitly labelled permitted fallback. Source URL and SHA-256 are pinned in preparation and bundled metadata.

Only **agency 5, Queensland Rail**, route type 2, is included. Through-running and short-turn services retain official route names/codes, stopping patterns, headsigns and colours; there are **46 active route groups**, rather than an invented remapping into a fixed list of line badges. This includes suburban/interurban SEQ railway journeys in the archive. Use **Fit selection** to include outlying termini beyond the initial Brisbane/SEQ view. There are no regional long-distance Queensland Rail services inferred from a map or current timetable.

The source omits native shape distances, so complete ordered stop sequences use the established projection onto each trip's own shape within 150 m. The **232,395-byte** reference has **706 shared patterns**, **no omitted trips and no unresolved geometry**. Daily services are 501 on the Monday public holiday, 838 on Tuesday–Thursday, 864 Friday, 725 Saturday and 650 Sunday. Timezone is `Australia/Brisbane`; Queensland does not inherit Sydney's daylight-saving offset.

**Later modes:** G:link is light rail (type 0), Brisbane Metro is a bus service, and the archive contains other SEQ buses and ferries, including CityCat-related services. These are excluded by explicit railway operator/type selection. Before enabling them, verify each mode's actual service dates, shapes, route/provider classification and any rail-replacement buses. The current official train T-code mapping spreadsheet is useful for a future label update, but must not be applied retroactively without checking the selected feed.

**Passenger data:** the [June 2024 official OD ZIP](https://www.data.qld.gov.au/dataset/aeee186f-da4c-41cd-a6b2-85d11c7bd503/resource/6ad1614f-0a3f-4054-993c-0f8e5bea94e0/download/202406jun-tl-org-dest-trips.zip) actually downloaded successfully (**2,346,781 bytes**), containing a CSV and explanatory PDF. Rows group quantity by operator, month, route, direction, broad weekday/weekend **time bands**, ticket type, origin stop and destination stop. They are not exact-day/hour observations or individual train loads. The documentation says **Airtrain is excluded**, and some paper tickets have `n/a` destinations. Those gaps must not become zero demand or invented station pairs. The 2024 passenger period also does not match this October 2026 schedule replay. [Monthly performance datasets](https://www.data.qld.gov.au/dataset/translink-monthly-performance-data) offer aggregate patronage comparisons. Passenger features remain unavailable for this addition.

**Licence:** the official timetable catalogue returns **Creative Commons Attribution 4.0**. Replay attribution credits Translink, Department of Transport and Main Roads, Queensland Government, and links the data source and licence. No official map artwork or logos are used.

## Rebuild and extension checks

```bash
./.venv/bin/python scripts/prepare_australian_replay.py sydney
./.venv/bin/python scripts/prepare_australian_replay.py adelaide
./.venv/bin/python scripts/prepare_australian_replay.py perth
./.venv/bin/python scripts/prepare_australian_replay.py brisbane
```

Sources are pinned by URL, capture date and SHA-256. Downloads go to `.cache/australian-cities/<city>/`; compact references go to `data/reference/<city>/<first-date>.json.gz`. Preparation uses source calendars and date exceptions, GTFS hours beyond 24 and local time zones, with 03:00 carry-ins preserved and no duplicate occurrence within a day. Shapes remain shared; only one selected day is loaded in the browser.

Before extending dates or adding a mode, inspect the actual archive's dates, operators, route types, trip overrides/frequencies and geometry. Never use current timetables under historical labels. Preserve local clocks, branch paths, same-day uniqueness, shared relative stop schedules, attribution and empty paths for unresolved geometry. Passenger data requires a separate granularity and date check.

## Validation of this addition

All four prepared references loaded successfully for **every supported date**, with no omitted timetable trips, no unresolved geometry patterns, and no duplicate occurrences within a day. The source archives are used only during offline preparation; browsers receive a compact selected day with shared pattern stops.

**106 Python tests and 23 JavaScript tests passed**. New checks cover rail/operator scoping, original path endpoints, native-distance loops, Adelaide's historical closure and absent Port Dock, spaced CSV headers, and the four distinct local UTC offsets. Chrome checks passed separately for Sydney, Adelaide, Perth and Brisbane: map loading with no missing positions at 08:00, line filtering, 2,000× playback without server POSTs, the final supported date, fullscreen, mobile layout and switching back to Melbourne. Source notes and future passenger/mode opportunities are recorded above.
