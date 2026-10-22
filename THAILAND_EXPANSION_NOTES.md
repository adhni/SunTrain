# Thailand — Bangkok rail pilot

Implemented on `codex/thailand-rail`. Select **Bangkok** for **12–18 October 2026**, the same display week as Malaysia. This is Bangkok coverage, not a nationwide Thailand train replay. Existing playback, filters, source line colours, details, themes and city Overview are reused.

## Included

| Network | Lines | Transport filter |
| --- | --- | --- |
| BTS | Sukhumvit, Silom | BTS / MRT |
| MRT | Blue, Purple | BTS / MRT |
| Automated / monorail | Gold, Yellow | Gold / Yellow lines |
| SRT suburban | Dark Red, Light Red | SRT Red Lines |

The compact week contains **22,704 estimated journey occurrences/sections**: **3,687 on normal weekdays**, **2,652 on 13 October and each weekend day**. The source's 13 October holiday exceptions switch weekday templates to weekend templates. All departures are **frequency-based estimates**, not actual individual train departures. Blue Line sections and BTS short workings remain sections as supplied; counts must not be described as distinct physical trains or complete end-to-end services.

The week is **139,676 bytes gzip**, with **36 shared timing patterns, 30 stop patterns and 152 station/platform records**. No browser expansion of every trip's stops; the source's 41.6 MB ZIP stays in ignored `.cache/thailand/`.

## Validated source and reuse

- **Producer:** Office of Transport and Traffic Policy and Planning, Thailand (OTP / สนข.).
- **Official open-data policy:** https://namtang-api.otp.go.th/opendata — explicitly links CC BY 4.0 and the GTFS download.
- **Download:** https://namtang-api.otp.go.th/download/namtang-gtfs.zip
- **Feed version:** `20261021`; retrieved **22 October 2026**.
- **SHA-256:** `a451d1081c6008fb2c94a0c8c0be7172c2dd320adacb3a3db1b1390a1bf50ce7`.
- **Licence:** https://creativecommons.org/licenses/by/4.0/ — applies to the supplied timetable, shapes, station positions and route colours; OTP attribution and SunTrain changes are retained.

`feed_info.txt` covers 1 January–31 December 2026. Selected service calendars have broad 2023–2026 validity. This is the **October snapshot applied to source calendars**, not proof that every line or timetable operated unchanged since 2023, and not a reconstruction of every historical disruption. No schedules are backdated to 2024. Timezone is **Asia/Bangkok (UTC+7)**, using a 03:00–03:00 business window.

## Template handling and exclusions

The feed encodes several urban railways as GTFS type 0, so scope uses explicit route/agency/type combinations, not a generic tram filter. Eight selected route IDs are `1`, `2`, `3`, `4`, `2025`, `2026`, `2027`, `2224`.

Of 52 templates in these lines, **40 are retained**. Six have zero running time between distinct stations; two have conflicting times for an identical route/calendar/stop sequence; four duplicate another timing definition with less detailed headway windows. For otherwise identical timing templates, keep the detailed peak/off-peak definition once. Every excluded trip ID and reason is retained in `metadata.excluded_templates`. No alternative clock values are invented.

The existing headway helper checks half-open windows, positive headways and overlap. Source first-stop dwell is preserved while placing the first **departure** at the frequency window's start. Each estimated occurrence belongs once to its departure business day, including after-midnight calls. Frequency-based status is retained in service details and Overview. English display names come directly from the feed's bilingual fields.

## Railway geometry

Use each trip's own directional GTFS shape and the existing ordered stop projection, with a **150 m** matching limit. These are OTP-provided railway alignments; no OSM-derived graph or new licensing layer is needed for the implemented pilot.

The Red Line source shapes do not match their **Krung Thep Aphiwat approach** within that limit. Match valid adjacent stop pairs against their own directional shape and leave the unmatched approach empty. All other selected networks have mapped legs. **99.58% of weekday / 99.51% of holiday-weekend service-weighted legs** are mapped; **259 approach legs/day** remain gaps. Vehicles are hidden during those legs. The exact route/stop pairs are retained in `metadata.unresolved_stop_pairs`; do not broaden matching or draw straight connectors to hide this.

## Not implemented and next steps

1. **National SRT trains:** the same feed is not a usable national timetable. Many records contain only Bangkok-area portions of advertised intercity journeys; newer full-length entries have placeholder minute-by-minute clocks. For example, trip `7932` advertises Bangkok–Chiang Mai with `00:01` to `00:07` times. The source also contains duplicate train numbers. Do not enable all route-type-2 records or reinterpret these placeholders as departures. The [official SRT timetable](https://www.railway.co.th/SRTTimetable/StationList) and [SRT timetable matrix](https://ttsview.railway.co.th/timetable_modern.php?line=1&ln=en) are follow-up sources; the matrix data requires its Turnstile/JWT access flow. The older [government timetable catalogue](https://data.go.th/en/dataset/after32) was found, but its API download returned 403 in this environment. No validated historical national timetable or connected nationwide geometry was obtained in this pilot.
2. **MRT Pink / Muang Thong branch:** source templates have zero running time between distinct stations and cannot support plausible animation. Obtain corrected timing templates; retain the published branch/service calendar only once verified.
3. **Airport Rail Link:** one direction has implausibly short running times, including a segment above 220 km/h in the template. Excluded as a whole rather than adding one direction or mirroring the other direction's times. Obtain corrected operator station timings for both directions.
4. **Red Line approach geometry:** verify the source station/shape mismatch at Krung Thep Aphiwat using an independent station/railway reference. Existing clocks and all remaining path segments are unchanged.
5. **Buses, BRT and ferries:** present in Namtang but excluded. Audit their own timing quality, duplicates, shapes and browser volume before enabling them. Retain each source route's colours.
6. **Passenger data:** optional future work. Station/line totals must not be presented as actual individual train loads.

## Rebuild and checks

```bash
./.venv/bin/python scripts/prepare_thailand_replay.py
./.venv/bin/python -m pytest tests/test_thailand.py -q
```

Keep the pinned ZIP in `.cache/thailand/namtang-gtfs.zip` for an identical rebuild: the producer URL rolls forward, and the preparer stops if its hash changes. Filtered template ZIPs are preparation-only. `SUNTRAIN_BANGKOK_REFERENCE` overrides the compact runtime bundle. There are no runtime source API requests or new infrastructure.
