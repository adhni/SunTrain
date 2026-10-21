# United States commuter and regional railway expansion

## Implemented scope

In **United States**, select **Regional / commuter rail** under Transport. It adds the following networks for **12–18 October 2026**, using the existing map, route/operator/station filters, service details, overview, themes and playback controls. No new selection screen or live service is introduced.

| Region | Included |
| --- | --- |
| New York / New Jersey | LIRR's branches and terminals; Metro-North Hudson/Harlem/New Haven and branches; NJ Transit rail, including Port Jervis and Pascack Valley |
| Pennsylvania / Maryland / Virginia | SEPTA Regional Rail; MARC Brunswick/Penn/Camden; VRE Manassas/Fredericksburg |
| Chicago / Northwest Indiana | Metra's 11 source lines; South Shore Line's Lakeshore and Monon corridors |
| California | Caltrain local/limited/express and South County Connector; all seven Metrolink lines; ACE; COASTER; SMART |
| Washington | Sounder N/S lines, using published explicit departures |
| Florida | Tri-Rail mainline and Downtown Miami Link; SunRail |
| Texas | DART's Trinity Railway Express and Silver Line; Trinity Metro TEXRail |
| New Mexico / Utah | Rail Runner; FrontRunner |

**MBTA is already implemented in Boston and is neither downloaded nor stored again.** The existing NYC Subway/SIR, CTA and BART city files are also untouched. The new United States view does not duplicate their metro/light rail/bus services. Metro-North's west-of-Hudson services appear only through NJ Transit's GTFS, avoiding duplicate sections from overlapping operators. Amtrak's incidental MARC data remains excluded; MARC comes from its own operator feed.

Source `route_type=2` plus explicit agency scoping selects trains. **TEXRail is a deliberate exception:** Trinity Metro encodes that commuter train as type 0; only the pinned TEXRail route ID is allowed. This does not enable other type 0 routes. NCTD SPRINTER, DART light rail/streetcars, Seattle Link, buses and rail replacement buses remain excluded.

## Size, loading and clocks

The optional week has **29,922 departures**, **3,352 shared timing patterns**, **1,216 source station/platform records**, **3,354 shared paths**, and a compressed size of about **1.18 MB**. Daily counts, Monday through Sunday: **4,775; 4,805; 4,805; 4,806; 4,815; 3,040; 2,876**. With intercity trains enabled too, Monday has **5,108** services and Sunday **3,198**.

Amtrak/Brightline still open first: their **2.48 MB** file, schedules and default counts are unchanged. The commuter bundle is not opened or included in the HTTP cache identity until selected. Commuter-only playback does not open the intercity file. Browser services refer to shared stop/timing patterns and never receive copied stop arrays. No new warehouse, API service or credential is needed at runtime.

All replay clocks and stop tables remain **Eastern time**. Preparation reads each agency's actual GTFS service-day zero in Eastern/Central/Mountain/Pacific time, then converts the same instants into the Eastern replay window. It does not relabel western wall clocks as Eastern. For example, COASTER 620 starts Oceanside at **05:00 Pacific / 08:00 Eastern**. An overnight Caltrain train at **00:05 Pacific / 03:05 Eastern** belongs to that Eastern departure day. Relative dwell/travel times remain unchanged.

Each occurrence belongs once to the **03:00–03:00 Eastern** origin-departure window. The extra source service dates on either side support wrapped GTFS times. Do not copy weekday schedules to weekends: ACE, Sounder, SunRail and VRE have no regular weekend departures in this week; FrontRunner has no Sunday service. VRE also has **no trains on Monday 12 October**, matching its holiday exception. Late arrivals can extend the timeline beyond its normal end.

## Verified sources and reproducibility

All twenty source configurations, agency/route IDs, actual ZIP URLs, captures and SHA-256 hashes are pinned in [data/sources/us_commuter_sources.json](data/sources/us_commuter_sources.json). Raw ZIPs were downloaded, opened and checked; catalogue metadata alone was not treated as a timetable. Prepared metadata retains feed versions and validity. All selected calendars cover the actual October week; no weekday mapping from another year or operator was used.

