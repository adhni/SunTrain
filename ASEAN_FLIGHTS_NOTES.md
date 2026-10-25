# Remaining ASEAN flight locations

Brunei, Cambodia, Laos, Myanmar and Timor-Leste complete the **11 ASEAN country
locations** in SunTrain's flight catalogue. This means a view for each country,
not complete national flight coverage. All five cover **2 November 2026** and
connect to the shared **International network · Flights** UTC view.

| Location | Timeline | Initial scope | Domestic discovery |
| --- | --- | --- | --- |
| Brunei | Asia/Brunei · BNT (UTC+8) | International | None; no invented domestic BWN–KUB service |
| Cambodia | Asia/Phnom_Penh · ICT (UTC+7) | International | KTI, SAI, KOS: 6 directions |
| Laos | Asia/Vientiane · ICT (UTC+7) | Domestic | 8 selected airports: 18 directions |
| Myanmar | Asia/Yangon · MMT (UTC+6:30) | Domestic | 14 selected airports: 36 directions |
| Timor-Leste | Asia/Dili · TLT (UTC+9) | International | DIL–OEC in both directions |

Cambodia and Timor-Leste retain a Domestic option with an honest empty snapshot:
no timed domestic flights were returned for their candidate queries. This does
**not** establish that no domestic service operates. Brunei has only International,
without a meaningless domestic selector. Boards use each airport's local time;
Myanmar's half-hour offset applies to the timeline, board and fare capture labels.
The same airport/carrier filters, departures/arrivals, fullscreen board, Destinations,
frequency lines, compact planes, themes and English/Indonesian copy are reused.

## Candidate evidence and airport identities

