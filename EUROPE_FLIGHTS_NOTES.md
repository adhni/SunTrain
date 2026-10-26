# Europe flights — Ryanair and easyJet starter

**Europe · Flights** is a regional view for **2 November 2026**, initially limited
to **Ryanair and easyJet**, with verified source-carrier aliases. The user chose
a **broad starter across Europe**, rather than a full published-network search.
Other airlines can be added to this same view later.

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
returned ten November 2 flights; all ten flight numbers and departure/arrival
clocks matched the Google pilot exactly. This is a representative comparison,
not evidence of full Ryanair coverage. No independent dated easyJet timetable
comparison is claimed: its local public timetable request was denied. Both
brands have usable dated Google records; official route lists remain discovery
evidence and never create dated flights or prices.

## Starter selection and exact airports

`data/sources/europe_flights_discovery.json` retains the full normalized discovery
inventory, source URLs, hashes, airport zones and partner exclusion. Eligible
discovery contains **5,305 Ryanair directions** and **2,564 easyJet directions**,
with at least one endpoint in the explicit reviewed Europe membership set.
Wholly non-European pairs, including Moroccan domestic routes, are deferred.
External endpoints such as Morocco, Egypt and Cape Verde can appear when the
other endpoint is in the reviewed Europe set.

The requested starter uses a deterministic selection: represent each published
country, then the reviewed major/secondary airport list, then round-robin
additional links across those airports. It chooses up to **80 undirected pairs
per brand**, yielding **160 directions per brand**, **306 unique directions**
and **84 airports**, across **48 candidate countries/territories**. Source pairs
are searched in their published directions; no reverse flight is invented.
Candidate coverage is not returned service coverage.

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

The regional UTC day requires **744 exact origin/date queries** across the 306
selected directions. The origin-local date range covers the UTC window plus an
eight-hour carry-in allowance; adjacent November 1/3 queries retain overnight
services. Eight hours is the documented regional duration ceiling, not an
invented flight time. Existing timestamp/DST/source-duration validation applies.
Repeated identities deduplicate; conflicting records fail rather than silently
win. Airport boards use half-open event ownership, including arrivals exactly
at the replay midnight.

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
.venv/bin/python scripts/prepare_europe_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_europe_flights.py --concurrency 2
.venv/bin/python scripts/prepare_europe_flights.py --prepare-only
```

`data/reference/europe_flights/2026-11-02.json.gz` is the deterministic regional
snapshot, with fixed gzip mtime and atomic replacement. Its runtime override is
`SUNTRAIN_EUROPE_FLIGHTS_REFERENCE`; it is independent of every country snapshot
and `SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE`. Unsupported dates are rejected.
HTTP gzip revisions/ETags include the regional reference; a changed file
invalidates generated responses.

`.cache/google-flights-europe-eur-v1/` holds resumable source queries and
diagnostics. Removing it means public queries are needed again for preparation;
the committed replay still works. `.cache/google-flights-europe-pilot-eur-v1/`
holds the reusable pilot. `.cache/europe-flights-audit/` contains optional raw
catalogues, pilot comparisons, logs and screenshots; pinned URLs/hashes and
committed normalized discovery permit recovery. Generated `.cache/europe-http/`
responses regenerate. The earlier untracked `EUROPE_FLIGHTS_PLAN.md` is preserved.

## Captured coverage and validation

All **744 / 744 planned queries** completed, with **zero failed or unattempted queries** and **zero rejected source records**. This is the requested broad starter, not the airlines' complete networks.

| Brand | Records | Airports | Directional routes | Priced records |
| --- | ---: | ---: | ---: | ---: |
| Ryanair group | 336 | 52 | 115 | 336 |
| easyJet | 180 | 39 | 83 | 180 |

The combined replay has **516 overlapping records**, **511 departures inside the UTC day**, **64 airports**, **184 directional routes** and **38 countries/territories**. All **516** records have captured **EUR** quotes. Source carriers are **FR: 304, RK: 32, U2: 180**. No competing airline is included and no marketing code is replaced by a guessed operating affiliate.

There are **92 domestic records** and **424 international records**, classified by the actual endpoint countries. The scope-level query counts are independently computed from their relevant airport pairs. Five records depart before the UTC day and remain available because of arrival overlap; frequency totals count only the 511 owned departures.

Across all origin-local search dates, **451 queries returned target-brand records**, **23 returned only other carriers**, and **270 returned no direct records**. These categories sum to 744. A single query had unverified fare context; no unverified quote was assigned. Successful empty queries and other-carrier results are saved and are not “no service” claims. A target-brand result on an adjacent date also does not imply a flight overlaps November 2.

Twenty candidate airports did not return target-brand records overlapping the replay day: **ADB, AMM, BJV, DBV, DJE, INI, IOM, KTT, LCA, NAP, PRN, PUY, SCR, SEN, SJJ, SKP, TBS, TIV, VIL, WAW**. The starter includes only selected links at each represented airport; unsearched links, seasonal changes, sold-out/unreturned services and other airlines remain gaps. All source schedules and fares remain partial dated captures.

Snapshot gzip: **67,999 bytes** (about 66.4 KiB), SHA-256 `14056960dab139809a8da18eddc3cc99b4a062703321ea3c8088a85d52da0e68`. The uncompressed replay payload is approximately **1.19 MiB**; no partition is needed at this size. The archive and selected route manifest reproduce byte for byte from cached/committed inputs. The shared international archive and all previous country reference data are unchanged; unrelated local notes and the untracked Europe plan were checked unchanged too.

**286 Python tests and 100 JavaScript tests passed**, including original flight countries and transit regressions. Coverage includes brand/affiliate maps, competitor exclusion, unchanged source identities, exact airports/BSL country, Europe membership, domestic versus cross-border scopes, EUR minimum quotes, UTC/local/overnight/DST handling, duplicate/conflict rejection, missing versus empty/other-carrier results, cache context, HTTP gzip/ETags/revisions and unsupported dates.

The Europe browser suite passed for both brand groups and RK-specific filtering, real-country scopes, GB–IE/GB–MA/IT–IT filters, STN/LGW/DUB/BGY/GVA/BSL boards, arrivals/Destinations, EUR previews, fullscreen pagination/back, UTC versus Swiss local clocks, all five themes, Indonesian, 390px mobile layout, frequency totals, cache reuse and return to the existing Nepal view. Desktop/mobile screenshots were visually checked.

The existing international-network browser suite also passed, covering earlier country views and filters, foreign local boards, fullscreen navigation, frequency totals, themes, Indonesian and mobile layout.
