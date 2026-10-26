# Europe flights — Ryanair expansion and easyJet starter

**Europe · Flights** is a regional view for **2 November 2026**, limited to **Ryanair and easyJet**, with verified source-carrier aliases.
Ryanair now searches its full published Europe-connected airport-pair catalogue;
easyJet retains its original broad starter. Other airlines can follow later.

It opens on **Both** and moving planes, with no airport selected. Domestic and
International use the countries of the actual endpoint airports, not airline
nationality or EU membership. Timeline: **UTC**. Airport boards retain their own
IANA zones and local dates. Brand/carrier, exact-airport and From country / To
country filters combine with departure/arrival boards, Destinations, fullscreen
pagination, frequency lines, themes and English/Indonesian labels.

International-network integration is deliberately a later phase, as proposed
in the existing Europe plan. Europe's domestic and cross-border records are
stored once in their own regional snapshot; the previous shared archive and
country snapshots are unchanged.

## Source discovery and pilot

Reviewed **26 October 2026 (Melbourne)**:

- [Ryanair's public booking-widget catalogue](https://www.ryanair.com/api/views/locate/3/aggregate/all/en)
  supplies exact `airport:` route entries and airport IANA zones. City/country
  entries are not airport pairs. One explicitly partner-labelled `MLA|Air Malta`
  entry is excluded. [Ryanair destinations](https://www.ryanair.com/gb/en/flights)
  and [timetable](https://www.ryanair.com/gb/en/lp/timetable) provide source context.
- [easyJet flight timetables](https://www.easyjet.com/en/flights-timetables)
  publishes exact-airport route links. All visible route facts were reviewed
  through the web tool, normalized and deduplicated into **2,564 directions**.
  The local HTML client returned Access Denied, so the recorded hash covers the
  normalized reviewed route facts, not a claimed raw HTML capture. No access
  challenge was bypassed, and no private/partner booking API was used.
- [Ryanair's carriage conditions](https://help.ryanair.com/hc/en-ie/articles/12890911974289-General-Terms-Conditions-of-Carriage)
  explicitly identify FR, RK, RR and AL. Its
  [group-airline directory](https://careers.ryanair.com/group-airlines/)
  identifies the corporate affiliates. A marketing FR flight does not imply a
  known wet-lease operator; source carrier/airline fields remain unchanged.
- easyJet aliases U2/EC/DS and EZY/EJU/EZS are supported by the official
  [Geneva airport airline directory](https://www.gva.ch/en/passengers/flights-and-destinations/airlines/easyJet),
  [EuroAirport flight search](https://www.euroairport.com/en/passengers-visitors/arrivals-departures/flights/flightsearch.html)
  and [Antalya airline allocation table](https://www.antalya-airport.aero/files/2025%20G%C3%BCncel%20Terminal%20Da%C4%9F%C4%B1l%C4%B1m%C4%B1_rev.1.pdf).
  Matching is by the reviewed carrier-code map, never an airline-name substring.

The 16-query Google pilot covered STN–DUB, BGY–CTA, STN–RAK, BFS–STN, LGW–BCN,
GVA–LGW, BSL–NCE and LTN–EDI, in both directions. It returned **68 target records**,
all with verified **EUR** quotes, using FR/RK/U2, plus **17 competitor records**
that are excluded from the replay. One-adult, economy, one-way fare context was
verified for all pilot queries. Affiliate codes are supported independently;
Google's U2 presentation does not prove a specific operating subsidiary.

The [public Ryanair STN–DUB November timetable](https://services-api.ryanair.com/timtbl/3/schedules/STN/DUB/years/2026/months/11)
returned ten November 2 flights; all ten numbers and departure/arrival clocks
matched the Google pilot exactly. Additional checks covered STN–RAK (RK codes),
TFS–STN (Canary time zone and longer flights), and BGY–CTA (domestic flights).
The full collection uses this public monthly timetable, not thousands of Google
searches. No independent dated easyJet timetable comparison is claimed: its
local public timetable request was denied. Route lists are discovery evidence;
only returned dated schedules create flights.

## Route selection and exact airports

`data/sources/europe_flights_discovery.json` retains the full normalized discovery
inventory, source URLs, hashes, airport zones and partner exclusion. Eligible
discovery contains **5,305 Ryanair directions** and **2,564 easyJet directions**,
with at least one endpoint in the explicit reviewed Europe membership set.
Wholly non-European pairs, including Moroccan domestic routes, are deferred.
External endpoints such as Morocco, Egypt and Cape Verde can appear when the
other endpoint is in the reviewed Europe set.

Ryanair's **5,305 directional entries represent 2,653 unique airport pairs**
across **224 airports**. Directions are requests, not separate undirected routes;
a few published entries lack a reverse counterpart. Every eligible published
direction is requested once for November 2026. A route not operating on November
2 does not create a replay flight.

easyJet retains the original deterministic selection of **80 undirected pairs /
160 published directions**. It covers published countries, reviewed major and
secondary airports, then round-robin additional links. The union manifest has
**5,443 directions and 245 candidate airports**. Source directions are never
invented by reversing another flight. Candidate coverage is not returned service
coverage.

`europe_flights_starter_routes.json` freezes the original Google selection:
306 union directions and 84 airports. `europe_flights_google_seed.json.gz`
retains that captured snapshot as a small reproducible source seed, including
all 180 easyJet records and original quotes. The larger
`europe_flights_routes.json` is the current timetable search manifest.

STN/LTN/LGW/SEN, CDG/ORY/BVA, FCO/CIA and MXP/LIN/BGY remain separate.
**BSL is physically in France** even when its commercial name refers to Basel;
country-scope classification follows the pinned airport country. GVA remains
Swiss. Spanish/Portuguese islands have explicit airport zones; TFS uses
Atlantic/Canary and FNC uses Atlantic/Madeira. Cyprus, Türkiye, Georgia and
non-EU European countries/territories have explicit reviewed membership rather
than membership inferred from EU status or map bounds.

Coordinates and exact IATA/ICAO identities use pinned OurAirports commit
`3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`.
Ryanair's per-airport IANA zones supplement explicit country and island mappings.
All 280 discovery airports resolve uniquely in the pinned catalogue. The app
loads only airports represented by returned flights.

## Capture, dates and fares

The timetable collector requests **5,305 airport-pair/month payloads** with
at most two concurrent HTTP requests. Each compressed cache envelope records the
URL, UTC capture timestamp, raw response hash, exact pair, collection context
and complete monthly payload. HTTP errors remain gaps. 401/403/429 or captcha
stops collection; successful captures are retained, with no challenge retry.

The source supplies local departure and arrival clocks, departure day, carrier
code and flight number. It does **not** supply prices, aircraft, arrival date or
a source duration. Arrival day is accepted only when there is exactly one UTC
interpretation lasting **one minute to eight hours**. Adjacent departure dates
November 1–3 retain flights overlapping the UTC replay window. DST folds and
nonexistent clocks cannot silently choose an instant. Records with ambiguous
or invalid timing are reported and excluded. The eight-hour ceiling is a
regional validation bound, not a claimed source duration.

Official schedules take precedence for matching identities. A seed quote and
source aircraft are retained only when the exact identity and both UTC times
match. Changed times remove the quote and are reported in `schedule_updates`.
New timetable records have no price and unspecified aircraft. A validated Google
seed flight not returned by the timetable remains a separately counted Google
fallback; an empty timetable does not prove cancellation. Repeated identical
identities deduplicate and conflicting official records are rejected.

The original Google collection used **744 exact origin/date queries** across
306 selected directions, including adjacent days. Original Google parsing
retains source-duration validation. Airport boards use half-open event windows;
arrivals at the opening midnight belong to that day.

Public Google searches request **EUR, one adult, economy, one-way**. Only exact
dated nonstop segment offers can become a fare. The cheapest positive captured
quote per exact flight/currency is retained; route minima, connecting totals,
optional baggage and seats are not substituted. Runtime formatting also retains
original USD/MYR quotes without conversion if explicit later reuse supplies
them. Current new captures request EUR. Missing/unverified quotes remain
**Price unavailable**; dated schedules remain useful without prices.

Raw airport-pair queries are unfiltered so multiple target brands sharing a pair
are captured once. Competitors are retained only in source diagnostics and
filtered out of prepared replay records. Coverage distinguishes no returned
direct flights, results containing only other carriers, returned target-brand
records, rejections, failed queries and unattempted queries. These statuses
must not be summarized as “no service”.

The collector uses at most **two concurrent searches**, cache/collection locks,
atomic writes and stop-on-challenge behaviour. The 16 pilot captures are reused.
Capture context includes region/version, currency, fare context, parser version,
duration ceiling and absence of a source airline filter. Incompatible contexts
are rejected rather than shared between differently scoped caches. Source page
hashes and timestamps are preserved. No live tracking, paid source or automatic
refresh is added.

## Rebuilding and local storage

```bash
# Reproduce the full Ryanair + easyJet starter manifest from pinned discovery.
.venv/bin/python scripts/prepare_europe_flight_airports.py
# Collect missing official monthly payloads, then publish the combined snapshot.
.venv/bin/python scripts/prepare_ryanair_flights.py --concurrency 2
# Rebuild without network from the source seed and timetable captures.
.venv/bin/python scripts/prepare_ryanair_flights.py --prepare-only
```

The original Google collector remains available for refreshing its seed:
`prepare_europe_flights.py --prepare-only` now writes
`data/sources/europe_flights_google_seed.json.gz`, never the expanded runtime
archive. Re-run the Ryanair preparation after changing that seed. Collecting
new Google captures additionally requires `PYTHONPATH=.cache/browser-tools`.
The committed seed permits timetable-only rebuilds without the old Google cache.

`data/reference/europe_flights/2026-11-02.json.gz` is the deterministic regional
snapshot, with fixed gzip mtime and atomic replacement. Its runtime override is
`SUNTRAIN_EUROPE_FLIGHTS_REFERENCE`; it is independent of every country snapshot
and `SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE`. Unsupported dates are rejected.
HTTP gzip revisions/ETags include the regional reference; a changed file
invalidates generated responses.

`.cache/ryanair-timetables-v1/` stores resumable compressed monthly source
captures; deleting it requires downloading the public timetables again to rebuild.
The committed combined snapshot still works without it. Failed requests have
`.error.json` diagnostics; a stop reason is recorded separately. Collection and
preparation share an exclusive cache lock. Output uses fixed gzip mtime, sorted
records and atomic replacement for byte-for-byte reproducibility.

`.cache/google-flights-europe-eur-v1/` holds the original 744 Google queries;
`.cache/google-flights-europe-pilot-eur-v1/` holds the pilot. These are needed only
to refresh the preserved Google seed. `.cache/europe-flights-audit/` and
`.cache/ryanair-expansion-audit/` contain optional comparisons, logs and browser
screenshots. `.cache/europe-http/` contains generated responses that regenerate.
The untracked Europe plan and unrelated country notes are preserved.

## Captured coverage and validation

All **5,305 / 5,305 official monthly requests** completed, with **zero failures,
unattempted requests, rejected timing records or changed seed schedules**.
Full catalogue query completion is not a claim that every Ryanair service was captured. Seasonal
routes, source omissions and rejected timings remain possible gaps. easyJet
continues to be a sample. Prices cover selected seed flights only.

Request counts are reported separately in `coverage_by_source`: official
**airport-pair/month** requests and Google **airport-pair/date** queries are
different units. Combined counters count source requests, never imply thousands
of dated Google searches. `coverage_by_brand` separates officially confirmed
Ryanair records from Google-only fallbacks. Empty results mean **not returned**,
never **no service**.

| Brand | Flight records | Airports returned | Directions returned | Priced records |
| --- | ---: | ---: | ---: | ---: |
| Ryanair group | 3,476 | 171 | 2,500 | 336 |
| easyJet (unchanged starter) | 180 | 39 | 83 | 180 |

The combined replay contains **3,656 overlapping records**, **3,606 departures
owned by the UTC day**, **182 airports**, **2,569 directions** and **40
countries/territories**. There are **525 domestic** and **3,131 international**
records; carriers are **FR: 3,396; RK: 80; U2: 180**. Fifty flights depart before
the UTC day and remain because of arrival overlap. Frequency lines count only
the 3,606 owned departures.

All **336 original Ryanair records** are confirmed by identical official flight
identities and UTC schedules; **zero Google-only fallbacks** are needed. All
**516 original EUR quotes** remain unchanged. The **3,140 new timetable records**
have no captured price. All **180 easyJet records** match the source seed exactly.
The original Google search collection remains 744/744 complete.

Of 5,305 monthly timetables, **1,983 returned no monthly days**. A total of
**2,805 directions returned no eligible replay-day flight**, including seasonal
or otherwise non-operating-on-this-day entries. These are source-result gaps,
not assertions of no service. Fifty-three of Ryanair's 224 candidate airports
returned no Ryanair flight overlapping the day:

AMM, BJV, BOJ, BVE, BZR, CCF, CDT, CHQ, CUF, DLE, DLM, EFL, EGC, FSC, GNB, HER, INI, JMK, JSI, JTR, KGS, KLU, KLX, LCA, LEI, LRH, LXS, MAH, MMX, NAP, NWI, NYO, OSI, PAD, PED, PIS, PUY, PVK, RDZ, RHO, RJK, SCN, SJJ, SPU, SZY, VAR, VIL, VOL, VST, VXO, XCR, ZAD, ZTH.

The union manifest has 63 candidate airports without an overlapping target-brand
flight (the Ryanair gaps above plus ADB, DJE, IOM, KTT, PRN, SCR, SEN, SKP, TBS
and TIV). Search completion does not make easyJet's selected sample complete,
and missing flights, other airlines and unsupported source times remain gaps.

The snapshot is **425,662 bytes** (about 416 KiB), SHA-256
`b7f4346d05631f5808e11b85ad21822b3e93929f0df73bb6bfc9e562ad3b16ff`.
The generated replay is about **10.1 MiB uncompressed / 2.8 MiB gzip**. The
expanded route manifest and snapshot reproduce byte for byte from pinned inputs
and cached captures. The shared international archive and previous country
reference files remain unchanged.

**Validation:** 266 Python tests and 100 JavaScript tests passed, including the
existing flight-country, international-network, Melbourne replay, HTTP cache
and translation regressions. New checks cover the full exact-airport manifest,
RK identity, overnight and previous-local-day arrivals, island zones, one-minute
flights, invalid clocks, DST ambiguity/nonexistent times, duplicate/conflicting
identities, exact quote reuse, changed-schedule quote removal, Google fallback,
missing/failed/empty requests, resumability and stop-on-access-challenge behaviour.

The expanded Europe browser suite passed with all 3,656 records: both brands,
RK filtering, domestic/international scopes, country pairs, STN/LGW/DUB/BGY/GVA/BSL
boards, departures/arrivals/Destinations, EUR previews, fullscreen/back, local
clocks, all themes, Indonesian and 390px mobile layout. The coverage display
separates monthly timetable requests from dated searches in both languages.
Frequency totals match the owned departures and filters reuse the cached day.
Desktop map and mobile board screenshots were visually checked. The existing
international-network browser suite also passed, including older country
views, filters, local boards, themes, mobile and fullscreen navigation.
