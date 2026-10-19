# Great Britain rail replay

## Scope

The initial week is **5–11 October 2026**, in **Europe/London** (BST, UTC+1). It uses the same actual archived timetable as London, rather than pretending a current schedule represents June. Select **Great Britain** for mainline trains and optional shared London rail. The separate **London** view retains its existing networks and buses.

Included operators: **LNER, Avanti West Coast, CrossCountry, TransPennine Express, Hull Trains, Grand Central, both dated Lumo operator records, and selected GWR/EMR intercity corridors**. Colours come from the archived route records. The source calls Lumo's records East Coast and West Coast, with route labels Lumo and Lumo Stirling; both actually have active services in this week.

The converted feed does **not** preserve an official intercity/regional category for each train. Conservative, explicit corridor selection avoids enabling every GWR and EMR local service:

- **GWR:** journeys calling at Paddington and at least one listed mainline destination/intermediate hub: Swindon, Bath, Bristol Temple Meads/Parkway, Cardiff, Swansea, Exeter St Davids, Plymouth, Penzance, Hereford, Worcester Shrub Hill, Cheltenham, Gloucester, Carmarthen, Paignton or Newton Abbot. Intermediate calls and complete source journeys are retained. This includes Night Riviera where scheduled; Plymouth–Penzance local trains and Paddington–Oxford/Reading-only services are excluded.
- **EMR:** St Pancras journeys reaching Leicester, Derby, Nottingham or Sheffield, plus journeys between at least two of those four mainline hubs. Corby commuter and EMR Regional services outside that scope are excluded.

This remains a conservative intercity corridor selection, not a claim that every intercity short working is covered. **Regional / commuter rail** is now available as an optional Transport layer: Northern, ScotRail, Transport for Wales, Greater Anglia (including Stansted Express), West Midlands Railway / London Northwestern Railway, South Western Railway, Southeastern, Southern, Thameslink, Great Northern, c2c, Chiltern and Merseyrail Northern/Wirral. The intercity layer opens first; selecting regional rail downloads only that date. Caledonian Sleeper and other urban networks remain future additions. Overground, Elizabeth line, Underground, DLR, trams, replacement buses and ordinary buses are explicitly excluded from the Britain bundles. The existing London files and selector entry are reused unchanged; no London service is copied into either stored Britain layer. In the **Great Britain** map, select **London Underground**, **London DLR / trams** and/or **London Overground / Elizabeth line** under Transport. These options read the existing London rail reference directly, once per request even when all three are selected. London buses remain in the London view. National Rail services into London (e.g. Thameslink/Southern) are new services here, not duplicate TfL journeys. No individual train loads are supplied.

## Timetable provenance and terms

