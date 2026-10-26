# Europe flights — Ryanair, easyJet and Wizz Air

**Europe · Flights** is a regional view for **2 November 2026**, covering **Ryanair, easyJet and Wizz Air**, with verified source-carrier aliases.
Ryanair and easyJet retain their full pinned Europe-connected candidate
catalogues. Wizz Air adds a secondary route-map inventory, validated through
dated Google Flights captures. The airline's direct route page returned a human
verification challenge; no claim of a complete official Wizz catalogue is made. Other airlines can follow later.

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

easyJet's **2,564 published directions / 1,282 unique airport pairs** cover
**164 candidate airports**. The complete union has **7,409 directions and 279
candidate airports**. Wholly non-European pairs remain excluded. The existing
easyJet selection no longer limits collection to 80 undirected pairs. Published
routes remain candidates: seasonal and unreturned services never create flights.

`europe_flights_starter_routes.json` freezes the original 306-direction Google
selection. `europe_flights_google_seed.json.gz` preserves its 516 captured
records and quotes as a small source seed. The current full manifest is
`europe_flights_routes.json`. Repeated origin/date captures are reused across
both brands instead of searched again.

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

## Wizz Air discovery and collection

Reviewed **27 October 2026**. Wizz Air's
[own route map](https://www.wizzair.com/en-gb/flights/wizz-route-map) returned a
405 AWS WAF human-verification page in a normal browser. Collection stopped on
that site without attempting a bypass. FlightConnections also denied the local
HTTP client, so its maps are not used as a bulk source.

[Seats Frog's public Wizz route map](https://www.seatsfrog.com/airlines/w6/route-map)
provides **1,329 candidate airport pairs / 2,658 search directions across 187
candidate airports**. This is a secondary inventory, including announced or
historical routes, not proof of service on November 2. The public page's point
and arc data resolve endpoints to exact IATA codes; pinned OurAirports data,
not the secondary map coordinates, supplies replay airport identities and
positions. `wizzair_routes_discovery.json` stores normalized pairs, source URL,
raw-page hash, review dates, access limitations and primary cross-checks. All
26 Wizz-group Barcelona pairs reviewed in Aena's directory are present in the
candidate inventory; that sample does not establish network completeness.

Aena's [Wizz Air](https://www.aena.es/en/josep-tarradellas-barcelona-el-prat/aerolineas/wizz-air.html),
[Malta](https://www.aena.es/en/josep-tarradellas-barcelona-el-prat/airlines/wizz-air-malta.html)
and [UK](https://www.aena.es/en/josep-tarradellas-barcelona-el-prat/airlines/wizz-air-uk.html)
directories verify **W6/WZZ, W4/WMT and W9/WUK**. These codes map to the Wizz Air
brand, while source flight numbers and airline labels remain unchanged. Other
historical subsidiaries are not inferred from airline names. Wizz uses magenta
(`#e660b6`), distinct from Ryanair blue and easyJet orange.

The dated pilot returned W62201/203/205 BUD–LTN and W43142/146 FCO–OTP with EUR
quotes. Existing cached W9 captures include W95724 AGP–LGW and W95386 ALC–LTN.
Wizz searches only **2 November in each departure airport's local time**:
**2,658 airport-pair/date queries**, rather than the original 7,800-query plan.
The broad adjacent-day run was stopped; successful captures remain reusable
in the cache, but adjacent dates are not requested or included in this Wizz
preparation. This deliberately leaves a UTC-boundary gap: previous-local-day
carry-ins and next-local-day departures falling inside the UTC replay window
may be absent. It does not change the existing Ryanair/easyJet snapshots or
claim complete UTC-day coverage. Each requested pair is a candidate, not a
confirmed operating route. Existing same-date captures are reused before any
network request, with at most two searches running concurrently.

Exact dated segments, source
duration and airport/time-zone validation remain mandatory; each flight keeps
the cheapest verified EUR quote. OTP/BBU, LTN/LGW, SPX and RMO retain their exact
identities. Armenia, Azerbaijan, UAE and Saudi airports have explicit IANA zones.

The full three-brand manifest contains **9,357 unique candidate directions and
320 airports**. A candidate route, future announcement, empty response or query
completion never creates an operating-flight claim.

## Capture, dates and fares

The full easyJet catalogue requires **6,694 exact airport-pair/date searches**,
covering origin-local dates needed for the UTC replay day plus an eight-hour
carry-in allowance. **403** were already cached after the representative pilot;
**6,291** remained for this expansion. The new pilot checked LGW–AMS, GVA–NCE and
LGW–SID, returning exact U2 records and verified EUR offers. Competitors such as
Swiss and TUI remain source diagnostics and are excluded from easyJet replay
records. Google requests stay unfiltered by carrier so existing captures remain
compatible; preparation admits only verified easyJet carrier codes.

The separate easyJet preparation merges into the original source seed before
the Ryanair timetable preparation runs. It cannot replace Ryanair records.
Google query identities deduplicate by date and exact endpoints, with matching
source hashes and collection contexts required for reuse. The cheaper quote is
retained only for identical flight identity, UTC schedule and currency. Changed
easyJet schedules do not inherit stale prices. Original seed flights not returned
by a later source remain fallbacks rather than presumed cancellations.

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
# Reproduce both full manifests from pinned discovery.
.venv/bin/python scripts/prepare_europe_flight_airports.py
# Collect missing easyJet searches only, retaining original EUR capture context.
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_europe_flights.py --brand easyjet --collect-only --concurrency 2
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_europe_flights.py --brand wizzair --collect-only --concurrency 2
# Build easyJet from cache and combine with the cached Ryanair timetables.
.venv/bin/python scripts/prepare_ryanair_flights.py --prepare-only
```

The final preparation creates temporary deterministic
`prepared-easyjet.json.gz` and `prepared-wizzair.json.gz` files in the Google
cache, then combines them
with the original committed Google seed and Ryanair captures. No additional
large source snapshot is committed. The Google cache and Ryanair cache have
exclusive preparation locks; final preparation refuses to run while easyJet
collection is active. `--google-cache` (also accepted as `--easyjet-cache`) and `--cache` select their respective
cache directories. `--ryanair-only` explicitly reproduces the earlier Ryanair
plus easyJet-starter stage; it is not the default for the full manifest.

The original Google seed collector still defaults to its frozen starter and
writes `data/sources/europe_flights_google_seed.json.gz`, never the combined
runtime archive. `--brand easyjet --prepare-only` prepares only easyJet into its
cache. Run the combined preparation afterwards to publish the replay archive.

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

`.cache/google-flights-europe-eur-v1/` contains 11,020 saved dated captures
(about 11.1 MiB including prepared intermediates). The final replay uses 9,539
unique queries; the rest include retained adjacent-date Wizz captures from the
stopped broad run.
`.cache/google-flights-europe-pilot-eur-v1/` holds the pilot. The full cache is needed to rebuild expanded easyJet and Wizz records;
the committed starter seed needs it only for a refresh. `.cache/europe-flights-audit/` and
`.cache/ryanair-expansion-audit/` and `.cache/easyjet-expansion-audit/` contain
optional comparisons, logs and browser
screenshots. `.cache/europe-http/` contains generated responses that regenerate.
The untracked Europe plan and unrelated country notes are preserved.

## Ryanair/easyJet baseline before Wizz expansion

All **6,694 / 6,694 easyJet origin/date searches** completed, covering all
**2,564 published directions and 164 candidate airports**, with **zero failed,
unattempted or rejected queries/records**. The interruption left successful
captures intact; 955 remaining searches were resumed without repeating those
already captured.

| Brand | Flight records | Airports returned | Directions returned | Priced records |
| --- | ---: | ---: | ---: | ---: |
| Ryanair group (unchanged) | 3,476 | 171 | 2,500 | 336 |
| easyJet | 1,449 | 119 | 940 | 1,449 |

The combined replay has **4,925 overlapping records**, **4,849 departures owned
by the UTC day**, **222 airports**, **3,295 directions** and **45 countries or
territories**. It contains **764 domestic** and **4,161 international** records.
Seventy-six records depart before the UTC day and remain because of arrival
overlap. Frequency lines count the 4,849 owned departures. Original carriers are
**FR: 3,396; RK: 80; U2: 1,449**; no operating subsidiary is inferred from U2.

There are **1,785 captured EUR quotes**, including all 1,449 easyJet records and
336 Ryanair seed records. The cheapest verified quote per exact flight is kept.
The 3,140 timetable-only Ryanair records remain unpriced. All **3,656 previous
records**, including all 180 easyJet starter records, compare equal field for
field with the previous snapshot; this expansion adds **1,269 easyJet records**.

The easyJet source queries comprise **2,362 target-brand results**, **635 results
containing only other carriers**, and **3,697 searches returning no direct
records**. These sum to 6,694. Across adjacent dates, 1,405 candidate directions
returned easyJet flights; 940 have records overlapping the replay day. Seven
queries had unverified fare context; no uncertain quote was assigned.

Forty-five easyJet candidate airports returned no overlapping easyJet flight:

ADB, AEY, AJA, BES, BIA, BIQ, BOH, BOJ, BVC, CAG, CLY, DBV, DJE, EFL, ESU, EVE, FDH, FSC, GNB, JMK, JSI, KLX, KTT, NAP, NQY, OSL, PUY, PVK, PXO, REU, RMI, RMU, RVN, SCR, SOF, SPC, SZG, TBS, TIA, TIV, TNG, TOS, TRN, VXE, ZAD.

The 744 original Google queries and 6,694 easyJet queries share **401 captures**,
so there are **7,037 unique Google searches**, plus **5,305 official Ryanair
monthly timetables**. All 7,409 union candidate directions were searched. The
combined generic request count is 12,342, with the different units explicitly
labelled; it must not be interpreted as 12,342 dated Google searches.

Snapshot: **852,060 bytes** (about 832 KiB), SHA-256
`27e5a8034e7c4b3f11cb27ff9c412e1127f45a58fbde54fb60284da70e1ba637`.
The final snapshot and full manifest reproduce byte for byte from pinned inputs
and cached captures. Existing country snapshots and the shared international
archive are unchanged. Generated caches are local and excluded from Git.

Full catalogue search completion is not a claim that every flight was captured.
easyJet's inaccessible direct timetable, seasonal schedules, unreturned services,
missing quotes and validation failures remain explicit gaps. Empty results mean
**not returned**, never **no service**. This is a dated November 2 snapshot,
not live tracking or a complete season's operating schedule.

Request counts remain separate: official **airport-pair/month** payloads,
easyJet **airport-pair/date** queries and **unique Google queries** after reuse.
The starter and easyJet source subtotals overlap and must not simply be added.
The overview displays monthly timetables and unique dated searches separately
in English and Indonesian. Expanded map bounds include Cape Verde endpoints.


The generated replay payload is about **16.3 MiB uncompressed / 3.9 MiB gzip**.
Deleting the Google cache leaves the committed replay working but requires
public searches again to rebuild expanded easyJet data. No search runs in the
application, and no automatic refresh is added.

**Validation:** 277 Python tests and 100 JavaScript tests passed. Checks cover
full manifests, exact airports, adjacent dates and island zones, verified carrier
aliases, competitor exclusion, context/currency mismatches, duplicated source
queries, conflicting flight identities, minimum quote selection, changed-clock
quote removal, missing/failed/empty results, complete source accounting, immutable
previous Ryanair/easyJet records, deterministic output, HTTP gzip/ETags/revisions,
unsupported dates, original flight countries and Melbourne replay regressions.

The full Europe browser suite passed with all 4,925 records: brand/RK filtering,
domestic/international and country filters, STN/LGW/DUB/BGY/GVA/BSL/NCE/MXP boards,
Sal arrivals in Atlantic/Cape_Verde (GMT-1), local dates, EUR previews, fullscreen
pagination/back, departures/arrivals/Destinations, frequency totals, cache reuse,
all themes, English/Indonesian and 390px mobile layout. Desktop map and mobile
board screenshots were visually checked. The existing international-network
browser suite also passed across prior country views and filters, local boards,
fullscreen navigation, themes, Indonesian and mobile layout. Unrelated local
notes and the untracked Europe plan remain unchanged.


## Wizz expansion coverage and validation

All **2,658 / 2,658 Wizz local-day searches** completed with zero failed,
unattempted or rejected queries/records. Of these, **905** returned Wizz flights,
**226** returned only other carriers, and **1,527** returned no direct flight
records. Empty responses mean **not returned**, never **no service**.

| Brand | Flight records | Airports returned | Directions returned | Priced records |
| --- | ---: | ---: | ---: | ---: |
| Ryanair group (unchanged) | 3,476 | 171 | 2,500 | 336 |
| easyJet (unchanged) | 1,449 | 119 | 940 | 1,449 |
| Wizz Air | 1,061 | 130 | 905 | 1,061 |

Wizz returned flights across **37 countries/territories**, with original
carriers **W6: 490, W4: 501, W9: 70**, including **62 domestic** and **999
international** records. All Wizz quotes are verified EUR, one adult, economy,
one way. Missing airport pairs, seasonal service, future/historical route
candidates, source omissions and the deliberate UTC-boundary gap remain
limitations. This is not a complete Wizz network claim.

The combined replay contains **5,986 records**, **256 airports**, **3,923
unique directions**, **50 countries/territories**, and **2,846 EUR quotes**.
Its **5,907 UTC-owned departures** drive frequency lines; 79 earlier departures
remain because their arrivals overlap the replay day. All **4,925 baseline
Ryanair/easyJet records compare equal field for field**.

The final source accounting has **9,539 unique dated Google captures** plus
**5,305 monthly Ryanair timetables**. Wizz reuses 156 queries already referenced
by the starter/easyJet data. Its collector also reused the earlier Wizz pilot
and partial-run captures. Google query identities and missing queries are
deduplicated across all three brand preparations; monthly Ryanair requests
remain a separate source unit. Source subtotals overlap and must not simply
be added. No shared International-network integration or country snapshot
change is included in this expansion. The initial map includes Baku.

Final compressed archive: **1,057,914 bytes**, SHA-256
`b2824d42584d9349236592959a988085e681a829c96de6cdb8bd210d7891a2db`.

Validation: **250 Python tests and 100 JavaScript tests passed**, including
flight-country regressions, Melbourne replay, HTTP gzip/ETags, date rejection,
exact airport identities, UTC/local and overnight timing, brand/carrier
validation, one-date Wizz query planning, shared capture accounting, duplicate
identities, quote selection and source gaps. The full manifest and final
archive reproduce byte for byte from pinned inputs and cached captures.

The browser suite passed against all **5,986 records**, covering all three
brand filters and RK/W6/W4/W9 carrier filters, real-country scopes, airport
boards including BUD/OTP/LTN, departures/arrivals/Destinations, fullscreen/back,
EUR previews, UTC/local clocks, frequency totals, cache reuse, themes,
English/Indonesian, 390px mobile layout and reset to the existing Nepal view.
Desktop map and mobile board screenshots were visually checked. Unrelated
country notes and the local Europe plan remain unchanged.
