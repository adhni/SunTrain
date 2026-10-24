# Australian international flights — 2 November 2026

A dated schedule replay alongside the existing Australian domestic snapshot. It is not live tracking or a claim of complete flight coverage. Australia opens in Domestic; International and Both reuse the same compressed day payload. Airport boards use their own local dates and time zones; the timeline is midnight-to-midnight Australia/Melbourne. The historical March 2013 Jetstar reference remains isolated from the 2026 international supplement.

## Targeted search strategy

Start with BITRE's July 2026 **passenger** city pairs (Table_5), published 14 October 2026. Rows with no positive July 2026 passenger count are excluded; the national total and freight-only routes are not turned into searches. City-pair statistics are historical candidates and can include intermediate stops. They do not establish a current nonstop service.

- Workbook: <https://www.bitre.gov.au/sites/default/files/documents/International_airline_activity_0726.xlsx>
- SHA-256: `ea1c46bd8c436f713fa0d1b0354da8afc3b76e3efb2ce2b403339885ee4c2c25`.
- Exact airport catalogue: the existing pinned OurAirports commit and checksum, recorded in `data/sources/australia_international_routes.json`.
- Explicit city-to-airport mapping keeps HND/NRT, PEK/PKX, TFU/CTU, BKK/DMK and PVG/SHA separate. Searches always use individual IATA codes.
- Only source-backed pairs are searched in both directions. There is no Cartesian product of Australia's domestic airports with overseas airports.
- Published airport supplements include AVV–DPS, HBA–AKL, WSI–AKL and seasonal ADL–CHC and the Qantas-listed PER–CDG pair. Qantas notes rerouting in the northbound direction, so both directions are checked independently. MEL/AVV and SYD/WSI remain distinct.
- NTL/MCY–SIN via Bali are not searched as nonstop routes; NTL/MCY–DPS are searched. Published WSI–SIN starts after the replay date; ADL–SFO's December–February season is outside this date. ADL–HKG and MEL–ICN have published seasonal returns after the replay date and are excluded too. These exclusions and their official sources are stored in the manifest.
- Broome's `International` airport name alone does not establish scheduled international passenger service. Its July 2026 passenger count is zero; no all-destinations Broome search is generated.

The initial manifest contains 14 Australian candidate airports: ADL, AVV, BNE, CBR, CNS, DRW, HBA, MCY, MEL, NTL, OOL, PER, SYD and WSI. Airports that return no flights are documented gaps, not proof of no service. A WSI service announcement is a candidate, never a fabricated timed flight.

## Collection and reproducibility

`prepare_google_flights.py --country AU --scope international` reuses the country/scope collector. Australia's existing domestic CLI defaults, captures and reference bytes are unchanged. The maximum accepted international segment duration is 24 hours; the source's stated duration must agree with UTC timestamps. Unspecified aircraft remain unknown. Repeated flight identities are deduplicated; distinct source flight numbers are retained without inferring codeshares.

For each pair, query origin-local dates covering every departure instant that could overlap the selected Melbourne day, allowing up to 24 hours for carry-ins. This includes dates before the Australian day and next-day dates in New Zealand/Pacific origins. Selection is by UTC, not a comparison of local calendar dates. Arrival boards own events at the starting midnight and exclude the ending midnight.

Collection uses two searches concurrently, a resumable cache and atomic capture writes. Existing exact-airport/date Indonesian international captures are reused when applicable; their original URLs, timestamps and source hashes remain attached. Each new capture records its URL, capture time, source-script hash and status. Challenges stop collection; unsuccessful queries remain explicit. Empty results mean not returned, never no service.

```bash
# Preparation-only openpyxl and Playwright packages are in existing ignored tool folders.
PYTHONPATH=.cache/excel-tools .venv/bin/python scripts/prepare_australia_international.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_google_flights.py --country AU --scope international --concurrency 2
# Offline, deterministic preparation from captures already held locally:
.venv/bin/python scripts/prepare_google_flights.py --country AU --scope international --prepare-only
```

Manifest: `data/sources/australia_international_routes.json`.
Capture cache: `.cache/google-flights-australia-international/`.
Prepared supplement: `data/reference/australia_flights/2026-11-02-international.json.gz`.
Override: `SUNTRAIN_AUSTRALIA_INTERNATIONAL_REFERENCE`.
A custom `SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE` fixture stays isolated unless the international override is also explicit. Runtime requests never make external flight searches.

## Map and exploration

