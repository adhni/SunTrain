# Philippines flights

Choose **Philippines · Flights** for **2 November 2026**, with Domestic /
International / Both. Domestic remains the default. The replay clock uses
**Asia/Manila, Philippine time (PHT, UTC+8)**; each airport board uses its own local
zone and the selected replay window. International connects only to existing
SunTrain flight countries and DXB/AUH/DOH, and appears in the shared UTC network.
Coverage is partial, paths are illustrative and fares are captured quotes, not live
prices. The app performs no live search or refresh.

## What the supplied ZIP contributes

`philippines_recovered_partial_2026-11-02.zip` is a reconstructed partial research
package, not a schedule archive. It supplies **150 domestic route candidates,
128 international candidates, 314 evidence rows, 74 endpoint rows and 278 queue
rows**. Its timetable CSV has **zero records**; it has **no dated flights or fares**.
Airport names, coordinates and ICAO fields are blank, and some foreign zones are
missing. Its own metadata says the original larger research package was unavailable
and several route transcriptions were not independently rendered again.

The committed `data/sources/philippines_recovered_candidates.json` retains source
rows, package metadata, the original ZIP SHA-256 and per-member hashes. This is
input data, not operational instructions. Candidates remain labelled **recovered,
not independently verified**; descriptions such as “published” in the package do
not become claims of current service. The original archive remains unchanged in
Downloads. Rebuilding manifests uses the committed seed and pinned airport CSV,
not an unavailable original research report or a new ZIP download.

An explicit package-specific correction maps **NAG → WNP** for the row claiming
Philippines/Naga. Pinned OurAirports identifies Naga as **WNP / RPUN**, while **NAG /
VANP is Nagpur, India**. The raw package row is preserved and the correction appears
in both manifests. Existing Indian NAG identities and routes remain unchanged.

## Exact identities and candidate handling

Pinned OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies unique,
non-closed, country-matching IATA identities and coordinates. All Philippine
endpoints explicitly use Asia/Manila. MNL/CRK, CEB/TAG, USU/ENI and DRP/WNP remain
separate. Cities or similar airport names never substitute for IATA endpoints.

The domestic manifest has **37 airports and 150 directional candidates** across
Luzon, Visayas and Mindanao. Regional pairs in the package are included as probes;
this is not an exhaustive national inventory. The international manifest has
**90 directions across 31 airports**, preserving **52 existing candidates** from
other country manifests. All 90 are included in the shared network. **38 package
directions** outside the existing flight-country footprint are deferred and listed
explicitly, including Hong Kong/Macau/Taiwan, Vietnam, Canada and Pacific endpoints.
No existing country manifest is replaced by the reduced research package.

Official pages were reviewed to check the package’s limitations:

