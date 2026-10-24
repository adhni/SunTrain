# Indonesian domestic flights

Choose **Indonesia · Flights** for **2–8 November 2026**. This is a domestic
schedule snapshot, not live aircraft tracking or a complete list of operational
movements. Indonesia flights are separate from Jakarta and Java rail/transit.

The map reuses compact airline-coloured planes and airport code labels. Click an
airport or choose Airports to browse departures and arrivals, expand the board,
page through flights and preview a journey. Only Go to departure / arrival moves
the timeline. Filters run locally. Airport visibility remains optional, and route
arcs appear only for selected airports, routes or flights. Existing themes and
English / Indonesian interfaces apply.

International connections are available through the Flights filter; see the
[international flight notes](INDONESIAN_INTERNATIONAL_FLIGHTS_NOTES.md). The counts
below describe the unchanged domestic snapshot.

## Captured week

The bundle contains **13,586 departures** owned by the Jakarta calendar week,
plus **8 overnight carry-ins**: **13,594 overlapping services**, **107 airports**,
**487 directional routes** and **13 airlines**, in **637,642 bytes gzip**.
Daily departures are 1,950 / 1,908 / 1,976 / 1,928 / 1,953 / 1,925 / 1,946.

All **6,930 planned airport/date searches** were captured across **770 candidate
routes** and **149 searched airports**. There are no failed or pending queries.
**3,075 searches returned no matching direct flights**; **20 contained only
unusable records**. **131 source records** were rejected for durations outside
the accepted range. Other valid flights in those searches remain included.
Query completion is not a measure of nationwide flight completeness.

| Island group | Candidate airports | Airports with captured flights |
| --- | ---: | ---: |
| Sumatra | 35 | 20 |
| Java | 18 | 11 |
| Kalimantan | 26 | 16 |
| Sulawesi | 23 | 16 |
| Bali & Nusa Tenggara | 18 | 17 |
| Maluku | 15 | 11 |
| Papua | 35 | 16 |

The catalogue has **170 candidates**; **21 have no resolved route in the search
manifest**. Missing regional routes and unreturned flights remain gaps. The
snapshot includes separate CGK/HLP and YIA/JOG services. Carriers are Garuda
Indonesia, Citilink, Lion Air, Batik Air, Wings Air, Super Air Jet, Indonesia
AirAsia, Sriwijaya Air, NAM Air, Trigana Air, TransNusa, Pelita Air and FlyJaya.

## Airport identity and clocks

All searches use individual IATA codes. **CGK and HLP**, and **YIA and JOG**, stay
separate in the catalogue, query inputs, route keys, flight identities, positions
and boards. Airports without returned flights are not advertised as served.

The main replay day runs **00:00–00:00 Asia/Jakarta (WIB)**. Airport boards and
flight endpoints use airport-local time: **WIB, WITA or WIT**. Western and central
Kalimantan use Asia/Pontianak (WIB), not the eastern Kalimantan zone. The query
window covers **1–9 November**, including preceding overnight flights and early
9 November eastern departures that overlap the final Jakarta day. Board events
use a half-open daily window; arrivals exactly at midnight belong to the new day.
An overlapping flight can appear on two replay days, but its departure or arrival
is counted only on the day containing that event.

## Sources and coverage

