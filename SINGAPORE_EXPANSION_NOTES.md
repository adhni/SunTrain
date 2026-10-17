# Singapore MRT/LRT expansion — access and validation notes

Checked **17 October 2026**, after completing NYC Subway on `codex/nyc-singapore-replay`.

## Current status

**Singapore is implemented for 5–11 October 2026**, using the actual LTA timetable and separately validated OpenStreetMap railway geometry. All six MRT lines, the airport branch and all three LRT systems are available. Existing controls, themes and local `Asia/Singapore` time are reused. No approximate frequencies, station-to-station straight lines or unrelated schedules have been substituted.

The [official DataMall catalogue](https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html) lists **GTFS Schedule (Train)** separately from realtime alerts and trip updates. Realtime is outside this task. The [DataMall homepage](https://datamall.lta.gov.sg/content/datamall/en.html) states that API access requires an Account Key issued to registered subscribers.

The key is stored in the ignored `.cache/singapore-audit/account-key` with owner-only permissions. `scripts/audit_singapore_gtfs.py` also accepts `LTA_ACCOUNT_KEY`. Do not print credentials, pass them as command arguments or commit them. Registration is through the [official API access form](https://datamall.lta.gov.sg/content/datamall/en/request-for-api.html).

## Actual download checks

- `GET https://datamall2.mytransport.sg/ltaodataservice/GTFSScheduleTrain` without credentials returned **HTTP 404**, body `The requested API was not found`. **With the AccountKey header it returned HTTP 200**, and the supplied signed link downloaded a **3,418,649-byte GTFS ZIP** with HTTP 200. SHA-256: `d825c9021f0bad4241cee0a4cef10c23a4434a2d2521169cde2fb81d332e1a9e`.
- The catalogue's [public GTFS sample ZIP](https://datamall.lta.gov.sg/content/dam/datamall/datasets/PublicTransportRelated/GTFSScheduleTrain.zip) downloaded successfully: **3,499 bytes**, containing only `GTFSScheduleTrain.json` and `.xml`. It is an API response example, **not a timetable**. Its dated, signed download link is not a reusable historical archive.
- Local evidence is ignored under `.cache/singapore-audit/`. Do not commit signed URLs or treat the sample timestamp as service validity.

The [official API guide, version 6.10](https://datamall.lta.gov.sg/content/dam/datamall/datasets/LTA_DataMall_API_User_Guide.pdf), records the launch on **3 August 2026**. Section 2.31 documents the endpoint above, returning a ZIP download link valid for 15 minutes. It documents no historical-date selector.

## Actual timetable audit

The downloaded archive contains **114 route variants, 21,159 trips, 1,211 stops and 392,744 stop-time rows**. Agencies include LTA, SMRT and SBS Transit. The six MRT lines are NS, EW, NE, CC, DT and TE, with CG for the airport branch; BP, SK and PG cover Bukit Panjang, Sengkang and Punggol LRT. Colours and operators are present in the actual route rows. No frequency-based schedules were found.

`feed_info.txt` says 2025–2026, but **service calendars actually start 1 January 2026 and end 31 December 2026**. The narrower calendars must control date availability. The snapshot includes special Circle Line services and cancellation exceptions for 17–18 October 2026; it is not proof of all previous changes across the year. Do not describe it as an archive of every day in 2026.

**5–11 October 2026** was audited as a candidate full week: all ten line codes have active trips daily. Service-date totals are 7,160 on weekdays, 5,906 on Saturday and 6,084 on Sunday. These are calendar-based GTFS trips, not 03:00 replay-day occurrence counts. No missing trip/route/stop references, duplicate stop sequences, invalid stop coordinates, invalid times or backwards trip times were detected.

**`shapes.txt` is absent and `trips.txt` has no `shape_id` column**: all 21,159 trips lack supplied alignments. The [URA Master Plan 2019 rail layer](https://data.gov.sg/datasets/d_222bfc84eb86c7c11994d02f8939da8d/view) is explicitly indicative planning geometry from December 2019 and was not used. LTA's station points and line-code list are insufficient. Initial Overpass failures were bypassed by downloading the [BBBike Singapore OSM XML extract](https://download.bbbike.org/osm/bbbike/Singapore/); direct OSM relation download also worked.

## Validated geometry and replay

The OSM extract downloaded on **17 October 2026** contains directional MRT/LRT route relations for every supported line. `scripts/prepare_singapore_geometry.py` retains only operating railway ways in those relations and joins ways only at identical OSM node IDs. Missing ways and disconnected endpoints split the path; no connectors or shortest-path guesses are added. Future lines, Sentosa Express and airport Skytrain are not included as replay services.

The derived geometry is bundled in `data/reference/singapore/osm-rail-2026-10-17.json.gz` with the source URL, date, archive hash, relation IDs and ODbL licence. `scripts/prepare_singapore_replay.py` reuses the Boston whole-journey ordered projection and the existing path simplification, compact reference format and prepared-city loader. Closed loops permit a second traversal of the same connected geometry so an OSM relation can begin midway around a terminal-to-terminal LRT loop. Only trip sequences present in LTA's schedule generate services.

**176 of 177 unique stop sequences matched** within 150 m of the railway geometry. A single Sunday NS trip, `NSL_NB_PH_210_5334`, has a reversing/skipping stop sequence that did not match a complete directional run. Its source schedule is retained, with empty geometry rather than interpolated movement. There are no omitted timetable trips. The seven replay dates have 7,160 services each weekday, 5,906 Saturday and 6,084 Sunday; only Sunday has unresolved geometry (21 legs from that one trip).

The replay bundle `data/reference/singapore/2026-10-05.json.gz` is **890,860 bytes**, with **3,053 shared patterns and 430 paths**. It never expands every trip's schedule in the browser. Passenger controls remain unavailable. OSM geography is a reference snapshot, not proof of historical running tracks; schedule positions do not reproduce GPS, delays or every past disruption.

Rebuild using the original GTFS cached locally:

```bash
./.venv/bin/python scripts/prepare_singapore_replay.py
```

The script requires the recorded GTFS SHA-256 and fails on a changed download. Audit any new feed before deliberately updating the pin or period. To regenerate geography from the matching original extract:

```bash
./.venv/bin/python scripts/prepare_singapore_geometry.py .cache/singapore-audit/Singapore.osm.gz --source-date 2026-10-17
```

The source extract URL changes over time; confirm its hash against the bundled metadata before attempting an exact rebuild. Keep the cached original source files if this version is needed later.

Repeat the audit offline:

```bash
./.venv/bin/python scripts/audit_singapore_gtfs.py
```

To fetch a fresh snapshot first, add `--download`. The ZIP and report stay ignored under `.cache/singapore-audit/`; a fresh download may differ from the recorded hash. This raw-GTFS audit still reports missing supplied shapes; the separate replay preparation validates the OSM geometry. It honours calendar exceptions, accepts GTFS hours beyond 24 and reports invalid references/times. It sends the key only to LTA and never stores the signed link. Preserve the cached ZIP if this exact version is needed later.

## Checks for future extensions

1. Fetch with the key in the `AccountKey` request header; keep credentials and temporary signed links out of logs, browser code and tracked metadata. Record a stable endpoint, retrieval date and ZIP SHA-256 instead.
2. Inspect agency, routes, trips, stops, calendars, exceptions, shapes and any frequency-based services. Establish SMRT/SBS Transit and MRT/LRT coverage from actual rows. Report missing lines; do not fabricate services. Frequency-based schedules may need an explicit estimate label and should not silently become exact departures.
3. Choose dates wholly supported by the feed, including adjoining service dates for overnight carry-ins. Do not relabel current schedules as earlier historical operations. Start with one complete week; extend only after validation.
4. Reuse `scripts/prepare_boston_replay.py`, `scripts/prepare_nyc_replay.py`, the compact shared-pattern reference format, `dashboard/cities.py` and the prepared-city loader. Use `Asia/Singapore`, local bounds and verified route colours. Keep passenger controls unavailable initially.
5. Preserve official trip shapes and ordered stop occurrences through branches and loops. Check stop-to-shape distances before simplification. If shapes are absent or unsuitable, document the gap and assess a licensed railway source before enabling animation. Station points alone are insufficient.
6. Audit calendars, extended-hour trips, same-day occurrence uniqueness, referenced IDs, unresolved geometry, payload size and browser playback. Check MRT and LRT branches explicitly. Keep Melbourne, Boston, Chicago and NYC checks passing.

## Passenger data and future buses

The catalogue lists monthly station and origin–destination passenger datasets. The guide's sections 2.7–2.8 describe `/PV/ODTrain` and `/PV/Train`, with `Date=YYYYMM` for the last three months; previous-month data is generated by the tenth. Annexes A–B group totals by month, day type and hour, with merged interchange codes. These can support labelled aggregate station demand, not exact-day observations or train loads.

**Actual passenger download verified:** `/PV/Train?Date=202609` returned HTTP 200 and a **72,649-byte ZIP** containing `transport_node_train_202609.csv` with **7,376 rows**. Fields include `YEAR_MONTH`, `DAY_TYPE`, `TIME_PER_HOUR`, `PT_TYPE`, `PT_CODE`, `TOTAL_TAP_IN_VOLUME` and `TOTAL_TAP_OUT_VOLUME`. The file is cached as `train-passengers-2026-09.zip`. Origin–destination file access has not been tested. September totals must not be labelled as October observations.

Keep passenger features optional. Verify station-code joins and align the passenger month with the selected schedule period before adding a heatmap. Bus arrival estimates and route first/last timings do not establish a complete historical bus timetable; Singapore buses remain a future investigation.

## Licensing and attribution

The [API terms](https://datamall.lta.gov.sg/content/datamall/en/api-terms-of-service.html) explicitly put datasets under the [Singapore Open Data Licence v1.0](https://datamall.lta.gov.sg/content/datamall/en/SingaporeOpenDataLicence.html), rather than relying on the website's generic copyright notice. The licence permits redistribution and adaptation, including commercial use, subject to its conditions. A product using the dataset must conspicuously acknowledge its source and link the licence; it must not imply LTA endorsement. Trademarks and third-party rights are excluded.

The replay shows the dataset name, access date, LTA DataMall source and licence link, plus OpenStreetMap contributor credit and an ODbL link. See `data/reference/singapore/README.md` for the derived data's licences and available geometry source. API terms also require confidential credentials and prohibit releasing data before any designated effective date. SunTrain is independent of LTA and the operators and uses no official logos or map artwork.
