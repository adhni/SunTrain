# Türkiye flights

**Türkiye · Flights** is a partial, dated schedule replay for **2 November 2026 departures in each origin airport’s local time**, including dated overnight arrivals. The timeline uses **Europe/Istanbul / UTC+3**; airport boards use their own local clocks. This is not live tracking.

## Efficient footprint

- **IST and SAW:** published worldwide nonstop candidates, with both directions searched separately and all returned airlines eligible.
- **Domestic starter:** published pairs among **IST, SAW, ESB, ADB and AYT**. The maps supply **18 directions**, excluding an invented IST–SAW shuttle; this is not every domestic airport or route.
- **Existing captures:** compatible dated Turkish-endpoint captures beyond the starter remain available without new searches, including BJV and DLM international links.
- **One date only:** no adjacent-day, weekly, per-airline or Cartesian airport expansion. The initial reviewed budget was **840 total directions**, **142 compatible captures reused**, **698 missing queries**. New collection is restricted to 786 sourced starter directions; the other 54 directions are reuse-only and can never trigger a new search when their cache is absent.

The initial map stays over Türkiye. Selecting an airport fits its captured connections; **Fit selection** can reach overseas endpoints, and clearing the airport selection restores the country view. Reuses airline/code, airport and From/To country filters, Domestic/International/Both, local departures/arrivals, Destinations, fullscreen pagination, fare previews, frequency lines, airport visibility, themes and English/Indonesian copy.

## Sources and exact identity