Reuse airline-code and exact-airport filters, Departures/Arrivals/Both, Destinations, full-day connection drill-down, fullscreen boards, explicit timeline seeking and frequency lines. Selecting an airport hides unrelated planes. Frequency counts represent captured events inside the selected replay day, with arrivals including overnight carry-ins.

Pacific illustrative arcs use continuous longitudes across the date line; interpolation and plane headings cannot jump across the world. Both directions use the same world copy, and Fit selection centres a Pacific connection over the Pacific. Normal Australian and Indonesian routes retain their existing coordinates. Carrier colours are stable with a deterministic fallback for unfamiliar carriers. English and Indonesian copy, themes and mobile layouts reuse the shared flight UI.

## Actual coverage and validation

Final collection counts and airport-level gaps are recorded below. Query completion must not be described as nationwide completeness. Only captured dated flights are displayed; empty/missing searches and seasonal or unreturned airport candidates remain gaps.

### Prepared capture results

- 86 airports planned/searched: 14 Australian candidates and 72 overseas candidates.
- 402 directional airport pairs searched; 318 returned flights on at least one queried origin-local date; 268 have flights overlapping the selected Melbourne day.
- 1089/1089 query captures; 387 not-returned results; 0 failed, 0 pending; 0 rejected source records. No unresolved airport identities.
- **605 captured departures inside the replay day + 168 carry-in records = 773 overlapping flight records**.
- 64 represented airports: 11 Australian + 53 overseas; 57 carrier codes. Distinct flight numbers remain separate records and must not be interpreted as independently verified physical aircraft or inferred codeshares.
- Initial collection reused 48 exact-airport/date Indonesian captures. New queries were capped at two concurrent searches; the long-haul/date-line pilot was reused by the main pass. Final offline preparation is deterministic.
- Prepared supplement: 85,482 bytes gzip; SHA-256 `bf17d38d23d7710bdaed70c39b6a2c9d2da1d7145ced74ccb03ca6c05fc301d2`. The existing Australian domestic and historical snapshots are unchanged.

All event counts below use the **Melbourne replay day's UTC interval**, displayed locally on airport boards. They are captured schedule counts, not a measure of full airport activity.

| Australian airport | Outbound candidate destinations | Captured departures inside day | Captured arrivals inside day | Overlapping records, either direction |
|---|---:|---:|---:|---:|
| ADL | 11 | 11 | 11 | 26 |
| AVV | 1 | 1 | 1 | 3 |
| BNE | 36 | 49 | 49 | 115 |
| CBR | 2 | 1 | 0 | 1 |
| CNS | 9 | 7 | 6 | 16 |
| DRW | 4 | 5 | 3 | 8 |
| HBA | 1 | 0 | 0 | 0 |
| MCY | 2 | 1 | 1 | 2 |
| MEL | 43 | 74 | 78 | 197 |
| NTL | 1 | 0 | 0 | 0 |
| OOL | 8 | 8 | 7 | 16 |
| PER | 21 | 39 | 40 | 103 |
| SYD | 61 | 108 | 109 | 286 |
| WSI | 1 | 0 | 0 | 0 |

HBA, NTL and WSI have no retained overlapping flights in this day. This can reflect sparse weekday schedules, results outside the replay window or unreturned searches, and does not establish that the airport has no international service. Their source-backed candidates and all query statuses are retained in the manifest and capture cache. PER–CDG is not returned in either direction; the published route information does not justify inventing a timed flight.

The 387 empty captures mean **not returned**. They include exact-airport alternatives, historical city-pair candidates, non-daily routes and advertised links that may operate with stops. The reference is neither a worldwide network search nor a complete census of Australian international flights. The public result set may omit flights; no paid schedules, live tracking, automatic refresh or frequency-only invented timings are included.

### Validation

100 focused Python tests and 82 JavaScript tests passed. These cover exact airport identities and the restricted gateway manifest, source-local query windows, US daylight saving, Pacific date reversal, continuous/reversible illustrative arcs, merged scope loading and custom-fixture isolation, HTTP revisions/caching and date rejection, deterministic preparation, coverage gaps and the retained Australian/Indonesian snapshots.

Chrome checks passed for the final Australian international snapshot (real scope control, Pacific movement and fit, cached filters, foreign airport-local boards, fullscreen/back, arrival frequency, themes, Indonesian, mobile and Overview), existing Australian domestic behaviour including Perth clocks and return to Melbourne transit, and all seven Indonesian international dates. Existing domestic and March 2013 reference files have no changes. The international gzip was reproduced byte-for-byte from the cached captures with no collection or network requests.
