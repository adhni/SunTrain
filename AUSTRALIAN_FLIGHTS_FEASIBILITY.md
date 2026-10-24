# Australian domestic flights: source assessment

Assessed **24 October 2026**, on `codex/australia-flights-feasibility`.

**Outcome: the timetable source milestone did not pass.** The airport map and
scheduled replay are technically feasible, but none of the sources assessed
supplies an Australian domestic timetable with confirmed rights for SunTrain's
public display and downloadable snapshots. No flight dataset or public flight
view is enabled. This is a finding about the assessed sources, not proof that
no suitable source exists.

The agreed scope is an **Australia-wide domestic passenger-flight explorer**,
using free sources first. An older or partial, clearly dated timetable pilot is
acceptable. A recorded-flight replay is a separate product choice.

## Downloaded and checked

Research downloads remain in the ignored `.cache/australia-flights-audit/`
directory. The [source register](data/sources/australian_flights_feasibility.json)
records URLs, checksums, coverage, missing fields and decisions. Restricted
timetable files are not included in the repository or served by the app.

| Source | Verified result | Decision for a free timetable pilot |
| --- | --- | --- |
| [OurAirports](https://ourairports.com/data/) | Public-domain CSV; pinned to commit `3b10d0b967cc04c62eb6411939e4e9936a88e701`. It contains 2,795 Australian records, including 157 non-closed records marked `scheduled_service=yes`. Those 157 have valid coordinates, nonempty IATA codes and no duplicate IATA codes. MEL and AVV are separate airports. | Suitable airport geography. There are no individual flight times or airport timezones. The scheduled-service flag does not establish current flight coverage. |
| [Rex Queensland schedules](https://rex.com.au/Schedules/default.aspx) | The linked six-page PDF downloads successfully. It contains numbered, multi-stop regional services, operating weekdays and leg departure/arrival times. It is effective **to 15 November 2026**; an explicit start date was not established. It also contains replacement bus information during the Burketown closure. | [Terms: Proprietary Rights / Copyright](https://rex.com.au/site_terms.aspx) limit reuse to private/personal and specified travel-professional uses without written permission. No permission for SunTrain publication is established. Queensland-only coverage would require a clear regional label. |
| [FlyPelican timetable](https://www.flypelican.com.au/timetable) | The rendered page contains flight numbers, endpoints, clocks and weekday labels. No effective-date interval was established. Plain HTTP downloads returned 403, although the page and policies were readable through web retrieval. | [Terms, sections 3 and 7](https://www.flypelican.com.au/policy/1) allow personal copies and require written permission for content reuse. This candidate does not pass. Plain-text weekday labels must not be interpreted as seven operating days: the active-day styling needs separate inspection. |
| [Jetstar domestic NW12 timetable](https://www.jetstar.com/_/media/Jetstar%20Australia/Files/PDF/Flight%20Schedules/NW12_Timetable_Domestic.pdf) | The ten-page PDF downloads successfully. Its internal header gives **28 October 2012–30 March 2013**, published as at **9 October 2012**. Fields include flight number, effective/discontinue dates, weekday restrictions, airport codes, equipment and local clocks. | [Terms, section 3](https://www.jetstar.com/au/en/terms-of-use) restrict copying/publication without consent, subject to statutory exceptions. No reusable licence or SunTrain permission is established. A recent search crawl date must not be mistaken for the timetable's validity date. |
| [Qantas timetables](https://www.qantas.com/en-au/where-we-fly/timetables) | The official page advertises timetable information, but no permitted bulk snapshot was established. | [Website terms, section 2](https://www.qantas.com/en-au/help/policies/website-terms-of-use) restrict copying, storage and publication without consent, subject to statutory exceptions. No qualifying dataset was obtained. |
| [BITRE Domestic Airlines — Top Routes and Totals](https://data.gov.au/data/dataset/c5029f2a-39b3-4aef-8ae1-73e7962f6170) | The official catalogue API and city-pair CSV download successfully. The catalogue specifies **CC BY 3.0 Australia**. The CSV has **29,676 rows**, organised by city pair and month. Fields include passengers, aircraft trips, seats, load factor and distance. | Suitable for labelled aggregate statistics. It has no individual flight number, airline, departure or arrival time. Monthly totals cannot become scheduled flights. City-pair aggregates must not be silently assigned to a particular airport when a city has several airports. |

The terms findings are source-selection decisions based on the published terms;
they do not assert that every possible use of timetable facts is prohibited.
There is no separate reuse agreement available in this workspace.

## Other sources checked

- The government's [international timetable summary](https://www.infrastructure.gov.au/infrastructure-transport-vehicles/aviation/international-aviation/air-services-agreements-arrangements/international-airlines-timetable-summary)
  lists approved international routes, weekly frequencies and capacity. It is
  outside the domestic scope and lacks individual flight clocks.
- [Airservices Flight Summary Data](https://data.airservicesaustralia.com/node/586)
  requires a subscription and is delivered by request for an airport/date range.
  Its documented clocks are actual takeoff/landing times, rather than a public
  scheduled departure/arrival feed. No price, access or redistribution agreement
  was obtained.
- [OpenSky's FAQ](https://opensky-network.org/about/faq) distinguishes recorded
  positions and inferred endpoints from commercial schedules. Its current
  [terms](https://opensky-network.org/about/terms-of-use) require a written
  agreement for operational REST API use, including nonprofit products.
- [ADSB.lol historical archives](https://www.adsb.lol/docs/open-data/historical)
  are published under ODbL 1.0 and are a credible candidate for a future
  **recorded-flight** pilot. Australian trace coverage, airport assignment and
  endpoint timing accuracy have not been validated here. The archive does not
  establish scheduled departure times or complete airport boards.
- [Aviationstack pricing](https://aviationstack.com/pricing) lists 100 requests
  on the personal/noncommercial free tier, and places flight schedules and
  historical access on paid tiers. The listed Basic monthly price is $49.99.
  Australian coverage, endpoint entitlements, snapshot retention and browser
  redistribution would need verification before selecting a subscription.

## What permits implementation to resume

A candidate must supply all of the following for at least one coherent dated
week, with partial airline/airport coverage disclosed:

1. Confirmed public-display and snapshot-redistribution rights, through an open
   licence or an agreement covering SunTrain's actual use.
2. Operating airline/flight identifiers, origin/destination airports, scheduled
   departure and arrival times, valid dates, and operating-day restrictions.
3. Enough timezone/date information to resolve each event to UTC without
   guessing arrival dates or applying one UTC offset to all Australian airports.
4. A downloadable or otherwise reproducible source whose bytes, validity and
   omissions can be recorded and reconciled against the prepared data.

No current source meets all four. An airline permission request could use the
Rex PDF as a concrete regional candidate, but permission alone would not
establish its start date or nationwide coverage. No publisher has been contacted
and no paid account has been created.

## Implementation boundary once a source qualifies

- Add **Australia · Flights** inside the existing explorer. Reuse playback,
  themes, both languages, airport selection and the expanded-board layout.
  Add airline/airport filters and arrivals alongside departures. Unsupported
  airports say **Timetable unavailable**, rather than implying no flights.
- Give each airport an explicitly verified IANA timezone. OurAirports has no
  timezone field; avoid a state-only mapping, which misses regional exceptions.
  Boards use airport-local time and flight details use each endpoint's local
  time. Keep the national timeline in labelled Melbourne time.
- Use a midnight-to-midnight Melbourne day and include overlapping flights
  from adjoining departure dates. Existing transit uses a 03:00 business-day
  boundary, so aviation needs its own date-window adapter.
- Add scheduled arrival indexing: the existing station board deliberately omits
  terminal arrivals. Count operating flight legs once, retain marketing
  codeshares as aliases, and distinguish multiple legs sharing a flight number.
- Render one compact, outlined plane per active leg. Animate along a great-circle
  path labelled **Scheduled replay · illustrative paths**. Show route lines on
  selection to control clutter. Scheduled block times must not be presented as
  observed takeoff/landing times.
- Validate source calendars, codeshares, overnight arrivals, Perth/eastern-state
  differences, Adelaide's half-hour offset, daylight-saving changes and regional
  timezone exceptions. Check airport boards and playback on desktop/mobile and
  preserve existing transit tests.

The useful free alternatives are a static airport/aggregate-route explorer or an
open historical recorded-flight replay. Either changes the chosen experience;
neither has been substituted for the requested timetable pilot.
