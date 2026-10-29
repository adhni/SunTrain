# Targeted international follow-up

This pass extends **World · Flights** for **2 November 2026 UTC**, starting from
55,599 flights. It uses a separate **300-search** budget: 150 European airline
candidates, 100 gateway connections and 50 Asian/Gulf candidates. It does not
reset or extend the first campaign's completed 1,000-search journal. The original
40 views, domestic captures, timeline and rendering remain unchanged.

## Selection and collection

Candidates come only from the first campaign's 4,608 unattempted route/date
candidates, with their published route-map and reviewed manifest evidence. No
airport-pair matrix or additional dates are generated. Already captured queries
and all previous attempts, including interrupted requests, are excluded.

The ranking favours dated captures in either direction, then missing directions,
reverse-direction frequency and published map corroboration. **279 of the 300**
selected queries have dated same-day evidence in at least one direction. Reverse
captures help prioritise a query; they never establish a return flight's schedule.
The remaining 21 candidates have route-discovery evidence only.

Three 100-search checkpoints mix the streams in proportions 50/33/17,
50/34/16 and 50/33/17. Each checkpoint is reviewed before the next collection.
Two workers collect exact-IATA, origin-local 2 November, nonstop all-airline
results, with verified USD fares where returned. Failed or interrupted requests
are durably charged before navigation; access challenges stop the collection.
Empty results mean **not returned**, never no service.

The cumulative supplement retains the previous cache recovery and first-pass
captures. Query ownership, exact-identity deduplication, independent official
timetable evidence, aircraft alternatives and distinct compatible fare quotes
use the existing validated preparation. Newly collected quotes use the cheapest
returned compatible USD fare. No currency conversion or codeshare inference is
introduced.

## Reproduction

```sh
export PYTHONPATH=.cache/browser-tools:.
export PYTHONPYCACHEPREFIX=.cache/pycache
.venv/bin/python scripts/prepare_international_followup.py manifest
.venv/bin/python scripts/prepare_international_followup.py collect  # checkpoint 1
.venv/bin/python scripts/prepare_international_followup.py collect  # checkpoint 2, after review
.venv/bin/python scripts/prepare_international_followup.py collect  # checkpoint 3, after review
.venv/bin/python scripts/prepare_international_followup.py finalize # offline, no searches
```

The follow-up source ledger is
`data/sources/world_international_followup.json.gz`. It pins the unchanged first
campaign ledger, the baseline World/input hashes, selected evidence and the
complete follow-up attempt journal and capture hashes. Raw results live under
ignored `.cache/google-flights-world-international-usd-followup/`; scorecards,
frozen comparison inputs and validation artifacts live under ignored
`.cache/international-followup/`. Missing local journals cannot reset the
published budget. Completed collection performs zero further searches.

The original campaign ledger and its 1,000 attempts remain unchanged. Use the
follow-up preparation command for this release's cumulative supplement rather
than re-finalizing the closed first campaign. Raw caches are required to
re-prepare the supplement. Normal World preparation remains offline using the
committed supplement, without requiring raw caches or rebuilding on HTTP requests:

```sh
PYTHONPATH=. .venv/bin/python scripts/prepare_world_flights.py
```

## Coverage limitations

This is still a partial passenger-flight collection. Discovery maps can include
seasonal routes; dated results can omit airlines, sold-out services and individual
frequencies. No domestic expansion, new searches for adjacent local dates, live
tracking, connecting itineraries or automatic refresh are included. Previously
documented airport-identity and source gaps remain; failure to capture Iran or
Angola is not proof that flights do not operate there.

The previous throttled peak-playback performance limitation remains documented
in `PERFORMANCE_NOTES.md`; this collection does not change rendering or claim a
performance improvement.

## Results

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| All overlapping flights | 55,599 | 55,988 | +389 |
| International overlapping flights | 27,701 | 28,090 | +389 |
| International departures inside UTC day | 25,850 | 26,231 | +381 |
| International directional routes | 11,724 | 11,881 | +157 |
| Airports with international captures | 826 | 827 | +1 |
| International flights with a primary fare | 23,419 | 23,914 | +495 |

