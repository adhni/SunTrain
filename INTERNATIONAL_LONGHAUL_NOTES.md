# International long-haul and UTC-gap expansion

Latest pass: [European winter gaps](INTERNATIONAL_EUROPE_WINTER_NOTES.md). This document retains the completed 200-query checkpoint and its original results.

Bismillah, this pass extends **World · Flights** from **57,024 flights / 28,333 international records** on **2 November 2026 UTC**. It has an independent **200-search cap**, reviewed every 50. It uses the existing validated international supplement, exact-airport queries, all returned airlines and verified USD fares, retaining the cheapest compatible returned offer and existing quotes without conversion.

| Workstream | Search cap | Selection |
| --- | ---: | --- |
| North America–East Asia | 80 | Uncaptured published directions between US/Canada/Mexico and China/Japan/Korea/Taiwan/Hong Kong/Macao/Mongolia |
| Europe–East Asia | 69 | Uncaptured published directions from the reviewed European countries |
| UTC-boundary gaps | 50 | Specific 1 November origin-local queries backed by observed North American departures whose shifted timings can overlap the UTC day |
| Official timetable recheck | 1 | HND → LHR, once, because the prior empty capture contradicts ANA's dated daily timetable |

There are **150 exact 2 November queries and 50 exact 1 November queries**. No whole extra day, additional week, all-airport pair matrix, international connecting itinerary or automatic refresh is introduced. Airport boards retain half-open UTC-day events displayed in airport-local time, including preserved Canadian replay-zone overrides. All selected directions were absent from the starting World snapshot; the boundary selections also had no captured direction. Published maps and shifted timing clues are search evidence only, never synthetic flight records or proof of daily service.

## Evidence and preservation

The manifest pins all three completed international campaign ledgers (1,000 + 300 + 100 attempts), the 57,024-record World baseline, its 46 input hashes and the preceding prepared supplement. All prior charged attempts, including failures, are excluded. Two concurrent workers durably charge attempts before navigation and stop on an access challenge. Completed resumption performs zero further searches.

