# Malaysian flights and captured fares

**Malaysia · Flights** is a separate domestic/international schedule replay for **2 November
2026**, with a midnight-to-midnight **MYT** timeline. It leaves Malaysia/Kuala
Lumpur rail views and the existing Australian/Indonesian flight snapshots intact.
This is a partial dated capture, with illustrative paths rather than observed
aircraft positions.

Domestic opens first; use **Flights → International / Both** for cross-border
services. Airport boards use airport-local clocks; the replay stays on MYT.
Both scopes use the same captured MYR fare context. Airline/airport filters,
arrivals/departures, Destinations, fullscreen boards and frequency lines apply
to the selected scope.

## Captured domestic coverage

The bundle contains **449 departures on 2 November plus 8 overnight carry-ins**:
**457 overlapping flights**, **18 airports** and **81 directional routes**, in
**34,770 bytes gzip**. **409 flights have captured prices; 48 do not**. Source
captures were made on **25 October 2026, 04:18–04:34 MYT**.

| Returned airline | Overlapping flights | With a fare |
| --- | ---: | ---: |
| AirAsia | 257 | 257 |
| Malaysia Airlines | 92 | 92 |
| Firefly | 60 | 60 |
| Batik Air | 48 | 0 |

All **364 planned date/airport-pair queries** were captured across **182
directional candidates and 31 airports**. There are **no failed or unattempted
queries**, and no unresolved airport identities. **202 searches returned no
matching direct flight**. Completion of the manifest does not mean nationwide
completeness, and the 48 missing Batik fares are not zero-cost tickets.

| Region | Candidate airports | Airports with captured flights |
| --- | ---: | ---: |
| Peninsular Malaysia | 10 | 10 |
| Sabah & Labuan | 5 | 4 |
| Sarawak | 16 | 4 |

The unreturned airports are **BBN, BKM, LBP, LDU, LGL, LKH, LMN, LWY, MKM, MUR,
MZV, ODN and TGC**. Rural flights are a material coverage gap; no AirBorneo/RAS
timings were invented from the historical candidate table. Other airports or
routes outside this manifest may also be absent.

## Captured international coverage

The international supplement adds **910 departures owned by the MYT day plus
126 overnight carry-ins**: **1,036 overlapping flights**, **110 airports**
(**11 Malaysian and 99 overseas in 33 foreign countries**), **273 directional
routes** and **67 carrier codes**, in **94,573 bytes gzip**. **857 flights have
captured MYR fares; 179 do not**. International captures were made on
**25 October 2026, 04:48–05:14 MYT**.

| Malaysian gateway | Overlapping international flights | With a fare | Returned foreign airports |
| --- | ---: | ---: | ---: |
| KUL | 872 | 712 | 98 |
| PEN | 75 | 66 | 14 |
| BKI | 36 | 34 | 12 |
| SZB | 24 | 16 | 5 |
| JHB | 9 | 9 | 3 |
| IPH | 6 | 6 | 1 |
| KCH | 6 | 6 | 2 |
| KUA | 2 | 2 | 1 |
| LGK | 2 | 2 | 1 |
| MYY | 2 | 2 | 1 |
| TWU | 2 | 2 | 1 |

All **925 planned queries** were captured, with **no failed or pending queries**.
**306 returned no matching dated direct flight**. Four captures on **CAN–PEN /
PEN–CAN** could not verify fare context and returned no usable dated services;
they remain explicit search gaps, not evidence of no service. **Six PEN–KNO
Lion Air records** reported 24-hour-55-minute durations and were rejected rather
than having their dates repaired. Other valid records in those queries remain.
The candidate gateways **KBR, MKZ and SBW** returned no overlapping international
services for this replay day. Probed destinations outside the returned network
remain gaps; the manifest is not an exhaustive global route list.

With both scopes selected, the explorer contains **1,493 overlapping flights,
117 airports and 1,266 captured fares**. The original domestic bundle is unchanged.

## Fare interpretation

Searches explicitly request **MYR, one adult, economy, one-way, nonstop**. The
collector verifies the displayed currency, passenger count, cabin and trip type
before saving fares. If that context cannot be confirmed, dated schedules stay
available without prices and the query records a `price_error`.
A fare belongs to a single-leg offer for an exact departure
date, flight number, origin and destination. Multiple returned quotes for that
identity reduce to the cheapest positive quote. Different flight numbers remain
distinct, even when their times match; no codeshares are inferred.

Amounts are stored as integer sen (`amount_minor`) with currency, passenger/cabin/
trip context and capture timestamp. No price is assigned from a page minimum or
from a connecting itinerary's total. Unreturned prices remain missing and the UI
shows **Price unavailable**. The flight preview shows the quote context and
capture time; airport boards show each flight's price.

