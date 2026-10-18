# SunTrain

Historical transport replay across Australia, Canada, the Netherlands, the United Kingdom, the United States and Singapore, with passenger analysis for the Victorian train service passenger counts dataset.

## Netherlands replay

Choose **Netherlands** under **Location** for **1–7 June 2026**. This nationwide pilot includes domestic NS Intercity/Sprinter and regional trains from Arriva, Blauwnet, R-net and RRReis, plus **Amsterdam Metro 50–54**, **Rotterdam Metro A–E**, trams/light rail in **Amsterdam (GVB), Rotterdam (RET), The Hague (HTM) and Utrecht (U-OV)**, and **ten GVB ferry routes across the IJ and North Sea Canal**. Trains and metros open together; select **Trams / light rail** or **Ferries** under **Transport** to include those networks. Operator/route/stop filters, local time, themes, fullscreen and Overview reuse the existing interface. International services, buses and passenger counts are excluded.

The source is the [29 May 2026 OVapi historical archive](https://gtfs.ovapi.nl/nl/archive/NL-20260529.gtfs.zip), verified against its service calendars and pinned hash. Its shapes supply train, Amsterdam Metro, non-RET tram and ferry water geometry. Rotterdam metros/trams use connected OpenStreetMap railway paths, using an October 2026 geographic reference with contributor/ODbL attribution. Matching stays within 150 m; unresolved sections remain gaps. Source colours are retained where supplied; blank train, tram and ferry colours use documented display palettes. These are scheduled estimates, not recordings of actual movements or every disruption.

The 219 MB national source ZIP is preparation-only; the prepared seven-day reference for all four modes is **2.21 MB compressed**. Monday's opening train/metro download is **681 KB**, with **470 KB** for trams alone or **42 KB** for ferries alone when selected. All ferry and metro legs and **99.96%** of tram legs have matched route geometry; about **98.8%** of train legs have usable geometry. Unresolved sections stay hidden between stops. Rebuild with `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/prepare_netherlands_replay.py`. See [Netherlands expansion notes](NETHERLANDS_EXPANSION_NOTES.md) for provenance, usage conditions, geometry limits and future expansion instructions.

## Loading and performance

Every city uses compressed, versioned replay downloads for the selected date and transport modes. Melbourne opens with trains; select Trams or Buses under **Transport** to load them, or clear Transport for all modes. Boston opens with rail and Silver Line; regular buses are optional. London, Chicago and Perth open with rail; buses are optional. Other cities retain their available-mode defaults. Mode changes preserve the replay clock and complete journeys.

Overview follows the selected city, date and transport filters, reusing the loaded replay day. Its schedule totals, local-hour chart and paginated route table use shared schedules without expanding every trip. Melbourne passenger reports, Plotly and the raw-data table mount only when the optional analysis section opens. Replay playback tracks active services rather than scanning the whole day each frame; passenger heatmap indexes are built on demand. Switching cities releases previous replay indexes and map features.

The browser's Dash store holds only a small download descriptor. `/api/replay/<city>/<date>/<revision>.json?modes=...` serves gzip JSON with ETags and immutable versioned caching. The server keeps at most **256 MiB** of generated compressed responses under ignored `.cache/replay-http/`; override its directory with `SUNTRAIN_REPLAY_CACHE`. It is disposable and can be regenerated from the committed references and configured warehouse. Warm requests reuse the serialized response; no Redis or new hosted service is required. Changes to source file fingerprints or transport modes produce a new URL. Bump `FORMAT_VERSION` in `dashboard/replay_http.py` when changing the delivered format or preparation logic.

Initial loading improvements measured in local headless Chrome on 18 October 2026: the opening Melbourne replay download fell from **39.90 MB to 0.73 MB**, with **zero hidden charts instead of 13**. A cold generated response reached a usable map in **3.54 seconds**, versus the earlier **8.56 seconds**; cached-response fresh-page checks were about **2.9–3.0 seconds**. The lighter default also reduced the initial JS heap from approximately **137 MB to 35–38 MB**. These are local software-rendered browser measurements, not hosted-site or physical-phone guarantees. Full London buses remain a substantial optional layer; its first uncached load measured about **10.8 seconds**, versus about **2.4 seconds** with the generated response cached.

Browser checks cover all 13 cities, 2,000× playback, mode changes preserving time, full London buses, Melbourne heatmaps, Overview subtabs and both themes. With an uncached browser, a phone viewport, 4× CPU throttling and a 5 Mbit/s connection with 80 ms latency, the opening map reached usable state in **5.51 seconds** using the server's generated response cache. After loading London buses and repeatedly switching to Boston/Toronto, garbage-collected Toronto JS heap settled at **17–22 MB**; superseded bus downloads cancelled without overwriting the selected city.

The subsequent shared-schedule update keeps all existing date coverage. Every prepared city and Melbourne tram/bus snapshot stores stop order and geometry once per shared sequence, with flat relative times. On the server those timing vectors use read-only numeric buffers; they are delivered as ordinary JSON arrays. All preparation commands use the shared writer so rebuilding does not restore repeated stop arrays.

Only one uncached replay is generated at a time per worker. Cached downloads remain available while another day is prepared. JSON is compressed in bounded chunks, and parsed references/day objects are released after each build, including failed builds. Bus-only Boston/London downloads skip unselected rail references. The compressed disk cache remains the reusable cache; large parsed Python schedules do not stay resident across city switches.

Local HTTP measurements for the same dates/modes: Melbourne all transport fell from about **12.5 MB to 4.0 MB**, NYC from **2.1 MB to 0.54 MB**, London rail from **2.65 MB to 0.83 MB**, and London buses from **19.5 MB to 13.6 MB**. Melbourne's combined day measured about **421 MiB peak process memory**, returning to about **185 MiB** after the response was built. These are local measurements, not a promise that every network fits a 512 MB hosted instance. See [replay performance notes](PERFORMANCE_NOTES.md) for preservation checks, concurrency behaviour and hosting limits.

Melbourne’s full FY2023–24 train warehouse is only **43.2 MB** compressed (15.6 million stop rows). Keep the full year: the browser downloads one selected day. The current 126 Parquet row groups mix dates across the year, limiting date pruning; a future performance change should benchmark sorting by `Business_Date` or date/month partitioning rather than deleting history. [DuckDB documents Parquet filter pushdown and partition pruning](https://duckdb.org/docs/current/guides/performance/file_formats#hive-partitioning-for-filter-pushdown). No warehouse data is removed by the city expansion.

## London rail

Choose **London** in **Location** for **5–11 October 2026**: all **11 Underground lines**, **DLR**, **London Trams**, all **six Overground lines** (Liberty, Lioness, Mildmay, Suffragette, Weaver and Windrush), and the **Elizabeth line**, including Reading, Heathrow, Abbey Wood and Shenfield branches. London local time, route colours and the existing replay controls apply throughout. A validated public dated conversion supplies TfL and National Rail schedules; connected OpenStreetMap railway paths supply movement geometry. Unresolved legs remain gaps. This is a schedule replay, not live tracking or a reconstruction of every disruption.

Use **Operator / feed** under **More filters** to select Overground or Elizabeth line, or **Route / line** to select a named route. Their source does not specify journey directions, so these services use **Not specified**; origin and destination remain visible. London passenger sizing and heatmaps remain unavailable: the verified NUMBAT workbooks describe modelled typical autumn 2025 demand, rather than individual train loads in this 2026 week. Overview shows the selected city’s schedules; detailed passenger reports remain available for Melbourne only. See [London expansion notes](LONDON_EXPANSION_NOTES.md) for sources, licensing, gaps, passenger findings and future expansion instructions.

**London buses:** select **Buses** under **Transport** to load the prepared bus schedules for the same week. Rail is selected initially. Clear Transport to show every available mode, or select only Buses for a bus map. London bus markers are red (#DC241F); line, operator, direction, stop and trip filters apply to complete journeys. Positions follow detailed official TfL road geometry, with unresolved legs hidden. Non-exact frequency templates are not turned into invented departures, and unavailable routes 246 and 653 are not reconstructed. Loading or removing buses preserves the replay clock. Buses have no passenger loads or heatmap data.

Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019]. National Rail timetables: Rail Delivery Group / Rail Settlement Plan; station names and coordinates: DfT NaPTAN (OGL v3.0). Timetables converted by Planar Network; railway geometry © OpenStreetMap contributors, ODbL 1.0. [Source terms](https://planarnetwork.github.io/gb-transit/feeds/using-this-data/#sources-and-licences), [TfL licence](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service), [OSM attribution](https://www.openstreetmap.org/copyright).

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_replay.py
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_buses.py
```

## Toronto rapid transit and streetcars

Choose **Toronto** in **Location** for **5–11 October 2026**: TTC subway Lines **1 Yonge-University**, **2 Bloor-Danforth** and **4 Sheppard**, plus light rail Lines **5 Eglinton** and **6 Finch West**. The existing controls, route colours, Toronto local clock, filters, themes and fullscreen work for all five lines. Daytime streetcars and all six scheduled night routes (301, 304, 305, 306, 310 and 312) are also included under **Streetcars / night routes**. Day routes use feed red and night routes blue. Buses, GO Transit and UP Express are not included. Passenger sizing and heatmaps remain unavailable. Overview shows Toronto’s schedules; detailed passenger reports remain available for Melbourne only.

The official [Merged GTFS – TTC Routes and Schedules](https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/) downloaded successfully, with timetable validity **30 September–31 October 2026**. The selected week falls entirely within those calendars. These are regular schedule estimates, not observed GPS or a reconstruction of every closure. Shapes and stop sequences come from the same feed. Two Line 1 journey variants have inconsistent source geometry; those vehicles appear at stations, with gaps between stops rather than invented paths. See [Toronto expansion notes](TORONTO_EXPANSION_NOTES.md) for the exact source, known gaps and future extensions.

Rebuild with:

```bash
./.venv/bin/python scripts/prepare_toronto_replay.py
```

The source ZIP is cached as `.cache/toronto-audit/completegtfs.zip`; its SHA-256 is checked before preparation. The official URL is updated in place, so retain that validated ZIP for future rebuilds. A changed download is rejected instead of silently replacing historical services. The compact prepared reference is about **0.58 MB**, with shared schedules, and needs no schedule API or credentials at replay time. `SUNTRAIN_TORONTO_REFERENCE` overrides the prepared file.

Contains information licensed under the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/). Timetable and railway geometry: TTC / City of Toronto. SunTrain is independent of TTC and uses no official logos or map artwork.

## Washington, DC and SF Bay Area

Both additions reuse the existing replay controls, line/direction/station filters, local clocks, route colours, themes and fullscreen. Passenger sizing and heatmaps remain unavailable.

| Replay city | Historical week | Railway coverage |
| --- | --- | --- |
| Washington, DC | 5–11 October 2026 | WMATA Red, Blue, Orange, Silver, Green and Yellow lines |
| SF Bay Area | 17–23 August 2026 | BART Yellow, Orange, Green, Red and Blue lines, plus the Oakland Airport connector |

DC uses two dated [MobilityDatabase copies of WMATA's rail feed](https://mobilitydatabase.org/feeds/gtfs/mdb-1847), each applied only to service dates inside its declared validity. BART uses its [official dated August schedule ZIP](https://www.bart.gov/sites/default/files/2026-08/google_transit_20260810-20270108_v02.zip). BART's calendars and feed metadata disagree about the overall validity; this August week is inside both. Later dates are not enabled just because they appear in its calendars. These are schedule estimates, not observed movements or every disruption. No rail replacement buses, Metrobus, MARC, VRE, Muni or Caltrain services are included.

Rebuild with:

```bash
./.venv/bin/python scripts/prepare_us_rail_replay.py dc
./.venv/bin/python scripts/prepare_us_rail_replay.py sf_bay
```

Sources are SHA-256 pinned and cached under `.cache/us-rail/`. Compact references are about **0.11 MB for DC** and **0.08 MB for BART**, with shared schedules and paths. One rare journey variant in each city has unresolved source geometry; affected vehicles appear at stations only. `SUNTRAIN_DC_REFERENCE` and `SUNTRAIN_SF_BAY_REFERENCE` support alternate prepared files.

Source attribution and links to the [WMATA Transit Data Terms of Use](https://developer.wmata.com/license) and [BART Developer License Agreement](https://www.bart.gov/schedules/developers/developer-license-agreement) appear beside the map. SunTrain is independent of the operators and uses no official logos or map artwork. See [DC and Bay Area expansion notes](DC_BAY_AREA_EXPANSION_NOTES.md) for snapshots, geometry checks, known gaps and future extensions.

## Additional Australian cities

Choose the city in **Location**. These railway additions reuse route/operator/direction/station filters, scheduled movement, route colours, local clocks, fullscreen, themes and all playback speeds.

| City | Supported historical period | Railway coverage |
| --- | --- | --- |
| Sydney | 5–11 October 2026 | Sydney Trains T1–T9, Metro M1, TrainLink intercity BMT/CCN/SCO and light rail L1–L4 |
| Adelaide | 27 May–30 June 2024 | Suburban rail and Torrens Connect trams; Port Dock had not opened |
| Perth | 5–11 October 2026 | Eight suburban lines and stadium specials when scheduled, plus optional Transperth buses and CAT; Transwa/regional operators excluded |
| Brisbane | 5–11 October 2026 | Queensland Rail across SEQ and G:link Gold Coast light rail |

Adelaide uses official historical **version 1430**, covering the preferred five weeks. The other additions use publicly downloadable, pinned archives for a complete October 2026 week; a suitable 2024 ZIP was not obtained. Network changes are represented by each archive's actual calendars and stop sequences. This is a schedule replay, not observed GPS or a reconstruction of every disruption. Shapes come from the same archived timetable as the services. Passenger data was investigated, but no individual-train loads are supplied, so passenger sizing and heatmaps stay unavailable for these cities. Sydney/Adelaide/Gold Coast light rail is enabled with separate Transport filters and historical route colours. Sydney regional TrainLink, Newcastle light rail, Australian city buses outside Melbourne/Perth and ferries remain future additions documented in the notes.

Rebuild the compact references with:

```bash
./.venv/bin/python scripts/prepare_australian_replay.py sydney
./.venv/bin/python scripts/prepare_australian_replay.py adelaide
./.venv/bin/python scripts/prepare_australian_replay.py perth
./.venv/bin/python scripts/prepare_australian_replay.py brisbane
```

Preparation downloads the pinned archives to `.cache/australian-cities/<city>/`, verifies their SHA-256, and writes compact references under `data/reference/<city>/`. Native distance anchors preserve branches and loops where supplied; ordered whole-journey projection is used when the feed omits distances. Station matches must be within 150 m; unresolved paths remain gaps. Services retain shared relative stop schedules and only the selected date is loaded. `SUNTRAIN_<CITY>_REFERENCE` overrides each prepared file.

Source acknowledgements appear alongside each map. Sydney uses the [TfNSW Creative Commons Attribution data](https://opendata.transport.nsw.gov.au/dataset/timetables-complete-gtfs); Adelaide and Brisbane use CC BY 4.0 with government attribution. Perth uses the [PTA Spatial Data Licence](https://www.transperth.wa.gov.au/About/Spatial-Data-Access): **source data is available free of charge from www.transperth.wa.gov.au**. SunTrain is independent of the data providers and uses no official logos or map artwork. See [Australian expansion notes](AUSTRALIAN_EXPANSION_NOTES.md) for validated sources, network changes, licensing and future passenger/mode opportunities.

## NYC Subway and Staten Island Railway

Choose **New York City** in **Location** for **15 December 2025–18 January 2026**, five full weeks of regular MTA subway schedules. All 28 subway route IDs represented in the archive are retained, including 6X, 7X, FX, weekday services, branches and the separate 42 St, Franklin Avenue and Rockaway Park shuttles. Staten Island Railway (`SI`) is also included, with its own Transport filter, source blue (`#08179C`) and a view extending to Staten Island. Only services active on the selected date appear. LIRR, Metro-North and buses are excluded. The existing controls, route colours, local New York clock, filters, fullscreen and themes are reused.

The requested May–June 2024 historical ZIP required archive credentials. The supplied MyTransit archive is publicly accessible but its GTFS folders stop at 2016. This permitted fallback uses the [historical MTA regular feed captured on 5 December 2025](https://files.mobilitydatabase.org/mdb-516/mdb-516-202512050000/mdb-516-202512050000.zip), valid from 8 December. The chosen period includes the adjoining service dates needed for overnight carry-ins. A November alternative was rejected because 2,274 subway trips had blank shape IDs. The bundled fallback has no omitted invalid trips or unresolved geometry patterns.

Positions follow each trip's published shape and stop sequence. Express/local stopping patterns are preserved, but the feed does not prove which individual running track was used. [MTA distinguishes regular schedules from supplemented schedules](https://www.mta.info/developers); this replay does not reconstruct temporary service changes or actual GPS movements. Data is obtained from historical MTA feed copies, prepared and hosted by SunTrain under the [MTA data terms](https://www.mta.info/developers/terms-and-conditions). SunTrain is independent of MTA and uses no MTA logos, map artwork or route badges.

Rebuild with:

```bash
./.venv/bin/python scripts/prepare_nyc_replay.py
```

The script caches downloads under `.cache/nyc-archives/` and writes `data/reference/nyc/2025-12-15.json.gz` (about 3.67 MB). `SUNTRAIN_NYC_REFERENCE` overrides the file. Schedules, geometry and relative stop times remain shared; only the selected day is sent to the browser. The date badge explicitly includes both years.

Official hourly station-complex ridership and monthly/day-of-week/hour origin–destination estimates were verified as accessible for 2024. They are documented for optional station-level features, and are not mixed with these 2025–2026 schedules or presented as individual train loads. NYC passenger sizing and Melbourne's recorded-train-boarding heatmap stay unavailable. See [NYC data and expansion notes](NYC_EXPANSION_NOTES.md) for sources and the other networks' future integration issues.

## Singapore MRT and LRT

Choose **Singapore** for **5–11 October 2026**: North–South, East–West (including the Changi Airport branch), North East, Circle, Downtown and Thomson–East Coast MRT, plus Bukit Panjang, Sengkang and Punggol LRT. SMRT and SBS Transit schedules use the existing route/mode/operator filters, local Singapore clock, playback speeds, fullscreen and themes. Route colours come from the official feed. Passenger sizing and heatmaps remain unavailable.

The official **LTA DataMall GTFS Schedule (Train)** downloaded on 17 October 2026 contains the schedules but no shapes. Its calendars are applied to this candidate historical week; this snapshot does not reconstruct every past disruption. Railway paths come from **OpenStreetMap contributors via BBBike's Singapore extract**, downloaded the same day. Matching preserves a complete ordered stop sequence on one connected railway run within 150 m, including LRT loops. Unresolved geometry stays empty; one anomalous Sunday North–South trip is retained without interpolated movement.

Rebuild using the cached, pinned timetable and bundled geometry:

```bash
./.venv/bin/python scripts/prepare_singapore_replay.py
```

The compact reference is about 0.9 MB, with shared stop schedules and paths. The app requires no API key or network requests for schedule loading. `SUNTRAIN_SINGAPORE_REFERENCE` overrides the prepared reference. LTA schedule data is available under the [Singapore Open Data Licence v1.0](https://datamall.lta.gov.sg/content/datamall/en/SingaporeOpenDataLicence.html); the OSM-derived geometry database is under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). See [Singapore expansion notes](SINGAPORE_EXPANSION_NOTES.md) for downloads, checks, attribution, passenger-data limits and future extensions.

## Chicago CTA rail

Choose **Chicago** in **Location** for **24 November–28 December 2025**, five full weeks of CTA ‘L’ trains: Red, Blue, Brown, Green, Orange, Pink, Purple and Yellow. Chicago uses `America/Chicago` local time, historical feed colours and the existing route/direction/stop filters, playback controls, fullscreen and themes. CTA buses are available as an optional layer under **Buses**. Rail opens first. Bus route colours come from the same historical feed (grey, dark grey, red and blue), rather than Melbourne orange. Metra and individual vehicle passenger counts are unavailable. Overview shows Chicago’s schedules; detailed passenger reports remain available for Melbourne only.

**Chicago's period differs from Melbourne and Boston.** The requested May–June 2024 Transitland snapshot is listed, but its ZIP download required archive authentication. A publicly downloadable 2024 ZIP was not obtained. The supported 2025 period uses two accessible [MobilityDatabase CTA archives](https://mobilitydatabase.org/feeds/gtfs/mdb-389), captured on 23 November and 19 December 2025 (UTC); each service date selects the latest of these snapshots captured by that date. Calendars and date exceptions determine actual trips, including holidays. Current CTA schedules are never substituted for the labelled historical dates.

Rebuild the compact Chicago reference with:

```bash
./.venv/bin/python scripts/prepare_chicago_replay.py
```

The script downloads the pinned archives into `.cache/chicago-archives/` and writes `data/reference/chicago/2025-11-24.json.gz`. The base reference retains CTA rail; optional daily bus bundles use the same two dated archives. Stop schedules and trip-specific shapes remain shared; the existing prepared-city loader sends one selected day to the browser without querying Melbourne's warehouse. Set `SUNTRAIN_CHICAGO_REFERENCE` to use another prepared reference.

CTA supplies native stop/shape distance anchors, reused by the existing geometry matcher to preserve Loop stop occurrences and branch paths before simplification. Anchors must follow journey order and match stations within 150 m; unresolved paths remain gaps. Data is provided by Chicago Transit Authority under its [Developer License Agreement](https://www.transitchicago.com/downloads/sch_data/developers_license_agreement.htm). SunTrain is independent of CTA. Positions estimate scheduled movement, not GPS, delays or every historical disruption.

See [Chicago data and expansion notes](CHICAGO_EXPANSION_NOTES.md) for the archive limitation, Metra findings, daily station ridership and future bus support.

## Boston replay pilot

Choose **Boston** in the replay's **Location** selector to explore **24–30 June 2024**. Subway (Red, Orange and Blue), light rail (Green B/C/D/E and Mattapan), scheduled MBTA commuter rail and **Silver Line SL1–SL5 plus SLW** use the existing playback controls, route/mode/direction filters, journey details, dark mode and fullscreen. Silver Line has its own transport filter and retains individual route labels, including the SLW short-turn service where scheduled. Boston uses `America/New_York` local time, historical rail colours and a metropolitan Boston starting view. **Silver Line uses silver (`#7C878E`); regular MBTA buses use yellow (`#FFC72C`).** Select **Buses** under Transport to download regular buses, or clear Transport for all modes. Rail and Silver Line open initially. **Fit selection** also shows outlying commuter rail termini. The Overview tab shows Boston’s schedules; detailed passenger reports remain available for Melbourne only.

This is a scheduled-service simulation. It does not reproduce GPS movements, delays or disruptions missing from the archived timetable. Boston has no passenger counts: passenger sizing and heatmap controls are unavailable. Replacement shuttles, ferries and non-MBTA operators (including CapeFLYER) remain excluded. Regular MBTA buses are an optional layer: weekdays have 150 active routes and 10,950 scheduled journeys. Only services active in the historical calendars appear; a listed line without active trips is not fabricated.

Data is provided by **MassDOT / MBTA**, under its [Developer License Agreement](https://github.com/mbta/gtfs-documentation/blob/master/developers-license-agreement.pdf). SunTrain is independent of MassDOT and MBTA. The [official archive index](https://cdn.mbta.com/archive/archived_feeds.txt) selects four feeds for this week and the adjoining calendar dates needed for overnight services: `20240613.zip`, `20240625.zip`, `20240626.zip` and `20240627.zip`. The index's recommended validity windows determine selection, including retrospective corrections; ZIP filename dates are not assumed to be publication dates. Source URLs, versions, validity dates and SHA-256 hashes are retained in the prepared reference.

Rebuild the pilot with:

```bash
./.venv/bin/python scripts/prepare_boston_replay.py
./.venv/bin/python scripts/prepare_boston_replay.py --buses
```

The script caches source downloads in `.cache/boston-archives/` and writes the compressed reference `data/reference/boston/2024-06-24.json.gz`. It applies service calendars and exceptions, trip-level vehicle-type overrides and extended-hour times. Silver Line membership comes from the feed's `line-SLWaterfront` and `line-SLWashington` groups; it remains a bus service with bus stops shown at closer zoom levels. Trips overlapping the 03:00 boundary remain visible on either side, with no duplicate occurrences within a replay day. Stop schedules and route geometry are shared by compact trip instances; only the selected day and its referenced paths are sent to the browser. Boston loading does not query Melbourne's passenger warehouse. `SUNTRAIN_BOSTON_REFERENCE` overrides the rail/Silver reference path. Regular buses have separate daily compact references in `data/reference/boston/bus/` (0.58–1.10 MB each); `SUNTRAIN_BOSTON_BUS_REFERENCE` overrides that directory. Stops and relative schedules stay shared.

MBTA stop times lack distance anchors. Preparation projects the whole ordered stop sequence onto each trip's own shape, preserving branches and repeated stop occurrences. Stop projections must lie within 150 metres of that shape; invalid geometry stays as a gap, with markers hidden between those stops. Supplied shapes are simplified at approximately six metres. The bundled week has no omitted invalid trips or unresolved geometry patterns. These checks establish consistency with the published feed, not independent proof of every historical track movement.

For future date extensions or additional bus coverage, see [Boston expansion notes](BOSTON_EXPANSION_NOTES.md), including the current fixed-date settings, archive selection, bus classification and checks to preserve.

## Structure

- `data/raw/`: source CSV
- `data/warehouse/`: full Parquet conversion and DuckDB database
- `data/processed/daily/`: day-level extracts
- `data/processed/werribee/`: Werribee-specific subsets and summaries
- `sql/`: reusable DuckDB queries
- `scripts/`: local analysis scripts
- `reports/`: written findings and generated figures

## Main files

- `data/raw/train_service_passenger_counts_fy_2023_2024.csv`
- `data/warehouse/train_service_passenger_counts_fy_2023_2024.parquet`
- `data/warehouse/suntrain.duckdb`
- `data/processed/werribee/werribee_2023-07-10.parquet`
- `sql/werribee_eda.sql`

## Git Notes

- `data/raw/` is local-only and ignored by git because the source CSV is too large for GitHub.
- The repo tracks the processed subsets, warehouse Parquet, DuckDB file, SQL, scripts, reports, and generated charts.

## Querying

Use `data/warehouse/suntrain.duckdb` in SQLTools and query the view:

```sql
SELECT *
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
LIMIT 20;
```

## Source Reference

Official source page:

- `https://opendata.transport.vic.gov.au/dataset/train-service-passenger-counts/resource/162887ef-1dba-4d9b-83bd-baee229229c6`

Direct CSV download:

- `https://opendata.transport.vic.gov.au/dataset/46b559b9-1846-4bf9-8ca6-fa4458f090ba/resource/162887ef-1dba-4d9b-83bd-baee229229c6/download/train_service_passenger_counts_fy_2023_2024.csv`

Key notes from the official data dictionary:

- One business date covers services operating from `03:00` to `02:59` the following day.
- `Direction`: `U` means toward Flinders Street, `D` means away from Flinders Street.
- `Passenger_Boardings`, `Passenger_Alightings`, `Passenger_Arrival_Load`, and `Passenger_Departure_Load` are rounded to the nearest `10`.
- `Mode` is the operator category, e.g. `Metro` or `V/Line`.
- `Station_Chainage` is the recorded station distance from Southern Cross Station.
- Scheduled arrival and departure times are stored in `HH:mm:ss`.

Relevant fields from the official reference table:

| Field | Meaning |
| --- | --- |
| `Business_Date` | Business date the service operates on |
| `Day_of_Week` | Calendar day name, or `Public Holiday` when masked |
| `Day_Type` | Day classification such as `Normal Weekday`, `Saturday`, `Sunday`, `School Holiday`, `Public Holiday` |
| `Mode` | Operator category |
| `Train_Number` | Unique train service identifier on a business date |
| `Line_Name` | Train line |
| `Group` | Location/service group |
| `Direction` | `U` toward Flinders Street, `D` away from Flinders Street |
| `Origin_Station` | Service origin station |
| `Destination_Station` | Service destination station |
| `Station_Name` | Station for the stop-level row |
| `Station_Latitude` | Station latitude |
| `Station_Longitude` | Station longitude |
| `Station_Chainage` | Distance from Southern Cross |
| `Stop_Sequence_Number` | Stop order within the service |
| `Arrival_Time_Scheduled` | Scheduled arrival time |
| `Departure_Time_Scheduled` | Scheduled departure time |
| `Passenger_Boardings` | Rounded count boarding at that stop |
| `Passenger_Alightings` | Rounded count alighting at that stop |
| `Passenger_Arrival_Load` | Rounded onboard count on arrival |
| `Passenger_Departure_Load` | Rounded onboard count on departure |

Planning caveat:

- The dataset does not include train vehicle capacity directly. Capacity planning in this repo should therefore treat `Passenger_Departure_Load` as observed demand/load, and use a separate rolling-stock capacity lookup if load factors are needed.
- The dataset includes scheduled stop times and `Station_Chainage`, which is enough to estimate scheduled inter-station speed. That metric should be treated as timetable-based rather than actual observed train speed.

## Segment Speed Analysis

You can estimate scheduled speed between consecutive stations with:

- distance from `Station_Chainage`
- run time from previous-station `Departure_Time_Scheduled` to current-station `Arrival_Time_Scheduled`

The reusable DuckDB query lives at `sql/segment_speeds.sql`.

To materialize the Werribee segment-speed review with confidence buckets, run:

```bash
./.venv/bin/python scripts/werribee_segment_speeds.py
```

This writes:

- `data/processed/werribee/werribee_segment_speeds_confidence_all.csv`
- `data/processed/werribee/werribee_segment_speeds_confidence_high.csv`
- `data/processed/werribee/werribee_segment_speeds_confidence_medium.csv`
- `data/processed/werribee/werribee_segment_speeds_confidence_low.csv`

To materialize the same review for every line in the warehouse, run:

```bash
./.venv/bin/python scripts/export_segment_speeds.py
```

This writes:

- `data/processed/segment_speeds/all_lines_segment_speeds_confidence_all.csv`
- `data/processed/segment_speeds/all_lines_segment_speeds_confidence_high.csv`
- `data/processed/segment_speeds/all_lines_segment_speeds_confidence_medium.csv`
- `data/processed/segment_speeds/all_lines_segment_speeds_confidence_low.csv`
- per-line folders under `data/processed/segment_speeds/by_line/`

## EDA Script

Run:

```bash
python3 scripts/werribee_eda.py
```

This reads `data/processed/werribee/werribee_2023-07-10.parquet` and writes charts to `reports/figures/werribee_2023-07-10/`.

## Dashboard

The repo now includes a multi-day Dash app backed directly by DuckDB.

Public deployment:

- `https://ptv-fc49.onrender.com/`

Run locally:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python app.py
```

Then open `http://127.0.0.1:8050`.

Notes:

- The app queries the warehouse Parquet directly through DuckDB, so it can handle additional dates without rebuilding a single-day dashboard dataset.
- The app reads `SUNTRAIN_PARQUET_GLOB`, so you can later point it at one file or a partition glob under `data/warehouse/`.
- Arrival and departure times are formatted in the UI as `HH:MM`.
- A basic health endpoint is available at `/health`.
- `render.yaml` is included for Render deployment.

## Transport Replay

The **Transport Replay** tab combines Metro and V/Line train records with archived PTV tram and bus schedules for **27 May–30 June 2024** (five full Monday–Sunday weeks), opening on Monday 27 May at 08:00. Choose a day, press **Play**, or drag the timeline. Filter by transport mode, operator/feed, route, direction, stop served or service/trip number. Stop filters keep each matching service's entire journey. Trams and metropolitan trains use the supplied route and line colors in both themes; Melbourne buses are orange (#FF8200). Other cities retain their own bus colours (Boston yellow, London red). Route colors also appear in the legend, service details and selected journey. Name variations are normalized; Stony Point uses Frankston green, V/Line uses purple, and unrecognized routes use neutral grey. Bus coverage includes complete branch-4 journeys with at least one stop inside the Melbourne map extent (144.55–145.6° E, 38.15–37.48° S), including journeys continuing beyond it. This is a timetable replay, not live tracking.

Click a vehicle to inspect its scheduled journey. **Size trains by passengers** affects trains with known loads; trams and buses keep their normal size and show passenger counts as unavailable. The **Passenger heatmap** uses train boardings only; selecting only trams or buses leaves the heatmap empty. Tram/bus directions A and B distinguish the two feed directions; they do not imply travel toward or away from the city. Operator/feed labels identify the PTV source, rather than the individual bus operating company.

Vehicle circles and outlines shrink at wider zooms and grow gradually when zooming in. At zoom 9, ordinary vehicle circles have a 2.5 px radius; at street zoom they grow to 5 px. Passenger sizing adjusts that radius by at most 20% either way. Train stations remain visible at wider zooms, while tram and bus stops fade in between zooms 12 and 13. The selected vehicle has a separate halo at every zoom. **Stops & stations** controls both types of stop markers.

The site has two main tabs: **Transport Replay** and **Overview**, sharing **Location**, **Date**, **Transport** and **Route / line** controls. **More filters** holds operator, direction, calling-at and trip filters. Overview shows scheduled departures, routes/lines, distinct mapped stops/platforms, departures by local hour and a sortable route table (15 rows per page). Departures are counted once by their first scheduled departure within the city’s 03:00–03:00 business window; a repeated daylight-saving hour is combined into one local-hour bar. Switching tabs preserves the selection and replay clock without another download.

For Melbourne, expand **Melbourne train passenger analysis** to open the existing **Summary**, **Lines & Services**, **Segment Speed**, and **Network** reports, with raw rows and CSV export. Its date and supported train-line filters are seeded from the shared controls on first opening; its own filters then retain the wider passenger-data period. These detailed reports stay closed initially and are unavailable for other cities.

Use **Dark mode** in the header or replay map toolbar to switch the site, charts, and map backgrounds together. The theme is saved in this browser. The map toolbar toggle also works in fullscreen, and changing themes preserves playback, filters, and the map view.

Choose **Passenger heatmap** or **Both** under the map to explore station boardings in the previous **15, 30, or 60 minutes**. The heatmap follows the replay clock and service filters. Marker colors use a fixed scale of **0, 100, 500, 2,000, and 5,000+ boardings**; hover or click a station for its exact aggregate. The softer glow shows relative concentration around nearby stations and varies with zoom. This measures boarding events, so a passenger boarding another train can be counted again. It does not measure unique passengers, platform crowding, or on-board load.

Counts use recorded boardings at scheduled departure times, in a right-closed rolling window, from the selected business date's services only. Zero counts stay zero; unavailable counts are excluded and reported separately. Seeking backwards recomputes the window. Unresolved train paths do not prevent station demand from being shown. Prefix sums run in the browser, and the heatmap refreshes at minute boundaries (at most five times per second during fast playback) without server queries. Fullscreen retains the view/window controls and scale.

Transport Replay is the opening view and first tab, with the map initially focused on metropolitan Melbourne. **Melbourne** restores that view, while **Fit selection** shows the full extent of the filtered services. **Follow service** keeps a selected vehicle centered during playback; dragging the map or choosing a view stops following.

**Fullscreen** expands the map with playback controls, speeds up to **2,000×**, and a **Filters** button for the date, line and operator controls. Selected-train details appear over the map and can be closed. Use **Exit fullscreen** or **Escape** to return. Browsers without native fullscreen expand the map to fill the browser window instead.

Positions are estimates interpolated between scheduled stops, with trains stationary during scheduled dwell times. They are not recorded GPS positions. Passenger counts are rounded to the nearest 10 and do not indicate capacity percentages. Each marker represents a scheduled service, rather than a tracked physical vehicle across multiple journeys.

Playback runs in the browser after loading the selected day. Midnight, the 03:00 business-day boundary and Melbourne daylight-saving changes are handled in stop order. The timeline extends when services assigned to a business date finish after the following 03:00. Ambiguous repeated-hour times are marked; invalid service timing is omitted with a visible count.

The replay uses MapLibre GL JS 5.6.1, vendored with its [license](assets/maplibre-LICENSE.txt), and attributed OpenStreetMap background tiles. The background needs an internet connection; vehicle playback and the prepared route geometry do not make external data requests.

Railway curves are prepared locally in `data/reference/rail_paths.json` from the official [Transport Victoria GTFS Schedule](https://opendata.transport.vic.gov.au/dataset/gtfs-schedule), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The pinned geographic reference is dated **15 October 2026**, so it may differ from the FY 2023–24 network. It supplies geometry only. No external timetable replaces the historical services or passenger counts. Unmatched or ambiguous paths are left as gaps. Train markers are hidden between those stops and reappear at the next recorded station; active-service counts include services whose positions are unavailable. The map and selected-service details explain these gaps. Selected-route highlights contain resolved railway geometry only.

To rebuild the geographic reference from a downloaded official archive:

```bash
curl --fail --location https://data.ptv.vic.gov.au/downloads/gtfs.zip --output /tmp/suntrain-gtfs.zip
./.venv/bin/python scripts/prepare_replay_geometry.py /tmp/suntrain-gtfs.zip --source-date YYYY-MM-DD
```

Use the archive's actual publication date. Preparation excludes replacement-bus trips, normalizes known station aliases (including Jolimont-MCG), and anchors each stop occurrence to its GTFS shape distance before simplification. Ordered journey stops and geometric checks for out-of-order station crossings constrain route matching; a unique corridor can be composed from verified station-to-station rail segments when no single shape covers a journey leg. Ambiguous corridors remain unresolved. Preparation retains train shapes only and caches intermediate geometry under `.cache/`; the full archive is not required by the app. Set `SUNTRAIN_RAIL_GEOMETRY` to use another prepared reference. Without a reference, replay shows trains at recorded stations and hides their positions between stops. Train data continues to use `SUNTRAIN_PARQUET_GLOB`.

The bundled tram/bus reference uses a small date index at `data/reference/transit/index.json` and separate compressed snapshot bundles beside it. The five [MobilityDatabase PTV archives](https://mobilitydatabase.org/feeds/gtfs/mdb-657) were captured on **27 May, 3 June, 8 June, 17 June and 24 June 2024**, in Melbourne time. Each date selects the most recent of these snapshots captured on or before that date; service calendars and exceptions determine which journeys run. Only the selected snapshot is opened on the server, and only the selected replay day is sent to the browser. Source dates and attribution follow the selected snapshot.

Rebuild all five weeks with:

```bash
./.venv/bin/python scripts/prepare_transit_period.py
```

The script downloads the pinned archives, caches only their tram/bus branches under `.cache/transit-archives/`, reuses matching geometry between snapshots, and writes the date index after every bundle is ready. Rebuilding individual date ranges is also supported by `scripts/prepare_transit_replay.py --help`.

Preparation applies weekday calendars and date exceptions, preserves GTFS times beyond 24:00, and includes journeys crossing the 03:00 business-day boundary. Stop-distance anchors locate each journey leg on the supplied shape, including loops; missing anchors leave route gaps rather than drawing straight shortcuts. Invalid schedules are omitted. Relative stop schedules and geometry stay shared between trips in the browser; playback applies each trip's departure offset without expanding its stops into separate arrays. Absolute times are calculated only when needed, including for a selected journey's stop table. Map paths and stop markers are collected once per shared schedule. No passenger counts are synthesized. Set `SUNTRAIN_TRANSIT_REFERENCE` to override the date index or use a legacy single `.json.gz` bundle. If it is missing, the original train-only historical replay remains available. The optional Melbourne passenger analysis retains the full train passenger dataset.

Validation:

```bash
./.venv/bin/python -m pytest -q
node --test tests/test_replay_animation.cjs tests/test_passenger_demand.cjs
```

## Deploying To Render

The repo is ready to deploy as a Python web service.

### Option 1: Use `render.yaml`

1. Push the repo to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Connect the GitHub repo and select this repository.
4. Render will read `render.yaml` and create the web service automatically.

### Option 2: Create The Web Service Manually

Use these settings:

- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 dashboard.app:server`
- Health Check Path: `/health`

Set this environment variable:

- `SUNTRAIN_PARQUET_GLOB=data/warehouse/train_service_passenger_counts*.parquet`

### Deployment Notes

- Current public site: `https://ptv-fc49.onrender.com/`
- The current tracked Parquet warehouse file is included in the repo, so the first deploy can run without an external database.
- If you later add much larger Parquet files, consider moving the warehouse onto a Render disk or object storage instead of keeping all data in git.
- The repo pins Python with [.python-version](/Users/adhni/Desktop/SunTrain/.python-version) so Render does not fall back to its current default `3.14.x`, which can break `pyarrow` wheel installs.

## Optional Chicago and Perth buses

Chicago buses cover **24 November–28 December 2025**; Perth buses cover **5–11 October 2026**, matching their existing rail periods. Select **Buses** (Chicago) or **Buses / CAT** (Perth) under Transport; clearing Transport includes all available modes. Rail opens first and changing modes preserves the replay clock. Perth includes only bus agencies named **Transperth**, including Perth, Fremantle and Joondalup CAT where scheduled; regional operators, Transwa and ferries stay excluded. Ordinary Perth buses retain feed green, while CAT retains its supplied route colours. Route legends, filters and selected journeys use the same colours.

Rebuild from the existing pinned source ZIPs:

```bash
./.venv/bin/python scripts/prepare_city_buses.py chicago
./.venv/bin/python scripts/prepare_city_buses.py perth
```

Prepared daily references live under `data/reference/<city>/bus/`. `SUNTRAIN_CHICAGO_BUS_REFERENCE` and `SUNTRAIN_PERTH_BUS_REFERENCE` can override those directories. Only the selected day is opened at runtime; stops, timings and geometry remain shared. Source ZIPs are preparation-only. Bus occurrences are assigned once by their start time within a 03:00–03:00 business window and may finish afterward. No frequency templates were present in these pinned bus feeds; future frequency feeds are rejected until explicitly supported. Passenger loads are unavailable. See the city expansion notes for source gaps, calendars and attribution.
