# Boston replay: notes for the next expansion

## Current baseline

- Boston covers **24–30 June 2024**: subway, Green Line B/C/D/E, Mattapan, scheduled MBTA commuter rail and **Silver Line SL1–SL5 plus SLW**. The initial rail-only pilot commit is `83310ab`; Silver Line is included in the same PR.
- This is historical **scheduled** movement. Do not add live feeds or infer passenger counts. Boston passenger sizing and heatmaps remain unavailable; Overview still analyses Melbourne.
- Four official archives supply the week and neighbouring calendar dates: `20240613.zip`, `20240625.zip`, `20240626.zip`, `20240627.zip`. Select using the [official index](https://cdn.mbta.com/archive/archived_feeds.txt)'s validity windows, not ZIP filenames or today's timetable. The index can include retrospective corrections.
- Bundled reference: `data/reference/boston/2024-06-24.json.gz`. It retains source URLs, versions, validity dates, hashes and preparation diagnostics. All seven days have all three rail categories and Silver Line, no duplicate occurrences within a day, no omitted invalid trips and no unresolved geometry patterns in this baseline.
- Silver Line is mode **`silver_line`**, identified by official feed groups `line-SLWaterfront` / `line-SLWashington`. Route IDs in this week are `741` (SL1), `742` (SL2), `743` (SL3), `751` (SL4), `749` (SL5), `746` (SLW). Keep the short-turn SLW trips and distinct route labels; do not assume only SL1–SL5 exist. **The user explicitly requested Silver Line be silver (`#7C878E`), overriding the general orange bus preference for these routes.** Use that colour for vehicles, legends and selected journeys in both themes. Silver Line stops use the existing zoom-dependent bus-stop layer.
- Preparation: `scripts/prepare_boston_replay.py`; local source cache: `.cache/boston-archives/`. The cache is ignored by git and may not exist on another machine.

## When extending the dates

The pilot dates are deliberately fixed in several places. There are **no start/end date CLI flags yet**; changing only the date picker is insufficient.

1. Add date arguments to preparation, then update Boston's `start_date` / `end_date` and description in `dashboard/cities.py`. Keep generated metadata and UI coverage consistent.
2. Review `FIRST`, `LAST` and the default output filename in `scripts/prepare_boston_replay.py`, plus `BOSTON_PATH` in `dashboard/replay.py`. `SUNTRAIN_BOSTON_REFERENCE` can override the loader path. Update README and the tests that assert this specific seven-day baseline.
3. Refresh the cached `index.csv` when necessary; `fetch()` currently reuses existing files. Obtain the correct archive for **each GTFS service date**, including the day before and the day after the requested period for overnight trips. Retain provenance and inspect omission/geometry diagnostics for every added feed.
4. For a substantially larger period, use a small date index and separate snapshot/week bundles, following `dashboard/transit.py` and `scripts/prepare_transit_period.py`. The browser already receives one selected day; avoid loading an ever-growing multi-month reference on the server or copying stop arrays per trip in the browser.

Start with complete additional weeks aligned to Melbourne's dates if that is what the user requests; do not automatically widen the scope to months or change Melbourne's dataset.

## When adding the remaining buses

- Keep the existing week for the first bus test unless the user requests a date expansion too. Audit bus routes and trip availability in the same archived MBTA feeds before changing the UI.
- Preparation currently selects MBTA rail routes plus the two Silver Line groups. Broaden route selection for regular buses and, if requested, replacement shuttles, then extend `replay_mode()`. Preserve classification by non-empty **`trip_route_type` override**, falling back to `route_type`. A bus replacing a rail service must appear once as a bus, never as a train too.
- Silver Line is already implemented and should remain a distinct filter. Decide from the actual feed how to distinguish regular buses and replacement shuttles. Do not assume route names, current route lists or bus rapid transit being rail. Continue excluding non-MBTA agencies unless separately requested.
- Reuse trip-specific shapes and the ordered stop projection in `project_stops()`. MBTA stop times lack distance anchors. Repeated stops and loops must retain journey order; distant or invalid matches remain gaps. Do not relax the 150 m matching threshold just to make an audit pass.
- Add regular bus mode/filter options in `dashboard/cities.py`, and derive any additional direction options from actual feed values. Preserve `train` / `bus` stop tags and mode-aware stop deduplication so bus stops stay in the existing zoom-dependent local-stop layer.
- **Keep regular buses orange (`#FF8200`) and Silver Line silver (`#7C878E`)**. `vehicleColor()` forces `bus` to orange, honours the historical Silver Line colour, and supplies a silver fallback for that mode. Do not collapse Silver Line into the generic orange bus colour rule. Preserve the existing Melbourne tram/train palettes and MBTA rail colours.
- Update the rail-and-Silver-Line captions, quality message and attribution in `dashboard/cities.py` and `assets/train_replay.js`, plus README and mode-coverage tests. The four current archives have no `frequencies.txt`; audit any frequency-based schedules if newly selected feeds contain them rather than silently ignoring or inventing departures.

## Behaviour to preserve and checks to run

- Replay uses a **03:00–03:00 local business window**, GTFS times beyond 24:00 and `America/New_York`. GTFS service zero is local noon minus 12 elapsed hours. Across DST changes, use local boundaries and timestamps rather than assuming every day is 86,400 seconds.
- Trips crossing 03:00 intentionally remain visible on both adjacent replays. This preserves continuity; the invariant is **no duplicate occurrence inside a single replay day**. Do not switch to start-date-only assignment without preserving carry-in visibility.
- Keep pattern stops and paths shared. Trip instances carry departure offsets; `hydrate()` attaches references and `stopTime()` adds offsets only when needed.
- Both the browser's loaded-day state and server cache checks must include **city and date**. Switching Boston → Melbourne on the same date previously exposed a loading-state bug; verify both directions with an active route filter, and ensure old-city responses do not replace the current selection.
- Audit every new date for active modes, unique trip occurrences, valid station/path references, omissions and geometry gaps. Check weekdays, weekends, feed changes, calendar exceptions, extended-hour trips and any DST transition in the expanded period.
- Browser-check bus density at metro zoom and close zoom, filters, route details, 2,000× playback, dark mode, fullscreen and mobile. Confirm Melbourne's replay and passenger tools still work.

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -q
node --test tests/test_replay_animation.cjs tests/test_passenger_demand.cjs
```

The rail-and-Silver-Line pilot passed **75 Python tests + 23 JavaScript tests**, plus desktop/mobile browser checks. Browser verification scripts and screenshots under `.cache/` are local artifacts, not tracked test dependencies.

Keep **MassDOT / MBTA attribution**, the [Developer License Agreement](https://github.com/mbta/gtfs-documentation/blob/master/developers-license-agreement.pdf) link and the application's independent status visible. Do not introduce MBTA logos or claim exact historical vehicle movements.
