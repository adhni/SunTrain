# Consistent flight presentation · 29 October 2026

The 40 flight views share one presentation policy. Existing flight records, fares, airport identities, paths, capture dates and collection policies are unchanged.

- At zooms below 4.5, each moving flight is a coloured dot with a 2.2 px radius and 0.8 px outline. At and above 4.5, its plane canvas stays at 16 CSS px. A selected active flight has a 22 px plane, ring and journey path at every zoom. Nearest-flight picking uses a 12 px radius; a direct airport-label hit takes priority. Frequency mode hides all moving-flight representations and the selected journey path.
- `flight_view_kind` in city settings and replay payloads classifies seven hub views, seven regions, two networks and 24 countries. Countries/regions open on configured bounds; hubs/networks use captured route endpoints and the shared dateline-aware bounds calculation. The retained opening frame is also Reset view's target. Fit flights frames matching flights. Filters and board opening preserve camera and clock; explicit following remains available.
- Every flight view starts with All captured (`both`) and no airline or airport filter. The clock is 10:00 on the selected date in the declared timezone, clamped to the existing replay window. Airport boards retain their local clocks and event ownership.
- The two moving-flight count lines distinguish unique marker centres in the viewport, all active matching identities, matching captures and total captures. Projection uses the nearest longitude world copy, and counts update on playback, filtering and map movement. The key identifies moving flights and hollow airports and keeps partial coverage visible.
- When matching flights exist but none is on the map, Next departure seeks a captured future departure whose origin is inside the viewport, pausing playback. Otherwise the hint points to the timeline or Fit flights. English/Indonesian translations preserve state and format numbers once.
- Plane artwork is cached by carrier and actual colour, preserving different Europe and Singapore palettes for the same carrier. HTTP format **27** invalidates old presentation responses while preserving gzip, ETags, immutable caching, endpoints and the previous exclusion of download-only `schedule.queries` / `schedule.wizzair_inventory`.

## Actual opening comparisons

All screenshots use the original 1440 × 1000 browser viewport. Different opening times and default scopes are intentional, so the before/after counts do not measure changes in underlying traffic.

| View | Updated opening | Matching captures | On map / active |
| --- | --- | ---: | ---: |
| Europe | Regional frame, dots, 10:00 UTC | 13,073 | 1,835 / 1,846 |
| Bahrain | Captured endpoint frame, dots, 10:00 Bahrain | 173 | 13 / 13 |
| Laos | Country frame, compact planes, 10:00 ICT | 32 | 1 / 1 |
| Taiwan | Country frame, compact planes, 10:00 CST | 973 | 52 / 179 |
| Singapore | Captured endpoint frame; Reset restores it | 1,101 | 212 / 213 |
| Pacific Islands | Regional frame, 10:00 UTC on 2 November | 877 | 20 / 21 |

Europe remains dense because every scheduled flight keeps its own identity; no clustering or aggregation was introduced. Compact country views no longer enlarge planes. Laos's explicit Domestic filter has no active flight at 10:00; Next departure correctly seeks LK212 at **12:15 ICT**, followed by the captured return LK213 at 13:20. No timing was invented.

The before/after selector, all 13 original comparison cases, screenshots and machine-readable metrics are under ignored `.cache/flight-display-consistency/comparison.html` and `maps.json`. The original audit remains in `.cache/flight-display-audit/`. Separate future collection gaps are in [FLIGHT_COVERAGE_GAPS.md](FLIGHT_COVERAGE_GAPS.md).

## Validation

- **473 Python flight/HTTP tests**, **14 transit/i18n Python tests** and **114 JavaScript tests** passed. These cover every view's classification/default, local opening dates (including Bahrain, Pacific and historical Australia), cache invalidation/projection, world wrapping, unique IDs, nearest picking, next-departure timestamps and palette keys.
- The new Chrome presentation regression passed marker checks below/at/above 4.5, selected planes, dot/plane picking, direct airport labels, station visibility, frequency switching, filter/board camera stability, distinct Reset/Fit targets, Europe → Singapore → Europe palettes, Laos empty-state actions, bilingual counters/state, five themes and mobile/fullscreen keyboard behavior.
- Existing Europe (30 airport boards), Africa, Singapore, Gulf hubs, Australia international, Pacific, real airport selection, bilingual, station-departure and Melbourne map browser regressions passed. Singapore/Gulf fare assertions were updated to accept the existing mixed-currency context while still checking captured USD fares; no fare data changed.
- Comparing all 40 views against the pre-change flight adapter found exact preservation of records, fares, airport objects, paths and capture metadata. Presentation settings and the opening timestamp are the intended differences. All **292 reference-file SHA-256 hashes** matched; `data/` has no diff. Full source query evidence remains in the references.

Responsiveness measurements and final browser outcomes are recorded in [PERFORMANCE_NOTES.md](PERFORMANCE_NOTES.md). Browser assertions and shutdown outcomes are recorded separately in ignored logs; assertion completion alone is not counted as a clean process exit.
