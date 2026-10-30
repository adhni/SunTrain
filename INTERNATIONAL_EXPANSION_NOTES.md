# World international passenger expansion

This page records the first, completed 1,000-search campaign. The subsequent
300-search pass is documented in [INTERNATIONAL_FOLLOWUP_NOTES.md](INTERNATIONAL_FOLLOWUP_NOTES.md).
The later 100-search campaign is in [INTERNATIONAL_BOUNDARY_NOTES.md](INTERNATIONAL_BOUNDARY_NOTES.md).
Current totals and the active cumulative preparation command are in
[INTERNATIONAL_LONGHAUL_NOTES.md](INTERNATIONAL_LONGHAUL_NOTES.md).

This campaign expands **World · Flights** for **2 November 2026 UTC**. It uses public dated passenger-flight captures, keeps individual flight numbers, and remains partial coverage. The 40 existing country/region views and their reference archives are unchanged. There is no additional homepage location, currency conversion, live tracking or automatic refresh.

## Collection policy

- Recover compatible all-airline caches before searching. The original baseline is 53,591 overlapping flights, including 25,693 international flights and 23,950 international departures inside the UTC day.
- Use published exact-airport routes from 35 Asian/Gulf/intercontinental gateways and nine underrepresented European airline networks, supplemented by previously reviewed manifest candidates. Foreign endpoints need not belong to an existing country view. Both directions are candidates, never proof of dated service. No new airport-pair Cartesian product is generated.
- Attempt at most **1,000 new route/date searches** with two workers. The original stream allocations are 350 Asian/Gulf, 300 European airline, 250 intercontinental and 100 absent-country searches; unused allocations spill in stream order. Published routes touching multiple streams belong to the first applicable stream. The selected queue mixes streams across checkpoints.
- Use origin-local 2 November first. Additional local dates require observed timing evidence of possible UTC overlap. Unobserved adjacent-day schedules remain an explicit gap; this campaign does not collect another whole week.
- Each request is durably charged before navigation, including failed or interrupted requests. A revised unattempted queue cannot erase previous attempts. The final source ledger also retains the attempt journal, preventing a fresh checkout from silently resetting a completed campaign.
- Stop on access challenges, retain successful captures and do not automatically retry. Empty results mean **not returned**, not no service. Partial parser rejections are reported and excluded from query ownership.
- New fare requests use USD, one adult, economy, one-way. Schedules remain usable without a verified fare. All compatible historical quotes survive in their original currencies, with cheapest USD preferred, then EUR, then MYR; no quotes transfer between changed flight identities.

## Integrity and integration

`data/reference/world_international_expansion/2026-11-02.json.gz` is a separately validated prepared input to World. `data/sources/world_international_expansion.json.gz` holds the frozen candidate ledger, published-source URLs/hashes, cache evidence, missing identities, remaining queue and final collection scorecard. Raw query files and route-map downloads remain under ignored `.cache/` and are not duplicated into another cache tree.

Latest successful complete captures own their exact route/local-date query slots. Older positive results cannot override newer empty results; raw caches older than the validated adapters cannot restore excluded schedules. The verified settings of legacy 24-hour collectors are recorded explicitly when their captures predate per-query parser metadata. Truly incompatible empty eight-hour results remain unusable for the long-haul collector.

Owned query replacements are applied before World's canonical merge. Unchanged identities retain original source evidence and quotes. Independent official Ryanair timetable entries absent from Google survive, following the existing Europe preparation policy. Exact carrier, number, origin, destination and UTC times define identity; distinct flight numbers are not inferred codeshares. Conflicting same-source IDs fail preparation.

Airport identity resolution reuses validated World records and the pinned OurAirports/OpenFlights catalogues. Retired Cambodian endpoints are excluded, and new codes require an unambiguous active identity and explicit IANA zone. XPL uses the reviewed `America/Tegucigalpa` zone. Existing Canadian dated replay offsets and the US/Puerto Rico domestic jurisdiction rule are preserved. Unknown aircraft remain unknown; specified aircraft disagreements retain their alternatives.

