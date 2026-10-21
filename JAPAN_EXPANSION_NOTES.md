# Japan intercity expansion — partial coverage

## Implemented

The **Japan** view uses the community Shinkansen timetable dated **10 March 2026**. It contains **927 regular services**, **19 named service families**, **118 station records** and **702 shared timing patterns**, in **333,465 bytes gzip**. The operating corridors are Tōkaidō, Sanyō, Kyūshū, Nishi-Kyūshū, Tōhoku, Hokkaidō, Jōetsu, Hokuriku, Yamagata and Akita, plus represented Gala-Yuzawa services.

Services include Nozomi, Hikari, Kodama, Mizuho, Sakura, Tsubame, Hayabusa, Hayate, Yamabiko, Nasuno, Tsubasa, Komachi, Toki, Tanigawa, Kagayaki, Hakutaka, Asama, Tsurugi and Kamome. This covers the national Shinkansen corridors, **not every extra train or every conventional intercity train**. The unfinished Chūō maglev and Hokkaidō extension are excluded.

The default view also includes **527 JR East limited-express journey sections** reused directly from the existing Tokyo reference. That source is dated **20 October 2026**; both dates are Tuesdays, and the overlay retains its original local clocks. Its source-date mapping is included in the response and explained in the map note. These are representative weekday sections, **not claims about March operations**. No Tokyo timetable is copied into the Japan file. Ordinary JR East locals/rapids and Tokyo subway services are not brought into the national intercity view. The separate Tokyo view remains unchanged.

Transport selects Shinkansen, JR East limited express or both; route and operator filters, details, Overview, fullscreen and themes reuse existing functionality. Clocks use **Asia/Tokyo**. Source services retain printed arrival/departure times, including intermediate dwell times. No passenger loads or live tracking are supplied. Service colours are display colours grouped by train family, not an assertion of official individual route branding.

## Timetable provenance and duplication

