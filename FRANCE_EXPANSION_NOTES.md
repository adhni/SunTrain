# France rail expansion

France uses **1–7 June 2026**, the same week as the Netherlands and Germany. These are real archived timetables, not current schedules assigned to earlier dates. Switzerland and Austria are separate future tasks.

## Included

National passenger trains represented in the SNCF archive: **TGV INOUI, OUIGO, Intercités, Intercités de nuit, TER, ICE, TGV Lyria**, other source-labelled `Train` services and the verified Tours–Saint-Pierre-des-Corps rail shuttle. National trains open first. **RER A–E and Transilien H/J/K/L/N/P/R/U/V** are optional under Transport.

The existing replay, route/operator/stop filters, details, local clock, Overview, themes and fullscreen are reused. Passenger controls stay unavailable. No actual train loads or live positions are inferred.

This is coverage of the selected publishers, not every French operator. Eurostar, Trenitalia, Renfe, Corsica and other independent/regional publishers have not been added separately; do not assume their complete services are included. RATP metros/trams, buses, ferries and cable cars are excluded.

## Validated historical archives

Both original ZIPs were publicly downloadable without an account or paid access from the French national transport portal's history store. The source datasets declare **ODbL 1.0**. Keep source credit and the license link with redistributed data and derived databases.

| Feed | Archive | SHA-256 |
| --- | --- | --- |
| [SNCF national schedules](https://transport.data.gouv.fr/datasets/horaires-sncf) | [31 May 2026, 00:16 UTC](https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services.clever-cloud.com/83582/83582.20260531.001627.736700.zip), 5,061,015 bytes | `678ff24f33098a357abdbd539974a693d3d920e9184db4f5c9f101a81b36b786` |
| [Transilien / Île-de-France Mobilités](https://transport.data.gouv.fr/datasets/horaires-des-lignes-transilien-1) | [31 May 2026, 18:16 UTC](https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services.clever-cloud.com/67595/67595.20260531.181639.479952.zip), 11,434,136 bytes | `c356e92b5e4d3a8f18c7be107779ee9eb7d9d35498b1d264e9e863b02c125cf2` |

National `feed_info` declares 30 May–31 October 2026, version `2026-05-30`; actual calendar exceptions determine active services. Transilien has no `feed_info`; its calendars cover 28 May–29 June 2026. Neither archive supplies `shapes.txt` or `frequencies.txt`.

The portal's complete history CSVs are at `https://transport.data.gouv.fr/datasets/1290/resources_history_csv` (national) and `https://transport.data.gouv.fr/datasets/240/resources_history_csv` (Transilien). Validate the actual ZIP, hash and calendars when extending dates; history metadata alone is insufficient.

## Scope and schedule handling

- Require audited agency ID/name pairs and rail route type. The national feed incorrectly labels some coaches as rail: additionally whitelist the product embedded in its OCE stop IDs. `Car TER` and `Car à réservation` remain excluded even on rail routes. Only the exact audited A01 Tours shuttle is accepted from generic `Navette` entries.
- For international national-feed journeys, retain the first through last French/border-coded OCE UIC call (eight-digit code beginning `87`), retaining intervening foreign calls and original times. These publisher codes can include border stations beyond the geographic frontier; they are not a precise country boundary. Journeys with fewer than two eligible calls and foreign-only journeys are excluded. There are no invented border crossing times or straight connections over removed calls.
- Exclude agency `IDFM:93` TER from Transilien to avoid repeating national TER services. Exclude replacement bus variants by route type.
- Commercial national train numbers come from `trip_headsign`; the retained terminal stop supplies the destination. Original trip IDs remain in stable vehicle IDs and `source_trip_id`.
- Assign each occurrence by its retained first departure in a single **03:00–03:00 Europe/Paris** window. Keep calls beyond 24:00 and overnight night trains. Calendars also include the adjoining service dates needed for early-morning starts. This week is on CEST; shared preparation uses GTFS noon-minus-12-hours time arithmetic.
- Shared stop topology and flat timing vectors remain compact; trips retain a shared pattern and departure offset instead of expanded stop arrays.

| Business date | National | RER / Transilien | Combined |
| --- | ---: | ---: | ---: |
| 1 June | 8,946 | 4,849 | 13,795 |
| 2 June | 8,906 | 4,868 | 13,774 |
| 3 June | 8,906 | 4,868 | 13,774 |
| 4 June | 8,929 | 4,865 | 13,794 |
| 5 June | 9,118 | 4,857 | 13,975 |
| 6 June | 5,095 | 4,115 | 9,210 |
| 7 June | 4,617 | 3,913 | 8,530 |

## Railway geometry

Use the official [SNCF Réseau RFN track alignments](https://www.data.gouv.fr/datasets/fichier-de-formes-des-voies-du-reseau-ferre-national), extracted **12 August 2026**, and [nominal line speeds](https://ressources.data.sncf.com/explore/dataset/vitesse-maximale-nominale-sur-ligne/), accessed 19 October 2026 in Melbourne. Both are ODbL 1.0. This later geometry is a geographical reference, not proof of June's exact running tracks or diversions. No OSM railway database or OpenRailwayMap tiles were substituted.

The compiler keeps VPL/VPA tracks, excludes service tracks, and derives connections only where an original endpoint coincides with an original vertex (rounded to seven decimals). Two interior crossings do not create a junction. Repeated GAIA IDs are separated by feature/fragment identifiers. This is **inferred topology**, not native operational junction data. Curves are simplified between preserved junctions.

Station anchors use local latitude, a 150 m maximum distance, and indexed segment projections. Routing reuses the existing railway graph. TGV/OUIGO/ICE/Lyria prefer higher nominal-speed corridors; other trains prefer shorter railway paths constrained by every retained call. Whole-feature nominal speed preferences are approximate, not actual train speeds. A negative chainage such as `000-168` must parse correctly so the main LGV does not fall back to a slow default.

Reject disconnected routes and excessive detours. Missing paths remain empty geometry; vehicles do not draw distant straight-line shortcuts. About **99.9% of national scheduled legs** have matched geometry. Check representative Paris–Lyon, Bordeaux, Rennes, Lille, Strasbourg and Marseille corridors after changing routing inputs.

**Suburban geometry is partial:** the RFN source does not cover all RATP-owned RER infrastructure, and other gaps remain on RER E. Initial matched scheduled-leg coverage is approximately **74.2%** overall: A 18.7%, B 41.8%, E 83.7%; C/D and all included Transilien lines match fully. Timetables include these calls, but movement is hidden on unmapped sections. Complete RER geometry should use a separately validated, licensed RATP/IDFM alignment source; do not stretch RFN tracks or invent connectors to fill it.

Minor national gaps include some border sections, Dijon–Porte-Neuve, Limoges, and Morbier–Morez. Preserve gaps until an actual connected railway alignment is validated.

## Rebuilding and future work

```bash
.venv/bin/python scripts/prepare_france_geometry.py --cache .cache/france
.venv/bin/python scripts/prepare_france_replay.py --cache .cache/france
.venv/bin/python -m pytest tests/test_france.py tests/test_rail_preparation.py tests/test_replay_http.py -q
```

The geometry compiler expects `sncf-tracks.geojson` and `sncf-speeds.json` from the exact export URLs recorded in `scripts/prepare_france_geometry.py`. Their SHA-256 hashes are embedded in the derived geometry metadata. The replay builder verifies the committed geometry hash and timetable ZIP hashes; source updates must be audited deliberately. It downloads missing pinned timetables into preparation cache. Neither source ZIP nor raw track export is shipped to browsers.

The compact weekly replay is **10.02 MB gzip** and the derived track reference is **2.59 MB gzip** (12.61 MB added storage). The week contains **54,517 national** and **32,335 suburban** departures. Visitors receive only their selected day and modes through the existing compressed HTTP cache: Monday is **5.73 MB gzip** for national trains, **0.91 MB** for suburban services, or **6.52 MB** combined. Local uncached response preparation measured approximately 3–5 seconds; this is not a hosted Render timing guarantee. The track compiler reference and raw inputs are preparation-only. Measure compressed responses when adding publishers or dates; do not expand every service's stops or preload other countries.

Potential follow-ups: complete RER geometry; validate independent French operators separately; optional station-level passenger data if accessible and licensed. These do not imply individual train loads. Do not add urban networks or neighbouring countries implicitly while extending France's dates.
