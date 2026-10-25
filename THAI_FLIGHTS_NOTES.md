# Thailand flights: domestic now, international next

## Domestic release

Choose **Thailand · Flights** for the **2 November 2026** dated schedule snapshot.
The midnight-to-midnight timeline and airport boards use **Asia/Bangkok, ICT
(UTC+7)**. Fares are the lowest returned positive **USD** quotes for one adult,
economy, one-way, with original capture timestamps. Missing offers remain
unavailable; THB prices are never relabelled or converted. Paths are illustrative,
not recorded flight tracks, and the app performs no live searches or refreshes.

**BKK (Suvarnabhumi) and DMK (Don Mueang) stay separate**, including searches,
filters, boards and flight identities. The release reuses moving planes, airline
codes and exact-airport filters, departure/arrival boards, fullscreen/back and
pagination, Destinations, fare previews without implicit seeking, frequency
lines, airport visibility, themes, English/Indonesian and mobile layout.
International/Both controls remain hidden. Existing Thailand SRT and Bangkok rail
views are separate and retain their original source periods and data.

The manifest contains **30 airports and 112 directional search candidates**:

| Region | Selected airports |
| --- | --- |
| Central | BKK, DMK, HHQ |
| North | CNX, CEI, LPT, NNT, PHS, MAQ, THS |
| Northeast | UTH, UBP, KKC, KOP, SNO, ROI, BFV, LOE |
| East | UTP, TDX |
| South | HKT, KBV, USM, URT, NST, HDY, TST, NAW, CJM, UNN |

Smaller/commuter services such as HGN and PRH are deferred. This is a selected
domestic network, not a claim that all Thai airports, airlines or flights are covered.
No BKK–DMK flights or all-pairs regional searches are invented.

## Sources and preparation