Downloaded and inspected: [Shinkansen Live `timetable/data.json`](https://github.com/manavya-des/shinkansen-live-open/blob/2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96/timetable/data.json), from immutable revision `2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96` (11 March 2026). The data explicitly declares `date=2026-03-10`; it is a community dataset, not a national official GTFS archive. Raw timetable SHA-256: `73ed3276be89dc846237fe1dd588d3606fedee557c7983bbc0e20fa6bba1dcaa`.

Only rows explicitly marked daily or weekday and without caution symbols are selected for this Tuesday. **193 source rows** with blank/conditional operation information are excluded, rather than inventing their operating dates. Blank and arrow cells do not create timed station calls. Tōkaidō/Sanyō/Kyūshū overlapping columns are merged by service name, number and direction, retaining the union of consistent printed stops. A conflicting duplicate fails preparation. Nozomi 1 appears once from Tokyo **06:00** to Hakata **10:52**, including its intermediate calls; it is not emitted again at Shin-Osaka.

The station catalogue is extracted from the same revision's [map station table](https://github.com/manavya-des/shinkansen-live-open/blob/2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96/src/components/map-client.tsx) and [Japanese/English names](https://github.com/manavya-des/shinkansen-live-open/blob/2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96/src/app/timetable/page.tsx), in `data/sources/japan_shinkansen_stations.json`. Japanese identifiers distinguish **仙台** in Tōhoku from **川内** in Kyūshū even though both translate to Sendai. Mikawa-Anjō's source point was on the conventional station rather than the Shinkansen station; its corrected coordinate comes from [OSM station node 6620847242](https://www.openstreetmap.org/node/6620847242), recorded in that catalogue.

## Connected railway geometry

The community project's display polylines contained multi-kilometre shortcuts and were **not used** in the final replay. SunTrain downloaded the original operating railway ways from ten [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API_v0.6) route relations on **21 October 2026**. Exact source URLs and SHA-256 hashes are pinned in `data/sources/japan_shinkansen_geometry.json`. Nodes connect only by their original OSM IDs; platforms and construction ways are excluded. The existing railway graph and 150 m station-matching rule are reused, then paths are simplified for playback. This is inferred railway alignment, not proof of a historical running track or platform.

The preparation-only graph is **790,361 bytes gzip**, SHA-256 `05fc1fc57f4b43c9267a81c31af1f948d505191a2abd6f0235356128703d6c68`. **8,218 of 8,358 scheduled journey legs (98.3%)** have connected paths. This weights legs by included services; it is not a fraction of physical railway mileage. Three underlying station sections remain unresolved: Kurikoma-Kōgen–Ichinoseki, Morioka–Iwate-Numakunai and Echigo-Yuzawa–Gala-Yuzawa. A timed express leg crossing one of these remains hidden until its next supported station. Nozomi 1's entire journey has mapped paths.

## Rights

The community source repository distributes its bundled timetable under its [MIT licence](https://github.com/manavya-des/shinkansen-live-open/blob/2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96/LICENSE), **Copyright (c) 2026 Shinkansen Live Contributors**. This implementation relies on that publisher declaration and makes no claim of endorsement or a separate official JR redistribution grant. Its [third-party notes](https://github.com/manavya-des/shinkansen-live-open/blob/2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96/THIRD_PARTY.md) retain providers' rights. The original MIT notice is included in `data/reference/japan/LICENSE.txt`; no upstream application code is copied.

The connected graph, derived railway paths and OSM station correction retain **ODbL 1.0** with OpenStreetMap attribution. The MIT notice does not relicense OSM data. The downloadable replay includes geometry/source credits, and the prepared geometry database is available alongside the code. Third-party map tiles, cameras, analytics and live-status endpoints from the community app are not imported. The reused Tokyo source retains its separate [notice](data/reference/tokyo/LICENSE.txt).

## Remaining conventional intercity coverage

**The request for all Japanese intercity trains is not complete.** No complete reusable national conventional timetable was validated during this investigation. Do not label the JR East overlay as nationwide coverage. Important remaining groups include JR Central's conventional limited expresses, JR West's wider limited-express network and Sunrise sleepers, JR Hokkaidō's conventional services, JR Shikoku, JR Kyūshū and private intercity operators such as Kintetsu.

Validated source leads:

- [Kotsu Shimbunsha bulk timetable data](https://www.kotsu.co.jp/service/jikoku_solution/data_sales/) explicitly offers JR passenger companies' nationwide data in CSV/XML/GTFS, plus private railway data. It is a commercial service for corporations/organisations, not an unrestricted downloadable feed. Access and permission to redistribute prepared replay data need confirmation; no subscription or contract was purchased.
- [JR Kyūshū's actual 14-page timetable PDF](https://www.jrkyushu.co.jp/english/pdf/timetable_20260314_20270228.pdf) is accessible and declares **14 March 2026–28 February 2027**. It includes limited-express and Shinkansen tables. It has not been converted, its individual running-day conditions/redistribution permissions have not been resolved, and it must not be presented as a March 10 timetable.
- [JR Hokkaidō's timetable/route page](https://www.jrhokkaido.co.jp/global/english/train/index.html) links station-name PDFs and timetable search. The accessible [MajorTrainTimetable.pdf](https://www.jrhokkaido.co.jp/global/pdf/MajorTrainTimetable.pdf) is explicitly **2022**, so it cannot establish 2026 service. Search results are not a validated downloadable national archive.
- [JR Shikoku station timetables](https://www.jr-shikoku.co.jp/01_trainbus/jikoku/index.html) are available as references; complete dated train-level conversion and reuse terms remain unvalidated.
- [JR Central's timetable page](https://global.jr-central.co.jp/en/info/timetable/) supplies dated basic Shinkansen PDFs and explicitly says they omit some extra trains. It does not establish a complete conventional intercity feed.
- The [ODPT JR East catalogue](https://ckan.odpt.org/en/dataset/jreast_tokyo_area) is the previously investigated restricted Kantō feed, not nationwide JR or Shinkansen coverage. A Challenge token alone does not solve this national-data gap.

Next step for full conventional coverage: secure a suitable dated bulk source with reuse terms, or validate and convert operator publications individually. Preserve actual calendars, overnight times, all printed stops, and operator-specific paths; never create departures from advertised headways. Passenger data remains optional.

## Rebuild

Run `./.venv/bin/python scripts/prepare_japan_replay.py`. It verifies the immutable timetable and bundled graph hashes and writes `data/reference/japan/2026-03-10.json.gz`. Raw downloads remain in ignored `.cache/japan/`. `SUNTRAIN_JAPAN_REFERENCE` overrides the prepared timetable.

To rebuild the graph from the preserved raw OSM responses, run `./.venv/bin/python scripts/prepare_japan_geometry.py`. OSM is mutable: if a fresh response differs, inspect it before updating source/compiled hashes. The graph is not opened by the website at runtime. Expanding dates requires actual timetable/calendar evidence; changing the date picker alone is insufficient. Keep the JR East weekday mapping labelled and preserve the single stored Tokyo reference.