All 389 additions are distinct international flight identities; no prior identities were removed. Domestic records remain **27,898**, byte-for-byte equivalent at record level. The pass adds no new country/territory endpoint; **BJA (Béjaïa, Algeria)** now has captured international flights as well as its existing domestic coverage. No airport is newly introduced to the overall World collection.

**300 attempts / 300 completed captures:** 260 nonempty and 40 empty queries; zero failed, interrupted or rejected queries, and no access challenges. They returned 529 dated raw records, including 508 verified USD fares. UTC overlap and existing identities reduce this to 389 additions. The 495-record increase in primary fare coverage comprises **368 newly added flights with fares** and **127 existing flights newly receiving a fare**. Additional quotes on already priced identities remain preserved as well.

| Checkpoint | Net flights added so far | New directional routes so far | Nonempty queries so far |
| --- | ---: | ---: | ---: |
| 100 searches | 240 | 89 | 91 |
| 200 searches | 344 | 143 | 183 |
| 300 searches | 389 | 157 | 260 |

Final additions by stream: **207 Europe / 84 gateway connections / 98 Asia-Gulf**. The remaining original candidate queue contains 4,308 entries; it is evidence to review, not proof of 4,308 active missing flights or routes.

Largest airline additions: Vueling (43), Transavia (42), Air Serbia (42), Eurowings (32), easyJet (27), SunExpress (11), Korean Air (11), United (10), KLM (9), ANA (8).

Examples retained inside the UTC window: ORY → BCN (11), LIN → AMS (10), FCO → ORY (9), LIN → CDG (9), LIN → FRA (8), LAX → HND (7), and JFK → ICN (3). These are captured departure records, including multiple airlines where returned; they do not establish complete route frequencies.

The source snapshot is **3,111,292 bytes gzip**. This is the repository snapshot, distinct from the larger HTTP replay download. The complete 389-record addition list is under ignored `.cache/international-followup/added-flights.csv`.

## Validation

- **56 Python tests passed**, covering World regeneration, exact identities,
  source hashes, UTC boundaries, fares, aircraft alternatives, HTTP caching/date
  rejection, parser behaviour, bilingual copy, independent campaign budgets,
  frozen baselines, interrupted attempts and completed-campaign resumption.
- **49 JavaScript tests passed** for flight rendering, presentation, frequency
  mode and World geometry/viewport behaviour.
- All **40 existing flight-view payloads** and **292 original reference-file
  hashes** passed preservation checks. Existing domestic World records are
  identical. Every compatible pre-existing quote and specified aircraft option
  survives on each retained identity; no baseline identity was removed.
- World preparation reproduced the final snapshot byte-for-byte, reading each
  of its 45 prepared inputs once. The supplemental source-manifest hash, its
  World input hash and the first campaign's unchanged ledger/journal all match.
- World browser assertions passed for the union and peak playback, Pacific
  wrapping, picking, country/airline/scope filters, local airport boards,
  destinations/fullscreen/back, fares, frequency totals, Reset/Fit, World →
  Europe → Singapore transitions, English/Indonesian, themes and mobile layout.
  Browser shutdown completed cleanly; no assertion or shutdown failure remains.
- Resuming the completed follow-up performed **zero further searches**.

The running local preview served **55,988 services** using HTTP format **28**.
Its actual gzip response is **5,479,477 bytes / 5.23 MiB**, compared with the
first pass's 5,436,083 bytes / 5.18 MiB (+0.8%). The HTTP representation retains
endpoint-only geometry; the detailed campaign ledger is not transferred.
This is a download-size check, not a repeat of the earlier responsiveness or
throttled-playback benchmark. Their documented performance limitations remain.

Logs, scorecards, screenshots, raw validation comparisons and the HTTP-size
measurement are under ignored `.cache/international-followup/`. No PR, merge or
deployment is included in this pass.