[ASEAN's member list](https://asean.org/member-states/) includes Timor-Leste,
[admitted on 26 October 2025](https://asean.org/forging-a-new-era-timor-leste-admitted-into-asean/).
Sources reviewed on 26 October 2026 provide candidates and identity context:

- Brunei: [Royal Brunei route map](https://www.flyroyalbrunei.com/brunei/en/destination/route-map/route-map/).
  Maps may include onward connections. New exact BWN gateway pairs are labelled
  probes; the map does not prove dated nonstop flights.
- Cambodia: [Air Cambodia's historical route promotion](https://www.aircambodia.com/en/offer/-ready-for-your-ultimate-vacation-ready-for-takeoff-)
  is candidate context only. Its 2025 dates and frequencies do not create 2026 flights.
  [Techo's opening notice](https://www.techoairport.com.kh/news/techo-intl-airport-welcome-first-flight-09-sep-2025)
  establishes KTI's September 2025 opening. [Cambodia's State Secretariat of Civil
  Aviation paper hosted by ICAO](https://www.icao.int/sites/default/files/APAC/Meetings/2023/2023%20MET%20SG%2027/3-Working%20Papers/WP24_A.I.5_KHM_SIEM-REAP-ANGKOR-INTERNATIONAL-AIRPORT-VDSA.pdf)
  establishes REP's commercial transfer to SAI in October 2023.
- Laos: [Lao Airlines route map](https://laoairlines.com/en/route-map/) and
  [schedule page](https://laoairlines.com/en/flight-schedule/), plus
  [official tourism transport guidance](https://www.visitlaos.org/essentials/getting-around/).
  Selected regional pairs are probes, not a transcribed complete map. Unresolved
  old/new NEU airport identity is excluded from this release.
- Myanmar: [Myanmar National Airlines' network page](https://secure.flymna.com/plan-a-trip)
  provides context. Selected Yangon and Mandalay regional pairs are probes;
  the much larger published network is not claimed as captured coverage.
- Timor-Leste: [official visitor planning](https://timorleste.tl/plan-your-trip),
  [2026 Aero Dili network news](https://timorleste.tl/news/aero-dili-direct-darwin-dili-service-2026)
  and [Aero Dili's domestic context](https://www.aerodili.com/about/).
  Country-level destination mentions do not prove an exact airport pair. DIL–OEC
  is searched, not turned into a frequency-based or guessed timetable.

The builder imports relevant exact pairs from the existing Australia, Indonesia,
Malaysia, Singapore, India and Gulf manifests, then adds focused regional gateway
probes. It does not search every airport against every other airport. Both
candidate directions are searched independently; reverse flights are not inferred.
Cross-country pairs among the new five are included in both endpoint manifests.

| International manifest | Airports | Directional candidates |
| --- | ---: | ---: |
| Brunei | 22 | 42 |
| Cambodia | 28 | 72 |
| Laos | 17 | 44 |
| Myanmar | 16 | 36 |
| Timor-Leste | 8 | 14 |

These overlap on six directions, adding **202 unique directions** to the shared
manifest: **2,012 directions / 177 airports / 6,865 airport-date queries**.

Pinned OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies
unique active IATA identities and coordinates. All new national airports have
explicit IANA zones, including western Laos and Myanmar's half-hour offset.

**KTI/VDTI and SAI/VDSA are searched explicitly.** PNH and REP survive in historical
input manifests/bundles for provenance, but their commercial flights are excluded
from the November 2026 shared projections. Candidate labels migrate PNH→KTI and
REP→SAI; cached flights, times, fares and identities are never relabelled or reused
across these airports. KOS remains separate. No old airport coordinates are moved.

The nine new manifests retain evidence, source URLs, input hashes and airport pins.
Source hashes cover curated evidence and pinned inputs, not claimed raw copies of
all live airline websites. Regional, frequency-only and unverified routes remain gaps.

## Dated captures and fares

Only dated Google Flights nonstop segments matching exact endpoints, source
local date and validated duration become flight records. Domestic searches cover
1–2 November, retaining overlaps with the local replay day; durations allow one
minute to eight hours. Shared searches use adjacent origin-local dates needed by
UTC and all endpoint-local windows, with a 24-hour duration cap.

New quotes request **USD, one adult, economy, one-way**. The cheapest positive
returned quote for an exact flight is kept with its source capture timestamp.
Reused USD/MYR quotes preserve their original context, currency and timestamp.
No conversion or numerical price comparison across currencies occurs. Missing
or unverified prices remain unavailable. Unknown aircraft remain unknown;
separate flight numbers do not imply codeshare knowledge or physical aircraft counts.

Two concurrent public searches at most; normalized captures are resumable. Access
challenges stop collection and preserve successful captures. Missing, failed,
rejected and not-returned queries stay distinct. Complete query execution does
not imply complete coverage, ticket availability or live tracking.

## Preparation and local storage

```bash
.venv/bin/python scripts/prepare_remaining_asean_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_remaining_asean_flights.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py --concurrency 2
```

Run domestic collection sequentially with its default one worker while the
international collector uses one worker, or run collectors separately with up to
two workers. Avoid running both at two workers. Optional domestic `--country MM`
(or LA/KH/TL) selects just one country. Brunei uses the shared archive directly.

Offline rebuild from retained captures:

```bash
.venv/bin/python scripts/prepare_remaining_asean_flights.py --prepare-only
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Domestic bundles live at `data/reference/{cambodia,laos,myanmar,timor_leste}_flights/2026-11-02.json.gz`.
International flights are stored once in `data/reference/international_network/2026-11-02.json.gz`.
The five views project the shared archive into their own local day. Existing
country reference bundles remain untouched. HTTP cache revisions include shared
file changes and reject unsupported dates. Stable ordering and fixed gzip mtime
make cached preparation reproducible.

`.cache/google-flights-{cambodia,laos,myanmar,timor_leste}/` and
`.cache/google-flights-international-network/` contain resumable normalized source
captures; deleting them requires public searches again for a later preparation,
but committed snapshots keep working. `.cache/australia-flights-audit/ourairports-airports.csv`
can be downloaded again from the manifest's pinned URL and verified SHA.
`.cache/asean-flights-audit/` contains optional logs, coverage audits and screenshots;
`.cache/asean-http/` regenerates when replay HTTP responses are requested.

Older Malaysian KTI entries store the pinned OurAirports internal identifier
`KH-0002`; the shared catalogue uses that same row's ICAO `VDTI`. This exact alias
is accepted only with matching IATA, country and coordinates. It does not permit
PNH/KTI substitution or broadly relax airport identity checks.


## Captured coverage

These are overlapping records in each country's **local** day, preserving separate
flight numbers; they are not inferred physical aircraft movements. Airport totals
in the international table include foreign endpoints. Counts across countries
must not be summed: one shared flight can appear in two country views.

| Country | Domestic records | International records | Priced records, both scopes | Domestic queries | International queries |
| --- | ---: | ---: | ---: | ---: | ---: |
| Brunei | — | 22 | 16 | — | 94 / 94 |
| Cambodia | 0 | 59 | 51 | 12 / 12 | 166 / 166 |
| Laos | 2 | 30 | 25 | 36 / 36 | 97 / 97 |
| Myanmar | 18 | 71 | 18 | 72 / 72 | 90 / 90 |
| Timor-Leste | 0 | 8 | 0 | 4 / 4 | 35 / 35 |

All **124 domestic queries** and all **6,865 shared archive queries** are captured;
there are **0 failed or missing queries** and **0 unresolved selected airports**.
Empty results still mean not returned. Query coverage does not establish national
completeness. The extension reuses 178 additional historical query captures and
collects 494 new international captures beyond the preserved 6,193-query archive.

- Brunei returns BWN international records on 15 directions, across 11 airports
  including foreign endpoints. Domestic service is not fabricated.
- Cambodia returns international records at **KTI and SAI** on 27 directions;
  **KOS** and all six domestic directions remain unreturned for the replay window.
- Laos returns domestic **VTE–XKH in both directions**, plus international records
  at **VTE/LPQ** on 22 directions. PKZ, LXG, ODY, ZVK and HOE candidates remain
  unrepresented; this is particularly incomplete regional coverage.
- Myanmar returns domestic records at **RGN/MDL/HEH/THL/TVY/NYT**, on nine directions,
  and international records at **RGN/MDL**, on 25 directions. Many smaller regional
  candidates remain unreturned. None of the 18 domestic records has a verified
  captured fare; their prices correctly remain unavailable.
- Timor-Leste returns **DIL** international records on six directions, across four
  airports including foreign endpoints. **OEC**, DIL–OEC and probes to additional
  foreign gateways remain gaps. All eight international records are unpriced.

The UTC network now has **4,550 overlapping records**, **3,996 owned departures**,
**140 returned airports**, **1,269 returned directions**, and **3,593 priced records**
(3,158 USD / 435 MYR). The shared archive retains **6,125 records** across all local
windows. All **5,886 previous records and 6,193 previous query objects** are
unchanged, including schedules, fares and provenance. Existing country reference
bundles are unchanged.

The shared gzip is **758,250 bytes**, SHA-256
`4c864001dd4796ff6614f0203d1033faf74c418deb8d345688c32f1132bee971`.
All nine country manifests, the shared manifest and the five compressed outputs
reproduce exactly from pinned inputs and cached captures.

Validation: **247 Python tests and 96 JavaScript tests passed**, including existing
Australian/Indonesian/Malaysian/Asian flight and Melbourne transit regressions.
Browser checks passed for all five country views and their UTC country filters:
local midnight labels, Myanmar half-hour time, exact airport/carrier filters,
original quotes, departures/arrivals, Destinations, fullscreen/back, mobile,
frequency lines, station visibility, themes and Indonesian copy. Existing UTC
network filtering, pagination, cache reuse and China/Japan/Korea/Thailand scope
switching also passed. Screenshots were visually reviewed for desktop/mobile.

```bash
.venv/bin/python -m pytest -q tests/test_remaining_asean_flights.py tests/test_international_network.py
node --test tests/*.cjs
PYTHONPATH=.:.cache/browser-tools SUNTRAIN_TEST_URL=http://127.0.0.1:8878 .venv/bin/python tests/browser_remaining_asean_flights.py
```
