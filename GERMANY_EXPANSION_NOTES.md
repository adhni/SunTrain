# Germany rail

## Implemented

Location **Germany**, **1–7 June 2026**, matching the Netherlands week, in **Europe/Berlin**. Reuses the existing compact schedule loader, replay, route/operator filters, city Overview, themes and fullscreen. Long-distance trains open first. **Regional rail** and **S-Bahn / Regio-S-Bahn** are optional Transport selections. U-Bahn, trams and buses are excluded. No live tracking or passenger loads.

The long-distance layer contains **5,554 scheduled German journey portions**: **803 / 805 / 806 / 790 / 814 / 768 / 768** from Monday through Sunday. Source categories are **ICE, IC, EC and ECE**. Active operators are **DB Fernverkehr AG, SNCF, Dänische Staatsbahnen and SÜWEX**. Agency names and categories are retained as supplied, rather than inferred from rolling stock or marketing names. SÜWEX's source-labelled IC services are included; its regional services are not.

**Railjet / EuroNight limitation:** all six requested category families are supported by the preparation scope, but this particular archive has **no active German RJ or EN journey portion in the selected week**. Its EN trips are abroad; three RJ candidates with German calls fall outside the week. Do not present those foreign services as German coverage or rename ICE/EC services to fill the gap. **352 included journey occurrences cross midnight**, including scheduled overnight ICE/IC services; this is not a claim to cover sleeper operators or the complete Nightjet network. The separately audited regional archive also contains NJ/RJX and other long-distance entries; these are not enabled by the regional scope. Audit their German calls and possible codeshare duplicates against the long-distance layer before extending sleeper coverage.

## Verified timetable

