# Thailand — Bangkok rail pilot

Implemented on `codex/thailand-rail`. Select **Bangkok** for **12–18 October 2026**, the same display week as Malaysia. This is Bangkok coverage, not a nationwide Thailand train replay. Existing playback, filters, source line colours, details, themes and city Overview are reused.

## Included

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

1. **National SRT trains:** the same feed is not a usable national timetable. Many records contain only Bangkok-area portions of advertised intercity journeys; newer full-length entries have placeholder minute-by-minute clocks. For example, trip `7932` advertises Bangkok–Chiang Mai with `00:01` to `00:07` times. The source also contains duplicate train numbers. Do not enable all route-type-2 records or reinterpret these placeholders as departures. The [official SRT timetable](https://www.railway.co.th/SRTTimetable/StationList) and [SRT timetable matrix](https://ttsview.railway.co.th/timetable_modern.php?line=1&ln=en) are follow-up sources; the matrix data requires its Turnstile/JWT access flow. The original [government timetable catalogue](https://data.go.th/en/dataset/after32) API returned 403, but a **working Ministry of Transport datastore mirror was found in the second investigation below**. No validated historical national timetable or connected nationwide geometry was obtained in this pilot.
2. **MRT Pink / Muang Thong branch:** source templates have zero running time between distinct stations and cannot support plausible animation. Obtain corrected timing templates; retain the published branch/service calendar only once verified.
3. **Airport Rail Link:** one direction has implausibly short running times, including a segment above 220 km/h in the template. Excluded as a whole rather than adding one direction or mirroring the other direction's times. Obtain corrected operator station timings for both directions.
4. **Red Line approach geometry:** verify the source station/shape mismatch at Krung Thep Aphiwat using an independent station/railway reference. Existing clocks and all remaining path segments are unchanged.
5. **Buses, BRT and ferries:** present in Namtang but excluded. Audit their own timing quality, duplicates, shapes and browser volume before enabling them. Retain each source route's colours.
6. **Passenger data:** optional future work. Station/line totals must not be presented as actual individual train loads.

## Second national SRT investigation — 22 October 2026

**Outcome:** found and downloaded an independent official spreadsheet mirror; national replay remains disabled because its operating period and public passenger timetable interpretation could not be validated. The Bangkok replay and its data are unchanged.

- **Working catalogue:** https://datagov.mot.go.th/en/dataset/after32
- **Working metadata API:** https://datagov.mot.go.th/api/3/action/package_show?id=after32
- **Public datastore:** https://datagov.mot.go.th/api/3/action/datastore_search?resource_id=da06de08-1c8d-4ecd-88f1-67652f65cb95&limit=5
- **Dictionary resource:** `f961ca55-74a5-441a-a785-62e47e8973ec`, available through the same datastore API.

The ministry reports that this datastore contains all records from SRT's `after32.xlsx`. Downloaded **21,841 distinct rows covering 491 train identifiers**, in pages at offsets **0, 10000, 20000** (the server caps responses at 10,000 even if a larger limit is requested). Raw evidence is preparation-only in `.cache/thailand/srt/`: `catalog.json`, `dictionary.json`, `records.json`, `records-10000.json`, `records-20000.json`. The ministry's TLS chain failed local certificate validation; the public, credential-free catalogue reads used a per-request verification override, not a persistent application setting. Original `gdc.railway.co.th` XLSX downloads timed out.

This source has plausible full-length and overnight timings rather than Namtang's placeholders: train 7 lists Bang Sue–Chiang Mai **09:05–19:30**; train 9 **18:40–next day 07:15**; train 21 lists Bang Sue–Ubon Ratchathani **06:10–14:00**. These are evidence of useful source content, **not confirmation of an applicable historical date**. Original spreadsheet resource metadata is dated **5 April 2023**, while the catalogue's March 2026 modification is a metadata/harvesting date. Both first/last year-of-data fields are blank; no effective-from/to timetable period was found. Do not label these rows October 2026 or treat the resource creation date as an operating date.

The export includes internal train templates, non-stopping timing points and simulation/run-time fields. All downloaded `Public arrival` / `Public departure` fields are empty. Operating-day values comprise **16,092 `Daily` rows and 5,749 `Not defined` rows**; the latter also occur within otherwise daily overnight trains. These are row-level values: do not discard overnight continuation rows or infer a complete calendar from them without validating the export. The catalogue licence is `Other`, with free text **“Open Data Common, Creative Commons Attributions”**, without a specific CC version/URL; OTP's separate CC BY 4.0 licence does not cover this spreadsheet automatically.

The [transport ministry's national timetable announcement](https://mot.go.th/PRNews/160) links the official [5 April 2023 PDF](https://www.railway.co.th/Download/Timetable/2566/SRT-Timetable-2023-04-05.pdf) and an [ebook copy](https://online.fliphtml5.com/ctvfc/teeb/). Both operator hostnames (`www.railway.co.th` and `railway.co.th`) timed out for the PDF. The ebook redirects to a verification challenge; no timetable content was obtained. The current SRT matrix also requires verification. These access checks were not bypassed.

**Practical resume point:** obtain the dated public SRT timetable publication or another dated operator export; establish a genuine service period; validate representative daytime/overnight calls and passenger-only scope against this working datastore; then prepare connected railway geometry. Different dates from Bangkok are acceptable if explicitly labelled. Until that evidence is available, keep the existing eight Bangkok lines and move other country work forward rather than re-querying the faulty Namtang national records.

## Rebuild and checks

```bash
./.venv/bin/python scripts/prepare_thailand_replay.py
./.venv/bin/python -m pytest tests/test_thailand.py -q
```

Keep the pinned ZIP in `.cache/thailand/namtang-gtfs.zip` for an identical rebuild: the producer URL rolls forward, and the preparer stops if its hash changes. Filtered template ZIPs are preparation-only. `SUNTRAIN_BANGKOK_REFERENCE` overrides the compact runtime bundle. There are no runtime source API requests or new infrastructure.
