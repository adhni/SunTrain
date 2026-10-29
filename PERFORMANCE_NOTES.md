# Replay performance and memory

The first 30 October World international expansion increased the collection to 55,599 flights and a 5.18 MiB gzip HTTP download. Its actual peak was 7,973 active flights. Median first-map readiness measured 7.89 s desktop / 12.69 s at 4× CPU, board response 1.24 s / 1.77 s, and peak paint p95 24.6 ms / 165.5 ms. The 4× CPU peak exceeds the earlier 150 ms target; desktop first-map/board targets also remain missed. Full collection evidence, baseline comparisons, method and limitations are in [INTERNATIONAL_EXPANSION_NOTES.md](INTERNATIONAL_EXPANSION_NOTES.md).

The subsequent targeted 300-search pass brings World to **55,988 flights** and **5,479,477 bytes / 5.23 MiB gzip HTTP** (+0.8% download). Rendering and HTTP format 28 are unchanged. The responsiveness/peak-paint measurements above apply to the earlier 55,599-flight snapshot; this follow-up does not claim an updated performance benchmark. Collection and validation results are in [INTERNATIONAL_FOLLOWUP_NOTES.md](INTERNATIONAL_FOLLOWUP_NOTES.md).

All existing historical date ranges, routes, passenger records and geometry are retained. Melbourne trains keep FY2023–24; trams/buses keep five weeks. This change does not create daily files for every city or change hosting plans.

## Representation and rebuilding

Every committed schedule reference uses `shared-stops-flat-times-v1`. A pattern holds a shared stop-sequence ID and a flat relative timing vector. Each shared sequence holds station IDs and geometry leg IDs. Timings remain distinct when traffic profiles or dwell times differ; loops retain every stop occurrence. Existing pattern/trip/path IDs are unchanged. Older unpacked references remain readable for environment overrides.

All seven common preparation modules now call `scripts.compact_transit.save_reference()`. Toronto, DC/BART and London reuse the common rail preparer. Boston and London optional buses already use this encoding. Existing preparation commands still rebuild their respective files; source archives and licences are unchanged. Saving is atomic and deterministic, and the shared writer is idempotent. Do not expand a schedule into separate stop arrays per trip in the application.

Runtime timing vectors use read-only NumPy buffers (NumPy is already required by pandas and is now explicitly pinned to the tested version). Only their Python representation changes: `orjson` serializes them as the same ordinary JSON arrays used by the browser. Coordinates, timestamps and passenger values are not rounded or inferred.

## Server memory and concurrency

The versioned gzip HTTP cache is the persistent reusable representation within a running deployment. Parsed references and prepared-day caches are cleared before and after each uncached build. Garbage collection releases obsolete containers; a successful or failed build leaves no retained parsed schedules. A worker-wide generation lock prevents different dates/modes from building concurrently. A second request for the same version rechecks the compressed cache after waiting, so it does not rebuild the response.

Cache-hit downloads bypass generation entirely and remain available while an unrelated cold request builds. Open file descriptors preserve an in-flight response during cache eviction. The existing 256 MiB compressed cache limit, ETags, gzip negotiation and immutable versioned URLs remain. `FORMAT_VERSION` is now 28 (29 October 2026).

Serialization passes individual services, patterns and paths through a 64 KiB output buffer into gzip, avoiding a second complete day-sized JSON byte string. Pattern order from preparation is preserved so adjacent route/timing profiles compress together. Per-pattern geometry quality totals are reused rather than recomputed for every occurrence.

Bus-only Boston/London requests skip rail parsing and obtain attribution from their bus reference. Adding buses to selected rail copies both the pattern and shared-sequence dictionaries before appending, preserving cached rail-only payloads.

Cold requests queue behind other cold requests. This intentionally trades parallel generation throughput for a lower predictable memory peak. Do not increase Gunicorn worker count casually: the lock and memory budget apply per process, and each extra worker can hold another large schedule. Browser cancellation prevents stale data replacing the selected city, but does not cancel a Python build already running.

## Measurements on 18 October 2026

