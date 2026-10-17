# London replay and future expansion

## Shipped scope

The first London week is **5–11 October 2026**, in **Europe/London** (BST, UTC+1). It includes all eleven Underground lines, their scheduled branches and service variations, DLR, London Trams, **all six Overground lines** and the **Elizabeth line**. The latter includes Reading, Heathrow Terminals 4/5, Abbey Wood and Shenfield services. It uses the existing city selector, shared schedule patterns, local playback, filters, route colours, themes and fullscreen. No live tracking or passenger loads are implied. Overview continues to analyse Melbourne passenger data.

The bundle contains **9,193 shared patterns**, **1,168 station/platform records** and **1,856 paths** in approximately **1.67 MB compressed**. Daily service occurrences are **13,422 / 13,425 / 13,432 / 13,584 / 13,615 / 11,151 / 9,701**, Monday through Sunday. The original Underground/DLR/Trams service counts are preserved. Services follow their source calendars; not every line operates every day. The existing 03:00 business windows retain journeys crossing the boundary, including carry-ins from the previous service date.

## Timetable availability and provenance

The brief's [Transitland converted ZIP](https://gtfs-source-feeds.transit.land/uk-tfl.zip) returned HTTP 401 during the 18 October audit. An alternative Teleport no-bus download returned 403. No accessible, validated 2024 timetable was obtained; 2026 is an explicitly permitted fallback.