The only permitted compatible-cache override is the single timetable-backed HND → LHR recheck. The [official ANA winter route table](https://www.ana.co.jp/en/us/plan-book/routes/international-route-information/) lists NH211 daily for 25 October 2026–27 March 2027. Its reviewed downloaded HTML has SHA-256 `a9b1d7277357e1de3a88b1458beb84c770096b226b2ac23504da9c236a1bdf1b`, recorded with the source URL and dated facts. The original empty capture stays intact. That recheck returned JL41, JL43, NH211 and BA6; these are dated captured records, not four inferred daily frequencies.

The 50 boundary queries come from 216 compatible timing-backed candidates. The manifest records each source path/hash, original clocks, explicit airport zones and derived timing proof. For example, origin-local 2 November Toronto → Heathrow captures depart on 3 November UTC and do not fill the selected World day; the justified 1 November query supplies actual dated results for evaluation. Uncollected adjacent local dates, including early eastern-airport departures on 3 November, remain gaps.

Europe/Asia route maps can include seasonal services. Empty means “not returned,” never “no service.” Ezeiza long-haul candidates were not included: the [official Argentine notice](https://inprotur-prod.turismo.gob.ar/prensa/novedades/ezeiza-mantendra-su-operatividad-y-la-conectividad-internacional-durante-las-obras-en-su-pista-principal) describes runway restrictions covering the replay date. Iran/Angola and new South American international networks remain separate collection/source-validation work.

## Reproduction

The published campaign ledger is `data/sources/world_international_longhaul.json.gz`. It includes the selected exact queries, source evidence, attempts, source hashes, checkpoint allocations and before/after metrics. The cumulative prepared supplement retains the existing path `data/reference/world_international_expansion/2026-11-02.json.gz`; the derived World retains its current URL, format 28, endpoint-only geometry and HTTP compression/cache behavior.

```sh
export PYTHONPATH=.cache/browser-tools:.
export PYTHONPYCACHEPREFIX=.cache/pycache
.venv/bin/python scripts/prepare_international_longhaul.py manifest
.venv/bin/python scripts/prepare_international_longhaul.py collect  # next reviewed 50, up to 200 total
.venv/bin/python scripts/prepare_international_longhaul.py finalize # offline, raw caches required
.venv/bin/python scripts/prepare_world_flights.py                  # portable prepared archives only
```

Older campaign ledgers and original view archives remain unchanged. Historical test comparisons follow hash-pinned descendants and account for the independently prepared domestic addition exactly once. Old domestic preparation refuses to overwrite the newer international supplement because its historical frozen supplement hash changed. Normal World rebuilding uses committed prepared archives and does not need ignored Google caches or rebuild member views on HTTP requests.

## Results and validation

Results below describe the completed capped pass. Raw captures, the pinned timetable HTML, immutable comparison baselines, scorecards, added-flight CSV, browser screenshots and logs remain under ignored `.cache/international-longhaul/` and `.cache/google-flights-world-international-usd-longhaul/`.

| Metric | Before | After | Added |
| --- | ---: | ---: | ---: |
| All overlapping flight records | 57,024 | **57,227** | **203** |
| International overlapping records | 28,333 | **28,536** | **203** |
| International departures inside the UTC day | 26,317 | 26,506 | 189 |
| International directional routes | 11,916 | **12,040** | **124** |
| Airports with international captures | 827 | **828** | 1 |
| International records with primary fares | 24,143 | 24,307 | 164 |
| Domestic records | 28,691 | 28,691 | 0 |

**200 attempts / 200 completed captures:** 126 nonempty, 74 empty; zero failed, interrupted or rejected queries and no access challenges. They returned 209 dated raw records with 169 USD fares; UTC overlap retains 203 additions with 164 fares. No previous identity is removed. These are exact scheduled flight identities, not a claim to have measured all physical aircraft movements or every frequency on a route.

| Workstream | Searches | New World records |
| --- | ---: | ---: |
| North America–East Asia | 80 | 103 |
| Europe–East Asia | 69 | 36 |
| UTC-boundary gaps | 50 | 60 |
| Official HND → LHR recheck | 1 | 4 |

| Reviewed checkpoint | Added records so far | Added directions so far |
| --- | ---: | ---: |
| 50 searches | 62 | 33 |
| 100 searches | 130 | 70 |
| 150 searches | 178 | 104 |
| 200 searches | **203** | **124** |

Examples: NRT → LAX (5), LAX → NRT (5), ICN → SEA (4), YVR → ICN (4), HND → LHR (4), YYZ → LHR (4), PVG → LAX (3), and JFK → PVG (1). These counts describe captured records overlapping the UTC day, including in-air arrivals from the prior date. **TIJ** now has international captures through PEK ↔ TIJ; its existing airport identity remains unchanged. The historical candidate queue has 4,027 remaining route/date entries; those are neither confirmed dated services nor an exhaustive global gap list.

The complete 203-record addition list is under ignored `.cache/international-longhaul/added-flights.csv`. Data validation preserves all **57,024 prior flight identities**, all **28,691 complete domestic records**, every prior compatible fare quote, specified aircraft alternative and source-ID provenance, and all **1,849 prior airport catalogue entries**. All **45 immutable input hashes** and three parent campaign hashes match. The international supplement is the only changed input among World's 46 member archives.

Prepared supplement: **614,409 bytes gzip**. Prepared World: **3,192,641 bytes gzip**. The actual local replay transfers **5,632,812 bytes / 5.37 MiB gzip**, compared with 5,608,985 bytes before this pass (+23,827 bytes). The original 5 MiB HTTP target remains exceeded; there is no new rendering or performance-improvement claim. A cached localhost HTTP retrieval measured 24.42 ms; that is not a first-map or hosted-network measurement. The live local response contains 57,227 services and 1,849 stations and retains gzip, ETags, format 28 and endpoint-only geometry.


**Validation passed:** 212 relevant Python tests, 78 JavaScript tests and three browser regressions (World, bilingual UI and Melbourne map/boards). Python checks cover the independent 200-search budget, 50-query checkpoints, durable recovery after journal loss, explicit one-query cache override, pinned parent hashes and timetable evidence, UTC timing proofs, fares, local dates, prepared World byte-for-byte reproducibility and read-once inputs, the unchanged original 40-view union, HTTP gzip/ETags/date rejection and transit compatibility. Historical checkpoints are verified through hash-pinned descendants, with the domestic layer counted once.

The World browser checks the new NH211 capture through Japan → UK filters, stable camera/time, global and peak playback, dateline viewport clipping/picking, scope/airline/country filters, local airport boards, destinations/fullscreen/back, alternate quotes, frequency totals, source evidence, World → Europe → Singapore palettes, both languages, themes and mobile. The existing bilingual regression covers calendar/keyboard/fullscreen/state preservation; Melbourne covers vehicle sizes/turns/seeking, station hover/click/visibility and board/journey navigation. All three browser runs exited normally, without page errors, assertion failures or shutdown failures. The completed real campaign was resumed once and performed **zero further searches**.