These are local macOS/Python 3.9 measurements. Render runs Python 3.12 and its actual service plan/logs were not accessible, so hosted performance and memory need verification after deployment.

| Selected replay | Previous gzip download | Updated gzip download |
| --- | ---: | ---: |
| Melbourne, all modes, 27 May 2024 | 12.5 MB | 4.0 MB |
| NYC, Subway + SIR, 15 December 2025 | 2.10 MB | 0.54 MB |
| London rail, 5 October 2026 | 2.65 MB | 0.83 MB |
| London buses only, 5 October 2026 | 19.5 MB | 13.6 MB |

The updated HTTP test loaded Melbourne trains, Melbourne all modes, NYC, London rail, Boston buses, London buses and then Melbourne trains again. Every response succeeded and every parsed schedule cache was empty afterwards. Melbourne all modes peaked around 421 MiB and returned to about 185 MiB resident memory. The sequence including London buses peaked around 470 MiB and returned to about 195 MiB. The cached Melbourne train response took about 8 ms in this local HTTP test.

Full London rail plus buses remains a large workload. A separate test peaked around 503 MiB in the app process, before a separate Gunicorn master or other activity. This change does **not** establish that every combination is safe on a 512 MB instance. Confirm actual Render memory limits/restart logs and leave hosting headroom. Free-service wake-up delays are also separate from these data improvements.

The 17 converted source references total about 28.35 MB versus 38.89 MB previously. Each transformed reference was checked against a canonical signature of every calendar, trip occurrence, station, schedule, route attribute, geometry path and original provenance field. All matched. Added encoding metadata is the only provenance-independent metadata change. Existing geometry gaps and unavailable passenger counts remain unavailable.

No new parser dependency or hosted infrastructure is required. Alternative parsers were tested and rejected when their memory use was worse. The retained implementation uses the existing standard JSON reader, numeric buffers and chunked output.

## Validation

Automated checks cover the shared representation in all 31 city/snapshot/bus bundles, loop occurrences, distinct clocks, deterministic writes, source-scope/calendar/geometry checks, cache release after success/failure, partial-file cleanup, single-build concurrency, duplicate-request coalescing and cache hits during a blocked cold build. Historical semantic checks decode individual shared patterns in test helpers only; runtime trips retain shared references.

