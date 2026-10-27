# Pakistan and Bangladesh flights

Neither country previously had a standalone flight view; their airports appeared as foreign endpoints in other captures. These additions provide separate **Pakistan · Flights** and **Bangladesh · Flights** for **2 November 2026 departures in each origin airport's local time**, including dated overnight arrivals. This is a partial schedule replay, not live tracking or observed operations.

Pakistan uses **Asia/Karachi / UTC+5**; Bangladesh uses **Asia/Dhaka / UTC+6**, year-round. Foreign airport boards keep airport-local time. Reuses compact planes, domestic/international scope, airline/airport/country filters, departures/arrivals, Destinations, fullscreen, fare previews, frequency lines, themes and English/Indonesian copy. Both countries start fitted to their own bounds.

## Sourced scope

- Pakistan reviews **23 civilian airport candidates**, including regional airports, Gilgit, Skardu and the current Gwadar airport. Published domestic candidates comprise **46 directions across 15 airports**. International candidates come from published maps and existing sourced manifests, with compatible positive captures beyond the footprint retained as reuse-only.
- Bangladesh reviews **eight scheduled-airport candidates**: DAC, CGP, ZYL, CXB, JSR, RJH, SPD and BZL. **22 domestic directions** include Dhaka spokes and eight additional directional candidates from an official historical passenger-route table: CXB↔CGP, CXB↔SPD, CXB↔ZYL and CGP↔ZYL. Historical routes are candidates, not proof of service on the replay date.
- No Cartesian airport expansion, per-airline, adjacent-day or weekly collection. Initial map-based budget was **362 country-direction entries**, **177 cached**, **185 new searches**; the historical Bangladesh supplement adds eight candidates. Countries run sequentially, with two searches concurrent and another cache-seeding pass before each country.

Exact modern identities use pinned OurAirports data and identity-matched OpenFlights zones, with explicit national IANA overrides. **ISB/OPIS** is the current Islamabad airport; the former airport is not substituted. **GWD/OPGW** is the pinned New Gwadar airport, not the old airport's coordinates. **DAC/VGHS**, **CGP/VGEG** and **ZYL/VGSY** remain distinct, including historical spelling variations such as Chattogram/Chittagong and Jashore/Jessore. Source hashes and foreign-zone overrides are pinned in the manifests.

