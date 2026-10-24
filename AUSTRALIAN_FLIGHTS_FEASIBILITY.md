# Australian domestic flight pilot

Choose **Australia · Flights** in Location for **4–10 March 2013**. The pilot
replays the published Jetstar domestic timetable across 18 airports, including
Melbourne, Avalon, Sydney, Brisbane, Perth, Adelaide, Darwin, Cairns and Hobart.
Other airlines are absent. This is a dated personal-project timetable replay;
plane positions and great-circle paths are illustrative.

Click an airport marker or code to open its **Departures / Arrivals** board.
The map shows its connections and mutes unrelated planes. The board expands to
fill the viewport, supports paging and returns to the same arrival/departure
selection after viewing a flight. Previewing a flight preserves replay time;
**Go to departure / arrival** explicitly seeks to that event and pauses playback.

## Timetable and preparation

The [official Jetstar domestic NW12 PDF](https://www.jetstar.com/_/media/Jetstar%20Australia/Files/PDF/Flight%20Schedules/NW12_Timetable_Domestic.pdf)
is dated **9 October 2012**, valid **28 October 2012–30 March 2013**. Its internal
dates determine coverage; recent web indexing dates are irrelevant. The dated
week is within that period, with adjacent origin-local departure dates retained
for overnight and cross-timezone flights.

The source contains **568 parseable schedule rows**. **Thirteen rows on page 3**
have malformed flight identifiers or date serials in printed fields. They are
excluded, rather than assigning guessed flight numbers or dates. This makes
coverage partial, particularly in the Sydney–Melbourne direction. Every retained
flight has its source PDF page in the prepared reference. Equipment is the
published A320/A321 type, rather than an observed aircraft registration.

The prepared gzip is `data/reference/australia_flights/2013-03-04.json.gz`, about
29 KB. It contains 1,451 departures in the selected Melbourne-time week, plus
adjacent departure dates (1,871 source occurrences in the prepared file).
It does not bundle the PDF. Source URLs and SHA-256 checksums are recorded in the
reference and [source register](data/sources/australian_flights_feasibility.json).
The publisher's [terms](https://www.jetstar.com/au/en/terms-of-use) remain linked;
this personal pilot makes no claim of an open-data licence or a separate
publisher agreement.

Rebuild using a preparation-only PDF reader:

```bash
.venv/bin/python -m pip install --target .cache/flight-tools pypdf==6.21.2
PYTHONPATH=.cache/flight-tools .venv/bin/python scripts/prepare_australian_flights.py
```

The script verifies pinned source checksums before parsing, checks parsed and
malformed row totals, applies effective-date/weekday restrictions, resolves each
airport clock to UTC, checks domestic durations and rejects duplicate operating
flight identities. The runtime app uses the prepared gzip and existing replay
HTTP cache; it needs neither pypdf nor a flight-data API. Override the prepared
file with `SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE`.

## Airports, time and paths

Airport names, IATA/ICAO codes and coordinates come from the public-domain
[OurAirports data](https://ourairports.com/data/), pinned to commit
`3b10d0b967cc04c62eb6411939e4e9936a88e701` on **24 October 2026**. The full CSV
contains 2,795 Australian records and 157 non-closed airports marked for scheduled
service, with valid coordinates and unique nonempty IATA codes. The pilot uses
only its 18 source-matched airports. The scheduled-service flag is not used to
invent flights. Modern airport names/coordinates are a geographic reference,
not a reconstruction of all 2013 naming or infrastructure.

OurAirports has no airport timezone column. The preparation script explicitly
maps these 18 airports to IANA zones, preserving Queensland's lack of daylight
saving, Adelaide's half-hour offset and Darwin/Perth differences. It rejects
ambiguous or nonexistent local clocks. Arrival date rollover is resolved using
UTC ordering and checked domestic flight duration, rather than comparing local
clock numbers alone.

The national day runs **00:00–00:00 Melbourne time**. Flights overlapping that
window remain visible, including departures from the preceding origin-local day.
Overview counts only departures owned by that Melbourne day. Boards show their
window and event clocks in airport-local time; selected-flight details show each
endpoint in its own timezone. Scheduled block times are not labelled as actual
takeoff/landing times. Gates, delays, fares, passenger loads and codeshare
inventories are not provided by this source.

Each unique directional airport pair shares a sampled great-circle path, tagged
`quality=illustrative`. Unresolved transit paths continue to stay hidden. Plane
icons are drawn locally in canvas, rotate along the path and keep a crisp outline
in all five themes. Airport codes use locally rendered labels without an extra
font service. Airport connections appear on selection to limit clutter.

## Validation

- Python checks cover the actual JQ402 Sydney–Gold Coast source clocks, operating
  days, Adelaide/Darwin and Perth/Melbourne overnight differences, DST ambiguity,
  all seven prepared days, unique flights, carry-ins, paths and cached downloads.
- JavaScript checks cover terminal arrivals, date-window ownership, illustrative
  movement, headings, local clocks and midnight Overview totals.
- `tests/browser_australian_flights.py` exercises actual airport clicks, moving
  planes and seeking, local boards, arrival paging, journey return, fullscreen,
  mobile, themes, Indonesian, the last date, station visibility and Melbourne
  return. Screenshots are saved to `.cache/australia-flights-*.png`.

The source register also retains the alternatives investigated: Rex/FlyPelican
published regional timetables, Qantas, BITRE monthly statistics, Airservices,
OpenSky, ADSB.lol and Aviationstack. These are not mixed into this pilot. BITRE
aggregates do not reconstruct flight times, and historical tracking archives
would need their own recorded-flight experience and coverage validation.