The completed suite passed **198 Python tests and 26 JavaScript tests**. Chrome validation passed for all 13 cities and the controls below, with no page or console errors.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
node --test tests/test_replay_animation.cjs tests/test_passenger_demand.cjs
```

Browser validation covers every city, optional buses, filters/details, clock preservation, 2,000× playback, Melbourne heatmaps, Overview, mobile layout, themes and fullscreen. Performance artifacts and the source-conversion audit are local ignored files under `.cache/`.

## Toronto streetcars and optional Chicago/Perth buses (18 October 2026)

Toronto's existing seven-day reference now includes streetcars, with the same shared timing/topology representation. Chicago and Perth buses reuse the existing optional daily-bundle loader, so their initial rail requests do not open bus data and bus-only requests do not open rail. The bus bundles add about 116 MB to the repository; that collection is not transferred to a visiting browser. A request opens one selected city/day and sends only its selected modes. Rail sources and coverage remain unchanged.

An isolated local Python 3.9 HTTP-generation sequence measured Chicago buses (24 November 2025) at **1.520 s / 4.061 MB gzip**, then Perth buses (5 October 2026) at **1.399 s / 3.126 MB gzip**. Process peak RSS was about **180.5 MiB**, then **195.5 MiB**, respectively. These measurements exclude the separate web-server master and are local cold-build measurements, not Render or phone guarantees. Existing cache limits, build serialization and schedule release still apply.


## Departure boards and flight downloads (29 October 2026)

Departure picker options now render airport/station names and route lists directly as text. Only their interface tokens (transport names and missing-location text) are translated; switching English/Indonesian rebuilds choices while preserving the board state. This removes the expensive translation-pattern matching on long source labels without changing the global translation engine.

Flight HTTP responses omit only the top-level `schedule.queries` and `schedule.wizzair_inventory` fields. Complete collection evidence remains in the committed reference files and Python replay objects. Coverage summaries, credits, fares, notes, unknown metadata and nested fields remain available. The HTTP format advances from 25 to **26** to invalidate old response URLs; gzip, ETags, conditional responses and immutable caching remain in place.

Paired local Chrome measurements used one Gunicorn worker, four threads, a dedicated ignored response cache and three fresh-browser samples per condition. Each Europe replay was fully loaded before opening Heathrow from the unfiltered map at the default time. The timer ended after the airport filter/board synchronization and two animation frames. The final measurements used both production changes with no browser monkeypatches. These are local software-WebGL measurements, not public-host or physical-phone guarantees.

| Board opening, median of 3 | Before | After | Improvement |
| --- | ---: | ---: | ---: |
| Desktop | 3.30 s | 1.24 s | 62.5% |
| 390 × 844 viewport, 4× CPU throttling | 11.04 s | 2.52 s | 77.1% |

Generated downloads, gzip level 3; MB means 1,000,000 bytes:

| Replay | Before | After | Flights preserved |
| --- | ---: | ---: | ---: |
| Europe | 8.759 MB | 7.412 MB | 13,073 |
| Africa | 2.187 MB | 1.960 MB | 3,693 |
| Americas | 3.247 MB | 3.019 MB | 11,783 |
| Singapore | 0.396 MB | 0.340 MB | 1,101 |

For all four flight snapshots, decoded responses matched the baseline exactly after excluding the revision and the two intentionally removed audit fields. Reference-file SHA-256 hashes were unchanged. Melbourne's decoded response was also unchanged apart from revision; its gzip size differed by 42 bytes because the revision string changed. All four flight download budgets and both board-time/improvement targets were met.

Validation passed **80 targeted Python tests and 108 JavaScript tests**. Europe (30 airport boards), Africa, bilingual replay/calendar/mobile/fullscreen, and homepage/coverage/source-credit browser checks passed without page errors. New tests prevent option data entering translation matching, preserve literal HTML-like text, cover language round trips and verify HTTP source immutability, empty/missing audit fields, transit preservation, gzip/plain equivalence, cached 304s and format invalidation.

The transit-departure browser script completed all assertions successfully on two runs, but local Chrome stalled at `browser.close()` afterward and required interrupting those audit-owned test processes. Explicit context closure did not resolve that shutdown issue, so no speculative cleanup change was retained. This is a browser-harness limitation; its process exit is not reported as a clean pass.

Detailed samples, preservation comparisons and logs are under ignored `.cache/performance-small-fixes/`. Audit-only servers and generated HTTP/baseline gzip files were cleaned up after validation. Route geometry, cache prewarming and hosting changes remain deferred. No flight searches, source-data preparation, hosting changes or deployment were performed.

## Consistent flight maps (29 October 2026)

Flight HTTP format is now **27**, adding `flight_view_kind` and local-date 10:00 opening behavior. The compressed endpoint structure, cache policy and exclusion of download-only query metadata remain intact. The presentation uses individual dots below zoom 4.5, fixed 16 px plane canvases nearby and a 22 px selected plane at every zoom. Full behavior and coverage boundaries are in [FLIGHT_DISPLAY_NOTES.md](FLIGHT_DISPLAY_NOTES.md) and [FLIGHT_COVERAGE_GAPS.md](FLIGHT_COVERAGE_GAPS.md).

The new viewport counter initially projected every active flight and repeatedly read canvas dimensions. Its first isolated samples averaged a median **12.1 ms desktop / 58.3 ms at 4× CPU** per playback paint. The final implementation reads one geographic viewport for a level, unrotated map, with exact screen projection retained for rotated/tilted maps. It also caches carrier/colour sprite keys and avoids writing/translating the flight count twice. Independent screen projection matched the optimized count across all 13 actual opening maps, including Pacific wrapping; identities are deduplicated without clustering.

Final measurements used local Chrome/software WebGL, one Gunicorn worker/four threads, a warmed dedicated HTTP cache and three fresh browser contexts per condition. No other audit browser ran during the final samples. Europe was fully loaded, then played for three wall-clock seconds at 60× speed (about 1,768 active flights). Before measuring Heathrow board opening, the clock returned to 10:00. The board timer ended after filter/board synchronization and two animation frames, following the previous benchmark's completion rule.

| Median of 3 | Earlier notes | Final |
| --- | ---: | ---: |
| Desktop Heathrow board | 1.24 s | **0.46 s** |
| 390 × 844, 4× CPU Heathrow board | 2.52 s | **1.57 s** |
| Desktop playback JS per paint | 6.9 ms | **7.8 ms** |
| 390 × 844, 4× CPU playback JS per paint | 29.2 ms | **35.9 ms** |

Board responsiveness improved in these samples, consistent with removing automatic camera fitting during airport filtering. Playback JS remains slightly higher than the earlier notes, despite the counter optimization. The earlier playback numbers were from a separate run, not a paired same-session baseline. These measurements do not establish physical-phone performance, GPU frame time or public-host latency. All final benchmark samples had no page errors and the benchmark browser shut down cleanly.

Validation passed **473 flight/HTTP Python tests, 14 transit/i18n Python tests and 114 JavaScript tests**. The complete presentation browser run and ten existing browser regressions passed: Europe, Africa, Singapore, Gulf hubs, Australia international, Pacific, airport focus, bilingual calendar/fullscreen/mobile, transit departures and Melbourne map/vehicles. Final runs exited cleanly. One earlier presentation retry completed every assertion but stalled inside Chrome shutdown; it was interrupted and is recorded separately in `browser-optimized.log`, not counted as a clean pass. An overlapping experimental timing run was interrupted and excluded from the final samples. Two stale USD-only browser assertions were corrected for already-existing mixed-currency Singapore/Gulf metadata; their reruns passed without changing any fares.

All 40 views' records, fares, airport objects, paths and capture metadata matched the pre-change adapter; all 292 reference hashes were preserved and `data/` has no diff. No flight searches or preparation runs were performed. The updated before/after selector, 13 screenshot pairs, metrics, source hashes, regression logs and raw timing samples are under ignored `.cache/flight-display-consistency/`. Audit-only generated HTTP responses are disposable; screenshots and measurements are retained.

## World · Flights (29 October 2026)

World's prepared union has 53,591 unique flights overlapping 2 November UTC, 16,823 directional routes and 1,476 airports with returned flights. It uses all 40 validated member views and preserves their replacements/exclusions. The derived snapshot records 44 input-file hashes. See `WORLD_FLIGHTS_NOTES.md` for identity, quotes, alias resolution and adjacent-day coverage limits.

HTTP format advances **27 → 28**. Endpoint-only `great_circle_v1` descriptors remove the need to transfer every route's coordinate/distance arrays. The ordinary service and airport fields remain. The World response is **5,095,519 bytes / 4.86 MiB gzip**, within the 5 MiB target, versus approximately 21 MiB with every path transferred. Level 9 gzip is used only for World; existing views retain level 3, ETags, immutable response caching and download-only query-metadata exclusions. Uncached World requests read only the prepared file; cache hits serve the compressed response. Neither rebuilds the 40 members.

World renders at 250 ms below zoom 4.5 and 60 ms nearby, sending MapLibre only markers inside the viewport plus 12 px. Counts retain all matching identities. Dot rendering avoids heading/artwork work, and the canonical union permits counting known unique identities without allocating another ID set each paint. The World interpolation path skips transit stop/dwell calculations while retaining the same arc positions, exact scheduled endpoints and inclusive arrival instant. Airport/aircraft artwork is lazy in World; code labels appear from zoom 4.5, and hollow airport markers retain wide-view selection. Reusing small canvases avoids thousands of context allocations. The World airport picker searches exact code/name pairs directly rather than constructing every route label.

Measurements used local Chrome with software WebGL, one Gunicorn worker/four threads, a warmed dedicated HTTP response cache and three fresh contexts per condition. Desktop was 1440 × 1000; the throttled condition used 390 × 844 and 4× CPU. The opening timer starts at the homepage shortcut and ends after the first map positions, opening frame and two animation frames. Thus it includes initializing a fresh replay WebGL map, decoding the response and initial lazy arcs. No other test browser or preparation/hash audit ran during the timing samples.

Peak paint samples hold the clock at **15:00 UTC / 7,584 active flights**, measuring five seconds at the global cadence. This separates worst-density drawing from changes in active counts. Paint duration measures the main-thread JavaScript call, not total GPU raster time. Each reported paint p95 is the median of three runs' p95 values. Board/filter timers include synchronization and two animation frames. Heathrow opens from the unfiltered World map after resetting to 10:00; the filter sample then chooses BA within that airport selection.

| Median of 3 | Desktop | 390 × 844, 4× CPU | Target |
| --- | ---: | ---: | --- |
| First map, warm HTTP cache | **8.48 s** | **12.01 s** | ≤5 / ≤15 s |
| Heathrow board | **1.74 s** | **1.67 s** | ≤1 / ≤3 s |
| Airline filter | **0.28 s** | **0.50 s** | ≤1 / ≤3 s |
| Peak paint p95 | **26.1 ms** | **140.7 ms** | ≤40 / ≤150 ms |

The download, throttled opening, filter, throttled board and both peak-paint targets pass in these samples. **Desktop first-map readiness and first Heathrow board opening miss their targets.** They remain release limitations, not hidden passes. Profiles show significant fresh WebGL/shader work as well as initial response decoding; board samples include the first route-line rendering. These observations do not establish hosted latency or performance on a physical phone. No flight identities were dropped, aggregated or clustered to improve the timings.

The initial implementation measured about 14.3 seconds to first map, 2.26 seconds for the board and 44.2 ms paint p95 on desktop. Those exploratory samples were single runs, not paired statistical baselines. Profiling led to lazy artwork, canvas reuse, simpler World interpolation and count handling; the final table uses the uninstrumented implementation except for a paint-duration wrapper. An unfinished early benchmark was intentionally interrupted before final samples and excluded. Final benchmark samples had no page errors and Chrome shut down cleanly.

Validation results are recorded below after the complete regression run. Screenshots, raw measurements, CPU profiles and logs remain under ignored `.cache/world-flights/`; audit-only HTTP responses are disposable. Existing views and all source files are checked separately against the completed display-consistency baseline.

Final validation passed **495 relevant Python tests, 122 JavaScript tests and 12 browser regressions**: World, shared flight presentation, airport focus, Europe, Africa, Singapore, Gulf hubs, Australia international, Pacific, bilingual UI, transit departures and Melbourne map/vehicles. Every final browser regression exited normally; there were no assertion failures or browser shutdown failures in that run. The final World pass includes nearby lazy plane/airport artwork, nearest picking, the selected 22 px journey, Pacific viewport transfer, scope/country/brand filtering, local Heathrow/Vancouver/Sydney boards, destinations/fullscreen previews, multi-currency quotes, frequency totals, palettes, source evidence, themes and mobile.

The union rebuild matches the committed gzip byte for byte and reads each of the 44 source archives once. HTTP tests verify the 5 MiB budget, exact service identities/fares/times/airports, descriptors, gzip/ETag/cache behaviour and invalid-date rejection. JavaScript tests compare lazy 64-segment arcs with the Python algorithm across long-haul, polar, dateline and coincident endpoints, and compare the World interpolation fast path with legacy positions at departure, arrival and intermediate times. Synthetic tests cover quote selection, unknown/conflicting aircraft, explicit airport aliases and unexpected conflicts.

A separate preservation audit compared every field of all **40 existing replay payloads** with the completed display-consistency adapter and verified **all 292 original reference SHA-256 hashes**. They match exactly. The only `data/` addition is the derived World snapshot. The audit-only HTTP response directory is removed after validation; screenshots, timing evidence and logs are retained. PR creation, merging and deployment remain separate requests.
