# Missing directions and UTC-boundary flights

**Later expansion:** current World counts and the active international preparation command are in [INTERNATIONAL_LONGHAUL_NOTES.md](INTERNATIONAL_LONGHAUL_NOTES.md). Counts below describe this earlier pass.

This campaign extends **World · Flights** from its 55,988-flight snapshot for
**2 November 2026 UTC**. It has an independent **100-search** cap: **49 missing
Asian/Gulf return-direction candidates and 51 adjacent-local-date candidates**.
It preserves the previous 1,000- and 300-attempt ledgers. Collection is reviewed
after 50 attempts; no additional homepage view, replay date or automatic refresh
is added.

## Search selection

Candidates come from the prior campaign's remaining queue and retain the
published route evidence. Existing compatible caches and every charged prior
attempt, including failures/interruption, are excluded. No all-airport pair
matrix or whole additional day is collected.

The 49 primary-date directions have a captured reverse direction and no captured
forward route. The 51 boundary queries use observed flight timings shifted by
one **airport-local calendar day** to identify possible overlap with the UTC
window. They are ranked by potentially missing identities and number of timing
clues. Those shifted timestamps are **search evidence only**: they never enter
the flight records or establish daily service. Actual dated Google results alone
supply departures, arrivals, flight numbers and fares.

The selection contains **49 queries for 1 November, 49 for 2 November and two
for 3 November**, all origin-local dates. Checkpoint mixes are 25 reverse/25
boundary, then 24 reverse/26 boundary. Two workers capture exact-airport nonstop
all-airline results, using verified USD fare context and the cheapest returned
compatible quote. All existing compatible currencies/quotes remain preserved
without conversion.

World still includes only flights departing before the UTC window ends and
arriving at or after its start. Airport boards retain only departure/arrival
events inside the half-open UTC day, displayed in airport-local time. Replay
opens paused at 10:00 UTC; existing country/region views remain unchanged.

## Airport identity review: zero flight searches

