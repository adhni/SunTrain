# Thailand — SRT working timetable and Bangkok rail

Implemented on `codex/thailand-rail`. Select **Thailand** for national SRT working-timetable services using **illustrative 3–9 April 2023 dates**; the effective timetable period is unconfirmed. Select **Bangkok** for **12–18 October 2026**, the same display week as Malaysia. Existing playback, filters, line colours, details, themes and city Overview are reused. The two views have separate, clearly labelled source periods.

## National SRT working-timetable replay

**Date assumption:** approximate period **April 2023**, using the week containing the spreadsheet's 5 April 2023 publication date as a display anchor. The user explicitly accepted approximate dates with a visible note. Publication does not establish the actual effective period, and the source may describe older workings. The description above the map and replay source note say the dates are **illustrative**. Do not relabel this an authenticated April 2023 or October 2026 operating calendar.

The working Ministry of Transport datastore described below supplies **178 numeric passenger-service candidates (1–499)**: special/express/rapid, ordinary, suburban, local and mixed passenger workings. Cargo/depot/empty-stock model identifiers are excluded. This covers the source's northern (39), northeastern (53), southern (48), eastern (26), western (8) and Bangkok suburban (4) corridors. These are source working-timetable services, not a claim of complete present-day SRT coverage.

All **5,787 scheduled calls/endpoints** and original clocks are retained, including operational stops. Non-stopping technical timing points between calls are omitted. Each selected origin says `Daily`, used as the illustrative working calendar; after-midnight `Not defined` row values do not discard the remainder of an overnight journey. Explicit day prefixes such as `1  7:15:00` remain next-day events. Departures belong once to a 03:00–03:00 business date, and playback continues through the last arrival, **14:45:01 the following day**. No source timings are adjusted to fit the date assumption or map.

The week is **458,705 bytes gzip**, with 178 shared timing patterns and 173 shared stop patterns. There are **604 named source calls/stations**, of which **542** have matched coordinates. The other **62** retain their names, clocks and details rows with null map positions. Native-node railway paths cover **83.3% of service-weighted legs** (4,674 of 5,609); **935 legs/day** remain gaps. Vehicles are hidden at unlocated calls and across missing paths. Fit selection and station layers ignore missing coordinates, so they do not appear at longitude/latitude zero. No source calls are silently removed or replaced with a nearby station.

