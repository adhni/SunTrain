# Vietnam flights

Choose **Vietnam · Flights** for **2 November 2026**, with Domestic /
International / Both. Domestic is the initial scope. The midnight-to-midnight
replay uses **Asia/Ho_Chi_Minh, Vietnam time (ICT, UTC+7)**. Airport boards use each
airport's local dates and times. International connections also appear in
**International network · Flights**, whose clock/day window uses UTC.

This is a dated schedule snapshot with partial coverage and illustrative paths,
not live tracking. Fares are captured quotes; no automatic refresh occurs.

## Sources and exact airports

Pinned OurAirports commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`, CSV SHA-256
`a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17`, supplies exact,
unique, non-closed, country-matching IATA identities and coordinates. Every
Vietnamese endpoint explicitly uses Asia/Ho_Chi_Minh. **HAN, SGN, DAD, DLI and CXR**
stay distinct. Nha Trang uses **CXR (Cam Ranh)**; the former NHA airport is not
substituted. SGN stays Tan Son Nhat; no future Long Thanh airport or flight times
are inferred or substituted from a city label.

Domestic discovery covers **22 selected airports and 122 directional candidates**:

| Region | Airports |
| --- | --- |
| North | HAN, HPH, DIN, VDO |
| Central and Highlands | THD, VII, VDH, HUI, DAD, VCL, UIH, TBB, CXR, DLI, BMV, PXU |
| South | SGN, VCA, VKG, CAH, VCS, PQC |

International discovery covers **190 directional candidates across 42 airports**,
restricted to existing SunTrain flight countries and **DXB/AUH/DOH**. It starts
with **78 directions** in existing primary country manifests, adds recovered
Philippine candidates previously deferred because Vietnam was outside the
footprint, and adds focused East Asian/Thai gateway candidates/probes. It does not
perform every-airport/all-country Cartesian searches or claim worldwide coverage.

Sources reviewed for candidate discovery:

- [Vietnam Airlines domestic promotional route table](https://www.vietnamairlines.com/content/dam/vna/vna-assets/MKT-PDF/BOD-WKS-DOM-EN.pdf)
  lists city pairs. Cities are explicitly resolved to exact airports, but promotion
  amounts, travel-day restrictions and frequencies never create flight instances.
- [Vietnam Airlines route groups](https://giftcards.vietnamairlines.com/nhom-duong-bay/)
  provide undated regional candidates. Such lists are not proof of Nov 2 operation.
- [Vietnam Airlines international promotion table](https://www.vietnamairlines.com/content/dam/vna/vna-assets/MKT-PDF/BOD-WKS-INT-VI.pdf)
  and [Hanoi–Japan offers](https://www.vietnamairlines.com/en-vn/flights-from-hanoi-to-japan)
  provide country/city/exact-airport candidates, not dated nonstop or fare evidence.
- [Vietjet's Da Nang airport/route page](https://www.vietjetair.com/vi/ve-may-bay/san-bay-da-nang-dad-da-nang)
  supplies Korean gateway candidates. Additional CXR/PQC Korean and China/Japan/
  Thailand gateway pairs are labelled supplemental probes, not published routes.
- [Vietnam Airlines airport directory](https://airportmap.vietnamairlines.com/?lang=en)
  supplies identity context for explicitly labelled probes; it is not evidence that
  any particular pair operates. HAN/SGN hub probes cover selected regional airports
  while avoiding all-pairs regional discovery.
- [Vietnamese CAA's Lien Khuong reopening notice](https://caa.gov.vn/Pages/Print.aspx?NewsId=20260805113611646)
  concerns the earlier 2026 closure/reopening. That closure is not treated as a
  November closure. DLI remains a candidate; dated searches determine actual data.
- The recovered Philippine package remains a partial, unverified source of route
  candidates only. It contains no flight times or prices; its original metadata
  and hashes are retained in the committed seed. Existing richer manifests remain
  untouched.

The manifests retain candidate kinds, source URLs and input-file hashes. Their
route hashes cover curated evidence and input pins, not complete raw website bytes.
No unpublished raw-download hashes are claimed. Published lists, historical
promotions, contextual maps, recovered rows and supplemental probes remain
separate from actual captured flight evidence.

## Schedules, fares and collection

Only dated Google Flights nonstop segments matching exact IATA endpoints, source
local departure date and stated duration become records. Repeated exact flight
identities are deduplicated; distinct flight numbers remain distinct without
inferring codeshares. Unknown aircraft remain unknown. Empty queries mean
**not returned**, never **no service**. Completing a candidate manifest does not
imply national completeness or complete coverage among selected countries.

Domestic searches cover **1–2 November**, retaining flights overlapping the
Vietnam day, with one-minute to eight-hour durations. Shared international
searches cover the union needed by UTC and every endpoint country's local day,
including adjacent origin-local dates and a 24-hour duration ceiling. Inbound
and outbound searches remain directional; route lists never invent reverse flights.

New queries request **USD**, **one adult, economy, one-way**, retaining the cheapest
returned positive quote for the exact flight and its capture timestamp. Reused
international USD/MYR quotes keep their original currency and timestamps. There
is no currency conversion or numerical comparison across currencies. Missing or
unverified offers remain unavailable; captures are not promises of bookable fares.

The shared collector preserves all **5,143 prior archive records and 5,540 prior
queries**, reuses **203 additional international captures**, and needs **450 new
international searches**. Domestic requires **244 searches**. Collection starts
with one worker per collector, maintaining at most two simultaneous searches; a
remaining collector can resume with two workers after the other finishes. Access
challenges stop collection, retaining successful caches and missing-query reports.

## Rebuild and local storage

```bash
.venv/bin/python scripts/prepare_vietnamese_flight_airports.py
.venv/bin/python scripts/prepare_international_network_routes.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_vietnamese_flights.py --concurrency 1
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_international_network.py --concurrency 1
.venv/bin/python scripts/prepare_vietnamese_flights.py --prepare-only
.venv/bin/python scripts/prepare_international_network.py --prepare-only
```

Domestic data is `data/reference/vietnam_flights/2026-11-02.json.gz`, overridable
with `SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE`. International is stored once in the
shared archive and independently projected into Vietnam and UTC days. The Vietnam
HTTP revision fingerprints both files. Older shared archives lacking a Vietnam
consumer entry leave its overlay disabled. Custom domestic fixtures remain
isolated unless an explicit shared reference is also supplied.

Normalized resumable captures live in `.cache/google-flights-vietnam/` and
`.cache/google-flights-international-network/`. Optional audits, test logs and
screenshots live in `.cache/vietnam-flights-audit/`. Removing captures saves local
space but requires fresh searches to rebuild; committed replays still work. The
OurAirports CSV is reused from `.cache/australia-flights-audit/`, or can be
redownloaded from the pinned URL/hash. Generated HTTP caches are disposable.
Gzip uses deterministic ordering, fixed mtime and atomic replacement.

## Actual coverage

Captured **25 October 2026** for **2 November 2026 Vietnam time**:

- Domestic: **592 overlapping records**, **574 departures** and **576 arrivals**
  inside the day, **20 airports**, **74 directional routes** and **4 carriers**.
  All **592 have positive USD fares**. Eighteen records depart before the
  selected day but overlap its window; records are not inferred aircraft movements.
- **244 / 244 domestic queries captured**, all **122 directions** searched;
  **76 directions** returned flights on at least one searched date. **98 queries**
  returned no matching direct flights. **CAH, VKG** were searched but not returned
  in the replay; this is a coverage gap, not proof of no service. Bamboo Airways
  and other unreturned carriers/services must not be interpreted as absent nationally.
- International: **575 overlapping records**, **495 departures**, **500 arrivals**,
  **156 directions**, **42 airports** and **41 carriers**. Vietnamese gateways:
  **CXR, DAD, DLI, HAN, PQC, SGN**. **492 records have fares** (448 USD,
  44 MYR); **83 remain unpriced**.
- **463 / 463 Vietnam-view international queries captured**, all **190 directions**
  searched; **168 directions** returned flights on at least one searched date.
  **103 queries** returned no matching direct flights. Both scopes have zero
  failed/missing queries, rejected source records or unresolved identities. Further
  regional international pairs, other foreign countries and uncaptured services
  remain gaps. Query completion never implies national or worldwide completeness.
- Both scopes: **1,167 records**, **1,084 with captured fares**. The UTC network separately
  contains **4,364 records** and **3,818 departure events**. All **5,143 prior archive
  records** and **5,540 prior queries** retain their exact schedules, fares and
  provenance. Existing country reference bundles are unchanged.

| Origin region | Airports returned / selected | Vietnam-day departures | With USD fare |
| --- | --- | ---: | ---: |
| North | 4 / 4 | 167 | 167 |
| Central and Highlands | 12 / 12 | 144 | 144 |
| South | 4 / 6 | 263 | 263 |

Domestic gzip: **30,460 bytes**, SHA-256
`55d12c560b66f96b7d7eca1c0b95e9bc6f7e16b461d210a5784bb426529dc221`.
Shared gzip: **699,609 bytes**, SHA-256
`811d57a684c7d0d7e4f32f1eb967c04789cf677d1f17886a8d088597638b2990`.
Both archives and all three manifests reproduce byte for byte from cached inputs.

Validation: **229 Python tests and 95 JavaScript tests passed**, including all
existing flight profiles, Melbourne replay/HTTP, Thailand rail, app/i18n and Japan
rail. Two Chrome suites passed the Vietnam and existing shared-network views:
eight domestic airport boards, exact airports, USD previews without implicit
seeking, ICT and foreign local clocks, all scopes, airline/airport/country filters,
fullscreen/back/pagination, Destinations, frequency totals, visibility, all five
themes, Indonesian, mobile and cache reuse. Desktop/mobile screenshots were
visually inspected; no page errors occurred. Both archives rebuild byte for byte,
and all 5,143 prior shared records/5,540 prior queries were independently checked
for unchanged schedules, fares and provenance.
