# Taiwan and Hong Kong flights

Choose **Taiwan · Flights** or **Hong Kong · Flights** for **2 November 2026**.
Taiwan offers Domestic / International / Both, opening on Domestic. Hong Kong
has International only. Both international views cover **worldwide passenger
route candidates**, including Europe, the Americas, Africa and the Pacific;
they are not restricted to countries with existing SunTrain flight views.

The same worldwide TW/HK connections appear in **International network · Flights**,
with From country / To country filters for their foreign endpoints. Other older
countries keep their previous shared-network scope: adding a US endpoint for
TPE–SFO does not trigger unrelated Australia–US or India–Europe collection.
No new domestic views are inferred for these foreign endpoints.

Taiwan's timeline uses **Asia/Taipei (UTC+8)**; Hong Kong uses **Asia/Hong_Kong,
HKT (UTC+8)**. The combined network uses UTC. Airport boards use airport-local
dates and times, including North American/European daylight-saving offsets.
These are dated schedule snapshots with partial coverage and illustrative paths,
not live tracking or a promise of ticket availability. No automatic refresh occurs.

## Published worldwide discovery

The international seed combines the following primary evidence:

- [Taiwan CAA's international/cross-strait passenger-route statistics index](https://www.caa.gov.tw/article.aspx?a=1741&lang=1)
  and [August 2026 ODS](https://www.caa.gov.tw/FileAtt.ashx?id=41534&lang=1),
  published 29 September 2026. Airport-specific monthly sheets 33-1 through 33-6
  and January–August sheets 39-1 through 39-6 cover **TPE, KHH, TSA, RMQ, HUN
  and TNN**. Every numbered route row is considered, worldwide, rather than
  filtering destination countries. Statistics and frequencies discover candidates;
  they never create a dated flight or a price.
- [Hong Kong Airport Authority's March 2026 airline/destination inventory](https://www.hongkongairport.com/iwov-resources/file/airport-authority/publications/annual-and-interim-reports/en/25_26/E_24_Airlines%20and%20Destinations.pdf),
  linked from its [2025/26 annual report](https://www.hongkongairport.com/en/airport-authority/publications/annual-interim-reports/annual2026).
  Passenger destination entries are explicitly resolved to airports. Entries
  marked freight-only are excluded as passenger-route evidence; partner or cargo
  operations do not become scheduled passenger flight instances.
- [Kaohsiung's public airport schedule](https://www.kia.gov.tw/FLIPLAN.html) and
  its [flight-plan JSON](https://www.kia.gov.tw/data/flightplan.json) supplement
  the monthly inventory with exact airport pairs. Schedule periods and weekly
  patterns remain discovery context; Google supplies the dated replay records.
- [Cathay's current destination directory](https://flights.cathaypacific.com/destinations/en_HK/)
  supplies supplementary SEA/TLV probes. Directory entries may describe future,
  suspended or connecting services; only returned dated nonstop segments qualify.
- Existing primary Australian, Indonesian, Malaysian, Singaporean, Indian and
  Gulf manifests retain relevant reciprocal TW/HK candidates. Their cached flight
  identities, fares and timestamps are never relabelled.

Sources were reviewed on 26 October 2026. The committed
`data/sources/taiwan_hong_kong_route_seed.json` retains normalized evidence rows,
CAA sheet/row references, explicit airport resolutions, source URLs and raw pins:

| Download | Bytes | SHA-256 |
| --- | ---: | --- |
| CAA August 2026 ODS | 126,798 | `e079dd1f8fa59bb3a6ca0a6b11d88663a74aa169494f16a94a35e9e23ff9e6fa` |
| HKIA March 2026 inventory PDF | 45,286 | `917922a01f52ea01831d9a68558a35730703e0bfc77d3333b8394ab97c182e13` |

The Kaohsiung JSON has its own raw SHA/byte count in that same seed. Route hashes cover normalized
curation and input hashes, not claimed complete raw copies of every live website.

International discovery has **356 Taiwanese directions / 116 airports** and
**342 Hong Kong directions / 172 airports**. Four TW–HK pairs are shared, giving
**690 unique directional candidates across 203 airports**. Both directions are
searched independently; a published route never invents a reverse flight.
Completing these searches does not prove every flight, current route, charter,
seasonal service or last-minute change has been captured. The latest published
statistics are historical discovery, not November operation evidence.

Almaty is explicitly deferred: [Cathay's passenger launch is 9 January 2027](https://news.cathaypacific.com/cathay-pacific-launches-direct-flights-to-almaty-from-9-january-2027),
after this replay. It is not promoted from a bookable future destination into a
November 2 service. Cargo-only destinations are not searched solely as passenger
routes. The HKG airport identity refers to the current VHHH airport, not Kai Tak.

## Exact Taiwan airports and domestic coverage

[Official Taiwan tourism domestic route guidance](https://eng.taiwan.net.tw/m1.aspx?sno=0024034)
discovers **40 directional domestic candidates across 13 airports**:

| Area | Candidates |
| --- | --- |
| Main island | TSA, RMQ, KHH, CYI, TNN, HUN, TTT |
| Penghu | MZG |
| Kinmen | KNH |
| Matsu | LZN (Nangan), MFK (Beigan) |
| Eastern islands | GNI (Green Island), KYD (Lanyu) |

**TPE (Taoyuan) and TSA (Songshan) stay separate throughout.** The domestic
manifest uses TSA; no TPE domestic trunk service is inferred from old city labels.
In foreign-route statistics, the Japanese destination 松山 is resolved to **MYJ
(Matsuyama)**, never Taiwan's TSA. HND/NRT, GMP/ICN, SHA/PVG, CTU/TFU, PEK/PKX,
LZN/MFK and KUL/SZB also stay separate. Ambiguous Beijing/Moscow city entries
become explicitly labelled airport probes; they do not merge airports or flights.
Retired Cambodian city labels resolve to KTI for new discovery only, without
relabelling historical PNH records. Hengchun and small Penghu commuter services
remain deferred; frequency-only island routes do not receive guessed times.

Pinned OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies
unique active IATA rows, countries and coordinates. Every airport has an explicit
IANA zone, including airport-specific US/Canadian zones and Asian quarter-hour
offsets. No whole-country US offset or city-code Google search is used.

## Dates, fares and collection

New searches request **USD, one adult, economy, one-way**, keeping the cheapest
positive returned quote for each exact flight. Reused USD/MYR quotes retain their
original currency, fare context and capture timestamp. No currency conversion or
numerical comparison across currencies occurs; absent/unverified offers remain
unavailable. Distinct flight numbers remain distinct without guessing codeshares;
unspecified aircraft remain unknown.

Domestic searches cover **1–2 November** and one-minute to eight-hour segments.
International searches use exact origin-local dates needed by the NZ/TW/HK/other
endpoint-country and UTC day windows, with a 24-hour duration cap. Adjacent-day
and date-line flights are selected by UTC overlap. Boards use half-open event
ownership; local flight dates are not assumed to equal the replay's business date.

The US repeated clock hour on 1 November is resolved only when the source's dated
arrival and stated duration select exactly one UTC pair. Multiple equally valid
UTC meanings are rejected rather than guessed; nonexistent local times are also
rejected. DST and overnight dates do not come from fixed offsets.

A single worldwide query queue serves TW, HK and their shared-network consumers,
so TW–HK and other shared airport/date queries are searched once. Two concurrent
public Google searches at most; completed normalized captures are resumable.
Challenges stop collection, preserving completed data and explicit missing queries.
Empty results mean **not returned**, never **no service**.

## Rebuild and local storage

```bash
.venv/bin/python scripts/prepare_taiwan_domestic_routes.py
.venv/bin/python scripts/prepare_taiwan_hong_kong_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_taiwan_flights.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_taiwan_hong_kong_flights.py --concurrency 2
```

Run domestic and worldwide collectors sequentially at two workers, or use one
worker each if running together. Do not run both at two workers. Domestic
`--validate-only` runs representative probes without publishing a full snapshot.

Offline preparation:

```bash
.venv/bin/python scripts/prepare_taiwan_flights.py --prepare-only
.venv/bin/python scripts/prepare_taiwan_hong_kong_flights.py --prepare-only
```

Only domestic Taiwan is stored separately at
`data/reference/taiwan_flights/2026-11-02.json.gz`. International records are stored
once in `data/reference/international_network/2026-11-02.json.gz`; there is no
second duplicate worldwide replay bundle. The worldwide preparer seeds its saved
queries into the existing shared cache and prepares the complete shared archive.
Previously captured records and queries remain unchanged. Hong Kong directly
projects this archive; Taiwan overlays it on its domestic bundle.

`SUNTRAIN_TAIWAN_FLIGHTS_REFERENCE` overrides domestic Taiwan.
`SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE` overrides shared international data.
A custom Taiwan domestic fixture stays isolated unless the shared override is
explicit too. HTTP revisions include the shared archive and reject unsupported
dates. Stable ordering, fixed gzip mtime and atomic replacement enable exact
cached rebuilds.

`.cache/google-flights-taiwan/`, `.cache/google-flights-taiwan-hong-kong-worldwide/`
and `.cache/google-flights-international-network/` contain resumable source
captures/provenance. Removing them requires public searches again for later
preparation; committed snapshots still work. Normalized route manifests rebuild
from the committed seed without re-downloading the official inventory. Raw source
downloads, optional logs and browser screenshots in
`.cache/taiwan-hong-kong-flights-audit/` may be removed; their pinned URLs/hashes
allow later recovery. Generated `.cache/taiwan-hong-kong-http/` responses regenerate.

## Captured coverage and validation

All **80 domestic queries** and **2,260 unique worldwide airport/date queries** were captured, with **zero failed or missing queries**. This is query completion, not a complete timetable. Local-day figures:

| View/scope | Records | Local-day departures | Airports | Directional routes | Priced records |
| --- | ---: | ---: | ---: | ---: | ---: |
| Taiwan domestic | 73 | 73 | 10 | 21 | 73 |
| Taiwan international | 900 | 814 | 88 | 242 | 837 |
| Hong Kong international | 895 | 784 | 112 | 216 | 728 |

Taiwan domestic returned CYI/KHH/KNH/LZN/MFK/MZG/RMQ/TNN/TSA/TTT, operated by Mandarin Airlines and Uni Airways. All 73 records have USD fares. Main-island airports returned 6/7, Penghu 1/1, Kinmen 1/1 and Matsu 2/2; neither eastern-island candidate returned dated records. HUN/GNI/KYD are gaps, not assertions of no service. Hengchun and small Penghu commuter airports remain deferred.

Taiwan international returned TPE/TSA/KHH/RMQ; HUN/TNN candidates did not return international records. Its 900 records include 821 USD and 16 MYR fares, with 63 unavailable prices. Hong Kong returned 703 USD and 25 MYR fares, with 167 unavailable prices. There are 270 unreturned searches in Taiwan's 835-query local-day projection and 296 in Hong Kong's 776-query projection. The larger 2,260-query queue also serves UTC and foreign endpoint-country windows; these numbers must not be conflated. Both views returned US/European connections; Hong Kong also returned African and Pacific connections. Returned country/territory endpoints:

- TW: AE, AT, AU, CA, CN, CZ, DE, FR, HK, ID, IT, JP, KR, MO, MY, NL, PH, PW, SG, TH, TR, US, VN.
- HK: AE, AU, BD, BE, BN, CA, CH, CN, DE, ES, ET, FI, FJ, FR, GB, ID, IN, IT, JP, KR, LK, MN, MY, NL, NP, NZ, PG, PH, QA, SG, TH, TR, TW, US, VN, ZA.

TW–HK records appear in both local views and are stored once. The shared archive now holds **9,087 records / 9,440 queries**, preserving every previous **6,767 record / 7,180 query** verbatim, including original prices and timestamps. No new source records were rejected; the nine previously documented duration rejections and 11 earlier unverified-fare queries remain unchanged.

Taiwan domestic gzip: **8,430 bytes**, SHA-256 `7e6b4a72c8f6612d7102092cc628bd2bd59ad879a7b2f1b35b55e64edff02382`.
Shared international gzip: **1,072,844 bytes**, SHA-256 `d62153c15145ea1f14b46821740e601daede2aa698fb64f36dffaea3fd800177`. Both archives and all five route manifests reproduce byte for byte from their pinned/cached inputs.

Validation: **266 Python tests and 98 JavaScript tests passed**, covering exact airport identities, worldwide scope restrictions, local/UTC/date-line ownership, repeated and nonexistent DST times, cheapest verified fares, duplicates, missing queries, challenge-stop publication, custom domestic isolation, HTTP gzip/ETags/date rejection, all existing flight countries and Melbourne/transit regressions. The existing international-network browser suite also passed.

The Taiwan–UK candidates returned no dated records in this snapshot; a destination appearing in a published inventory is not enough to display a flight. The browser's Taiwan–Europe filter check uses the captured France connection.

The Taiwan/Hong Kong browser suite passed for TSA/KHH/RMQ/MZG/KNH/LZN boards, CST/HKT clocks, US airport-local dates, USD flight previews, carrier/airport filters, departures/arrivals/Destinations, fullscreen pagination/back, all five themes, Indonesian, 390px mobile layout, frequency totals, cache reuse and worldwide TW/HK country filters in the UTC network. Desktop and mobile screenshots were visually checked.
