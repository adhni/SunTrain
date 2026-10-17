# Australian railway expansion

Work began 17 October 2026 on `codex/australian-cities-replay`, in order: Sydney, Adelaide, Perth, Brisbane. Reuse the existing compact prepared-city replay; no live tracking or new runtime services. API credentials and source downloads stay local. The pre-existing untracked `docs/` directory is unrelated and remains untouched.

## Sydney

The preferred 27 May–30 June 2024 period could not be downloaded through the official historical archive link: the [TfNSW archive catalogue](https://opendata.transport.nsw.gov.au/dataset/historical-gtfs-bundles-and-timetables) is readable through its public CKAN API, but its `https://opendata-gtfs.transport.nsw.gov.au/historical_gtfs` resource returned HTTP 404. The website advertises login for some resources. No account was created or credentials requested.

The permitted fallback is **5–11 October 2026**, one complete week using the [official TfNSW feed archived by MobilityDatabase](https://mobilitydatabase.org/feeds/gtfs/mdb-2449), captured **4 October 2026**. The pinned public ZIP actually downloaded successfully (about 279 MB, containing the whole multimodal network). Exact source URL and SHA-256 are in `scripts/prepare_australian_replay.py` and each prepared reference's metadata. It is never served to browsers.

Scope is explicitly **Sydney Trains** (`agency_id=x0001`, rail type 2) and **Sydney Metro** (`agency_id=SMNW`, type 401). Route variants group under the feed's T1–T9 and M1 line names and colours. Calendar exceptions determine which services appear; a route in the feed does not force trips onto every date. The 2026 Metro and train network must not be relabelled as May–June 2024: the [official station usage catalogue](https://opendata.transport.nsw.gov.au/dataset/train-station-entries-and-exits-data) records the Chatswood–Sydenham Metro extension opening on 19 August 2024, and T3/T6 patterns changed subsequently.

Native stop/shape distance anchors preserve ordered railway paths, including loops and branch services. Every projected station must match within 150 m; unresolved paths remain gaps. Metro's source `routes.txt` marks its timings as indicative (`exact_times=0`); replay positions remain schedule estimates. The feed includes no `frequencies.txt` requiring generated departures.

**NSW TrainLink remains separate.** The same archive includes intercity agency `X0000` (e.g. BMT, CCN, SCO) and regional trains/coaches under other agencies (including 711 and extended route types). Do not include them via an indiscriminate rail-type filter. Replacement bus agencies and bus types are also excluded even when names resemble train lines.

**Later modes:** the complete archive includes light rail (extended type 900, with Sydney and Newcastle represented separately), many bus operators and ferries. Future additions should retain operator scope, distinguish rail replacement buses, and apply each route's calendars and shapes. Their presence in the archive is confirmed; their complete replay has not been validated or enabled.

**Passenger data:** the [station monthly usage CSV](https://opendata.transport.nsw.gov.au/data/dataset/3977df59-a1fa-422e-91ff-cfaeac355cc9/resource/f8bb2918-0540-4bb3-9ccf-f7aef04d4249/download/entry_exit.csv) actually downloaded with HTTP 200 (1,122,668 bytes, 17,982 rows). Actual months run **October 2024–September 2026**, despite the resource title saying November 2024. Fields are `MonthYear`, `Station`, `Station_Type`, `Entry_Exit`, `Trip`; **786 cells contain “Less than 50”**, not zero. Suitable for a labelled monthly station-use map, not hourly observations or individual train loads. The [monthly Opal train/metro totals](https://opendata.transport.nsw.gov.au/dataset/opal-trips-train) also warn that line/operator/mode aggregates must not be summed across levels after the July 2024 methodology change. Passenger features remain unavailable for this replay.

**Licence:** the official complete-timetable CKAN record labels this [Creative Commons Attribution](https://opendata.transport.nsw.gov.au/dataset/timetables-complete-gtfs). SunTrain acknowledges Transport for NSW, links the source/licence information and remains independent of the operators. No official map artwork or logos are copied.

## Rebuild and extension checks

```bash
./.venv/bin/python scripts/prepare_australian_replay.py sydney
```

Sources are pinned by URL, capture date and SHA-256. Downloads go to `.cache/australian-cities/<city>/`; compact references go to `data/reference/<city>/<first-date>.json.gz`. Preparation uses source calendars and date exceptions, GTFS hours beyond 24 and local time zones, with 03:00 carry-ins preserved and no duplicate occurrence within a day. Shapes remain shared; only one selected day is loaded in the browser.

Before extending dates or adding a mode, inspect the actual archive's dates, operators, route types, trip overrides/frequencies and geometry. Never use current timetables under historical labels. Preserve local clocks, branch paths, same-day uniqueness, shared relative stop schedules, attribution and empty paths for unresolved geometry. Passenger data requires a separate granularity and date check.