These are **lowest returned quotes in the captured search**, not a guarantee of
the lowest available booking price across sellers. The collector does not open
every booking offer or refresh fares automatically. Required taxes/fees are
included as represented by Google Flights; optional baggage and charges may cost
extra. Australian and Indonesian snapshots are unchanged and have no added fares.

## Search candidates and sources

The manifest contains **31 exact airports and 182 directional airport pairs**.
Both directions are searched for **1–2 November**, retaining previous-day flights
that overlap the replay day. With all Malaysian airports on UTC+8, next-day
departures cannot overlap 2 November; no 3 November searches are needed.

Airport identities and coordinates come from the existing SHA-pinned
[OurAirports snapshot](https://ourairports.com/data/). **KUL and SZB** never merge.
Peninsular airports explicitly use `Asia/Kuala_Lumpur`; Sabah, Sarawak and Labuan
use `Asia/Kuching`. Both zones display **MYT**.

The rural candidates transcribe 38 unsuspended pairs from
[CAAM's published Rural Air Services table](https://www.caam.gov.my/industry/public-service-obligations/current-ras-programme/).
The table describes the 2019–2024 programme, so it supplies historical search
candidates, not proof of service or an airline in November 2026. Its expressly
suspended BKI–KUD and KUD–SDK pairs are excluded. Additional targeted probes
connect KUL, SZB, PEN, JHB, BKI and KCH to named domestic airports. These are
explicitly labelled probes, not published operating routes; the manifest links
Malaysia Airlines' destination page as background only.

The manifest records the source review date and airport source hash. Its route
hash covers the **curated candidate evidence**, not downloaded CAAM HTML. Every
airport resolves to a unique Malaysian IATA identity. A completed search that
returns no matching direct flight means **not returned**, never **no service**.

## Reproduce

```bash
.venv/bin/python scripts/prepare_malaysia_airports.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_google_flights.py --country MY --concurrency 2
.venv/bin/python scripts/prepare_google_flights.py --country MY --prepare-only
```

The resumable captures live in **`.cache/google-flights-malaysia/`**. Keep this
cache to rebuild the same dated prices without new network searches. Its saved
per-query records include exact query URL, source timestamp, script hash,
schedules and associated minimum fares; raw pages and booking tokens are not
stored in the normal cache. Access challenges stop collection; successful
captures remain available and failed/missing queries are reported. No challenge
bypass, paid API or automatic refresh is enabled.

The deterministic runtime bundle is
**`data/reference/malaysia_flights/2026-11-02.json.gz`**. It uses existing compressed
HTTP replay caching; `SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE` can override it for
tests. Missing dates are rejected.

The international manifest uses **14 Malaysian gateways, 124 overseas airports
and 408 directional pairs**, with **925 airport/date queries**. It combines
published [Singapore Airlines/Scoot gateways](https://www.singaporeair.com/en_UK/my/plan-travel/local-promotions/malaysia/),
the [Scoot airport catalogue](https://www.flyscoot.com/flights/en-my/), reciprocal
candidates from the existing Australian/Indonesian manifests, and explicitly
labelled gateway probes. Malaysia Airlines/AirAsia destination pages are
background sources for the probes, not proof of operating nonstop routes.
The manifest's route hash covers curated evidence rather than source HTML.
Nearby airports remain distinct, including KUL/SZB, BKK/DMK and HND/NRT.

International collection searches both directions and the necessary adjacent
origin-local dates, using UTC overlaps with the MYT replay day. Maximum duration
is 24 hours for long-haul services; the domestic eight-hour limit is unchanged.
Foreign boards show their local dates/times, and board events use half-open day
boundaries. Frequency counts are captured schedules, not live movements.

```bash
.venv/bin/python scripts/prepare_malaysia_international.py
PYTHONPATH=.cache/browser-tools .venv/bin/python scripts/prepare_google_flights.py --country MY --scope international --concurrency 2
.venv/bin/python scripts/prepare_google_flights.py --country MY --scope international --prepare-only
```

Keep **`.cache/google-flights-malaysia-international/`** to reproduce the captured
international schedules and fares. The supplement is
**`data/reference/malaysia_flights/2026-11-02-international.json.gz`**;
`SUNTRAIN_MALAYSIA_INTERNATIONAL_REFERENCE` overrides it for tests. Domestic-only
fixtures remain isolated unless the international override is explicit. The
loader merges coverage without double-counting shared airports, retains each
flight's fare, and invalidates the HTTP revision when either bundle changes.

## Validation

Automated checks cover exact flight fare association, minimum selection,
connections/page minima/missing prices, airport identity, both Malaysian zones,
previous-day queries, deterministic gzip, runtime price preservation, HTTP ETags
and date rejection. Browser checks exercise the priced and unpriced previews,
boards, language switching, fullscreen return, East Malaysia, filters, frequency
view, themes and mobile layout. Shared Australian/Indonesian and Melbourne
regressions accompany the change.