Great Circle Pro maps were available for [Karachi](https://www.gcpromap.com/airports/khi/), [Islamabad](https://www.gcpromap.com/airports/isb/), [Lahore](https://www.gcpromap.com/airports/lhe/) and [Dhaka](https://www.gcpromap.com/airports/dac/). These secondary maps describe July 2026–June 2027, updated 12 October 2026. The other **20 Pakistani and seven Bangladeshi map pages returned 404**. Missing local maps can hide additional regional routes even when the airport appears as a hub-map destination.

Official [PIA domestic destinations](https://www.piac.com.pk/where-we-fly/destinations/domestic-destinations), [Fly Jinnah domestic routes](https://www.flyjinnah.com/en/landing-pages/pakistan-domestic-routes) and [Biman domestic destinations](https://biman-airlines.com/destinations-domestic) were inspected as network cross-checks. Frequency-only statements do not become invented timings. Bangladesh's supplement uses government **table 7.28, Passenger Movement by Bangladesh Biman**, with route statistics through 2023–24, published at [the government statistics PDF](https://file-chittagong.portal.gov.bd/uploads/81db240c-6dae-45b9-b738-2ae6a3ee3ec2/68c/a7a/ecb/68ca7aecb0d2b352134283.pdf). Exact city-pair facts were reviewed through public web-tool text and explicitly mapped to IATA codes. Direct PDF retrieval reset the connection; discovery records hash the normalized facts and do not claim an original-PDF hash.

Frozen discovery and route manifests record candidates, evidence, timestamps, reuse sources, missing map pages and unresolved airports. Empty Google results mean **not returned**, never **no service**. Airport catalogue flags and seasonal/historical route maps are not current flight evidence. Regional, seasonal, other-weekday and previous-day-arrival gaps remain; query completion is not nationwide completeness.

## Capture, fares and reproducibility

Exact IATA Google Flights queries request **one adult, economy, one way, USD**. Only dated departure/arrival records are included. Local clocks must agree with source duration, between one minute and 24 hours. Identical source identities collapse; conflicting records fail; distinct flight numbers remain separate without inferred codeshares. Unknown aircraft stay unknown. Paths are illustrative.

The cheapest verified returned offer per exact nonstop flight is retained; connecting itinerary totals are excluded. Original reused USD/EUR/MYR quotes retain their currency, amount, timestamp and context. Missing/unverified quotes stay unavailable; no currency conversion or relabelling. Captured prices may change and exclude optional charges. Source challenges stop collection without retries, retaining successful captures and reporting missing queries.

```bash
.venv/bin/python scripts/discover_pakistan_bangladesh_flights.py
.venv/bin/python scripts/prepare_pakistan_bangladesh_routes.py
.venv/bin/python scripts/prepare_pakistan_bangladesh_flights.py --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_pakistan_bangladesh_flights.py
.venv/bin/python scripts/prepare_pakistan_bangladesh_flights.py --prepare-only
```

Discovery refresh preserves reviewed historical supplements. Caches: `.cache/pakistan-bangladesh-flights-audit/` and `.cache/google-flights-{pakistan,bangladesh}-usd-v1/`, with new USD queries under `new-usd/`. Sources are copied intact; originals stay untouched. Prepared bundles: `data/reference/{pakistan,bangladesh}_flights/2026-11-02.json.gz`. Gzip uses `mtime=0` and is validated before atomic publication. Runtime reads the bundles without searches. Existing countries and the shared International network are unchanged; the original Arabia/Jordan CLI defaults are preserved.

## Actual capture and validation

| View | Flights | Domestic | International | Priced | Returning directions | Captured queries | Reused queries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Pakistan | 293 | 64 | 229 | 289 | 144 | 260 | 124 |
| Bangladesh | 243 | 99 | 144 | 163 | 70 | 110 | 55 |

These are per-view counts; the countries share some international flight identities. **370/370 country-query entries were captured**, with **179 reused entries** and **191 new searches**, plus **one targeted verification query**. Two Pakistan captures were reused when Bangladesh started, saving two searches. No failed, rejected or unattempted queries/records remain. Pakistan had **116** empty directional results; Bangladesh **40**.

Pakistan returned domestic flights at **nine airports**: ISB, KDU, KHI, LHE, LYP, MUX, PEW, SKT and UET. The wider 23-airport catalogue includes unreturned airports. Gilgit, Gwadar and other uncaptured regional services remain gaps, not proof of no service. Skardu→Karachi was checked once because the reverse returned flights; it remained empty. The prior query and verification hashes/timestamps/counts are recorded in snapshot metadata, with original files under `.cache/pakistan-bangladesh-flights-audit/domestic-rechecks/pakistan/originals/`.

Bangladesh returned domestic flights at **six airports**: CGP, CXB, DAC, RJH, SPD and ZYL. BZL and JSR did not return flights. The eight historical regional directions did not return flights either; no historical timetable was promoted to current service. Its **43 domestic records without verified fares** are retained as schedules with unavailable prices. All 64 Pakistani domestic records have verified USD fares.

Prices: Pakistan **288 USD / 1 EUR**, four unpriced records; Bangladesh **155 USD / 8 MYR**, 80 unpriced records. New queries request USD; original reused currencies are unchanged. Pakistan returned flights across **36 of 59 catalogued airports**; Bangladesh **33 of 45**.

- Pakistan gzip: **37,687 bytes**, SHA256 `a71fea78ecb7dcf36a33ccc183ba0fdcb70b57d31f2d6e72ce91d860555903de`.
- Bangladesh gzip: **21,603 bytes**, SHA256 `c77ec5eec42ec058c960d4c88663e90999757dbe8663d7d6f2211ebc82164258`.

Both bundles reproduce byte-for-byte offline. Validation passed: **136 Python tests** across Pakistan/Bangladesh, Arabia/Jordan, Saudi, Türkiye, Africa, shared Google parsing/fares, Europe, Australia and replay HTTP; **105 JavaScript tests**; and byte-identical offline rebuilds of both new archives. Browser checks passed for every returned national airport board, both country maps, scopes, airport/carrier filters, departures/arrivals, Destinations, fullscreen, frequency totals, all five themes, Indonesian, mobile, and existing Oman/Jordan/Saudi/Türkiye/Africa/Melbourne views. Existing country reference files are unchanged.
