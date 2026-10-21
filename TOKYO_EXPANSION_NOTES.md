# Tokyo — JR East and subway pilot

## Included

Select **Tokyo**, **20 October 2026**. This first test includes **9,998 scheduled journey sections**, **47 JR East conventional route variants**, **848 station records**, line colours and original train numbers. Major lines include Yamanote, Chūō Rapid, Chūō–Sōbu Local, Keihin-Tōhoku–Negishi, Saikyō–Kawagoe, Shōnan–Shinjuku, Jōban, Tōkaidō, Yokosuka, Keiyō and Narita Express. The feed also represents outer Kantō branches. This is the feed's JR East coverage, not every JR East service across Japan.

The same dated source now adds **7,474 subway journey sections**: Tokyo Metro's **Ginza, Marunouchi (including its branch), Hibiya, Tōzai, Chiyoda, Yūrakuchō, Hanzōmon, Namboku and Fukutoshin** lines, and Toei Subway's **Asakusa, Mita, Shinjuku and Ōedo** lines. These are 13 subway lines / 14 source route variants. Both subway operators retain their supplied line colours and separate Operator choices. JR East and subway open together; **Transport** can select either. Toei's non-subway **Arakawa tram and Nippori-Toneri Liner** remain excluded even though the latter uses GTFS type `1`.

Combined: **17,472 journeys, 61 route variants and 1,146 station records** in **1,085,621 bytes gzip**. All original JR East journey rows, timing patterns, station indices and paths are unchanged. The reference replaces the earlier JR-only file rather than storing JR East twice.

The map opens over metropolitan Tokyo; **Fit selection** shows outer routes. Replay, filters, service details, themes, fullscreen and Tokyo Overview reuse the existing application. The clock is **Asia/Tokyo**. Each journey belongs to the single 03:00–03:00 window containing its origin departure, retaining calls after midnight.

Other railway operators, Shinkansen, buses and passenger loads are not included. Through-running sections retain the source's separate scheduled trips; they are not merged into claims about individual physical trainsets. Metro trip calls in the selected day remain within their respective operator's station records. Passenger totals, if obtained later, must not become invented onboard loads.

## Actual downloaded source and dates

The [published TokyoGTFS railway ZIP](https://mkuran.pl/gtfs/tokyo/rail.zip) was downloaded and opened on **21 October 2026**. It contains timetables, supplied shapes, weekday/weekend calendars, holiday exceptions and English/Japanese labels. The importer selects `agency_id=JR-East`, railway type `2`, and JR East route IDs, plus an explicit allowlist of Tokyo Metro / Toei Subway routes using type `1`. Other routes in the full download are not enabled automatically.

Its generated GTFS calendars run **19 October 2026–19 October 2027** and `feed_info` does not declare historical validity. The [converter's calendar generator](https://github.com/MKuranowski/TokyoGTFS/blob/main/tokyo_gtfs/rail/load_schedules.py) creates a year from its build date. **That is not evidence of an authentic year-long historical archive.** The source uses committed [Mini Tokyo 3D timetable tables](https://github.com/nagix/mini-tokyo-3d/tree/master/data/train-timetables); for example, Yamanote's [18 March 2026 revision](https://github.com/nagix/mini-tokyo-3d/commit/c708abea8bf05ab56137a50e52c032112b6f9beb) refers to the 14 March timetable change.

The pilot deliberately exposes **one past day inside that downloaded calendar** and labels it as a community snapshot. It does not relabel these schedules as June 2024 or claim to reconstruct October disruptions. The adjoining 19/21 October service dates are available for conversion. To expand the period, obtain and preserve a suitable dated source, check timetable revisions and Japanese public holidays, and test weekends as well as weekdays. Do not simply extend the date picker for the whole generated year.

GTFS SHA-256: `e08cae7c18915b4aede6da51bb24b01e0c308c8f4bde7dc101ca1de922bf14b2`.

## Railway geometry

Supplied shapes are generated from TokyoGTFS's own published railway graph. Native distance anchors preserve station occurrence order, particularly full Yamanote loops returning to the same station. Original shape edges are checked against that graph before the usual simplification. The converter can insert straight node-to-node fallbacks when routing fails; an edge absent from the graph makes the affected leg a hidden gap. Legitimate straight railway sections remain usable. Station matches still require the existing 150 m tolerance.

All **10,931 legs across shared topologies** pass these checks. This establishes mapped railway alignment, not exact physical tracks, platforms or observed train movement. Yamanote's inner/outer directions, a full Ōsaki–Ōsaki loop and Ōedo's repeated Tochōmae calls around its loop are checked explicitly. Branches, short workings and original overnight times are retained.

Graph: [TokyoGTFS `data/rail_geo.osm`](https://github.com/MKuranowski/TokyoGTFS/blob/main/data/rail_geo.osm), retrieved 21 October 2026, SHA-256 `8809cab8a2e5eb499411c98d5285c1913ae1afebdd85ba0f02fbf89b95918bd8`. The `.osm` file format alone does not establish an OpenStreetMap origin or licence: the publisher declares its data directory CC0.

## Licence and official ODPT alternative

The [TokyoGTFS publisher](https://mkuran.pl/gtfs/) and [project licence declaration](https://github.com/MKuranowski/TokyoGTFS#license) explicitly license the resulting **railway GTFS as MIT**, crediting **Copyright (c) 2019–2025 Akihiko Kusanagi**. The project's data directory, including its railway graph, is declared **CC0**. SunTrain retains those credits and the upstream MIT notice in [the bundled notice](data/reference/tokyo/LICENSE.txt). This integration consumes the published data; no GPL converter source code is copied. It relies on those publisher declarations and does not assert that unrelated ODPT datasets have MIT terms.

The official [JR East Tokyo-area GTFS catalogue](https://ckan.odpt.org/en/dataset/jreast_tokyo_area) is a separate, **Challenge 2026-only** source. Its actual ZIP endpoint was tested without credentials and returned **403**. The [resource](https://ckan.odpt.org/en/dataset/jreast_tokyo_area/resource/a6f842e9-e053-4be5-a926-87d0b49753d3) requires a **Challenge 2026 token**, not merely a normal ODPT key. No usable token is configured locally.

[Challenge entry](https://challenge2026.odpt.org/en/entry.html) and the [limited licence](https://developer.odpt.org/challenge_license) impose separate conditions, including restrictions on making source data or substantially reconstructable derivatives reusable by third parties. A public repository and downloadable replay JSON need consideration before switching to that source. Do not commit an official ZIP, derived schedule bundle or access token merely because an app display is permitted. The current community pilot does not download that feed or require challenge registration.

## Rebuild and next steps

Run `./.venv/bin/python scripts/prepare_tokyo_replay.py`. Raw GTFS and the graph stay in ignored `.cache/tokyo/`; the compact prepared file is `data/reference/tokyo/2026-10-20.json.gz`. `SUNTRAIN_TOKYO_REFERENCE` can override it. Timetables remain shared patterns in the browser, with no full stop array duplicated per journey.

Both download URLs can change. SHA-256 checks reject different bytes; preserve the validated local cache. A later download requires a fresh source/calendar/geometry audit and updated pins rather than silently replacing the reference. The large all-operator GTFS and graph are preparation inputs and are not served to visitors.

Next practical step: validate a full weekday/weekend period. Other private railways, monorails, automated guideways and trams remain possible later additions, using their own scope and colours. Official ODPT access is an optional future source, subject to its own terms.
