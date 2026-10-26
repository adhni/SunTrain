# Europe: nine main flag carriers

The **2 November 2026** Europe replay adds the main flag carriers from three
groups. The collection is one shared queue, not nine separate searches of the
same airport pair.

| Group | Included source carrier codes | Map colour |
| --- | --- | --- |
| Lufthansa Group | LH Lufthansa, LX SWISS, OS Austrian, SN Brussels Airlines | Gold |
| IAG | BA British Airways, IB Iberia, EI Aer Lingus | Teal |
| Air France–KLM | AF Air France, KL KLM | Lavender |

This release excludes Eurowings, Discover, Edelweiss, ITA, Vueling, LEVEL,
Transavia, SunExpress, SAS, Virgin Atlantic and regional carriers appearing
under their own separate codes. A regional-operated flight returned under one
of the nine included source codes remains eligible; no operator is inferred.
The map groups are a deliberately limited collection roster, not a claim to
cover every airline owned or partly owned by each group.

Group membership references:
[Lufthansa Group 2026 report](https://investor-relations.lufthansagroup.com/fileadmin/downloads/en/financial-reports/interims-reports/LH-QR-2026-1-e.pdf),
[IAG airlines](https://www.iairgroup.com/about-us/),
[Air France–KLM](https://www.airfranceklm.com/en).
The pinned discovery records link each carrier to the
[IATA code directory](https://www.iata.org/en/publications/directories/code-search/).

## Exact route candidates

`data/sources/europe_groups_discovery.json` pins airport pairs from the public
Great Circle Pro airline route-map SVGs, with source URLs, file SHA-256 hashes
and schedule-period descriptions. For example, the
[Lufthansa map](https://www.gcpromap.com/assets/images/airlines/carriers/lh-routes.svg)
and [Air France map](https://www.gcpromap.com/assets/images/airlines/carriers/af-routes.svg)
contain explicit airport-pair labels, so destination lists are never expanded
into guessed hub combinations. Secondary maps are candidates only, not dated
flight evidence. Their July 2026–June 2027 schedule period can contain seasonal,
historical or future routes; no Nov 2 operation is inferred from it. Pairs
outside the European footprint are excluded. Previously captured dated flights
supplement candidate pairs missing from a map, with their provenance pinned.

The normalized manifest has **3,190 airline-specific directional candidates**
and **3,098 unique airport directions**. Overlapping airline candidates share
one Google query. **352** compatible exact-date captures were already cached,
leaving **2,746 new requests**, including four pilot searches. No all-airport
Cartesian product or international-to-existing-country restriction is used.
Both directions are candidates; a route's existence never proves both operate.

Pinned OurAirports data supplies unique exact IATA/ICAO identities and positions.
Each airport has an explicitly pinned IANA time zone. City airports remain
separate, including LHR/LCY/LGW, CDG/ORY, JFK/EWR and FCO/CIA. Airport resolution
and conflicting country/time-zone/ICAO identities fail preparation rather than
silently substituting a city code. Routes wholly outside Europe, including
foreign fifth-freedom legs, are outside this release.

## One date, shared cache, verified fares

**Only 2 November in each origin airport's local time is searched.** No adjacent
date is requested, even for overnight flights. Arrivals can be on another local
date when explicitly returned by the source. The replay keeps its existing UTC
window and airport-local boards. This deliberately leaves UTC-midnight gaps:
some previous-local-day carry-ins and next-local-day departures are missing.
Source flights not overlapping the UTC replay window do not enter the replay.

The existing Google collector runs two workers, records capture timestamps and
source hashes, resumes successful captures and stops on access challenges.
The representative pilot checked FRA–SIN, LHR–JFK, AMS–LAX and CDG–RUN: source
arrival dates, durations longer than eight hours and verified EUR fares passed.

New captures use a separate 24-hour parser/capture context in
`.cache/google-flights-europe-groups-eur-v1/`. The nine new airlines permit
one-minute to 24-hour durations, validated against source duration and both
airport-local dated clocks. Ryanair, easyJet and Wizz retain the eight-hour
limit. Unsupported/ambiguous timings are rejected rather than guessed.

Compatible earlier EUR captures in `.cache/google-flights-europe-eur-v1/` are
read directly with their original timestamps and capture context unchanged.
Reuse requires exact airport/date identity, the same parser/fare context and
no rejected source records. A prior duration rejection or incompatible context
requires a new capture. Missing quotes remain missing; no page-wide minimum or
connecting-itinerary total is assigned to an individual segment.

The fare policy remains one adult, economy, one way, cheapest verified EUR
quote per exact source flight identity and schedule. Distinct flight numbers
remain distinct; matching times are not evidence of a codeshare or one physical
flight. Frequency lines count captured flight identities, not independently
verified physical aircraft movements. Aircraft unspecified by the source stay
unknown. No live tracking or automatic refresh is added.

## Rebuilding and interface

```sh
# Rebuild exact-airport candidates from pinned discovery (no flight searches).
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_europe_group_routes.py

# Show deduplication and cache reuse before any flight search.
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_europe_groups.py --dry-run

# Capture only missing searches; two workers, Nov 2 only.
PYTHONPATH=.cache/browser-tools PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_europe_groups.py --collect-only

# Rebuild all twelve Europe brands from cached sources.
PYTHONPYCACHEPREFIX=.cache/pycache .venv/bin/python scripts/prepare_europe_groups.py --prepare-only
```

The original Ryanair preparation CLI also includes the group captures when
their manifest is present. The frozen starter and previous brand manifests
remain separate. Final preparation deduplicates query identities and missing
queries across sources. Monthly Ryanair timetables and dated Google queries
are separate request units; per-brand/group subtotals overlap.

The existing airline selector adds group options alongside individual airlines
and source carrier codes. Replay responses add optional `flight_groups`
metadata and per-service `flight_group`; other locations do not receive them.
Original airline colours stay unchanged. Europe remains the initial map frame;
Fit selection reaches overseas airports using existing continuous route arcs.
Airport filters, local departures/arrivals, Destinations, fullscreen/back,
frequency view, English/Indonesian and mobile layout are reused.

The committed archive remains
`data/reference/europe_flights/2026-11-02.json.gz`. It uses deterministic gzip,
sorted identities and atomic replacement. The original 5,986 records must
compare equal field for field. Country snapshots and the shared International
network are unchanged. Deleting raw collection caches leaves the committed
replay working, but rebuilding would require collecting those public searches
again. Audit logs and screenshots are local and excluded from Git.

## Actual coverage and validation

All **3,098 / 3,098 searches** completed, with zero failed, unattempted or
rejected queries/records. **1,781** returned a target carrier, **286** returned
only other carriers, and **1,031** returned no direct records. Only **2,746**
requests were new; the other **352** were read from compatible earlier captures.

| Airline | Replay records | Airports | Directions | Priced records |
| --- | ---: | ---: | ---: | ---: |
| Lufthansa | 768 | 123 | 324 | 768 |
| SWISS | 319 | 75 | 151 | 319 |
| Austrian | 276 | 64 | 115 | 276 |
| Brussels Airlines | 184 | 54 | 98 | 184 |
| British Airways | 735 | 139 | 275 | 734 |
| Iberia | 579 | 98 | 212 | 579 |
| Aer Lingus | 247 | 57 | 119 | 247 |
| Air France | 638 | 141 | 258 | 637 |
| KLM | 660 | 132 | 236 | 660 |

Group totals are **1,547 Lufthansa Group**, **1,561 IAG** and **1,298 Air
France–KLM** records. The nine airlines return **4,406 overlapping records**,
including **458 flights longer than eight hours**, across **296 airports** and
**117 countries/territories**. There are **822 domestic** and **3,584
international** new records. Of the 4,406 records, **4,404 have verified EUR
quotes**. AF662 CDG–DXB and BA400 LHR–AMM have no returned quote and remain
unpriced. The combined new-cohort manifest has 402 candidate airports; 106
returned no overlapping target flight. Those airports remain coverage gaps,
not evidence of no service.

Europe now contains **10,392 records**, **415 airports**, **5,394 distinct
airport directions**, **119 countries/territories** and **7,250 EUR quotes**.
All **5,986 original records compare equal field for field**. Frequency lines
count the **10,277 UTC-owned departures**; the other 115 records remain because
their arrivals overlap the replay window. This is a partial dated schedule
snapshot, not a complete network or physical-aircraft census. Empty responses
mean **not returned**, never **no service**.

Overall accounting is **12,285 unique dated Google captures**, plus **5,305
monthly Ryanair timetables**. The three new group subtotals share routes and
must not be added as if each were a separate request queue. Country snapshots
and the shared International network remain unchanged.

Archive: **1,415,547 bytes** (about 1.35 MiB), SHA-256
`5b6ceefc54ad2ffd1196fe7056134dfe2c799868e10ee263484f707b1252d882`.
The normalized route manifest and final archive reproduce byte for byte from
pinned inputs and saved captures.

**Validation:** 261 Python tests and 101 JavaScript tests passed, including
single-date/deduplicated query planning, compatible-cache reuse and rejection,
source duration/overnight/local clocks, exact airports, group/brand/code filters,
quote handling, shared merge accounting, existing flight-country regressions,
Melbourne replay, HTTP caching and date rejection.

The browser suite passed against all **10,392 records**, including all twelve
brand filters, three group filters, original carrier codes, country scopes,
FRA/ZRH/VIE/BRU/LHR/MAD/AMS/CDG/JFK boards alongside earlier airports, JFK's
GMT-5 clock, departures/arrivals/Destinations, fullscreen/back, EUR previews,
frequency totals, cache reuse, all themes, English/Indonesian, 390px mobile
layout and reset to the existing Nepal view. The regional Europe starting
frame and overseas airport fitting were also verified. Desktop and mobile
screenshots were visually inspected. Unrelated local notes and plans are
preserved.
