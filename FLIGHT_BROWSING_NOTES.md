# Geographical flight browsing

Flight discovery now uses **World → region → country/territory → exact airport**.
Each choice filters the existing canonical World snapshot. A flight belongs to a
place when either endpoint is there; domestic flights count once. Connections
can appear in both geographical views without duplicating identities on the map.

The prepared 2 November 2026 UTC snapshot contains **57,250 unique flights**,
**17,903 directional routes**, **1,577 airports with captures** and **213 endpoint
countries/territories**. These are partial captures, not complete national or
worldwide traffic. No captures, quotes, paths or replay HTTP formats changed.

## Discovery

- Six primary regions: Africa, Asia, Europe, North America, South America,
  Oceania. Central Asia and Pacific Islands are subregions.
- Regional membership is explicitly reviewed in `dashboard/flight_places.py`.
  North America includes Central America and the Caribbean. Türkiye, Georgia,
  Cyprus and Russia browse under Europe. Territory codes stay distinct. These
  are navigation groups, not airspace boundaries or collection-completeness claims.
- Country/region counts include every matching World capture, regardless of
  which original collection supplied it. A UK choice exposes 4,208 flights;
  Singapore exposes 1,067 on this UTC day.
- Only countries and transit places get discovery pins. Regions, airports,
  experiences and World are searchable without arbitrary regional map pins.
  Country clusters have bounded screen extents so nearby pins cannot chain
  into a single enormous list. Cluster members sort by displayed place name.
- Dropdowns separate regions, countries, airports, experiences, rail/local
  transport and original dated replays. Blank searches show popular countries
  and airports; typing searches the full catalogue, including names, cities,
  exact IATA codes, ISO codes and UK/USA aliases. Regional/country choices narrow
  the suggestions; direct search remains global. Selected values remain valid
  while searching for something else. Search results omit disabled headings so
  Enter chooses a real place.
- Gulf connections, Across the Atlantic, International flights and European
  airline networks are experiences over World. Airline brand/group filters remain.
- The Singapore Watch scene uses the shared Singapore lens at **02:00 UTC /
  10:00 Singapore time**. World Watch remains 10:00 UTC. Scene presets still
  respect reduced motion and superseded choices.

## Replay behaviour

Geographical navigation reuses the loaded World replay, retaining clock,
playback, airline filters and other explicit filters. Breadcrumbs navigate to
parents. Region/country cameras use their place bounds; airports and countries
with at most two captured airports open around connections. Reset restores that
place's opening frame; Fit flights frames the matching flights. Other filter
changes keep the camera steady. Moving flights, local boards, destinations,
frequency, fullscreen and visibility controls use the same geographical filter.

Data revisions refresh coverage without triggering navigation. Adding transit
modes on the same city/date keeps the existing camera and clock; transit
city/date changes retain the original replay loader's framing policy. The
Melbourne regression explicitly checks that a bus-mode reload changes the
revision while preserving centre, zoom, bearing, pitch and time (PR #81 review).

The explorer keeps **one UTC day**, including overlapping flights already in
World. Airport boards retain their local timestamps and existing dated Canadian
offsets. Original collection views remain available through **Dated replays**
(search the place or “replay”), keeping their original windows and additional
dates, including Indonesia's 2–8 November week. The discovery default no longer
equates these collector-specific windows with a geographical country choice.

Airline choices sort by unique captured flights, descending, with deterministic
name/code ties. Counts follow place, airport, domestic/international and other
filters, excluding the airline filter itself. Carriers come first, then named
groups and networks; these overlapping categories are labelled. Selected
zero-match airlines remain removable. These are captured schedule counts, not
current airborne counts or complete airline traffic.

Native dropdown string labels preserve search/focus state. Names, codes,
secondary descriptions and count badges are presented without nesting dynamic
Dash components into the option labels (which caused search popover remounts
and restored older queries in the installed Dash 4). English/Indonesian place
names use browser region names; new interface copy has both translations.

## Index preparation

`data/reference/flight_places.json` is a small, deterministic discovery index,
derived from the validated World snapshot, with its SHA-256. It contains counts,
membership and bounds, **no flight records or geometry**. Homepage discovery
does not download a replay. Tests verify the index against the unchanged source.

The normal World preparation CLI also refreshes the index. To rebuild just it:

```bash
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python -m scripts.prepare_flight_places
```

Existing World and original-view replay endpoints, gzip caching, carrier palettes,
fares, source evidence and archived files are unchanged. No searches or downloads
were performed to expand coverage.

## Validation

Artifacts and browser logs are ignored under `.cache/flight-geography/`.
The focused regression covers repeated searches, keyboard selection, unique
geographical counts, exact airports, no-download drill-down, ongoing playback,
ranked/contextual airline counts, rapid switching, Pacific Reset, frequency
totals, airport/fullscreen boards, translation, mobile layout, Back and original
week-long replay access. Existing World, playground and Melbourne checks are
run separately; final results are recorded with the artifacts.

Results: **115 Python tests** and **64 JavaScript tests** passed, plus the final
targeted preset/dropdown checks. Flight-place, World, playground and Melbourne
browser assertions passed, covering both languages and all five themes.
Flight-place, World and Melbourne browser shutdowns completed. The final
playground run stalled in Playwright shutdown after Chrome had exited; its
orphaned driver was terminated separately. Its assertions, including the shared
Singapore preset, passed; the earlier playground run exited normally.

The Melbourne harness initially selected a train ring almost coincident with a
bus stop before the latest map frame had rendered. The actual click correctly
opened the nearer bus stop. The regression now waits for rendering and chooses
an unambiguous station using native pointer pixels; all station and board
assertions then passed. No production transit picking behaviour changed.
