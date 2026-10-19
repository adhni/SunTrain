# Austria rail

Use **1–7 June 2026**, matching the Netherlands, Germany, France, Switzerland and Belgium. Reuses replay, filters, details, Overview, themes and fullscreen. National passenger trains and Vienna U-Bahn; passenger loads are unavailable.

## Timetable and coverage

The actual [official ÖBB 2026 GTFS ZIP](https://static.web.oebb.at/open-data/soll-fahrplan-gtfs/GTFS_Fahrplan_2026.zip) was downloaded. The [publisher catalogue](https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~) identifies an annual timetable, last changed **12 December 2025**, valid **14 December 2025–12 December 2026**. The download's HTTP Last-Modified also reports 12 December 2025. It is a published historical annual plan, **not a June snapshot of every later amendment** or actual running records. No current schedule is backdated. Calendar exceptions, including the adjoining service days, select the actual replay occurrences from this source.

The original ZIP is 173,582,700 bytes. Its SHA-256 is `a1ace21ca33ff5d6c740a1467252a44f7b9bece2692ca9d96e167f639d5ab633`. The source puts its GTFS tables under `GTFS_Fahrplan_2026/`; the existing rail builder now reads one enclosing directory without repacking or losing the original source hash. There is no `feed_info.txt`; actual calendars validate the week instead. The original ZIP also exactly matches Transitland’s archived annual version SHA-1 `c1bd2b28676fbd642892972ad3d8af14f887c989`; this confirms file identity, not a later amendment history.

Included source agencies:

- `01` — OEBB Personenverkehr AG Kundenservice
- `10` — Montafonerbahn AG
- `08` — City Air Terminal Betriebsgesellschaft m.b.H.

Include type-2 passenger rail: Railjet/Railjet Xpress, IC/EC/ICE, Nightjet/EuroNight, REX/R/CJX/IR, S-Bahn and other published passenger categories. Preserve commercial train identifiers from `trip_short_name`; never infer an operating company from a foreign train category. Exclude source type-3 replacement buses and the dedicated `11-220-A-j26-1` ATB car-shuttle route. This national component excludes metros, trams, buses, cableways and funiculars; Vienna U-Bahn is added separately below.

Austria is defined by source station IDs starting `at:`. International journeys retain first through last Austrian calls, including any foreign intermediate calls (for example the Salzburg–Innsbruck corridor through Germany), with original times and geometry. Foreign-only trips and portions with fewer than two Austrian calls are excluded. This is a source-country boundary, not an assertion about exact physical frontier locations. Source portions may remain separate trips.

Every occurrence belongs to one 03:00–03:00 business window according to the first retained departure. A dwell spanning 03:00 uses departure for day assignment while retaining its original arrival and dwell times. Keep journeys past midnight intact. All selected source agencies use **Europe/Vienna**; June uses CEST.

## Geometry and performance

The official timetable supplies detailed `shapes.txt` geometry and native stop distances. Reuse these exact trip shapes, anchored in stop order within the existing 150 m tolerance, with simplification between stop anchors. Invalid paths stay empty; do not substitute straight lines or another route's geometry. Supplied shapes describe geographical route alignments, not guaranteed platform tracks or historical diversions.

The 666 MB raw shapes table and annual ZIP stay in preparation cache, never in browser downloads. Only the selected week is committed, using shared stop patterns and timing vectors. The existing compressed selected-day endpoint and cache serve the browser.

[ÖBB Geo Netz](https://data.oebb.at/de/datensaetze~geo-netz~) was inspected and its December 2024 archive downloaded, but is **not used or redistributed**: supplied timetable shapes are sufficient and the older infrastructure snapshot does not prove 2026 coverage.

The national component contains **38,011 departures**: **5,831 / 5,833 / 5,949 / 4,714 / 5,959 / 5,009 / 4,716** from Monday through Sunday. Of these, 37,024 are from the ÖBB agency, 483 from Montafonerbahn and 504 from CAT. **All 465,499 scheduled legs have supplied matched paths**; no selected trips were omitted for invalid data. This measures usable source geometry, not proof of exact historical running tracks.

The national preparation-cache reference is **2,803,691 bytes gzip** (2.80 MB). With the combined reference, Monday's train-only browser response is **2,384,868 bytes gzip** (2.38 MB); local uncached preparation measured about 1.44 seconds, with hosted timing dependent on the server. No additional geometry database is committed.

Validation covers nationwide scope, rail-only selection, source pins, domestic clipping, shared schedules, unique overnight/start windows, representative Railjet/Nightjet/regional/S-Bahn paths, city/date/mode descriptors and loader behaviour. Browser checks passed for Monday/Sunday, category route filtering, details, city Overview, 2,000× playback, themes and fullscreen, with no page errors.

## Terms and attribution

The official timetable and its supplied route shapes are **CC BY 4.0**, as stated in the publisher catalogue. Retain the source/license links and credit **ÖBB-Personenverkehr AG / ÖBB Open Data**, identifying historical selection/simplification as SunTrain. Colours are SunTrain category/operator styling, not an assertion that every route has an official assigned colour. No OSM-derived geometry or new geometry licence is introduced.

## Additional train operators

**Deferred by request:** additional train operators remain notes only until a suitable national source is supplied. No registration or download credentials are configured locally. The [official API instructions](https://mobilitaetsverbuende.atlassian.net/wiki/spaces/DBP/pages/231145473/Public%2BAPI%2BDownload%2Bfor%2BDBP) require manual account registration, email confirmation and manual licence acceptance; these cannot be completed by a preparation script.

WESTbahn, Raaberbahn/GYSEV, Niederösterreich Bahnen and other operators are **not claimed as covered** by this three-agency source. The [national platform](https://data.mobilitaetsverbuende.at/en/data-sets) offers railway datasets for the annual timetable-change baseline and rolling updates, with registered access and licence acceptance. The annual baseline explicitly describes more operators; obtain and validate its actual 2026 ZIP before adding them. The rolling feed's past calendars do not establish that its amendments match June.

[Transitland](https://www.transit.land/feeds/f-oebb~at) currently points at a broader national feed, while its September 2026 archived ÖBB version lists the same three agencies and annual timetable. An archive's capture date does not override the original file's December 2025 publication date. Historical download APIs may require credentials; no gated dataset is included. The route.lw1.at secondary archive was investigated but its repository responds with a browser challenge; it was not used. Do not merge a newer national timetable into June without checking provenance and avoiding duplicate ÖBB trips.

## Vienna U-Bahn

Adds **U1, U2, U3, U4 and U6** to the same June week. Only agency `04` (`Wiener Linien GmbH & Co KG`) with route type `1` and those line names is selected. Tram, bus, replacement bus and Wiener Lokalbahnen records in the archives are excluded. U5 is not invented. Preserve the GTFS line colours, destinations, calendars and source trip IDs.

Actually downloaded public historical ZIPs from [MobilityDatabase’s Wiener Linien archive](https://mobilitydatabase.org/feeds/gtfs/mdb-648):

| Capture | Selected service dates | Original bytes | SHA-256 |
| --- | --- | ---: | --- |
| [26 May 2026](https://files.mobilitydatabase.org/mdb-648/mdb-648-202605260032/mdb-648-202605260032.zip) | 31 May–1 June, including carry service day | 67,496,798 | `915f8c10e08f827c49d724b832d2f644f8bc3325c743d061776f907e56b8e62a` |
| [2 June 2026](https://files.mobilitydatabase.org/mdb-648/mdb-648-202606020029/mdb-648-202606020029.zip) | 2–8 June, including carry service day | 68,529,469 | `9e38d4ea387445af3b91a2bdd25fd31e7e1eacf3c6990135e181348e3c115d70` |

No `feed_info.txt` is supplied. Actual calendars/exceptions select services in each snapshot; a current annual date range is not used as evidence for historical amendments. Capture dates identify archive retrieval, not an unverified publisher release date. The public archive interface needs its anonymous session initialized before loading older history pages. Transitland’s historical ZIP API returned HTTP 401 without credentials and was not used.

Shapes and native stop-distance anchors come from the same dated GTFS files. The existing rail preparation validates anchors within 150 m and preserves curves; no OSM or additional track graph is needed. Every occurrence is assigned by first departure within one 03:00–03:00 window in Europe/Vienna. Shared stop/timing patterns stay compact. Feed IDs and station indices are namespaced/remapped using the existing Belgium merge logic, now shared in `compact_transit.py`, so train and metro IDs cannot collide.

The [official Austrian open-data catalogue](https://www.data.gv.at/datasets/ab4a73b6-1c2d-42e1-b4d9-049e04889cf0?locale=de) records **CC BY 4.0**. Credit **Stadt Wien – Wiener Linien** for both schedules and shapes; archive retrieval is credited to MobilityDatabase, with selection/simplification identified as SunTrain. No account or paid download was needed for these ZIPs.

The metro component adds **18,457 departures**: **2,935 / 2,924 / 3,035 / 2,052 / 2,953 / 2,506 / 2,052** from Monday through Sunday. All **377,570** selected metro legs have supplied matched paths, with no invalid-trip omissions or geometry gaps. The combined week has **56,468 departures** and is **3,155,630 bytes gzip** (3.16 MB). Monday opens with **2,498,532 bytes gzip** (2.50 MB); metro alone is **93,737 bytes gzip** (94 KB). The large raw archive ZIPs remain in preparation cache.

Browser checks passed for all five source-coloured lines, independent mode/route filters with clock preservation, details, metro-only Overview, 2,000× playback, theme/fullscreen and Monday/Sunday, with no page errors.

Trains and U-Bahn open together; select either independently under the existing Transport filter. Route/operator/stop filters, playback and Overview reuse the existing UI. National train coverage remains unchanged; the skipped additional train operators stay documented above. The national-only builder now writes `.cache/austria/at-oebb-week.json.gz` to avoid replacing the combined website reference. The combined builder validates that base cache or rebuilds it when absent; rebuild it explicitly after changing national selection rules.

## Future modes and passengers

Use the national platform's dated regional feeds for Vienna trams/buses, Graz/Linz/Innsbruck trams and Salzburg buses/trolleybuses. Validate actual access, calendars, operators, mode codes, shapes, attribution and size first. The [Wiener Linien Open Data page](https://tramwm.wienerlinien.at/web/guest/open-data) is another starting point for Vienna; its [GTFS download](https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip) is current, so validate historical versions before enabling further modes. Enable these separately after train coverage; do not assume railway shapes suit roads or tram tracks.

[Statistik Austria rail passenger statistics](https://www.statistik.at/en/statistics/tourism-and-transport/passenger-transport/rail-passenger-transport) report annual aggregate passenger transport; these are not individual train loads. No validated train-level historical loads are included. Leave passenger sizing and heatmaps unavailable unless a suitable dataset is obtained.

## Rebuild

```bash
.venv/bin/python scripts/prepare_austria_replay.py  # national preparation cache only
.venv/bin/python scripts/prepare_austria_ubahn.py  # combined website reference
.venv/bin/python -m pytest tests/test_austria.py tests/test_austria_ubahn.py tests/test_belgium_urban.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The builder downloads the pinned original annual ZIP if missing and rejects a different hash. For a later snapshot or additional operator, inspect the file before updating the pin, scope and notes. Keep full-year raw tables out of the committed replay and browser payload.
