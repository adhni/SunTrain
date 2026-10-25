# Gulf hub flights

Bismillah, one explorer for Dubai International **DXB**, Abu Dhabi **AUH** and Doha **DOH**, for **2 November 2026**. This is a dated schedule and fare snapshot, not live tracking or a complete hub timetable.

## Experience and time

Choose **Gulf hubs · Flights**. DXB opens first. The three hub shortcuts apply the existing airport filter; **All hubs** clears the airport and route filters. Airline filters stay selected. An airport selection hides unrelated traffic; Departures / Arrivals / Both controls the matching endpoint. Other captured airports can also be selected by exact IATA code. DXB, AUH, DWC and SHJ are never merged by municipality.

The shared midnight-to-midnight replay uses **Asia/Dubai (UTC+4)**. DXB and AUH boards use that zone; DOH uses **Asia/Qatar (UTC+3)**. All overseas boards retain explicit local IANA zones. Source origin-local dates around the replay window are searched to retain overnight and long-haul carry-ins. Flights require dated departure and arrival timestamps; durations of 1 minute to 24 hours are checked against the source duration. Aircraft unspecified by the source remain unknown. Paths are illustrative great-circle arcs, visible only for selected flights unless frequency mode is selected.

Departures, arrivals, Destinations, preview/back behavior, fullscreen pagination, airline-code filters, frequency lines, five themes and English/Indonesian reuse the existing flight explorer. Frequency counts respect the selected airport and direction and stay fixed when seeking the timeline.

## Candidates and airport identity

The manifest is `data/sources/gulf_flights_routes.json`, rebuilt by `scripts/prepare_gulf_airports.py`. Every candidate pair is searched in both directions. A published or historical route is a search candidate, never evidence of a dated flight.

The reviewed manifest contains **303 candidate airports**, **1,170 directional routes** and **3,095 origin-local airport/date queries**. Canonical ownership assigns 536 directional routes to DXB, 250 to AUH and 384 to DOH; inter-hub routes appear only once in those totals.

Primary candidate sources, reviewed 25 October 2026:

