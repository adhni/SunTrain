# Osaka Metro — investigated, not enabled

Checked **22 October 2026** on the Japan expansion branch. Intended scope is the eight Osaka Metro subway lines plus New Tram, using SunTrain's existing replay, filters, colours and compact reference format. **No Osaka schedules or city option have been added.** No suitable reusable, dated journey dataset was verified in this investigation.

## Official timetable source

The [official timetable menu](https://kensaku.osakametro.co.jp/timetable/ja/) and [line selector](https://kensaku.osakametro.co.jp/timetable/ja/subway/dia/rail) are accessible. The selector covers Midosuji, Tanimachi, Yotsubashi, Chuo, Sennichimae, Sakaisuji, Nagahori Tsurumi-ryokuchi, Imazatosuji and New Tram; Kita-Osaka Kyuko is listed separately.

Downloaded and inspected the actual [Umeda southbound departure board](https://kensaku.osakametro.co.jp/timetable/ja/subway/dia/station/29089/1019/1): **77,082 bytes**, with the printed date **14 October 2025**. It supplies weekday/weekend departures and destination markers, including short workings. The inspected HTML has no train identifiers or individual journey links. It does **not** establish complete dated train journeys or all operators' historical timetable revisions. Matching departures across stations would need additional evidence, especially for trains beginning/ending mid-line and through services. Do not simply generate trains from frequencies or apply this board's date to the whole network.

The operator's [site terms, copyright section](https://www.osakametro.co.jp/site_info.php) ask users to consult it before reproducing or repurposing site content outside permitted exceptions. No separate open timetable redistribution grant was found. Public visibility of the departure boards does not establish a licence to publish a derived schedule bundle. No bulk collection, app API access, account registration or external contact was performed.

An external API-list article mentions `https://opendata.osakametro.co.jp/`; that hostname **did not resolve** when tested. Treat it as an unverified lead, not evidence of an operating official open-data service.

## Community alternatives checked

- [OSAKA RAIL 3D](https://github.com/m-nagasako/osaka-rail-3d-orp3/blob/main/README.md) explicitly describes headway-based operation and approximate running. Its line metadata supplies speed, dwell and headway assumptions; geometry is interpolated between stations. This is a simulation, not a historical train timetable suitable for import.
- [rinmon/osaka-metro-3d](https://github.com/rinmon/osaka-metro-3d/blob/main/README.md) uses an internal mobile-app train-position API with a server-side key and fallback predictions/demo operation. Its documented endpoints provide current positions and network/station information, not a historical scheduled-journey archive. It is not a substitute for a permitted replay timetable. No key was extracted, requested or used.
- Searches of public GTFS listings, government archives and the Transitland feed registry did not produce a verified downloadable Osaka Metro timetable with suitable reuse terms. This is a search result, not proof that no such dataset exists.

## Resume when a source is available

Obtain either a dated operator/community timetable with explicit reuse terms, or permission covering conversion and public redistribution of the operator's published timetable data. Preserve the actual source period; a different historical period is acceptable if documented. Confirm full stop sequences, short workings, weekday/holiday calendars, overnight times and the boundaries of Kita-Osaka Kyuko/Kintetsu/Hankyu through services.

Then reuse the existing rail importer and compact schedules. Prefer validated railway geometry with OpenStreetMap attribution where applicable, retaining gaps rather than drawing shortcuts. There is no need for a live API, passenger estimates or a new replay architecture. Raw investigation downloads stay ignored in `.cache/osaka/`.
