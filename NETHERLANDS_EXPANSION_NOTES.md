# Netherlands expansion

## Implemented scope

One nationwide location, `netherlands`, covering **1–7 June 2026** in `Europe/Amsterdam`. Domestic NS Intercity/Sprinter, regional passenger trains, **Amsterdam Metro 50–54**, **Rotterdam Metro A–E**, trams/light rail in **Amsterdam, Rotterdam, The Hague and Utrecht**, and **GVB ferries** reuse the existing prepared-city loader, compact shared schedules, map, filters, themes, fullscreen and city-aware Overview. Trains and metros open together; **Trams / light rail** and **Ferries** are optional Transport selections. Operator and route controls isolate each network. Passenger sizing and heatmaps are unavailable.

The pinned feed's eight domestic rail agencies are NS, Arriva, Blauwnet Arriva, Blauwnet Keolis, R-net NS, R-net Qbuzz, RRReis Arriva and RRReis Keolis. Route type **2** is required for these agencies. Metros require route type **1**, exact agency/name **GVB** or **RET**, and one of their five audited route codes. Trams require route type **0**, exact agency/name GVB, RET, HTM or `UOV` / **U-OV**, and an audited tram route code. Ferries require type **4**, exact agency/name **GVB**, and one of the ten audited F-codes below. The four NS type-1 entries are excluded. Replacement buses, other buses and international operators are excluded. Arriva's two RE18 routes (`124366`, `124367`) extend into Belgium/Germany and are excluded as complete routes; their journeys are never truncated or relabelled domestic.

## Verified source

