# Victorian buses — Melbourne view

The **Melbourne** location includes scheduled Victorian public buses and coaches
from the same **27 May–30 June 2024** period as the existing tram replay. Its
initial map remains metropolitan Melbourne; **Fit selection** fits the chosen
routes, including regional and cross-border termini. Buses retain orange
(`#FF8200`). Train and tram coverage is unchanged.

## Sources and scope

The five dated MobilityDatabase PTV archives listed in
`scripts/prepare_transit_period.py` supply the original calendars, exceptions,
stop times, stops and trip shapes. The most recent snapshot captured on or before
each replay date is selected. No current timetable is substituted for 2024.

| Historical branch | Replay operator / feed | Scope |
| --- | --- | --- |
| 3 | PTV tram | Existing trams |
| 4 | PTV bus | All published trips, without the old Melbourne bounding box |
| 5 | V/Line coach | Regional coach journeys, including cross-border calls |
| 6 | PTV regional bus | Regional town and country buses |
| 7 / 8 | PTV bus | TeleBus / old night-bus schedules, where actual trips exist |
| 11 | SkyBus | Airport buses represented in the archived schedule |

The label “all buses” means services actually represented in these public
archives. Private charters, tours, school contracts or demand-responsive trips
without published departures are not invented. The feed labels identify source
branches rather than individual contracted bus companies. The operator filter
can isolate regional buses, coaches or SkyBus without adding new UI controls.

Timetables and geometry: Department of Transport and Planning / Public Transport
Victoria, [GTFS Schedule](https://opendata.transport.vic.gov.au/dataset/gtfs-schedule),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). SunTrain selects dates,
converts and shares stop schedules, clips source shapes using stop-distance
anchors and compacts geometry. Prepared snapshot metadata retains archive URLs,
capture dates and SHA-256 hashes of each original branch ZIP. Missing geometry
remains a gap. No bus passenger loads are available.

## Rebuild and preserve

```sh
./.venv/bin/python scripts/prepare_transit_period.py
```

Legacy caches containing only branches 3 and 4 are downloaded again to obtain
the other branches. Raw ZIPs remain ignored in `.cache/`; only compact references
are committed. Trips are namespaced by branch to avoid identifier collisions.
Source calendars and clocks, including times beyond midnight, are preserved;
the replay timeline extends for coaches finishing beyond the next 03:00.
Non-empty frequency templates fail preparation until explicitly supported.

Buses remain optional under **Transport**. Opening Melbourne with trains skips
tram/bus references. Only the selected date and transport modes are sent to the
browser; stop sequences, timing vectors and geometry remain shared. Keep this
representation when extending dates or adding sources.

## Validation

All 35 dates retain the original 819,295 tram/bus occurrences and add 171,253
occurrences. Preparation omits no invalid trips in these snapshots. On 27 May,
the bus selection includes 23,003 PTV bus journeys, 5,072 regional bus journeys,
280 coaches and 257 SkyBus journeys. Regional coverage was checked on every date,
including Mildura, Ballarat, Bendigo, Geelong and Warrnambool.

65 Python tests and 44 JavaScript tests passed. Browser checks covered the metro
starting view, statewide fit, orange markers, Mildura route geometry and stop
details, operator filtering, Overview, playback, themes and returning to trains.
