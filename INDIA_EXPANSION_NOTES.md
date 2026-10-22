# India — local intercity rail pilot

Branch: `codex/india-rail`. Candidate week: **31 August–6 September 2026**, Asia/Kolkata (UTC+05:30). This is a community timetable snapshot applied to source calendars, not observed running or a reconstruction of disruptions.

## Distribution status

The timetable producer has not documented an explicit data licence. [Issue 23](https://github.com/Neo2308/indianrailways-gtfs/issues/23) asks about permission and upstream provenance; as checked on 23 October 2026 it has no answer. **Do not commit or publish the timetable or derived replay until reuse permission is established.** The script, cached geometry and replay are a local pilot. Ordinary deployments do not show India; setting `SUNTRAIN_INDIA_REFERENCE` explicitly enables it.

## Pinned timetable and scope

- Producer: P. Radha Krishna / Neo2308, unofficial Indian Railways GTFS.
- [Pinned download](https://raw.githubusercontent.com/Neo2308/indianrailways-gtfs/b340b7048e99c18330ad333e8210d61161ac7a43/gtfs/gtfs.zip).
- SHA-256: `a0347d046ccc66b182f08df88dd5eb6153fd19610a58c87d14e1e6910c937be8`.
- Version `2026-08-30-02-22-43`, declared feed period 30 August–30 September 2026. Broad individual calendars are not proof of historical coverage outside that period.
- Full source: 10,594 train templates, 8,550 stations and 207,224 stop events; 4,173,379 bytes zipped. These are source totals, not pilot departure counts.
- Initial scope: conventional 1xxxx/2xxxx passenger train numbers, excluding explicitly named local/MEMU/DEMU/EMU/passenger/parcel/goods services. This conservative number/name selection is not an authoritative national service classification. Regional trains, suburban networks, specials, metros and buses are future work.
- 205 full-source train entries have no matching calendar. They are excluded by the existing preparer, without inventing dates. Invalid/reversed calendars never activate. Overnight times stay unchanged; each departure belongs once to its 03:00–03:00 window and playback extends to the final arrival.
- Colours distinguish train categories for this visualization; they are SunTrain display colours, not an official operator palette. Passenger sizing is unavailable.

## Geography and rebuilding

All 10,594 supplied shapes consist only of station coordinates. **Never use those for movement.** The explicit geometry resolver replaces them with connected OSM railway paths. Tracks join at native node IDs; unresolved legs stay empty, without straight connectors. Paths are plausible alignments rather than verified running tracks. The modern geographic reference may differ from the August timetable.

Download the [Geofabrik India PBF](https://download.geofabrik.de/asia/india.html) into `.cache/india/india.osm.pbf`. The preparation records its actual SHA-256 and replication timestamp in the derived graph. Preserve that PBF and graph for reproducibility; do not silently rebuild from a changed `latest` extract. OSM-derived geography is ODbL 1.0 with OpenStreetMap attribution, separate from the unresolved timetable rights.

```bash
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_india_replay.py --prepare-geometry .cache/india/india.osm.pbf
.venv/bin/python scripts/prepare_india_replay.py
SUNTRAIN_INDIA_REFERENCE="$PWD/.cache/india/2026-08-31.json.gz" .venv/bin/python -m dashboard.app
```

The full PBF and source timetable stay in ignored cache. The runtime reads only the compact replay; shared schedules and paths are preserved and only the selected replay day is sent to the browser. Home uses the existing small place catalogue and does not download schedules.

## Next additions

Next candidates are a dedicated Mumbai suburban view with a coverage audit, Kolkata Metro, and remaining express specials. Regional/suburban layers and Kochi/Delhi/Chennai city views are implemented below. Do not treat a software licence on an NTES crawler as a licence for the timetable it collects. Live APIs and passenger statistics are not required.

## Validated local build — 23 October 2026

- OSM extract replication timestamp: `2026-10-21T20:21:46Z`; SHA-256 `fb29cabcecd245fa6e172cdcd70ab32c617684a7e545211405db36b2509d52e4`.
- Graph: 75,363 selected ways, 112,923 compact segments, no missing node coordinates; 4,546,407 bytes gzip.
- Pilot: 3,579 shared timing patterns, 4,875 station records, 18,367 shared paths; **10,601,662 bytes** gzip for the week.
- Daily departures, Monday–Sunday: **2,148 / 2,089 / 2,114 / 2,114 / 2,157 / 2,126 / 2,107**.
- Resolved 335,987 of 343,270 service-weighted legs (**97.9%**); remaining 7,283 are hidden geometry gaps. Some journeys contain several gaps; these numbers do not imply complete historical track accuracy.
- Audit verified shared schedules, single start-window ownership, empty unresolved paths, API descriptors and multi-day arrival extension. Monday's timeline extends 91 elapsed hours from its 03:00 boundary.
- Browser: India opens from Home, 2,148 services, 511 rendered vehicle features at the checked clock, playback advances, no JavaScript errors, zero schedule requests while on Home.
- Checks: 48 Python tests (44 existing app/HTTP + four India cases), 48 JavaScript tests, and `git diff --check`.

## Kochi, Delhi and Chennai follow-up

All three reuse `scripts/prepare_india_cities.py`, compact references, map playback, mode/route/operator filters and city Overview. No buses, live tracking or passenger loads were added. Kochi is bundled and visible in ordinary deployments. Delhi and Chennai remain local pilots behind `SUNTRAIN_DELHI_REFERENCE` / `SUNTRAIN_CHENNAI_REFERENCE`: Delhi OTD terms require clarification for this reuse, and CUMTA does not specify a source-data redistribution licence. A community mirror's compilation/code licence is not assumed to cover the agencies' source files.

| View | Source period and coverage | Departures | Compressed week |
| --- | --- | --- | --- |
| Kochi | Official 15–21 December 2025 calendar, all 25 stations | 255 Mon–Sat; 195 Sunday | 32,503 bytes |
| Delhi | Preserved OTD weekday timetable, 15–19 December 2025; Delhi lines, Noida Aqua and Gurgaon Rapid Metro; 262 station records | 5,379 each weekday | 201,736 bytes |
| Chennai | Suburban snapshot applied to 12–18 October 2026; metro from 13–19 December 2021 matched by weekday, explicitly a comparison | 567 suburban + 625 metro Mon–Sat; 548 suburban and no supplied metro Sunday | 183,639 bytes |

**Delhi weekend limitation:** the preserved feed has 5,379 weekday, only 59 Saturday and zero Sunday trip templates, despite defining all three calendar types. We therefore expose weekdays only. The official static download currently returns 404. The mirror consolidates route identifiers/names and supplies readable colours; it does not claim new metro schedules. Do not describe its broad 2019–2025 calendars or OTD's 2023 page date as proof of a fully reconstructed December 2025 timetable. Geometry uses original native distances with existing ordered per-leg recovery on the same supplied shape. **96.1%** of service-weighted legs resolve; remaining sections stay gaps. No schedules were discarded for geometry.

**Chennai dates:** both GTFS ZIPs were downloaded directly from the working `test.cumta.org` portal, rather than its unreachable `opendata.cumta.org` hostname. The official metro calendar is 20 April–31 December **2021**, Monday–Saturday only; its frequencies and calendar-exceptions files are empty. Source dates and offsets are retained in preparation, and every display/source weekday mapping is recorded in the merged metadata. Sunday metro is explicitly unavailable in this dataset, not a claim that the real network closes. Suburban calendars start in August/September 2025 and expire implausibly in 2170: the replay uses an October **2026 source snapshot**, not a validated century-long or full historical archive. Nineteen suburban templates with backwards clocks and four with fewer than two calls are excluded without changing source times. All valid selected Chennai legs resolve: native metro shapes, and the existing connected OSM India railway graph for suburban services. Chennai opens on the urban core; **Fit selection** includes outer suburban termini.

### Pinned downloads

- Kochi: https://kochimetro.org/opendata/KMRLOpenData.zip — SHA-256 `26347766f41574bbde22e57c1ac12d8c169baed10ea7ea232008ffb428fcb158`. [KMRL terms](https://kochimetro.org/open-data/) expressly permit adaptation and redistribution with attribution. The replay displays “Contains data provided by Kochi Metro Rail Limited”. All valid journey legs use native supplied geometry. The feed has no route colour; SunTrain uses a teal display colour.
- Delhi: https://ethanc8.github.io/delhi-gtfs/metro.zip — SHA-256 `fe9d74757a192bac058560d252c0edee6ad6a0eb2693005f71f0106a7ef711c3`. Mirror repository revision inspected: `ce9586990a5474f3e4e02b876823fc4cd058e1db` (`trunk`). Original source: https://otd.delhi.gov.in/data/staticDMRC/ ; [terms](https://otd.delhi.gov.in/terms). Supplied colours are the mirror's display palette, originally taken from INAT; no map artwork is used.
- Chennai Metro: https://test.cumta.org/CMRL%20gtfs.zip — SHA-256 `094f6cfb2e393e5f0ccf516dc7ad41aa25e766d836c98a0b8b682dac090fc3e9`. Original folder-wrapped archive is preserved unchanged in cache; its route colours are retained, with a neutral display colour for unspecified through services.
- Chennai suburban: https://test.cumta.org/Southern%20Railways.zip — outer ZIP SHA-256 `da3f41ab4f83ad6a4f629f4b24f706ad939114e6348a4738e875fb6080ff5533`; inner timetable SHA-256 `ed8bb1ae8aa32a70459c9fd41c20fd3070620541ed52007e7abaa0c8bef46343`. The shared archive reader now supports exactly one nested GTFS ZIP, alongside the outer archive's geography files. Source encodes suburban rail as GTFS type 1; explicit operator scoping classifies it as train. SunTrain uses a maroon display colour.

The original ZIPs remain in ignored cache; preparation verifies hashes before reading them. Mutable source URLs are not assumed to be permanent archives: keep the pinned caches, and re-audit any changed file before updating hashes. The existing OSM graph is reused for preparation only, without copying India's timetable into Chennai. No new runtime API, dependency or separate map implementation is needed.

```bash
.venv/bin/python scripts/prepare_india_cities.py all
SUNTRAIN_INDIA_REFERENCE="$PWD/.cache/india/2026-08-31.json.gz" \
SUNTRAIN_DELHI_REFERENCE="$PWD/.cache/india-cities/delhi/2025-12-15.json.gz" \
SUNTRAIN_CHENNAI_REFERENCE="$PWD/.cache/india-cities/chennai/2026-10-12.json.gz" \
.venv/bin/python -m dashboard.app
```

Validation: **76 Python tests and 48 JavaScript tests** passed. Source audits checked departure-window ownership, shared schedules, Sunday availability, mode filtering, date mapping and geometry gaps. Browser checks opened all three from Home, rendered vehicles and advanced playback with no JavaScript errors; Home made zero initial schedule requests. Rebuilds and screenshots stay in ignored cache. Preview with all India pilots is running at `http://localhost:8089` for this session.

## Nationwide regional and suburban follow-up

The **India** view now offers **Regional / MEMU / DEMU** (`regional_rail`) and **Suburban / local** (`commuter_rail`) in Transport, alongside the existing intercity layer. Intercity remains the default; unselected layers are not opened. These use the same pinned nationwide GTFS and OSM railway graph, **31 August–6 September 2026**. No new source download, runtime dependency or city-specific rendering system was added.

The initial intercity selection has precedence, so additional services cannot duplicate a train already in that layer. Regional scope accepts five-digit 3/4/5/6/7/9-series source numbers, plus otherwise-unselected 0/1/2-series services explicitly named MEMU, DEMU/DMU, EMU, LOCAL, SUBURBAN, PASS/PAS or PASSENGER. Cargo, parcel, goods, PCET, JPP, empty-stock and FTR labels are excluded. Explicit MEMU/DEMU names take precedence over number-based categories; 3/4/9-series and EMU/local-labelled trains use the suburban filter. Remaining selected passenger services use the regional filter. This is SunTrain's practical source-number/name grouping, not an official service taxonomy. Existing 1/2-series intercity entries remain in their original layer, including a handful named DMU or PAS. The four 8-series IRCTC Tejas entries and other unclassified specials are outside this addition. Do not claim complete Mumbai, Kolkata or Chennai suburban coverage from this feed.

The source contains **6,151 selected regional/suburban route entries**, with **6,137 shared patterns** producing occurrences in this week. Missing calendars never receive invented running days. No additional active trip was omitted for malformed schedules. Separate daily bundles preserve relative timing vectors and shared stop patterns; schedules/topologies are namespaced using the existing regional bundle helper so combining modes cannot overwrite station mappings or duplicate IDs. Original train numbers remain unchanged. The runtime reuses the existing optional-rail composer and extends playback through the selected journeys' final arrivals.

| Layer | Mon | Tue | Wed | Thu | Fri | Sat | Sun | Resolved journey legs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Regional / MEMU / DEMU | 3,126 | 3,121 | 3,112 | 3,096 | 3,113 | 3,055 | 2,905 | 94.9% |
| Suburban / local | 2,772 | 2,774 | 2,774 | 2,774 | 2,772 | 2,748 | 2,503 | 97.1% |

Monday has **8,046 departures with all three modes**, versus the unchanged **2,148** default intercity departures. Unresolved legs remain empty and hide movement between calls; station calls and source clocks are retained. The supplied station-to-station straight shapes are never substituted for missing railway paths.

Rebuild after preparing the existing India railway graph:

```bash
.venv/bin/python scripts/prepare_india_replay.py --regional
```

The preparation-only combined week is `.cache/india/regional-week.json.gz` (**4,144,444 bytes**). Runtime bundles are `.cache/india/regional_rail/YYYY-MM-DD.json.gz` and `.cache/india/commuter_rail/YYYY-MM-DD.json.gz`. Daily regional files are **4.05–4.22 MB**, suburban files **0.61–0.68 MB**. All fourteen files total **33,980,675 bytes**; this deliberately trades a little local disk duplication for independently opened daily layers. None are added to git. Default viewing downloads neither layer. `SUNTRAIN_INDIA_REGIONAL_RAIL_REFERENCE` and `SUNTRAIN_INDIA_COMMUTER_RAIL_REFERENCE` optionally override their directories; otherwise they sit beside `SUNTRAIN_INDIA_REFERENCE`. The local preview command above remains valid.

Validation: tests cover source scope, intercity de-duplication, optional-layer isolation (including opening regional without a base file), unique combined IDs, independent station remapping, shared schedules and overnight end times. A full seven-day audit verified single departure-window ownership, mode membership, geometry gaps and selected-day bundles. Existing German regional and app/HTTP checks also pass. Source reuse status remains documented in the earlier distribution section.

Checks for this follow-up: **84 Python tests and 48 JavaScript tests passed**. Browser verification covered the actual Transport options (2,148 default → 5,274 with regional → 8,046 with both layers), suburban-only filtering (2,772 Monday / 2,503 Sunday), playback and zero Home schedule downloads, with no JavaScript errors.