Most inputs are actual dated [MobilityDatabase](https://mobilitydatabase.org/) copies of official feeds: LIRR `mdb-507`, Metro-North `mdb-524`, NJ Transit `mdb-509`, SEPTA rail `mdb-503`, MARC `mdb-468`, VRE `tld-61`, Metra `mdb-2854`, South Shore `mdb-585`, Caltrain `mdb-54`, Metrolink `mdb-96`, ACE `mdb-2684`, Sound Transit `mdb-268`, SMART `mdb-3222`, SunRail `mdb-626`, DART `mdb-152`, UTA `mdb-170`, and Trinity Metro `mdb-2890`.

Three old catalogue URLs needed replacement:

- **COASTER:** [NCTD's current static GTFS](https://lfportal.nctd.org/staticGTFS/google_transit.zip), version `2607-GTFS-Sept2026TripAdjustment (2026-09-01)`. No dated feed_info interval; explicit calendars cover the week. Only COASTER type 2 routes are selected.
- **Tri-Rail:** [current official ZIP](https://gtfs.tri-rail.com/gtfs.zip), version **10**, declares validity through **20 October 2026**, with active calendars covering the chosen week. The older `mdb-333` download was inspected and rejected: its base calendars end in August 2025. Future holiday exceptions are not proof of 2026 operation. The old official `/GTDF/Current/` URL returned 404.
- **Rail Runner:** Rio Metro's [official developer page](https://www.riometro.org/261/GTFS-Data) links [this operator-published ZIP](https://mjcaction.com/MJC_GTFS_Public/nmrailrunner_google_transit.zip). Version **20260727**, declared validity **15 July 2026–30 April 2027**. The stale 2023/2024 catalogue copy was rejected. Only agency `nmrr` / route `rr` is selected, excluding Rio Metro buses.

Those three mutable publisher files were captured **21 October 2026** and explicitly describe dates including this replay week; they are published schedule estimates, not observations of movements. A later changed download must fail its hash check until re-audited. Retain the local validated ZIPs if reproducible rebuilding is needed after the publishers update them. The committed prepared bundle is sufficient to run the site without downloading them again.

DART needs two snapshots: the **11 October capture** declares validity **9–18 October**, while the **15 October capture** begins service validity **19 October**. Only the latter supplies the adjoining 19 October service date. Its future timetable is not applied prematurely to 12–18 October. Broader calendar spans do not override narrower declared feed validity.

## Railway paths

Use only the selected source's supplied railway shapes, with the existing **150 m** ordered station checks. All **726 Metrolink pattern legs** now match its original geometry: its `shapes.txt` is present, but `trips.txt` omits `shape_id`. The manifest explicitly binds its seven line IDs to the corresponding `AV`, `IEOC`, `OC`, `RIVER`, `SB`, `VT` and `91` in/out shapes from that same dated ZIP. These candidates still must match the actual stop sequence. An unrelated line or later snapshot cannot supply a path.

Across shared patterns, **41,044 of 41,115 legs** match supplied shapes; **71 remain gaps**: **45 VRE, 13 MARC, 8 South Shore and 5 SEPTA**. This is a pattern-leg count, not distinct track sections or daily vehicle counts. VRE has 33 such legs across Fredericksburg variants and 12 across Manassas variants. Schedules remain available, but markers disappear between unsupported stops. No straight connector or widened tolerance hides these source limitations. Shapes establish plausible route alignments, not guaranteed platform/track assignments or observed movements.

## Source terms

Source-specific terms and operator credits are retained beside the map, including when commuter and intercity layers are combined. Prepared representations retain schedule instants and source identifiers. No operator logos, branded map artwork or passenger counts are included. Archive access is not a blanket Creative Commons licence.

- [MTA's data-feed terms](https://www.mta.info/developers/terms-and-conditions) allow hosting and redistribution from a non-MTA server, require independent/non-guaranteed descriptions, and restrict modifying the underlying data. SunTrain serves its own stored representation and preserves the scheduled instants and station sequence.
- [SEPTA's published agreement](https://www3.septa.org/developer/) grants use/reproduction/redistribution subject to its terms and reserves operator ownership. [Metra's linked licence](https://metra.com/sites/default/files/assets/developers/gtfs_license_agreement.pdf) is the applicable operator reference; fetching that document was blocked here, so no broader licence claim is made.
- ACE and SMART retain the [511 Data Disseminator Agreement](https://511.org/sites/default/files/pdfs/511_Data_Agreement_Final.pdf), including its registered-access, onward-terms and current-information conditions. [511's official API documentation](https://511.org/open-data/transit) explicitly offers monthly historical regional GTFS. SunTrain uses public dated copies and does not operate a new 511 API client or resell raw feeds; this does not remove the publisher's conditions.
- [Sound Transit's terms](https://www.soundtransit.org/help-contacts/business-information/open-transit-data-otd/transit-data-terms-use) include current-data/no-change, onward-terms and contact-address requirements. A fixed historical replay does not itself establish compliance with those current-data conditions; historical redistribution permissions were not separately cleared. Preserve this follow-up rather than describing the data as unrestricted open content.
- Other configurations retain the relevant operator/developer/data-terms links and operator rights. [Maryland](https://www.mta.maryland.gov/developer-resources), [Metrolink](https://metrolinktrains.com/about/gtfs/), [SunRail](https://corporate.sunrail.com/about-sunrail/gtfs-data-download/) and [Rio Metro](https://www.riometro.org/261/GTFS-Data) publish their data for third-party applications. Do not confuse the GTFS specification's licence with a licence for an operator's actual data.

## Rebuild, validation and later work

Run `./.venv/bin/python scripts/prepare_us_commuter_replay.py`. The source manifest controls scope, dates, hashes and the Metrolink shape associations; the shared rail converter handles calendars, service-day ownership, time-zone conversion and compaction. Raw/prepared intermediates stay in ignored `.cache/us-commuter/`. The committed file is `data/reference/us_rail/commuter-2026-10-12.json.gz`; `SUNTRAIN_US_RAIL_COMMUTER_RAIL_REFERENCE` overrides it.

Validation covers all seven dates, agency/mode exclusion, unique departure ownership, shared schedules, native clock conversion, daylight-saving fixtures, holiday/empty-weekend calendars, Metrolink's explicitly associated geometry and optional cache invalidation. Browser checks cover mode/operator filters, seven representative networks, Caltrain details with dates, 2,000× playback, Metra overview, Sunday closures and returning to intercity-only loading. Existing Java, Great Britain and Germany layer loading remains covered by regression checks.

Alaska remains pending verified railway geometry; an older authentic timetable is now available, as recorded in the [intercity notes](US_RAIL_EXPANSION_NOTES.md). The three light rail additions below are implemented separately. Other unlisted commuter operators and urban metro/light rail/bus networks remain future scope. Passenger data must retain its genuine aggregate level and cannot become invented train loads.

## TRAX, DART light rail and SPRINTER follow-up

Select **Light rail: TRAX / DART / SPRINTER** under Transport in **United States**. This adds **nine routes** for **12–18 October 2026**: TRAX Blue, Red and Green; S-Line; DART Blue, Green, Orange and Red; and SPRINTER. It uses the same operator controls, route filters, dated stop details, overview, clocks and map playback. Native Mountain/Central/Pacific times are converted to the existing Eastern replay axis. Intercity trains remain the default; this file is opened only when selected.

The separate compact bundle is **111,058 bytes**, with **74 shared patterns**, **7,961 departures across the week**, and daily counts **1,186; 1,185; 1,185; 1,185; 1,195; 1,173; 852**. It adds no duplicate commuter or intercity trips: source type 2 routes stay in the existing commuter layer. The old intercity and commuter bundles remain unchanged. MBTA remains in Boston.

Sources are inherited from the existing pinned manifest: **UTA 2 October capture**, **DART 11 October capture plus its adjoining-day 15 October release**, and **NCTD's validated September-adjustment feed captured 21 October**. The only enabled routes are agency-scoped **type 0** routes from those three packages. This selects TRAX/S-Line, four DART light rail lines and SPRINTER; it excludes buses, DART's type 5 streetcars/trolley, other operators, and type 2 FrontRunner/TRE/Silver Line/COASTER. Existing source rights, links, hashes and calendar validity checks continue to apply.

Source colours are retained: TRAX Blue `#004A97`, Red `#BE2036`, Green `#2EB566`, S-Line grey `#77777A`; DART Blue `#198BC3`, Green `#006F38`, Orange `#F68B1F`, Red `#FD3E3E`; SPRINTER teal `#00AB9B`. No Melbourne palette is applied.

**1,224 of 1,227 pattern legs** match supplied railway geometry. All TRAX/S-Line and SPRINTER legs match; three DART pattern sections remain empty paths under the existing 150 m rule. Their schedules stay present, with vehicles hidden between unsupported stops. No straight connectors or increased tolerance are introduced.

Rebuild with `./.venv/bin/python scripts/prepare_us_light_rail.py`. It reuses the commuter preparer's calendar, geometry, clock conversion, source-pin and shared-pattern processing, with an explicit light-rail mode and scope. Output: `data/reference/us_rail/light-rail-2026-10-12.json.gz`; override: `SUNTRAIN_US_RAIL_LIGHT_RAIL_REFERENCE`. Ignored raw caches can share the same downloaded ZIP files; no second copy of existing replay services is stored.

Checks cover all seven days, all nine routes and their colours, mode/agency exclusions, unique departure ownership, the three bounded geometry gaps, unselected-file isolation, optional cache invalidation and combinations of all three US transport layers. Browser checks cover real transport controls, all three operator filters, SPRINTER's route colour and dated details, 2,000× playback, the overview, Sunday service and returning to the unchanged intercity default.
