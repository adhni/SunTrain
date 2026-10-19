# Spain rail

Spain uses **24–30 June 2024**, with **Europe/Madrid** local time. Reuses replay, filters, service details, country Overview, themes and fullscreen. **Trains only**; no passenger loads or live tracking.

## Historical period and actual sources

June 2026 was investigated first. The old national Renfe MobilityDatabase entry stops in December 2025; its replacement points at a smaller international AVE feed, not a validated nationwide replacement. Transitland records newer national versions, but historical ZIP access requires credentials. The current Renfe download is a rolling timetable and is not used to simulate June. Matching, actually downloaded June 2024 national and commuter archives provide the practical historical fallback allowed by the brief.

| Component | Actual historical ZIP | Original bytes | SHA-256 |
| --- | --- | ---: | --- |
| Renfe national | [24 June 2024](https://files.mobilitydatabase.org/mdb-790/mdb-790-202406240002/mdb-790-202406240002.zip) | 676,369 | `885f50c3c0dbff11ed54758c49d1e1c8d8ff8947b1f7eac8f68667fa5d90c6d9` |
| Cercanías / Rodalies | [24 June 2024](https://files.mobilitydatabase.org/mdb-1065/mdb-1065-202406240019/mdb-1065-202406240019.zip) | 13,498,575 | `e630225b5acfe8c14b58c6197e00b439716ec929ea8538f1fcd22a4d64f342d4` |
| FGC | [7 June 2024](https://files.mobilitydatabase.org/mdb-1856/mdb-1856-202406071504/mdb-1856-202406071504.zip) | 4,134,294 | `b27cae62bf76e28b0cecd9a8b6dc92e901b61f2361506a18ebcc07caa52b54d7` |

Renfe calendars and exceptions cover the week and adjoining service days; neither Renfe file has `feed_info.txt`. The commuter file uses dated calendars without an exceptions table. FGC declares validity 1 January 2023–31 December 2024, with actual version **4 June 2024**; calendar exceptions select the June services. Archive capture dates are not claimed as unverified publisher release dates. These are published schedules, not a reconstruction of every later amendment or disruption.

## Included and excluded

National Renfe includes the actual archived products **AVE, AVE INT, Avlo, Alvia, Euromed, Intercity, Media Distancia, Avant, Regional/Regional Express, Proximidad, Rodalies, Torre Oro and Tren Celta**. Retain commercial train numbers. The source also labels four **Bus** routes as rail type 2; these are explicitly excluded by product selection.

Cercanías/Rodalies includes the published regional networks represented in the archive, including Madrid, Catalonia, Valencia, Seville, Málaga, Bilbao, Asturias, Cantabria and Murcia/Alicante. Operator and route identifiers stay separate from national Renfe. Original station names are retained, including source variants such as “A Corunya”. No exact cross-feed duplicates with the same station coordinates, full call times and origin time were found across the two Renfe sources.

FGC adds its validated type-2 regional/suburban services: **S1/S2/S3/S4/S8/S9, R5/R6/R50/R53/R60/R63, RL1/RL2**, where calendars are active. FGC metro-classified L6/L7/L8/L12 and route-type-7 mountain/funicular services are excluded in this train-first phase. The source legally omits agency IDs in its single-agency GTFS; the shared rail builder supports that standard case.

International trips retain first through last Spanish calls and any intervening foreign calls, with original times. Foreign stop IDs are audited explicitly in these snapshots: prefixes alone are unsafe, since **94002 Daimiel** and **94004 Almagro** are Spanish, while other 94xxx records are Portuguese. French border stops Cerbère and La Tour de Carol are excluded as outer endpoints. Foreign-only portions or fewer than two Spanish calls are excluded. No cross-border paths are invented. Journeys belong to one 03:00–03:00 window by first retained departure, preserving overnight calls and origin dwell times.

No Canary Islands transport is included. Mainland rail uses Europe/Madrid; do not apply it to future Canary Islands modes, which need Atlantic/Canary.

## Railway geometry

Both Renfe archives lack `shapes.txt`. Downloaded all **60,018** official [IGN railway links](https://api-features.idee.es/collections/railwaylink?f=json), checking page counts and unique feature IDs. The [official IGN services catalogue](https://www.ign.es/web/ign/portal/ide-area-nodo-ide-ign) identifies this national transport dataset. Original export SHA-256: `2f69b61322cef54ce16e64cbfc404d1537bdcba119c9846b3872f0e0c1940b3a`.

The derived geometry is **2,741,801 bytes gzip**, SHA-256 `ae1acc73a5fbe3b49a498b49bb65d62e0e08d3b675b0c9f770c7329dcead86d2`. Reuses France/Belgium's original coincident endpoint/vertex compiler, with seven-decimal coordinates and simplification between preserved junctions. Interior crossings are not joined and no distance-based connectors are added. Heights are not used to establish operational connectivity. Reuses the indexed station-local 150 m rail matcher, extended to Spanish latitudes, and rejects disconnected/excessively long detours. FGC uses its own dated shapes and anchors instead.

This is an **October 2026 geographic reference for 2024 schedules**, not a historical infrastructure snapshot. Individual record creation dates are not opening dates. Inferred paths follow plausible geography but do not prove exact high-speed/conventional running tracks, platforms or historical diversions. The Adif catalogue/service was investigated; the older catalogue identifies an April 2018 version and the direct service did not yield a usable export here, so it is not substituted for current coverage.

Usable paths cover **97.79% of all 536,607 scheduled legs**: **97.49% national Renfe**, **97.28% Cercanías/Rodalies**, and **100% FGC**. Remaining gaps include central Málaga/Bilbao sections and parts of the coastal Rodalies R1 corridor. Gaps remain empty and moving positions are hidden between those calls; never add straight-line shortcuts to improve the percentage. Representative Madrid–Barcelona AVE, regional, commuter and FGC movements were checked in the browser.

## Size and validation

The week contains **39,422 departures**: **5,538 / 6,208 / 6,210 / 6,217 / 6,253 / 4,509 / 4,487** from Monday through Sunday. National Renfe contributes 9,139; Cercanías/Rodalies 25,877; FGC 4,406.

The compact weekly reference is **2,913,155 bytes gzip** (2.91 MB), with **2,741,801 bytes** preparation-only geometry: about **5.65 MB** committed total. Monday's selected-day browser download is **2,520,663 bytes gzip** (2.52 MB); uncached local response preparation measured about one second, with hosted timing dependent on the server. Raw ZIPs, full-year source tables and IGN export pages stay in preparation cache, not browser downloads.

Validation covers pinned provenance, train-only scope, mislabelled bus exclusion, border clipping, nationwide products/stations, compact schedules, overnight/start-window uniqueness, geometry gaps and existing loader/date/mode behaviour. Browser checks passed for national/Cercanías/FGC route filters, commercial train details, Spain Overview, 2,000× playback, themes, fullscreen and Monday/Sunday, with no page errors.

## Licensing and attribution

[Renfe national](https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia) and [commuter](https://data.renfe.com/dataset/horarios-cercanias) catalogues declare **CC BY 4.0**. Retain **“Origen de los datos: Renfe Operadora”**, source links and processing credit. The [FGC official dataset metadata](https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets/gtfs_zip) also declares CC BY 4.0; credit Ferrocarrils de la Generalitat de Catalunya for schedules and shapes.

IGN's linked [licence](https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf) permits CC BY 4.0 use and requires derived-work attribution. The replay and geometry metadata credit **“Obra derivada de IGR Redes de Transporte, consulta 2026-10-19, CC BY 4.0, ign.es / Sistema Cartográfico Nacional”** and identify matching/simplification as SunTrain. No OSM geometry or additional licence is introduced.

## Rebuild and future additions

```bash
# The committed derived geometry is sufficient to rebuild the timetable.
.venv/bin/python scripts/prepare_spain_replay.py
# Only if the original validated IGN export remains in cache:
.venv/bin/python scripts/prepare_spain_geometry.py .cache/spain/ign-railwaylinks.json
.venv/bin/python -m pytest tests/test_spain.py tests/test_france.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The national IGN export was retrieved from its public API in 1,000-feature pages (`limit=1000&offset=0`, then offsets 1000…60000) and combined in page order into a compact JSON FeatureCollection with `features` and `numberMatched`. The geometry compiler and replay builder verify input hashes. The API is mutable; if the original export changes, inspect and deliberately update the source/geometry pins rather than treating it as the same snapshot. Shared patterns and feed namespaces reuse existing SunTrain functionality.

**Next train sources:** investigate [Spain's NAP](https://nap.transportes.gob.es/) for same-week Euskotren, FEVE, Iryo and OUIGO España files. No suitable matching archive was validated for those operators, so they are not represented. The old public FEVE archive is particularly misleading: a June 2024 capture contains **2012–2014 calendars**, not 2024 service. A later capture alone does not make it usable. Additional FGC rack rail and omitted networks need explicit source/category audits. Do not claim that the current Renfe replay covers every Spanish operator.

**Future urban modes:** Madrid Metro/Metro Ligero via CRTM/NAP; Barcelona TMB Metro/trams via their operator/ATM catalogues; Metrovalencia/Alicante TRAM via FGV/NAP; Bilbao Metro via its operator and Basque data portals; Seville, Málaga and Granada metro via their official/regional catalogues and NAP. These are source leads, not validated June downloads. Audit dates, access, modes, shapes and size before enabling them. Buses remain a later phase.

Passenger features remain unavailable. The inspected [Renfe hourly station-volume dataset](https://data.renfe.com/dataset/volumen-de-viajeros-por-franja-horaria-estaciones-de-cercanias/resource/566dcfa2-4c02-48bf-99c9-a7606a097073) describes 2018 station totals, which do not match this replay week. Other station/aggregate datasets may support future analysis after date/granularity checks; they do not establish individual train loads. Keep passenger data optional.
