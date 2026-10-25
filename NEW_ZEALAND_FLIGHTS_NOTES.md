# New Zealand flights

Choose **New Zealand · Flights** for **2 November 2026**, with Domestic /
International / Both. Domestic opens first. The timeline uses **Pacific/Auckland,
NZDT (UTC+13)**; boards use each airport's local dates and times. International
connections also appear in **International network · Flights**, whose day uses UTC.
These are dated schedule captures with partial coverage and illustrative paths,
not live aircraft tracks or ticket availability. No automatic refresh occurs.

## Discovery and exact airports

Domestic discovery covers **20 selected airports and 82 directional candidates**:

| Region | Selected airports |
| --- | --- |
| North Island | AKL, WLG, HLZ, TRG, ROT, TUO, GIS, NPE, NPL, PMR, KKE, WRE |
| South Island | CHC, ZQN, NSN, BHE, HKK, TIU, DUD, IVC |

[Air New Zealand's destination table](https://www.airnewzealand.com/en-nz/travel-info/destinations-we-fly-to)
supplies destination context; [Wellington Airport's domestic list](https://www.wellingtonairport.co.nz/flight-information/routes/domestic-destinations/)
supplies additional route context. Selected AKL/CHC/WLG hub pairs are explicitly
labelled probes because destination lists do not establish every exact pair or
its operation on this date. Frequencies never become invented flight instances.
A typo in Wellington's Gisborne paragraph names Hamilton; it is not transcribed
as proof of a Gisborne pair. WLG–GIS is a separately labelled probe.

Chatham Islands (CHT), smaller commuter, island and scenic services are deferred.
This release does not claim every domestic airport or carrier. Selected mainland
airports all explicitly use Pacific/Auckland; CHT is not assigned Auckland time.
The November day has daylight saving (+13), while winter fare-capture timestamps
retain NZST (+12). No fixed offset replaces IANA timestamp calculations.

International discovery covers **90 directions across 31 airports**, limited to
existing SunTrain flight countries and DXB/AUH/DOH. It imports **70 directions**
from primary Australia/Indonesia/Malaysia/Singapore/India/Gulf manifests and adds
focused Asian gateways. It does not perform all-airport/all-country searches.

Additional candidate context:

- [Air New Zealand destinations](https://www.airnewzealand.com/en-nz/travel-info/destinations-we-fly-to):
  country/city entries and seasonal notes, not proof of November 2 service.
  Tokyo is explicitly probed as NRT. Western Sydney WSI stays separate from SYD;
  a November launch mention does not establish operation on November 2.
- [Wellington Airport international destinations](https://www.wellingtonairport.co.nz/flight-information/routes/international-destinations/):
  Australian destinations become exact BNE/SYD/MEL/OOL candidates.
- [Auckland Airport's 2025 results presentation](https://www.aucklandairport.co.nz/content/dam/aia/files/corporate/annual-report-2025/FY25%20Annual%20results%20presentation.pdf):
  historical network context for focused Asian gateway probes, including exact
  TFU for a Chengdu probe. No city label substitutes a different airport.
- [Christchurch Airport's 2026 summer notice](https://www.christchurchairport.nz/about-us/who-we-are/media/2026/christchurch-airports-biggest-ever-international-summer-takes-flight/):
  CAN is a candidate; the announced CHC–NRT November 28 and CHC–PER November 30
  launches are outside this replay and excluded from new discovery.

HKG/TPE, Pacific islands, North America and other countries outside the existing
shared flight footprint remain out of this international scope. Existing country
views keep their previously captured worldwide routes. A Dubai candidate with a
stopover does not become a nonstop flight: only exact returned segments qualify.

Pinned OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies
unique active, country-matching IATA rows and coordinates. AKL/WLG/CHC/ZQN and
HLZ/DUD stay distinct. No municipality search codes or future airport substitutions.
The two new manifests retain evidence, input hashes, pinned airport provenance and
source URLs reviewed on 26 October 2026. Curated evidence hashes are not claimed
raw copies of complete live airline or airport websites.

## Captures, prices and ownership

Only dated Google Flights nonstop segments matching exact IATA endpoints, source
local departure date and validated duration become records. Domestic queries cover
**1–2 November**, with one-minute to eight-hour durations, retaining adjacent-day
overlap. International uses the shared union needed by UTC and every endpoint's
local day with a 24-hour duration ceiling. Inbound/outbound searches are separate;
reverse flights are not inferred from a published route. Empty results mean
**not returned**, never **no service**.

New searches request **USD, one adult, economy, one-way** and keep the cheapest
positive returned quote for each exact flight with its source capture timestamp.
Reused USD/MYR fares keep their original currency, context and timestamps. Amounts
are never converted or numerically compared across currencies. Missing or
unverified quotes remain unavailable. Unknown aircraft remain unknown; distinct
flight numbers are retained without guessing codeshares or physical aircraft counts.

The collector uses at most two concurrent public searches, resumable normalized
captures, challenge stops and explicit missing/failed/rejected/unreturned queries.
The shared international archive is stored once and projected by each view's UTC
timestamps and local day window. NZ's early local midnight does not shift UTC-day
ownership. Arrival/departure board events use half-open day boundaries.

## Preparation and local storage

```bash
.venv/bin/python scripts/prepare_new_zealand_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_new_zealand_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_new_zealand_flights.py --concurrency 1
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py --concurrency 1
```

The two collectors may run together with one worker each, or separately with up
to two workers. Do not run both at two workers. Domestic probes never publish a
full-manifest snapshot. Successful captures survive a collection stop.

Offline rebuilding:

```bash
.venv/bin/python scripts/prepare_new_zealand_flights.py --prepare-only
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Prepared domestic output: `data/reference/new_zealand_flights/2026-11-02.json.gz`.
International output: `data/reference/international_network/2026-11-02.json.gz`.
The domestic override is `SUNTRAIN_NEW_ZEALAND_FLIGHTS_REFERENCE`; shared overrides
use `SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE`. Custom fixtures remain isolated
unless both overrides are explicit. Existing reference bundles are untouched.
Stable ordering, fixed gzip mtime and atomic replacement enable exact cached rebuilds.

`.cache/google-flights-new-zealand/` and `.cache/google-flights-international-network/`
contain resumable normalized source captures. Removing them requires public
searches again for a later preparation; committed snapshots keep working.
The pinned CSV at `.cache/australia-flights-audit/ourairports-airports.csv` can be
downloaded again from the pinned manifest URL and verified SHA. Audit logs,
screenshots and optional artifacts in `.cache/new-zealand-flights-audit/` can be
removed; generated `.cache/new-zealand-http/` replay responses regenerate.


## Actual captured coverage

| Scope, NZ local day | Records | Airports, including foreign endpoints | Returned directions | Priced records | Queries |
| --- | ---: | ---: | ---: | ---: | ---: |
| Domestic | 433 | 20 | 78 | 433 USD | 164 / 164 |
| International | 198 | 21 | 57 | 40 USD + 4 MYR | 225 / 225 |

There are **0 failed/missing queries** and **0 unresolved selected airports**.
Domestic has 8 unreturned date queries, international 80. Returned domestic
coverage includes all **12 selected North Island and 8 selected South Island**
airports. WLG–IVC and WLG–TUO in both directions remain unreturned in the replay
window. CHT and smaller commuter/island/scenic services were not searched.

International records use **AKL, CHC, HLZ, WLG and ZQN**, connecting with returned
counterparts in AU/CN/ID/JP/KR/MY/SG/AE. DUD, Qatar and other unreturned candidates
remain gaps, not proof of no service. **154 international records are unpriced**;
there are 165 international departure events inside the NZ day. Records overlapping
a local day include overnight arrivals; they are not all departures owned by that
day. Distinct flight numbers are not inferred physical aircraft movements.

The shared UTC view now has **4,750 overlapping records**, **4,153 departures**,
**147 returned airports**, **1,325 returned directions** and **3,655 priced records**
(3,216 USD / 439 MYR). The shared archive has **6,767 records and 7,180 captured
queries**, with zero failed/missing queries. Its 315 additional queries reuse 194
existing captures and need 121 new international searches.

All **6,125 previous archive records and 6,865 previous query objects** remain
unchanged, including schedules, fares and provenance. NZ's earlier local midnight
extends the archive envelope two hours earlier; 375 additional non-NZ records from
existing captures fall outside all previous consumer-day windows and do not shift
existing view ownership. Existing country reference files remain untouched.

The shared gzip is **803,467 bytes**, SHA-256
`87fdf474b40947c1eb678bbfea80ff7cf4a041d577ca4b3de16bfb6a00c00304`.
The two NZ manifests, shared manifest and both compressed outputs reproduce
exactly from pinned inputs and saved captures.

Validation: **255 Python tests and 97 JavaScript tests passed**, including existing
ASEAN, Australia, Indonesia, Malaysia, Gulf and Asian flights, HTTP caching/date
rejection and Melbourne transit regressions. NZ tests cover exact national airport
identities, seasonal route exclusions, NZDT versus winter NZST, local midnight,
adjacent dates, overnight/short flights, duplicate records, cheapest USD quotes,
missing queries, strict currency/zone context and reproducible preparation.

Browser checks passed at AKL/WLG/CHC/ZQN/NSN/BHE/DUD for exact airport/airline
filters, departures/arrivals, quotes, fullscreen/pagination/back, Destinations,
frequency lines, station visibility, themes, Indonesian and mobile. A Sydney
board retains its GMT+11 local window while the replay uses NZDT. NZ→AU/SG/JP/MY
UTC network filters passed. All five recent ASEAN country views and network
filters also passed after the shared profile change. Desktop/mobile screenshots
were visually reviewed.

```bash
.venv/bin/python -m pytest -q tests/test_new_zealand_flights.py tests/test_international_network.py
node --test tests/*.cjs
PYTHONPATH=.cache/browser-tools SUNTRAIN_TEST_URL=http://127.0.0.1:8879 .venv/bin/python tests/browser_new_zealand_flights.py
```
