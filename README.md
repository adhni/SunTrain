# SunTrain

Historical transport replay for Melbourne and Boston, with passenger analysis for the Victorian train service passenger counts dataset.

## Boston rail pilot

Choose **Boston** in the replay's **Replay city** selector to explore **24–30 June 2024**. Subway (Red, Orange and Blue), light rail (Green B/C/D/E and Mattapan) and scheduled MBTA commuter rail use the existing playback controls, route/mode/direction filters, journey details, dark mode and fullscreen. Boston uses `America/New_York` local time, its historical route colours and a metropolitan Boston starting view; **Fit selection** also shows outlying commuter rail termini. The Overview tab continues to analyse Melbourne passenger data.

This is a scheduled-service simulation. It does not reproduce GPS movements, delays or disruptions missing from the archived timetable. Boston has no passenger counts: passenger sizing and heatmap controls are unavailable. Replacement buses, other bus services, ferries and non-MBTA operators (including CapeFLYER) are excluded from this rail pilot. Only services active in the historical calendars appear; a listed line without active trips is not fabricated.

Data is provided by **MassDOT / MBTA**, under its [Developer License Agreement](https://github.com/mbta/gtfs-documentation/blob/master/developers-license-agreement.pdf). SunTrain is independent of MassDOT and MBTA. The [official archive index](https://cdn.mbta.com/archive/archived_feeds.txt) selects four feeds for this week and the adjoining calendar dates needed for overnight services: `20240613.zip`, `20240625.zip`, `20240626.zip` and `20240627.zip`. The index's recommended validity windows determine selection, including retrospective corrections; ZIP filename dates are not assumed to be publication dates. Source URLs, versions, validity dates and SHA-256 hashes are retained in the prepared reference.

Rebuild the pilot with:

```bash
./.venv/bin/python scripts/prepare_boston_replay.py
```

The script caches source downloads in `.cache/boston-archives/` and writes `data/reference/boston/2024-06-24.json.gz` (about 260 KB). It applies service calendars and exceptions, trip-level vehicle-type overrides and extended-hour times. Trips overlapping the 03:00 boundary remain visible on either side, with no duplicate occurrences within a replay day. Stop schedules and route geometry are shared by compact trip instances; only the selected day and its referenced paths are sent to the browser. Boston loading does not query Melbourne's passenger warehouse. `SUNTRAIN_BOSTON_REFERENCE` overrides the prepared reference path.

MBTA stop times lack distance anchors. Preparation projects the whole ordered stop sequence onto each trip's own shape, preserving branches and repeated stop occurrences. Stop projections must lie within 150 metres of that shape; invalid geometry stays as a gap, with markers hidden between those stops. Supplied shapes are simplified at approximately six metres. The bundled week has no omitted invalid trips or unresolved geometry patterns. These checks establish consistency with the published feed, not independent proof of every historical track movement.

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

The **Transport Replay** tab combines Metro and V/Line train records with archived PTV tram and bus schedules for **27 May–30 June 2024** (five full Monday–Sunday weeks), opening on Monday 27 May at 08:00. Choose a day, press **Play**, or drag the timeline. Filter by transport mode, operator/feed, route, direction, stop served or service/trip number. Stop filters keep each matching service's entire journey. Trams and metropolitan trains use the supplied route and line colors in both themes; all buses are orange (#FF8200). Route colors also appear in the legend, service details and selected journey. Name variations are normalized; Stony Point uses Frankston green, V/Line uses purple, and unrecognized routes use neutral grey. Bus coverage includes complete branch-4 journeys with at least one stop inside the Melbourne map extent (144.55–145.6° E, 38.15–37.48° S), including journeys continuing beyond it. This is a timetable replay, not live tracking.

Click a vehicle to inspect its scheduled journey. **Size trains by passengers** affects trains with known loads; trams and buses keep their normal size and show passenger counts as unavailable. The **Passenger heatmap** uses train boardings only; selecting only trams or buses leaves the heatmap empty. Tram/bus directions A and B distinguish the two feed directions; they do not imply travel toward or away from the city. Operator/feed labels identify the PTV source, rather than the individual bus operating company.

Vehicle circles and outlines shrink at wider zooms and grow gradually when zooming in. At zoom 9, ordinary vehicle circles have a 2.5 px radius; at street zoom they grow to 5 px. Passenger sizing adjusts that radius by at most 20% either way. Train stations remain visible at wider zooms, while tram and bus stops fade in between zooms 12 and 13. The selected vehicle has a separate halo at every zoom. **Stops & stations** controls both types of stop markers.

The site has two main tabs: **Transport Replay** and **Overview**. Overview contains **Summary**, **Lines & Services**, **Segment Speed**, and **Network** sub-tabs; it remembers your selected sub-tab when you return from replay.

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

Preparation applies weekday calendars and date exceptions, preserves GTFS times beyond 24:00, and includes journeys crossing the 03:00 business-day boundary. Stop-distance anchors locate each journey leg on the supplied shape, including loops; missing anchors leave route gaps rather than drawing straight shortcuts. Invalid schedules are omitted. Relative stop schedules and geometry stay shared between trips in the browser; playback applies each trip's departure offset without expanding its stops into separate arrays. Absolute times are calculated only when needed, including for a selected journey's stop table. Map paths and stop markers are collected once per shared schedule. No passenger counts are synthesized. Set `SUNTRAIN_TRANSIT_REFERENCE` to override the date index or use a legacy single `.json.gz` bundle. If it is missing, the original train-only historical replay remains available. Overview retains the full train passenger dataset.

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
