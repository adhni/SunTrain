# Jakarta rail and TransJakarta busway

## Scope and dates

Select **Jakarta** for **15–21 December 2025**, in **Asia/Jakarta** (UTC+7, no daylight-saving change). KRL coverage includes: Bogor, its Nambo branch, Cikarang/Bekasi via both Manggarai and Pasar Senen, Rangkasbitung, Tangerang and Tanjung Priok. Short workings and published continuation segments retain their actual station calls and train numbers. The six route labels use SunTrain colours matching the familiar line families; Nambo shares Bogor red.

Airport rail and Whoosh are included. Regional diesel services, the Whoosh Bandung feeder and non-BRT buses are not enabled. Both LRT systems are included separately. LRT Jabodebek is included, as described below. TransJakarta busway is optional under Transport. Passenger sizing/heatmaps are unavailable. Existing city playback, filters, service details, Overview, themes and fullscreen are reused.

## MRT North–South overlay

MRT is enabled alongside KRL. It uses [the community GTFS](https://github.com/MuhammadNafishZaldinanda/gtfs-mrt-jakarta) pinned to commit `c39d5b10ffc6a749363477ce7702425b719c1814` (3 May 2026), retained in `data/reference/jakarta/mrt-may-2026.zip` (61,976 bytes, SHA-256 `47fb971e1ac7842a68bacde88f6105f9512b5185767b0615cc98c7f5640255a0`). Its 2019–2030 calendar is an author-created weekday template, **not evidence of historical validity**. The replay explicitly identifies MRT as a **May 2026 snapshot matched by weekday/weekend onto the KRL week**, not December 2025 MRT history. Source periods remain visible in the city description, replay note and metadata. Do not extend the source calendar as if every historic holiday/revision were covered.

The feed includes 13 stations, both directions and the published Blok M short workings. Weekday/weekend counts are **285 / 219**, giving **1,863 journeys** in the displayed week. Eleven shared timing patterns reuse the supplied four route shapes. All MRT legs resolve using ordered projection onto their own route geometry. The evening Lebak Bulus–Blok M short turn is labelled Blok M rather than the upstream generic Bundaran HI headsign. The upstream assumed 30-second dwell is removed: arrival and departure both use the source departure event. No departures are generated from headways.

The official website now serves its station tables through `https://beweb-dev.jakartamrt.co.id/middleware/api/datum` (public query `filters[field][slug]=stasiun`, `pagination[limit]=100`, `locale=id`, header `X-Platform: mrt`). On 20 October 2026, 6,011 of 6,024 non-terminal departure events matched the pinned conversion exactly. Twelve differ by 10–40 seconds; one Blok M weekend endpoint differs (the official table lists the terminating late event and omits the early origin shown by the conversion). We retain the pinned snapshot rather than mix later values into it. Terminal event times and train grouping remain the community conversion, not independently observed train movements. The current station records were updated March–April 2026 and do not establish December 2025 validity.

Conversion licence: **MIT, © 2026 Muhammad Nafish Zaldinanda**; full notice retained in `data/reference/jakarta/MRT-LICENSE.txt`. Operator source rights remain with MRT Jakarta. Shape provenance is OSM relations `9677669` and `9677670`; keep **© OpenStreetMap contributors, ODbL 1.0** attribution alongside the conversion licence. No passenger loads are supplied.

Preparation uses `scripts/prepare_jakarta_mrt.py` and the shared rail converter. Before the LRT addition, the KRL/MRT reference was **121,586 bytes**, with **9,805 departures** (1,429 on weekdays, 1,330 on weekends). Both transport/operator filters work independently. The source ZIP is preparation-only; the browser receives only the selected compact day.

## LRT Jabodebek — Cibubur and Bekasi

Both branches are enabled under **LRT Jabodebek**, with **18 stations**, blue Cibubur (`#21409A`) and green Bekasi (`#006838`). This is distinct from the separately imported LRT Jakarta South Line. The displayed calendar remains the KRL week; LRT uses an explicitly labelled **September 2026 community conversion**, captured **20 October 2026**, matched by weekday/weekend. Source row update dates are 6 September (weekdays) and 27 September (weekends), not proof of the operator’s precise validity interval.

The [official departure page](https://lrtjabodebek.kai.id/jadwal-keberangkatan) is accessible and contains 36 station/day tables, but mixes direction clocks without train identifiers. It is insufficient by itself to reconstruct complete journeys reliably. The public [Commute Data Platform API](https://data.commute.shiorilabs.id/docs), operated by Shiori Labs, supplies licensed station-time groupings via `/stations/LRTJBDB/{code}/timetable?day=WD|SAT|SUN` and route sequences via `/lines/LRTJBDB/CB|BK`. No runtime requests or API keys are required. These grouped IDs are community identifiers, not verified official train numbers.

All **3,242 weekend station events** match the current official tables exactly (Saturday and Sunday use the same source schedule). **5,033 of 5,158 weekday station events** match; 125 differ from the current page. We retain the pinned conversion rather than patching mixed revisions or inventing joins. The normalized source records the comparison, official HTML hash, 54 timetable response hashes and three station/line catalogue hashes.

**Terminal arrival times are absent in this dataset.** Each included journey therefore covers its contiguous origin-to-penultimate station calls: 11 calls for Cibubur and 13 for Bekasi. Arrival/departure use the same published station event, with no invented dwell. The advertised destination is retained, but animation ends at the last supported call. A short selected-service note and replay note explain this. No guessed final-leg duration, headway-generated train departures or artificial terminal arrival is added.

Daily journeys: **430 on weekdays** (216 Cibubur, 214 Bekasi), **270 on Saturday/Sunday** (134 Cibubur, 136 Bekasi), **2,690** over the displayed week. Source sequences are checked for missing/duplicate stations and increasing times. Railway geometry comes from native OSM route relations **16036440, 16036441, 16079478, 16079479**; the connected graph uses native node IDs, with no straight connectors. Every included timed leg has a track path. Missing terminal legs remain absent rather than being presented as timed travel.

Committed preparation references:

- `lrt-jabodebek-2026-10-20.json.gz`: **44,183 bytes**, SHA-256 `fcd5394fd05c965f0ae22ad7c8c0afdde3989eeb17fbc66d68c73b2f6881c6b8`.
- `lrt-osm-2026-10-20.json.gz`: **4,734 bytes**, SHA-256 `7a5a2485dcf8d1c6aeae32f9a535ff5d7d7779193a3644eb49871388529d69b6`.

The converted station-time database is **ODbL 1.0**, as stated by Commute Data Platform; the independently retained source reference and its derivatives preserve that licence, attribution and source URLs. Operator source attribution remains KAI / LRT Jabodebek. Geography is **© OpenStreetMap contributors, ODbL 1.0**. This does not relicense KRL’s original publication or the MRT conversion. Keep the individual source references/licences when redistributing.

`scripts/prepare_jakarta_lrt.py` reads those pinned references and reuses the existing railway graph and shared schedule encoding. The normal Jakarta preparation command now merges KRL, MRT and LRT offline. `--prepare-sources` regenerates references from the audited local API/OSM cache and prints new hashes for review; never silently accept newer API data as the old snapshot.

Before adding LRT Jakarta, the combined rail replay was **150,668 bytes gzip**, **12,495 journeys**, **1,859 on weekdays / 1,600 on weekends**. Buses remain separate and optional. Tests cover source pins, original calls, calendars, both branches, shared paths and independent mode filtering. Browser checks cover both route filters, colours, playback and the terminal-time note.

## LRT Jakarta — official September 2026 publication

The separate **LRT Jakarta South Line** is enabled alongside Jabodebek. Choose **LRT Jakarta / Jabodebek** under Transport, then **LRT Jakarta South Line** under Route, or select its operator under More filters. Route colour is orange `#F26324`. No extra filter or runtime system is introduced.

The operator’s [official Linktree](https://linktr.ee/lrtjkt) links to a public [timetable folder](https://drive.google.com/drive/folders/1gZnM3zLUC1wwksAzZXhnL-4vR-LchaLO). The downloadable file is **Jadwal LRT Printable 18 September 2026.pdf**, explicitly **valid from 19 September 2026**. [Pinned PDF download](https://drive.google.com/uc?export=download&id=1mBXkx0-9OHVZCXrU-1FCK2yzHjCZMcfh): **161,455 bytes**, SHA-256 `719a9e1ef4a1813b6d7ae7d4b129cc64bcf938e2db8b07e15b31596a5a9e8892`. One page, two main ruled tables, original train numbers and printed station times. Raw PDF stays preparation-only.

The edition serves **eight stations**: Kelapa Gading (formerly Pegangsaan Dua), Boulevard Utara Summarecon Mall, Boulevard Selatan, Pulomas, Equestrian, Velodrome, Rawamangun and Manggarai. **Pramuka, Matraman and Proklamasi are explicitly `Ls.` pass-throughs**, so they are not passenger calls or stop dots in this replay. Their alignments remain part of the track path. Do not turn the website’s eleven-station catalogue or OSM stop positions into eleven stopping stations for this timetable.

**146 daily published journeys:** 72 southbound and 74 northbound. Of these, 116 run between Kelapa Gading and Manggarai (57 southbound, 59 northbound). Thirty have shorter printed call sequences: 15 southbound end at Equestrian, and 15 northbound begin at Velodrome. Dashes remain absent calls; no unprinted Velodrome time is added to the southbound short workings. Full journeys include their actual terminal times, unlike the separate Jabodebek source. There is no assumed dwell and no generation of departures from the regular-looking intervals. The publication prints one daily table with no weekday/weekend split. Its September timetable is explicitly overlaid on the existing KRL display week; it is not claimed as December 2025 history.

`prepare_jakarta_lrt_city.py` extracts ruled PDF cells with the same preparation-only pdfplumber tooling used for KRL. It preserves `Ls.`, dashes, train IDs, both directions and source date. The community API was inspected, but its list and routing catalogue disagree about station coverage and its departure count differs from this PDF; that timetable is **not imported**. Source colour `#F26324` follows its LRT Jakarta line catalogue, rather than a Melbourne vehicle default.

Native OSM route relations **10693160** (southbound) and **10693119** (northbound), discovered through route master **10693161**, cover the extension to Manggarai. Each direction retains its own connected ways and actual stop-position nodes, so the two physical tracks are not joined by nearest-coordinate guesses. Every included timed leg resolves along tracks, including Rawamangun–Manggarai through the three non-stopping stations. Geography is **© OpenStreetMap contributors, ODbL 1.0**. Timetable is attributed to **PT LRT Jakarta**, with source rights retained; no open licence is invented for the operator PDF.

Pinned preparation references:

- `lrt-jakarta-timetable-2026-09-19.json.gz`: **4,294 bytes**, SHA-256 `858c0917d413ed79b33b3f131f49512545ef028c9a0ee21b60a9ffb387e44b3a`.
- `lrt-jakarta-osm-2026-10-20.json.gz`: **3,377 bytes**, SHA-256 `04e260e8ea949268e341e631b67b189d0f7dc28f925a3b7da5616fc3673ec5b9`.

The normal `prepare_jakarta_replay.py` command rebuilds the combined replay offline. To repeat source preparation with the exact downloaded files:

```bash
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_jakarta_lrt_city.py --extract-pdf
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_jakarta_lrt_city.py --prepare-geometry
```

LRT Jakarta adds **1,022 journeys in the displayed week** and about **10 KB** to the runtime reference. Before airport rail and Whoosh, the combined rail file was **160,538 bytes gzip**, **13,517 journeys**, **2,005 on weekdays / 1,746 on weekends**. Five shared LRT Jakarta timing patterns reuse four stop/path sequences. Tests cover PDF pass-throughs/dashes, original numbers and terminal times, short workings, source pins, mapped tracks and independent operator/route filtering. Browser checks cover the extended route, both directions and playback.

## Airport rail and Whoosh

Choose **Airport rail / Whoosh** under Transport, then the individual route. Existing playback, speed/route/operator filters, station details and fullscreen are reused. Airport trains use operator **KAI Commuter** and purple `#262262`; Whoosh uses **KCIC / Whoosh** and its mapped dark red `#8C0023`. The default bounds now include Greater Jakarta and the full Whoosh route to Bandung. Use Fit selection for a closer view of a selected route.

### Soekarno–Hatta Airport Rail Link

The official **1 September 2025** KAI Commuter PDF is preserved in the Internet Archive (capture **6 December 2025, 18:07:18**): [original operator URL](https://www.commuterline.id/files/download/documents/Jadwal%20Commuter%20Line%20Basoetta%20-%20Update%201%20September%202025.pdf), [archived download](https://web.archive.org/web/20251206180718id_/https://www.commuterline.id/files/download/documents/Jadwal%20Commuter%20Line%20Basoetta%20-%20Update%201%20September%202025.pdf). Direct operator downloads returned 403; the archived PDF is accessible. **101,279 bytes**, SHA-256 `1456e5726d345ea3e550a7343e3b38fd67d45128cb448cac91b49739e1942c38`. Its SHA-1 matches the archive’s CDX digest (`IAL6LWPEHBHY56R4QC2BAVNNUQQTBTFO`).

Two ruled tables contain **70 logical journeys**, 35 each way, with **six calls**: Manggarai, BNI City, Duri, Rawa Buaya, Batu Ceper and Soekarno–Hatta Airport. Published number pairs such as **801A / 802A** represent one journey, counted once using the first number while retaining both in the source. The source gives one event per station; no dwell is invented.

Six journeys are explicitly cancelled on the listed September weekend dates. We use the actual source week **15–21 September 2025**, mapped to the display week’s weekdays: **70 Monday–Friday, 64 Saturday/Sunday**, **478 in the week**. Cancellation dates remain explicit rather than being applied indiscriminately to other months. This is not claimed as a December 2025 airport timetable. Today’s OSM relation also contains Sudirman; that station is **not added** to this older PDF’s six-call schedule.

### Whoosh Jakarta–Bandung

Primary source: **KP-DJKA 2 Tahun 2025**, issued **22 January 2025**, effective **1 February 2025**. [Official government PDF](https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%202%20Tahun%202025_GAPEKA%20KA%20KECEPATAN%20TINGGI%20JAKARTA%20-%20BANDUNG.pdf), [archived download](https://web.archive.org/web/20250131154742id_/https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%202%20Tahun%202025_GAPEKA%20KA%20KECEPATAN%20TINGGI%20JAKARTA%20-%20BANDUNG.pdf). **62 pages, 2,053,338 bytes**, SHA-256 `0f411bc301d2c2642eada213b09c3e7c680d8d78e975587af57602779fe0f366`; SHA-1 matches archive digest `NBGK3WHEHRK6Y6KKKXWEVYFW5OA3E5HS`. The government host was inaccessible here; the authentic January archive was downloaded and parsed.

Only the relevant passenger tables are converted: regular scenario **A, pages 14–24**, and Sunday maintenance scenario **C, pages 39–49**. The [KCIC announcement dated 10 October 2025](https://kcic.co.id/kcic-siaran-pers/pastikan-standar-keselamatan-tetap-maksimal-kcic-sesuaikan-jadwal-whoosh-di-hari-minggu-menjadi-mulai-08-00/) confirms **62 journeys Monday–Saturday and 56 on Sundays**, with first Sunday departures at **08:00 from Halim / 07:35 from Tegalluar**. The regular table starts at **06:25 / 06:05**. The imported schedules retain those rules: **428 journeys over the display week**. Do not enable optional `F` services, alternative additional scenarios, confirmation trains (`DJ`) or depot movements as daily passenger trains. Source calendars are planned schedules, not a record of actual disruption/cancellation.

Four stations are represented: **Halim, Karawang, Padalarang, Tegalluar Summarecon**. Some journeys pass Karawang without stopping (`Ls`); those journeys have three passenger calls and follow the same railway alignment through Karawang. Actual arrival/departure pairs are retained, including the published two-minute Karawang and three-minute Padalarang dwell where applicable. No synthetic intermediate stops or times are added. The Bandung–Padalarang feeder is not Whoosh and remains excluded.

### Geometry, storage and reproduction

Native OSM directional route relations **17675694 / 17675695** supply airport railway tracks and stop positions; **12150229 / 12150230** supply the full Whoosh high-speed route. Each direction is routed on its own connected native ways, never a road/rail mix or a straight station connector. All included timed legs resolve. A complete Whoosh journey is approximately **141.35 km** along the mapped path. October 2026 geography is an alignment reference, not proof of exact historical platform assignments.

Timetable attribution remains KAI Commuter and DJKA / PT KCIC; published source rights are retained, with no invented blanket open licence. Geographic database: **© OpenStreetMap contributors, ODbL 1.0**. Source URLs, archive URLs and raw PDF hashes are retained in the reference and attribution metadata.

Pinned preparation references:

- `airport-whoosh-timetables-2025.json.gz`: **6,266 bytes**, SHA-256 `b728a6edb5797c9dee305c4f114c5a01fd54cd4267f544bff12b5ea65ddb8d64`.
- `airport-whoosh-osm-2026-10-20.json.gz`: **18,907 bytes**, SHA-256 `fe75d1314d652d8aba59ac23481576f04635de5145995374396912761ffd9640`.

`prepare_jakarta_intercity.py` normalizes both PDFs and compiles native geometry; the normal Jakarta replay build merges these sources offline. To regenerate audited inputs:

```bash
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_jakarta_intercity.py --extract-pdf
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_jakarta_intercity.py --prepare-geometry
```

Raw PDFs/OSM responses remain in the ignored preparation cache. No upstream requests or PDF tooling run on the site. Added runtime size is approximately **17.5 KB gzip**. The combined rail week now totals **177,992 bytes**, **14,423 journeys**: **2,137 Monday–Friday / 1,872 Saturday / 1,866 Sunday**. Optional bus bundles are unchanged and loaded separately. Tests verify original events, date-specific cancellations, Sunday maintenance, pass-throughs, real dwell, source pins, route lengths, native paths and bounds. Browser checks cover both routes, train numbers, source colours, playback and Sunday counts.

## Optional TransJakarta busway

Select **TransJakarta busway** under Transport. Scope is the feed’s **BRT** category: **32 routes**, including corridors 1–14 and connecting/express BRT services. Ordinary feeder buses, Mikrotrans, Royaltrans, tourist, housing-estate and Transjabodetabek services are excluded. Route colours come directly from this city’s feed; Melbourne bus orange is not used as a fallback.

Source: [official TransJakarta GTFS](https://gtfs.transjakarta.co.id/files/file_gtfs.zip), retained in [MobilityDatabase’s 7 May 2026 archive](https://files.mobilitydatabase.org/mdb-1909/mdb-1909-202605070137/mdb-1909-202605070137.zip). Download verified: **5,328,559 bytes**, SHA-256 `d6b6db4823b8bfdc11e98f44229bf7afdb797ea85fc96a0a269cb856bc439023`. The archive is pinned and reproducible; the raw ZIP is preparation-only and not committed. Its very broad calendar is not historical validity evidence. As with MRT, its weekday templates are explicitly displayed on the KRL week; this is **not December 2025 bus history**.

**Timing limitation:** all **161 selected BRT templates** use `frequencies.txt` with `exact_times=0`. The optional map illustrates the published service levels by placing representative buses at those headways. These are **frequency-based estimates, not exact scheduled or observed individual departures**. This distinction appears in the city description, replay note and selected-bus details; each pattern carries `frequency_based=true`. Synthetic occurrence identifiers contain `:estimate-`, not vehicle fleet numbers. Feed stop-to-stop timing and dwell values are retained as estimates, without claiming observed driving or dwell times. No passenger loads are invented.

The selected archive includes weekday/weekend/Sunday calendars and overnight frequency windows. Instances use half-open start/end windows and belong to one 03:00–03:00 replay day by their origin departure. Friday/Saturday differences can include the following civil morning. No last-day holiday exceptions or historic diversions are inferred. Non-exact frequency support is confined to this explicitly illustrative importer; other rail/bus converters continue rejecting such feeds by default.

Geometry: official trip-specific road shapes, with ordered stop projection because several upstream `shape_dist_traveled` anchors are inconsistent. All selected template legs resolve on their own road shapes; no railway paths or straight connectors are substituted. Keep unresolved sections as gaps if future source revisions fail projection.

Licence verified directly on the [official PPID page](https://ppid.transjakarta.co.id/informasi/berkala): **GTFS Static Transjakarta © 2026 PT Transportasi Jakarta, CC BY 4.0**. Metadata and the existing attribution footer preserve publisher, archive, licence link and an indication of changes (BRT selection, compaction and illustrative headway departures).

Daily illustrative occurrences: **15,073 / 15,073 / 15,073 / 15,073 / 15,043 / 14,250 / 15,534**; **105,119** over the displayed week. These are simulated service occurrences, not unique physical buses or actual historical trip totals. Seven independent daily bundles total **1,938,095 bytes gzip**, with only **273–288 KB** loaded for a selected bus day. Rail-only remains the default and never opens a bus bundle. All occurrences reuse compact stop/timing patterns; schedules are not expanded per bus.

Rebuild with:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_jakarta_busway.py
```

The importer verifies the archived ZIP hash, reuses the shared road-shape/timing preparation, then constructs explicitly labelled frequency estimates and writes daily bundles. It rejects missing/overlapping frequency windows or unexpectedly exact services rather than silently changing their meaning. Tests cover scope, colours, half-open frequency windows, overnight ownership, source pins, optional loading and shared schedules. Browser checks cover selection, frequency labels, road paths and playback.

## Actual KRL timetable source

The source is KAI Commuter's official **13 December 2025** timetable PDF:

- [Official PDF](https://commuterline.id/files/download/documents/Jadwal%20Commuter%20Line%20Jabodetabek%20-%20Update%2013%20Desember%202025.pdf).
- **571,618 bytes**, SHA-256 `dc53b5b96b19afcf6ed4c7c86ab7ac9655810b0d27e5879b1183fb2ea9666901`, **13 pages**.
- The user supplied a local copy after the operator's Cloudflare-protected download returned HTTP 403 in this environment. Preparation verifies that copy's exact hash. The raw PDF is not committed or downloaded by the running site.
- Replay dates follow the edition date and precede the Christmas holiday period. The [official 2025 holiday publication](https://setkab.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025/) was checked; the selected week and carry dates contain no national holiday. Extending dates requires a new holiday/revision audit.

No usable official KRL GTFS archive was validated. `scripts/prepare_jakarta_timetable.py` reads the PDF's **actual ruled table cells with pdfplumber**. Blank branch columns, pass-through `Ls` cells, side-by-side Tanjung Priok tables and Cikarang loop branches keep their proper alignment. Flattened PDF text is unsuitable here.

The PDF contains **1,145 published rows**; **1,144** are usable. Train **5020A**, page 7 row 13, has an additional clock value in the remarks cell and ambiguous station alignment; that row is recorded in `omitted_rows` and excluded rather than repaired. The extraction fails on unknown clock cells, duplicate primary train numbers, backwards times and unexpected headers.

- **33** rows explicitly say `Sabtu/Minggu/Libur Nasional Batal`; they run on weekdays and are excluded on Saturday/Sunday. Suffix letters alone never determine the calendar.
- Trains **7100/7101** explicitly operate through **31 December**; their expiry is retained.
- Notices that passenger service begins at Sudirman or Matraman remove preceding positioning calls. Continuation notes never invent additional stops or times.
- `5505B - 5506` and other Full Racket descriptions retain the primary number for that published segment. The continuation has its own published row; the converter does not fabricate a whole-loop journey or count a composite label as another train.
- A published station time is one event. Arrival and departure use that same instant; no dwell durations are invented. Midnight rollovers retain extended clock values. Each occurrence belongs to one 03:00–03:00 business window according to its first passenger departure.

The preparation-only normalized timetable is `data/reference/jakarta/timetable-2025-12-13.json.gz`. It preserves source pages, row numbers, notes and extracted cells for review. Runtime reads only the compact replay file, never PDF tooling or the normalized source.

The community [mini-jabodetabek project](https://github.com/stndaru/mini-jabodetabek) was useful for discovering OSM relation IDs. Its mixture of PDF/API schedules, approximate station coordinates and stitched track polylines was **not imported**. Headway-based community examples are not a source of individual departures.

## Railway geometry

`data/reference/jakarta/rail-osm-2026-10-20.json.gz` is a compact ODbL reference built from the public OSM API. It retains native way/node connectivity, simplifies between preserved junctions and locates the timetable's **83 passenger stations** from real OSM features. Gambir's `Ls` pass-through is not a passenger call.

Seven route relations supply the network: `16877210`, `16877211`, `15094545`, `2922163`, `15094546`, `17193463`, `17193008`. OSM node `1228345121` supplies Pondok Rajeg, and way `605535396` supplies the historic Karet station location. A small native map extract supplements actual junction tracks at Tanah Abang. Every source URL and raw SHA is recorded in the derived reference and pinned in the geometry script.

Routing reuses the indexed connected railway graph used for other national imports. Calls must anchor within **150 m**, and implausible detours are rejected. There are no nearby-coordinate joins or straight connectors across missing sections. October 2026 geography is an alignment reference for December 2025 schedules, not proof of the exact platform/running track or a record of historic diversions. Stop locations can represent a physical station complex rather than a particular platform.

Geography: **© OpenStreetMap contributors, ODbL 1.0**. Preserve the source pins, licence and derived reference when redistributing geographic data. Timetable information remains attributed to **PT Kereta Commuter Indonesia / KAI Commuter**; no blanket MIT/CC BY licence is asserted for the operator's publication. No third-party software licence is substituted for the original timetable rights.

## Validation and storage

Daily passenger departures Monday–Sunday are **1,144 / 1,144 / 1,144 / 1,144 / 1,144 / 1,111 / 1,111**, **7,942** in total. The source's original segments are counted, not unique physical trainsets.

The KRL-only component before the MRT merge is **98,826 bytes gzip**, with **1,144 shared timing patterns** and **73 shared stop/path sequences**. The preparation-only normalized source is **78,102 bytes** and the OSM reference **29,725 bytes**; runtime reads neither preparation file. All **122,468 scheduled legs** have connected track paths after the Tanah Abang junction supplement. This measures mapped alignment coverage, not proof of the exact historic running track.

Tests cover ruled-cell branch alignment, pass-throughs, passenger-only origins, weekday restrictions, temporary-service expiry, overnight rollover, duplicate occurrence ownership, original PDF examples, shared schedule/path references, city/date validation and unsupported transport modes. Chrome checks cover route filters, service details, Overview, dates, 2,000× playback, themes and fullscreen. Shared timetable and JavaScript playback/Overview suites also pass.

## Reproduction

The committed normalized KRL timetable, geography and pinned MRT ZIP allow combined replay rebuilding without contacting any upstream service:

```bash
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_jakarta_replay.py
```

To repeat the PDF extraction, retain the exact source PDF locally and install **preparation-only** pdfplumber 0.11.4 (used here with Python 3.11). It is not an application/runtime dependency:

```bash
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_jakarta_timetable.py \
  '.cache/jakarta/timetable-december-2025.pdf'
./.venv/bin/python scripts/prepare_jakarta_geometry.py --cache .cache/jakarta
```

The geometry command requires the raw OSM extracts listed in `SOURCE_PINS`, with the exact audited hashes. Do not silently replace them with newer API responses. Updated PDF or OSM inputs need inspection and new pins. Do not expand this timetable's calendar merely by changing the period constants.

## Next additions — sources only

These are starting points from the brief, not validated historical imports:

1. **MRT historical refinement:** replace the explicitly dated snapshot overlay if a genuine operator-dated complete historical timetable becomes available. Do not treat the broad community calendar as historical proof.
2. **LRT Jabodebek refinement:** obtain an authentic operator-dated, complete trip timetable including terminal arrivals. Replace the current documented partial station-time coverage when available; do not fill terminal times from headways.
3. **LRT Jakarta updates:** retain the dated original when updating timetables, and check whether the three pass-through stations have begun accepting passengers. Do not assume every mapped station was served in an older timetable.
4. **Airport rail updates:** obtain a dated newer PDF before extending calendar coverage or enabling extra stations such as Sudirman. Do not carry September cancellation dates into unrelated months.
5. **Whoosh updates / Bandung feeder:** validate revised operator schedules and maintenance rules separately; do not enable conditional `F` runs without an operating calendar. The Bandung feeder and other regional trains need their own operator/source scope.
6. **Passenger data:** operator/provincial statistics could provide station/day or network totals after validation. No individual train boarding, alighting or onboard-load dataset was validated; passenger features remain disabled.

Keep future operators' actual source dates explicit. Their historical periods may differ from this KRL week; do not relabel current schedules as December 2025. Non-BRT buses remain out of scope.

## Java-wide view

The separate **Java** view now reuses this existing Jakarta reference in place: default Whoosh/airport rail and optional KRL/MRT/LRT. Its intercity source week is **3–9 February 2025**; Jakarta dates are explicitly mapped by weekday from 15–21 December (retaining all operator-specific source overlays). Nothing under `data/reference/jakarta/` is duplicated, and this Jakarta view/date range is unchanged. See [Java expansion notes](JAVA_EXPANSION_NOTES.md) for the government intercity source, scope and remaining regional additions.
