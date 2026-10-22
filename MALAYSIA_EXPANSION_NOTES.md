# Malaysia — Kuala Lumpur rail

Implemented on `codex/kuala-lumpur-rail` for **12–18 October 2026**. Select **Kuala Lumpur**.
Uses the existing replay, filters, line colours, service details, themes and city Overview.

## Included

- **KTM Komuter:** Batu Caves–Pulau Sebang/Tampin (Seremban) and Tanjung Malim–Pelabuhan Klang lines, including scheduled short workings. Complete journeys and outer termini are retained; use Fit selection to see them.
- **MRT:** Kajang and Putrajaya lines.
- **LRT:** Ampang, Sri Petaling, Kelana Jaya and Shah Alam lines.
- **KL Monorail:** included with the LRT / Monorail transport filter.

The week contains **16,455 journey occurrences** in about **184 KB gzip**: 2,485 per weekday, 2,018 Saturday and 2,012 Sunday. KTM contributes 90 published weekday / 74 weekend departures; the remainder illustrate Rapid KL's published headways. All included journey legs have mapped geometry. Timings, station sequences and paths remain shared (72 timing patterns, 39 stop patterns); no browser expansion of every trip's stops.

## Actual sources and dates

Both public ZIPs were downloaded directly on **22 October 2026**, without accounts or keys:

| Feed | Download | SHA-256 |
| --- | --- | --- |
| KTM | https://api.data.gov.my/gtfs-static/ktmb | `4a6e2a3b0640078f6dec0aa17f9fc8ca9e89960f2c780c794af63c6117d93e5f` |
| Rapid KL rail | https://api.data.gov.my/gtfs-static/prasarana?category=rapid-rail-kl | `3b00cf0debb428a3533f67c29f9c3c87e09ba9735c05569368a033c9a4491614` |

The [government API documentation](https://developer.data.gov.my/realtime-api/gtfs-static.en) confirms the operator endpoints. Its [FAQ](https://developer.data.gov.my/faq.en) grants CC BY 4.0 for platform data; credit both operators and data.gov.my.

KTM's active calendars cover 18 August–5 November 2026 (weekend calendar begins 22 August). Rapid KL's selected templates cover this October week. Its broad 2019–2026 calendar does **not** prove that today's network operated throughout that entire period. This is the retrieved snapshot applied to the selected calendars, not an archive of every historical revision or disruption. No schedules are backdated to 2024.

## Frequency handling

KTM has individual trip stop times. Rapid KL has 42 selected weekday/Saturday/Sunday timing templates and `frequencies.txt`, with non-exact headways (`exact_times` omitted). We reuse the existing headway expansion helper and shared rail template converter. Source windows are half-open, retain changing peak/off-peak headways, and place the first **departure**, rather than arrival, at `start_time`. The source's initial dwell is retained. Estimated occurrences carry `frequency_based: true`, appear as estimates in details and Overview, and remain distinguishable from KTM schedules. They are not live trains or actual individual departure observations.

Each occurrence belongs once to its departure's 03:00–03:00 business day in `Asia/Kuala_Lumpur` (UTC+8). Original overnight times and weekend differences remain intact.

## Geometry

Rapid KL supplies 14 directional shapes; all selected ordered stop sequences project onto their own shapes within 150 m. BRT Sunway is excluded despite being present in the same rail ZIP.

KTM has **no shapes**. Its paths use the [OSM France Malaysia extract](https://download.openstreetmap.fr/extracts/asia/malaysia-latest.osm.pbf), downloaded 22 October; PBF header timestamp **2026-10-21T01:16:18Z**, SHA-256 `1abfb77758d28dea24ffa4d8ce38527ab7bcdaa0ebacfe074b387cac49bde03a`. Only operating conventional metre-gauge railway ways around the selected network are retained. Original shared OSM node IDs define junctions; tracks are not joined merely because they cross or are nearby. Reuses the existing station-local rail graph with 150 m matching and a route-detour bound. No straight connectors are inserted. Geography describes plausible railway alignments, not exact running tracks or historical platform assignments.

The derived graph is separately distributed as `data/reference/kuala_lumpur/ktm-tracks-2026-10-22.json.gz` (about 48 KB gzip), under ODbL 1.0. Raw ZIPs and the 249 MB PBF stay in ignored `.cache/kuala-lumpur/` and are never sent to browsers. Timetable/shapes CC BY attribution and separate OSM ODbL attribution remain in the replay's sources.

## Rebuild and next additions

```bash
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_kuala_lumpur_replay.py
```

Pyosmium is preparation-only. The source URLs roll forward; the script verifies the above hashes and stops if they change. Retain the pinned files in `.cache/kuala-lumpur/` for an identical rebuild. `SUNTRAIN_KUALA_LUMPUR_REFERENCE` can override the compact timetable path.

- **National KTM:** the same official ZIP also contains ETS, northern Komuter, Shuttle Selatan, Intercity and Shuttle Tebrau. Add later in a nationwide Malaysia view with railway coverage beyond the KL extract; keep KTM's unusual source route types scoped explicitly.
- **KLIA Ekspres / Transit:** separate ERL operator; not present in either validated feed. Investigate a reusable dated timetable before adding.
- **Buses / BRT:** government endpoints exist, but are not included in this rail addition. Audit their own shapes, frequency semantics and payload size first.
- **Passenger data:** not implemented. Operator/line totals or station counts must not be presented as individual train loads.
