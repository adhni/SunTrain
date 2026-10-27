# Canada and Mexico flight expansion

Separate **Canada · Flights** and **Mexico · Flights** views expand beyond the five-airport country subsets in the North America starter. Both use **2 November 2026 departures in each origin airport’s local time**, a UTC timeline, local airport boards, USD for new fares, and unchanged original USD/EUR/MYR quotes when reusing captures. Coverage and prices are partial.

## Reviewed footprint and search limits

Canada’s 15 gateways: **YYZ, YVR, YUL, YYC, YEG, YOW, YWG, YHZ, YYT, YQB, YTZ, YLW, YYJ, YXE, YQR**.

Mexico’s 15 gateways: **MEX, CUN, GDL, MTY, TIJ, SJD, PVR, NLU, BJX, MID, CUL, HMO, CUU, OAX, TLC**.

This is a practical gateway selection, not an exact top-15 passenger ranking. It adds regional reach, Atlantic Canada, Toronto’s Billy Bishop and Mexico City’s separate Felipe Ángeles/Toluca airports. Published domestic destinations can extend beyond these gateways.

New searches cover **published domestic and Canada/US/Mexico directions**, both ways, with all returned airlines. Compatible existing worldwide captures are reused, including routes beyond the reviewed gateways. Prior all-pairs manifests never become new route evidence. There are no additional dates, airline-by-airline sweeps or inferred reverse flights.

