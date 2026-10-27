# Pacific Islands flights

A separate **Pacific Islands · Flights** view for departures on **2 November 2026 in each origin airport’s local time**, including overnight and date-line arrivals. UTC timeline, airport-local boards, new USD quotes, original reused USD/EUR/MYR quotes. Coverage and prices are partial, not a complete Pacific timetable.

## Scope and sources

The reviewed footprint covers Melanesia, Micronesia, Polynesia, Hawaii, Norfolk Island, Chatham Islands and Easter Island. Mainland US/Chile, Australia and New Zealand airports are connecting destinations. Country/territory airport identities define domestic versus international; Hawaii–mainland US is domestic. The view does not add mainland domestic networks or flights between arbitrary airport pairs.

The pinned OurAirports and OpenFlights airport catalogues preserve exact IATA/ICAO identities. Nouméa La Tontouta (NOU) and Magenta (GEA), and Samoa's Faleolo (APW) and American Samoa's Pago Pago (PPG), remain separate.

Most secondary airport map pages were unavailable: 67 of 71 reviewed airport pages returned HTTP 404. Maps for HNL, OGG, KOA and LIH supplied candidates. These failures describe source availability, not the absence of flights.

A pinned [OpenFlights route archive](https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat), which [stopped updating in June 2014](https://nginx.openflights.org/data), supplements discovery. **Historical zero-stop routes are search candidates only**, searched in both directions. They provide no current-service claims or flight times. OpenFlights route data attribution: OpenFlights contributors, Open Database License. Source hashes and warnings are stored in `data/sources/pacific_flights_discovery.json`.

Primary facts supplement the historical list: [Talofa's APW–PPG route](https://www.talofaairways.com/routes/) and [Air Chathams' October 2026 Wellington/Christchurch network](https://www.airchathams.co.nz/blog/upcoming-changes-to-chatham-islands-air-services). Only normalized route facts are hashed for those sources; there is no invented raw-document checksum. Their frequency descriptions never become dated flights. Current [SFO airport Nadi service](https://www.flysfo.com/vi/node/14876) and [Air Tahiti’s San Francisco access list](https://www.airtahiti.com/en/coming-to-polynesia) add the two newer transpacific pairs absent from the historical archive; Paris itineraries with US stops are excluded. The [official New Caledonia October 2026 status](https://www.newcaledonia.travel/frequently-asked-questions/domestic-flights/) records Air Calédonie’s March move from GEA to NOU: four island pairs are searched from NOU as separate exact-airport candidates. The old GEA candidates remain historical, never aliases for NOU; the October Maré cancellation is not treated as proof of November service. The [Fiji Airways 2024 annual report](https://parliament.gov.fj/wp-content/uploads/2026/03/11Fiji-Airways-Annual-Report-2024-2.pdf) adds Nadi–Funafuti, introduced in January 2024. Chatham's discontinued regular Auckland route is not added from older visitor schedules.

Prior successful dated captures are reused. Previously generated all-pairs manifests are not accepted as new Pacific route evidence. Google exact-IATA queries establish captured dated schedules; no city-code substitution, paid adapter, fabricated timetable, automatic refresh or live tracking.

## Clocks and date line

Explicit IANA zones follow the [IANA Australasia rules](https://data.iana.org/time-zones/tzdb/australasia). Bougainville (including Buka) uses UTC+11, other Papua New Guinea UTC+10. French Polynesia distinguishes Tahiti (−10), Marquesas (−9:30) and Gambier (−9). Kiribati distinguishes Gilbert (+12), Phoenix (+13) and Line Islands (+14). Chatham has its +13:45 November daylight-saving offset; Easter Island uses its own seasonal clock. Hawaii is −10, Samoa +13, American Samoa −11.

The initial map spans 128°E–252°E across the date line. Flight arcs remain continuous around 180°. The UTC timeline spans the complete origin-local date and all returned arrivals, rather than truncating them at UTC midnight. Source duration must agree with elapsed UTC duration (1 minute to 24 hours); an arrival calendar date before departure is valid when crossing the date line eastbound.

## Rebuild and resume

```bash
# Re-fetch missing airport maps and regenerate pinned historical/primary candidates.
.venv/bin/python scripts/discover_pacific_flights.py
# Recreate supplements alone using the pinned historical archive.
.venv/bin/python scripts/discover_pacific_flights.py --supplement-only
.venv/bin/python scripts/prepare_pacific_routes.py
.venv/bin/python scripts/prepare_pacific_flights.py --seed --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_pacific_flights.py --seed
# Offline, without searching:
.venv/bin/python scripts/prepare_pacific_flights.py --prepare-only
```

Caches: `.cache/pacific-flights-audit/` (discovery, diagnostics), `.cache/google-flights-pacific-usd-v1/` (dated captures). There are at most two concurrent Google searches, one origin-local date and no per-airline/date expansion. Access challenges stop collection and leave completed captures resumable. The prepared bundle is `data/reference/pacific_flights/2026-11-02.json.gz`, compressed deterministically and validated before atomic replacement. Runtime reads it without searches.

Only positive captured schedules appear. Empty queries mean **not returned**, never **no service**. Missing queries, rejected records, source timestamps, price availability and unresolved airports remain explicit in metadata. JJA is absent from the pinned active-airport catalogue and remains unresolved.

## Actual capture and validation

**877 dated flights**, across **305 returned directions** and **110 returned airports**. 710 domestic and 167 international; **776 verified fares**, all USD in this snapshot, and 101 unavailable prices. Reused quotes remain intact; this particular set returned no EUR/MYR quotes.

**837/837 queries captured**, including 66 reused queries; 532 empty results. No failed, rejected or unattempted queries/records. 219 airports searched in a 222-airport catalogue; unqueried catalogue entries remain visible gaps, not captured services.

| Island group | Catalogued airports | Returned airports | Captured flights touching group |
| --- | ---: | ---: | ---: |
| Melanesia | 90 | 22 | 150 |
| Micronesia | 14 | 9 | 50 |
| Polynesia | 43 | 24 | 124 |
| Hawaii | 11 | 10 | 559 |
| Other islands | 3 | 2 | 6 |

Group flight counts overlap when a flight connects two groups and must not be added together. Polynesia here includes the listed island countries/territories; Chatham and Easter Island are in Other islands, Hawaii is separate. The regional catalogue is broader than the returned network.

Melanesia returned airports: BUA, GKA, GUR, HGU, HIR, ILP, KVG, LAE, LBS, LIF, MAG, MEE, NAN, NOU, PNP, POM, RAB, SUV, SVU, TVU, UVE, VLI.

Micronesia returned airports: GUM, INU, KWA, MAJ, PNI, ROR, SPN, TKK, TRW.

Polynesia returned airports: AIT, APW, AUQ, BOB, FAV, HOI, HUH, MAU, MOZ, NHV, PPG, PPT, RAR, RFP, RGI, RMT, RUR, RVV, TBU, TIH, TUB, UAH, UAP, WLS.

Hawaii returned airports: HNL, HNM, ITO, JHM, KOA, LIH, LNY, MKK, MUE, OGG.

Other islands returned airports: CHT, IPC.

Reviewed launch airports without returned flights: CXI, FUN, FUT, GEA, GMR, HPA, IUE, KDV, KSA, MAS, MUA, NLK, ROP, SON, TAH, TIQ, VAV, WWK, YAP. These are date/source gaps, not declarations of no service. Smaller Solomon Islands, Vanuatu, PNG and New Caledonia services are especially incomplete in Google; route-map outages and the age of historical candidates also leave discovery gaps, including newer routes.

Validation: dated source/duration checks, exact airport membership, all regional time-zone cases, date-line arrivals, deterministic offline preparation, HTTP caching/date rejection, browser map/home-pin/local-board/filter/frequency/theme/Indonesian/mobile checks, and Australian/Melbourne/shared flight regressions.

Prepared bundle SHA-256: `3fc70bc1f51c4a6df00324b6fa7b089a61ebd928edbc272916c9c150eca18053`.