- [Clark flight listings](https://clarkinternationalairport.com/flights/) are an
  airport timetable/destination source whose edition can differ from the target
  date; undated weekly patterns are not November 2 flight instances.
- [Cebgo/AirSWIFT Manila-to-Clark relocation](https://help.cebupacificair.com/article/transfer-of-cebgo-dg-and-air-swift-t-220100)
  explicitly transfers those operations from MNL to CRK from March 29, 2026.
  Older MNL candidates are not silently moved, nor is every carrier assumed to
  follow one carrier’s notice. Each exact origin/date is collected separately.
- [PAL winter timetable, October 16 edition](https://www.philippineairlines.com/content/dam/palportal/migration/feature/timetable/261016-International-W26-as-of-Oct-16-2026.pdf)
  has recurring services and effective-date restrictions, including later-November
  and December launches. The supplied timetable CSV is empty. This release does
  not add a PDF schedule adapter or invent dated instances from route names.
- [Cebu Pacific’s Iloilo guide](https://help.cebupacificair.com/article/iloilo-travel-guide-iloilo-international-airport-ilo-211297)
  links route information but does not establish a particular Nov 2 flight. The
  package flags ILO–SIN start-date conflicts; those pairs remain unverified probes.
- The package’s Dubai–Cebu–Clark triangular-service warning is retained. A route’s
  reverse direction or multi-leg itinerary never creates a fictitious nonstop.

Only dated Google Flights nonstop segments with matching exact airports, local
date and source duration become replay records. Empty searches mean **not returned**,
not **no service**. Distinct flight numbers remain distinct; repeated exact
identities are deduplicated without guessing codeshares. Unknown aircraft remain
unknown. Domestic durations allow one minute to eight hours; international allows
up to 24 hours.

## Fares, collection and storage

New searches request positive USD quotes for **one adult, economy, one-way**, choosing
the cheapest returned quote for the exact flight. Original capture timestamps are
retained. International reused USD/MYR quotes retain their original currency;
there is no conversion or numerical comparison between currencies. Missing or
unverified offers remain unavailable.

Domestic searches cover November 1–2 and retain only flights overlapping the
Manila day. The shared collector computes the union for UTC and every country’s
local day, including adjacent origin-local dates for overnight international
flights. The extension reuses **127 international captures** and needs **176 new
international searches**, plus **300 domestic searches**. The collectors initially run one worker each, then domestic resumes with two
workers after international finishes; at most two searches run simultaneously. Challenges stop the affected
collector; successful captures and missing-query diagnostics survive.

```bash
.venv/bin/python scripts/prepare_philippine_flight_airports.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_philippine_flights.py --concurrency 1
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py --concurrency 1
.venv/bin/python scripts/prepare_philippine_flights.py --prepare-only
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Domestic data lives at `data/reference/philippines_flights/2026-11-02.json.gz`,
overridable with `SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE`. International is stored
once in the shared archive, independently projected into Manila and UTC windows.
The Philippine HTTP revision fingerprints both files; custom domestic fixtures
remain isolated unless an explicit shared reference is provided too.

Resumable queries live in `.cache/google-flights-philippines/` and
`.cache/google-flights-international-network/`; optional logs, coverage reports and
screenshots are in `.cache/philippines-flights-audit/`. Deleting those captures
saves local storage but requires new searches to rebuild; committed replays still
work. The pinned OurAirports CSV is reused from `.cache/australia-flights-audit/`.
Generated HTTP caches are disposable. Gzip uses stable ordering, fixed mtime and
atomic replacement for reproducible offline preparation.

## Actual coverage at the initial Philippine release

The figures below describe the initial Philippine release. Vietnam adds 33
overlapping international records; the current international view has **310 records**,
**260 Manila-day departures** and **278 priced records**. Current shared totals
are in [International network notes](INTERNATIONAL_NETWORK_NOTES.md).

Captured **25 October 2026** for the **2 November 2026 Manila day**:

- Domestic: **647 overlapping records**, **627 departures** and **631 arrivals**
  inside the day, **30 airports**, **106 directional routes**, **5 carriers**.
  All **647 have positive captured USD fares**. Overnight records from November 1
  are retained; a record overlapping the day is not necessarily a departure in it.
- All **300 / 300 domestic airport/date queries** captured. **120 of 150**
  directions returned flights on at least one searched date; **91 queries** returned
  no matching direct flights. **BSO, CBO, PAG, SJI, TBH, TWT, WNP** were searched but not
  represented in the replay. These are coverage gaps, not assertions of no service.
- International: **277 overlapping records**, **232 departures**, **233 arrivals**,
  **74 directional routes**, **29 airports**, **26 carriers**. Returned Philippine
  gateways: **CEB, CRK, DVO, ILO, MNL**. **245 priced records**
  (219 USD, 26 MYR), **32 unpriced**.
- All **210 / 210 Philippine-view international queries** captured; **45**
  returned no matching direct flights. Both scopes have zero failed/missing queries,
  rejected records or unresolved airport identities. Larger nationwide coverage,
  unreturned airlines/services and the 38 deferred international directions remain
  gaps. Search completion does not imply complete aviation coverage.
- Both scopes together contain **924 records**. The UTC network separately contains
  **3,849 records** and **3,336 departure events**. Every one of the previous
  **4,778 archive records and 5,237 queries** remains unchanged, including
  original schedules, fares and provenance. Existing country bundles are untouched.

| Origin island group | Airports returned / selected | Manila-day departures | With USD fare |
| --- | --- | ---: | ---: |
| Luzon | 11 / 14 | 292 | 292 |
| Visayas | 10 / 11 | 225 | 225 |
| Mindanao | 9 / 12 | 110 | 110 |

Domestic gzip: **36,852 bytes**, SHA-256
`b99f70d3758716bb329dddb25878133982e2a25e05139113a2a22d2c40e330db`.
Shared gzip: **625,007 bytes**, SHA-256
`6a7adf9aba6f8d74f9ab84f1e080a397c57f516909b14012e28de7b7a64b51d2`.
Both archives and all three manifests reproduce byte for byte offline from cached inputs.

Validation: **222 Python tests and 94 JavaScript tests passed**, including all
existing flight profiles, Melbourne replay/HTTP, Thailand rail, app/i18n and Japan
rail. Two Chrome suites passed the Philippine and existing shared-network views:
eight domestic airport boards, separate MNL/CRK, USD previews without implicit
seeking, PHT and foreign local clocks, all scopes, airline/airport/country filters,
fullscreen/back/pagination, Destinations, frequency totals, airport visibility,
all five themes, Indonesian, mobile and cache reuse. Desktop/mobile screenshots
were visually inspected; no page errors occurred. Byte-identical rebuilding and
preservation of all prior shared records/queries were independently checked.
