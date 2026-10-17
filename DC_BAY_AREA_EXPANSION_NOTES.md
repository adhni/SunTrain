# Washington, DC and SF Bay Area expansion notes

## Implemented scope

**Washington, DC:** all six WMATA Metrorail lines, **5–11 October 2026**, in `America/New_York`. Red, Blue, Orange, Silver, Green and Yellow retain their published stop sequences, short turns and branches. The rail feed also contains a `SHUTTLE` bus route; it is explicitly excluded. Metrobus, DC Streetcar, MARC and VRE are not included.

**SF Bay Area:** BART, **17–23 August 2026**, in `America/Los_Angeles`. Yellow, Orange, Green, Red and Blue lines plus the Grey **Oakland Airport connector** are included. The source's twelve direction-specific railway route IDs are grouped into six map/filter entries, with original route IDs retained in the patterns. `directions.txt` supplies North/South labels. A few trip direction bits disagree with that file; where a direction-specific route has just one published direction name, that unambiguous route label is retained. Bus bridges, Muni, Caltrain, ACE, SMART and other operators are not included. BART published journeys can span connections such as eBART; this replay does not identify a physical vehicle continuing through a transfer.

These are historical **schedule estimates**, not observed GPS, delays, guaranteed running-track locations or every temporary service change. Neither addition has individual train passenger loads. Passenger sizing and heatmaps remain unavailable; the Overview continues to analyse Melbourne data.

## Verified downloads and dates

