# Malaysian domestic flights and captured fares

**Malaysia · Flights** is a separate domestic schedule replay for **2 November
2026**, with a midnight-to-midnight **MYT** timeline. It leaves Malaysia/Kuala
Lumpur rail views and the existing Australian/Indonesian flight snapshots intact.
This is a partial dated capture, with illustrative paths rather than observed
aircraft positions.

## Captured coverage

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

## Fares

Searches explicitly request **MYR, one adult, economy, one-way, nonstop**. The
collector verifies the displayed currency, passenger count, cabin and trip type
before saving fares. A fare belongs to a single-leg offer for an exact departure
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
bypass, paid API, international collection or automatic refresh is enabled.

The deterministic runtime bundle is
**`data/reference/malaysia_flights/2026-11-02.json.gz`**. It uses existing compressed
HTTP replay caching; `SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE` can override it for
tests. Missing dates are rejected. `--country MY --scope international` is
explicitly unsupported.

## Validation

Automated checks cover exact flight fare association, minimum selection,
connections/page minima/missing prices, airport identity, both Malaysian zones,
previous-day queries, deterministic gzip, runtime price preservation, HTTP ETags
and date rejection. Browser checks exercise the priced and unpriced previews,
boards, language switching, fullscreen return, East Malaysia, filters, frequency
view, themes and mobile layout. Shared Australian/Indonesian and Melbourne
regressions accompany the change.
