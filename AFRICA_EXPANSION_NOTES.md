# Africa: cached recovery and deferred African routes

Expands the existing Africa view using only the two selected passes: compatible newer captures, then the **658 published directions already deferred by the starter's 30-airport boundary**. No new gateway discovery, worldwide route sweep, additional dates, new airline source adapter or shared International-network expansion.

## Frozen scope and source provenance

`data/sources/africa_flights_starter_routes.json.gz` freezes the previous manifest, original source evidence and canonical fingerprints of the 2,468 original records. It also fingerprints the 96 records recovered offline. The file's SHA-256 is pinned in `scripts/expand_africa_routes.py`; rebuilding checks it and the original pinned airport/timezone catalogues.

The ordinary `prepare_africa_routes.py` delegates to the bounded expansion builder and requires this frozen input. New collection is exactly the starter's existing collection directions plus its reviewed deferred directions. Reuse-only routes never turn into fresh searches if their captures are missing. Additional worldwide source manifests provide identity-matched airport clocks, not additional route candidates.

The 658 directions consist of **320 domestic and 338 cross-border African candidates**, each connected to at least one original starter airport. All resolve to distinct active airport identities with explicit IANA zones. They are seasonal published candidates, not proof of dated operation. Exact airports stay separate, including JNB/HLA, CAI/SPX and the DRC's separate airport zones. Existing source gaps remain documented; this expansion does not declare nationwide completeness.

The current Europe archive preserves the official Ryanair source records used by Africa. Its updated archive hash is deliberately pinned in the expanded manifest, replacing the outdated pre-Europe-expansion hash. The frozen starter retains the historical hash for provenance; preparation fails if the newly pinned archive changes unexpectedly.

## Pass 1: no flight searches

**96 flights recovered offline**, taking the interim snapshot from 2,468 to **2,564 flights**, while preserving all original flight fields exactly. Recovery adds **70 positive directions** outside the starter manifest and refreshes one previously empty query, **ACC–FCO**, with a compatible dated ITA capture. The previous empty result is retained verbatim under `previous_empty_capture`, alongside the new source path and byte hash. A populated existing query cannot be replaced through this mechanism.

Quotes retain their original currency, amount, capture timestamp and one-adult/economy/one-way context. Sources are selected as intact compatible query captures, rather than combining conflicting schedules. Newer eight-hour empty captures cannot establish a missing long-haul service. Original external capture files are never modified.

## Pass 2: bounded collection

After reuse, **658 missing directions** remain. Search each once for **2 November 2026 in the origin's local time**, all returned airlines, at most two concurrent searches. New fares request **USD** and use the cheapest verified quote for the exact flight. No query is repeated solely to change a reused currency or obtain a missing fare. Access challenges stop collection and preserve completed captures.

Reuse the existing UTC timeline spanning origin-local departure days and overnight arrivals, airport-local boards, country/airline/airport filters, Domestic/International/Both, Destinations, fullscreen boards, frequency lines, themes and English/Indonesian copy. The map initially frames Africa. Unreturned airports stay selectable with capture-gap boards; empty means not returned, never no service.

## Rebuilding

```bash
# Rebuild from frozen route evidence and compatible local captures; no searches.
.venv/bin/python scripts/prepare_africa_routes.py
# Seed/recover reviewed captures and inspect the remaining one-date budget.
.venv/bin/python scripts/prepare_africa_flights.py --seed --dry-run
# Collect only missing selected directions.
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_africa_flights.py
# Rebuild offline and enforce the original/recovered record fingerprints.
.venv/bin/python scripts/prepare_africa_flights.py --prepare-only
```

Caches remain `.cache/google-flights-africa-usd-v1/`, with new captures under `new-usd/`. The committed replay remains `data/reference/africa_flights/2026-11-02.json.gz`; runtime requires no raw collection caches. Deterministic preparation validates source identities, dates, durations, quotes and preservation fingerprints before atomic replacement. Audit logs/screenshots are ignored locally under `.cache/africa-expansion-audit/`.

Resuming collection publishes only the pending queries from that invocation, including failure diagnostics. Old files left in `new-usd/` cannot overwrite a populated, reviewed reused capture with a stale empty result. Record-preservation guards run before publishing the prepared bundle.

## Actual coverage and validation

Final snapshot: **3,693 flights**, including **96 recovered offline** and **1,129 from the bounded collection**, across **188 returned African airports in 52 country/territory codes**. There are 335 returned airports worldwide and 137 source carrier codes. All **2,468 original records and 96 recovered records pass their frozen canonical fingerprints**.

| Bucket | Flights | Directions | Priced flights |
| --- | ---: | ---: | ---: |
| domestic | 1253 | 265 | 796 |
| intra african | 586 | 287 | 432 |
| intercontinental | 1854 | 1039 | 1704 |

| African region | Returned African airports | Flights touching region |
| --- | ---: | ---: |
| north | 56 | 1726 |
| west | 38 | 507 |
| central | 9 | 50 |
| east | 60 | 1001 |
| south | 25 | 680 |

Regional rows overlap for cross-region flights and must not be summed as unique flights. The starter’s country-group definitions remain unchanged.

All **2,749/2,749** directional source captures are present: **2,655 Google queries**, plus **94 archive-only directions**. This release ran **658 new single-date searches**; reused/previous captures were not re-searched. Remaining failed queries: **0**; uncollected: **0**; rejected source rows: **0**.

Fare counts: **EUR: 513**, **MYR: 1**, **USD: 2,418**, **unpriced: 761**. Missing fares stay unavailable. Empty or rejected results do not establish no service. The 12 original map gaps and remaining unresolved candidate airports are still documented in the manifest. HMB, KRT and MRA are resolved through identity-matched existing airport catalogues for compatible cached captures; they do not create new search sweeps.

Prepared bundle: **359,198 bytes**, SHA-256 `bed6dfe70309b0121669969b9ab12da413245115ed87ce3a60f6f806d632d6f9`. Offline reproduction is byte-identical.

Validation passed: **262 Python regressions**, **106 JavaScript tests**, and the complete browser suite covering original and expanded airport boards, exact city airports, country/carrier/scope filters, local clocks, original currencies, fullscreen/back, themes, Indonesian, mobile, frequency totals and existing regional/transit views. A historical Türkiye regression now compares its original European carrier cohort explicitly; its reference archive is unchanged.
