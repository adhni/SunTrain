# Italy expansion notes

## Included

**5–11 October 2026**, using authentic historical snapshots that cover the week and both carry days. June 2026 was not forced: the reusable national conversion's Git history starts in August, and no matching downloadable June national version was validated.

- **Trenitalia:** Frecciarossa, Frecciargento, Frecciabianca, Intercity, Intercity Notte, Eurocity/EuroNight and regional/suburban services represented by the active calendars, including REG, RV, SFM and MET. MET is Trenitalia heavy-rail service, not a general Italian metro expansion.
- **Trenord:** the archive's rail routes, including regional/suburban and Malpensa Express services where represented. Its FNM-network services are included under Trenord, not imported a second time as another operator.
- **Italo:** direct high-speed train journeys. Connecting itineraries and ItaloBus are excluded.

**61,322 scheduled departures**: Trenitalia **44,074**, Trenord **16,302**, Italo **946**. Daily totals: **9,161 / 10,251 / 9,175 / 9,174 / 9,355 / 8,159 / 6,047**. Source calendar differences are preserved rather than copying a generic weekday. Coverage includes northern, central and southern Italy, **Sicily and Sardinia**. Other independent regional operators are not claimed as included.

Reuses existing playback, operator/route filters, details, themes/fullscreen and Italy Overview. Europe/Rome (CEST in this week); original after-midnight calls retained. Each occurrence belongs once by first departure to a 03:00–03:00 replay day. Passenger sizing/heatmaps remain disabled.

## Downloaded historical timetables

