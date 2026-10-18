# Netherlands expansion

## Implemented scope

One nationwide location, `netherlands`, covering **1–7 June 2026** in `Europe/Amsterdam`. Domestic NS Intercity/Sprinter and regional passenger trains reuse the existing prepared-city loader, compact shared schedules, map, filters, themes, fullscreen and city-aware Overview. Passenger sizing and heatmaps are unavailable.

The pinned feed's eight domestic rail agencies are NS, Arriva, Blauwnet Arriva, Blauwnet Keolis, R-net NS, R-net Qbuzz, RRReis Arriva and RRReis Keolis. Route type **2** is required. Replacement buses, other buses, metros, trams, ferries and international operators are excluded. Arriva's two RE18 routes (`124366`, `124367`) extend into Belgium/Germany and are excluded as complete routes; their journeys are never truncated or relabelled domestic.

## Verified source

- [OVapi nationwide historical archive](https://gtfs.ovapi.nl/nl/archive/).
- Actual ZIP: `https://gtfs.ovapi.nl/nl/archive/NL-20260529.gtfs.zip`.
- Snapshot modified **29 May 2026, 17:04:59 UTC**; downloaded and inspected **18 October 2026**.
- Size: **219,126,362 bytes**. SHA-256: `7b5cb589fb42965b768e6e73c2fedb8639cb417426e5b015f2d2b21d28e6254e`.
- `feed_info.txt`: OVapi, version **9375**, declared validity **29 May–12 December 2026**. Each trip's actual dates come from `calendar_dates.txt`; broad feed validity alone is not a service guarantee.
- A single pre-period snapshot supplies this pilot. All eight selected agencies have active services throughout the week and adjoining dates needed for overnight departures. This is a timetable snapshot applied to its valid dates, not a reconstruction of later timetable revisions, cancellations or every historical disruption.
- No `frequencies.txt` is present. There are native shapes and stop/shape distance anchors for every selected trip.

The raw national ZIP is preparation-only. It includes other modes and foreign services; it is never sent to the browser. The bundled reference is `data/reference/netherlands/2026-06-01.json.gz`. The server and browser retain the existing one-day, selected-mode behaviour and shared stop/timing representation.

The prepared week is **942,554 bytes gzip**, with **4,162 shared timetable patterns**. Daily departures are **5,960 / 5,977 / 5,985 / 5,973 / 5,737 / 5,249 / 4,652** from Monday through Sunday. No selected timetable trips were omitted, and every occurrence belongs to one 03:00–03:00 start-day window.

The measured Monday HTTP download is **544,917 bytes gzip** (2,908,787 bytes JSON), with 5,960 service references and 1,589 shared timetable patterns. It contains no expanded per-service stop arrays. This is a local payload measurement, not a hosted latency benchmark.

## Geometry and display colours

The audited selected source patterns use **326 shapes with 115,180 points**. Native distance anchors are tried first. A sizeable subset contains inaccurate distance anchors, so this source explicitly opts into `native_or_ordered_per_leg`: match the complete stop order against the **same published shape** within the existing **150 m** limit. If that fails, retain only native legs whose two endpoints meet the limit and leave the others as gaps. This does not route across disconnected shapes, widen tolerances or invent station connectors. Other cities keep their existing geometry method.

Source shapes are a geographic reference, not evidence of individual running tracks. Some sections are sparsely sampled. No ProRail or OpenStreetMap railway database was substituted; those sources would require separate matching and attribution if used later.

Across the week's actual service occurrences, **336,403 of 340,377 legs (98.8%)** have usable source geometry; **3,974 legs** remain gaps. There are **278 distinct geometry cases**, corresponding to **430 shared timetable patterns**, with at least one gap. On Monday, 394 of 5,960 trips have a gap somewhere; only two have no usable moving section. Across the week, 56 trip occurrences have no usable moving section and appear only at their scheduled stops. Geometry recovery changed no service identifiers, stop orders or scheduled times.

Rail `route_color` values are blank in this snapshot. SunTrain therefore uses an explicit display palette, grouped by operator family: NS `#003082`, Arriva `#008C95`, Blauwnet `#006BB6`, R-net `#C8102E`, RRReis `#71368A`. These are display choices, not a claim of official line colours. A populated source colour takes priority. Preserve route IDs and complete route/series labels so separate regional services and branches do not collapse under labels such as “Intercity”. Journey identifiers remain the GTFS trip IDs.

## Usage and attribution

The [OVapi README](https://gtfs.ovapi.nl/README) permits use of these feeds, describes their conversion from agencies' open NDOV data, provides the service on a best-effort basis and prohibits impersonating the agencies. Keep operator/OVapi/NDOV attribution, link these actual conditions and retain SunTrain's independence/estimated-position text. Do not relabel the source as CC BY, OGL or another licence it does not name. No official logos or map artwork are included.

Preparation identifies SunTrain through its User-Agent, requests gzip transport encoding, reuses its cached ZIP and verifies the archive hash. Runtime schedule loading requires no external API account or live tracking service.

## Validation

On 18 October 2026, **258 Python tests** and **34 JavaScript tests** passed. Netherlands-specific checks cover domestic scope, colours, all seven calendars, unique start-day assignment, shared schedules, geometry endpoint distances, local time and runtime independence from the Melbourne passenger warehouse. The default geometry behaviour for other sources remains covered by regression tests.

Local Chrome checks passed for nationwide playback at 2,000×, NS and regional route filters, service details/follow, operator-filtered Overview, Sunday schedules, shared downloads between tabs, fullscreen, both themes, a 390 px viewport and switching back to Toronto, with no page errors. The Randstad map was visually inspected around Amsterdam, Utrecht, Rotterdam and The Hague. No hosted performance benchmark was run for this addition.

## Rebuild and future expansion

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/prepare_netherlands_replay.py
```

Use `--cache` and `--output` to override paths, and `SUNTRAIN_NETHERLANDS_REFERENCE` to override the runtime bundle. The default cache is `.cache/netherlands/`. Preparing the full national archive can take several minutes; source ZIP scanning happens offline, never during a visitor's replay download.

For a longer period, first audit dated archives, per-trip calendars and the selected operators across every proposed day. Preserve source capture/validity/hash metadata, check whether additional snapshots are required and retain one 03:00–03:00 start-day assignment per occurrence. Re-audit explicit route/operator scope whenever changing the source pin, particularly international and replacement services. Do not merely extend the date picker or use a current feed for past dates.

Amsterdam GVB and Rotterdam RET metros are the next candidates. This archive contains five route-type-1 entries for each agency, but their complete calendars and geometry have not been prepared or validated here. Restrict by agency as well as mode: there are also four route-type-1 entries under NS. Trams, buses and ferries need their own geometry, frequency, service-volume and colour audit before enabling them.

The linked [NS occupancy listing](https://data.ndovloket.nl/bezetting/ns/) exposes recent October files; availability and journey-ID matching for June 2026 have not been established. Predicted occupancy categories must remain labelled forecasts and must not become fabricated passenger counts. [NS station ridership](https://nieuws.ns.nl/flink-meer-reizigers-op-stations-door-nieuwe-dienstregeling-en-woningbouw-in-de-buurt/) describes average station use for 2025, not these trains' individual loads or a June 2026 daily passenger heatmap. Passenger features remain optional future work.
