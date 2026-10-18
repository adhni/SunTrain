# Switzerland rail

Swiss passenger trains use **1–7 June 2026**, matching France, Germany and the Netherlands. Reuse the existing replay, filters, details, Overview, theme and fullscreen. No passenger counts or live tracking are added.

## Timetable and scope

Use the official [2026 nationwide GTFS catalogue](https://data.opentransportdata.swiss/en/dataset/timetable-2026-gtfs2020), specifically [GTFS_FP2026_20260530.zip](https://data.opentransportdata.swiss/dataset/3d2c18f9-9ef1-463f-a249-5c67604efd74/resource/caf12531-948a-4683-91d8-fc63167e4da2/download/gtfs_fp2026_20260530.zip). The original 169,377,893-byte ZIP was actually downloaded without registration/payment. Its SHA-256 is `c50a50f8673303bc05ed1dbb602736484d5f107452221a2ad397f1a4a088f146`.

The publisher's catalogue records publication on **1 June 2026**, with feed version `20260530` and declared validity **14 December 2025–12 December 2026**. The snapshot/version date is not its public release date. Actual weekly calendars and exceptions select the replay services; we do not use a current feed to simulate June.

Include the archive's passenger rail products: IC/EC/ICE/RJX, TGV, IR, RE/R/RB/TER, S/SN, Nightjet, panorama trains, rack railways and published special passenger trains. Operators include **SBB, BLS, SOB, RhB, Matterhorn Gotthard, Zentralbahn, THURBO**, regional and mountain railways. Audited agency IDs/names are pinned in `data/reference/switzerland/rail-operators.json`; extended GTFS types are paired with the publisher's actual rail categories.

Exclude buses (including replacement buses), metros, trams, cableways, funiculars, car-shuttle trains and unvalidated placeholder/special-operator records. ANAT is a museum tram operator despite a rail-labelled route and is excluded. The generic INFO Glacier Express record is not added separately to the operating railways' Glacier Express portions. This is the validated published train coverage, not a claim to include every Swiss railway operator or every special excursion.

International journeys retain first through last **Swiss/border-coded** station calls (seven-digit UIC/DiDok IDs beginning `85`, with optional platform suffixes in this snapshot). Preserve intervening foreign calls and original times; do not join over them. Exclude foreign-only journeys or those with fewer than two eligible calls. This code rule is not an exact geographical frontier; border stations can lie outside Switzerland. Operator changes may remain separate source trip portions.

Keep commercial train numbers from `trip_short_name`, source trip IDs and retained terminal names. Each occurrence belongs to one 03:00–03:00 business window according to its first retained departure. Calls after midnight remain intact. The feed declares **Europe/Berlin** for every agency; preparation checks that it matches the **Europe/Zurich** clock over the selected dates and adjoining service days, and publishes Zurich as the replay timezone. This week uses CEST.

The full source includes frequency entries for other transport modes; none of the calendar-relevant rail trips uses them. Do not turn non-exact frequency templates into fictional scheduled departures in a future expansion.

## Geometry and size

This GTFS has no `shapes.txt`. Use connected rail alignments from the dated [Geofabrik Switzerland OSM extract](https://download.geofabrik.de/europe/switzerland-261017.osm.pbf), dated **17 October 2026**. PBF SHA-256: `7e35adb483f61ab05d9ec273b3d62aaed4cf6a55d84e17360a3f9066c8384ae9`. October geometry is a geographical reference for June timetables, not proof of historical diversions or exact running tracks.

Include rail, narrow-gauge, preserved and light-rail track geography needed for train networks; this does not enable tram/light-rail timetables. Exclude cable/funicular tracks, disused lines and industrial/yard/spur tracks. Preserve native OSM node identities and junctions while simplifying curves. Coincident coordinates on unrelated tracks do not create a connection. Train station sequences constrain routing; station anchors must be within 150 m. Missing connections and excessive detours remain empty paths rather than straight-line shortcuts.

SBB/BLS main lines, Alpine railways, narrow-gauge and rack-rail operators receive representative checks. Remaining gaps should be documented rather than patched with speculative connectors. The app does not add a routing service or download raw geometry at runtime.

The prepared week contains **103,584 departures across 45 operator names**: 15,076 / 15,068 / 15,110 / 15,071 / 15,424 / 14,387 / 13,448 from Monday through Sunday. **99.2% of scheduled legs** have mapped railway geometry. Remaining gaps include street-running Appenzeller sections around St. Gallen and some cross-border corridors around Jestetten/Rafz; keep those gaps until suitable connected track geography is validated.

The weekly reference is **4.59 MB gzip**, with **1.33 MB gzip** of preparation-only derived track geometry (about **5.93 MB** added storage). Monday's selected-day browser response is **3.00 MB gzip**. Local uncached response preparation measured about 2.5 seconds; hosted timings can differ. The full-year 169 MB timetable ZIP and 549 MB OSM extract are not browser downloads.

[SwissTNE Base](https://www.swisstopo.admin.ch/en/landscape-model-swisstne-base) was also inspected: its current GeoPackage download combines road/rail networks in a 1.06 GB ZIP (1.79 GB uncompressed). The existing OSM extraction and native-node graph approach is simpler here; no swisstopo geometry is included.

## Usage terms

The timetable uses the publisher's [Open Data terms](https://opentransportdata.swiss/en/terms-of-use/), which permit processing/publication and require source citation and identifying the processor. The replay credits **opentransportdata.swiss / SKI** and identifies the historical selection/matching as **SunTrain**. It is processed historical data, not a mirror of the latest raw timetable.

Derived OSM geometry is **ODbL 1.0**. Keep **© OpenStreetMap contributors** credit, the license link and the source/derivation metadata when redistributing. Existing map/replay attribution handles both sources. Do not relabel the timetable itself as ODbL.

## Rebuild and extend

```bash
# Preparation tools only; the application has no osmium dependency.
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_switzerland_geometry.py .cache/switzerland/switzerland-261017.osm.pbf
.venv/bin/python scripts/prepare_switzerland_replay.py
.venv/bin/python -m pytest tests/test_switzerland.py tests/test_france.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The replay builder downloads the pinned timetable if missing and verifies both input hashes. The geometry builder verifies the dated PBF hash. The prepared reference uses shared stop patterns and flat timing vectors, not expanded per-trip stops. Source ZIP/PBF files and graph-building inputs stay in preparation cache. Only the requested day is sent to the browser via the existing compressed response cache.

For a different historical week, obtain and validate a suitable dated file from the same catalogue or [official historical archive](https://archive.opentransportdata.swiss/), check actual calendars, mode/category mappings, timezone equivalence and frequency handling, then rebuild. Do not enable other transport modes or Austria implicitly when expanding Swiss dates.
