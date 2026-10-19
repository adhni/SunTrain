# Portugal expansion notes

## Included

**1–7 June 2026**, matching the Netherlands/Germany and other June 2026 European replays. Mainland passenger trains and Lisbon/Porto metros:

- **CP** Alfa Pendular, Intercidades, InterRegional, Regional, and Lisbon/Porto suburban services represented by the archive, including Cascais, Sintra, Azambuja, Sado, Aveiro, Braga, Guimarães, Marco and Leixões.
- **Fertagus** Lisboa–Setúbal and short workings to Coina/Fogueteiro, including the 25 de Abril bridge.
- **Lisbon Metro** Azul, Amarela, Verde and Vermelha, with the archived line colours and supplied route shapes. Select **Lisbon / Porto metros** under Transport for metro replay, then use Operator or Route to focus on either city.
- **Porto Metro** lines A–F, including B express, with published line colours and dated timetable shapes.

25,911 departures: 8,045 CP, 988 Fertagus, 9,554 Lisbon Metro and 7,324 Porto Metro. Combined daily totals: **4,202 / 4,202 / 4,203 / 3,152 / 4,203 / 3,007 / 2,942**. Train-only daily totals remain **1,517 / 1,517 / 1,518 / 1,022 / 1,518 / 979 / 962**. June 4's reduced service is selected from the source calendars, not interpolated from weekdays. The archive includes Coimbra-area services where scheduled; no closed Coimbra/Mondego railway service is invented. Freight, tourist services outside these feeds, Other metros/light rail, trams, Metrobus/BRT, buses and ferries are excluded. No individual train passenger loads.

The shared-pattern week is approximately **0.725 MB gzip**, with a **0.103 MB** preparation-only rail graph. Uses existing replay, route/operator filters, vehicle details, themes/fullscreen and Portugal Overview. Dates use **Europe/Lisbon**, including summer time; departures belong to one 03:00–03:00 business window. Overnight calls retain original times.

## Downloadable historical schedules

All four dated ZIPs were actually downloaded and inspected; their service calendars cover May 31–June 8, including carry days.

