# Java railway expansion

## Implemented scope

Select **Java**, **3–9 February 2025**, Asia/Jakarta (UTC+7, no DST). This is the first complete Monday–Sunday week after GAPEKA 2025 took effect on 1 February. The new intercity layer contains **253 published train-number sections per day**, **1,771 in the week**, and **78 service names**. Coverage includes both north/south mainline corridors, Bandung, Cirebon, Semarang, Purwokerto, Yogyakarta, Solo, Madiun, Surabaya, Malang, Blitar, Jember and Banyuwangi/Ketapang, and intermediate passenger calls in the source.

Intercity and **Regional / commuter trains** open together by default. The train option includes intercity services, the Bandung–Padalarang feeder, YIA and Adi Soemarmo airport rail, plus the already stored Whoosh and Soekarno–Hatta airport rail. Optional Jakarta KRL, MRT and both LRT networks reuse `data/reference/jakarta/2025-12-15.json.gz`. No Jakarta timetable or railway file is duplicated under Java. Jakarta buses are excluded from the Java view. The separate Jakarta replay remains unchanged.

Java displays 3–9 February. The reused Jakarta source week is 15–21 December 2025, matched by weekday. Jakarta’s own airport/MRT/LRT source overlays retain their original September 2025 / May–September 2026 periods. These combined layers are explicitly labelled weekday overlays, not simultaneous February history. See [Jakarta source notes](JAKARTA_EXPANSION_NOTES.md).

Default daily counts including the new regional services and reused airport/Whoosh: **681 Monday–Friday, 675 Saturday, 669 Sunday**; **4,749 across the week**. With all optional Jakarta rail: **2,686 Monday–Friday, 2,421 Saturday, 2,415 Sunday**. The train-only option has 515 / 509 / 503 services, including the reused Jakarta airport/Whoosh layer. Each day owns departures in its single 03:00–03:00 window. The slider continues until the last arrival of those journeys, including afternoon arrivals on the next calendar day. Departure ownership prevents adjacent-day duplication.

## Bandung feeder and airport rail — implemented

All three use the same official GAPEKA 2025 PDF and **3–9 February 2025** source week, with fully published station-event tables. They are compiled into the existing Java train reference; no new Transport mode or network infrastructure is added. Use Route / line to select them:

| Route | Operator | Journeys/day | Published coverage |
| --- | --- | ---: | --- |
| Bandung–Padalarang Feeder | KAI | 72 | Bandung–Cimahi–Padalarang, both directions |
| YIA Airport Rail | KAI Bandara / Railink | 48 | Yogyakarta–YIA, 24 via Wates and 24 nonstop |
| Adi Soemarmo Airport Rail | KAI | 10 | Adi Soemarmo–Kadipiro–Solo–Madiun, both directions |

**130 added departures per day / 910 in the week.** These are explicit original train tables, not departures generated from their apparent headways. All **297 additional passenger legs** have connected railway geometry: the feeder is approximately **14.78 km**, YIA **40.17 km**, and Adi Soemarmo–Madiun **110.83 km**. The existing Java OSM file and native graph are reused; no geography is downloaded or stored a second time.

Source extraction checks **132 original tables**, validates each regular service’s origin/destination/first departure/final arrival against the document’s contents, and excludes conditional **547F / 548F**. It reads ruled station-event cells so the multi-line `Yogyakarta International Airport (YIA)` name stays attached to the correct time. Rows continued across pages retain their source sequence. Normalized source file `connections-timetable-2025.json.gz`, **7,911 bytes**, SHA-256 **`635502480e8eb8ec0849572987356552ad5d32cd851c8187ba6b9fd36e22e213`**.

