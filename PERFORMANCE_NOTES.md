# Replay performance and memory

All existing historical date ranges, routes, passenger records and geometry are retained. Melbourne trains keep FY2023–24; trams/buses keep five weeks. This change does not create daily files for every city or change hosting plans.

## Representation and rebuilding

Every committed schedule reference uses `shared-stops-flat-times-v1`. A pattern holds a shared stop-sequence ID and a flat relative timing vector. Each shared sequence holds station IDs and geometry leg IDs. Timings remain distinct when traffic profiles or dwell times differ; loops retain every stop occurrence. Existing pattern/trip/path IDs are unchanged. Older unpacked references remain readable for environment overrides.

All seven common preparation modules now call `scripts.compact_transit.save_reference()`. Toronto, DC/BART and London reuse the common rail preparer. Boston and London optional buses already use this encoding. Existing preparation commands still rebuild their respective files; source archives and licences are unchanged. Saving is atomic and deterministic, and the shared writer is idempotent. Do not expand a schedule into separate stop arrays per trip in the application.

Runtime timing vectors use read-only NumPy buffers (NumPy is already required by pandas and is now explicitly pinned to the tested version). Only their Python representation changes: `orjson` serializes them as the same ordinary JSON arrays used by the browser. Coordinates, timestamps and passenger values are not rounded or inferred.

## Server memory and concurrency

The versioned gzip HTTP cache is the persistent reusable representation within a running deployment. Parsed references and prepared-day caches are cleared before and after each uncached build. Garbage collection releases obsolete containers; a successful or failed build leaves no retained parsed schedules. A worker-wide generation lock prevents different dates/modes from building concurrently. A second request for the same version rechecks the compressed cache after waiting, so it does not rebuild the response.

Cache-hit downloads bypass generation entirely and remain available while an unrelated cold request builds. Open file descriptors preserve an in-flight response during cache eviction. The existing 256 MiB compressed cache limit, ETags, gzip negotiation and immutable versioned URLs remain. `FORMAT_VERSION` is now 3.

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