The public [Planar Network 4 October 2026 release](https://github.com/planarnetwork/gb-transit/releases/tag/feed-2026-10-04) was actually downloaded and inspected:

- ZIP: `https://github.com/planarnetwork/gb-transit/releases/download/feed-2026-10-04/gtfs-rail-and-tfl.zip`.
- Size: 39,552,156 bytes. SHA-256: `7bc0854bbc6d5206bfdd51a0e77a7bb1b3af8c627c360e2c5b0823fb03a7c5b7`.
- Declared feed validity: **4 October 2026–4 January 2027**; version `RJTTC978.ZIP`.
- Release metadata says TfL timetables were retained on **2 October 2026**. This is the conversion release date, not a claim that every source timetable was newly issued that day.
- Select `tfl_` routes from agencies `LUL`, `DLR` and `TCL`, plus agency `=LO` routes `LIB`, `LIO`, `MIL`, `SUF`, `WEA`, `WIN` and agency `=XR` route `XR`, type 2 only. Exclude National Rail/CIF Underground placeholders (`=LT`), replacement buses, cable car, boats and other operators. DLR is classified as light rail despite its GTFS type 2; Overground and Elizabeth line use commuter rail, with separate operator filters.

The official [TfL Journey Planner timetable download](https://tfl.gov.uk/tfl/syndication/feeds/journey-planner-timetables.zip) also downloaded successfully, but its 15 October snapshot was not substituted for the earlier week. Current APIs/downloads are not historical archives. Working-timetable PDF reconstruction was unnecessary.

These are scheduled estimates, not GPS observations or a reconstruction of every engineering closure or disruption. Direction A/B preserves the TfL timetable's GTFS bits without claiming compass directions. **All 29,214 Overground/Elizabeth source trip records have `direction_id=0` as a placeholder**, including opposite journeys; these are explicitly labelled **Not specified**. Use line, origin/destination, station or trip filters rather than interpreting that placeholder as an actual direction. The original operator/line identities and colours come from the dated feed.

## Railway geometry and known gaps

The converter [documents its data limitations](https://planarnetwork.github.io/gb-transit/feeds/using-this-data/), including sketch shapes between stations. **Those shapes are never used for London animation.**

The committed ODbL geometry database uses operating railway ways from OSM route relations:

- [BBBike London extract](https://download.bbbike.org/osm/bbbike/London/London.osm.gz), last modified **11 October 2026**, 406,645,358 bytes; SHA-256 `51a9f096bcd6da2c6435cc2dc8ec663f142ea5649498fb6bf1ac65fd858a7b9e`.
- Missing railway route-member ways, including the Reading/Maidenhead branches, Overground connections, outer Metropolitan branches and Waterloo & City, supplemented through the [OpenStreetMap API](https://api.openstreetmap.org/api/0.6/) on **18 October 2026**. The combined 170,910-byte supplement contains the 118 newly requested missing ways/nodes plus the original Underground supplement; SHA-256 `56485111eca113a5f9d7e6e3ba9b1a73a2c9865cfb713e2ee3e1d32e10037a62`. This supplement is not a historical attic snapshot.
- `data/reference/london/osm-rail-2026-10-11.json.gz`, 957,422 bytes; SHA-256 `72e871945569f7b708ee10a49dc50c24d8f4afe04120986cec522524461e1b6a`. Metadata records both source dates and licences.

Ordered stops first match a connected route variant, including closed loops. When a through-service crosses variants, a London-only graph joins **identical OSM node IDs**, never nearby coordinates. Circle, District, Hammersmith & City and Metropolitan services may use their shared physical network. Other lines stay in their own network. Stop anchors must be within 150 m of the railway. This establishes plausible connected alignment, not the actual running track or signalling direction.

No timetable trips are omitted. Fifty-six geometry variants have one or more unresolved legs, representing **under 1% of scheduled legs on every replay date** (approximately 0.70–0.83%). Only those legs are hidden; matched portions and station dwells remain available. Known original locations include Jubilee West Ham–Stratford, Piccadilly Heathrow Terminal 5–Terminals 2 & 3, some Metropolitan Harrow/Wembley/Finchley Road journeys, Tram sections around Blackhorse Lane and Belgrave Walk, and Waterloo–Bank in one direction. Some source stop coordinates miss the 150 m threshold (approximately 152 m at Stratford, 186 m at Belgrave Walk and 204 m at Bank); other gaps reflect unresolved OSM connectivity. Do not widen the threshold or draw straight connectors simply to eliminate these counts.

The additions introduce **74–76 Elizabeth line gaps per day** between Heathrow Terminal 5 and Terminals 2 & 3. Reading–Abbey Wood journeys and the other branches have matched track paths. All six Overground lines have complete geometry on Monday–Saturday. One Sunday Suffragette journey diverts via Hampstead Heath toward Willesden Junction: seven legs are not resolved by its own line's route geometry. Its timetable identity is retained rather than relabelled Mildmay or drawing connectors. Every added line still has fewer than 1% unresolved scheduled legs on each date. For a future geometry improvement, inspect the actual connecting OSM ways at Heathrow and Gospel Oak before adding edges; sharing the Mildmay graph alone does not resolve the first diversion connection.

## Passenger data audit

[TfL's documentation](https://tfl.gov.uk/info-for/open-data-users/our-open-data) and the public [crowding bucket](https://crowding.data.tfl.gov.uk/) were inspected. NUMBAT folders **2016–2025** were available; no 2026 folder was listed during the audit.

The official S3 copies of [the introduction](https://s3-eu-west-1.amazonaws.com/crowding.data.tfl.gov.uk/NUMBAT/Intro_to_NUMBAT.pdf) and [2025 Monday workbook](https://s3-eu-west-1.amazonaws.com/crowding.data.tfl.gov.uk/NUMBAT/NUMBAT%202025/NBT25MON_Outputs.xlsx) downloaded successfully (180,103 and 12,136,790 bytes). The latter actually contains `Link_Loads`, `Link_Frequencies`, `Line_Boarders`, `Station_Flows`, `Station_Entries`, `Station_Exits`, `Station_Boarders` and `Station_Alighters`, with 15-minute columns and station/line/direction identifiers. Other published day types include Friday, Saturday, Sunday and **TWT**, an average Tuesday/Wednesday/Thursday day.

NUMBAT is modelled typical autumn demand, not observations for each historical journey. **2025 does not match this 2026 week**, so London passenger sizing and heatmaps remain unavailable. A future optional layer could explicitly show typical autumn 2025 station boardings or link loads. Link load divided by corresponding service frequency would be a modelled average per train, never an observed load; preserve units and missing/zero frequencies. Station entries, boardings, exits, alightings and link loads measure different things.

TfL also documents daily station entry/exit footfall, in weekly files since 2023, and publishes annual station counts (2017–2025 folders were listed). Those have different granularity: daily footfall could support an exact-date daily layer after file validation, while annual totals cannot supply hourly boardings. No footfall CSV has been incorporated into this replay.

## Future scope

**Extend the timeframe:** first check actual calendars in the pinned GTFS and source provenance, not only the release date. The current feed declares validity through 4 January 2027, but the committed replay is deliberately one week. Validate later exceptions, service coverage, overnight boundaries, BST changes and geometry gap rates before rebuilding a longer bundle. Don't imply all future disruptions are represented. Preserve shared patterns and lazy service hydration.

**Overground and Elizabeth line are now enabled:** their dated schedules come from the same verified archive, with connected OSM route geometry supplemented beyond the London extract. Preserve that full outer coverage when changing the geographic reference. The [Network Rail feeds](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/) offer registered CIF/JSON access, not an automatic historical archive; no new account or CIF pipeline was needed here. [Overground timetable downloads](https://tfl.gov.uk/modes/london-overground/london-overground-timetables) remain an additional reference rather than a newly validated historical feed.

**Buses and river services:** not implemented. Audit dated TfL Journey Planner bus schedules separately, road/river geometry, conversion completeness and browser volume before enabling them. Do not reuse Underground sketch geometry or railway paths. Cable car is also excluded.

### Bus availability audit — 18 October 2026

Buses have a practical data path; the website has not enabled them yet. Verified downloads and limitations:

- **Historical GTFS:** the [Open Innovations / National Data Library archive](https://data.datalibrary.uk/transport/BODS-ARCHIVE/timetables/2026/10/05/) actually exposes `itm_london_gtfs_20261005.zip`, **300,783,330 bytes**, modified **5 October 2026 01:30:36 UTC**. Byte-range reads verified the ZIP directory and extracted the agency, route, feed-info and calendar tables using about 3 MB, rather than downloading the whole archive. The feed is published by BODS, version `20261004_023931`, with declared validity **4 October 2026–1 August 2027**. That broad validity is not proof every route runs throughout it; calendars and exceptions must be applied per trip.
- That GTFS has **57 agencies and 1,094 routes**, including actual London bus operators such as Arriva London, Stagecoach London, Metroline, Go Ahead London and London United. It also contains other modes and non-TfL operators: **889 bus, 169 extended-type coach, 23 metro, 5 rail, 4 ferry, 3 tram and 1 cable-car route records**. Do not merge the whole feed into the existing rail replay. Route labels alone can collide with regional services; scope by verified operator, route and stops. **673 of the 675** line labels in the newer official TfL bus XML appear in this archived GTFS; `246` and `653` need date/coverage checks. This comparison establishes label overlap, not full journey completeness.
- The archived feed includes **31,311 calendar exceptions** and **81 frequency rows, all `exact_times=0`**. Determine which belong to the selected TfL bus routes before handling them; they describe non-exact headways, not guaranteed departure times. The raw stop-times table alone is approximately **1.48 GB uncompressed**, so conversion must run offline and produce shared schedules rather than send raw rows to the browser.
- **Detailed official bus geometry:** [TfL's 9 October geometry ZIP](https://s3-eu-west-1.amazonaws.com/bus.data.tfl.gov.uk/bus-geometry/Route_Geometry_20261009.zip) downloaded successfully: **7,281,991 bytes**, SHA-256 `496e20fb361d385b7e045369d41f8c6d54860537fb80f4418e3ba615759798bd`. It contains **757 route XML files**, **1,602 line/run/direction groups** and **404,448 ordered coordinate records**, with no duplicate sequence numbers within those groups. Every one of the current official bus XML's **675 line codes** has a matching geometry code. Coordinates include WGS84 longitude/latitude as well as British National Grid eastings/northings. Match the complete ordered stop sequence to a line/run/direction path; these coverage counts do not yet establish that every short working, diversion or stop matches. The geometry's `Base_Version=20261009` is a snapshot reference, not proof of exact paths on each date of the week. TfL retains earlier geometry snapshots, including 26 September.
- **Official dated schedules:** [TfL's 5 October schedule ZIP](https://s3-eu-west-1.amazonaws.com/bus.data.tfl.gov.uk/schedules-20261005.zip) also downloaded, but is **3,099 PDFs**, not GTFS/XML. Size **276,151,325 bytes**; SHA-256 `df571086ba800459b56837f25c3a088fa4f588a74edede5583a6facb176606cc`. Sample routes 1 and 101 contain implementation dates, operating day types, operator/vehicle duties and timing points. Its 781 codes include replacement/river entries, so this is not a count of ordinary bus routes. Use as a cross-check, not as the primary conversion source.
- **Current official Journey Planner XML:** the already cached 15 October ZIP has four bus archives containing **735 XML files, 675 unique line codes and 375,994 VehicleJourney records across day types**, approximately **4.28 GB uncompressed**. These are not 375,994 buses per day. All 735 files were checked for operating periods and track elements: none supplies `Track` geometry. Only **635 line codes** have at least one retained version covering the entire 5–11 October week, so a later download cannot establish a complete earlier-week timetable. Preserve `DepartureDayShift`, operating-profile inheritance, school/holiday exceptions, journey-specific timings and both directions if native conversion is ever required.
- **Other GTFS options:** the Transitland/Interline TfL conversion lists only Underground, DLR, Trams, cable car, Thames Clippers and Woolwich Ferry operators, not the London bus network; its protected ZIP is not the bus solution. The live BODS London endpoint responded HTTP 200 and its operator table was inspected, but the bulk transfer timed out; that partial current file is marked `.zip.part` in ignored cache and is not treated as a validated archive. Prefer the confirmed dated archive above.

The archive identifies BODS data under OGL v3.0; TfL's geometry/PDF/XML retain the TfL transport data terms and required notices. Preserve these distinctions and source dates. Neither source establishes individual bus passenger loads or actual GPS movements.

**Recommended next implementation:** use the archived GTFS calendars and bus-only scope, with pinned official TfL bus geometry; reuse shared patterns and browser playback. First validate a small set of ordinary, night, loop and outer-London routes. Audit the frequency table and exact-time semantics before expanding any headways; apply calendar exceptions and deduplicate overlapping source versions. Leave unmatched road legs as gaps. Keep buses as an optional layer, loaded when selected, and retain orange bus markers. Daily service counts, active-vehicle counts, compressed payload size, mobile memory, seeking and 2,000× playback still need measurement; do not turn on the entire network by default based only on download availability. No app or replay-data changes were made during this audit.

## Licensing and attribution

TfL schedules use the [TfL transport data licence](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service), based on a modified Open Government Licence. The app and bundle include:

> Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019].

They also credit Planar Network's conversion. Railway geometry is © OpenStreetMap contributors under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/); the derived geometry database is distributed in the repository and linked in map attribution. TfL roundels, logos and official map artwork are not used. The mixed national GTFS has additional source obligations; do not describe the entire archive as TfL-licensed.

For Overground and Elizabeth line, the source's actual `attributions.txt` and `feed-meta.json` identify **Rail Delivery Group / Rail Settlement Plan**, **DfT NaPTAN (OGL v3.0)** and **National Rail Enquiries Knowledgebase** separately. These credits are retained in the bundle and app; only names, coordinates and timetable fields are used, not Knowledgebase accessibility, amenities or station-page content. The [government timetable catalogue](https://ckan.publishing.service.gov.uk/dataset/rail-timetables) labels the free timetable download CC BY 2.0 UK with an own-business/end-user timetable information condition. The converter itself identifies RSP data terms, rather than granting a blanket software licence over all data. The linked [RSP contract template](https://www.raildeliverygroup.com/files/Publications/services/rsp/RSP_Data_Licence_Template_v07-00_%281%29.pdf) also distinguishes service outputs from supplying licensed data to other parties; it is not evidence of the publisher's particular agreement. Consequently the app links all source terms, retains notices, and does not relabel the national schedules as TfL OGL, MIT or ODbL. Do not treat this replay's data credits as permission to mirror the entire national archive or Knowledgebase; obtain the applicable distributor terms for that separate use. Live RDG/NRE feed access still requires registration and acceptance of the relevant product agreement.

## Rebuild and verification

Timetable preparation needs only the pinned GTFS download and committed geometry; no API key or new runtime dependency:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_replay.py
```

To rebuild geometry, retain the exact XML extract and supplementary OSM response locally. Install Pyosmium as a preparation tool, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_geometry.py \
  .cache/london-audit/London.osm.gz \
  --supplement .cache/london-audit/osm-all-rail-supplement.json
```

The XML and compiled geometry are hash checked. Raw downloads stay in ignored `.cache/`; no raw national feed, NUMBAT workbook, API credentials or signed URLs are committed. The supplement's ID-preserving ways/nodes are recorded in the compiled database; retain the original cached response for an exact raw rebuild. A newly downloaded live extract must be re-audited before changing pins.

Tests cover city scope, graph node identity, disconnected railways, loop preservation, pinned geometry provenance, all replay dates in BST, compact shared schedules, no passenger claims, leg-level gap budgets and external-geometry validation without sketch fallback. Browser checks exercise filtering, details, playback, themes, fullscreen and mobile layout.
