# Malaysia — national KTM and Kuala Lumpur rail

Implemented on `codex/malaysia-rail` for **12–18 October 2026**. Select **Kuala Lumpur** for urban rail or **Malaysia** for the national KTM view.
Uses the existing replay, filters, line colours, service details, themes and city Overview.

## Included

- **KTM Komuter:** Batu Caves–Pulau Sebang/Tampin (Seremban) and Tanjung Malim–Pelabuhan Klang lines, including scheduled short workings. Complete journeys and outer termini are retained; use Fit selection to see them.
- **MRT:** Kajang and Putrajaya lines.
- **LRT:** Ampang, Sri Petaling, Kelana Jaya and Shah Alam lines.
- **KL Monorail:** included with the LRT / Monorail transport filter.
- **KLIA Ekspres / Transit:** both airport lines, including the Salak Tinggi early short working and combined late-night services.

The week contains **17,897 journey occurrences** in about **205 KB gzip**: 2,697 per weekday, 2,209 Saturday and 2,203 Sunday. KTM contributes 90 published weekday / 74 weekend departures, ERL airport trains contribute 212 weekday / 191 weekend departures, and the remainder illustrate Rapid KL's published headways. All included journey legs have mapped geometry. Timings, station sequences and paths remain shared (86 timing patterns, 44 stop patterns); no browser expansion of every trip's stops.

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

## National KTM addition

**Malaysia** adds all seven other railway products in the same pinned KTM feed: ETS (86 services/day), Ekspres Rakyat Timuran / Intercity (3), Intercity Shuttle (14), Shuttle Tebrau (31), Shuttle Selatan (14), and northern Komuter's Padang Besar (38) and Ipoh (24) lines. These **210 individually scheduled journeys per day** are stored once in a **231 KB gzip** week. KL Komuter is reused from the existing KL file: the default Malaysia view has **300 weekday / 284 weekend** KTM departures. KL MRT and LRT/Monorail are optional and reuse their existing frequency estimates. No KL timetable is copied into the national bundle.

Coverage is the **Peninsular Malaysia KTM network represented in this source**, including original cross-border calls at Woodlands and Hat Yai; it does not include Sabah rail. KLIA airport rail is an optional shared KL layer. The existing KTM and Rapid KL schedules remain unchanged. Original source route types are scoped explicitly (KTM encodes several commuter/shuttle products as type 0). No source train is discarded, moved to another day or retimed to fit the map. Each departure belongs to one business date; the timeline extends through the last overnight arrival (12:40 the next day in this snapshot).

The national railway graph comes from the same cached OSM France PBF, expanded beyond KL. Incomplete country-border ways are omitted; no disconnected track nodes are joined. **13 minor station coordinates** in KTM's source did not match the railway and were replaced using explicitly named OSM stations/stop positions. Original coordinates, replacement coordinates, source node IDs and names are retained in `data/reference/malaysia/station-positions-2026-10-21.json` and replay metadata. Matching used exact normalized names, the documented Sungai/SG and Kampung/KG abbreviations, a unique station cluster, and the existing 150 m track check. Station names and all timetable times remain unchanged. This OSM geography is ODbL, separate from the CC BY timetable facts.

**98.8% of national service-weighted journey legs** have mapped paths (99.3% including reused KL Komuter). The remaining 26 legs/day are concentrated at **Kemubu, Sungai Mengkuang Baru and Padang Besar–Hat Yai**: ambiguous/unmatched minor-stop positions and missing Thai track coverage are left as gaps, with vehicles hidden between the relevant calls. Woodlands journeys have mapped paths. The detailed route/stop pairs are retained in `metadata.unresolved_stop_pairs`; do not substitute another station or broaden matching to make these disappear.

The new schedule, separately distributed ODbL graph and station-position reference add about **380 KB** on disk. The large PBF remains preparation-only. `SUNTRAIN_MALAYSIA_REFERENCE` overrides the national timetable. The optional KL layers fingerprint the existing KL file and can load without opening the national timetable. Date selection, route/operator filters, themes, details and Overview use the existing shared implementation.

## KLIA airport rail addition

