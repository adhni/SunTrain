# Chicago: verified data and next steps

## Implemented scope

- Same feature branch / PR as Boston. Chicago uses the existing replay UI and compact shared-pattern format, via the prepared-city loader in `dashboard/replay.py`.
- **24 November–28 December 2025**, CTA rail only: Red, Blue, Brown, Green, Orange, Pink, Purple and Yellow. This is a clearly labelled fallback, not the preferred 27 May–30 June 2024 period. Boston remains 24–30 June 2024 and Melbourne retains its existing dates.
- `dashboard/cities.py` supplies Chicago's coverage, `America/Chicago` timezone, bounds, CTA operator and direction filters. Cardinal directions are taken from the feed when present; direction A/B represents GTFS direction IDs where no usable compass label is supplied.
- `scripts/prepare_chicago_replay.py` writes `data/reference/chicago/2025-11-24.json.gz`; `SUNTRAIN_CHICAGO_REFERENCE` overrides the loaded file. The source downloads in `.cache/chicago-archives/` are local and ignored by git.

## Source accessibility audit (17 October 2026)

| Source | What was verified | Consequence |
| --- | --- | --- |
| [CTA official GTFS](https://www.transitchicago.com/developers/gtfs/) | Official page describes a rolling feed with one current package. | Do not use the current ZIP to reconstruct 2024. |
| [Requested Transitland 2024 version](https://www.transit.land/feeds/f-dp3-cta/versions/d0dfae0ebdeb10443ac66a068a4501fb6d25120b) | Public metadata lists 22 March–30 June 2024. The SHA-specific download returned HTTP 401 without credentials. | Metadata alone is insufficient to integrate this period. [Transitland documents](https://www.transit.land/documentation/concepts/static-gtfs-feed-versions) historical ZIP access through paid or qualifying complimentary accounts. |
| [MobilityDatabase CTA catalog](https://mobilitydatabase.org/feeds/gtfs/mdb-389) | Public history exposes downloadable later snapshots. The older-history API required authentication; no 2024 ZIP was obtained. | Use the actual accessible 2025 ZIPs below; revisit 2024 when an authenticated archive or verified ZIP is supplied. |
| [Metra current ZIP](https://schedules.metrarail.com/gtfs/schedule.zip) | Downloadable and contains schedules, but it is the current rolling package. A sample calendar included 2025–2026 dates. No historical 2024 publication was validated. | Calendar dates alone do not prove a historical timetable version. Defer Metra; do not pretend the current package is an archived 2024 feed. |
| [CTA daily station entries](https://data.cityofchicago.org/d/5neh-572f) | Public JSON API returned station/day entry totals for 27 May 2024, with station ID, station name, date, day type and rides. | Suitable for a separate **daily station** view after station matching and date coverage checks; not per-train loads or within-day boarding times. |

The user explicitly allowed another historical period if usable historical data was available. No subscription was purchased and no account was created.

## Pinned fallback feeds

1. [mdb-389-202511230128.zip](https://files.mobilitydatabase.org/mdb-389/mdb-389-202511230128/mdb-389-202511230128.zip), captured 23 November 2025 UTC. Used for service dates through 18 December, including Thanksgiving exceptions.
2. [mdb-389-202512190112.zip](https://files.mobilitydatabase.org/mdb-389/mdb-389-202512190112/mdb-389-202512190112.zip), captured 19 December 2025 UTC. Used from 19 December, including Christmas exceptions.

Source URLs, capture dates and SHA-256 hashes are retained in the generated reference. GTFS service dates include the preceding and following calendar days for overnight carry-ins. Trips overlapping 03:00 intentionally remain visible on adjacent replays; there must be no duplicate occurrences within one day. GTFS service zero uses local noon minus 12 elapsed hours.

The prepared baseline is **392,174 bytes**, with 77 shared schedule patterns and all eight lines on every date. All 35 day payloads passed reference/uniqueness checks, with no invalid-trip omissions or unresolved geometry patterns. Thanksgiving and Christmas each contain 1,520 services, compared with 1,913 on ordinary Monday–Thursday dates. The suite passed **79 Python + 23 JavaScript tests**; Chrome checks covered the actual Brown Line Loop, holidays, feed changes, playback, themes, fullscreen, mobile and Chicago → Boston → Melbourne switching without page errors.

Both CTA source ZIPs must be parsed locally; the browser never downloads them. Routes omit `agency_id` in this single-agency feed, which is valid GTFS: the importer checks the sole CTA agency and timezone. Buses are filtered out before retaining stop times and geometry. Frequency-based rail schedules cause an explicit preparation error rather than fabricated exact departures.

## Geometry and passenger constraints

- Use **native `shape_dist_traveled` anchors**, shared with the existing Melbourne geometry preparation, for every ordered stop occurrence. This preserves repeated Loop stops without nearest-point shortcuts. Trip-specific shapes preserve branch and express/local differences encoded in the feed.
- Do not infer direct lines across missing geometry or relax the 150 m station matching threshold to hide errors. Keep unresolved legs as gaps and report them. Check downtown Loop geometry visually and test a journey that revisits its origin.
- Train colours come from the archived CTA routes. Keep Silver Line's explicit silver exception in Boston and the existing Melbourne palettes intact.
- Passenger controls remain disabled for Chicago. Do not split daily station totals across hours or allocate them to trains without independent data. A future daily ridership map needs its own daily scale and explanation; it must not reuse Melbourne's intraday heatmap semantics.

## Future dates, buses and Metra

- For 2024, first obtain an actual dated ZIP, inspect calendars/exceptions and check whether newer snapshots change the requested days. Update archive selection, preparation dates/default output, city coverage, loader path and tests together. Never relabel 2025 data.
- For CTA buses, the existing archives already contain bus routes and shapes. Add them in a separate requested step, keeping the same validated period first. Review shape quality, frequency rows, holidays, memory and marker density. Regular bus markers stay orange; separate line filters retain route numbers.
- For Metra, find and validate a historical snapshot before integration. The current ZIP's calendar headers and values include leading spaces, so normalize them before calendar parsing. Keep Metra separate from CTA in mode/operator filters and validate all branches, weekday-only lines and source geometry. It should not delay CTA.
- For longer periods, consider the Melbourne-style date index and snapshot chunks instead of growing one multi-month in-memory reference. Continue sending one selected day and retaining shared stop arrays in the browser.

Run Python and JavaScript tests, audit every date for all eight lines / unique occurrences / geometry diagnostics, and browser-check city switches, dates, line colours, Loop selection, playback, mobile, themes and fullscreen. Include a holiday, weekend, archive-change date and overnight trips. Preserve Melbourne passenger tools and Boston Silver Line.

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest -q
node --test tests/test_replay_animation.cjs tests/test_passenger_demand.cjs
```