- OurAirports pinned commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
  `a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies exact
  airport codes, identities and coordinates; every selected airport explicitly uses
  Asia/Bangkok.
- [AirAsia's 1 October 2026 BKK reopening and domestic hub list](https://newsroom.airasia.com/news/airasia-is-back-at-suvarnabhumi-direct-flights-resume-oct-1-to-chiang-mai-krabi-and-phuket)
  distinguishes BKK/DMK and lists Chiang Mai's cross-country routes. A small set of
  additional DMK regional and BKK/HKT probes is labelled **supplemental**, not
  represented as published route pairs or proof of current service.
- [Thai Airways' official domestic destination directory](https://www.thaiairways.com/en-bd/content/where-we-fly/thailand/)
  supplies the core BKK network. Unofficial lookalike booking sites are not sources.
- [Bangkok Airways' older Airpass route table](https://www.bangkokair.com/eng/discovery-airpass/route-fare)
  supplies historical Samui, Trat, Sukhothai, Lampang and regional route candidates.
  It is not evidence of November operation. Product prices and timetable assumptions
  are never copied. Bangkok Airways' Bangkok endpoint is explicitly BKK.
- [U-Tapao's domestic timetable page](https://www.utapao.com/apps/domestic.php)
  supplies UTP candidates. Its undated clocks/frequencies never create replay flights.
- Exact-IATA Google Flights captures supply dated nonstop segments and verified
  fare context. Published lists, historical routes and empty searches never create
  flight timings. Empty results mean **not returned**, not **no service**.

Source evidence records each candidate's provenance and whether it is published,
historical or a supplemental probe. The curated evidence hash is not a raw-page
hash. Raw AirAsia/U-Tapao HTML pins are in the manifest; Thai Airways/Bangkok
Airways returned 403 to the local download client and were reviewed through the
web tool, without claiming raw-download hashes or bypassing access checks.

The two-worker collector searches **1 and 2 November**, keeping adjacent-day
flights overlapping the ICT day. Only dated departure/arrival records validated
against the source duration survive. The duration range is one minute to eight
hours. Repeated exact flight identities are deduplicated; distinct flight numbers
remain distinct without guessing codeshares. Unknown aircraft remain unknown.
Access challenges stop collection and retain captures/missing-query diagnostics.
Gzip uses stable ordering, fixed mtime and atomic replacement.

```bash
.venv/bin/python scripts/prepare_thai_flight_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_thai_flights.py --validate-only
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_thai_flights.py
.venv/bin/python scripts/prepare_thai_flights.py --prepare-only
```

Runtime reads `data/reference/thailand_flights/2026-11-02.json.gz`, overridable with
`SUNTRAIN_THAILAND_FLIGHTS_REFERENCE`. Normalized resumable queries live in
`.cache/google-flights-thailand/`; deleting those saves local storage but requires
new searches to rebuild. The committed replay continues working. OurAirports is
reused from `.cache/australia-flights-audit/` and can be re-downloaded from its pinned
URL. Curated manifest rebuilding needs no official-page downloads. Audit HTML,
test logs and browser screenshots stay in `.cache/thailand-flights-audit/` and
`.cache/thai-flights-*.png`. Generated replay HTTP caches regenerate.

## International plan — not executed in this release

1. **Start with existing flight locations.** Reuse the **176 directional candidates**
   already present in other countries' international manifests. Their Thai endpoints
   are BKK, DMK, HKT, CNX, CEI, HDY, KBV, URT and USM. Review current official
   airport/airline lists, prioritising BKK/DMK/HKT, then CNX/KBV/USM. Add UTP and other
   regional gateways only with explicit passenger-route evidence. Treat seasonal,
   announced, via-only and cargo routes as candidates or exclusions, not flights.
2. **Extend the shared network in one collection.** Add TH and the Thai view to the
   shared network's country/consumer configuration and manifest builder. Include
   only cross-country pairs within the existing flight footprint; Gulf endpoints
   remain DXB/AUH/DOH. Reuse exact airport/date raw captures from Australia,
   Indonesia, Malaysia, Singapore, India and Gulf caches, preserving timestamps and
   valid original USD/MYR context. Do not join prepared bundles with different UTC
   day windows or re-search successful captures merely for a price.
3. **Keep separate clocks and truthful prices.** Calculate the query union for the
   UTC network day, Thailand's ICT day and other country-local days, including
   adjacent origin-local dates with a 24-hour international duration ceiling.
   New queries request USD; retained USD/MYR quotes follow the shared network's
   existing no-conversion policy. Domestic Thai USD data stays unchanged.
4. **Enable the same country experience only with data.** Keep domestic as default;
   add International/Both when the replacement shared bundle contains Thailand's
   consumer queries. Apply domestic-only endpoint rules only to domestic records;
   international flights must have exactly one Thai endpoint. Stamp the shared
   archive in the Thai HTTP revision and use the existing event-window, filter,
   board, Destinations and frequency behaviour. Existing country routes outside
   this footprint survive. Worldwide Thai expansion beyond these locations is a
   later, separate scope.
5. **Validate before enabling.** Probe BKK and DMK separately, HKT/USM, overnight
   routes, ICT↔IST/UTC+8/JST/Australia/Gulf boundaries, reused currencies, missing
   queries and duplicate identities. Check no flight leaks through airport/country
   filters; each shared flight appears once and consistently in both endpoint
   country views. Test all scopes, local boards, UTC network counts, HTTP cache
   invalidation, reproducible preparation, mobile, themes and Indonesian. Report
   actual gateway/country-pair coverage and priced/unpriced records. Do not equate
   query completion with complete international coverage.

## Actual domestic coverage and validation

Captured **25 October 2026**, for **2 November 2026 ICT**:

- **615 dated flights**, **29 airports**, **88 directional routes**, **6 carriers**.
  All 615 depart inside this ICT day; no previous-day flight overlaps the window.
  All **615 have positive captured USD quotes**; this is snapshot availability,
  not a promise that fares remain available or every service was captured.
- **224/224 airport/date queries captured**, **112/112 directional candidates**
  searched across **30 airports**. **170 queries returned flights**, **54 returned
  no matching direct flights**. **100 directions** returned flights on at least one
  searched date; **88** appear within the replay day's window.
- **Zero failed/missing queries, rejected records, unverified fare contexts or
  unresolved airport identities**. **NNT (Nan Nakhon)** was searched but did not
  return flights; that is a documented coverage gap, not proof of no service.
  Smaller/commuter services and further regional route pairs remain outside scope.

| Origin region | Airports returned / selected | Departures | With USD fare |
| --- | --- | ---: | ---: |
| Central | 3 / 3 | 274 | 274 |
| North | 6 / 7 | 106 | 106 |
| Northeast | 8 / 8 | 52 | 52 |
| East | 2 / 2 | 4 | 4 |
| South | 10 / 10 | 179 | 179 |

Gzip: **31,054 bytes**, SHA-256
`cbf2018820915a0c7d31f6358743bba3deaf6fecdb2cbbd9c5b976c4438926c5`.
Manifest rebuilding and preparation from cached captures reproduce byte-for-byte output.

Validation: **210 Python tests and 93 JavaScript tests passed**, covering Thai
flights, all existing flight countries/shared network, Melbourne replay/HTTP,
app/i18n, Japan rail and existing Thailand SRT/Bangkok transit. Final Chrome checks
passed exact BKK/DMK, CNX, HKT, USM, HDY and UBP departure/arrival boards, ICT clocks
and fare capture timestamps, USD previews without implicit seeking, combined
carrier/airport filters and empty intersections, fullscreen/back/pagination,
Destinations, frequency totals stable during seeking, airport visibility, all five
themes, Indonesian, mobile viewport coverage, cache reuse and switching back to
Japan's separate JST view. Screenshots were visually inspected; no page errors
occurred. International is planned only; the shared network footprint is unchanged.
