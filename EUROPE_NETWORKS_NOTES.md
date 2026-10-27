# Additional European airline networks

Expands the existing **Europe · Flights** view on **2 November 2026** with nine networks: **SAS (SK), Norwegian (DY/D8), Finnair (AY), LOT Polish Airlines (LO), TAP Air Portugal (TP), Aegean/Olympic Air (A3/OA), airBaltic (BT), Icelandair (FI) and ITA Airways (AZ)**. Existing Ryanair, easyJet, Wizz and nine flag-carrier records remain intact. Carrier codes identify returned source records, not independently verified operating aircraft or inferred codeshares.

## Efficient search footprint

Published exact-airport pairs come from pinned [Great Circle Pro carrier-map SVGs](https://www.gcpromap.com/assets/images/airlines/carriers/sk-routes.svg). Their descriptions, file hashes, source URLs and IATA code-directory references are saved in `data/sources/europe_networks_discovery.json`. Each map pair supplies two directional search candidates; neither direction is assumed to operate on the replay date. No hub-to-all-destinations expansion, all-airports Cartesian product or per-airline duplicate searches.

| Network | Directional candidates |
| --- | ---: |
| SAS | 564 |
| Norwegian | 764 |
| Finnair | 246 |
| LOT | 238 |
| TAP | 216 |
| Aegean/Olympic | 356 |
| airBaltic | 258 |
| Icelandair | 134 |
| ITA | 228 |

Overlapping airline candidates share **2,578 unique airport directions**. **496 compatible EUR captures** are reused directly, leaving **2,082 new searches**. One origin-local departure date only, two workers, resumable caches and an exclusive collection lock. Access challenges stop collection and retain successful captures. Routes with neither endpoint in the reviewed European footprint are excluded.

The Olympic Air **OA map returned HTTP 404**. Aegean's published pairs can still return OA-coded flights, but this is not a complete standalone Olympic inventory. The retired **ALY** identity was absent from the pinned active-airport catalogue and its candidates were excluded; it was never substituted with **HBE**. Seasonal, historical and future map routes remain candidates only. Empty queries mean **not returned**, never **no service**.

## Sources, clocks and fares

Pinned OurAirports identities and the identity-matched timezone catalogue supply exact airports, coordinates and IANA zones. Existing Europe airport identities and zones must agree during merging. Additional explicit zones cover GZP, JJU and KUS; Qaqortoq's current airport remains distinct from the retired heliport identity. LHR/LGW, FCO/CIA, ARN/other Stockholm airports, KEF/RKV and separate Greek island airports are never replaced with city-wide codes.

The existing Europe policy remains: **UTC midnight-to-midnight replay**, airport-local boards, and **2 November in each origin's local time** for new searches. Explicit next-day arrivals and durations from one minute to 24 hours must validate against source duration and dated airport clocks. No extra departure dates are searched; prior-local-day carry-ins and next-local-day departures can therefore be missing at the UTC edges. Previous Europe captures retain their original clock interpretation, including Canadian endpoints; the separate Canada view's dated overrides do not reinterpret these archived records.

New and reused fares use **EUR, one adult, economy, one way**. Cheapest verified quotes are attached only to the exact source flight and schedule. Existing captures are read in place with their original timestamp, context and page hash, without copying raw cache trees or relabelling currencies. Unverified/missing quotes remain unavailable. Unknown aircraft stay unknown. Distinct flight numbers stay distinct, and frequency lines count captured identities rather than a deduplicated physical-aircraft census.

Discovery cross-checks: [Finnair destinations](https://www.finnair.com/en/destinations), [SAS routes](https://www.flysas.com/en/flight-routes), [LOT destinations](https://www.lot.com/gb/en/flights) and [TAP destinations](https://www.flytap.com/en-us/destinations). Destination marketing lists are not converted to guessed airport pairs.

## Integration and rebuilding

Adds individual network and source-code filters to the existing Europe controls, with stable network colours. The three existing group filters keep their reviewed nine-carrier roster; new networks are not assigned to ownership groups by inference. Airport/country filters, domestic/international scopes, departures, arrivals, Destinations, fullscreen boards/back, frequency lines, themes and English/Indonesian copy remain shared. The map initially frames Europe and fits external destinations on selection. Country views, Europe–Americas and the shared International network retain their existing archives.

```bash
# Pin published maps; successful local map files are reused.
.venv/bin/python scripts/discover_europe_networks.py
# Rebuild the normalized manifest offline from pinned discovery.
.venv/bin/python scripts/prepare_europe_network_routes.py
# Inspect the exact single-date cache budget.
.venv/bin/python scripts/prepare_europe_networks.py --dry-run
# Collect missing queries only, two workers.
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_europe_networks.py --collect-only
# Rebuild all old and new cohorts offline from their frozen inputs/captures.
.venv/bin/python scripts/prepare_europe_networks.py --prepare-only
```

New captures: `.cache/google-flights-europe-networks-eur-v1/`; existing EUR fallback caches: `.cache/google-flights-europe-groups-eur-v1/` and `.cache/google-flights-europe-eur-v1/`. Reuse requires exact airport/date, reviewed capture context and no rejected source rows. Mixed or incompatible contexts require a fresh query; unknown parsers are never accepted. The ordinary Ryanair and group preparation commands also include this cohort when its manifest is present, so a later rebuild does not drop it.

Prepared output remains `data/reference/europe_flights/2026-11-02.json.gz`. Rebuilds use original frozen cohort inputs rather than merging repeatedly into a mutable previous archive. Gzip is deterministic, identities are sorted, and replacement is atomic. Raw caches are ignored by Git; deleting them leaves the committed replay working but requires deliberate recollection for a full rebuild.

## Actual coverage and validation

| Network | Flights | Domestic | International | Airports | EUR quotes |
| --- | ---: | ---: | ---: | ---: | ---: |
| SAS | 720 | 268 | 452 | 97 | 18 |
| Norwegian | 339 | 154 | 185 | 52 | 339 |
| Finnair | 316 | 88 | 228 | 70 | 316 |
| LOT Polish Airlines | 275 | 62 | 213 | 75 | 275 |
| TAP Air Portugal | 286 | 63 | 223 | 68 | 286 |
| Aegean / Olympic Air | 289 | 128 | 161 | 63 | 288 |
| airBaltic | 116 | 0 | 116 | 29 | 116 |
| Icelandair | 78 | 14 | 64 | 41 | 78 |
| ITA Airways | 262 | 163 | 99 | 42 | 262 |

The added cohort has **2,681 overlapping flights**, **1,978 verified EUR quotes**, **236 returned airports**, and **1104 returned directions**. Original source codes remain visible; these are source flight identities, not verified unique aircraft movements.

All **2,578/2,578** single-date queries were captured, including **496 reused** and **2,082 new** searches. **1,134** returned a target network, **186** returned only other airlines, and **1,258** returned no direct records. **0 rejected records**, **0 failed queries**, **0 unattempted queries**. Empty results and unreturned candidates remain source gaps.

Europe now has **13,073 flights across 478 returned airports and 124 countries/territories**, with **9,228 verified EUR quotes** and **6,210 distinct directions**. All **10,392 original records compare equal field for field**. New-cohort query subtotals overlap the earlier groups; overall source accounting has **14,367 unique dated Google captures**, separately from **5,305 monthly Ryanair timetable captures**.

Missing quotes remain unavailable, including unpriced SAS records; no connecting-trip total or route-wide minimum is substituted. Returned flights near UTC edges can be fewer than source-local-day flights because the existing Europe replay window stays unchanged. The missing OA map, excluded ALY candidates, unreturned destinations/carriers, seasonal routes and midnight boundaries remain explicit coverage gaps.

Archive: **1,661,584 bytes**, SHA-256 `1147ba93513dcd708ed25670a4d02306937936aa10a093c802593cb69ca6deab`. Offline reconstruction from pinned manifests and retained captures is byte-identical.

Validation includes single-date deduplication, cache compatibility and provenance, exact city airports, separate Iceland airports, overnight long-haul duration checks, missing and duplicate records, quote handling, preservation of earlier cohorts, HTTP caching/date rejection, and browser checks for all 21 brands, original codes, country scopes, local airport boards, fullscreen/back, frequency totals, themes, Indonesian, mobile and existing location regressions.

**172 Python tests and 106 JavaScript tests passed.** The full browser suite passed against all 13,073 records, including the new CPH, OSL, HEL, WAW, LIS, ATH, RIX, KEF, RKV and FCO boards. The final archive reproduced byte for byte. Audit logs and screenshots remain local under `.cache/europe-networks-audit/` and `.cache/europe-flights-audit/`.