- Airport identities and coordinates: [pinned OurAirports catalogue](https://raw.githubusercontent.com/davidmegginson/ourairports-data/3b10d0b967cc04c62eb6411939e4e9936a88e701/airports.csv), public domain. The preparation script validates its SHA-256.
- Route candidates: [Kemenhub 2023 aviation statistics](https://hubud.kemenhub.go.id/hubud/website/assets/file/bukustatistik/9a4eaeb68ab0e5bb3be1a8b5202ccb90.pdf), PDF pages 34–37, and public domestic-route sections for the fourteen hub airports in the [official directory](https://hubud.kemenhub.go.id/daftar-bandara). Historical routes and published frequencies identify searches to attempt; they do not establish operation in November 2026.
- Dated flight times: public [Google Flights](https://www.google.com/travel/flights) airport-specific one-way nonstop searches. The collector parses JSON already embedded in the rendered page without executing the source data. No API key or signed-in profile is required; playback uses only the prepared local bundle.

The manifest includes the official pairs in both directions plus every directional
pair among CGK, HLP, SUB, DPS, KNO, UPG, BPN, YIA, BTH, KOE, MDC, AMQ, SOQ and DJJ.
It contains **170 candidate airports and 770 directional search routes**. Scheduled
service flags in OurAirports are catalogue hints, not confirmation of service on
our dates. Some officially named destinations cannot be matched to a unique
airport in the pinned catalogue; these are retained as unresolved evidence.

Source frequencies without exact dated times never become animated flights.
Small regional and perintis airlines may be absent from Google Flights. Empty
results mean **no matching flight returned**, not proof of no service. Completed
queries do not imply nationwide completeness. There is no international, cargo,
charter or live-position layer and no automatic refresh.

Each query retains its airport codes, local departure date, URL, capture time,
page-data hash and result status. Repeated options with the same date, flight
number and airport pair are deduplicated; conflicting records fail validation.
Distinct flight numbers are preserved without inferred codeshare consolidation.
Invalid source records are omitted individually, keeping other valid departures
from the same search. Conflicting valid versions of one flight are both omitted;
query-level rejection diagnostics distinguish unusable source records from empty
results and failed searches.
Flight duration is checked against UTC timestamps derived from explicit IANA
zones. One-minute to eight-hour domestic legs are accepted. Aircraft are labelled
unknown when unspecified. Paths are illustrative great-circle arcs.

The bundle's `metadata.coverage` records planned/captured/missing/failed queries,
searched/returned airports and routes, and counts by island group. `queries`,
`uncollected_queries`, `failed_queries` and `unresolved_airports` retain the
underlying audit. Overview displays week-level search counts alongside the
selected day's departure totals. Source citations do not imply an open licence
for Google or airline timetable material.

## Rebuild

Preparation-only tools are Playwright with Chrome and pypdf; neither is a new
runtime dependency. Use the existing local tool directories when available:

```bash
PYTHONPATH=.cache/flight-tools python3 scripts/prepare_indonesia_airports.py
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py --country ID
PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py --country ID --prepare-only
```

The first command rebuilds `data/sources/indonesia_flights_routes.json` from
cached official references; source hashes and evidence are included. The second
resumes successful cached searches in `.cache/google-flights-indonesia`, using
two concurrent pages and a one-second pause per page. Browser caches and JavaScript heaps are bounded,
and the browser is recycled every 50 queries to contain memory/disk growth.
A 128 MB free-space guard stops collection before exhausting local disk space;
cache and snapshot files are published atomically. A file lock prevents overlapping
collectors for the same cache; a disconnected network stops collection rather
than submitting the remaining queue while offline. Ordinary failures are
recorded separately and remain eligible for a later retry. Access challenges
stop collection; do not bypass them. After an interrupted run, `--prepare-only`
builds a clearly partial snapshot from captured results.

The output is `data/reference/indonesia_flights/2026-11-02.json.gz`. Compression
uses a fixed timestamp and no filename; rebuilding from unchanged caches is
byte-identical. `SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE` can select a local reference
without changing Australia's reference or its legacy 2013 tests. The shared
adapter defaults to Australia for compatibility; country-specific collection is
selected through `--country ID`. Replay downloads retain the existing endpoint
and data format, with a `replay_kind: "flights"` capability. Cache revision 6
invalidates older payloads that lack that capability.

## Validation

Python checks cover exact airports, manifest identities, all Indonesian zones,
western Kalimantan, short flights, overnight dates, midnight arrivals, adjacent
search dates, duplicate/conflicting source records, honest coverage counts,
reproducible compression, all seven replay days and HTTP caching/date limits.
JavaScript checks cover local labels and half-open departure/arrival ownership.
The Indonesia browser test checks map clicks in all three zones, distinct CGK/HLP
boards, airline filtering, fullscreen paging, preview/seek/back behaviour, five
themes, Indonesian, mobile layout, seven dates and return to Australian flights.
Australian flights and Melbourne map browser checks provide regression coverage.

Final checks: **79 focused Python tests**, **73 JavaScript tests**, and the
Indonesia, Australian flights and Melbourne map browser checks passed.
Both country snapshots rebuilt byte-identically from unchanged cached captures.