Both downloads are linked directly from the [official ERL schedule page](https://www.kliaekspres.com/schedule), retrieved **22 October 2026**:

| Timetable | Effective | PDF SHA-256 |
| --- | --- | --- |
| [KLIA Ekspres](https://www.kliaekspres.com/media/14uietk1/train-schedule-08-dec-25-onwards-ke.pdf) | 8 December 2025 | `58f2e5677526177551a5e8d0e7bd955424d5de78526cc4e3515159d319a296df` |
| [KLIA Transit](https://www.kliaekspres.com/media/rojb45mf/kt-train-schedule_effective-21-mar-2026.pdf) | 21 March 2026 | `0fa011a6eb757bd8e4524a4ba2569af05958041bbcb48e66d0ac5e9d7cdea452` |

The PDF tables contain explicit journeys: **108 express departures daily**, plus **104 weekday / 83 weekend Transit departures**. Ten grey late-night rows in the Ekspres table are the same all-stops trains in each Transit calendar. Each matches all three printed airport/terminal times before being represented **once under KLIA Transit**. The 05:00 Salak Tinggi–T2 short working, midnight rollover and final 01:00 T2–01:40 KL Sentral journey are preserved. Internal trip IDs describe schedule rows, not actual train numbers. Terminal times are retained as printed; intermediate columns supply single station events, without separately published arrivals/dwell. No headway-derived departures are introduced.

The dated editions are applied to our existing **12–18 October 2026** week in `Asia/Kuala_Lumpur`, with weekday/weekend tables and after-midnight journeys belonging once to the preceding business date. There is no national public holiday in this week. The website's temporary **2–4 October** all-stops notice is outside it; this is a timetable replay, not a disruption record.

Four directional OSM route relations from the same pinned PBF provide **standard-gauge ERL tracks and platform stop positions**: `2082100`, `8119876`, `8119878`, `8119879`. Native shared nodes define connectivity; the KTM metre-gauge graph is not used. All airport legs have mapped paths, including the long express section. Route colours come from these OSM relations: Ekspres purple `#800080`, Transit teal `#139593`, credited under ODbL. The KL default bounds now include both airport terminals.

The converted source facts (`erl-timetable-2026-03-21.json.gz`, **4.5 KB**) and separate ODbL geometry (`erl-tracks-2026-10-22.json.gz`, **12.2 KB**) rebuild 14 shared airport timing patterns. The replay grows only **21.4 KB**. Airport schedules live once in the KL bundle; Malaysia's **KLIA airport rail** mode reuses that file and can load without opening the national KTM file. KL includes airport rail by default; Malaysia keeps its KTM defaults. With every mode selected, Malaysia has **2,907 weekday departures**.

ERL publishes the PDFs publicly but provides no open-data licence on the inspected schedule/privacy pages. Attribute **Express Rail Link Sdn Bhd**, retain operator source rights, and **do not label ERL CC BY**. The source PDFs, artwork and logos stay in ignored preparation cache. The committed conversion contains factual times; no general redistribution permission for ERL publications is asserted. OSM-derived tracks, positions and colours are separately ODbL. No passenger loads are supplied.

## Rebuild and next additions

```bash
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_kuala_lumpur_replay.py
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_malaysia_replay.py
```

Pyosmium is preparation-only. The source URLs roll forward; the script verifies the above hashes and stops if they change. Retain the pinned files in `.cache/kuala-lumpur/` for an identical rebuild. `SUNTRAIN_KUALA_LUMPUR_REFERENCE` can override the compact timetable path.

For airport source regeneration, save the linked PDFs as `.cache/malaysia-airport/ekspres.pdf` and `transit.pdf`, then run these before rebuilding KL:

```bash
PYTHONPATH=.cache/pdf-tools ./.venv/bin/python scripts/prepare_malaysia_airport.py --extract-pdf
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_malaysia_airport.py --prepare-geometry
```

Ordinary KL rebuilds use the committed airport facts/geometry and need no PDF tooling. Source PDF/PBF and converted artifact hashes are pinned in the airport preparer.

- **National geometry follow-up:** obtain reusable connected Thai border geometry for the Hat Yai continuation and verify the two remaining minor station positions against primary references. Do not invent connectors or alter their timetable.
- **Buses / BRT:** government endpoints exist, but are not included in this rail addition. Audit their own shapes, frequency semantics and payload size first.
- **Passenger data:** not implemented. Operator/line totals or station counts must not be presented as individual train loads.