[Great Circle Pro airport maps](https://www.gcpromap.com/airports/yyz/) supply source candidates. Pinned page/map hashes and the full published destination inventory are retained in the discovery JSON. The selected `destinations` subset contains only exact active airports in CA/MX/US; `published_destinations` preserves the wider source inventory. Published routes are seasonal candidates, not evidence of dated service.

Canadian maps were available for 13 gateways; **YXE and YQR returned HTTP 404**. Mexican maps were available for eight gateways; **BJX, MID, CUL, HMO, CUU, OAX and TLC returned HTTP 404**. Sourced reverse directions and prior positive captures still cover some routes from those airports. Their missing maps leave discovery gaps; they do not establish absence of service.

Airport identities/coordinates use the pinned OurAirports catalogue and identity-matched IANA zones from the existing pinned timezone catalogue. **YYZ/YTZ, MEX/NLU/TLC, CUN/TQO, and TIJ/SAN remain separate.** No airport is replaced with a nearby city airport. Current explicit zones resolve newer airports and regional ports missing from the old timezone catalogue; geographic IANA identity remains separate from dated replay overrides.

## Dated clock rules

The snapshot’s Canadian clocks require the announced 2026 changes:

- [British Columbia](https://archive.news.gov.bc.ca/releases/news_releases_2024-2028/2026AG0013-000209.htm): most of B.C. stays on UTC−7 after March 2026. Eastern communities following Alberta’s clock are handled separately.
- [Alberta](https://www.alberta.ca/albertas-new-time-system-abt): UTC−6 from November 2026, without the autumn clock reset.
- [Northwest Territories](https://www.gov.nt.ca/en/newsroom/northwest-territories-ends-seasonal-time-change): UTC−6 from November 2026.
- [Saskatchewan](https://www.saskatchewan.ca/Government/Municipal-Administration/Tools-Guides-and-Resources/Saskatchewan-Time-System): UTC−6, including the former Lloydminster exception now aligned with Alberta.

Dated `replay_timezone` fields freeze these November offsets for older server/browser timezone databases, while `timezone` retains the geographic IANA identity. Overrides apply to Canadian endpoints in **both country views**, including Mexican connections. They are dated snapshot rules, not general historical timezone aliases. Source parsing, local-date validation, boards and previews all use the same effective zone.

Other Canadian zones retain their own IANA rules: Toronto/Montreal UTC−5, Halifax UTC−4, St John’s UTC−3:30, Yukon UTC−7 and Nunavut’s separate regional zones. [Sanikiluaq’s official station data](https://www.meds-sdmm.dfo-mpo.gc.ca/isdm-gdsi/twl-mne/inventory-inventaire/sd-ds-eng.asp?no=4628&region=CA&user=isdm-gdsi) identifies its Eastern zone; YSK uses America/Iqaluit.

Mexico follows the [official standard-time rules and northern-border exceptions](https://www.gob.mx/sener/articulos/en-la-republica-mexicana-ya-no-hay-horario-de-verano?idiom=es). Mexico City, NLU, TLC and Chihuahua use UTC−6; Cancún/Tulum UTC−5; Tijuana UTC−8; Sonora and Baja California Sur UTC−7 for the replay date. Ciudad Juárez explicitly uses America/Ciudad_Juarez, distinct from Chihuahua/Ojinaga. Airport region and explicit border exceptions determine zones; no blanket Mexico City clock is assigned nationally. [CENAM](https://www.cenam.mx/hora_oficial/default2.aspx) provides official zone context.

## Shared experience and preparation

Reuses planes, airport/airline/country filters, Domestic/International/Both, departures/arrivals, Destinations, fullscreen boards, flight previews, frequency lines, station visibility, themes and English/Indonesian copy. The initial maps frame Canada and Mexico respectively. Timelines include all origin-local departures and overnight arrivals; source durations must agree with UTC elapsed time (1 minute–24 hours). Missing aircraft/fares stay unspecified. Distinct flight numbers remain distinct; repeated source identities deduplicate.

```bash
.venv/bin/python scripts/discover_canada_mexico_flights.py
# Reapply the bounded destination selection without refreshing source pages:
.venv/bin/python scripts/discover_canada_mexico_flights.py --select-only
.venv/bin/python scripts/prepare_canada_mexico_routes.py
.venv/bin/python scripts/prepare_canada_mexico_flights.py --seed --dry-run
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_canada_mexico_flights.py --seed
# Resume just one country or prepare offline:
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_canada_mexico_flights.py --country CA --seed
.venv/bin/python scripts/prepare_canada_mexico_flights.py --prepare-only
# After both collections, share newly positive cross-border captures offline:
.venv/bin/python scripts/prepare_canada_mexico_routes.py
.venv/bin/python scripts/prepare_canada_mexico_flights.py --seed --prepare-only
```

Canada and Mexico collect sequentially, with at most two concurrent searches. Mexico can reuse newly completed Canadian cross-border queries. Access challenges stop collection, preserve completed captures and report missing queries. Caches: `.cache/canada-mexico-flights-audit/`, `.cache/google-flights-canada-usd-v1/`, `.cache/google-flights-mexico-usd-v1/`.

Prepared bundles: `data/reference/{canada,mexico}_flights/2026-11-02.json.gz`. Gzip metadata is deterministic and output is validated before atomic replacement. Runtime reads the bundles without searching. Existing North America/Americas snapshots retain their original footprints and hashes; the shared International network remains separate.

**Empty means not returned, never no service.** Small/northern Canadian services, seaplanes, seasonal Mexican destinations, unreturned airlines and missing quotes remain gaps. Query completion is not nationwide completeness.

## Actual capture and validation

Five exact queries were independently rechecked after collection: YRT–YWG, YWG–YRT, YWG–YRL, CJS–MEX and CUN–CJS. The source inconsistencies persisted. For example, YRT–YWG MO309 showed 19:15–22:45 in the same zone but a stated 150 minutes; CJS–MEX VB1001 showed 08:51–12:20 across UTC−7/UTC−6 but a stated 209 minutes. Other Aeromexico rows on CJS–MEX validated correctly. The legal airport clocks remain unchanged, valid rows are retained and inconsistent rows omitted. Raw normalized clock/duration rechecks and page hashes are retained locally in `.cache/canada-mexico-flights-audit/source-rechecks/`; minimal conflict fixtures are covered by tests.

| View | Flights | Domestic | International | Priced | Returned national airports | Returned directions | Captured/reused queries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Canada | 2284 | 1211 | 1073 | 2261 | 81 | 765 | 1166 / 342 |
| Mexico | 2014 | 1155 | 859 | 1599 | 56 | 722 | 968 / 315 |

The original five-airport subsets had **289 Canadian domestic flights** and **287 Mexican domestic flights**. New country views retain source-specific flight identities and original quotes; their shared Canada–Mexico flights must not be added together as unique physical flights.

Canada: 1166/1166 captured queries, 398 empty results, 5 rejected records, 0 failed and 0 uncollected queries. Fare currencies: EUR 65, USD 2196, unpriced 23.

Returned national airports: QBC, YAM, YAZ, YBC, YBG, YBL, YBR, YCD, YCG, YDF, YEG, YFB, YFC, YFO, YGG, YGL, YGP, YGW, YGX, YHM, YHU, YHZ, YKA, YKF, YLW, YMM, YMT, YOW, YPR, YPW, YPX, YPY, YQB, YQD, YQG, YQM, YQQ, YQR, YQT, YQU, YQX, YQY, YQZ, YSB, YSJ, YSK, YTH, YTS, YTZ, YUL, YUY, YVO, YVP, YVR, YWG, YWH, YWL, YXC, YXE, YXJ, YXS, YXT, YXU, YXX, YXY, YYC, YYD, YYF, YYG, YYJ, YYR, YYT, YYZ, YZF, YZP, YZT, YZV, YZZ, ZBF, ZEL, ZNA.

Domestic flights returned at: QBC, YAM, YAZ, YBC, YBG, YBL, YBR, YCD, YCG, YDF, YEG, YFB, YFC, YFO, YGG, YGL, YGP, YGW, YGX, YHM, YHU, YHZ, YKA, YKF, YLW, YMM, YMT, YOW, YPR, YPW, YPX, YPY, YQB, YQD, YQG, YQM, YQQ, YQR, YQT, YQU, YQX, YQY, YQZ, YSB, YSJ, YSK, YTH, YTS, YTZ, YUL, YUY, YVO, YVP, YVR, YWG, YWH, YWL, YXC, YXE, YXJ, YXS, YXT, YXU, YXX, YXY, YYC, YYD, YYF, YYG, YYJ, YYR, YYT, YYZ, YZF, YZP, YZT, YZV, YZZ, ZBF, ZEL, ZNA.

Reviewed gateways without returned flights: none. These are capture/date gaps, never no-service claims.

Rejected-source queries: YRT–YWG, YWG–YRL, YWG–YRT. Their invalid rows are omitted; rejection diagnostics remain in metadata.

Canada bundle SHA-256: `56eca735d30c370857fa1ff8dfe0c463749d9b328fd8d8767d3e65a51783424a`.

Mexico: 968/968 captured queries, 236 empty results, 24 rejected records, 0 failed and 0 uncollected queries. Fare currencies: EUR 33, USD 1566, unpriced 415.

Returned national airports: ACA, AGU, BJX, CEN, CJS, CLQ, CME, CPE, CTM, CUL, CUN, CUU, CVM, CZM, DGO, GDL, HMO, HUX, IZT, LAP, LMM, LTO, MAM, MEX, MID, MLM, MTT, MTY, MXL, MZT, NLD, NLU, OAX, PBC, PDS, PVR, PXM, QRO, REX, SJD, SLP, SLW, TAM, TAP, TGZ, TIJ, TLC, TPQ, TQO, TRC, UPN, VER, VSA, ZCL, ZIH, ZLO.

Domestic flights returned at: ACA, AGU, BJX, CEN, CJS, CLQ, CME, CPE, CTM, CUL, CUN, CUU, CVM, CZM, DGO, GDL, HMO, HUX, IZT, LAP, LMM, LTO, MAM, MEX, MID, MLM, MTT, MTY, MXL, MZT, NLD, NLU, OAX, PBC, PDS, PVR, PXM, QRO, REX, SJD, SLP, SLW, TAM, TAP, TGZ, TIJ, TLC, TPQ, TQO, TRC, UPN, VER, VSA, ZCL, ZIH, ZLO.

Reviewed gateways without returned flights: none. These are capture/date gaps, never no-service claims.

Rejected-source queries: CJS–CUN, CJS–GDL, CJS–MEX, CJS–MTY, CJS–NLU, CJS–TIJ, CUN–CJS, GDL–CJS, MEX–CJS, MTY–CJS, NLU–CJS, TIJ–CJS. Their invalid rows are omitted; rejection diagnostics remain in metadata.

Mexico bundle SHA-256: `19f6867e5c4112e6a0f948dad126d5c8c072c6e471391001da9866d1ae82e01e`.

Validation: dated national and border clocks, 2026 Canadian changes, Newfoundland’s half-hour offset, distinct city airports, bounded sourced directions, duplicate records, cheapest verified fares through the shared parser, retained currencies, overnight flights, missing/rejected queries, deterministic offline preparation, HTTP caching/date rejection, browser boards/filters/frequency/fullscreen/themes/Indonesian/mobile, and existing North America/Americas/Australia/Melbourne regressions.