| Operator | Archive | SHA-256 |
| --- | --- | --- |
| CP | [MobilityDatabase, 31 May 2026](https://files.mobilitydatabase.org/mdb-2057/mdb-2057-202605310107/mdb-2057-202605310107.zip) | `6e2c9832899eec69abf16545b4bd6af82879481d1c35823159ba057c74b2ceae` |
| Fertagus | [MobilityDatabase, 14 April 2026](https://files.mobilitydatabase.org/tld-715/tld-715-202604140058/tld-715-202604140058.zip) | `a0735e39bb85438de09c98c89f7e0d45680bc372f23255f9183d1df12ff8fb3a` |
| Lisbon Metro | [MobilityDatabase, 1 May 2026](https://files.mobilitydatabase.org/tld-716/tld-716-202605010025/tld-716-202605010025.zip) | `79480fbe7cedb1c72bba2e2d62245107d7d979d6b1b50d6a7c0c5e8e94815956` |
| Porto Metro | [Municipal archive labelled 7 April 2026](https://dadosabertos.cm-porto.pt/dataset/713a680c-9e19-11f1-84ed-6abdb6d5cf34/resource/28a13723-2af1-4bbb-a2b1-f8b08df8c7e4/download/___) | `c0ff2e53e6fe6bb1e8c78a44e4342faba974a8202acdfd7fbc49a9115d53be06` |

CP has no `feed_info.txt` or shapes; dated calendars are checked explicitly. Fertagus declares April 13–October 13, version `26.10.17` (the source's literal version, not an inferred publication date). Its timestamped April archive is the historical evidence. Current URLs are discovery/update references, not substitutes for these pinned files:

- CP: <https://publico.cp.pt/gtfs/gtfs.zip>, [MDB catalogue](https://mobilitydatabase.org/feeds/gtfs/mdb-2057).
- Fertagus: <https://www.fertagus.pt/GTFSTMLzip/Fertagus_GTFS.zip>, [MDB catalogue](https://mobilitydatabase.org/feeds/gtfs/tld-715).

Explicit agency/product/type checks admit CP rail types 2/109 and Fertagus type 2; no generic fallback imports other transport. Zero malformed timetable omissions. CP international journeys are clipped to the span of Portuguese `94_` stations; Spanish destinations beyond that span are excluded and displayed destinations reflect the retained final call.

## Reuse and attribution

Checked the actual rendered, selected form values on the official Portuguese National Access Point on 19 October 2026:

- [CP NAP record 176](https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/176) identifies the exact `publico.cp.pt` feed and declares **“Sem licença - Sem contrato” / no licence - no contract**, with an empty further-terms field. This is recorded verbatim in metadata; **we do not claim CP is CC BY or CC0**. This declaration is less explicit than a standard open-data licence; retain the source record and recheck before broader commercial redistribution or future updates. CP and the archive are credited.
- [Fertagus NAP record 185](https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/185) identifies the exact Fertagus ZIP and explicitly declares **CC BY 4.0**. Attribution includes Fertagus, archive date and SunTrain selection/simplification.
- [Lisbon Metro NAP record 186](https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/186) identifies the exact `metrolisboa.pt` feed and explicitly states **“Sem licença - Sem Contrato”**. Recorded as no licence / no contract, independently of CP and Fertagus terms; no CC licence is claimed for this newer feed. Its archived dados.gov.pt CC0 listing concerns an older resource.
- Older Lisbon/Transporlis CP/Fertagus entries on dados.gov.pt are CC0 but refer to different resources; their licence is **not transferred** to these newer operator feeds.
- IP geographic data is **CC BY 4.0**, independently of the timetable terms. The dashboard credits Infraestruturas de Portugal, dated source and transformation.

All four operator terms are retained separately in `schedule_licenses`; the merged reference does not relicense CP under Fertagus's terms. No passenger data redistribution or inferred loads.

## Railway geometry

[Official IP national operating railway shapefile](https://dados.gov.pt/en/datasets/rede-ferroviaria-nacional), updated **15 April 2026**. [Pinned download](https://dados.gov.pt/s/resources/rede-ferroviaria-nacional/20260415-171819/rede-ferroviaria.zip), SHA-256 `6065ac244973d192ae705008fe0a6c4fc595b49d74c9f30369fadd22ebef7e19`.

56 non-null operating features become 87 simplified graph ways after conversion from PT-TM06/ETRS89 to WGS84. Junctions use coincident original endpoints/vertices; no proximity joins or new crossing intersections. Existing indexed rail routing matches consecutive CP calls within 150 m and rejects implausible detours. Geometry is geographic inference, not exact operational tracks, platform assignments or a reconstruction of every diversion. A small number of disconnected branches/station offsets remain unresolved.

Fertagus uses its own archived shapes. Two direction patterns contain distance anchors over 150 m from their stations; the established `native_or_ordered_per_leg` option recovers them against the same shape and complete ordered stop sequence. No replacement geometry is invented. Covers all Fertagus legs, including the bridge.

Usable paths cover **118,465 / 121,211 CP scheduled legs (97.73%)** and **11,509 / 11,509 Fertagus legs (100%)** across the week. Missing legs stay empty; moving vehicles are hidden during those intervals. Do not draw straight shortcuts to fill them.

## Lisbon Metro addition

The 1 May 2026 archive declares 1 January–31 December 2026 and contains scheduled stop times, not frequency-based templates. All four line IDs and the exact agency identity/type are checked. 50 distinct station names, 97 shared timing patterns and 104 retained shape legs. **Zero timetable omissions and zero geometry gaps.** The provider shapes are comparatively sparse geographic paths, not exact tunnel or platform tracks; the national IP graph is not reused for the metro.

Metro departures per day: **1,532 / 1,532 / 1,532 / 1,206 / 1,532 / 1,110 / 1,110**. June 4's special service follows `calendar_dates.txt`. The May–July Green Line service variants are selected by their actual calendars; no later extension or timetable is invented. Original overnight calls are kept and each occurrence belongs to one 03:00–03:00 replay day. All four published colours are retained.

The combined week adds approximately **109 KB gzip** over the train-only reference. Metro-only mode downloads only the selected mode/day through the existing endpoint; no new client schedule expansion is introduced. Existing train-only counts, source trip IDs, geometry and operator filters are preserved. Lisbon Metro has its own mode/operator/route filters and appears in Portugal Overview.

## Porto Metro addition

The actual **7 April 2026-labelled ZIP** was downloaded on 19 October 2026 from the [official municipal catalogue](https://dadosabertos.cm-porto.pt/en/dataset/horarios-paragens-e-rotas-metro-porto). Unlike a rolling current feed, this is a separately dated retained file. Its actual calendars run **6 April–19 July 2026**, covering the June week and carry days. There is no `feed_info.txt`; calendar validity is checked explicitly. Catalogue migration/publication in September is not presented as an April capture timestamp.

The [original municipal catalogue](https://opendata.porto.digital/ne/dataset/horarios-paragens-e-rotas-em-formato-gtfs/resource/ef7d2140-5d2d-430f-9593-a51288a40957) lists this same dated April resource and declares **Creative Commons CCZero** for the dataset. The migrated catalogue marks the files public/free access but leaves its licence fields empty; CC0 provenance is therefore linked to the original declaration rather than invented from the migrated fields. Attribution retains “Fonte: Metro do Porto, SA”, source date, retrieval date and SunTrain transformations.

**A, B, B express, C, D, E and F**, 85 distinct station names, 61 shared timing patterns. The one agency has a blank ID, which existing single-agency GTFS handling supports. Only its explicitly selected rail routes/type are enabled; Metrobus/BRT is excluded. B express keeps its actual skipped-stop sequence. No frequency expansion is needed. The source's sparse shapes are used as supplied, not treated as exact operating tracks.

Porto departures per day: **1,153 / 1,153 / 1,153 / 924 / 1,153 / 918 / 870**. Holidays/exceptions, weekend schedules and overnight calls follow the original calendars. **Zero timetable omissions.**

One source defect: shape **CR** begins at Fórum Maia, although some Line C trips start at ISMAI. Those journeys retain four empty northern legs (ISMAI–Castêlo da Maia–Mandim–Zona Indústrial–Fórum Maia); their complete supported suffix is projected onto the **same CR shape**. Other CR trips use normal matching. No reverse-direction shape or straight shortcut is substituted. The opposite direction has its complete supplied shape. Usable paths cover **150,269 / 151,541 scheduled Porto legs (99.16%)**; unavailable positions remain hidden only across the missing part.

Adds approximately **81 KB gzip** over the Lisbon+trains reference. Lisbon and Porto share the metro Transport option, while Operator and Route distinguish them. Existing CP/Fertagus/Lisbon counts and provenance remain intact.

## Reproduce

```sh
# Download the exact IP ZIP above to .cache/portugal/rede-ferroviaria.zip.
# Geometry preparation needs pyshp + pyproj (prep only; no runtime dependency).
PYTHONPATH=.cache/portugal/tools .venv/bin/python scripts/prepare_portugal_geometry.py .cache/portugal/rede-ferroviaria.zip
.venv/bin/python scripts/prepare_portugal_replay.py
.venv/bin/python -m pytest tests/test_portugal.py tests/test_lisbon_metro.py tests/test_porto_metro.py tests/test_rail_preparation.py tests/test_compact_schedules.py tests/test_replay_http.py
```

Hashes are checked before use. Raw downloads and optional preparation packages remain ignored in `.cache/portugal/`. The browser loads only the selected replay day using the existing compressed/cache flow.

## Next time

1. **Longer train period:** find historical CP and Fertagus snapshots covering each added service date and carry day. Recheck source terms, holidays/exceptions, calendar validity, overnight assignment and geometry. Do not simply stretch the date constants or backdate current files.
2. **Metros:** Lisbon and Porto are included. For longer periods, use their dated archives and actual calendars, and recheck later line changes. Porto CR’s missing northern geometry remains documented; improve it only with a verified suitable source.
3. **Trams / other light rail:** scope operators and railway geometry separately; Coimbra/Mondego coverage must follow actual dated service and transport type.
4. **Buses / ferries:** later additions only, with their own dated feeds, operator colours, road/river geometry and download-volume audit.
5. **Passenger features:** public station/operator totals can be documented separately if useful. They do not establish individual train occupancy.
