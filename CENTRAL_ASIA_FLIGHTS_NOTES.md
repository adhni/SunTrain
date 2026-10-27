# Central Asia flights

A separate **Central Asia · Flights** regional view for **2 November 2026 departures in each origin airport’s local time**. Covers Kazakhstan, Uzbekistan, Kyrgyzstan, Tajikistan and Turkmenistan, with domestic, intra-regional and worldwide international connections. UTC timeline and airport-local boards; newly captured quotes use USD. Reused USD/EUR/MYR quotes retain their original currencies. Coverage and fares are partial.

The map starts over Central Asia. Existing airline, airport, country and domestic/international filters, moving planes, selection-only arcs, frequency lines, Destinations and fullscreen departure/arrival boards are reused. Flights between different member countries are international; the country filters distinguish them from connections further afield.

## Exact airports and clocks

The pinned OurAirports catalogue supplies active IATA/ICAO identities. **Bishkek uses BSZ / UCFM**, not retired FRU; **Astana uses NQZ / UACC**, not TSE. The [airline notice](https://www.trinityairways.com/app/customerCenter/notice/retrieve/12418) confirms Bishkek’s 2025 code change, and [Kazakhstan’s notice](https://www.gov.kz/uploads/2022/2/14/f4bd7a89429f465aae98022132afc98f_original.3460307.pdf) records Astana’s change. Retired IATA codes are normalized only when generating historical route candidates; neither cached flights nor published flight identities are relabelled.

Uzbek airports retain their modern UZ-prefixed ICAO identities, including TAS/UZTT, SKD/UZSS and FEG/UZFF. The [Uzbek civil aviation amendment](https://uzaeronavigation.com/media/file/am04_2026_eBAFjR4.pdf) documents these identities. Names and airports in the route lists never override the exact active catalogue.

[Kazakhstan adopted UTC+5 nationwide in March 2024](https://www.gov.kz/org/mfa-jakarta/press/news/details/715495?lang=en). Explicit IANA zones retain western airport identities (Aqtau, Atyrau, Aqtobe, Oral, Qostanay, Qyzylorda) and Asia/Almaty elsewhere, all UTC+5 for this date. Uzbekistan, Tajikistan and Turkmenistan use UTC+5; Kyrgyzstan uses UTC+6. Regional airports absent from the older timezone catalogue receive explicit national IANA zones. Foreign airports retain their own zones. The current [IANA Asia rules](https://data.iana.org/time-zones/tzdb/asia) govern dates and offsets.

Only dated source segments with consistent departure, arrival and source duration are retained (1 minute–24 hours). The timeline includes the complete origin-local date and overnight arrivals. Aircraft and fares remain unspecified when the source does not provide them.

## Route discovery and limits

The reviewed launch set contains **44 airports**: 18 Kazakhstan, 11 Uzbekistan, 4 Kyrgyzstan, 4 Tajikistan and 7 Turkmenistan.

Secondary route pages for ALA, NQZ and TAS supplied pinned raw map documents. The other **41 airport map pages returned HTTP 404**. Those errors describe the source, not the existence of flights.

Reviewed October 2026 nonstop facts supplement the maps: [Bishkek](https://www.flightconnections.com/flights-from-bishkek-bsz), [Dushanbe](https://www.flightconnections.com/flights-from-dushanbe-dyu), [Samarkand](https://www.flightconnections.com/flights-from-samarkand-skd), [Osh](https://www.flightconnections.com/flights-from-osh-oss), [Khujand](https://www.flightconnections.com/flights-from-khujand-lbd), [Urgench](https://www.flightconnections.com/flights-from-urgench-ugc), [Fergana](https://www.flightconnections.com/flights-from-fergana-feg) and [Namangan](https://www.flightconnections.com/flights-from-namangan-nma). Larger pages contribute their reviewed top-20 nonstop lists plus explicitly identified nonstop airport codes, not a complete route catalogue. Connecting-destination sections, zero-flight entries and explicitly future-only additions are excluded. A raw download attempt returned HTTP 403 and was not repeated; these public indexed facts have normalized fact hashes, **not fabricated raw-page hashes**.

The [official Turkmenistan Airlines domestic table](https://turkmenistanairlines.tm/en/services/show/napravlenie-i-raspisanie-reysov) supplies Ashgabat and cross-regional domestic candidates, including Kerki. Its [exact-IATA international map](https://turkmenistanairlines.com/flight-map) distinguishes LGW from LHR and PEK from PKX. Timetable frequencies, generic fare advertisements and undated weekly timings are not imported as dated flights or prices.

A pinned [2014-era OpenFlights route archive](https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat) supplies **domestic-only historical candidates** among the reviewed airports. [The archive stopped updating in June 2014](https://nginx.openflights.org/data); it establishes neither current service nor flight timings. OpenFlights contributors, Open Database License. Historical international networks are not expanded, and prior all-pairs manifests do not supply new route candidates. Existing positive dated captures are reused, retaining timestamps, identity and currency.

IYO/Sariosiyo appears in the Tashkent source map but is absent from the pinned active-airport catalogue; it remains unresolved. Smaller airports and new services outside the selected source lists remain discovery gaps. Russian and regional services may not be returned by Google even where published route lists show them. **Empty results mean not returned, never no service.** Query completion is not regional completeness.

## Rebuild and resume

```bash
.venv/bin/python scripts/discover_central_asia_flights.py
# Regenerate reviewed facts and domestic historical candidates without refreshing maps:
.venv/bin/python scripts/discover_central_asia_flights.py --supplement-only
.venv/bin/python scripts/prepare_central_asia_routes.py
.venv/bin/python scripts/prepare_central_asia_flights.py --seed --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_central_asia_flights.py --seed
# Offline preparation:
.venv/bin/python scripts/prepare_central_asia_flights.py --prepare-only
```

Discovery/audit cache: `.cache/central-asia-flights-audit/`. Dated captures: `.cache/google-flights-central-asia-usd-v1/`. At most two concurrent Google queries, one origin-local departure date, no per-airline or additional-day sweeps. Access challenges stop collection; completed captures remain resumable. Captures keep source timestamps, query/page hashes, failures, rejected records and missing fares explicit.

The prepared bundle is `data/reference/central_asia_flights/2026-11-02.json.gz`, validated and atomically written with deterministic gzip metadata. Runtime reads the bundle without searching. Existing country views and the shared International network stay separate.

## Actual capture and validation

**604 dated flights**: 215 domestic and 389 international, over **347 returned directions** and **93 returned airports** (including connecting destinations). **285 verified fares**; 319 prices unavailable. Currency counts: EUR 2, USD 283, unpriced 319. No currency conversion.

**839/839 queries captured**, including **95 reused queries** and 492 empty results. Failures: 0; uncollected: 0; rejected records: 0. 152 airports searched in a 154-airport catalogue.

| Country | Returned/catalogued airports | Domestic flights | Intra-regional flights | Other international flights | Priced flights |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kazakhstan | 19/23 | 171 | 18 | 115 | 214 |
| Uzbekistan | 11/14 | 42 | 23 | 155 | 55 |
| Kyrgyzstan | 2/4 | 2 | 7 | 42 | 13 |
| Tajikistan | 2/4 | 0 | 2 | 47 | 6 |
| Turkmenistan | 1/7 | 0 | 0 | 5 | 5 |

Country flight counts overlap for flights between two member countries; they must not be summed to derive the regional total. Domestic means both airports have the same country. Captured query completion does not imply complete national coverage.

Kazakhstan returned airports: AKX, ALA, CIT, DMB, DZN, GUW, HSA, KGF, KOV, KSN, KZO, NQZ, PLX, PPK, PWQ, SCO, TDK, UKK, URA.

Uzbekistan returned airports: AZN, BHK, FEG, KSQ, NCU, NMA, NVI, SKD, TAS, TMJ, UGC.

Kyrgyzstan returned airports: BSZ, OSS.

Tajikistan returned airports: DYU, LBD.

Turkmenistan returned airports: ASB.

Reviewed launch airports without returned flights: BKN, CRZ, IKG, IKU, KEA, KQT, KRW, MYP, TAZ, TJU. These remain date/source gaps, never claims of no service.

**Turkmenistan domestic coverage is missing** despite published domestic routes. The weekly official table is retained as route evidence and a documented gap; no undated schedule has been promoted into dated flights.

Validation: exact modern airports and candidate-only retired-code normalization; all five national clocks, Kazakhstan’s 2024 change, overnight cross-zone segments, duplicate identities, retained USD/EUR/MYR fares, missing-query reporting, deterministic offline preparation, HTTP caching and date rejection. Browser checks cover all five country filters, local airport boards, regional map/home pin, departures/arrivals, Destinations, fullscreen, frequency lines, five themes, Indonesian, mobile and existing flight/transit regressions.

Prepared bundle SHA-256: `96933ef3c4c3da7b17b133ee881b19e6eccf2132041ae695ef88e6cb896dcb00`.
