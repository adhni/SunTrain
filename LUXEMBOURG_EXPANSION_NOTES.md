# Luxembourg expansion notes

## Included

**1–7 June 2026**, matching the Netherlands, Germany and most other European replays. **Passenger trains and Luxtram T1**. Rail categories: RB, RE, TER, IC and TGV represented in the national timetable. Includes northern, eastern and southern branches, domestic portions of cross-border services and actual source border timing points. Nearby international branch termini Audun-le-Tiche and Volmerange-les-Mines are retained; their unavailable foreign geometry stays empty.

**6,216 departures**, daily totals **990 / 990 / 990 / 990 / 996 / 718 / 542**; 74 retained stops and 116 shared timing patterns. Categories: RB 3,488; RE 1,509; TER 612; IC 504; TGV 103. Train-only data is **94 KB gzip**. With Luxtram the week has **9,363 departures** in **130 KB gzip**, plus **154 KB** preparation-only national railway geometry and **12 KB** tram geometry. Uses existing playback, filters, service details, themes/fullscreen and Luxembourg Overview. No new infrastructure or browser schedule expansion. Select Trains or Tram under Transport.

The operator filter says **CFL**, following the source's railway agency 11. TER/IC/TGV category names do not establish the actual operating company of every international journey. Categories use a SunTrain display palette because the archive supplies no rail route colours; these are not purported official CFL line colours.

## Historical timetable

