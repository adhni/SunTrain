# London replay and future expansion

## Shipped scope

The first London week is **5–11 October 2026**, in **Europe/London** (BST, UTC+1). It includes all eleven Underground lines, their scheduled branches and service variations, DLR and London Trams. It uses the existing city selector, shared schedule patterns, local playback, filters, route colours, themes and fullscreen. No live tracking or passenger loads are implied. Overview continues to analyse Melbourne passenger data.

The bundle contains 7,460 shared patterns, 790 station/platform records and 1,404 paths in approximately 1.32 MB compressed. Daily service occurrences are 11,120 / 11,123 / 11,123 / 11,282 / 11,284 / 8,912 / 7,911, Monday through Sunday. Services follow their source calendars; not every line operates every day. The existing 03:00 business windows retain journeys crossing the boundary, including carry-ins from the previous service date.

## Timetable availability and provenance

The brief's [Transitland converted ZIP](https://gtfs-source-feeds.transit.land/uk-tfl.zip) returned HTTP 401 during the 18 October audit. An alternative Teleport no-bus download returned 403. No accessible, validated 2024 timetable was obtained; 2026 is an explicitly permitted fallback.

The public [Planar Network 4 October 2026 release](https://github.com/planarnetwork/gb-transit/releases/tag/feed-2026-10-04) was actually downloaded and inspected:

- ZIP: `https://github.com/planarnetwork/gb-transit/releases/download/feed-2026-10-04/gtfs-rail-and-tfl.zip`.
- Size: 39,552,156 bytes. SHA-256: `7bc0854bbc6d5206bfdd51a0e77a7bb1b3af8c627c360e2c5b0823fb03a7c5b7`.
- Declared feed validity: **4 October 2026–4 January 2027**; version `RJTTC978.ZIP`.
- Release metadata says TfL timetables were retained on **2 October 2026**. This is the conversion release date, not a claim that every source timetable was newly issued that day.
- Select only `tfl_` routes from agencies `LUL`, `DLR` and `TCL`. Exclude National Rail/CIF Underground placeholders (`=LT`), replacement buses, cable car, boats and other operators. DLR is classified as light rail despite its GTFS type 2.

The official [TfL Journey Planner timetable download](https://tfl.gov.uk/tfl/syndication/feeds/journey-planner-timetables.zip) also downloaded successfully, but its 15 October snapshot was not substituted for the earlier week. Current APIs/downloads are not historical archives. Working-timetable PDF reconstruction was unnecessary.

These are scheduled estimates, not GPS observations or a reconstruction of every engineering closure or disruption. Direction A/B preserves GTFS direction bits without claiming compass directions.

## Railway geometry and known gaps

The converter [documents its data limitations](https://planarnetwork.github.io/gb-transit/feeds/using-this-data/), including sketch shapes between stations. **Those shapes are never used for London animation.**

The committed ODbL geometry database uses operating railway ways from OSM route relations:

- [BBBike London extract](https://download.bbbike.org/osm/bbbike/London/London.osm.gz), last modified **11 October 2026**, 406,645,358 bytes; SHA-256 `51a9f096bcd6da2c6435cc2dc8ec663f142ea5649498fb6bf1ac65fd858a7b9e`.
- Nineteen missing railway route-member ways, including outer Metropolitan branches and Waterloo & City connections, supplemented through the [OpenStreetMap API](https://api.openstreetmap.org/api/0.6/) on **18 October 2026**. Supplement SHA-256 `9b2b0c7947ab2e8bf1dfb5dccfeb74f133dc986823e29d577dac67fe60c4821c`. This supplement is not a historical attic snapshot.
- `data/reference/london/osm-rail-2026-10-11.json.gz`, 585,412 bytes; SHA-256 `63459c614ad0df422f382f19f6bd14618b0173dbef334630f763924e80e82a3c`. Metadata records both source dates and licences.

Ordered stops first match a connected route variant, including closed loops. When a through-service crosses variants, a London-only graph joins **identical OSM node IDs**, never nearby coordinates. Circle, District, Hammersmith & City and Metropolitan services may use their shared physical network. Other lines stay in their own network. Stop anchors must be within 150 m of the railway. This establishes plausible connected alignment, not the actual running track or signalling direction.

No timetable trips are omitted. Forty geometry variants have one or more unresolved legs, representing **under 1% of scheduled legs on every replay date**. Only those legs are hidden; matched portions and station dwells remain available. Known locations include Jubilee West Ham–Stratford, Piccadilly Heathrow Terminal 5–Terminals 2 & 3, some Metropolitan Harrow/Wembley/Finchley Road journeys, Tram sections around Blackhorse Lane and Belgrave Walk, and Waterloo–Bank in one direction. Some source stop coordinates miss the 150 m threshold (approximately 152 m at Stratford, 186 m at Belgrave Walk and 204 m at Bank); other gaps reflect unresolved OSM connectivity. Do not widen the threshold or draw straight connectors simply to eliminate these counts.

## Passenger data audit

[TfL's documentation](https://tfl.gov.uk/info-for/open-data-users/our-open-data) and the public [crowding bucket](https://crowding.data.tfl.gov.uk/) were inspected. NUMBAT folders **2016–2025** were available; no 2026 folder was listed during the audit.

The official S3 copies of [the introduction](https://s3-eu-west-1.amazonaws.com/crowding.data.tfl.gov.uk/NUMBAT/Intro_to_NUMBAT.pdf) and [2025 Monday workbook](https://s3-eu-west-1.amazonaws.com/crowding.data.tfl.gov.uk/NUMBAT/NUMBAT%202025/NBT25MON_Outputs.xlsx) downloaded successfully (180,103 and 12,136,790 bytes). The latter actually contains `Link_Loads`, `Link_Frequencies`, `Line_Boarders`, `Station_Flows`, `Station_Entries`, `Station_Exits`, `Station_Boarders` and `Station_Alighters`, with 15-minute columns and station/line/direction identifiers. Other published day types include Friday, Saturday, Sunday and **TWT**, an average Tuesday/Wednesday/Thursday day.

NUMBAT is modelled typical autumn demand, not observations for each historical journey. **2025 does not match this 2026 week**, so London passenger sizing and heatmaps remain unavailable. A future optional layer could explicitly show typical autumn 2025 station boardings or link loads. Link load divided by corresponding service frequency would be a modelled average per train, never an observed load; preserve units and missing/zero frequencies. Station entries, boardings, exits, alightings and link loads measure different things.

TfL also documents daily station entry/exit footfall, in weekly files since 2023, and publishes annual station counts (2017–2025 folders were listed). Those have different granularity: daily footfall could support an exact-date daily layer after file validation, while annual totals cannot supply hourly boardings. No footfall CSV has been incorporated into this replay.

## Future scope

**Extend the timeframe:** first check actual calendars in the pinned GTFS and source provenance, not only the release date. The current feed declares validity through 4 January 2027, but the committed replay is deliberately one week. Validate later exceptions, service coverage, overnight boundaries, BST changes and geometry gap rates before rebuilding a longer bundle. Don't imply all future disruptions are represented. Preserve shared patterns and lazy service hydration.

**Overground and Elizabeth line:** the same accessible GTFS contains agency `=LO` routes `LIB`, `LIO`, `MIL`, `SUF`, `WEA`, `WIN` (Liberty, Lioness, Mildmay, Suffragette, Weaver and Windrush) and agency `=XR`, route `XR`. They are not enabled. Their National Rail-derived shapes also need railway geometry; Reading/Shenfield and other outer routes need coverage beyond the London extract. Audit Network Rail/RDG/National Rail Enquiries attribution and redistribution terms before adding them. Prefer this already available dated conversion if suitable. The [Network Rail feeds](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/) offer registered CIF/JSON access, not an automatic historical archive. [Overground timetable downloads](https://tfl.gov.uk/modes/london-overground/london-overground-timetables) are another reference, not a validated historical feed yet.

**Buses and river services:** not implemented. Audit dated TfL Journey Planner bus schedules separately, road/river geometry, conversion completeness and browser volume before enabling them. Do not reuse Underground sketch geometry or railway paths. Cable car is also excluded.

## Licensing and attribution

TfL schedules use the [TfL transport data licence](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service), based on a modified Open Government Licence. The app and bundle include:

> Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019].

They also credit Planar Network's conversion. Railway geometry is © OpenStreetMap contributors under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/); the derived geometry database is distributed in the repository and linked in map attribution. TfL roundels, logos and official map artwork are not used. The mixed national GTFS has additional source obligations; do not describe the entire archive as TfL-licensed.

## Rebuild and verification

Timetable preparation needs only the pinned GTFS download and committed geometry; no API key or new runtime dependency:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_replay.py
```

To rebuild geometry, retain the exact XML extract and supplementary OSM response locally. Install Pyosmium as a preparation tool, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_london_geometry.py \
  .cache/london-audit/London.osm.gz \
  --supplement .cache/london-audit/osm-supplement.json
```

The XML and compiled geometry are hash checked. Raw downloads stay in ignored `.cache/`; no raw national feed, NUMBAT workbook, API credentials or signed URLs are committed. The supplement's ID-preserving ways/nodes are recorded in the compiled database; retain the original cached response for an exact raw rebuild. A newly downloaded live extract must be re-audited before changing pins.

Tests cover city scope, graph node identity, disconnected railways, loop preservation, pinned geometry provenance, all replay dates in BST, compact shared schedules, no passenger claims, leg-level gap budgets and external-geometry validation without sketch fallback. Browser checks exercise filtering, details, playback, themes, fullscreen and mobile layout.