- **JUB:** the pinned active airport uses **HJJJ**, while the old OpenFlights
  timezone entry uses HSSJ. The [South Sudan CAA location-indicator publication](https://sscaa.gov.ss/media/aip/master/aip.pdf)
  identifies Juba as HJJJ. The resolver now explicitly associates the active
  pinned identity with `Africa/Juba`; it does not replace coordinates or collect
  another schedule. The timezone identifier was already present in the pinned
  legacy airport data.
- **PBI/DJT:** the pinned active catalogue already uses **DJT/KDJT**. The
  [airport's dated notice](https://flydjt.org/articles/post/president-donald-j-trump-international-airport-name-change-takes-effect/)
  specifies that PBI changes to DJT after 18 August 2026. PBI remains excluded
  for the November replay; it is never silently mapped into a different query
  or captured identity. DJT now resolves independently with `America/New_York`.
  Old PBI route candidates require separately reviewed exact-DJT queries in a
  later pass. No new JUB or DJT flight query is inserted into this 100-search cap.
- Retired Cambodian PNH remains excluded. Other unresolved/excluded airport
  candidates remain documented; catalogue resolution is not proof of service.

The original historical source ledgers remain byte-identical, including their
then-unresolved airport lists. The latest ledger records the reviewed resolution
and retains discovery gaps separately from search results.

## Reproduction and audit

```sh
export PYTHONPATH=.cache/browser-tools:.
export PYTHONPYCACHEPREFIX=.cache/pycache
.venv/bin/python scripts/prepare_international_boundaries.py manifest
.venv/bin/python scripts/prepare_international_boundaries.py collect  # first 50
.venv/bin/python scripts/prepare_international_boundaries.py collect  # after review
.venv/bin/python scripts/prepare_international_boundaries.py finalize # offline
```

The source ledger is `data/sources/world_international_boundaries.json.gz`.
It pins both parent ledgers, the frozen baseline hashes, exact queries, observed
timing evidence, airport resolutions, attempt journal and captured-file hashes.
Raw queries are under ignored
`.cache/google-flights-world-international-usd-boundaries/`; scorecards,
screenshots, comparisons and logs are under ignored
`.cache/international-boundaries/`.

Each navigation is charged durably before it starts. Missing/stale local
journals cannot reset a published campaign, completed resumption makes zero
further searches, and an access challenge stops collection. A closed campaign
cannot rewrite a newer campaign's ledger or prepared provenance. Use the latest
campaign's preparation command for the cumulative supplement. Rebuilding that
supplement requires the recorded raw caches. Normal World regeneration remains
offline from the committed prepared inputs:

```sh
PYTHONPATH=. .venv/bin/python scripts/prepare_world_flights.py
```

Coverage remains partial. Empty means **not returned**, not no service. Only 51
specific adjacent-date directions were selected; this does not close all UTC
midnight gaps or establish complete frequencies. There is no new domestic
collection, live tracking, currency conversion, connecting itinerary, PR,
merge or deployment in this pass.

## Results

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| All overlapping flights | 55,988 | 56,231 | +243 |
| International overlapping flights | 28,090 | 28,333 | +243 |
| International departures inside UTC day | 26,231 | 26,317 | +86 |
| International directional routes | 11,881 | 11,916 | +35 |
| Airports with international captures | 827 | 827 | +0 |
| International flights with a primary fare | 23,914 | 24,143 | +229 |

**243 exact identities added; zero removed.** All additions are international; domestic records remain **27,898** and identical. No airport or country/territory endpoint is newly introduced. There were no extra cache-recovery additions from airport resolution.

**100 attempts / 100 completed captures:** 88 nonempty and 12 empty queries; zero failed, interrupted or rejected queries, and no access challenge. The captures contain **395 raw dated records**, including **376 verified USD fares**. Only the 243 new overlapping identities enter the World replay; other returned records lie outside its UTC window or already match existing identities.

The primary-fare increase comprises **229 newly added flights with fares** and **0 existing flights newly receiving a fare**. All compatible old quotes and specified aircraft alternatives survive on retained identities.

| Checkpoint | Net flights added so far | New routes so far | Nonempty queries so far |
| --- | ---: | ---: | ---: |
| 50 searches | 128 | 18 | 44 |
| 100 searches | 243 | 35 | 88 |

Final contributions: **36 missing-direction additions and 207 UTC-boundary additions**. Of the 243 additions, **157 were already airborne when the UTC day began**, while 86 depart inside it. Accordingly, frequency-mode departure totals increase by 86 rather than 243.

Examples inside the UTC window include JFK → CDG (9), LGA → YYZ (8), LHR → JFK (7), JFK → LHR (6), and HNL → HND (6). The LHR/JFK examples depart on local 1 November and overlap 2 November UTC. These are captured records, not completeness claims.

Largest airline additions: LATAM (28), British Airways (22), American (16), Air Canada (14), Iberia (12), Virgin Atlantic (12), Delta (12), COPA (11), Avianca (11), Air France (10).

The reviewed queue has **4,208** original candidates left, not 4,208 confirmed active missing services. The complete 243-record addition list is under ignored `.cache/international-boundaries/added-flights.csv`.

## Validation

- **70 Python tests passed**, including deterministic World regeneration, old/new campaign budgets and provenance transitions, UTC boundaries, Canadian dated offsets, exact identity/fare/aircraft preservation, parser validation, HTTP cache/304/date rejection and bilingual copy.
- **49 JavaScript tests passed** for flight rendering, lazy geometry, viewport picking/counts, presentation and frequency behaviour.
- All **292 original reference-file hashes** remain unchanged. The existing 40 flight views are untouched. Every domestic World record is identical; every prior compatible fare quote and known aircraft option is retained, and no baseline identity is removed.
- World preparation reproduces the final snapshot byte-for-byte, with each of its 45 prepared inputs read once. Both historical campaign ledgers and their 1,000/300 local attempt journals are unchanged. The current source-manifest and World input hashes match.
- Completed campaign resumption performs **zero further searches**.
- World browser assertions passed for global/peak playback, dateline clipping and picking, country/scope/airline filters, local airport boards, destinations/fullscreen/back, fares, frequency totals, Reset/Fit, World → Europe → Singapore transitions, English/Indonesian, themes and mobile. Browser shutdown completed cleanly. The first collection batch logged background Chrome profile cleanup and then returned normally; no search or browser assertion/shutdown failure remains.

The local preview serves **56,231 services** using HTTP format **28**, with **5,509,842 bytes / 5.25 MiB gzip**. The repository snapshot is 3,129,360 bytes gzip. Endpoint-only geometry and the omission of download-only query evidence remain intact. This measures download size, not new first-map or throttled playback performance; earlier documented performance limitations remain.
