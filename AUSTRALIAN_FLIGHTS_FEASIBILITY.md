# Australian domestic flights

Choose **Australia · Flights** for **2 November 2026**. The expanded snapshot has
**36 airports**, **1,170 scheduled departures** in the Melbourne calendar day and
**19 overnight carry-ins**. Visible carriers are Qantas, Virgin Australia,
Jetstar, Rex, Link Airways and Alliance Airlines. Search coverage is partial.

**MEL and AVV are independent airports** throughout: query inputs, IATA identity,
coordinates, route keys, flight identifiers, markers and arrivals/departures.
Searches never use a city name as an airport identifier. The snapshot has seven
AVV departures and seven arrivals; MEL has 235 departures and 234 arrivals,
including overlapping journeys at the calendar boundary.

Planes use airline colours. Airport markers or code labels open their boards,
show connections and mute unrelated planes. Boards offer Departures / Arrivals,
expanded view, paging and flight previews. Previewing preserves the replay clock;
Go to departure / arrival explicitly seeks and pauses. More filters → Operator /
feed selects airlines without downloading another timetable. Smaller national
plane icons keep the busier corridors readable; zooming reveals more detail.

## Collection and provenance

The source is the rendered public [Google Flights](https://www.google.com/travel/flights)
search page, captured **24 October 2026** for **2 November 2026**. Queries specify
one-way, nonstop travel between exact IATA codes. The collector reads JSON arrays
already embedded in those pages; it never executes the source data as code and
requires no API key or signed-in profile.

The prepared file is `data/reference/australia_flights/2026-11-02.json.gz`
(**46,306 bytes**). It contains **1,623 unique flight occurrences** across the
queried local dates, including adjacent dates needed for carry-ins. Runtime
selection clips these to the selected Melbourne day. All **271 planned
airport/date queries** were captured; none remains uncollected. Empty query
results mean no matching flights were returned, rather than proving that an
airport pair has no services.

Each query retains its exact airport codes/date, source URL, capture timestamp,
response-data SHA-256 and result status in the bundle's `metadata.queries`.
The [source register](data/sources/australian_flights_feasibility.json) records the
selected source and earlier alternatives. Search options for the same flight
are deduplicated by local departure date, flight number and airport pair;
conflicting schedule records are rejected. Flight numbers, aircraft descriptions
and endpoint dates/times come from the source. No departure times are generated
from route frequencies. Bookable search results may omit flights and airlines;
this is not a complete operational movements feed or observed tracking.

Rebuild from the saved local query cache, or resume uncaptured queries:

```bash
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py --prepare-only
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py
```

Collection uses installed Chrome and preparation-only Playwright, two concurrent
pages by default, a pause between queries and an ignored on-disk cache. Access
challenges stop collection. The runtime app reads the prepared snapshot through
the existing replay cache and makes no requests to Google during playback.

## Airports and time

Airport names, IATA/ICAO codes and coordinates use the public-domain
[OurAirports data](https://ourairports.com/data/), pinned to commit
`3b10d0b967cc04c62eb6411939e4e9936a88e701`. Its checksum is verified before the
36 individual airports are matched. Airports have explicit IANA zones, including
**Australia/Broken_Hill**, Queensland's lack of daylight saving, Adelaide's
half-hour offset and Darwin/Perth differences. Every converted flight duration
must match the duration reported by the search result.

Boards and flight details show airport-local clocks. The national timeline is
**00:00–00:00 Melbourne time**. Prior local departure dates are searched where
that timezone is behind Melbourne, so overnight flights can carry into the day.
Overview counts departures owned by the selected Melbourne calendar day.
Great-circle paths illustrate scheduled block-time progression; they are not
actual tracks or takeoff/landing observations. Live delays, gates and passenger
loads are outside this snapshot.

## Validation and the earlier pilot

Python tests cover exact MEL/AVV isolation, published flight identity, zero-minute
source encoding, deduplication/conflicts, Broken Hill offsets, duration checks,
all carriers, airport identity, source-query completion and cached downloads.
Browser checks cover airline filtering, independent MEL/AVV boards, map clicks,
plane motion, local arrivals, expanded boards, mobile, themes, Indonesian,
Overview and returning to Melbourne. Existing transit tests remain applicable.

The earlier Jetstar-only **4–10 March 2013** bundle remains in the repository for
reproducibility and regression tests. It is not the active flight view. Its
preparation script is `scripts/prepare_australian_flights.py`, using the pinned
[2012 Jetstar PDF](https://www.jetstar.com/_/media/Jetstar%20Australia/Files/PDF/Flight%20Schedules/NW12_Timetable_Domestic.pdf)
and preparation-only `pypdf==6.21.2`. That older parser retains 568 valid schedule
rows and excludes 13 malformed rows. It is not mixed into the November snapshot.
