# NYC Subway and Staten Island Railway: implementation, sources and future networks

## Implemented baseline

- City `nyc`, display name New York City, timezone `America/New_York`; **15 December 2025–18 January 2026**, five full weeks. Uses the existing city selector, prepared-city loader, browser animation, filters, details, colours, fullscreen and themes. Overview remains Melbourne analysis.
- The archive contains 28 subway route IDs: regular numbered/lettered services plus 6X, 7X, FX and three distinct shuttle IDs `GS`, `FS`, `H`. Do not merge all three shuttles under their common short name `S`; their full route labels remain distinct. Weekday-only services must not be fabricated on weekends or holidays.
- Also includes `SI` / route type 2 (Staten Island Railway) as its own Transport option, using the historical feed colour `#08179C`. The initial view includes Staten Island. Other rail operators and buses remain excluded. Train passenger counts and passenger controls remain unavailable.
- `scripts/prepare_nyc_replay.py` builds `data/reference/nyc/2025-12-15.json.gz` (**3,673,177 bytes**). `SUNTRAIN_NYC_REFERENCE` overrides the loader path. Downloads and audit samples in `.cache/nyc-archives/` are ignored local files.

## Schedule availability checked on 17 October 2026

1. [Official MTA developer page](https://www.mta.info/developers): regular subway GTFS is a normal timetable, with most temporary service changes excluded. The supplemented feed is updated hourly and mainly covers changes over the following seven days. Today's feed is not a reconstruction of 2024.
2. [Transitland historical version `c656286b…`](https://www.transit.land/feeds/f-dr5r-nyctsubway/versions/c656286bb5cd15780d5414b25797b9fd1cf140cb): metadata spans 1 April–22 June 2024. The ZIP download returned HTTP 401 without archive credentials. It would not cover the entire requested period by itself even with access. No authenticated account was created or subscription purchased.
3. [MyTransit archive README](https://s3.amazonaws.com/data.mytransit.nyc/README.HTML): actually downloaded. Public S3 folder listings show GTFS and stop-distance folders for **2014, 2015 and 2016**, not 2024. Object modification dates in June 2024 do not mean the schedules describe 2024. The bucket is maintained by an independent archivist, not MTA.
4. [MobilityDatabase NYC Subway catalog](https://mobilitydatabase.org/feeds/gtfs/mdb-516): public later ZIPs were downloadable. The [1 November 2025 capture](https://files.mobilitydatabase.org/mdb-516/mdb-516-202511010043/mdb-516-202511010043.zip) was audited but **rejected for this replay**: 2,274 subway trip records had blank shape IDs.
5. [5 December 2025 capture](https://files.mobilitydatabase.org/mdb-516/mdb-516-202512050000/mdb-516-202512050000.zip): downloaded, inspected and used. Its timetable begins **8 December 2025** and runs through **16 May 2026**. Every selected subway and Staten Island Railway geometry pattern matched the supplied shape with the existing 150 m threshold. Starting the replay on 15 December also keeps prior-day carry-ins inside this validated timetable.

The user allowed another reliable historical period. Do not relabel this fallback as 2024. Source URL, capture date, timetable validity and SHA-256 are stored in the prepared metadata. Archive selection must respect effective dates: a Dec 5 capture must not replace Dec 6 service when its calendars begin Dec 8.

## Geometry, calendars and memory

- NYC stop times and shape points lack native distance anchors. Reuse the ordered whole-journey projection from Boston's importer on each trip's own shape; preserve branch IDs and express/local stop sequences. Missing or inconsistent shapes stay as gaps. Do not guess track offsets or fill missing geometry from unrelated routes/dates.
- Published shapes establish routing consistency, not independently verified physical express/local running tracks. Preserve this limitation in the UI and documentation. No GPS or real-time feeds are used.
- Retain midnight and extended GTFS times, calendar exceptions, 03:00 business windows and carry-in visibility. GTFS service zero is local noon minus 12 elapsed hours. `occurrences()` uses sorted window boundaries to avoid repeatedly scanning the whole period for each trip instance.
- The five-week baseline has 4,793 shared schedule patterns (4,785 subway + 8 Staten Island Railway). Keep trip stop arrays shared in `hydrate()`, retain one selected day, and do not expand schedules for every trip on the main thread. Source ZIPs are not sent to the browser.
- Preserve city-and-date checks during switches, especially when NYC and Chicago dates overlap. Cross-year date badges must retain both years.

## Passenger datasets: verified, optional, not loaded

| Source | Actual fields / successful sample | Appropriate use |
| --- | --- | --- |
| [MTA Subway Hourly Ridership 2020–2024](https://data.ny.gov/d/wujg-7c2s) | Public API returned 27 May 2024 station-complex/hour rows. Fields include `transit_timestamp`, complex ID/name, mode, payment method, fare category, ridership, transfers and coordinates. | A separate hourly station-complex entries map. Aggregate fare/payment strata without double-counting and inspect transfer definitions. Do not infer individual train loads, boardings or alightings. |
| [MTA Subway OD Ridership Estimate 2024](https://data.ny.gov/d/jsu2-fbtj) | Public API returned June 2024 records with year/month, day of week, hour, origin/destination complex IDs, coordinates and `estimated_average_ridership`. | Monthly/day-of-week/hour estimated travel patterns. The representative timestamp is not an individual observed journey or exact daily flow. |

These supplied datasets cover 2024 and do not match this replay's 2025–2026 period. Keep them separate. For a future heatmap, verify the official dataset covering the chosen replay dates, use station-complex IDs and locations, and label entries by hour. Do not reuse Melbourne's exact scheduled-train-boarding rolling window semantics or allocate station totals to passing trains. Passenger features must not delay schedule integration.

## Other NYC networks

**Commuter follow-up:** LIRR, Metro-North and NJ Transit rail are now available in **United States → Regional / commuter rail**, for **12–18 October 2026**. They use their own feeds and are not duplicated into this older NYC Subway/SIR bundle. See [US commuter notes](US_COMMUTER_EXPANSION_NOTES.md). The original source-audit table below records the earlier investigation; MTA buses remain future scope.

| Network | Starting source | Follow-up issues |
| --- | --- | --- |
| Staten Island Railway | **Implemented** from `SI` / route type 2 in the same pinned MTA ZIP. | All 35 days have scheduled services, no omissions or geometry gaps. Subway occurrences remain unchanged. Separate Transport filter; St George–Tottenville paths retained. |
| LIRR | [Official current GTFS](https://rrgtfsfeeds.s3.amazonaws.com/gtfslirr.zip), linked by MTA. | Obtain a dated historical version; rolling timetables include near-term changes and do not establish 2024 service. Preserve branches, terminals, express patterns and agency IDs. |
| Metro-North | [Official current GTFS](https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip), linked by MTA. | Historical archives and geometry must be checked. MTA states Port Jervis and Pascack Valley schedules are in NJ TRANSIT GTFS, so the MTA ZIP alone does not imply complete coverage. |
| MTA buses | [MTA developer page](https://www.mta.info/developers) lists Bronx (`gtfs_bx.zip`), Brooklyn, Manhattan, Queens, Staten Island and MTA Bus Company (`gtfs_busco.zip`) packages on `rrgtfsfeeds.s3.amazonaws.com`. | Archive all needed packages for one period; borough/operator coverage overlaps. Preserve feed namespaces, prevent duplicate trips and audit calendar boundaries and route changes. Quarterly regular schedules omit most temporary detours. Choose MTA/NYC bus colours rather than Melbourne orange. |

LIRR and Metro-North are implemented in the separate United States commuter layer. MTA buses remain a future addition. Staten Island Railway is implemented in NYC.

## Data terms and validation

[MTA data terms](https://www.mta.info/developers/terms-and-conditions) permit local hosting of feed data and require applications to serve data from their own servers. Keep raw downloads local and provenance intact; serve prepared data through SunTrain. Do not imply MTA sponsorship, completeness or guaranteed accuracy. No MTA logos, route badges or map artwork are used; [MTA's developer page](https://www.mta.info/developers) distinguishes data use from licensed brand assets.

Run the full Python / JavaScript suite, audit all 35 dates, and browser-check express/local route filters, all three shuttles, holidays, overnight services, year boundaries, shared schedules, mobile, themes, fullscreen, playback and switching back to other cities. Existing Boston Silver Line must remain silver and Melbourne passenger tools must remain available.