World preparation checks the original 44 input hashes, reads the supplement once, and writes the derived World snapshot. Normal HTTP requests still read only that snapshot. Endpoint-only geometry, lazy browser arcs, viewport clipping, compression, ETags, HTTP format 28 and the UTC timeline remain unchanged. The source-evidence panel labels the additional input in English and Indonesian.

## Reproduction

Run from the repository root with the existing browser tools:

```sh
export PYTHONPATH=.cache/browser-tools:.
export PYTHONPYCACHEPREFIX=.cache/pycache
.venv/bin/python scripts/discover_international_expansion.py audit
.venv/bin/python scripts/discover_international_expansion.py discover
.venv/bin/python scripts/discover_international_expansion.py manifest
.venv/bin/python scripts/prepare_international_expansion.py recover
.venv/bin/python scripts/prepare_international_expansion.py collect
.venv/bin/python scripts/prepare_international_expansion.py finalize
```

`audit` reads caches; `discover` may download missing published route maps. Only `collect` searches Google Flights. The attempt journal is under `.cache/google-flights-world-international-usd-v1/attempts.json`; it is restored from the published ledger when necessary. Do not delete or replace it to obtain another 1,000 searches. A stored access stop requires a separate review, not an automatic retry.

Once inputs are prepared, regenerate World entirely offline with:

```sh
PYTHONPATH=. .venv/bin/python scripts/prepare_world_flights.py
```

Re-preparing the supplement additionally requires the original raw captures named and hashed in the ledger. Missing raw caches are evidence gaps, not permission to recollect automatically. A fresh audit reconstructs the original 40-view baseline rather than treating the already-expanded World as a new baseline. If a source archive changes, preparation fails for review instead of silently reinterpreting this dated campaign.

## Remaining coverage

The source maps are seasonal discovery evidence, not dated schedules. Several absent-country airport maps and Bulgaria Air's carrier map returned HTTP 404; their gaps remain recorded, while other published gateway maps supply reciprocal candidates. Some candidates cannot be resolved to an exact airport/timezone. The remaining ranked queue is preserved separately from the 1,000-query campaign.