- [Emirates/flydubai June 2025 network map](https://c.ekstatic.net/ecl/documents/partners/ek-fz-network.pdf), supplemented with the [flydubai airport directory](https://www.flydubai.com/en-gb/destinations/airports/) and [Dubai’s official Helsinki announcement](https://cd1.mediaoffice.ae/en/news/2026/january/13-01/emirates-to-launch-flight).
- [Zayed International Airport destination/airline table](https://www.zayedinternationalairport.ae/en/flights-and-check-in/destination-and-airlines/destinations): 125 exact airport codes. Includes published/upcoming candidates; not every entry necessarily operates on the replay day.
- [Qatar Airways network map](https://www.qatarairways.com/content/dam/corporate/images/551_networkroutemap_global.pdf), supplemented by its [April 2026 map](https://dmassets.qatarairways.com/adobe/assets/urn%3Aaaid%3Aaem%3A46c43466-defb-44be-92cc-15668586a966/original/as/Q60-Network-map-07APR26.pdf) and [Bogotá/Caracas announcement](https://www.qatarairways.com/press-releases/en-WW/265500-qatar-airways-set-to-operate-to-caracas-venezuela-and-bogota-colombia-from-july-2026/). Maps can include seasonal or via services; only returned single-leg dated records are retained.
- Reciprocal candidates from the existing Australian, Indonesian and Malaysian international manifests, plus explicitly labelled exact-airport probes for other carriers and newer routes.

City labels are resolved to separate exact-airport candidates where ambiguous. The route evidence hash covers the curated resolutions and probes; it is **not** a hash of the original website bytes. Source URLs and evidence kind are retained per candidate. Queries that return nothing mean **not returned**, never no service.

Airport coordinates and identities use the existing pinned **OurAirports** snapshot. Time zones use a pinned [OpenFlights catalogue](https://raw.githubusercontent.com/jpatokal/openflights/e539814f664cf31e662710555b27e9688610a911/data/airports.dat), SHA-256 `9387cdb38df5bd664da823f8ccb69fdd9b33a1888f5b7cca09c34a3cd9ff59f9`, joined only where airport ICAO identity also matches. Existing reviewed country zones and explicit modern-airport overrides are recorded in the manifest. Bishkek’s former **FRU** resolves to **BSZ**, the same **UCFM** airport, following the [official 9 August 2025 code change](https://airport.kg/ru/news/15); unrelated reuse of BSZ is not accepted. New Luanda **NBJ** and old **LAD** remain distinct candidates.

## Captured USD fares

Searches request **USD, one adult, economy, one-way** and verify the visible fare context. The collector retains the cheapest positive quote linked to the **exact dated flight identity**, including carrier/flight number and airports. It does not use a page-wide minimum or a connecting itinerary’s total. Repeated identities are deduplicated; different flight numbers stay distinct even when times match. No codeshares are inferred from matching clocks.

Prices preserve integer USD minor units and capture timestamps. No MYR-to-USD conversion is performed; existing Malaysian snapshots remain MYR. A schedule can be retained without a price if fare context cannot be verified or no exact-flight quote is returned. The UI shows **Price unavailable** for missing fares. Required taxes/fees follow the returned quote; optional baggage and charges can cost extra. These are captured fares, not current offers or booking guarantees.

## Rebuilding and storage

```sh
.venv/bin/python scripts/prepare_gulf_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_gulf_flights.py
# Rebuild solely from successful cached captures; no searches:
.venv/bin/python scripts/prepare_gulf_flights.py --prepare-only
# Reproduce elsewhere for byte comparison:
.venv/bin/python scripts/prepare_gulf_flights.py --prepare-only --output /tmp/suntrain-gulf-rebuilt
```

The network collector requires Playwright and local Chrome, as the other flight collectors do. It uses **two concurrent searches total**, round-robin across the hubs, and a single collection lock. Successful JSON captures are atomic and resumable. Search challenges stop all collection; successful captures and missing-query reports are retained. Do not retry or bypass an access challenge. Ordinary query failures are reported separately from empty results.

Caches live under `.cache/google-flights-gulf/DXB/`, `AUH/` and `DOH/`. The first matching endpoint in **DXB, AUH, DOH** order owns both directions of an inter-hub pair, so those queries run once. Preparation writes deterministic gzip bundles `data/reference/gulf_flights/2026-11-02-DXB.json.gz`, `-AUH.json.gz` and `-DOH.json.gz`. Ownership is a storage detail; each hub’s visible coverage includes every flight touching it, including flights captured by another owner. The loader merges all three and deduplicates flights and query identities.

`SUNTRAIN_GULF_FLIGHTS_DIRECTORY` overrides the bundle directory. Existing compressed replay HTTP caching serves the combined selected day; no collection happens at runtime, no paid API is used, and there is no automatic refresh. The source airport CSV and 1.1 MB timezone catalogue are preparation-only ignored caches and can be downloaded again from their pinned URLs/hashes.

## Coverage

Captured **24 October 2026 23:37 UTC – 25 October 2026 00:46 UTC** (25 October in Melbourne). All **3,095 planned queries**, **1,170 directional routes** and **303 candidate airports** were searched. There are **zero unresolved failed/missing queries** and **zero unresolved airport identities**. One DXB–RIX query for 1 November timed out, then succeeded on a single ordinary retry; no access challenge occurred.

The retained replay contains **2,461 overlapping flights**, **837 directional routes**, **211 airports**, **93 airport-country codes** and **58 carrier codes**. It has **2,421 captured USD fares** and **40 unavailable prices**. Sixteen queries could not verify fare context; any returned dated schedules were retained without assigning uncertain prices. No source records failed duration/identity validation.

| Hub | Airports returned | Directional routes returned | Overlapping flights | USD fares | Unavailable prices |
| --- | ---: | ---: | ---: | ---: | ---: |
| DXB | 188 | 369 | 1,191 | 1,163 | 28 |
| AUH | 103 | 204 | 561 | 556 | 5 |
| DOH | 139 | 268 | 749 | 742 | 7 |

Hub rows include both endpoints of inter-hub flights, so their totals are not additive. The combined view deduplicates those identities: 40 retained flights touch two selected hubs. Ownership remains separate: DXB stores 1,331 query captures, AUH 619 and DOH 1,145.

**920 queries returned no matching direct flight records.** This includes adjacent origin-local dates and means “not returned”, never “no service”. Some routes returned records outside the replay window only. Ninety-two candidate airports have no retained overlapping flight; historical, seasonal, upcoming, via-only and unlisted services remain explicit gaps. Google listings, airline coverage and fare coverage can be incomplete even where all queries finished. No schedules were invented to fill those gaps.

The three deterministic prepared bundles total **288,612 bytes (about 282 KiB)**. The manifest, per-query timestamps, result status, source hashes, fare errors, route provenance and uncollected-query lists make the actual capture auditable. Search completion does not establish complete hub timetables.