- Pinned ZIP: [Planar Network release, 4 October 2026](https://github.com/planarnetwork/gb-transit/releases/tag/feed-2026-10-04), asset `gtfs-rail-and-tfl.zip`.
- Download: `https://github.com/planarnetwork/gb-transit/releases/download/feed-2026-10-04/gtfs-rail-and-tfl.zip`.
- SHA-256: `7bc0854bbc6d5206bfdd51a0e77a7bb1b3af8c627c360e2c5b0823fb03a7c5b7`; 39,552,156 bytes. Reuses the already validated London archive.
- Feed validity: **4 October 2026–4 January 2027**, version `RJTTC978.ZIP`. Release built 4 October at 11:21:39Z, converter commit `b4fabd22e5164dad1a9197ca19cc95f3f0e3d5a3`. Source calendars and exceptions select actual replay dates, including adjacent service dates for 03:00 windows.
- The brief's Interline/Transitland `uk-rail.zip` returned **HTTP 401** in this audit. No protected archive or paid API is necessary for this selected week.
- Source National Rail/RDG timetable terms remain distinct from **DfT NaPTAN's OGL v3.0** and **OSM's ODbL**. See [the converter's source licences](https://planarnetwork.github.io/gb-transit/feeds/using-this-data/#sources-and-licences). The converter's software licence does not relicense the timetable. National Rail Knowledgebase accessibility/facility fields, station URLs and fares are not reproduced.
- Attribution: National Rail timetable data © Rail Delivery Group / Rail Settlement Plan; station names/coordinates DfT NaPTAN, contains public sector information licensed under OGL v3.0; conversion Planar Network. Preserve these acknowledgements and the upstream timetable licence link when extending/reusing the bundle. A public ZIP is not a new blanket CC BY grant. The historical RSP licence template is a negotiated licence, not evidence that all timetable uses are automatically unrestricted; confirm applicable RDG/RSP permissions before unrelated bulk redistribution or a change in use.

The [official National Rail portal](https://opendata.nationalrail.co.uk/) and [Network Rail schedule feeds](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/) require registration for direct access and do not automatically provide a historical GTFS archive. No new account, secret or CIF conversion pipeline is needed for this existing archived conversion.

Schedules describe the published plan, not observed running or every later disruption. Apply dated overlays/exceptions as supplied. Source direction `0` is a placeholder, displayed **Not specified**. Source retail service IDs remain available; do not invent a public headcode from them. First departures assign each occurrence to one 03:00–03:00 business window; overnight arrival times are preserved. The selected week avoids the autumn BST transition. Later extensions must check GTFS midnight semantics on the clock-change weekend.

## Railway paths

The source `shapes.txt` is a station/passing-point **sketch**, never displayed as railway geometry. Ordered sketch points guide routing between actual calls on connected OSM railway tracks. Missing passing-point anchors may be skipped; scheduled call anchors must remain within 150 m. A stable track anchor joins adjacent routed pieces without straight connectors. At grade-separated interchanges, a failed fixed-anchor match can use flexible endpoint tracks only if the resulting single connected curve passes within 400 m of every retained corridor hint; source call anchors still require 150 m. This avoids choosing Tamworth’s wrong railway level while rejecting routes that bypass the documented corridor. Only the main connected railway component is used; no invented joins across nearby coordinates, water or disconnected track components.

Pinned PBF: `https://download.geofabrik.de/europe/great-britain-261018.osm.pbf`, **2,188,594,877 bytes**, SHA-256 `a47a150f448aeb72738019e053c8aa1ce6a3ed65dea6f1b1acd4afed75775065`.

Geofabrik's [Great Britain extract](https://download.geofabrik.de/europe/great-britain.html), dated **18 October 2026**, supplies passenger railway ways. Native OSM node IDs preserve junctions through simplification. Britain uses mph in many `maxspeed` tags; preparation converts these to km/h. The compressed derived graph is preparation-only; raw nationwide map downloads are never committed or sent to the browser. The temporary PBF was removed after successful extraction to reclaim 2.19 GB locally; redownload the pinned URL to rebuild it. Derived graph: **3,730,289 bytes**, SHA-256 `ea5698742e8c5e164f52d5d7b7ad1f0b3ed08fc3d05d1f6abbd29550fb1c1ccc`, 96,049 compact ways, zero missing native nodes.

Paths are plausible alignments, not proof of the exact platform, individual running track, operational direction or historic diversion. Unsupported legs stay gaps. Geometry carries © OpenStreetMap contributors / ODbL 1.0 attribution; retain the derived graph/source pins for reproducibility.

## Bundle and verification

The intercity bundle contains **11,003 departures**, **4,168 shared patterns** and **1,002 source station/platform records**, in **1,980,607 bytes gzip**. Daily departures Monday–Sunday: **1,689 / 1,693 / 1,694 / 1,694 / 1,692 / 1,464 / 1,077**. No selected trips were omitted as malformed. Whole source journeys and retail service identifiers are retained.

Track coverage is **97,074 / 97,267 scheduled legs (99.80%)**. The remaining **193 leg occurrences** are CrossCountry variations around Birmingham–Derby/Burton; they remain hidden gaps. Other included source operators have matched paths on every scheduled leg in this week. Coverage measures connected alignments, not proof of the exact running track or historical diversion. No effort was spent reconstructing the remaining individual variants.

The initial intercity build passed **97 shared timetable/encoding tests and 25 JavaScript overview/playback tests**. The expanded implementation passes **13 GB tests**, plus the selected-day HTTP and Germany rail regression checks needed for the reused optional-layer loader. Chrome checks cover the country switch, GWR/EMR/LNER route filters, a selected train, Overview, dates, 2,000× playback, themes and fullscreen.

### Optional regional storage and coverage

Regional Monday–Sunday departures: **16,190 / 16,241 / 16,205 / 16,218 / 16,252 / 14,907 / 9,022**, **105,035** in total. Combined with intercity, the week contains **116,038** departures; Monday has **17,879** when both layers are selected. Every one of the 13 requested regional operator groups has active services. No selected regional trips were omitted as malformed.

The seven regional files total **28,834,479 bytes gzip**, with individual days **2.57–4.55 MB**. That is repository storage: an intercity-only request never opens them, and a regional request opens one selected date, never the whole week. Regional-only selection also skips the intercity file. Preparation reuses the existing **3.73 MB** nationwide graph; no second geometry source or London timetable/geometry bundle was added. Shared patterns and stop sequences remain unexpanded in the browser.

Regional paths cover **1,224,666 / 1,228,252 scheduled legs (99.71%)**. Remaining gaps concentrate on Glasgow Central low-level approaches and Shotton, with a small number of West Midlands variants. These remain gaps; no special-case reconstruction was attempted. All other selected operators have complete scheduled-leg matches in this week. Railway-path coverage is not a guarantee of the exact historic track.

The optional daily layers use their own pattern/topology namespaces and preserve source retail service IDs. Regression checks verify that combined counts equal the sum of the two layers, shared indices remain valid, defaults ignore unselected regional files, regional-only loads open neither the intercity nor London files, and occurrence IDs do not overlap the existing London replay.

### Shared London rail in the Britain view

London and Britain currently use the same **5–11 October 2026** week and timezone, so source dates and times match exactly. London rail adds **13,422** services on Monday; selecting intercity, regional and all London rail modes gives **31,301** services. Original London modes, operators, line colours, directions and geometry are retained. Intercity-only loads still open no London file, and London-only selection opens no intercity/regional file. Selecting multiple London modes parses its one existing reference once. Revision keys include the London file only when a London mode is selected.

Combined views retain the required **Powered by TfL Open Data**, OS/Geomni and National Rail acknowledgements and geometry credits. Existing London assets are unchanged; no new replay or geometry files are generated for this option. The ordinary prepared HTTP cache can hold a chosen combined view, as with other transport selections; it does not create a second committed London dataset.

Regression checks cover one-time file loading, combined counts and unique occurrence identities, shared station/topology indices, attribution and cache invalidation. Browser checks cover all rail layers together, London-only filtering, the Elizabeth line, Overview and returning to the small intercity selection. If future city periods differ, weekday matching is an accepted product direction; retain/display the actual London source date when implementing that extension. No weekday substitution is needed for this matching week.

## Reproduction

Preparation-only pyosmium is already used by the other national rail imports; no new runtime dependency or live API is introduced.

```bash
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_great_britain_geometry.py .cache/great-britain/great-britain.osm.pbf
./.venv/bin/python scripts/prepare_great_britain_replay.py
./.venv/bin/python scripts/prepare_great_britain_replay.py --regional
```

The runtime reuses the existing city selector, route/operator filters, city Overview, shared timetable encoding, prepared selected-day HTTP cache, playback, themes and fullscreen. Never expand the whole week into individual stop arrays in the browser.

## Next additions

1. **Remaining operators/local services:** the requested regional/commuter operators are now implemented. GWR/EMR local services, Gatwick Express, Heathrow Express and Island Line remain outside this selection; validate their scope and geometry if requested next. Keep `=LO` and `=XR` excluded from new Britain files and reuse the shared London reference in both views. Preserve explicit route-to-agency mapping: `LN`/`WM` share `=LM`, `SX` uses `=LE`, and Merseyrail has `ME_Northern`/`ME_Wirral` under `=ME`.
2. **Caledonian Sleeper:** verify split/join associations and portion journeys before adding it. GTFS may represent portions separately; don't deduplicate distinct portions based only on coincident times or locations. Night Riviera is already in selected GWR mainline scope where active.
3. **Longer timeframe:** select authentic dated releases, check declared feed windows AND per-trip calendars, preserve exception removals and business-day ownership, and inspect bank-holiday modelling limitations documented by the converter. Do not extend by altering date constants alone.
4. **Passenger data:** [ORR station usage](https://dataportal.orr.gov.uk/statistics/usage/estimates-of-station-usage/) describes annual entries/exits/interchanges. It cannot supply hourly demand or observed individual train loads; passenger controls remain disabled.
5. **Northern Ireland:** separate Translink/Northern Ireland Railways data; [NI open data](https://www.opendatani.gov.uk/) is a future source to validate. Not part of this GB selection.
6. **Urban networks:** Glasgow Subway, Tyne & Wear Metro, Manchester Metrolink and Edinburgh Trams need separate dated schedules and geometry audits. London already exists; do not rebuild it. Buses remain out of scope.