This campaign cannot establish worldwide completeness: [Google Flights omits some airlines and available flights](https://support.google.com/travel/answer/2475306?hl=en). It also does not establish all frequencies on a returned route. No service is invented from frequency-only or historical route evidence.

## Results and validation

| Metric | Original World | Expanded World | Net change |
| --- | ---: | ---: | ---: |
| All overlapping flights | 53,591 | 55,599 | +2,008 |
| International overlapping flights | 25,693 | 27,701 | +2,008 |
| International departures inside the UTC day | 23,950 | 25,850 | +1,900 |
| International directional routes | 11,135 | 11,724 | +589 |
| Airports with international captures | 778 | 826 | +48 |
| International flights with a primary fare | 20,604 | 23,419 | +2,815 |

Domestic overlapping records remain **27,898**. Counts use the project's existing country/territory and US/Puerto Rico jurisdiction treatment; they are exact captured identities, not an inferred count of physical aircraft movements.

Cache recovery supplied **1,433 net additional flights** and **1,367 additional UTC-day international departures**, without new searches. New collection supplied a further **575 net flights** and **533 UTC-day international departures**. Overall, 2,018 identities were added and ten superseded identities removed. The supplement contains 5,334 records because unchanged overlapping identities also contribute quote and aircraft evidence; its record count must not be added to the World total.

The campaign reserved exactly **1,000 attempts**: **998 completed captures**, including **377 nonempty queries / 621 empty results**, and **two interrupted in-flight requests**. No completed query failed or had rejected segments, and no access challenge occurred. The collector was paused after 116 reservations to correct compatibility for legacy captures without parser metadata; the two interrupted requests (`PEK → FNJ`, `AGP → HAJ`, both local 2 November) remain charged and were not retried. Running out of budget does not turn them into successful queries.

New searches returned **595 raw dated records**, of which **536 had verified USD quotes**. World-window selection, deduplication and query replacements account for the difference from net additions. The final queue used 992 origin-local 2 November queries and eight timing-justified 1 November queries. It did not search a whole week.

The unused absent-country allocation spilled into Asian/Gulf routes: final stream totals were **450 / 300 / 250 / 0**. Routes involving all six absent-country targets were still considered through other gateway/airline streams. New returned country/territory endpoint codes are **AI, BM, BQ, BZ, CU, DM, GD, HN, HT, KN, KY, NI, TC, VC, VG and VI**. Iran and Angola still have no returned World endpoints; no absence-of-service claim follows from that.

The final evidence queue retains **4,608 unattempted route/date candidates**, including adjacent-date candidates justified by the newly observed schedules. Ten airport identities are unresolved or excluded (including retired PNH), affecting 32 discovered directional candidates. These are discovery/identity gaps, not 32 confirmed active missing routes. Ten published map URLs returned HTTP 404. No extra searches were made to fill those gaps after the cap.

Detailed scorecards, raw-capture pointers, checkpoint logs, preservation comparisons, screenshots and measurements stay under ignored `.cache/international-expansion/`. The source ledger includes the final summary and durable attempt journal. Existing 40-view payloads and all 292 original reference hashes passed preservation comparisons; the original World union also reproduces its exact pre-expansion SHA-256 when the supplement is disabled.

Validation passed 145 targeted Python flight regressions, then 31 focused World/international/parser/bilingual tests against the final snapshot, a final 34-test budget/price/parser/bilingual suite, and all 122 JavaScript tests. These Python runs overlap and are not an additive unique-test total. The World test verifies byte-identical regeneration with each of its 45 archives read once, quote/aircraft preservation, compact HTTP geometry, caching/304s/date rejection and the original 40-view baseline. The completed collector was run again and performed zero further searches. Final guards cover absent/stale local journals, manifest regeneration retaining published attempts, conflicting journals, and refusal to erase prepared records when required raw captures are missing.

All five browser regressions passed with clean shutdowns: Europe, Singapore, bilingual UI, Melbourne and expanded World. World additionally checks Spain/Cuba filtering, Havana and Bermuda local boards, Canadian dated clocks, dateline picking/counts, quotes, destinations, frequency totals, Reset/Fit, view/palette switching, fullscreen, themes and mobile. No assertion or shutdown failure is hidden in those results. During collection, some disconnected Chrome profile cleanup finished in the background; the intentional 116-attempt pause required terminating its stalled task-owned collector after saving its journal.

## Performance measurements

The expanded World download is **5,436,083 bytes / 5.18 MiB gzip**, versus 5,095,519 bytes / 4.86 MiB previously (+6.7%). Flight identities increased 3.7%, with additional quote evidence. Endpoint-only geometry remains in place; no route coordinate arrays or full query ledger enter the World HTTP payload. The regression test bounds compressed transfer density as the corpus grows rather than enforcing the old 53,591-record download limit on a larger dataset.

Local Chrome/software WebGL, warmed HTTP cache, three fresh contexts per condition, median of three; no collector or other audit browser ran during measurement:

| Measure | Previous desktop | Expanded desktop | Previous 4× CPU/mobile viewport | Expanded 4× CPU/mobile viewport |
| --- | ---: | ---: | ---: | ---: |
| First map | 8.48 s | 7.89 s | 12.01 s | 12.69 s |
| Heathrow board | 1.74 s | 1.24 s | 1.67 s | 1.77 s |
| Airline filter | 0.28 s | 0.21 s | 0.50 s | 0.51 s |
| Peak paint p95 | 26.1 ms | 24.6 ms | 140.7 ms | 165.5 ms |

Expanded peak playback used the actual maximum **7,973 active flights at 15:00 UTC**, compared with the previous 7,584. These local samples are not a controlled physical-phone benchmark or evidence that coverage changes improve performance. Desktop first-map/board targets remain missed, and the expanded 4× CPU peak paint now exceeds the earlier 150 ms target; this is recorded for follow-up. The 4× CPU first-map, board and filter targets and desktop peak-paint target remain met. All six measurement contexts had no page errors, and benchmark browser shutdown completed.