The [WMATA developer page](https://www.wmata.com/about/developers.html) documents its key-protected feeds. The [MobilityDatabase rail archive](https://mobilitydatabase.org/feeds/gtfs/mdb-1847) provides publicly downloadable historical copies; no WMATA key is needed by SunTrain to replay the prepared local data. Both selected ZIPs actually downloaded successfully:

| Snapshot | Bytes | Declared feed validity | Assigned service dates |
| --- | --- | --- | --- |
| [3 October 2026, 00:15 UTC](https://files.mobilitydatabase.org/mdb-1847/mdb-1847-202610030015/mdb-1847-202610030015.zip) | 2,931,125 | 1–9 October 2026 | 4–6 October |
| [7 October 2026, 01:21 UTC](https://files.mobilitydatabase.org/mdb-1847/mdb-1847-202610070121/mdb-1847-202610070121.zip) | 2,365,584 | 6–16 October 2026 | 7–12 October |

The adjoining 4 and 12 October service dates preserve overnight carry-ins. Snapshot assignment is by **GTFS service date**, with no overlapping assignments, rather than the business window into which a trip extends. The newer snapshot is not applied to earlier service dates. WMATA uses `calendar_dates.txt` without `calendar.txt`; do not treat the absent weekly file as an empty schedule or extend trips to every weekday. The latest October 16 download was inspected but rejected for this replay because its `feed_info.txt` starts on October 15, despite calendars extending further. The dated snapshots' SHA-256 values are pinned in `scripts/prepare_us_rail_replay.py` and stored in the bundle metadata.

The [official BART download](https://www.bart.gov/dev/schedules/google_transit.zip) redirected to a [dated August release](https://www.bart.gov/sites/default/files/2026-08/google_transit_20260810-20270108_v02.zip). It downloaded successfully: **892,312 bytes**, SHA-256 `affdc4d70cac01f71e54f049c754ba36824a885edcdef2ef8b024820c9e93080`, last modified **4 August 2026**. `feed_info.txt` calls it version **72**, valid **12 January–30 August 2026**, while its active calendars describe an **August 10 timetable** continuing into January 2027. This disagreement is not silently ignored: **17–23 August and adjoining service dates lie within both intervals**. An October replay would require corrected metadata or another validated snapshot before implementation. Weekend exceptions in the selected week are retained. Neither BART nor the selected WMATA files contain frequency-based services that require generated departures.

These are deliberately verified 2026 weeks; no 2024 schedules have been inferred from newer files. Downloads occurred on 18 October 2026 in Melbourne local time. Raw source files stay in the ignored cache and are never served to browsers.

## Geometry and known gaps

Both cities reuse the existing whole-journey ordered projection onto each trip's **own published shape**, within **150 m** of every stop. No other route is substituted, no tolerance is widened and no straight connector is created. WMATA's supplied native distance anchors miss numerous platform locations by 150–235 m, even though those platforms match the same shapes within 150 m through ordered projection. DC therefore explicitly selects `geometry_method="ordered_projection"` for this validated source. It does not try an invalid anchor and silently fall back to a different railway. Toronto and the Australian cities retain their existing native-anchor behaviour.

DC has **75 shared patterns**, **1,405–1,857 services per day**, and a prepared reference of about **0.11 MB**, with **no omitted trips**. One Red Line **Friendship Heights–Shady Grove** variant cannot match its own shape within tolerance. It affects **11 source trip IDs**, or **three occurrences per day Monday–Saturday and two Sunday**. Its stops and schedule remain present; markers appear at stations and disappear between stops.

BART has **45 shared patterns**, **785–1,021 services per day**, and a prepared reference of about **0.08 MB**, with **no omitted trips**. One Yellow Line **Antioch–SFO** variant has stop times continuing to a Millbrae transfer platform while its assigned `001A_shp` ends at SFO. It affects **12 source trip IDs**, or **four occurrences per replay day**. It remains a station-only journey rather than acquiring a fabricated SFO–Millbrae connector. These known gaps are bounded in tests and explained by each map's quality note and selected-service details. Do not delay unrelated expansion work chasing these isolated source records.

## Rebuild and future extensions

Run `./.venv/bin/python scripts/prepare_us_rail_replay.py dc` or `sf_bay`. The source wrappers define scope and route labels; `scripts/prepare_rail_replay.py` handles validated snapshot selection, calendars, shared patterns, paths and references. Toronto delegates to the same preparation code; a rebuilt Toronto reference was compared with the existing bundle and its data was identical. Sources are cached in `.cache/us-rail/` and checked against SHA-256 before processing. Each source must cover its assigned dates inside the **declared feed validity**, as well as its service calendars. Prepared defaults are in `dashboard/replay.py`, city periods/settings in `dashboard/cities.py`, and source pins in the preparation script. `SUNTRAIN_DC_REFERENCE` and `SUNTRAIN_SF_BAY_REFERENCE` override prepared files.

For longer periods, first obtain snapshots covering the requested days **and adjoining service dates**, validate each declared interval, and assign every service day to exactly one source. Do not extrapolate this BART release beyond August 30 merely because some calendar rows run later. Preserve 03:00 boundary carry-ins without exact duplicate occurrences inside a day. Test local daylight-saving transitions rather than using fixed UTC offsets. Keep schedule arrays shared in the browser.

WMATA rail replacement buses and BART bus bridges must remain buses if enabled later. Ordinary DC buses need their own Metrobus source and scope. Other Bay Area operators need separate verified historical GTFS, operator licences and geometry checks; their presence in the region does not make them part of BART's feed. Passenger data requires a separate audit and must retain its actual station/time aggregation level rather than becoming individual train loads.

## Licensing and attribution

WMATA data uses its [Transit Data Terms of Use](https://developer.wmata.com/license), **not Creative Commons**. The terms permit use and redistribution within an application, restrict separate data/API redistribution and endorsement, and require users accessing the underlying WMATA services to follow their account/key rules. SunTrain uses the public historical copies for this application, exposes no new general transit-data API and needs no WMATA credentials during replay. Retain WMATA attribution, the terms link and the statement that SunTrain is independent and positions are estimates. Do not republish these sources as an unrelated data service.

BART uses its [Developer License Agreement](https://www.bart.gov/schedules/developers/developer-license-agreement), which permits data use, reproduction and redistribution subject to its terms. Retain BART source and licence links. Neither operator's official logos, trademarks or copyrighted map artwork are used. Each replay displays the operator's source acknowledgement, licence link and independence statement.
