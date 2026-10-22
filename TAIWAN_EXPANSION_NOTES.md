# Taiwan — Taiwan Railways and high-speed rail

## Included

Taiwan opens from Home with the existing replay, Overview, transport/operator/route filters, themes, details and fullscreen controls. Timezone is **Asia/Taipei**. Both Taiwan Railways (TRA) and Taiwan High Speed Rail (THSR) open by default. Public scheduled TRA express, Chu-Kuang, local and fast-local services are included wherever represented in the source, including branch services. Private charters, freight, empty stock and parcel services are excluded. Alishan Railway and metro networks are outside this scope.

**23–27 October 2026** is a five-day window, chosen because both official sources actually cover it. These are published schedules captured on 23 October, not observations of what ran. It is not a reconstruction of actual delays or cancellations. No July timetable is relabelled as October.

| Business date | TRA | THSR | Total |
| --- | ---: | ---: | ---: |
| 23 October | 929 | 187 | 1,116 |
| 24 October | 920 | 170 | 1,090 |
| 25 October | 914 | 192 | 1,106 |
| 26 October | 918 | 197 | 1,115 |
| 27 October | 906 | 155 | 1,061 |

The bundle contains **5,488 occurrences**, shared schedules and railway paths in about **546 KB gzip**. The browser receives the selected day and transport modes. No new runtime API or dependency was added. Home downloads no schedules.

## Timetable sources and reproduction

- **TRA:** [official daily JSON download index](https://ods.railway.gov.tw/tra-ods-web/ods/download/dataResource/railway_schedule/JSON/list), [government catalogue](https://data.gov.tw/en/datasets/6138), [station catalogue](https://data.gov.tw/en/datasets/33425). The daily files retain individual arrivals, departures, half-minute times, stopping patterns, special services and original train numbers. The 28 October file supplies only departures before 03:00 to the final business window. Train ownership is determined by origin departure within one 03:00–03:00 window, never interval overlap. A preceding-day schedule cannot contribute under this rule, so no missing 22 October trips are fabricated.
- **THSR:** the [official timetable download page](https://www.thsrc.com.tw/ArticleContent/a3b630bb-1066-4352-a1ef-58c7b4e8ef7c) supplied the [23–27 October holiday PDF](https://www.thsrc.com.tw/Attachment/Download?pageID=a3b630bb-1066-4352-a1ef-58c7b4e8ef7c&id=4d5ce117-801a-4848-aa53-adc35c3c6455). Its 225 numbered timetable rows have explicit holiday date restrictions; blank restrictions mean daily **within this five-day validity**, as the PDF states. The converter checks every time cell is consumed once, validates date expressions and retains partial workings. The publication gives one time per station: no separate arrival/departure dwell is invented.
- **THSR coordinates only:** twelve station names/coordinates from an explicitly dated [preserved TDX data file](https://raw.githubusercontent.com/siriushsu/taiwan-rail-live/d41aafac1482d50eb0ea72d37ebdf2f87d9d9677/data/thsr_schedule_dense.json). Its 9 July schedule and interpolated passing points are **not used**. No project code, visual assets or route interpolation are copied. The repository's [licence, section 3](https://github.com/siriushsu/taiwan-rail-live/blob/d41aafac1482d50eb0ea72d37ebdf2f87d9d9677/LICENSE) excludes third-party datasets from its source-code licence and refers them to their original terms.

TRA datasets and the government's [THSR daily timetable catalogue](https://data.gov.tw/en/datasets/161163) identify **Taiwan Open Government Data License 1.0**. The THSR conversion extracts timetable facts from its official publication; it does not reproduce the PDF design. Preserve attribution to Taiwan Railway Corporation, Taiwan High Speed Rail Corporation and MOTC TDX. [Government data licence](https://data.gov.tw/license). Passenger counts are unavailable.

The official TDX high-speed API returned **401 / Valid API Key Required** without credentials. PDF conversion avoids requiring an account for this initial period. To expand dates, prefer authenticated TDX daily timetables or another complete dated official publication. Do not repeat this holiday schedule into other dates, and do not use a single preserved July Thursday to infer a whole week.

Pinned URLs and SHA-256 digests are in [sources.json](data/reference/taiwan/sources.json). Original files remain in ignored `.cache/taiwan/`; the prepared bundle and source manifest are committed. Changed downloads fail checksum validation. Intermediate GTFS timestamps are deterministic and the conversion digest is recorded separately from the original sources.

```bash
# Download the pinned JSON/PDF/coordinate source files; keep these caches.
.venv/bin/python scripts/prepare_taiwan_replay.py --download-sources
# Download the Geofabrik Taiwan extract separately, preserving the version below.
curl -L https://download.geofabrik.de/asia/taiwan-latest.osm.pbf -o .cache/taiwan/taiwan.osm.pbf
# osmium and pdfplumber are preparation-only dependencies; the existing local
# installations are under .cache/osm-tools and .cache/pdf-tools.
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_taiwan_geometry.py
PYTHONPATH=.cache/pdf-tools .venv/bin/python scripts/prepare_taiwan_replay.py
```

The pinned PBF SHA-256 is `c2a077d7e9379ebea58062c6361a073017cc2add206104ed3458e646ed31becc`. The rolling Geofabrik URL will change; future extracts will produce a different graph hash and require review before changing the manifest. `SUNTRAIN_TAIWAN_REFERENCE` can override the prepared bundle path.

## Railway paths

[OpenStreetMap / Geofabrik Taiwan](https://download.geofabrik.de/asia/taiwan.html), replication **21 October 2026 at 20:21:46 UTC**, supplies railway geography. Native OSM junctions connect the graph; yard/spur, industrial, military and disused tracks are excluded. **1,067 mm TRA and 1,435 mm high-speed graphs are separate**, preventing shortcuts between the systems. The geography SHA, source date and attribution are recorded in the bundle. OSM-derived paths are distributed under **ODbL 1.0**, separately from timetable facts.

All included journey legs resolve to connected railway geometry in this build. These are inferred alignments, not records of actual platform/track assignments. TRA's published Mountain/Coast field guides skipped-stop express paths through the relevant corridor. When an intermediate geometry hint is needed, both halves share the same physical track anchor; different projected tracks never receive a synthetic join. Unresolved sections would stay empty and hide the vehicle between calls. No straight station-to-station substitutes are used. Source calls and times remain intact, and overnight trains continue to their final arrival.

## Next additions

1. **Taipei Metro**, using complete train-level timetables where available. Audit weekday/weekend calendars and branches; first/last departures alone do not describe every train.
2. Taoyuan Airport MRT, Kaohsiung MRT/light rail and Taichung MRT, one validated network at a time.
3. Alishan Railway as a separate operator and gauge, using its own dated schedules and geometry.
4. A longer common TRA/THSR period using archived daily files or authenticated TDX exports. Keep credentials outside git and the browser. No buses or passenger features are required for these additions.

## Validation

**49 Python tests and 48 JavaScript tests passed**. Tests cover holiday date lists/ranges, passenger scope, source clocks, midnight rollover, Mountain/Coast hints, single-day ownership, mode filtering, original train numbers, compact shared stops and the complete bundled period. Browser verification covers Home, rendered trains, Play, high-speed-only filtering, the final date and Taiwan Overview, with no JavaScript errors or Home schedule downloads. Preview for this session: **http://localhost:8090**.
