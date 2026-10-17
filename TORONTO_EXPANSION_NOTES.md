# Toronto expansion notes

## Implemented scope and source

Toronto initially covers **5–11 October 2026**, one complete Monday–Sunday week, in `America/Toronto` local time. Include TTC subway Lines **1, 2 and 4**, and the two rapid transit light rail Lines **5 and 6**. Streetcars (including night routes), replacement buses, other buses, GO Transit and UP Express are excluded. Line 3 is not invented from its old name or replacement bus service.

The [official City of Toronto merged GTFS catalogue](https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/) and its [CKAN metadata API](https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=merged-gtfs-ttc-routes-and-schedules) were accessible. The [actual ZIP](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b811ead4-6eaf-4adb-8408-d389fb5a069c/resource/c920e221-7a1c-488b-8c5b-6d8cd4e85eaf/download/completegtfs.zip) downloaded on **18 October 2026, Melbourne local date**: **84,337,545 bytes**, SHA-256 `5e0191d59cb991b6c88ba9c1a5f2ca93a5a064a4d258dbc7ba93801d15f3dfca`. The catalogue reports its last modification on **30 September 2026**. `feed_info.txt` identifies version **S1000542**, valid **30 September–31 October 2026**. The chosen replay week and adjacent service days are inside that interval.

This is an official published timetable applied to dates in its validity range, not a recording of actual movements or every temporary closure. A 2024 timetable was not used or substituted: this pilot intentionally uses the verified October 2026 feed. TTC confirms [Line 6 opened in December 2025 and Line 5 in February 2026](https://www.ttc.ca/news/2026/October/TTC-seeks-rider-feedback-on-Lines-5-and-6). They must not be backdated into a 2024 expansion.

The [older TTC catalogue](https://open.toronto.ca/dataset/ttc-routes-and-schedules/) also downloaded successfully (36,417,654 bytes) and points users toward the newer merged feed. The merged feed is used here; it includes platform/station structures, paths and levels. Do not combine the older and merged feeds indiscriminately: trip IDs and service definitions differ even where the railway shapes share IDs. [MobilityDatabase mdb-732](https://mobilitydatabase.org/feeds/gtfs/mdb-732) lists historical copies of the older feed, but it is not the source of this bundle.

## Preparation and geometry

`scripts/prepare_toronto_replay.py` reuses existing calendar, CSV, hash, geometry matching, simplification and compact-reference helpers. It selects agency **TTC**, subway type **1** with short names **1/2/4**, and light rail type **0** with short names **5/6**. Type 0 alone would incorrectly include the streetcar network; route numbers alone would incorrectly include replacement buses. Route labels, colours, destinations, direction IDs and stop sequences come from this feed.

No `frequencies.txt` is present. Explicit trips and stop times are retained, with extended hours and 03:00–03:00 business windows. Vehicles crossing a boundary remain visible on either side; there are no duplicate occurrences within one replay day. Relative stop schedules and railway paths are shared between trip instances. No raw GTFS ZIP is sent to the browser and Toronto loading does not query Melbourne's passenger warehouse.

Native stop/shape distances are checked where fully supplied. Otherwise the complete ordered station sequence must match the trip's own published shape within **150 m**. This preserves Line 1's U-shaped route through Union rather than drawing a shortcut between its northern arms. Invalid native anchors do not trigger a fallback to different geometry. Source shapes describe the published route, without a guarantee of individual running-track accuracy.

**Known geometry gaps, bounded deliberately:** two Line 1 journey variants do not pass the existing checks. Shapes `1124792`, `1124988` and `1124969` share a Sheppard West–Vaughan variant whose starting platform is about **157 m** from its shape. Shape `1125018`, a St Clair–Vaughan variant through downtown, has a terminal native anchor about **306 m** from the Vaughan platform. These account for **30 source trip IDs**, or **16 scheduled occurrences per weekday, 4 Saturday and 10 Sunday** in this week. Their schedules remain available and markers appear at stations; between-stop positions and route highlights remain unresolved. No tolerance was widened and no connector was drawn. The map's quality note and selected-service details explain the gaps. Resolve them only from validated source geometry, without delaying other city work to chase these isolated records.

The bundled week has **138 shared patterns** and **1,853–2,737 services per day**, with **no omitted trips**. The bundle is about **0.16 MB**. All five lines are scheduled on all seven dates. Source metadata, dates, hash and gap audit are embedded in `data/reference/toronto/2026-10-05.json.gz`.

## Licence and attribution

The catalogue identifies the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/), which permits adaptation and redistribution with acknowledgement. Retain **“Contains information licensed under the Open Government Licence – Toronto”**, link the licence, and credit TTC / City of Toronto. The app displays these notices beside the map. The CKAN raw field says `license_id=notspecified`; the public catalogue explicitly links the Toronto licence, so do not describe this as Creative Commons. No official logos, maps or endorsement are used.

## Extending the timeframe next time

1. Preserve the validated source ZIP at `.cache/toronto-audit/completegtfs.zip`. The official download URL is mutable, not a permanent archive. The script rejects changed bytes; a later download may no longer reproduce this snapshot. The committed prepared reference remains sufficient to run the current week without the source ZIP.
2. For dates inside this feed's validity, inspect the calendars and exceptions for the full requested interval **and adjoining service days**. In particular, **12 October has holiday exceptions**, so do not copy weekday departures into that date. For dates outside the feed, obtain and validate additional historical snapshots first. Do not stretch this timetable backwards to 2024 or forwards beyond its valid dates.
3. Update `SOURCE` dates/hash if appropriate, `dashboard/cities.py`, the `TORONTO_PATH` default in `dashboard/replay.py`, tests and README. Rebuild the reference. `SUNTRAIN_TORONTO_REFERENCE` supports an alternate prepared file.
4. Check every date for active lines, unique occurrences, ordered stop times, overnight carry-ins, direction labels and geometry gaps. Use Toronto timezone rules rather than a fixed UTC offset, particularly for extensions across the November daylight-saving change.

## Streetcars, buses and other rail later

The downloaded merged feed contains TTC streetcars and buses with stops, shapes and calendars. They have **not** been prepared or verified for replay in this pilot. Add explicit route-type/operator scoping, keep streetcars distinct from rapid transit Lines 5/6, retain the night network's calendar/extended-hour times, and identify rail replacement buses as buses. Stream/filter the large source files during preparation and continue sharing stop patterns; never expand every trip's schedule on the UI thread.

[Metrolinx's official open-data page](https://www.metrolinx.com/en/about-us/open-data) lists separate GTFS datasets for **GO Transit** and **UP Express**, under its own Ontario–Metrolinx licence. Their historical files, date compatibility and geometry remain to be validated before implementation. GO's feed can contain both trains and buses; do not enable every route by operator name alone.

## Passenger data later

TTC's [Subway Ridership 2023–2024 report](https://www.ttc.ca/-/media/Project/TTC/DevProto/Documents/Home/Transparency-and-accountability/Subway-Ridership-20232024.pdf) describes typical weekday line boardings and station-platform travel, aggregated over September 2023–August 2024. It is a possible static station-demand reference with the correct period and definitions, not October 2026 daily/hourly observations or individual train loads. No matching individual-train passenger dataset was obtained. Passenger sizing and heatmaps remain unavailable for Toronto; the Overview remains Melbourne analysis.
