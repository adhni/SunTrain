# European international winter gaps

Bismillah, this pass adds dated captures to **World · Flights** for **2 November 2026 UTC**, starting from 57,227 records, including 28,536 international flights. It uses a **100-search ceiling**, reviews every **25 attempts**, two workers, exact airport queries, all returned airlines and one-adult economy one-way **USD** fares. There are no additional-date sweeps or all-airport pair searches.

## Why only 25 searches

The remaining Europe route-map queue mixes summer services, later winter starts, wrong weekdays and already captured flights. That queue is a discovery list, not a list of confirmed missing Monday services. This pass reviewed the actual winter programmes for Nice, Bordeaux, Nuremberg, Weeze, Ancona, Toulouse and Strasbourg before collecting anything.

The selected 25 directional queries use five primary documents. Their downloaded PDF hashes, page numbers, reviewed exact-airport pairs, carriers, validity dates and weekdays are recorded in `data/sources/world_international_europe_winter.json.gz`:

- [Nice winter programme with operating days](https://entreprises.nice.aeroport.fr/services-compagnies/developpement-du-reseau/programme-vols-reguliers), updated 6 September 2026.
- [Bordeaux autumn/winter programme](https://www.bordeaux.aeroport.fr/professionnels/informations-actualites/le-programme-automne-hiver-20262027-en-detail), PDF edition 7 October 2026. Weekdays were checked visually because its frequency marks are vector artwork.
- [Nuremberg winter programme](https://www.airport-nuernberg.de/de/flugplan), updated 14 September 2026. Starred, non-continuous services were deferred.
- [Toulouse winter programme](https://www.toulouse.aeroport.fr/vols-et-destinations), updated 29 September 2026.
- [Strasbourg winter programme](https://www.strasbourg.aeroport.fr/passagers/programme-des-vols-et-ouverture-de-laerogare/), updated 23 October 2026.

The compact reviewed selection skips ten directions already captured, one direction already charged in an earlier campaign and seven ineligible route entries. Exclusions include Nice–Liverpool starting in March, Bordeaux–Naples starting 4 December, Toulouse–Pisa starting 6 November, Toulouse–Naples ending 30 October, and Strasbourg–Florence starting 6 November. Nice–Malaga does not operate on Monday in the reviewed programme. Weeze's reviewed Monday European directions were already captured; Ancona's later-starting Volotea programme does not justify November 2 searches. The Germany–Spain backlog is not blindly queried: reviewed Monday routes at Nuremberg and Weeze were already represented.

The final queries cover **BOD 7, NCE 12, NUE 1, SXB 4 and TLS 1**. Published outbound schedules nominate both directions as candidates, but the manifest explicitly distinguishes published departures from return-route leads; it never claims that the published outbound proves a same-day return. Nice–London City is the only two-direction cache override, justified by the airport's Monday winter programme. Both older empty captures remain intact. No previously charged international campaign query is repeated.

The finite evidence list is exhausted after 25 searches. The remaining **75 budget slots are deliberately unused**; no weaker route pairs are generated to fill them. This is a targeted regional pass, not a complete audit of every European winter timetable.

## Captures and remaining gaps

**25 completed searches: 18 nonempty, seven empty; 23 dated records, all 23 with USD fares.** No failed, interrupted or rejected query and no access challenge. Captured offers retain their original currency and cheapest compatible returned quote; there is no currency conversion.

The seven empty directions are **BOD → PRG, NCE ↔ FLR, NCE ↔ NAP and NCE ↔ LCY**. Empty means **not returned**, even when a winter timetable lists a route. These contradictions remain documented collection gaps; frequency tables do not supply invented flight times. They are not automatically retried.

The collector emitted `Browser disconnected; finishing profile cleanup in background` after all 25 captures were saved. Capture validation passed; this browser shutdown delay is recorded separately from flight-query failures. The collector subsequently exited normally and published from the saved captures.

## Preservation and reproduction

The manifest pins all four preceding international ledgers, their 1,600 charged attempts, the starting World snapshot, preceding supplement and 46 input hashes. Existing country/region archives, the South America domestic expansion, flight presentation and format 28 remain unchanged. Preparation reuses validated compatible captures and the existing cumulative supplement; normal World HTTP requests do not collect flights or rebuild member views.

```sh
export PYTHONPATH=.cache/browser-tools:.
export PYTHONPYCACHEPREFIX=.cache/pycache
.venv/bin/python scripts/prepare_international_europe_winter.py manifest
.venv/bin/python scripts/prepare_international_europe_winter.py collect  # finite list, at most 25 per review
.venv/bin/python scripts/prepare_international_europe_winter.py finalize # offline; raw captures required
.venv/bin/python scripts/prepare_world_flights.py                        # committed archives only
```

Completed resumption must perform zero further searches. Rebuilding the supplement needs the ignored raw captures and pinned catalogue caches; portable World preparation only needs committed prepared archives. Historical preparation commands refuse to overwrite a newer campaign. Raw PDFs, extracted tables, screenshots, comparison baselines, journals, scorecards, logs and the added-flight list stay under ignored `.cache/international-europe-winter/` and `.cache/google-flights-world-international-usd-europe-winter/`.

The UTC day and local airport-board clocks stay unchanged. Adjacent-day captures, unreviewed European networks, smaller airports, missing search results and other global gaps remain partial coverage. The wider historical candidate queue is not a denominator for national or worldwide completeness.

## Published results and validation

| Metric | Before | After | Added |
| --- | ---: | ---: | ---: |
| All overlapping flight identities | 57,227 | **57,250** | **23** |
| International identities | 28,536 | **28,559** | **23** |
| International departures inside the UTC day | 26,506 | 26,529 | 23 |
| International directional routes | 12,040 | **12,058** | **18** |
| Airports with international captures | 828 | 828 | 0 |
| International records with primary fares | 24,307 | 24,330 | 23 |
| Domestic records | 28,691 | 28,691 | 0 |

The 23 additions comprise **Bordeaux 9, Nice 8, Nuremberg 1, Strasbourg 4 and Toulouse 1** records, counting return-route queries with their evidence airport. Examples: BOD → LGW (3), BOD → LIS (2), NCE ↔ LUX (2 each), NCE ↔ DUS (1 each), NCE ↔ TBS (1 each), SXB ↔ CPH (1 each), SXB ↔ MUC (1 each), MXP → TLS (1) and NUE → BEG (1). These are captured directional scheduled identities, not inferred physical aircraft movements.

An exact before/after comparison preserves all **57,227 previous identities**, every prior compatible fare quote, specified aircraft alternative and source-ID provenance, all **28,691 complete domestic records** and all **1,849 airport catalogue entries**. All **45 immutable input hashes** and four preceding campaign hashes match. No prior identity was removed. The complete addition list is under ignored `.cache/international-europe-winter/added-flights.csv`; machine-readable preservation results and checkpoint scores are alongside it.

Prepared World: **3,194,173 bytes gzip**; cumulative international supplement: **617,647 bytes gzip**. The actual local HTTP response transfers **5,635,861 bytes / 5.37 MiB gzip**, up 3,049 bytes from the preceding pass. It contains 57,250 services and 1,849 stations and retains gzip, matching ETags, format 28 and endpoint-only geometry. A cached localhost retrieval measured 16.86 ms; this is not a hosted-network or first-map measurement. The original 5 MiB HTTP target remains exceeded; this pass makes no rendering-performance claim.

**Validation passed: 229 relevant Python tests, 78 JavaScript tests and three browser regressions.** Python coverage includes winter validity/weekday exclusions, exact European airport identity and direction evidence, compatible-cache reuse, the two-query recheck allowlist, the 100-attempt ceiling and 25-query checkpoint, finite-list exhaustion without spending the remaining budget, durable journal recovery, all four parent ledgers, aircraft/fare preservation, UTC/local boards, deterministic World preparation and source hashes, HTTP caching/date rejection, flight presentation, bilingual behavior and Australian/Melbourne compatibility. The real completed campaign was resumed once: **zero new searches**, still 25 durable attempts.

The World browser verifies the added Bordeaux → Gatwick records through France → UK filters and Bordeaux/Strasbourg local boards, alongside global/peak playback, dateline clipping and picking, selected journeys, scope/airline filters, destinations, fullscreen/back, fares, frequency, palette switching, both languages, themes and mobile. Bilingual and Melbourne browser assertions also passed with no page errors. All three browser regression processes exited normally; their assertions and shutdowns are separate from the collection shutdown delay noted above. Screenshots and logs remain ignored under the campaign cache.
