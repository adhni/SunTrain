# Belgium rail

Belgium uses the established SunTrain replay for **1–7 June 2026**, matching France, Switzerland, Germany and the Netherlands. It includes SNCB/NMBS trains, Brussels metro/trams, Antwerp/Ghent/coastal trams, Charleroi light rail and Liège tram T1. Trains and metro/light rail open first; trams are selectable under Transport. Existing playback, filters, details, Overview, themes and fullscreen are reused. Buses and passenger features are excluded.

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

The national train component contains **24,165 departures**: Monday–Sunday **3,786 / 3,794 / 3,801 / 3,795 / 3,794 / 2,653 / 2,542**. All selected candidates were prepared without schedule-parsing omissions.

## Geometry and storage

Use [Infrabel's official all-track-segment dataset](https://opendata.infrabel.be/explore/dataset/geografische-positie-van-alle-spoorsegmenten/), exported as WGS84 GeoJSON: **25,148 source segments**, catalogue processed **15 June 2026**, accessed **19 October 2026** in Melbourne. The catalogue declares **CC0**, and the replay credits Infrabel. The source export URL and SHA-256 are recorded in the committed derived reference.

The existing France compiler joins original coincident segment endpoints/vertices rounded to seven decimals and simplifies curves between preserved junctions. Interior crossings do not join and there is no distance snapping. This is **inferred geographical topology**, not native operational junction data; elevations are not used to identify running tracks. Reuse the existing indexed station-local 150 m anchoring and connected railway routing. Reject disconnected or excessive detours; gaps remain empty paths, not straight-line shortcuts.

**99.47% of scheduled legs** have mapped geometry. Remaining gaps include some southern corridors around Libramont/Marbehan and border sections. Preserve those until an actual connected alignment is validated.

The combined prepared week is **4.08 MB gzip**, plus **1.03 MB gzip** of preparation-only Infrabel geometry (about **5.11 MB** total Belgium storage). Monday's opening train/metro response is **753 KB gzip**, trams alone **774 KB**, urban rail together **911 KB**, or all modes **1.61 MB**. Raw source files are not sent to browsers. Schedules retain shared stop patterns and flat timing vectors.

## Urban rail sources and coverage

All three original archives were actually downloaded and validated. Their published route shapes are used directly, with ordered stop projection and per-leg recovery from the existing preparation engine. All selected urban legs have usable supplied geometry, including the Brussels metro ring and Coastal Tram. **Infrabel main-line tracks are not used for urban rail.**

| Archive | Feed validity / version | SHA-256 |
| --- | --- | --- |
| [STIB-MIVB, 31 May](https://gtfs.flatturtle.cloud/stib-mivb/stib-mivb-gtfs_2026-05-31.zip) | 25 May–21 June 2026; `2_13_20260525_010638` | `abb7e03497c3f61a1e7f92651a59b181a3e21ae606145fdd7f056e83d0941fb4` |
| [De Lijn, 31 May](https://gtfs.flatturtle.cloud/delijn/delijn-gtfs_2026-05-31.zip) | 30 May–30 September 2026; `20260530_20260930_003000` | `51f2a28e44d8f9a3d5bd9b36b7ac66992d638bec8b46d873015acae1f2cb3baa` |
| [LETEC, 30 May](https://gtfs.flatturtle.cloud/tec/tec-gtfs_2026-05-30.zip) | Feed end/version unspecified; calendars explicitly validated for the week and adjoining service days | `b887f24fc1164a05be272fc7fdfb0957ebe988aab1fef6f5578e3a8eef95007f` |

Select only STIB rail types 0/1, De Lijn type 0, TEC Charleroi type 1 M2/M3/M4 and TEC Liège type 0 T1, with audited agency IDs/names. Charleroi M1 is not present as rail in this snapshot. Seasonal services appear only when their actual calendars run; no July-only Ghent festival services are assigned to June. Preserve published STIB/De Lijn line colours; TEC's colourless lines use SunTrain teal/purple display colours. Original trips/patterns/stations/paths are namespaced by feed before merging so overlapping local IDs cannot collide. Train numbers and all national train departures remain intact.

Urban timetables and shapes are **CC BY 4.0**, with source/archive dates and SunTrain processing credit. TEC's missing publisher revision is explicitly labelled as unspecified; its archive date is not presented as a publisher update. All source hashes, calendars and credit remain in the bundled metadata.

The combined week contains **104,783 departures**: national trains **24,165**, STIB-MIVB **49,564**, De Lijn trams **25,755**, Charleroi light rail **3,224**, Liège tram **2,075**. No selected schedule-parsing omissions or bus services are included.

## Future additions only

[Belgian Mobility](https://data.belgianmobility.io/en/data.html) and the same FlatTurtle archive directories provide bus feeds for future expansion. Validate bus calendars, road shapes and browser volume separately before enabling them. Do not reuse Infrabel or metro/tram paths for buses.

Station boarding reports could support typical-day station demand later. No such report was imported or used to estimate train loads; the brief's 2024 totals would need validation before applying them to any heatmap or to a different year.

## Rebuild

```bash
.venv/bin/python scripts/prepare_belgium_geometry.py --cache .cache/belgium
.venv/bin/python scripts/prepare_belgium_urban.py --cache .cache/belgium
.venv/bin/python -m pytest tests/test_belgium.py tests/test_belgium_urban.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The geometry compiler expects `infrabel-segments.geojson` from its recorded export URL and `segments-catalog.json` from the matching catalogue API. It checks completeness and unique IDs. The urban builder creates or validates the cached national component, downloads any missing pinned feeds, prepares only selected rail trips and merges the compact references atomically. `prepare_belgium_replay.py` alone now writes the national component to `.cache/belgium/be-nmbs-week.json.gz`; it does not overwrite the combined site reference. Extending dates requires updating and validating all participating archives/calendars before merging. Do not add buses or passenger estimates implicitly.
