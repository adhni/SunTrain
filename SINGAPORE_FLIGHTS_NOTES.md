# Singapore flights

Bismillah, **Singapore · Flights** adds international scheduled passenger flight captures for **2 November 2026**, keeping the existing Singapore transport replay separate.

## Experience

Changi **SIN** opens first. **SIN / XSP / All airports** shortcuts apply the existing airport filter; the last clears airport and route filters while preserving the airline selection. Exact airport selection hides unrelated traffic. **Airport traffic → Departures / Arrivals / Both** controls the matching endpoint. Seletar **XSP** is never merged into SIN, and Subang **SZB** is never merged into KUL. The same departures/arrivals, Destinations tab, flight previews, fullscreen boards and fixed-day frequency map are reused. Five themes and English/Indonesian apply.

The midnight-to-midnight timeline uses **Asia/Singapore (SGT, UTC+8)**. Airport boards use their own IANA zones and display the actual board window in local dates. Adjacent origin-local days are searched to retain overnight and long-haul flights overlapping that Singapore day, including departures on the preceding local day. Only dated records with source-validated durations from one minute to 24 hours are kept. Paths are illustrative, not live flight tracks. Unspecified aircraft remain unknown.

## Candidate sources and airport identity

The reviewed manifest, `data/sources/singapore_international_routes.json`, has **187 candidate airports**, **372 directional routes** and **859 origin-local airport/date queries**. Both directions of each exact pair are searched. No domestic Singapore routes are invented.

- [Singapore Airlines destination directory](https://www.singaporeair.com/sg/en/plan-travel/destinations/): curated entries explicitly labelled SQ/TR, excluding its large partner-only connecting network. Entries are candidates, not evidence of a dated nonstop flight.
- [Scoot August 2026 network map](https://cdn.flyscoot.com/prod/images/default-source/where-we-fly/scoot-network-aug26.webp), linked by its [public destination map page](https://www.flyscoot.com/en/discover/plan-your-next-trip/destination-map): newer regional entries and exact-airport resolutions of map labels.
- [Seletar’s commercial passenger guide](https://www.seletarairport.com/commercial-flights.html): its published Firefly/Subang route, searched as **XSP–SZB** and **SZB–XSP**. SIN is not substituted if XSP returns nothing. This is a schedule snapshot; it does not infer daily operation from undated route advertising or reconstruct disruptions.
- Reciprocal Singapore pairs from the existing Australian, Indonesian, Malaysian and Gulf manifests, plus explicitly labelled probes for other carriers and newer gateways. Probe inclusion is not proof of published or current service.

Metropolitan codes such as NYC, TYO and BJS are not queried: EWR/JFK, HND/NRT and PEK/PKX remain separate exact airports. Airport identities and coordinates use the existing pinned OurAirports source. Time zones reuse the verified existing catalogues and the pinned OpenFlights file used by the Gulf collector, with ICAO matching; modern-airport overrides are explicit in the manifest. Source URLs, reviewed date, airport/timezone source hashes and per-pair evidence are retained. The route evidence hash covers curated candidates and probes, not raw website bytes. An empty result means **not returned**, never “no service”.

## USD fares and capture reuse

All new searches request **USD, one adult, economy, one-way**. Fare context is checked before retaining the lowest positive quote linked to the exact flight identity. A page-wide minimum or connecting itinerary total is not assigned to an individual flight. Original currency, minor units and capture timestamp are retained; no conversion or relabelling of MYR/SGD prices occurs. Missing or uncertain quotes show **Price unavailable**. Optional baggage and charges may cost extra; these are dated quotes, not live fares.

Thirteen compatible exact-airport/date **USD** captures were reused from the Gulf cache. Reuse requires the query date and airports to be in Singapore’s manifest, the original query currency to be USD, and any retained prices to be USD. Capture timestamps and fare errors are preserved. The full origin-local day captures are filtered afresh to the Singapore replay window; the Gulf’s four-hour-later window is not copied. Malaysia’s MYR captures and unpriced searches with unverified query currency are not reused.

Repeated source identities are deduplicated. Distinct flight numbers stay distinct even with matching times; codeshares are not inferred. The loader rejects conflicting airport identities, unrelated foreign-to-foreign flights and non-USD prices.

## Rebuilding

```sh
.venv/bin/python scripts/prepare_singapore_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_singapore_flights.py
# Rebuild from cached captures without searching:
.venv/bin/python scripts/prepare_singapore_flights.py --prepare-only
# Reproduce to another output for byte comparison:
.venv/bin/python scripts/prepare_singapore_flights.py --prepare-only --output /tmp/suntrain-singapore-flights.json.gz
```

The collector uses **two concurrent public searches total**, atomic resumable JSON captures and the existing collection lock. Cache: `.cache/google-flights-singapore/`. It stops on search access challenges and retains successful captures and missing-query reports; do not retry or bypass an access challenge. Ordinary failures remain reported until resolved. Preparation writes deterministic `data/reference/singapore_flights/2026-11-02.json.gz`. `SUNTRAIN_SINGAPORE_FLIGHTS_REFERENCE` overrides that bundle. The app uses the existing compressed HTTP replay cache and never searches at runtime. No paid source, live tracking or automatic refresh is introduced.

The preparation-only Scoot map is about 467 KiB; its public URL above allows downloading again if its ignored cache is removed. Airport and timezone downloads reuse existing pinned caches; no new runtime dependency is required.

## Captured coverage

All **859 planned exact-airport/date queries**, **372 directional candidate routes** and **187 candidate airports** were searched. Thirteen compatible USD captures were reused; 846 new searches completed with **zero failed/missing queries**, **zero unresolved airport identities** and no access challenges. Captures span **24 October 2026 23:37 UTC – 25 October 2026 03:50 UTC** (all on 25 October in Melbourne and Singapore); each fare retains its own original timestamp.

The replay contains **1,101 overlapping flights**, **249 directional routes**, **136 airports**, **46 airport-country codes** and **76 carrier codes**. There are **979 USD fares** and **122 unavailable prices**. All query fare contexts were verified; an exact-flight quote was not returned/retained for those 122 flights. No source records failed duration/identity validation.

| Airport | Overlapping flights | USD fares | Unavailable prices | Directional routes |
| --- | ---: | ---: | ---: | ---: |
| Changi SIN | 1,089 | 967 | 122 | 247 |
| Seletar XSP | 12 | 12 | 0 | 2 |

Seletar’s retained services are Firefly flights to/from **SZB**. Singapore’s **SIN–SZB** flights remain separate from **XSP–SZB** throughout the map, filters and boards.

**294 queries returned no matching direct flight records**; this means “not returned”, never “no service”. Some candidates returned flights on adjacent dates but none overlapping this replay day. Fifty-one candidate airports have no retained overlapping flight. Candidates include historical, seasonal, upcoming and partner/other-carrier probes; completing the manifest does not establish complete Changi or Seletar timetables. Weekly services on other dates, Google omissions and unreturned fares remain gaps. No timings or prices were invented to fill them.

The prepared bundle is **94,583 bytes (about 92 KiB)** and rebuilds byte-for-byte from cached captures. Query URLs, timestamps, source hashes, statuses, fare diagnostics and missing-query lists are retained in the reference metadata; route evidence and airport/timezone pins are in the manifest.
