# Austria rail

Use **1–7 June 2026**, matching the Netherlands, Germany, France, Switzerland and Belgium. Reuses replay, filters, details, Overview, themes and fullscreen. Trains only; passenger loads are unavailable.

## Timetable and coverage

The actual [official ÖBB 2026 GTFS ZIP](https://static.web.oebb.at/open-data/soll-fahrplan-gtfs/GTFS_Fahrplan_2026.zip) was downloaded. The [publisher catalogue](https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~) identifies an annual timetable, last changed **12 December 2025**, valid **14 December 2025–12 December 2026**. The download's HTTP Last-Modified also reports 12 December 2025. It is a published historical annual plan, **not a June snapshot of every later amendment** or actual running records. No current schedule is backdated. Calendar exceptions, including the adjoining service days, select the actual replay occurrences from this source.

The original ZIP is 173,582,700 bytes. Its SHA-256 is `a1ace21ca33ff5d6c740a1467252a44f7b9bece2692ca9d96e167f639d5ab633`. The source puts its GTFS tables under `GTFS_Fahrplan_2026/`; the existing rail builder now reads one enclosing directory without repacking or losing the original source hash. There is no `feed_info.txt`; actual calendars validate the week instead. The original ZIP also exactly matches Transitland’s archived annual version SHA-1 `c1bd2b28676fbd642892972ad3d8af14f887c989`; this confirms file identity, not a later amendment history.

Included source agencies:

- `01` — OEBB Personenverkehr AG Kundenservice
- `10` — Montafonerbahn AG
- `08` — City Air Terminal Betriebsgesellschaft m.b.H.

Include type-2 passenger rail: Railjet/Railjet Xpress, IC/EC/ICE, Nightjet/EuroNight, REX/R/CJX/IR, S-Bahn and other published passenger categories. Preserve commercial train identifiers from `trip_short_name`; never infer an operating company from a foreign train category. Exclude source type-3 replacement buses and the dedicated `11-220-A-j26-1` ATB car-shuttle route. Metros, trams, buses, cableways and funiculars are not enabled.

Austria is defined by source station IDs starting `at:`. International journeys retain first through last Austrian calls, including any foreign intermediate calls (for example the Salzburg–Innsbruck corridor through Germany), with original times and geometry. Foreign-only trips and portions with fewer than two Austrian calls are excluded. This is a source-country boundary, not an assertion about exact physical frontier locations. Source portions may remain separate trips.

Every occurrence belongs to one 03:00–03:00 business window according to the first retained departure. A dwell spanning 03:00 uses departure for day assignment while retaining its original arrival and dwell times. Keep journeys past midnight intact. All selected source agencies use **Europe/Vienna**; June uses CEST.

## Geometry and performance

The official timetable supplies detailed `shapes.txt` geometry and native stop distances. Reuse these exact trip shapes, anchored in stop order within the existing 150 m tolerance, with simplification between stop anchors. Invalid paths stay empty; do not substitute straight lines or another route's geometry. Supplied shapes describe geographical route alignments, not guaranteed platform tracks or historical diversions.

The 666 MB raw shapes table and annual ZIP stay in preparation cache, never in browser downloads. Only the selected week is committed, using shared stop patterns and timing vectors. The existing compressed selected-day endpoint and cache serve the browser.

[ÖBB Geo Netz](https://data.oebb.at/de/datensaetze~geo-netz~) was inspected and its December 2024 archive downloaded, but is **not used or redistributed**: supplied timetable shapes are sufficient and the older infrastructure snapshot does not prove 2026 coverage.

The prepared week contains **38,011 departures**: **5,831 / 5,833 / 5,949 / 4,714 / 5,959 / 5,009 / 4,716** from Monday through Sunday. Of these, 37,024 are from the ÖBB agency, 483 from Montafonerbahn and 504 from CAT. **All 465,499 scheduled legs have supplied matched paths**; no selected trips were omitted for invalid data. This measures usable source geometry, not proof of exact historical running tracks.

The committed reference is **2,803,691 bytes gzip** (2.80 MB). Monday's browser response is **2,373,259 bytes gzip** (2.37 MB); local uncached preparation measured about 1.15 seconds, with hosted timing dependent on the server. No additional geometry database is committed.

Validation covers nationwide scope, rail-only selection, source pins, domestic clipping, shared schedules, unique overnight/start windows, representative Railjet/Nightjet/regional/S-Bahn paths, city/date/mode descriptors and loader behaviour. Browser checks passed for Monday/Sunday, category route filtering, details, city Overview, 2,000× playback, themes and fullscreen, with no page errors.

## Terms and attribution

The official timetable and its supplied route shapes are **CC BY 4.0**, as stated in the publisher catalogue. Retain the source/license links and credit **ÖBB-Personenverkehr AG / ÖBB Open Data**, identifying historical selection/simplification as SunTrain. Colours are SunTrain category/operator styling, not an assertion that every route has an official assigned colour. No OSM-derived geometry or new geometry licence is introduced.

## Additional train operators

WESTbahn, Raaberbahn/GYSEV, Niederösterreich Bahnen and other operators are **not claimed as covered** by this three-agency source. The [national platform](https://data.mobilitaetsverbuende.at/en/data-sets) offers railway datasets for the annual timetable-change baseline and rolling updates, with registered access and licence acceptance. The annual baseline explicitly describes more operators; obtain and validate its actual 2026 ZIP before adding them. The rolling feed's past calendars do not establish that its amendments match June.

[Transitland](https://www.transit.land/feeds/f-oebb~at) currently points at a broader national feed, while its September 2026 archived ÖBB version lists the same three agencies and annual timetable. An archive's capture date does not override the original file's December 2025 publication date. Historical download APIs may require credentials; no gated dataset is included. The route.lw1.at secondary archive was investigated but its repository responds with a browser challenge; it was not used. Do not merge a newer national timetable into June without checking provenance and avoiding duplicate ÖBB trips.

## Future modes and passengers

Use the national platform's dated regional feeds for Vienna U-Bahn/trams/buses, Graz/Linz/Innsbruck trams and Salzburg buses/trolleybuses. Validate actual access, calendars, operators, mode codes, shapes, attribution and size first. The [Wiener Linien Open Data page](https://tramwm.wienerlinien.at/web/guest/open-data) is another starting point for Vienna; its [GTFS download](https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip) is current, so find a validated historical version for June. Enable these separately after train coverage; do not assume railway shapes suit roads or tram tracks.

[Statistik Austria rail passenger statistics](https://www.statistik.at/en/statistics/tourism-and-transport/passenger-transport/rail-passenger-transport) report annual aggregate passenger transport; these are not individual train loads. No validated train-level historical loads are included. Leave passenger sizing and heatmaps unavailable unless a suitable dataset is obtained.

## Rebuild

```bash
.venv/bin/python scripts/prepare_austria_replay.py
.venv/bin/python -m pytest tests/test_austria.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The builder downloads the pinned original annual ZIP if missing and rejects a different hash. For a later snapshot or additional operator, inspect the file before updating the pin, scope and notes. Keep full-year raw tables out of the committed replay and browser payload.