- **Feeder:** original numbers **601–672** (36 each direction), passenger calls Bandung/Cimahi/Padalarang, **18 minutes** total with the actual **two-minute Cimahi dwell**. Conventional Padalarang is separate from the Whoosh station/track positions. The feeder is a distinct KAI service, never part of a Whoosh vehicle or an invented continuation. Government table instructions and [KCIC’s 25 January 2025 announcement](https://kcic.co.id/kcic-siaran-pers/tiket-whoosh-jadwal-baru-1-februari-sudah-bisa-dibeli-kcic-siap-operasikan-62-perjalanan-per-hari/) establish the dated February timetable context; the announcement does not supply our station clocks. Existing Whoosh retains its separately labelled source overlay and Sunday rules; no guarantee of connections across those different source periods is implied.
- **YIA:** original numbers **521–570**, excluding **547F/548F**. Two passenger-call patterns: Yogyakarta–Wates–YIA and Yogyakarta–YIA. Wates remains a pass-through on nonstop trips, and Kedundang is a routing hint, not an invented passenger stop. Stopping trains retain the actual two-minute Wates dwell. Airport terminals use their printed arrival/departure event without invented dwell.
- **Adi Soemarmo:** numbers **571–580**, five each direction. The February source runs through **Madiun**, retaining Solo Balapan/Solo Jebres and other scheduled calls. **Palur is a passing point**, and later **Caruban** extensions are excluded. Nine trips have nine calls; **577** additionally stops at Geneng, retaining its original 08:32–08:50 dwell and the following Ngawi dwell. Later operator announcements, including the [17 August 2025 Palur addition](https://www.vritimes.com/id/articles/594aec5f-8a40-425a-b3f0-c07240c70ae6/47a0971a-a3e9-44aa-8b9e-f6eca906b4ff), must not be applied backwards to February.

The source/publication rights remain DJKA/KAI, with operator identities KAI and KAI Bandara / PT Railink. Colours are SunTrain presentation choices. Railway geography remains © OpenStreetMap contributors, ODbL 1.0. Full government original/archive URLs and raw PDF checksum are inherited from the intercity source; no new timetable licence is invented.

`prepare_java_connections.py` extracts this pinned normalized source. Routine `prepare_java_replay.py` builds the main train reference from the original 253 intercity sections **plus 130 connection services**, preserving all original intercity identifiers. The main reference now has **383 departures/day / 2,681 across the week**, **3,350 mapped passenger legs**, and is **449,405 bytes gzip** — only **8,448 bytes** larger than the preceding intercity-only file. The regional reference and Jakarta file are unchanged. The separate Jakarta view does not duplicate or silently import these new Java services.

Validation covers exact original train-number sets, conditional exclusions, passenger calls versus passing points, wrapped airport cells, source dwell/terminal times, operator filters, airport branch geography, separate feeder/Whoosh identities, compact shared patterns, default/combined/Sunday counts and unchanged Jakarta replay. Browser checks cover all three route filters, a YIA nonstop variant, airport operator selection, service details, mapped paths and playback.

## Regional / commuter networks — all four implemented

**166 journeys per day / 1,162 across the week**, representing **190 regular published train-number sections**. Source number coverage is reconciled exactly against the government tables. Combined number pairs are one through journey, not two vehicles; no constituent number is imported again.

| Region | Included services | Journeys/day |
| --- | --- | ---: |
| Merak | Rangkasbitung–Merak | 14 |
| Bandung / West Java | Bandung Raya, Garut, Walahar, Jatiluhur, Siliwangi | 64 |
| Yogyakarta / Solo | Yogyakarta–Palur KRL and Prameks Yogyakarta–Kutoarjo | 37 |
| East Java | Dhoho, Penataran, Supas, Jenggala, Arjonegoro, Blorasura, Pandanwangi | 51 |

Dates remain **3–9 February 2025**. Merak, Walahar/Jatiluhur, Siliwangi, Yogyakarta KRL, Prameks and Pandanwangi use the original government arrival/departure pairs. All regular selected tables are complete. Six optional government entries **511F, 512F, 730F, 731F, 732F, 733F** are excluded because actual operating dates are unconfirmed; no weekly activation is invented. There is no source weekday/weekend restriction on the included regular services in the selected baseline week. Airport trains, Whoosh feeder, Kedung Sepur and Batara Kresna are outside this four-network import.

Government Bandung/Garut tables and several East Java tables leave intermediate stops as `Berh Sb`. Instead of guessing times or mixing partial revisions, **complete operator-published journey tables** are used for Bandung Raya/Garut and the six East Java commuter families. These official KAI Commuter files are identified as effective **1 February 2025**, preserved in the Internet Archive:

- **Merak:** `Commuter Line Merak -Mulai 1 Februari 2025-.pdf`, capture **20251206175708**, 74,572 bytes. SHA-256 `ca594e81c59281b2e4e4ee7542f5a512e613c292205707115d40c7bfc9c4efbb`, CDX SHA-1 `5QWK6UQUMBPTKYYLU26WKWVIYXEP2FSM`. Kept as an operator reference alongside the fully timed government Merak tables.
- **Bandung:** `Commuter Line Wilayah 2 Bandung - Mulai 1 Februari 2025.pdf`, capture **20251207034821**, three pages, 263,244 bytes. SHA-256 `335635a2240a51beab1354b0611e26d70ade64712806f1f229fab92c646ab2ad`, CDX SHA-1 `OV6PYWEDQEDZWR6PIDYIEZ43XQXVXST3`.
- **Surabaya:** `Commuter Line Wilayah 8 Surabaya -Mulai 1 Februari 2025- -1-.pdf`, capture **20251206183020**, five pages, 278,697 bytes. SHA-256 `0ed22bed8f2fc069db590b7072d6a51ecac7472e58019a1ade4e745dc1960fb6`, CDX SHA-1 `HGIB5Q4TCCW2IAXMOSX4AALEWHIWEATJ`.

All three raw PDF SHA-1 values match the archive CDX records. Exact original/archived URLs and SHA-256 pins are in `scripts/prepare_java_regional.py` and normalized-source metadata. Raw PDFs remain in `.cache/java/regional/`.

The operator PDF supplies one station event per column unless explicit arrival/departure fields are printed; single events have arrival=departure, with **no invented dwell**. Arjonegoro's printed arrival/departure pair at Surabaya Pasarturi is retained. The government tables keep their genuine dwell pairs. Blank and pass-through entries do not become station calls.

The pinned Jenggala PDF has two clear station-code typos: **Wonokromo printed WR → WO**, and **Mojokerto printed SDA → MR**. Names and the government station sequences establish these identities; no station location is guessed. Garut's crowded header glyphs are read using the pinned printed column order. These small source corrections are recorded in metadata.

Dhoho and Penataran can revisit Surabaya Kota, Wonokromo, etc. during a whole through journey. The shared Java builder now resolves each station **occurrence in order**, preserving the full loop instead of looking up the last occurrence of a station code. Selected Dhoho **401–402** has 48 station calls and approximately **353 km** of connected native railway path. Through services are never expanded into duplicate vehicles.

All **2,106 regional passenger legs** have track geometry. The existing OSM file/graph is reused without adding another railway extract or geometry bundle. Regional schedules occupy one compact week file, opened independently when that mode is selected. Regional-only replay does not read the intercity or Jakarta files. Default combined views read each selected source file once and maintain separate namespaced patterns/topologies. No Jakarta KRL data is duplicated.

## Official historical timetable

- **KP-DJKA 224 Tahun 2024**, issued 30 December 2024; GAPEKA Java 2025 effective **1 February 2025**.
- [Original government PDF](https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%20224%20TAHUN%202024_GAPEKA_JAWA.pdf).
- [Accessible archived government PDF](https://web.archive.org/web/20250127040629id_/https://djka.kemenhub.go.id/uploads/202501/KP-DJKA%20224%20TAHUN%202024_GAPEKA_JAWA.pdf), captured **27 January 2025, 04:06:29 UTC**.
- Raw file `.cache/java/gapeka-java-2025.pdf`, **1,721 pages**, SHA-256 **`8dd51fe4f71309ed3f5d49eb0ca018e2c5168e11758c91910818c5948328d23b`**.
- PDF SHA-1 **`MXL7F3WHHGHG5BR6QZG3YT67J2GLUY7N`** matches the archive CDX digest. Government PDF downloaded and parsed, not merely archive metadata.

The intercity contents enumerate **297 train-number sections** (numbers 1–300, including conditional suffixes and the source’s numbering gaps). The detailed tables are fully reconciled against the contents: section identity, terminal codes, departure and final arrival. Visual PDF row order is essential: several PDF objects store their table header after their rows. `pdfplumber` visual text avoids attributing these rows to the preceding train. Source row sequences and terminals are validated, including tables continued on subsequent pages.

**36 conditional/fakultatif F sections are omitted**, since activation dates are unavailable. **Eight Pangrango sections, 223–230**, have passenger calls at Karangtengah/Cigombong marked `Berh Sb` without times; these sections are omitted instead of inventing timings. The normalized source records every exclusion. No freight, depot, positioning or tourism-only service is imported. No claim is made that every optional train ran during the selected week or that later 2025 revisions are covered.

Published arrival/departure pairs and seconds are retained; midnight is unwrapped across the whole route. `Ls` rows are passing points and never passenger stops. Passing stations guide geometry, including those without published pass times. Train numbers sometimes change at a junction (Harina, Pandalungan, etc.): retain the numbered source sections. At a shared boundary, the preceding section ends at its arrival and the following section begins at its departure, avoiding duplicated dwell. These section counts are not unique physical trainsets. Route colours are consistent SunTrain presentation colours, not claimed official KAI line colours. Individual passenger counts are unavailable.

## Railway paths

[Geofabrik Java extract](https://download.geofabrik.de/asia/indonesia/java-261018.osm.pbf), **18 October 2026**, raw SHA-256 **`31fb514159bf252515a95de0b4e47d92f00c1b34d1940477cf5c1de3dcf0d93a`**. The ~898 MB PBF is preparation-only and remains in `.cache/java/`.

`scripts/prepare_java_geometry.py` extracts conventional `railway=rail`, gauge 1067 mm (including unspecified gauge), excluding yard/spur and industrial/military/test uses. It preserves native OSM node connectivity and simplifies between native junctions. Station codes and names are matched from OSM station/stop features, with reference/name disambiguation and track anchors. This excludes Whoosh’s 1435 mm track; Whoosh uses its own existing Jakarta geometry.

Routing reuses the established connected graph and stable main-component anchors. Ordered source passing stations constrain the path, preventing shortcuts between distant passenger calls. Thirteen unmapped passing-only points (mostly untimed urban stops or closed features) are recorded; no passenger station is missing. Unsupported legs would remain gaps, with no straight connectors. The main intercity/airport/feeder reference maps **all 3,350 timed passenger legs**, and the regional layer maps **all 2,106 regional legs**. These are plausible inferred alignments, not verified historical running tracks/platforms or diversion records.

Geography: **© OpenStreetMap contributors, ODbL 1.0**. Timetables: **DJKA / PT Kereta Api Indonesia**, original government/operator source rights retained. No blanket CC/MIT licence is invented for the timetable PDF. Source URLs, archive URL and hashes are preserved in metadata. The existing Jakarta layers retain their own attribution and licences.

## Files and rebuild

Committed preparation/runtime references:

| File | Gzip bytes | SHA-256 |
| --- | ---: | --- |
| `intercity-timetable-2025.json.gz` | 114,743 | `c1f393e4e8c03323b20789092995f562531c636f26781364f9403df7073366f7` |
| `rail-osm-2026-10-18.json.gz` | 449,599 | `39970830646772bd2c4f131d2a94d2833f28e7c6671968ee1204c31e1d83a095` |
| `connections-timetable-2025.json.gz` | 7,911 | `635502480e8eb8ec0849572987356552ad5d32cd851c8187ba6b9fd36e22e213` |
| `2025-02-03.json.gz` | 449,405 | Main intercity/airport/feeder runtime from the pinned timetable/geometry references |
| `regional-timetable-2025.json.gz` | 25,814 | `71dd1ac48425eb6a9ab82d9bf7193cc062307b3a1797347b8b2b9152926521fb` |
| `regional-2025-02-03.json.gz` | 131,080 | Regional runtime from the normalized operator/government tables and existing railway geometry |

Only the compact selected-day HTTP payload is sent to the browser. Shared timing vectors/topologies remain compact; there is no per-trip stop-array expansion on the main thread. Original PDFs and raw OSM are never loaded by the running site. The runtime Java intercity/airport/feeder bundle is ~449 KB and the regional bundle ~131 KB; normalized source and full preparation geometry do not go to the browser. The HTTP descriptor includes the reused Jakarta file’s fingerprint so its changes invalidate the combined response correctly.

```bash
# PDF-only extraction uses the existing Python 3.11 preparation tools.
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_java_replay.py --extract-pdf
# Geometry extraction uses the existing pyosmium preparation tools.
PYTHONPATH=.cache/osm-tools ./.venv/bin/python scripts/prepare_java_geometry.py .cache/java/java-261018.osm.pbf
# Airport/feeder extraction uses the same already downloaded government PDF.
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_java_connections.py
# Routine offline replay rebuild uses only the pinned normalized references.
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_java_replay.py
# Regional extraction requires the three pinned operator PDFs in .cache/java/regional/.
PYTHONPATH=.cache/jakarta-pdf-tools python3.11 scripts/prepare_java_regional.py --extract-pdf
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python scripts/prepare_java_regional.py
```

`--extract-pdf` caches visual page text at `.cache/java/visual-pages.json`; remove that cache when deliberately auditing another PDF. Any source/edition update requires updating pins and the source week deliberately. Do not stretch this February snapshot across a whole year.

Validation covers source hashes, all 297 source sections and exclusions, midnight rollover, pass-throughs, terminal dwell boundaries, unique departure ownership, track paths, compact schedule structure, weekday/weekend Jakarta reuse, single file reads, HTTP invalidation and unchanged Jakarta counts. Browser checks cover Java selection, all four regional networks, route filters, original/combined train numbers, Dhoho loop playback, overnight services, optional Jakarta layers and Sunday maintenance.

## Subsequent additions

1. **Optional F services:** only enable when an authentic dated operating calendar confirms them. A timetable path alone does not prove a departure ran daily.
2. **Pangrango:** obtain the complete operator publication for the eight omitted sections; do not interpolate station-event times from the government’s `Berh Sb` entries.

Other local services outside these four groups (e.g. Kedung Sepur and Batara Kresna) can use the same government PDF in a later scoped addition. Freight, buses, Sumatra and other islands are outside this expansion. Passenger features remain optional and should use only the level genuinely supported by published data.
