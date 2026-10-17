# Singapore MRT/LRT expansion — access and validation notes

Checked **17 October 2026**, after completing NYC Subway on `codex/nyc-singapore-replay`.

## Current status

The user supplied a DataMall key locally and the **actual official timetable downloaded successfully**. Singapore is **not implemented or advertised in the city selector** because this feed has no railway shapes. No approximate frequencies, station-to-station straight lines or unrelated schedules have been substituted.

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

However, **`shapes.txt` is absent and `trips.txt` has no `shape_id` column**: all 21,159 trips lack supplied alignments. This blocks moving-map integration. The [URA Master Plan 2019 rail layer](https://data.gov.sg/datasets/d_222bfc84eb86c7c11994d02f8939da8d/view) is explicitly indicative planning geometry from December 2019; it was not treated as verified 2026 operating tracks. LTA's station points and line-code list do not resolve this. Attempts to retrieve OSM route relations returned TLS/server/HTTP errors; no OSM alignment was obtained or validated. These request failures do not prove OSM data is unavailable.

Repeat the audit offline:

```bash
./.venv/bin/python scripts/audit_singapore_gtfs.py
```

To fetch a fresh snapshot first, add `--download`. The ZIP and report stay ignored under `.cache/singapore-audit/`; a fresh download may differ from the recorded hash. The tool honours calendar exceptions, accepts GTFS hours beyond 24, reports invalid references/times and keeps `ready_for_replay` false pending geometry validation. It sends the key only to LTA and never stores the signed link. Preserve the cached ZIP if this exact version is needed later.

## Reuse the existing approach once geometry is confirmed

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

For an eventual Singapore replay, show the dataset name, access date, LTA DataMall source and licence link. Confirm any dataset-specific conditions with the actual download. API terms also require confidential credentials and prohibit releasing data before any designated effective date. Keep the app independent of LTA and avoid copying official logos or map artwork.