- [OVapi nationwide historical archive](https://gtfs.ovapi.nl/nl/archive/).
- Actual ZIP: `https://gtfs.ovapi.nl/nl/archive/NL-20260529.gtfs.zip`.
- Snapshot modified **29 May 2026, 17:04:59 UTC**; downloaded and inspected **18 October 2026**.
- Size: **219,126,362 bytes**. SHA-256: `7b5cb589fb42965b768e6e73c2fedb8639cb417426e5b015f2d2b21d28e6254e`.
- `feed_info.txt`: OVapi, version **9375**, declared validity **29 May–12 December 2026**. Each trip's actual dates come from `calendar_dates.txt`; broad feed validity alone is not a service guarantee.
- A single pre-period snapshot supplies this pilot. Every selected operator and all ten metro lines have active services throughout the week and adjoining dates needed for overnight departures. Tram codes vary by date: weekday, event and date-specific calendars are preserved rather than enabling every route on every day. This is a timetable snapshot applied to its valid dates, not a reconstruction of later timetable revisions, cancellations or every historical disruption.
- No `frequencies.txt` is present. Train trips and Amsterdam metros have usable native shapes. Some RET trips omit shapes; the populated RET shapes are stop-only sketches and are not used for movement. RET schedules instead use the separate railway geometry described below.

The raw national ZIP is preparation-only. It includes other modes and foreign services; it is never sent to the browser. The bundled reference is `data/reference/netherlands/2026-06-01.json.gz`. The server and browser retain the existing one-day, selected-mode behaviour and shared stop/timing representation.

Daily train departures are **5,960 / 5,977 / 5,985 / 5,973 / 5,737 / 5,249 / 4,652**, plus **2,347 / 2,347 / 2,347 / 2,347 / 2,372 / 2,020 / 1,782 metros**, from Monday through Sunday. All ten metro lines operate on every selected date. No selected timetable trips are omitted, and every occurrence belongs to one 03:00–03:00 start-day window. Trains retain their original occurrences, stop orders, scheduled times, colours and geometry.

The replay week including all four modes is **2,206,821 bytes gzip**, with **9,263 shared timetable patterns**. The separate offline RET metro geometry database is **147,113 bytes gzip**. All **257,698 scheduled metro legs** across the week have matched geometry, including the outer branches toward The Hague and Hoek van Holland. This is geographic matching, not an assertion of actual historical train movements.

Measured Monday HTTP downloads: **681,553 bytes gzip** for the opening selection of 8,307 trains and metros; **41,519 bytes** for 1,886 ferries alone, using just **20 shared timetable patterns**. The tram-only download remains about **470 KB**. No mode expands stop arrays per service. Payload measurements are local, not hosted latency benchmarks.

## Geometry and display colours

The original train audit selected **326 shapes with 115,180 points**. Native distance anchors are tried first for NS/regional trains and Amsterdam metros. A sizeable subset contains inaccurate distance anchors, so this source explicitly opts into `native_or_ordered_per_leg`: match the complete stop order against the **same published shape** within the existing **150 m** limit. If that fails, retain only native legs whose two endpoints meet the limit and leave the others as gaps. This does not widen tolerances or invent station connectors. Other cities keep their existing geometry method.

**Rotterdam geometry:** RET's supplied sketches contain only station points, inconsistent point order and missing terminal sections. They are never animated. A pinned [BBBike Rotterdam OSM extract](https://download.bbbike.org/osm/bbbike/Rotterdam/Rotterdam.osm.pbf), modified **17 October 2026**, supplies operating subway/railway ways from RET's A–E route relations. Raw PBF: **88,548,969 bytes**, SHA-256 `964daa57328d7abfd43791da46073759a849915a24b8664597f9cb4a4171cba5`. Four [official OSM API](https://api.openstreetmap.org/api/0.6/) relation downloads (`2777286`, `2777287`, `2785674`, `2785675`) fill the clipped outer B/E route members; accessed **18 October 2026**, with URLs and individual hashes embedded in the geometry bundle metadata.

The geometry bundle is `data/reference/netherlands/ret-osm-2026-10-17.json.gz`, SHA-256 `b5ebe6463a3b15f16923126b548afd5fa2b423e48895fdad8bc43aa73f1b587a`. It reuses Singapore's connected-run extraction and ordered matcher. London’s existing railway graph handles variants within the shared **A/B/C** or **D/E** physical corridors, joining only identical OSM node IDs. This also covers June A services continuing beyond Schiedam along the shared A/B track, even though the October A relations stop at Schiedam. The 150 m checks remain in force; disconnected sections stay gaps. No general road routing or straight connectors are used.

These are **October geographic references for June schedules**, not a historical track-use reconstruction. Source shapes and mapped railway ways do not identify individual running tracks. Some native train sections are sparsely sampled. No ProRail database was substituted.

Across the week's train occurrences, **336,403 of 340,377 legs (98.8%)** have usable source geometry; **3,974 train legs** remain gaps, across **430 shared timetable patterns**. On Monday, 394 of 5,960 train trips have a gap somewhere; only two have no usable moving section. Across the week, 56 train occurrences have no usable moving section and appear only at their scheduled stops.

Rail `route_color` values are blank in this snapshot. SunTrain therefore uses an explicit display palette, grouped by operator family: NS `#003082`, Arriva `#008C95`, Blauwnet `#006BB6`, R-net `#C8102E`, RRReis `#71368A`. These are display choices, not a claim of official line colours. A populated source colour takes priority. Preserve route IDs and complete route/series labels so separate regional services and branches do not collapse under labels such as “Intercity”. Journey identifiers remain the GTFS trip IDs.

Metro colours come directly from this snapshot: Amsterdam 50 `#187a36`, 51 `#FF6600`, 52 `#00adef`, 53 `#d81118`, 54 `#fff200`; Rotterdam A `#00b43f`, B `#ffdd00`, C `#e32119`, D `#34b4e4`, E `#003a8c`. Labels such as “Amsterdam Metro 50” and “Rotterdam Metro A” identify the city and line; the underlying GTFS route IDs remain intact. Do not apply later GVB line renumbering to this 2026 week.

## Usage and attribution

The [OVapi README](https://gtfs.ovapi.nl/README) permits use of these feeds, describes their conversion from agencies' open NDOV data, provides the service on a best-effort basis and prohibits impersonating the agencies. Keep operator/OVapi/NDOV attribution, link these actual conditions and retain SunTrain's independence/estimated-position text. Do not relabel the source as CC BY, OGL or another licence it does not name. No official logos or map artwork are included.

Preparation identifies SunTrain through its User-Agent, requests gzip transport encoding, reuses its cached ZIP and verifies the archive hash. Runtime schedule loading requires no external API account or live tracking service.

The separate RET geometry database and its derived railway paths use [OpenStreetMap's ODbL 1.0 licence](https://www.openstreetmap.org/copyright). The app displays the contributor credit and ODbL link, and the bundled geometry includes its source/redistribution metadata. Preserve these with future derivatives; the timetable's OVapi usage-conditions link remains separate.

## Validation

Validation completed **19 October 2026**: **141 focused Python tests** (44 app/rail-preparation/London regression checks and 97 Netherlands/HTTP/shared-schedule checks) and **35 JavaScript tests** passed. Netherlands checks cover all four mode scopes, colour handling, all seven calendars, geometry and source pins, unique start-day assignment, shared schedules, pier tagging, local time, mode-specific downloads and independence from the Melbourne passenger warehouse. Original train, metro and tram occurrences, schedules, colours and paths were compared against the previous reference and are unchanged.

Local Chrome checks covered the lighter opening selection, optional tram downloads preserving the clock, all four tram operators, city-specific route legends, source/display colours, route details/follow, 2,000× playback, filtered Overview without another download, event-date and Sunday calendars, fullscreen, theme switching, a 390 px viewport and returning to the original modes. Maps were visually inspected. No hosted performance benchmark was run for this addition.

Ferry browser checks passed for optional loading, ten routes, pier labels/status, colour, F3/F4/F22 movement and follow, 2,000× playback, Ferry-labelled Overview without another download, Sunday F9 exclusion, fullscreen, theme switching, a 390 px viewport and returning to the original modes, with no page errors. Representative IJ water paths were visually inspected; no fine-grained historical vessel tracking is implied.

## Rebuild and future expansion

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/prepare_netherlands_replay.py
```

Use `--cache` and `--output` to override paths, and `SUNTRAIN_NETHERLANDS_REFERENCE` to override the runtime bundle. The default cache is `.cache/netherlands/`. Preparing the full national archive can take several minutes; source ZIP scanning happens offline, never during a visitor's replay download.

The regular replay rebuild uses the already bundled, hash-checked RET geometry (`--geometry` overrides the path). To rebuild the geometry itself, install Pyosmium only in an offline tools environment and run:

```bash
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_netherlands_geometry.py \
  .cache/netherlands/Rotterdam.osm.pbf \
  --supplement .cache/netherlands/ret-relation-2777286.json \
  .cache/netherlands/ret-relation-2777287.json \
  .cache/netherlands/ret-relation-2785674.json \
  .cache/netherlands/ret-relation-2785675.json
```

Retrieve the dated PBF and API supplements using the embedded metadata URLs/hashes; current downloads may differ. Audit replacements before updating either pin. Pyosmium is not a runtime dependency.

For a longer period, first audit dated archives, per-trip calendars and the selected operators across every proposed day. Preserve source capture/validity/hash metadata, check whether additional snapshots are required and retain one 03:00–03:00 start-day assignment per occurrence. Re-audit explicit route/operator scope whenever changing the source pin, particularly international and replacement services. Do not merely extend the date picker or use a current feed for past dates.

Amsterdam GVB and Rotterdam RET metros, the four tram networks and GVB ferries are implemented. Buses are a future addition; keep them optional and measure browser volume before expansion. Restrict every mode by audited agency and route scope, rather than enabling all route types indiscriminately.

## Trams and light rail

Use the existing `tram` mode for GVB Amsterdam trams, RET Rotterdam trams, HTM The Hague trams/RandstadRail and U-OV Utrecht light rail 20/21/22. Route labels include the city, so Amsterdam Tram 1 and Rotterdam Tram 1 remain distinct. GTFS route IDs and source calendars are retained, including temporary routes and event services where scheduled. Utrecht 22 is present on 1 June but not every weekday of this particular week; do not replace these calendars with a generic weekday template.

There are **43 active city/route-code combinations** across the week: GVB 16, RET 10, HTM 14 and U-OV 3. Daily tram departures are **8,041 / 7,818 / 7,942 / 7,801 / 7,801 / 6,519 / 5,640**. No tram trips are omitted. **1,103,333 of 1,103,727 scheduled legs (99.96%)** have usable geometry. The remaining **394 legs** are one unresolved section on RET route 24, affecting 58 journeys per weekday, 54 on Saturday and 50 on Sunday. Their other sections remain visible; no tram journey is hidden for its entire length. Do not invent a connector or widen tolerances to fill this small gap.

Amsterdam, The Hague and Utrecht use their native GTFS railway shapes. Rotterdam uses the separate `ret-tram-osm-2026-10-17.json.gz` database, **152,296 bytes gzip**, SHA-256 `fb26e181cb992322accbf6205c4709630a8d3422fc5ceb094d3be0af622f1dff`, extracted from the same pinned Rotterdam PBF. It contains only operating **tram** ways from RET tram relations, sharing no subway/road graph. Ordered route matching and the existing graph matcher retain real OSM node connections; the shared RET tram graph can cover temporary scheduled route variations such as 24. Remaining disconnected sections stay gaps.

Rebuild that geometry with the existing geometry command plus `--mode tram`; the default output is the separate tram database. The normal timetable rebuild verifies both geometry hashes; `--tram-geometry` overrides the tram path. Both source metadata records are embedded under `geometry_references`.

HTM and U-OV retain supplied route colours. Where tram colours are blank, SunTrain uses explicit display colours: GVB **#008ACD**, RET **#008C5A**, and HTM's uncoloured route 10 **#6F818E**. These fallback colours are not claimed as official individual line colours. They do not use Melbourne's tram palette. Trams remain optional so the opening selection still downloads trains and metros only.

## GVB ferries

Implemented as optional mode **Ferries**, using GVB routes **F1, F2, F3, F4, F6, F7, F9, F20, F21 and F22** across the IJ and North Sea Canal. All ten operate somewhere in the selected week; F9 has weekday service only. Schedules come from the same pinned archive, without frequency templates or a new API account.

Daily departures in the 03:00–03:00 business windows are **1,886 / 1,886 / 1,886 / 1,936 / 1,967 / 1,694 / 1,639**, Monday through Sunday. All **12,894 ferry occurrences** have native water geometry, with no omitted ferry trips or unresolved legs. Overnight start-day assignment explains small differences from midnight-to-midnight calendar totals.

Native water shapes have **4–22 points**, match the ordered pier endpoints within the existing 150 m check, and have scheduled crossing durations of roughly **5–14 minutes**. Ferry piers are tagged separately from railway stations and remain visible through the existing station/stop display control. Details use pier labels and movement reports “At pier” / “Between piers”. Source ferry colours are blank, so **#0077B6** is an explicit SunTrain display choice rather than an official route colour.

Crossings reuse shared schedules, route filters, playback and Overview; they belong to one 03:00–03:00 start-day window, with no duplicate overnight occurrence. These are scheduled crossings, not identified physical vessels or precise recorded sailing trajectories. Keep the existing OVapi source conditions and attribution. For extensions, recheck calendars and water paths; do not substitute the later September 2026 timetable expansion for these June dates.

The linked [NS occupancy listing](https://data.ndovloket.nl/bezetting/ns/) exposes recent October files; availability and journey-ID matching for June 2026 have not been established. Predicted occupancy categories must remain labelled forecasts and must not become fabricated passenger counts. [NS station ridership](https://nieuws.ns.nl/flink-meer-reizigers-op-stations-door-nieuwe-dienstregeling-en-woningbouw-in-de-buurt/) describes average station use for 2025, not these trains' individual loads or a June 2026 daily passenger heatmap. Passenger features remain optional future work.
