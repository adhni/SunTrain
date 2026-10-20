# United States intercity railway expansion

## Implemented

Select **United States** for **12–18 October 2026**: Amtrak passenger trains nationwide and Brightline Florida, with operator and route filters. The week contains **2,309 departures**, **453 shared timing patterns** and a **2.48 MB compressed reference**. No connecting buses, MARC or Shore Line East commuter trains are included, even though those services appear in Amtrak's feed. Existing US city views retain their own timetables without duplication.

This describes the **intercity default**. The [optional commuter expansion](US_COMMUTER_EXPANSION_NOTES.md) now adds the other requested commuter operators, including MARC from its own feed, under **Regional / commuter rail**. MBTA stays in Boston. The intercity file and default service counts remain unchanged.

Amtrak coverage includes the source's Acela, Northeast Regional, long-distance sleepers, state-supported services, Canadian extensions and intermediate stops. Keep the actual 2026 names: **Floridian** and **Silver Meteor**, rather than inventing a separate historical Silver Star service. The Canadian Maple Leaf section is supplied separately under VIA Rail and remains a separate scheduled section, not a claim that two vehicles run. Brightline includes Miami, Aventura, Fort Lauderdale, Boca Raton, West Palm Beach and Orlando, using the feed's yellow colour.

All clocks and stop times use **America/New_York (Eastern time)**, explicitly stated in the location description and replay note. GTFS arrival/departure times use the agency time zone, not each station's `stop_timezone`; converting each stop again would corrupt western journeys. For example, train 5 departs Chicago at 15:00 Eastern / 14:00 Central and arrives Emeryville two days later at 19:57 Eastern / 16:57 Pacific. Original train numbers and dwell times are retained.

Each occurrence belongs to the single **03:00–03:00 Eastern window containing its origin departure**. Playback extends to that cohort's final arrival, including journeys lasting several days. These views show that day's departing journeys, not every train already underway from earlier departure days. Positions are schedule estimates; passenger counts, observed delays and live tracking are unavailable.

## Downloaded and validated sources