[Official national GTFS catalogue and archive](https://data.public.lu/en/datasets/horaires-et-arrets-des-transport-publics-gtfs/) · Administration des transports publics · **CC BY 4.0**.

Actually downloaded [GTFS dated 27 May 2026, published 28 May](https://download.data.public.lu/resources/horaires-et-arrets-des-transport-publics-gtfs/20260528-044959/gtfs-20260527-20260712.zip). SHA-256: `9c37b008f7e191658546c3a9247f2889065859d8a38801c18fbccdc2fe7b8933`.

The ZIP has calendars covering **27 May–12 July 2026**, actual exceptions, stop times and shapes. No `feed_info.txt`; explicit calendar validity checks cover the replay and both carry days. The selected historical snapshot describes schedules published before the replay week, not a claim to reconstruct every later amendment or disruption. Later dated June snapshots exist if future work needs a different amendment policy. Never backdate the rolling latest feed.

Only agency **11 / Chemins de Fer Luxembourgeois**, route type **2**, and the five audited railway categories are included. Agency **171**, despite its CFL name, contains bus routes and is excluded, together with all other buses in the train selection. Luxtram is prepared separately as tram transport. No frequency rows apply. **Zero malformed timetable omissions** and no duplicate trip/departure occurrences.

1,386 selected candidate trips, with 518 clipped to the retained national/border span. Source identifiers distinguish domestic `0001…` / `0002…` calls and explicitly audited border/branch calls. Foreign calls between retained endpoints preserve original order and times; distant foreign tails such as Metz, Thionville, Arlon station and Trier are excluded. Actual frontier timing points remain labelled as such; they are not presented as passenger boarding measurements. TGV replay represents its frontier–Luxembourg portion, not the complete international journey.

The feed declares **Europe/Berlin**. Preparation keeps that original timezone and verifies every hour of the selected window plus carry days against **Europe/Luxembourg** before labelling the output. They agree throughout this period (CEST, UTC+2). Trips are assigned once by first departure to a 03:00–03:00 business window; after-midnight calls retain original times.

## Railway geography

Native train shapes are sparse stop-to-stop sketches (for example the TGV shape has only four vertices). They are **not used for moving trains**.

[Official ACT / Géoportail INSPIRE RailwayLink](https://data.public.lu/en/datasets/inspire-annex-i-theme-transport-networks-rail-railwaylink-3/) · **CC0 1.0**. [Pinned GML resource](https://download.data.public.lu/resources/inspire-annex-i-theme-transport-networks-rail-railwaylink-3/20261009-231644/tn.railtransportnetwork.railwaylink.gml), downloaded 19 October 2026. SHA-256: `89d0142a9ec6821540dd167c0aa5410096ded1d73d8b4218fc220de5ede59eb4`.

3,545 official links become 3,552 graph ways, reusing the existing endpoint/vertex compiler and indexed railway routing. Reprojection respects EPSG:3035's GML **northing/easting** axis order and stores longitude/latitude output. Original coincident endpoints/vertices form junctions; no proximity snapping or invented crossings. Consecutive stop matches must be within 150 m, and implausible detours are rejected. This October geography is a reference for June schedules, not proof of historical running-track assignments or diversions.

**43,024 / 43,827 scheduled legs have usable paths (98.17%)**. The four directional gaps are the two international branches **Esch-sur-Alzette ↔ Audun-le-Tiche** and **Dudelange (Usines) ↔ Volmerange-les-Mines**. The national geometry does not supply connected coverage to their French termini. Their timetable calls remain; moving vehicles are hidden on those legs. No straight-line fallback or unvalidated neighbouring-network geometry is inserted. Full cross-border railway matching remains future work.

Attribution credits Administration des transports publics for schedules and ACT / Géoportail for geography, with dates, licences and SunTrain's selection/reprojection/matching/simplification. Source hashes are enforced by both preparation scripts.

## Luxtram T1 — included

Uses the same pinned May 2026 national GTFS, agency **111 / Luxtram**, route **T1**, type **0**. Includes source airport–Stadion journeys and short workings. **3,147 departures**: **514 / 514 / 514 / 514 / 514 / 339 / 238** per day. Zero timetable omissions or missing tram paths; overnight trips follow the same single business-day assignment. The route has a green SunTrain display colour because this archive leaves `route_color` blank.

The national ACT train graph does not cover the tram network, and native tram shapes are stop sketches. Geometry therefore uses actual **OSM `railway=tram`** tracks from the [Geofabrik Luxembourg extract](https://download.geofabrik.de/europe/luxembourg.html), retrieved 19 October 2026. Only shared native OSM nodes connect tracks; depots/sidings are excluded. October geography is a reference for June schedules, not exact historical running-track evidence. The derived OSM geometry is distributed under **ODbL 1.0**, independently of the CC BY timetable and CC0 ACT data, and credits OpenStreetMap contributors/Geofabrik in the site. The compiled geometry and preparation script are committed for reuse.

Adds approximately **35 KB gzip** to the timetable reference. Existing trains are retained. Focused checks cover the T1 endpoint coverage, paths, unique business days and mode filtering, plus browser playback/details. No bus routes are enabled.

## Reproduce

```sh
# Download the pinned GML to .cache/luxembourg/railwaylink.gml.
# Geometry preparation only needs pyproj (no dashboard runtime dependency).
PYTHONPATH=.cache/portugal/tools .venv/bin/python scripts/prepare_luxembourg_geometry.py .cache/luxembourg/railwaylink.gml
# Optional geometry regeneration also needs preparation-only pyosmium:
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_luxembourg_tram_geometry.py .cache/luxembourg/luxembourg.osm.pbf
# Builds trains + tram together; the train-only script would replace the combined output.
.venv/bin/python scripts/prepare_luxembourg_tram.py
.venv/bin/python -m pytest tests/test_luxembourg.py tests/test_luxembourg_tram.py
```

Downloads and temporary tools remain under ignored `.cache/`; committed references contain the compact shared schedule and preparation-only geography. The browser downloads only the selected day through the existing endpoint.

## Next additions

1. **Luxtram is included:** when expanding the dates, rebuild the combined trains+tram reference and validate its actual timetable calendars. Keep tram matching separate from the national railway graph.
2. **AVL / RGTR / TICE buses:** schedules are in the same ZIP: agency 6 (57 routes), 1 (607 routes), and 16 (10 routes). These are archive route counts, not a guarantee of active routes every day. Add road geometry and validate service volume before enabling; keep buses optional if needed for loading. Use Luxembourg/operator colours, never Melbourne orange by default.
3. **CFL bus routes:** agency 171 has 20 bus routes. Audit replacement versus regular services separately rather than inferring railway service from the CFL name.
4. **Longer timeframe:** select actual archived resources covering every added date/carry day and amendments. Recheck scope, calendars, overnight uniqueness, timezones and source terms; do not stretch constants beyond the source validity.
5. **International rail:** obtain connected railway geography to the retained French branch termini before filling those gaps. More distant Belgium/France/Germany journeys need additional scope and geometry validation, with no duplicate trains from other city references imported into Luxembourg.
6. **Passengers:** [STATEC/CFL railway statistics](https://data.public.lu/en/datasets/entreprises-transports-transport-ferroviaire/) include annual passenger traffic totals. These do not establish hourly station demand or individual train occupancy. No suitable train-level historical load dataset was validated; passenger sizing/heatmaps remain disabled.