[Discovery facts](data/sources/turkiye_flights_discovery.json) pin exact destination labels, SHA256 document hashes and the review timestamp for all five [Great Circle Pro airport maps](https://www.gcpromap.com/airports/ist/). Each inspected source describes the **July 2026–June 2027** period, updated **12 October 2026**. These are seasonal search candidates, not evidence of operation on 2 November. Reverse searches do not infer a return flight.

The [route manifest](data/sources/turkiye_flights_routes.json) records normalized evidence, previous source manifests, reusable capture paths, input hashes, deferred routes, exact airport identities and zones. The public [Turkish Airlines destination directory](https://www.turkishairlines.com/en-sg/flight-destinations/) provides a city-level cross-check; a listed destination does not itself establish an exact nonstop route or dated service. Both hubs include other returned carriers, including Pegasus and AJet; collection is not restricted to Turkish Airlines.

Airports come from the pinned OurAirports catalogue, with identity-matched OpenFlights IANA zone labels and explicit modern-airport overrides. **IST is LTFM**, the current Istanbul Airport; **SAW is LTFJ**, Sabiha Gökçen. Old Atatürk/ISL is not substituted for either. Coordinates and country identities are not merged by city. Türkiye’s zone is Europe/Istanbul; foreign airports keep their own zones, including **GNJ / Asia/Baku**. Overrides also distinguish **GSV / Europe/Saratov** from **GRV / Europe/Moscow**; an override does not bring a deferred route into the collection footprint. Source URLs, expected hashes and overrides are committed.

All five map sources were available. **ALY** has no unique active identity in the pinned catalogue and is omitted; it is not silently changed to HBE. Other Turkish domestic airports and international expansion from non-Istanbul airports are deferred unless already captured. The published timetable period and one-date collection leave seasonal and other-weekday gaps. Arrivals into Türkiye on 2 November whose overseas departure was on 1 November can also be absent; those extra departure dates are deliberately not collected. Empty results mean **not returned**, never “no service.”

The existing official Ryanair archive was audited for dated Turkish-endpoint records; none matched this date. Its hash and the empty reuse-route set are recorded. The preparer stops for review if a future manifest introduces such records rather than silently dropping them or treating them as Google captures.

## Dates, fares and provenance

Only records with dated departure and arrival timestamps are retained. Source-local clocks must match the published duration. The shared parser permits one minute through 24 hours for this profile, leaving other profiles’ limits unchanged. Every departure must belong to **2 November locally at its origin**. The replay window includes the whole set of those local days and their overnight arrivals; a board’s displayed range can therefore span more than one local date without extra-day searches.

Exact flight identities include date, flight number and both airport codes. Identical repeats collapse; conflicting records fail validation. Distinct flight numbers remain distinct; matching times are not used to infer codeshares. Missing aircraft remain unknown. Paths are illustrative arcs.

New missing searches request **USD, one adult, economy, one way**. The lowest verified returned offer for the exact nonstop flight is selected; connecting itinerary totals are excluded. Missing/unverified quotes stay unavailable. Compatible reused quotes retain their original currency, amount, source timestamp and context, with no conversion or relabelling. Prices are captured quotes, not live fares; optional charges and baggage can cost extra.

Seeding selects the latest compatible complete query by timestamp, not a mix of different schedule captures. Reused files are copied without changing their original caches; source paths and byte hashes accompany the copies. Empty older eight-hour-parser searches cannot establish an empty long-haul result, so incompatible captures remain missing rather than becoming false negatives.

The shared **International network** and existing country snapshots remain unchanged. This standalone view does not invoke the older multi-day network collector.

## Collection and offline preparation

```bash
# Refresh published candidate facts only when intentionally reviewing sources:
.venv/bin/python scripts/discover_turkiye_flights.py

# Build exact candidates from frozen discovery, pinned catalogues and existing captures:
.venv/bin/python scripts/prepare_turkiye_routes.py

# Seed compatible cached captures and inspect the one-date search budget:
.venv/bin/python scripts/prepare_turkiye_flights.py --seed --dry-run

# Resume missing queries only, at two concurrent searches:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_turkiye_flights.py

# Rebuild offline from the captures:
.venv/bin/python scripts/prepare_turkiye_flights.py --prepare-only
```

`PYTHONPATH` is only needed when Playwright lives in the local `.cache/browser-tools` installation. The route builder reads the pinned CSV at `.cache/australia-flights-audit/ourairports-airports.csv` and OpenFlights data at `.cache/gulf-flights-audit/openflights-airports.dat`; their download URLs and SHA256 hashes are in the manifest. The committed manifest makes runtime replay and offline preparation independent of those catalogue downloads.

Resumable captures live in `.cache/google-flights-turkiye-usd-v1/`; new USD captures use its `new-usd/` directory to keep parser/fare contexts separate from reused captures. Writes/imports are atomic. Challenges stop collection without retries; successful captures, failed-query files and stop reasons are retained. Preparation reports captured, unreturned, failed, rejected and unattempted queries separately, validates the result, then atomically publishes deterministic gzip (`mtime=0`) at `data/reference/turkiye_flights/2026-11-02.json.gz`.

## Actual coverage and validation

The frozen snapshot contains **1,662 unique flight identities across 73 carrier codes**:

| Scope | Flights | Directions returning flights | Priced flights |
| --- | ---: | ---: | ---: |
| Domestic | 206 | 17 | 206 |
| International | 1,456 | 612 | 1,408 |
| Total | 1,662 | 629 | 1,614 |

- **840/840 directional queries captured:** 142 reused and **698 newly collected**. **211** did not return flights. There were **zero failed, rejected or unattempted queries/records**.
- **239 airports** returned flights out of 300 catalogued, spanning **107 country/territory codes**. All seven Turkish airports in the catalogue returned flights: the five starter airports plus reused BJV/DLM captures. Foreign airports with no returned flights remain selectable.
- Prices: **1,437 USD**, **171 EUR**, **6 MYR**; **48 flights** have no verified quote. All 206 captured domestic flights have verified USD prices.
- All **38** dated Türkiye-endpoint identities in the existing Europe snapshot are retained. Original source snapshots and caches are unchanged.
- **137,643 bytes / about 134 KiB gzip**, reproduced byte-for-byte offline. SHA256: `58872e253033789c1b9b205f474f84d10f4a8ce1b482ea492e1a51868ed25c91`.

Domestic coverage is limited to the starter; wider Turkish domestic routes remain a gap. Other Turkish airports’ newly discovered international routes were deferred rather than searched. Seasonal, other-weekday and previous-day-arrival gaps remain. Completing the candidate queries does not establish nationwide or worldwide completeness.

Validation covers exact IST/SAW identity, sourced footprint restrictions, no invented IST–SAW route, one origin-local date, Turkish year-round UTC+3 and foreign-zone duration checks, overnight/short/long flights, original currencies, source immutability, duplicate identities, missing queries, HTTP gzip/ETag/date rejection, retained Europe identities, and translated notes. Browser checks cover all five starter boards, domestic/international/country/carrier filters, departures/arrivals, Destinations, fare previews, fullscreen/back, frequency counts, airport visibility, themes, Indonesian, mobile, and existing Africa/Europe/Americas/Australia/Melbourne views. Final validation passed: **357 Python tests**, **105 JavaScript tests**, and the complete Türkiye plus existing-view browser checks.
