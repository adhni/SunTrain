# Belgium rail

Belgium uses the established SunTrain replay for **1–7 June 2026**, matching France, Switzerland, Germany and the Netherlands. It includes SNCB/NMBS IC, L, S and P trains and other rail categories actually active in the archive. Existing playback, filters, train details, Overview, themes and fullscreen are reused. No passenger feature or additional transport modes are added.

## Sources and dates

The [FlatTurtle public archive](https://gtfs.flatturtle.cloud/sncb-nmbs/) provides the actual [31 May 2026 SNCB ZIP](https://gtfs.flatturtle.cloud/sncb-nmbs/sncb-nmbs-gtfs_2026-05-31.zip). It was downloaded without an account or payment: **11,399,526 bytes**, SHA-256 `237bd2286cac3b4d79d5caecbfb3716ea2c65fdf368904c2f0c08a71a0248b05`. It contains publisher `NMBS/SNCB`, feed version **2026-05-30**, validity **29 March–12 December 2026**, and actual service calendars/exceptions covering the selected week.

The current official source is the [Belgian Mobility portal](https://data.belgianmobility.io/en/data.html). Its [2026 terms](https://data.belgianmobility.io/en/terms.html) specify **CC BY 4.0**. The replay retains the required source/update credit: **Source: NMBS/SNCB – Open Data – 2026-05-30**, plus archive and SunTrain processing credit. FlatTurtle [documents its dated snapshots](https://blog.flatturtle.com/gtfs-archive-cleanup/); it is an archive, not the timetable producer.

The implementation uses a public archived file. The FlatTurtle catalogue also lists 2024 snapshots, but those were not downloaded or validated for this implementation. Recheck actual files/calendars when changing dates.

## Scope and time handling

- Pin the `NMBS/SNCB` agency ID/name and audited extended rail types/products. Exclude all `BUS`/type 700 services, including replacement buses. Preserve source labels such as T, EXT, TRN, EC, OTC and NJ where active; do not invent Eurostar/ICE coverage from them. International services requiring separate publishers remain future work.
- International journeys retain the first through last Belgian/border-coded UIC call (seven-digit IDs starting `88`, with optional `_platform` suffixes). Keep any foreign intermediate calls and original times. This is a publisher-code scope, not an exact geographic frontier. No synthetic border crossing times or connections are introduced.
- Commercial numbers come from `trip_short_name`; original trip IDs remain in service IDs and `source_trip_id`. Destinations use the retained terminal. The feed does not supply direction bits here, so directions remain **Not specified**.
- The source uses **Europe/Brussels**. Assign each occurrence to one 03:00–03:00 business day by its retained first departure, including adjoining service dates and calls beyond 24:00. Shared GTFS time arithmetic handles daylight saving; this week uses CEST.
- `stop_time_overrides.txt` contains service-dependent **platform stop IDs**, not changed arrival/departure fields. The replay uses the base station-level stops and timetable times; it does not claim exact platforms or running tracks.
- The source leaves colours blank. SunTrain supplies category display colours; these are not advertised as official line colours.

The week contains **24,165 departures**: Monday–Sunday **3,786 / 3,794 / 3,801 / 3,795 / 3,794 / 2,653 / 2,542**. All selected candidates were prepared without schedule-parsing omissions.

## Geometry and storage

Use [Infrabel's official all-track-segment dataset](https://opendata.infrabel.be/explore/dataset/geografische-positie-van-alle-spoorsegmenten/), exported as WGS84 GeoJSON: **25,148 source segments**, catalogue processed **15 June 2026**, accessed **19 October 2026** in Melbourne. The catalogue declares **CC0**, and the replay credits Infrabel. The source export URL and SHA-256 are recorded in the committed derived reference.

The existing France compiler joins original coincident segment endpoints/vertices rounded to seven decimals and simplifies curves between preserved junctions. Interior crossings do not join and there is no distance snapping. This is **inferred geographical topology**, not native operational junction data; elevations are not used to identify running tracks. Reuse the existing indexed station-local 150 m anchoring and connected railway routing. Reject disconnected or excessive detours; gaps remain empty paths, not straight-line shortcuts.

**99.47% of scheduled legs** have mapped geometry. Remaining gaps include some southern corridors around Libramont/Marbehan and border sections. Preserve those until an actual connected alignment is validated.

The prepared week is **827 KB gzip**, plus **1.03 MB gzip** of preparation-only derived track geometry (about **1.86 MB** added storage). Monday's browser response is **641 KB gzip**. Local uncached response preparation measured about **0.3 seconds**; hosted timings can differ. Raw source files are not sent to browsers. Schedules retain shared stop patterns and flat timing vectors.

## Future additions only

[Belgian Mobility](https://data.belgianmobility.io/en/data.html) lists STIB-MIVB (Brussels metro/trams/buses), De Lijn (Flemish trams/buses) and LETEC (Wallonia). Separate public archive directories exist for [STIB-MIVB](https://gtfs.flatturtle.cloud/stib-mivb/), [De Lijn](https://gtfs.flatturtle.cloud/delijn/) and [TEC](https://gtfs.flatturtle.cloud/tec/). Their historical ZIPs, calendars, route geometry, mode scope and browser volume need validation before enabling them; Belgium rail's Infrabel paths must not be reused for buses or urban tracks.

Station boarding reports could support typical-day station demand later. No such report was imported or used to estimate train loads; the brief's 2024 totals would need validation before applying them to any heatmap or to a different year.

## Rebuild

```bash
.venv/bin/python scripts/prepare_belgium_geometry.py --cache .cache/belgium
.venv/bin/python scripts/prepare_belgium_replay.py --cache .cache/belgium
.venv/bin/python -m pytest tests/test_belgium.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The geometry compiler expects `infrabel-segments.geojson` from its recorded export URL and `segments-catalog.json` from the matching catalogue API. It checks export completeness and unique segment IDs. The replay builder downloads the pinned timetable if absent, verifies both input hashes and uses the existing selected-day compressed HTTP cache. When extending dates, validate a suitable archived timetable and source classifications first. Do not add other modes or passenger estimates implicitly.
