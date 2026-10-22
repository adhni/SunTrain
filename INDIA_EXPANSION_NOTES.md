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

First resolve source reuse terms and audit representative timetables against official publications. Then consider broader express specials, regional/suburban services and separate metro city views. Do not treat a software licence on an NTES crawler as a licence for the timetable it collects. Live APIs and passenger statistics are not required for this pilot.

## Validated local build — 23 October 2026

- OSM extract replication timestamp: `2026-10-21T20:21:46Z`; SHA-256 `fb29cabcecd245fa6e172cdcd70ab32c617684a7e545211405db36b2509d52e4`.
- Graph: 75,363 selected ways, 112,923 compact segments, no missing node coordinates; 4,546,407 bytes gzip.
- Pilot: 3,579 shared timing patterns, 4,875 station records, 18,367 shared paths; **10,601,662 bytes** gzip for the week.
- Daily departures, Monday–Sunday: **2,148 / 2,089 / 2,114 / 2,114 / 2,157 / 2,126 / 2,107**.
- Resolved 335,987 of 343,270 service-weighted legs (**97.9%**); remaining 7,283 are hidden geometry gaps. Some journeys contain several gaps; these numbers do not imply complete historical track accuracy.
- Audit verified shared schedules, single start-window ownership, empty unresolved paths, API descriptors and multi-day arrival extension. Monday's timeline extends 91 elapsed hours from its 03:00 boundary.
- Browser: India opens from Home, 2,148 services, 511 rendered vehicle features at the checked clock, playback advances, no JavaScript errors, zero schedule requests while on Home.
- Checks: 48 Python tests (44 existing app/HTTP + four India cases), 48 JavaScript tests, and `git diff --check`.