- Publisher: **DELFI e.V. / GTFS.de**, [dedicated long-distance feed](https://gtfs.de/en/feeds/de_fv/), [feed documentation](https://gtfs.de/en/feeds/).
- Public historical ZIP: `https://files.mobilitydatabase.org/mdb-768/mdb-768-202605310001/mdb-768-202605310001.zip`, from the [Mobility Database history](https://mobilitydatabase.org/feeds/gtfs/mdb-768).
- Captured **31 May 2026**, covering source calendars **30 May–29 June 2026**. Actual `calendar.txt` and `calendar_dates.txt` determine each trip's active dates. One snapshot covers the entire week and adjoining service dates; no current schedule is used for June.
- Size **413,072 bytes**, SHA-256 `9da51452d56f80cbae493af56ac023aab7e4daee2836f12d8721dfaa74738ebe`.
- SHA-1 `d139dbe3486e98868bc5eca73557b3c733abe7b4`: **exactly matches** the [requested Transitland version](https://www.transit.land/feeds/f-germany~long~distance~rail/versions/d139dbe3486e98868bc5eca73557b3c733abe7b4).
- The actual Transitland API ZIP request returned **401 without credentials**. [Transitland's archive policy](https://www.transit.land/documentation/concepts/static-gtfs-feed-versions) requires appropriate historical-download access; no account, subscription or payment was needed for the identical Mobility Database file.
- 13 agencies, 96 routes and 5,598 source trip definitions; no `shapes.txt`, `frequencies.txt`, direction bits or individual train numbers. `feed_info.txt` exists but omits validity dates: preparation explicitly validates actual calendars instead. The shared engine now accepts this audited case and absent shapes while keeping existing feeds' date checks.

Scope requires route type **2**, an exact pinned agency ID/name, and a category/optional numeric line code matching ICE, IC, EC, ECE, EN or RJ. Route IDs and original GTFS trip IDs remain intact. A label such as **ICE 28** is a source line designation, **not an individual train number**. Directions are **Not specified**; origin/destination identify the journey portion. Colours are SunTrain display choices by category, not claimed official line colours: ICE red `#E32219`, IC burgundy `#B32636`, EC/ECE teal `#007A87`; future RJ dark red and EN blue. Supplied route colours take priority.

## International and overnight handling

`data/reference/germany/station-scope.json` pins the audited German/border stop IDs and names to this exact timetable hash. **Basel Bad Bf** is explicitly included as a German railway border station; **Forbach, France** is excluded. Its station IDs must be re-audited when changing archives.

Keep the original ordered calls **from the first through the last audited German/border call**. Retain any foreign calls between them rather than connecting over a foreign detour. No additional border stops or border-crossing times are invented. Foreign-only sections and journeys with fewer than two scoped calls are excluded. This intentionally gives German portions rather than complete international journeys; it cannot show the border-to-station stretch for a train with only one German call.

Of the 3,217 calendar-relevant candidate definitions, 2,596 meet that scope; 591 are trimmed. The remaining 621 are outside scope or have only one scoped call. No included trip has a parsing omission. These candidate counts are not daily departure counts.

Each portion belongs to exactly one **03:00–03:00 start-day window**, using its first retained call. Original GTFS times, including values above 24:00, are preserved without shifting the actual instants when clipping. A trip already assigned to the preceding business day is not repeated in the next day's replay. June uses CEST (UTC+2); conversion uses `zoneinfo` and the standard GTFS noon-minus-12-hours service origin. The selected week does not cross a daylight-saving change.

## Railway geometry

The bundled offline reference `data/reference/germany/db-rail-2026-10-18.json.gz` contains **28,230 passenger/mixed-use railway links** from **DB InfraGO's official INSPIRE network**. It uses published DB junction and station-node IDs and coordinates, not arbitrary connections between nearby tracks. RailwayLink geometry can be reversed relative to its named start/end nodes; the extractor corrects orientation against the published junction positions.

[Official service](https://geoviewer.deutschebahn.com/geoviewer-geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities), [official catalogue / licence metadata](https://www.govdata.de/suche/daten/wms-schienenverkehrsnetz-db-infrago). GeoServer's WFS provides `tn-ra:RailwayLink`, `RailwayNode`, `RailwayStationNode` and `DBInspire:TN.RailwayLinkMixed` / `TN.RailwayLinkPassengers`. Raw downloads and hashes are recorded in the geometry metadata. Links are paginated in blocks of 5,000; completeness and duplicate checks are required.

**This geometry was accessed 18 October 2026 UTC, not archived in June.** It supplies geographical alignments for the authentic June schedules, not proof of historical track assignments, engineering diversions or precise running-track use. The separate official [May 2026 infrastructure CSV](https://www.govdata.de/suche/daten/infrastrukturdaten-der-db-infrago) was downloaded and inspected, but its segmented lines lack the explicit network-node connections needed here; it is **not** the bundled geometry. OSM/Geofabrik/Overpass were investigated; no OSM railway geometry is used in this addition, and OpenRailwayMap tiles were not scraped.

Cargo-only and fictitious links are excluded. Missing geometry/junctions and contradictory endpoints stay excluded: **177 links lack geometry, two lack junction positions, 150 disagree with their named junctions by over 50 m**. Small source centreline/junction generalisation differences are reconciled only at the **same published DB node ID**, up to 50 m (observed maximum **49.43 m**). Separate nearby track IDs never connect. This is a route-centreline display, not a railway signalling graph.

The matcher reuses the existing `RailGraph` and simplifier. ICE/ECE routing favours faster published railway corridors; IC/EC use distance routing constrained by intermediate timetable stops. Detours above three times the direct distance (minimum allowance 5 km) are rejected. All station endpoints still meet the existing **150 m** check. No distant straight-line fallback is allowed. Native node connections alone cannot prove a particular historical service used the inferred corridor.

**45,300 / 47,599 scheduled legs (95.17%)** have usable geometry; **2,299 legs** remain gaps. Five of 5,554 journey occurrences have no usable moving section and appear only at scheduled calls. Frequent gaps include Berlin Hbf–Gesundbrunnen, Hamburg Hbf–Altona and Aschaffenburg–Würzburg. These gaps are explicit, not filled by false connectors. Representative Nürnberg–Erfurt, Frankfurt Airport–Siegburg/Cologne and Leipzig–Dresden paths have detailed railway curves; the timetable/path audit found no resolved leg over 10 km requiring an average speed above 380 km/h.

## Attribution and passenger data

GTFS.de's feed and the official DB railway-network metadata specify **CC BY 4.0**. Retain **DELFI e.V. / GTFS.de** timetable credit, **DB InfraGO AG** railway credit, licence/source links and the notice that SunTrain matched/simplified paths. Those credits are visible through the existing source footer. No logos, official map artwork, live APIs or credentials are required at runtime.

No downloadable historical **individual-train passenger counts** were verified. Occupancy forecasts and annual operator/station aggregates would not establish actual loads on these trains. Passenger controls stay unavailable; passenger data does not delay replay.

## Size, validation and rebuild

The weekly replay is **1,615,499 bytes gzip**, with **1,233 timing patterns**, **769 shared stop/geometry sequences** and **352 used station records**. The offline geometry database is **2,556,860 bytes gzip** and is not downloaded by visitors. Monday's selected-day HTTP JSON is approximately **1.30 MB gzip**; shared schedules are retained throughout. No new runtime dependencies or routing service were added.

Validation: **168 Python tests and 36 JavaScript tests passed**, including existing app, HTTP, compact-schedule, Netherlands and London regressions. Focused checks cover the scope, category colours, source pins, missing feed validity/shapes, domestic clipping, nationwide dates, unique overnight assignment, detailed representative corridors, speed-aware track choice and independence from Melbourne data. Chrome checks cover routes, vehicle details/follow, 2,000× playback, Overview without refetch, Sunday, dark mode, fullscreen, a mobile-width smoke check and switching back to the Netherlands. Local Chrome reached Germany's usable map in **0.98 seconds after selection**; this is not a hosted-site benchmark.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/prepare_germany_replay.py
```

Downloads the pinned historical ZIP if absent, verifies its hash and uses the bundled hash-checked geometry. Cache: `.cache/germany/`; runtime override: `SUNTRAIN_GERMANY_REFERENCE`. `--cache`, `--geometry` and `--output` override paths.

To rebuild geometry, retain the exact raw WFS downloads named/hashed in the bundled metadata, then run `scripts/prepare_germany_geometry.py --cache .cache/germany`. Metadata records `typeNames`, pagination and SHA-256 per file; use `service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&srsName=EPSG:4326` at the recorded service URL. Current WFS responses can change: audit replacements and update the geometry pin deliberately. Rebuilding the replay does not need those raw files or the evaluated May CSV.

For a longer timeframe, obtain dated archives whose **actual calendars** cover all days, re-audit station IDs/categories/operators, and preserve one start-day assignment. Do not extend the picker alone or replace June with `latest.zip`. Dedicated historical ÖBB/Nightjet/other operator schedules should be investigated for German sleeper/Railjet coverage before claiming it. Regional and S-Bahn are now implemented as the separate optional daily bundles below. Other urban modes and additional private railway geometry remain future work.


## Regional rail and S-Bahn addition

The **same 1–7 June 2026 week** is available through the existing Transport control: **Regional rail** (`regional_rail`) and **S-Bahn / Regio-S-Bahn** (`commuter_rail`). The opening selection remains long-distance only. Route/operator filters, city Overview, details/follow, themes, fullscreen and speed controls are reused; changing modes preserves the clock. Clearing Transport selects all three rail layers.

Verified historical ZIP: `https://files.mobilitydatabase.org/mdb-1089/mdb-1089-202605310104/mdb-1089-202605310104.zip`, from the [regional archive history](https://mobilitydatabase.org/feeds/gtfs/mdb-1089). Captured **31 May 2026**, **11,655,597 bytes**, SHA-256 `cffefa8a878d5846514ff472123060ca44d1cb356f0a93e575cf90fd4305c913`. This is a genuine historical copy of [GTFS.de's regional feed](https://gtfs.de/en/feeds/de_rv/); the rolling `latest.zip` is not used to simulate June. Calendars and exceptions determine each selected date, including the reduced 4 June holiday service. There are no shapes or frequency templates; actual calendars are checked because feed validity dates are omitted.

This ZIP also contains sleepers, long-distance, tourist/museum and tram-train entries. They are **not all regional trains**. `regional-scope.json` pins **823 route definitions** by ID, exact agency/name, source line label and one of the two modes. Regular RE/RB/IRE/MEX, NRB/NRE and audited named regional services (including AKN, FEX, trilex and selected border services) use Regional rail. S/RS lines use S-Bahn / Regio-S-Bahn, including source-labelled **S** services without an invented line number. German tram-train-only agency groups, tourist/museum-only labels, Nightjet/other sleepers, Flixtrain and numbered long-distance services are excluded. The selected operator list is generated from actual included patterns in `regional-operators.json`.

`regional-station-scope.json` pins the **separate regional feed's station IDs**; long-distance stop IDs are not assumed interchangeable. French border-buffer stations and Krzewina Zgorzelecka (Poland) are excluded as journey endpoints. Basel Bad Bf remains explicitly included. The first-to-last German/border-call rule, retained foreign intermediate calls, original timestamps and unique 03:00 start-day assignment are the same as long-distance.

The additional layers reuse the **same bundled DB InfraGO geometry**. An offline spatial index speeds up station matching without changing the 150 m projection candidates, endpoint rules or routing algorithm. Private infrastructure missing from the DB network remains unresolved. In particular, the AKN network has schedules but no moving paths in this reference; substantial gaps also affect portions of Südwestdeutsche Verkehrs-AG, Rurtalbahn and other private services. These are schedule entries with explicitly unavailable positions, not complete animation coverage. No tolerance was widened or distant connector invented for this addition.

Berlin S-Bahn (including Ringbahn S41/S42), Hamburg, Stuttgart and Hannover were checked. Source agency names and route labels are retained, including provisional/special labels rather than replacing them with a current network diagram. No claim is made to individual running tracks or every historical engineering diversion.

Source route colours take priority. Otherwise SunTrain display colours are **regional red `#C83038`** and **S-Bahn green `#008D4F`**, not claims of official individual line palettes. Overview labels these modes Regional rail and S-Bahn; other cities keep their existing labels.

### Loading and identifiers

Each optional mode has **seven independent daily files**, under `data/reference/germany/regional_rail/` and `commuter_rail/`. A long-distance-only request neither opens nor fingerprints those schedules. S-Bahn-only does not open the long-distance or regional schedules. HTTP revisions include exactly the selected files; the existing compressed disk cache, serialization lock, cancellation and schedule-release behaviour remain in use. No new runtime dependency or external routing service was added.

Schedules keep flat shared time vectors and stop patterns. The browser receives one date and selected modes, not the raw national ZIP or all seven days. Independent bundles namespace their pattern/topology keys, and runtime service IDs include their source mode so mixed feeds cannot overwrite one another. Displayed trip IDs remain the original GTFS IDs. A combined-mode test checks every service's first/last station against its own topology.

The prepared files repeat some geometry across dates in exchange for loading only the requested day. They are not all downloaded at startup. The unchanged long-distance source remains about 1.62 MB gzip, with its selected Monday response about 1.30 MB gzip. Combined modes are a substantially larger optional download; the isolated local all-mode build measured roughly **306 MiB peak process memory** and **5.23 seconds** for **38,867 Monday services**. Its compressed HTTP response was **8,486,859 bytes**. Those are local measurements, not hosted latency or a guarantee for every server/phone.

Rebuild both additions with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/prepare_germany_regional.py
```

The command verifies the archive and geometry hashes, writes optional per-day/mode files and regenerates the operator list. Use the existing `--cache`, `--geometry` and `--output` overrides. Runtime directories can be overridden with `SUNTRAIN_GERMANY_REGIONAL_RAIL_REFERENCE` and `SUNTRAIN_GERMANY_COMMUTER_RAIL_REFERENCE`. Keep scope files tied to their exact source hash when changing dates or archives; do not classify every type-2 route as regional. Passenger features remain unavailable and the existing DELFI/GTFS.de and DB InfraGO CC BY 4.0 credits apply.


### Final regional coverage and validation

- **155,100 regional departures**: 23,796 / 23,718 / 24,178 / 20,108 / 24,342 / 20,276 / 18,682, Monday through Sunday.
- **95,512 S-Bahn departures**: 14,268 / 14,367 / 14,552 / 12,523 / 14,847 / 13,155 / 11,800.
- **92 active source operators** across the optional layers; 17,279 shared timing patterns in their offline weekly preparation reference. No parsing omissions.
- Regional geometry: **1,414,061 / 1,579,739 scheduled legs (89.51%)**. **11,470 regional occurrences** have no matched moving section and appear only at scheduled stops.
- S-Bahn geometry: **1,537,410 / 1,601,813 legs (95.98%)**. **2,531 S-Bahn occurrences** have no matched moving section. Missing paths are never replaced by straight lines.
- Optional prepared files total approximately **49 MB gzip across seven days and two modes**. A selected Monday regional file is **5.93 MB gzip**, S-Bahn **1.42 MB**. The browser never fetches all fourteen files for one replay.

Validation covers all fourteen day/mode bundles, calendar counts and unique start-day ownership, source scopes/colours, exact indexed-versus-original track projections, immutable source trip IDs, mixed-mode service IDs/topology resolution and skipped unselected reference files. HTTP checks verify optional caches are released after compression and default revisions ignore changed unselected files. Existing app/HTTP/compact-schedule/Netherlands/London regressions and all 36 JavaScript tests pass. Chrome checks cover optional modes, unchanged clocks, Berlin Ringbahn details/follow, combined Overview without refetch, 2,000× playback, themes, fullscreen, Sunday, returning to long-distance only and a mobile-width smoke check. Final first-request mode switches were approximately **1.13 seconds for S-Bahn, 3.60 for regional rail and 4.10 for all rail** locally. Earlier cached-response switches were around 0.6–1.2 seconds. These are not Render benchmarks.