| Source | Immutable download | SHA-256 |
| --- | --- | --- |
| Trenitalia NeTEx → GTFS, Clément Desouche | [5 October commit](https://raw.githubusercontent.com/deryclem/trenitalia-gtfs/5cb930e7d9c135ea857e13608ad1ba1ec658e344/gtfs-trenitalia.zip) | `42b1a0bfb5b13c303382bb756d45457ad6c96418fc22324122930e86bc528b18` |
| Trenord / Regione Lombardia | [MobilityDatabase, 4 August](https://files.mobilitydatabase.org/mdb-855/mdb-855-202608040032/mdb-855-202608040032.zip) | `b4296f145b42ccb35c26085470ff4b3fd5dffe533251c0aab312312a73820ad6` |
| Italo NeTEx → GTFS, Clément Desouche | [5 October commit](https://raw.githubusercontent.com/deryclem/italo-gtfs/bb789e58e6b29be1896388b97b0c4dd642193706/gtfs-italo.zip) | `dbbb6e9fa453fa016cafaaafe4f61393c2de53f3c119110fb77539d885e2298d` |

All ZIPs were actually downloaded and inspected. Trenitalia's `feed_info` declares **26 September–12 December 2026**, original NeTEx publication **25 September**. The Git capture date is not misrepresented as the original publication. Italo declares **3 October 2026–2 February 2027**, publication **4 October**. Trenord uses actual `calendar_dates` with explicit active-service checks because its `feed_info` omits validity dates.

The two converted feeds are community conversions of official [Trenitalia NAP NeTEx](https://www.cciss.it/nap/mmtis/public/en/catalog/Dataset/1077621) and [Italo NAP NeTEx](https://www.cciss.it/nap/mmtis/public/en/catalog/Dataset/1813935), not GTFS files published directly by the train operators. Repositories: [Trenitalia](https://github.com/deryclem/trenitalia-gtfs), [Italo](https://github.com/deryclem/italo-gtfs). Existing conversions are reused; no NeTEx conversion infrastructure was added.

### Scope and duplicate handling

Rail selection checks the exact agency, route type and source product/identifier. Trenitalia **BUS** is excluded, and **FrecciaLink/FL is excluded even though the source labels it route type 2**. Trenord's **TN_Bus, R23 and RE_4** are type 3 in this archive and are excluded; do not silently reinterpret them as trains based on names alone. Italo requires an actual `RAIL-` route of type 2; connecting buses are excluded.

The Italo conversion also exposes rail legs of connecting passenger itineraries with `_rail`, `_rail1`, `_rail2` suffixes. These repeat direct trains and can retain the first train's commercial number on a different connecting train. **240 active candidate itinerary-leg records are excluded before geometry/occurrence preparation**, retaining 162 direct candidate journeys. Do not re-enable them as individual vehicles.

A conservative occurrence deduplicator checks normalized commercial number, origin departure, destination arrival and corresponding endpoint station names/coordinates. Prefers the national source over a matching Trenord record. Removes **269 Trenitalia and 4 Trenord occurrences**, including overlapping source variants, without deduplicating unrelated journeys merely because a number repeats. No synthesized merged timetables.

Trenitalia trips retain the span between first/last Italian `83` UIC calls. Trenord's audited Swiss S05-group and other Ticino station IDs are clipped from foreign tails; Italian S01-group stations remain. Foreign calls between Italian portions remain in order with original times, so no shortcut is introduced. Italo's selected direct rail journeys are domestic. Single-call/foreign-only sections are excluded. Numbers, original trip IDs and source route IDs remain traceable. **Zero malformed timetable omissions.**

## Railway geometry

The national converted Trenitalia shapes contain some large straight jumps and implausible alignments; examples inspected had tens of kilometres between vertices. They are not used for moving trains. All three selections use the same connected railway graph.

Source: **OpenStreetMap contributors / Geofabrik Italy**, [dated 18 October extract](https://download.geofabrik.de/europe/italy-261018.osm.pbf), retrieved 19 October 2026. SHA-256: `5e872974c98aeec82204df3a244369bb4cdd2a4b0ac0d580eed656b58e83467c`.

62,903 selected passenger railway ways become **75,186** simplified graph ways; no missing source nodes. Rail/narrow-gauge/preserved tracks are retained; metro, tram, road, industrial/military/test tracks and yards/spurs are excluded. Native OSM node IDs define connections, never coordinate snapping or new intersections. Curves simplify between preserved junctions. FR/FA/Italo use speed-weighted corridor routing to favour high-speed tracks; other services use distance routing constrained by intermediate calls. Station anchors stay within 150 m and implausible detours are rejected.

These are inferred geographic alignments, not exact running-track/platform assignments or a reconstruction of every October diversion. October geography does not create scheduled services absent from the historical calendars. RFI's [ePIR](https://epir.rfi.it/) is a useful official infrastructure reference, but no redistributable nationwide vector export was validated for this implementation.

| Operator | Usable scheduled legs | Coverage |
| --- | --- | --- |
| Trenitalia | 458,584 / 469,243 | 97.73% |
| Trenord | 188,462 / 189,884 | 99.25% |
| Italo | 6,335 / 6,635 | 95.48% |
| Combined | 653,381 / 665,762 | **98.14%** |

Remaining gaps include station-coordinate/connection mismatches around Torino Porta Susa/Porta Nuova, some Sardinian and Naples-area source stops, and certain cross-border/local branches. They remain empty with vehicles hidden during the interval. Sea/ferry crossings are not bridged by invented rails. The 150 m limit is not relaxed globally to hide source defects.

## Licences and storage

The converted Trenitalia and Italo GTFS datasets explicitly declare **CC BY 4.0**, © 2026 **Clément Desouche (@deryclem)**; attribution also retains **Trenitalia / Italo / CCISS MMTIS** as original data providers. This describes the conversions' declared terms rather than claiming the original NeTEx is independently published under the same licence. [Trenord's official regional catalogue](https://www.dati.lombardia.it/Mobilit-e-trasporti/Orario-Ferroviario-Regionale-Gtfs/3z4k-mxz9) declares **CC BY 4.0** and credits Trenord. All providers, snapshot dates and SunTrain transformations are credited in the replay.

OSM-derived railway geometry is distributed under **ODbL 1.0**, with OpenStreetMap/Geofabrik attribution, its compiled graph and preparation code supplied. Timetable terms remain separate. No individual passenger counts are redistributed or inferred.

**5.58 MB gzip** for the compact shared-pattern week; **2.93 MB** preparation-only geometry. Monday's selected-day HTTP download is approximately **3.90 MB gzip**. The raw 2.24 GB map extract stays under ignored `.cache/italy/`; it is **not deployed, loaded by the app, or sent to browsers**. Existing per-day compressed downloads/cache are reused, with no eager expansion of every schedule.

## Reproduce

```sh
# Download the pinned dated OSM PBF to .cache/italy/italy.osm.pbf.
# Pyosmium is preparation-only, already used for other countries.
PYTHONPATH=.cache/osm-tools .venv/bin/python scripts/prepare_italy_geometry.py .cache/italy/italy.osm.pbf
.venv/bin/python scripts/prepare_italy_replay.py
.venv/bin/python -m pytest tests/test_italy.py tests/test_rail_preparation.py tests/test_compact_schedules.py
```

Source hashes are enforced. The browser was checked for national coverage, Frecciarossa, Trenord S13, Italo AV, detailed service paths, Italy Overview, weekday/Sunday switching, accelerated playback, themes and fullscreen.

## Next time — not implemented

1. **Longer period:** validate actual source snapshots and every calendar/carry day; conversions use NAP checked resources whose publication may lag their Git commit. Retain Italo's direct-journey filter, bus exclusions, duplicate handling and original clocks. Never stretch dates or backdate latest downloads.
2. **EAV / Campania rail:** [official EAV open data](https://www.eavsrl.it/open-data/) lists GTFS for rail and buses, with IODL terms. Validate an actual historical ZIP matching the chosen period, agency/mode scope, narrow-gauge geometry and overlap with Trenitalia before enabling. The national [Campania RAP/NAP](https://www.cciss.it/nap/mmtis/public/en/catalog/Dataset) is another discovery source. No EAV services are enabled now.
3. **Ferrotramviaria / Circumetnea / other regional operators:** official [Ferrotramviaria](https://ferrotramviaria.it/web/guest/rete) and [Circumetnea timetables](https://www.circumetnea.it/le-nostre-linee/) are starting points. No matching dated machine-readable feeds were validated here; website/PDF timetables alone are not an implemented replay. Audit regional RAP feeds, calendars, narrow-gauge topology and terms. Do not treat Trenitalia as coverage of all independent operators.
4. **Milan urban transport:** [Comune di Milano ATM GTFS catalogue](https://dati.comune.milano.it/dataset?groups=tran&res_format=GTFS), producer feed `https://dati.comune.milano.it/gtfs.zip`. Validate dated archives and distinguish metro/tram/bus geometry. Do not duplicate Trenord suburban trains.
5. **Rome:** [Roma Mobilità open-data/geographic sources](https://romamobilita.it/sistemi-e-tecnologie/dataset-geografici/) and [transport data context](https://romamobilita.it/sistemi-e-tecnologie/centrale-mobilita/); validate actual static GTFS download, historical coverage, licence and ATAC/Roma TPL scope before adding metro/trams/buses.
6. **Turin:** GTT publishes `https://www.gtt.to.it/open_data/gtt_gtfs.zip` and [specific GTFS reuse terms](https://www.gtt.to.it/gtt_gtfs_license.html). Historical archives and each transport mode still need validation.
7. **Genoa / Catania / Palermo / Brescia:** [AMT Genova GTFS](https://www.amt.genova.it/amt/societa_trasparente/altri-contenuti/open-data/), [AMTS Catania GTFS/IODL](https://www.amts.ct.it/open-data) and [Palermo municipal GTFS catalogue](https://www.dati.gov.it/node/192?access_rights=PUBBLICO&organization=comune-di-palermo&tags=mobilita---amat---autobus---percorso---fermata---tram) are discovery sources, not validated historical integrations. AMTS buses do not establish Circumetnea metro coverage. Brescia Mobilità's matching dated metro/bus feed remains unvalidated. Use each operator's own colours and actual rail/road geometry; no Melbourne-orange bus fallback.
8. **Passengers:** [Istat railway statistics](https://www.istat.it/informazioni-sulla-rilevazione/trasporto-ferroviario/) cover annual/quarterly passenger flows, not individual train loads for this week. No suitable historical train-level occupancy dataset was validated; keep passenger features optional/disabled.
