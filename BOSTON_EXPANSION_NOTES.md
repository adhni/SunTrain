# Boston replay: notes for the next expansion

## Current baseline

- Boston covers **24–30 June 2024**: subway, Green Line B/C/D/E, Mattapan, scheduled MBTA commuter rail and **Silver Line SL1–SL5 plus SLW**, with regular MBTA buses available as an optional layer. The initial rail-only pilot commit is `83310ab`; Silver Line is included in the same PR.
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

## Regular buses: implemented, optional

- Regular MBTA buses now use the same **24–30 June 2024** week and four validated rail/Silver Line source archives. `--buses` verifies their SHA-256 against the existing baseline before preparing them. Keep rail and Silver Line selected initially; regular buses download only when Buses is selected, or Transport is cleared for all modes.
- Daily references live at `data/reference/boston/bus/<date>.json.gz` (about **0.58–1.10 MB** each). Weekdays have **10,950 services / 150 active routes**; Saturday has **7,517 / 121**, Sunday **5,026 / 99**. All seven dates have no omitted trips or unresolved geometry patterns. Route records that are inactive that day are not fabricated.
- **Regular buses are MBTA yellow (`#FFC72C`), from the historical feed; Silver Line stays silver (`#7C878E`).** Melbourne orange is specific to Melbourne. Other cities use their own palette or valid source route colour, with a neutral fallback for an unknown city.
- `is_regular_bus()` selects MBTA type-3 routes, excluding official Silver Line groups and `Rail Replacement Bus` routes. Non-empty `trip_route_type` still overrides route type, so a bus substitution on a rail route cannot become either a regular bus or an animated train. Non-MBTA operators and ferries remain excluded.
- Each bus follows its own dated road shape, with ordered stop projection within 150 m. Repeated stops and loops retain journey order. Regular stops use the zoom-dependent bus-stop layer; Silver Line remains a separate mode/filter.
- `scripts/compact_transit.py` shares stop topologies and flat relative times, then selects the paths/stations needed for each daily file. Do not expand stop arrays per trip. The common optional-bus loader is shared with London and keeps its one merged-day cache bounded.
- Rebuild regular buses with `PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_boston_replay.py --buses`. This preserves the separate rail/Silver file. `--output` accepts a daily-bundle directory in bus mode; `SUNTRAIN_BOSTON_BUS_REFERENCE` overrides that directory at runtime. For a date expansion, regenerate these daily files as well as rail and update their coverage together.
- The four selected archives contain no frequency templates. Preparation rejects selected frequency-based trips in a future source until explicit handling is implemented. Keep MBTA attribution/licensing alongside the optional bus layer; no TfL geometry credit belongs on Boston data.

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

Regular-bus expansion validated on 18 October 2026: the combined five-city suite passed 160 Python and 26 JavaScript tests. Chrome verified yellow regular buses, separate silver Silver Line, optional downloads, shared flat schedules, route filters/details, clock preservation and 2,000× playback without server POSTs. A local first bus-only load measured about 1.25 seconds; this is not a hosted/mobile performance guarantee.