Rail geography is the [Geofabrik Thailand extract](https://download.geofabrik.de/asia/thailand.html), through **20 October 2026 20:23:47 UTC**, downloaded 22 October. PBF SHA-256: `68a665cc5f618f63c6afe5cde011d783c3838ea27b1ebaceb857946626ded939`. It is a current geographic reference, not proof of historical running-track assignments. Only operating metre-gauge conventional railway ways are retained; original shared OSM node IDs define connections. Matching uses normalized English station names or a unique spelling variant with similarity at least 0.94 and a 0.05 margin over a different location; distant same-name candidates remain unresolved. Coordinates must anchor within 150 m of the railway. Per-station names, node IDs, coordinates and match method are retained in metadata. The separate ODbL graph is **285,495 bytes gzip**; the large PBF stays in ignored cache.

The source clocks can be checked directly: train 7 **09:05–19:30:01**, train 9 **18:40–next day 07:15:01**, train 21 **06:10–14:00:01**. Extra terminal seconds are source values, not smoothing. The SRT maroon display colour follows OTP's separately licensed palette. The spreadsheet's licence wording/version remains as documented below; do not automatically apply OTP's CC BY 4.0 licence to these source facts. No passenger loads or observed train positions are supplied.

Ordinary runtime reads only the compact reference. Rebuild from pinned cached datastore pages and the committed graph:

```bash
./.venv/bin/python scripts/prepare_thailand_srt.py
```

To regenerate the ODbL graph, retain the pinned full PBF in `.cache/thailand/srt/thailand-latest.osm.pbf`, then use `PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_thailand_srt.py --prepare-geometry .cache/thailand/srt/thailand-latest.osm.pbf`. Pyosmium is preparation-only. `SUNTRAIN_THAILAND_REFERENCE` overrides the national bundle. Bangkok's existing data is neither changed nor duplicated.

## Bangkok pilot: included

| Network | Lines | Transport filter |
| --- | --- | --- |
| BTS | Sukhumvit, Silom | BTS / MRT |
| MRT | Blue, Purple | BTS / MRT |
| Automated / monorail | Gold, Yellow | Gold / Yellow lines |
| SRT suburban | Dark Red, Light Red | SRT Red Lines |

The compact week contains **22,704 estimated journey occurrences/sections**: **3,687 on normal weekdays**, **2,652 on 13 October and each weekend day**. The source's 13 October holiday exceptions switch weekday templates to weekend templates. All departures are **frequency-based estimates**, not actual individual train departures. Blue Line sections and BTS short workings remain sections as supplied; counts must not be described as distinct physical trains or complete end-to-end services.

The week is **139,676 bytes gzip**, with **36 shared timing patterns, 30 stop patterns and 152 station/platform records**. No browser expansion of every trip's stops; the source's 41.6 MB ZIP stays in ignored `.cache/thailand/`.

## Validated source and reuse

- **Producer:** Office of Transport and Traffic Policy and Planning, Thailand (OTP / สนข.).
- **Official open-data policy:** https://namtang-api.otp.go.th/opendata — explicitly links CC BY 4.0 and the GTFS download.
- **Download:** https://namtang-api.otp.go.th/download/namtang-gtfs.zip
- **Feed version:** `20261021`; retrieved **22 October 2026**.
- **SHA-256:** `a451d1081c6008fb2c94a0c8c0be7172c2dd320adacb3a3db1b1390a1bf50ce7`.
- **Licence:** https://creativecommons.org/licenses/by/4.0/ — applies to the supplied timetable, shapes, station positions and route colours; OTP attribution and SunTrain changes are retained.

`feed_info.txt` covers 1 January–31 December 2026. Selected service calendars have broad 2023–2026 validity. This is the **October snapshot applied to source calendars**, not proof that every line or timetable operated unchanged since 2023, and not a reconstruction of every historical disruption. No schedules are backdated to 2024. Timezone is **Asia/Bangkok (UTC+7)**, using a 03:00–03:00 business window.

## Template handling and exclusions

The feed encodes several urban railways as GTFS type 0, so scope uses explicit route/agency/type combinations, not a generic tram filter. Eight selected route IDs are `1`, `2`, `3`, `4`, `2025`, `2026`, `2027`, `2224`.

Of 52 templates in these lines, **40 are retained**. Six have zero running time between distinct stations; two have conflicting times for an identical route/calendar/stop sequence; four duplicate another timing definition with less detailed headway windows. For otherwise identical timing templates, keep the detailed peak/off-peak definition once. Every excluded trip ID and reason is retained in `metadata.excluded_templates`. No alternative clock values are invented.

The existing headway helper checks half-open windows, positive headways and overlap. Source first-stop dwell is preserved while placing the first **departure** at the frequency window's start. Each estimated occurrence belongs once to its departure business day, including after-midnight calls. Frequency-based status is retained in service details and Overview. English display names come directly from the feed's bilingual fields.

## Railway geometry

Use each trip's own directional GTFS shape and the existing ordered stop projection, with a **150 m** matching limit. These are OTP-provided railway alignments; no OSM-derived graph or new licensing layer is needed for the implemented pilot.

The Red Line source shapes do not match their **Krung Thep Aphiwat approach** within that limit. Match valid adjacent stop pairs against their own directional shape and leave the unmatched approach empty. All other selected networks have mapped legs. **99.58% of weekday / 99.51% of holiday-weekend service-weighted legs** are mapped; **259 approach legs/day** remain gaps. Vehicles are hidden during those legs. The exact route/stop pairs are retained in `metadata.unresolved_stop_pairs`; do not broaden matching or draw straight connectors to hide this.

## Not implemented and next steps

1. **National SRT follow-up:** working-timetable replay is now implemented above with explicitly illustrative dates. Improve date/calendar certainty and unmatched station geography when better data becomes available. Namtang's national schedules remain excluded: many represent only Bangkok-area portions, and newer full-length entries have placeholder minute-by-minute clocks (trip `7932` advertises Bangkok–Chiang Mai with `00:01`–`00:07`). Do not enable these placeholders. The [official public timetable](https://www.railway.co.th/SRTTimetable/StationList), [SRT timetable matrix](https://ttsview.railway.co.th/timetable_modern.php?line=1&ln=en) and working ministry datastore below remain useful sources.
2. **MRT Pink / Muang Thong branch:** source templates have zero running time between distinct stations and cannot support plausible animation. Obtain corrected timing templates; retain the published branch/service calendar only once verified.
3. **Airport Rail Link:** one direction has implausibly short running times, including a segment above 220 km/h in the template. Excluded as a whole rather than adding one direction or mirroring the other direction's times. Obtain corrected operator station timings for both directions.
4. **Red Line approach geometry:** verify the source station/shape mismatch at Krung Thep Aphiwat using an independent station/railway reference. Existing clocks and all remaining path segments are unchanged.
5. **Buses, BRT and ferries:** present in Namtang but excluded. Audit their own timing quality, duplicates, shapes and browser volume before enabling them. Retain each source route's colours.
6. **Passenger data:** optional future work. Station/line totals must not be presented as actual individual train loads.

## Second national SRT investigation — 22 October 2026

**Outcome:** found and downloaded an independent official spreadsheet mirror. Its effective dates remain unconfirmed; it is now used by the national working-timetable replay above with explicitly illustrative April 2023 dates. Bangkok's data remains unchanged.

- **Working catalogue:** https://datagov.mot.go.th/en/dataset/after32
- **Working metadata API:** https://datagov.mot.go.th/api/3/action/package_show?id=after32
- **Public datastore:** https://datagov.mot.go.th/api/3/action/datastore_search?resource_id=da06de08-1c8d-4ecd-88f1-67652f65cb95&limit=5
- **Dictionary resource:** `f961ca55-74a5-441a-a785-62e47e8973ec`, available through the same datastore API.

The ministry reports that this datastore contains all records from SRT's `after32.xlsx`. Downloaded **21,841 distinct rows covering 491 train identifiers**, in pages at offsets **0, 10000, 20000** (the server caps responses at 10,000 even if a larger limit is requested). Raw evidence is preparation-only in `.cache/thailand/srt/`: `catalog.json`, `dictionary.json`, `records.json`, `records-10000.json`, `records-20000.json`. The ministry's TLS chain failed local certificate validation; the public, credential-free catalogue reads used a per-request verification override, not a persistent application setting. Original `gdc.railway.co.th` XLSX downloads timed out.

This source has plausible full-length and overnight timings rather than Namtang's placeholders: train 7 lists Bang Sue–Chiang Mai **09:05–19:30**; train 9 **18:40–next day 07:15**; train 21 lists Bang Sue–Ubon Ratchathani **06:10–14:00**. These are evidence of useful source content, **not confirmation of an applicable historical date**. Original spreadsheet resource metadata is dated **5 April 2023**, while the catalogue's March 2026 modification is a metadata/harvesting date. Both first/last year-of-data fields are blank; no effective-from/to timetable period was found. Do not label these rows October 2026 or treat the resource creation date as an operating date.

The export includes internal train templates, non-stopping timing points and simulation/run-time fields. All downloaded `Public arrival` / `Public departure` fields are empty. Operating-day values comprise **16,092 `Daily` rows and 5,749 `Not defined` rows**; the latter also occur within otherwise daily overnight trains. These are row-level values: do not discard overnight continuation rows or infer a complete calendar from them without validating the export. The catalogue licence is `Other`, with free text **“Open Data Common, Creative Commons Attributions”**, without a specific CC version/URL; OTP's separate CC BY 4.0 licence does not cover this spreadsheet automatically.

The [transport ministry's national timetable announcement](https://mot.go.th/PRNews/160) links the official [5 April 2023 PDF](https://www.railway.co.th/Download/Timetable/2566/SRT-Timetable-2023-04-05.pdf) and an [ebook copy](https://online.fliphtml5.com/ctvfc/teeb/). Both operator hostnames (`www.railway.co.th` and `railway.co.th`) timed out for the PDF. The ebook redirects to a verification challenge; no timetable content was obtained. The current SRT matrix also requires verification. These access checks were not bypassed.

**Practical follow-up:** obtain a dated public SRT timetable or dated operator export to confirm the working timetable's effective period and public passenger calling patterns. Improve the unresolved station positions/track gaps in batches, keeping all clocks and calls intact. Retain the approximate-date note until operating dates are actually confirmed. Do not re-query the faulty Namtang national clocks or replace them with the placeholder schedules.

## Rebuild and checks

```bash
./.venv/bin/python scripts/prepare_thailand_replay.py
./.venv/bin/python -m pytest tests/test_thailand.py -q
```

Keep the pinned ZIP in `.cache/thailand/namtang-gtfs.zip` for an identical rebuild: the producer URL rolls forward, and the preparer stops if its hash changes. Filtered template ZIPs are preparation-only. `SUNTRAIN_BANGKOK_REFERENCE` overrides the compact runtime bundle. There are no runtime source API requests or new infrastructure.