| Operator | Actual archived ZIP | Feed validity | Assigned GTFS service dates |
| --- | --- | --- | --- |
| Amtrak | [11 October archive](https://files.mobilitydatabase.org/mdb-11/mdb-11-202610110034/mdb-11-202610110034.zip), version 20261010 | 11–17 October 2026 | 11–17 October |
| Amtrak | [18 October archive](https://files.mobilitydatabase.org/mdb-11/mdb-11-202610180152/mdb-11-202610180152.zip), version 20261017 | 18–24 October 2026 | 18–19 October |
| Brightline | [11 October archive](https://files.mobilitydatabase.org/mdb-1126/mdb-1126-202610110040/mdb-1126-202610110040.zip) | No feed_info; explicit calendar 9 October 2026–6 August 2027 | 11–19 October |

The adjoining service dates support the business-day boundary; they are not extra selectable days. Original downloads were actually opened, their calendars inspected and SHA-256 hashes pinned in `scripts/prepare_american_replay.py`. Amtrak's broad calendar cannot override its narrower `feed_info` validity. These are authentic dated snapshots, not current schedules relabelled as 2024.

Official sources: [Amtrak GTFS](https://content.amtrak.com/content/gtfs/GTFS.zip), [Brightline GTFS](https://feed.gobrightline.com/bl_gtfs.zip). Archive catalogues: [Amtrak](https://mobilitydatabase.org/feeds/gtfs/mdb-11), [Brightline](https://mobilitydatabase.org/feeds/gtfs/mdb-1126).

## Geometry and limitations

Use supplied GTFS railway shapes and ordered station projection within 150 m. Amtrak trips missing their own shape may use a shape supplied for the **same route in the same dated snapshot**, only where stations match in journey order. An isolated off-shape station no longer discards otherwise validated legs. Unsupported sections are empty paths: vehicles disappear between those stops rather than drawing straight shortcuts. No national OSM download or new routing infrastructure is needed.

Of **5,598 legs across shared patterns**, **4,823** match supplied shapes and **775** remain gaps. This counts pattern legs, not distinct physical track sections or the percentage of daily trains. There are **2,157 validated shared paths**. All Brightline legs match; Amtrak has unresolved sections, including the Canadian Maple Leaf section. Some affected trips still animate on their verified portions. Full track coverage and real-time accuracy are not claimed.

## Alaska Railroad: investigated, not enabled

The [official GTFS page](https://www.alaskarailroad.com/GTFS) links a dated [10 April 2026 ZIP](https://alaskarailroad.com/sites/default/files/GTFS/GTFS-20260410.zip). Multiple actual download attempts timed out from this environment. This is an access failure, not evidence that Alaska publishes no GTFS.

During the commuter follow-up, an [older official-feed archive via the National Transit Database / MobilityDatabase](https://files.mobilitydatabase.org/ntd-41/ntd-41-202412090019/ntd-41-202412090019.zip) **did download and was inspected**: seven routes, 21 stops, declared validity **1 January 2024–1 May 2025**, with summer and winter service calendars. It has **no shapes.txt**. This closes the older-timetable access gap but does not supply railway paths or establish 2026 service. It remains unenabled pending usable railway geometry, rather than displaying every journey as a straight connector.

[Transitland's indexed version](https://www.transit.land/data/feeds/f-alaska~railroad~corporation/versions/dbf873bd099561ab9804d3425f737c6b525ac1a3) describes seven routes and 21 stops, but reports feed validity ending **1 May 2026**, despite calendars extending later. Metadata alone cannot justify replaying summer 2026 or claiming a successful historical download. Older indexed feeds also need a geometry audit. Alaska's [official schedules](https://alaskarailroad.com/ride-a-train/schedules) distinguish seasonal services; do not treat Denali Star, Coastal Classic or Glacier Discovery as year-round trains.

Next step: retain that validated older ZIP, select a week inside its true calendar/metadata validity, and match stations to verified railway paths. The [FRA railway GIS page](https://railroads.dot.gov/rail-network-development/maps-and-data/maps-geographic-information-system/maps-geographic) provides a possible federal railway geometry source; its Alaska coverage and station matching have not been audited yet. Use **America/Anchorage** in a separate Alaska replay if its dates differ. Do not infer individual departures from marketing headways or add unvalidated summer journeys just to populate the map.

## Rights and attribution

Amtrak's **7 January 2026 FOIA response, request 26-FOI-00215**, states GTFS use needs no licence, including commercial use, provided the use benefits Amtrak and drives consumer engagement. The [actual response](https://github.com/user-attachments/files/24483097/Response.-.26-FOI-00215.pdf) was downloaded and read. This is not a Creative Commons licence or public-domain declaration. The raw letter is not committed because it contains the requester's personal contact details. Retain Amtrak and VIA Rail attribution and independent schedule-estimate descriptions.

Brightline publicly publishes its GTFS and [describes its GTFS distribution partnership](https://www.gobrightline.com/press-room/2023/brightline-partners-with-distribusion-technologies). No explicit open-data or general redistribution licence was verified. The reference identifies operator-published schedule data with rights retained, links the [website terms](https://www.gobrightline.com/website-terms-of-use), and asserts no Creative Commons licence. Public availability does not establish unrestricted reuse rights; review specific feed permissions before wider third-party redistribution. MobilityDatabase's catalogue licence must not be substituted for either operator's feed terms. No operator logos or map artwork are included.

## Rebuild and later expansion

Run `./.venv/bin/python scripts/prepare_american_replay.py`. Sources stay in ignored `.cache/us-intercity/`; the prepared reference is `data/reference/us_rail/2026-10-12.json.gz`. The shared rail converter performs calendar/hash checks, compaction and snapshot assignment. Runtime uses existing location, overview, filters, details and map playback. Schedules remain shared in the browser; trips do not carry expanded stop arrays. To expand dates, obtain archives covering the entire period and adjoining service dates, validate feed metadata, and keep each occurrence assigned to one departure day. Explicitly test daylight-saving changes before spanning them.

The requested commuter operators are now implemented through their own feeds; see the [commuter notes](US_COMMUTER_EXPANSION_NOTES.md) for source pins, route scope and limitations. Existing Washington Metro and BART views already cover their enabled networks. Other metro, light rail and bus systems remain outside this change. Passenger reports and annual route totals, if added later, must not become invented train loads.
