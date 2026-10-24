# Indonesia international flights

Choose **Indonesia · Flights**, then **Flights → International** or **Both**.
Domestic remains the opening selection. The existing domestic week is unchanged.
Only flights with exactly one Indonesian endpoint are included; overseas domestic
networks and connecting itineraries are excluded. Flights are scheduled replays,
not live tracking. The week is **2–8 November 2026**, measured in **Asia/Jakarta**.

Changing the flight selection filters the map, airport boards, airline selection
and Overview locally, with no new flight download. The map fits overseas
connections when switching to International or Both. Airport labels retain
collision handling; visibility is optional and arcs appear only for selections.
Both departure and arrival boards use airport-local dates and offsets, including
foreign daylight saving and half-hour zones. Fullscreen boards, flight previews,
explicit timeline seeking, five themes and English / Indonesian remain shared.

## Sources and boundaries

The pinned [Kemenhub 2023 statistical book](https://hubud.kemenhub.go.id/hubud/website/assets/file/bukustatistik/9a4eaeb68ab0e5bb3be1a8b5202ccb90.pdf),
PDF pages 41–43, supplies international route **candidates**, never evidence of
current service. Both directions are searched. CGK and DPS are also paired with
all overseas endpoints in that table, and DPS–AVV is probed independently of MEL.
This produces **334 directional candidates**, **16 Indonesian airports** and
**64 overseas airports**. The table's MDC–DPS row is excluded because both ends
are Indonesian, with the reason preserved in the manifest.

Airport identities and coordinates use the same pinned OurAirports CSV as the
domestic implementation, supplemented with explicit airport-local IANA zones.
CGK/HLP, MEL/AVV, BKK/DMK and NRT/HND stay separate. Only endpoints with returned,
validated dated flights are shown as served. The manifests preserve source hashes
and page evidence. OurAirports is public domain; that licence does not cover the
Google or airline schedule material.

Flight times come from public, airport-specific Google Flights nonstop searches.
The collector needs no account or API key. It keeps resumable caches, query URLs,
capture timestamps, page hashes and rejected-record diagnostics. It stops on an
access challenge rather than bypassing one. Successful captures remain usable
when other searches fail. Empty searches mean **not returned**, never no service.

The manifest is historical and limited to its listed overseas endpoints. New
routes, additional foreign airports, seasonal services, charter operations and
carriers not returned by Google may be missing. Completing the query manifest
does not establish complete international coverage.

## Dates and validation

For each origin, searches cover every local departure date intersecting the
Jakarta replay week plus up to 24 hours of carry-in. This means dates between
**31 October and 9 November**, depending on the origin, rather than forcing one
local calendar window on every country. There are **2,906 planned dated searches**.

International durations must be **1 minute–24 hours** and agree with the source's
published duration within one minute. Domestic's 8-hour maximum remains unchanged.
Invalid records are omitted individually, with valid flights from the same query
retained. Repeated flight identities are deduplicated; conflicting identities are
rejected, and distinct flight numbers remain separate. Batik Air ID and OD have
distinct filter labels and colours despite the shared source name. Unknown aircraft stay
unknown. Great-circle paths are illustrative, not recorded flight tracks.

A selected day retains flights departing before its UTC end and arriving at or
after its UTC start. Boards own events inside the half-open day window, so a
midnight arrival appears on the new day's arrival board. The main clock stays
WIB; foreign boards show their local date and GMT offset. Overnight arrivals are
not relabelled as same-day flights.

## Rebuilding

With preparation-only Playwright and pypdf dependencies available:

```sh
PYTHONPATH=.cache/flight-tools python3 scripts/prepare_indonesia_international.py
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py --country ID --scope international --concurrency 2
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py --country ID --scope international --prepare-only
```

The first command deterministically rebuilds
`data/sources/indonesia_international_routes.json`. The second resumes successful
queries in `.cache/google-flights-indonesia-international`, using two search pages
and recycling Chrome every 50 queries. The third rebuilds only from those caches.
No collection runs in the app. Prepared output is
`data/reference/indonesia_flights/2026-11-02-international.json.gz`, separate from
the unchanged domestic bundle. Gzip output uses a fixed timestamp and no filename.

The loader merges exact airport identities and adds each service's `flight_scope`.
It rejects foreign-to-foreign flights and conflicting airport/flight records.
HTTP revision keys include both bundles, so replacing either invalidates replay
cache entries. `SUNTRAIN_INDONESIA_INTERNATIONAL_REFERENCE` overrides only the
international bundle. Setting `SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE` alone isolates
a custom domestic reference; explicitly set both to merge custom references.

## Captured coverage and checks

The international bundle contains **4,004 departures** owned by the
Jakarta calendar week, plus **74 carry-ins**: **4,078 overlapping services**,
**65 airports** (**13 Indonesian + 52 overseas**), **204 directional
routes** and **58 carrier codes**, in **251,964 bytes gzip**. Overseas endpoints
span **23 country/territory codes**. Source airline names are preserved;
ID and OD are separate carriers despite sharing the Batik Air name.
Daily departures are 578 / 560 / 575 / 558 / 587 / 558 / 588.

All **2,906 planned airport/date searches** were captured across **334 directional
candidates** and **80 airports**. There are **no failed or pending queries**.
**1,407 searches returned no matching flights**. **27 invalid source records**
on PEN–KNO exceeded 24 hours; valid records in those same queries were retained.
No source times were repaired or invented. A zero below means no captured result,
not proof that a service does not operate.

| Overseas region | Returned airports | Directional routes | Week departures |
| --- | ---: | ---: | ---: |
| Australia, New Zealand & Pacific | 10 | 26 | 545 |
| Central Asia | 0 | 0 | 0 |
| East Asia | 16 | 52 | 689 |
| Europe | 1 | 2 | 4 |
| Middle East | 7 | 24 | 335 |
| North Africa | 1 | 2 | 4 |
| South Asia | 3 | 6 | 58 |
| Southeast Asia | 14 | 92 | 2,369 |

| Indonesian island group | Candidate airports | Returned airports |
| --- | ---: | ---: |
| Sumatra | 5 | 4 |
| Java | 6 | 4 |
| Kalimantan | 1 | 1 |
| Sulawesi | 2 | 2 |
| Bali & Nusa Tenggara | 2 | 2 |
| Maluku | 0 | 0 |
| Papua | 0 | 0 |

Returned Indonesian airports are **BPN, BTJ, CGK, DPS, KNO, LOP, MDC, PDG,
PKU, SRG, SUB, UPG and YIA**. BTH, HLP and KJT were searched but returned no
matching validated international flights. Maluku and Papua have no international
candidates in this manifest; their domestic services remain available separately.
Central Asia's candidate returned no dated flights. Unlisted overseas endpoints
remain unsearched, not assumed absent. This is not nationwide or worldwide flight
completeness.

The two Indonesian bundles together contain **17,590 owned departures** and
**82 carry-ins**, covering **159 distinct airports**. Domestic's original bundle
and Australia's existing bundle rebuild byte-identically and remain unchanged.
The international bundle also rebuilds byte-identically from cached captures.

Validation: **91 focused Python tests and 75 JavaScript tests** cover exact
identity, long-haul and half-hour/DST clocks, origin-local adjacent-date searches,
all seven replay dates, foreign endpoint constraints, custom reference isolation,
HTTP revisions/caching, duplicate records, duration rejection, scope filtering,
airport event ownership and existing transit behaviour. Browser checks cover
international and domestic scope switching, foreign boards, previews, fullscreen,
all seven dates, airline filters, English/Indonesian, five themes and mobile.
Australian flight and Melbourne map browser regressions also passed.
