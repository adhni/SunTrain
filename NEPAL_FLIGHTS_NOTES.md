# Nepal flights

**Nepal · Flights** covers **2 November 2026**. It opens on Domestic and offers
Domestic / International / Both. International connections are limited to
countries with existing SunTrain flight views and **DXB/AUH/DOH**, and also appear
in the shared UTC international network. Foreign endpoints such as London,
Dhaka, Istanbul or Colombo do not become eligible merely because Taiwan/Hong
Kong worldwide routes already include their countries.

The timeline uses **Asia/Kathmandu, NPT (UTC+5:45)**. Airport boards use their
own local dates and zones. Reuses compact planes, airline/airport filters,
departures/arrivals, Destinations, fullscreen pagination, flight previews,
frequency lines, airport visibility, themes, English and Indonesian.

## Sources and airport identity

The exact-airport manifests contain **52 domestic directions / 21 airports** and
**48 international directions / 25 airports**. Both directions are independently
searched; a published sector does not invent a reverse flight.

- [Buddha Air's flight information](https://www.buddhaair.com/detail/flight-information)
  supplies trunk and cross-country route candidates. Its durations and
  frequencies are discovery context, not dated replay instances.
- [Yeti Airlines](https://yetiairlines.com/),
  [Tara Air's destinations](https://www.taraair.com/destination.jsp) and
  [Sita Air's destinations](https://www.sitaair.com.np/destination.jsp) supply
  trunk and remote-flight context. Ramechhap–Lukla is explicitly distinct from
  Kathmandu–Lukla; mountain, charter and sightseeing descriptions do not create
  scheduled flights. Pure scenic round trips are excluded.
- [CAAN's international schedule index](https://caanepal.gov.np/index.php/ne/air-transports/international-schedule)
  links the [winter 2026/27 all-airline schedule](https://www.caanepal.gov.np/storage/app/uploads/public/6ad/204/625/6ad20462584b8147669061.pdf),
  dated 16 October 2026, and the [Flydubai Pokhara winter schedule](https://www.caanepal.gov.np/storage/app/uploads/public/6ad/202/46c/6ad20246c8fd7187955340.pdf),
  revised 15 October and effective 25 October 2026–27 March 2027. Exact ICAO
  sectors are resolved to IATA search targets; only returned dated nonstop
  Google segments create records. The winter WMKK–VNBW sector adds KUL–BWA
  discovery. KUL's possible onward stop does not turn connecting itineraries
  into nonstop flights.
- Relevant exact-airport candidates/captures from the existing Indian,
  Malaysian, Singaporean, Gulf and Hong Kong manifests are reused, retaining
  original identities and timestamps. International route evidence outside
  existing flight countries/hubs is excluded.

Sources reviewed 26 October 2026. Raw PDF URLs, byte counts and SHA-256 pins are
committed in `data/sources/nepal_flights_source_pins.json`. The CAAN PDF host's
certificate chain was incomplete for the local downloader; these public,
credential-free downloads were inspected and hashed explicitly. Curated route
manifests rebuild from committed evidence without live website scraping.

Airports use pinned OurAirports commit
`3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`.
**KTM / VNKT**, **PKR / VNPK**, **PHH / VNPR** and **BWA / VNBW** stay distinct.
The official Dubai–Pokhara winter sector is **OMDB–VNPR**, resolved to **DXB–PHH**;
an older Gulf PKR–DXB probe is suppressed from new shared-network discovery.
Existing Gulf snapshots are not relabelled. Domestic airline lists often say
only “Pokhara”; PKR and PHH are separate exact-airport probes. Returned codes
are preserved without guessing that one airport means the other. Some booking
sources retain PKR labels despite operations having moved; this remains a
source/location limitation, not permission to shift captured flights between
airports. Missing PHH results are reported as gaps.

Domestic discovery includes trunk routes and selected remote probes via KTM,
RHP, PKR and KEP. Rara/Talcha has no unique active IATA row in the pinned catalogue
and remains unresolved/deferred without inventing a four-letter IATA code.
Other small commuter, charter, helicopter and scenic services remain gaps.

## Dates, fares and preservation

Domestic collection searches **1–2 November** for overlap with the local day,
using the existing one-minute to eight-hour duration limits. International
queries cover the union required by Nepal, UTC and other endpoint-country day
windows, with the existing 24-hour maximum. UTC timestamps and half-open event
windows handle overnight and quarter-hour offsets. Flights are deduplicated by
exact source identity; distinct flight numbers stay distinct without codeshare
inference. Unknown aircraft remain unknown; paths are illustrative.

New queries request **USD, one adult, economy, one-way** and choose the cheapest
verified quote returned for the exact flight. Reused USD/MYR quotes retain
their original currencies and capture timestamps; no conversion or numerical
comparison across currencies occurs. Unreturned/unverified fares remain
unavailable. Public Google quotes do not assert resident/citizenship eligibility
for Nepal's other domestic fare products. These are partial dated schedules
and prices, with no live tracking or automatic refresh.

The shared manifest now has **2,838 directions / 291 airports**, with **9,601
unique queries**. The 48 Nepal directions overlap two existing HKG–KTM directions,
so 46 are added. Of the additional 161 queries, 51 were reused before collection
and **110 required new searches**. Two concurrent public searches are used at
most. Challenges stop collection; successful captures and explicit gaps survive.
An empty query means “not returned”, never “no service”.

## Rebuilding and local caches

```bash
.venv/bin/python scripts/prepare_nepal_routes.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_nepal_flights.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py --concurrency 2
```

Run the collectors sequentially to keep the two-search limit. Saved successful
queries are reused. Offline preparation:

```bash
.venv/bin/python scripts/prepare_nepal_flights.py --prepare-only
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Domestic is stored at `data/reference/nepal_flights/2026-11-02.json.gz`;
international records are stored once in the shared international archive.
`SUNTRAIN_NEPAL_FLIGHTS_REFERENCE` overrides domestic. A custom domestic fixture
remains isolated unless `SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE` is explicit
too. HTTP revisions include both archives and reject unsupported dates.

`.cache/google-flights-nepal/` and `.cache/google-flights-international-network/`
hold resumable normalized captures/provenance. Deleting these requires public
searches again for later preparation, although committed replays still work.
The pinned airport CSV is in `.cache/australia-flights-audit/`. Raw PDFs, test
logs and screenshots in `.cache/nepal-flights-audit/` can be removed; URLs/hashes
are retained for recovery. Generated `.cache/nepal-http/` responses regenerate.

## Actual coverage and validation

All **104 / 104 domestic queries** and the **110 new international searches** completed, with zero failed or missing queries. Nepal's international projection uses 120 captured origin/date queries; the larger shared archive's union uses 9,601 queries for all country-local and UTC windows. Query completion does not imply timetable completeness.

| Scope | Records | NPT-day departures | Airports | Directional routes | Priced records |
| --- | ---: | ---: | ---: | ---: | ---: |
| Domestic | 203 | 203 | 14 | 27 | 41 |
| International | 105 | 91 | 17 | 31 | 85 |

Domestic returned BDP/BHR/BIR/BWA/DHI/IMK/JKR/KEP/KTM/PKR/RJB/SIF/SKH/TMI, operated by Buddha Air, Yeti Airlines, Shree Airlines and Nepal Airlines. All eight central/eastern trunk candidates and four western trunk candidates returned records. Only PKR returned among the two Pokhara candidates; PHH did not return domestic records. Of seven mountain/remote candidates only IMK returned a dated record; LUA/RHP/JMO/PPL/DOP/JUM remain gaps. There are 51 unreturned domestic queries, zero source-record rejections and no inferred small-airport schedules.

Domestic prices are sparse: **41 USD quotes**, **162 unavailable prices**. International has **79 USD and 6 MYR quotes**, **20 unavailable prices**. Both scopes together have 308 records and 126 fares. Nepal's international projection has 47 unreturned queries. Returned Nepal gateways are **KTM and PHH**; BWA did not return an international record. Returned counterpart countries are **AE, CN, HK, IN, JP, MY, QA, SG and TH**. There are no unrelated worldwide connections.

The new shared archive retains all **9,087 previous records and 9,440 previous queries verbatim**, including old prices, timestamps, airport codes and coordinates. All newly added records touch Nepal. The previous nine rejected international duration records and 11 unverified-fare queries are unchanged. Unrelated local notes/documents were checked unchanged too.

Domestic gzip: **11,879 bytes**, SHA-256 `206edda06f861ede0523b8526666bf796f5cc9faef03afc85c2caa67ab290019`.
Shared international gzip: **1,090,398 bytes**, SHA-256 `8fc8bae3c78be5b00fb6a727ada4f6835054b1c8d51b3ff81d935431a04f72e0`.
Both archives and all three rebuilt route manifests reproduce byte for byte from cached/pinned inputs.

**274 Python tests and 99 JavaScript tests passed**, covering exact PKR/PHH and KTM/RHP identities, limited international scope, NPT midnight/quarter-hour offsets, adjacent days, short regional durations, cheapest exact USD quotes, duplicates, missing queries, domestic fixture isolation, HTTP gzip/ETags/date rejection, shared local/UTC ownership and existing flight/transit regressions.

The Nepal browser suite passed for KTM/BIR/BWA/KEP/BDP/JKR/SIF boards, carrier/airport filters, priced previews, departures/arrivals/Destinations, fullscreen pagination/back, foreign IST versus Nepal NPT, themes, Indonesian, 390px mobile layout, frequency totals, cache reuse and Nepal's existing-country filters in the shared UTC network. Desktop and mobile screenshots were visually checked.

The existing international-network browser suite also passed for its earlier country filters and views, airport/carrier filters, local boards, fullscreen navigation, frequency totals, themes, Indonesian and mobile layout.
