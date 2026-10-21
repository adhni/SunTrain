"""A single business day's scheduled services, ready for browser-side replay."""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import logging
import math
import os
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from dashboard import data
from dashboard import transit
from dashboard.cities import city_settings, replay_settings

ROOT = Path(__file__).resolve().parents[1]
MELBOURNE = ZoneInfo("Australia/Melbourne")
GEOMETRY_PATH = ROOT / "data/reference/rail_paths.json"
BOSTON_PATH = ROOT / "data/reference/boston/2024-06-24.json.gz"
CHICAGO_PATH = ROOT / "data/reference/chicago/2025-11-24.json.gz"
NYC_PATH = ROOT / "data/reference/nyc/2025-12-15.json.gz"
SINGAPORE_PATH = ROOT / "data/reference/singapore/2026-10-05.json.gz"
TOKYO_PATH = ROOT / "data/reference/tokyo/2026-10-20.json.gz"
SYDNEY_PATH = ROOT / "data/reference/sydney/2026-10-05.json.gz"
ADELAIDE_PATH = ROOT / "data/reference/adelaide/2024-05-27.json.gz"
PERTH_PATH = ROOT / "data/reference/perth/2026-10-05.json.gz"
BRISBANE_PATH = ROOT / "data/reference/brisbane/2026-10-05.json.gz"
TORONTO_PATH = ROOT / "data/reference/toronto/2026-10-05.json.gz"
DC_PATH = ROOT / "data/reference/dc/2026-10-05.json.gz"
SF_BAY_PATH = ROOT / "data/reference/sf_bay/2026-08-17.json.gz"
US_RAIL_PATH = ROOT / "data/reference/us_rail/2026-10-12.json.gz"
US_COMMUTER_PATH = ROOT / "data/reference/us_rail/commuter-2026-10-12.json.gz"
US_LIGHT_RAIL_PATH = ROOT / "data/reference/us_rail/light-rail-2026-10-12.json.gz"
LONDON_PATH = ROOT / "data/reference/london/2026-10-05.json.gz"
NETHERLANDS_PATH = ROOT / "data/reference/netherlands/2026-06-01.json.gz"
GERMANY_PATH = ROOT / "data/reference/germany/2026-06-01.json.gz"
FRANCE_PATH = ROOT / "data/reference/france/2026-06-01.json.gz"
SWITZERLAND_PATH = ROOT / "data/reference/switzerland/2026-06-01.json.gz"
BELGIUM_PATH = ROOT / "data/reference/belgium/2026-06-01.json.gz"
AUSTRIA_PATH = ROOT / "data/reference/austria/2026-06-01.json.gz"
JAKARTA_PATH = ROOT / "data/reference/jakarta/2025-12-15.json.gz"
JAVA_PATH = ROOT / "data/reference/java/2025-02-03.json.gz"
JAVA_REGIONAL_PATH = ROOT / "data/reference/java/regional-2025-02-03.json.gz"
GREAT_BRITAIN_PATH = ROOT / "data/reference/great_britain/2026-10-05.json.gz"
ITALY_PATH = ROOT / "data/reference/italy/2026-10-05.json.gz"
LUXEMBOURG_PATH = ROOT / "data/reference/luxembourg/2026-06-01.json.gz"
PORTUGAL_PATH = ROOT / "data/reference/portugal/2026-06-01.json.gz"
SPAIN_PATH = ROOT / "data/reference/spain/2024-06-24.json.gz"
BUS_REFERENCE_CITIES = {"boston", "london", "chicago", "perth", "jakarta"}
LOGGER = logging.getLogger(__name__)
GERMANY_REPLAY_NOTE = "Long-distance trains open first. Select Regional rail, S-Bahn or U-Bahn / Stadtbahn under Transport to add those networks. German/border portions and original source categories/times are retained. Unavailable railway paths stay gaps. No individual passenger loads."

GREAT_BRITAIN_REPLAY_NOTE = "Long-distance trains open first. Select Regional / commuter rail under Transport to add those operators. Select the London rail options to use the existing London schedules in this map. Remaining GWR/EMR local services and Caledonian Sleeper are excluded. Unsupported track sections stay gaps. No individual passenger counts."
JAVA_REPLAY_NOTE = "Java intercity and regional trains, Bandung–Padalarang feeder and YIA/Adi Soemarmo airport trains use official timetables effective 1 February 2025. Optional F trains are excluded. Whoosh, Soekarno–Hatta airport rail and optional Jakarta networks reuse the existing Jakarta sources, matched by weekday from December 2025 (with labelled 2025/2026 operator overlays). The timeline continues through overnight arrivals. No live tracking or passenger loads."
US_RAIL_REPLAY_NOTE = "Amtrak and Brightline open first. Regional / commuter rail and Light rail (TRAX/S-Line, DART and SPRINTER) are optional under Transport. All clocks and stop times use Eastern time, including western stations. Journeys belong to their 03:00–03:00 Eastern departure day; playback continues through multi-day arrivals. MBTA remains in Boston. Other urban networks, connecting buses and passenger loads are excluded. Unsupported railway sections remain gaps. Scheduled estimates, not live tracking."


def prepared_path(city):
    default = {"boston": BOSTON_PATH, "chicago": CHICAGO_PATH, "nyc": NYC_PATH, "singapore": SINGAPORE_PATH, "tokyo": TOKYO_PATH,
               "sydney": SYDNEY_PATH, "adelaide": ADELAIDE_PATH, "perth": PERTH_PATH, "brisbane": BRISBANE_PATH,
               "toronto": TORONTO_PATH, "dc": DC_PATH, "sf_bay": SF_BAY_PATH, "us_rail": US_RAIL_PATH, "london": LONDON_PATH,
               "netherlands": NETHERLANDS_PATH, "germany": GERMANY_PATH, "france": FRANCE_PATH,
               "switzerland": SWITZERLAND_PATH, "belgium": BELGIUM_PATH, "austria": AUSTRIA_PATH,
               "spain": SPAIN_PATH, "portugal": PORTUGAL_PATH, "luxembourg": LUXEMBOURG_PATH, "italy": ITALY_PATH, "great_britain": GREAT_BRITAIN_PATH, "jakarta": JAKARTA_PATH, "java": JAVA_PATH}[city]
    return Path(os.getenv(f"SUNTRAIN_{city.upper()}_REFERENCE", str(default)))


def bus_reference_file(city, business_date, mode="bus"):
    directory = Path(os.getenv(f"SUNTRAIN_{city.upper()}_{mode.upper()}_REFERENCE", str(ROOT / "data/reference" / city / mode)))
    return directory / (business_date + ".json.gz")


def bus_modes(city):
    if city == "jakarta":
        return {"bus", "mikrotrans", "feeder_bus", "transjabodetabek", "rusun_bus", "royaltrans", "shuttle_bus", "tourist_bus"}
    return {"bus"} if city in BUS_REFERENCE_CITIES else set()


def bus_reference_files(city, business_date, modes):
    files = []
    for mode in sorted(set(modes) & bus_modes(city)):
        path = bus_reference_file(city, business_date, mode)
        files.append((mode, str(path), path.stat().st_mtime_ns))
    return tuple(files)


def germany_reference_files(business_date, modes=None):
    return rail_reference_files("germany", business_date, modes)


def rail_reference_files(city, business_date, modes=None):
    settings = city_settings(city)
    allowed = {mode for _, mode in settings["modes"]}
    selected = set(settings["default_modes"] if modes is None else modes or allowed)
    if not selected <= allowed:
        raise ValueError(f"Unsupported {settings['name']} transport mode")
    files = []
    for mode in sorted(selected):
        if mode == "train":
            path = prepared_path(city)
        elif city == "great_britain" and mode in {"subway", "light_rail", "commuter_rail"}:
            path = prepared_path("london")
        elif city == "java" and mode == "regional_rail":
            path = Path(os.getenv("SUNTRAIN_JAVA_REGIONAL_RAIL_REFERENCE", str(JAVA_REGIONAL_PATH)))
        elif city == "us_rail" and mode == "commuter_rail":
            path = Path(os.getenv("SUNTRAIN_US_RAIL_COMMUTER_RAIL_REFERENCE", str(US_COMMUTER_PATH)))
        elif city == "us_rail" and mode == "light_rail":
            path = Path(os.getenv("SUNTRAIN_US_RAIL_LIGHT_RAIL_REFERENCE", str(US_LIGHT_RAIL_PATH)))
        elif city == "java":
            path = prepared_path("jakarta")
        else:
            directory = Path(os.getenv(f"SUNTRAIN_{city.upper()}_{mode.upper()}_REFERENCE", str(ROOT / "data/reference" / city / mode)))
            path = directory / (business_date + ".json.gz")
        files.append((mode, str(path), path.stat().st_mtime_ns))
    if city == "java" and "train" in selected:
        path = prepared_path("jakarta")
        files.append(("jakarta_train", str(path), path.stat().st_mtime_ns))
    return tuple(files)


def clear_replay_cache():
    """Release parsed schedules once their compressed HTTP response is saved."""
    for cached in (_get_day, _get_prepared_day, _get_with_buses, _get_germany_day, transit.read_reference, _read_geometry):
        cached.cache_clear()


def pattern_key(operator: str, line: str, stations: list[str]) -> str:
    return hashlib.sha256(json.dumps([operator, line, stations], ensure_ascii=False).encode()).hexdigest()[:20]


def cumulative_distances(points: list[list[float]]) -> list[float]:
    if not points:
        return []
    distances = [0.0]
    for (lon1, lat1), (lon2, lat2) in zip(points, points[1:]):
        x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
        y = math.radians(lat2 - lat1)
        distances.append(round(distances[-1] + math.hypot(x, y) * 6_371_000, 2))
    return distances


@lru_cache(maxsize=32768)
def _instants(local: datetime) -> list[int]:
    """Return valid UTC instants, including both occurrences of a repeated hour."""
    result = set()
    for fold in (0, 1):
        aware = local.replace(tzinfo=MELBOURNE, fold=fold)
        if aware.astimezone(timezone.utc).astimezone(MELBOURNE).replace(tzinfo=None) == local:
            result.add(int(aware.timestamp()))
    return sorted(result)


def normalize_stop_times(business_date: str, times: list[tuple[time, time]]) -> tuple[list[tuple[int, int]], bool]:
    """Unwrap whole journeys, rather than resetting the date at each 03:00."""
    if not times:
        return [], False
    current_date = date.fromisoformat(business_date)
    if times[0][0] < time(3):
        current_date += timedelta(days=1)
    previous = None
    previous_clock = None
    output = []
    uncertain = False
    for arrival, departure in times:
        pair = []
        for clock in (arrival, departure):
            if previous_clock is not None and previous_clock >= time(21) and clock < time(3):
                current_date += timedelta(days=1)
            candidates = [value for value in _instants(datetime.combine(current_date, clock))
                          if previous is None or value >= previous]
            if not candidates:
                raise ValueError("Missing or backwards scheduled time")
            uncertain |= len(candidates) > 1
            previous = candidates[0]
            previous_clock = clock
            pair.append(previous)
        output.append(tuple(pair))
    return output, uncertain


def geometry_file() -> Path:
    return Path(os.getenv("SUNTRAIN_RAIL_GEOMETRY", str(GEOMETRY_PATH)))


@lru_cache(maxsize=2)
def _read_geometry(path: str, modified: int) -> dict:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {"metadata": {"status": "unavailable"}, "patterns": {}, "paths": {}}


def get_replay_day(business_date: str, city: str = "melbourne", include_buses: bool = False, *, modes=None) -> dict:
    date.fromisoformat(business_date)
    settings = city_settings(city)
    modes = tuple(sorted(set(modes))) if modes is not None else None
    if city in {"france", "belgium"} and modes is None:
        modes = tuple(settings["default_modes"])
    include_buses = include_buses or modes is not None and bool(set(modes) & bus_modes(city))
    if city != "melbourne":
        if not settings["start_date"] <= business_date <= settings["end_date"]:
            raise ValueError(f"{settings['name']} replay covers {settings['start_date']} through {settings['end_date']}")
        if city in {"germany", "great_britain", "java", "us_rail"}:
            files = rail_reference_files(city, business_date, modes)
            return _get_germany_day(business_date, files, city=city)
        path = prepared_path(city)
        modified = 0 if modes and set(modes) <= bus_modes(city) else path.stat().st_mtime_ns
        base = _get_prepared_day(city, business_date, str(path), modified, modes)
        if city in BUS_REFERENCE_CITIES and include_buses:
            files = bus_reference_files(city, business_date, modes if modes is not None else ("bus",))
            if files:
                return _get_with_buses(city, business_date, str(path), modified, files, modes)
        return base
    source = data._dataset_path()
    fingerprint = tuple((name, Path(name).stat().st_mtime_ns, Path(name).stat().st_size)
                        for name in sorted(glob.glob(source)))
    geometry = geometry_file()
    modified = geometry.stat().st_mtime_ns if geometry.exists() else 0
    transit_key = transit.fingerprint(business_date) if modes is None or set(modes) & {"tram", "bus"} else ("", 0)
    return _get_day(business_date, source, fingerprint, str(geometry), modified, transit_key, modes)


@lru_cache(maxsize=1)
def _get_germany_day(business_date, files, city="germany"):
    """Reuse prepared rail layers, including existing networks in wider views."""
    note = {"germany": GERMANY_REPLAY_NOTE, "great_britain": GREAT_BRITAIN_REPLAY_NOTE,
            "java": JAVA_REPLAY_NOTE, "us_rail": US_RAIL_REPLAY_NOTE}[city]
    modes = tuple(mode for mode, _, _ in files)
    base_path = prepared_path(city)
    modified = next((stamp for mode, _, stamp in files if mode == "train"), 0)
    base = _get_prepared_day(city, business_date, str(base_path), modified, modes)
    if modes == ("train",):
        return {**base, "schedule": {**base["schedule"], "replay_note": note}}
    payload = {**base, "services": list(base["services"]), "stations": list(base["stations"]),
               "paths": dict(base["paths"]), "transit_patterns": dict(base.get("transit_patterns", {})),
               "transit_stop_patterns": dict(base.get("transit_stop_patterns", {})),
               "revision": hashlib.sha256(repr((business_date, files)).encode()).hexdigest()[:16]}
    schedules = [base["schedule"]] if modified else []
    transit.read_reference.cache_clear()
    # Wider views reuse existing city files. Parse each file once and append
    # all selected modes together, without writing another schedule bundle.
    grouped = {}
    for mode, path, _ in files:
        if mode != "train":
            grouped.setdefault(path, []).append("train" if mode == "jakarta_train" else mode)
    display_date_mapping = {}
    for path, selected in grouped.items():
        with gzip.open(path, "rb") as stream:
            reference = transit.load_reference(stream)
        if city == "java" and selected != ["regional_rail"]:
            # Same timezone, no DST: retain all source clock/offset values and
            # map the existing source week by weekday without writing a copy.
            target = date.fromisoformat(business_date)
            source_day = next(day for day in sorted(reference["days"]) if date.fromisoformat(day).weekday() == target.weekday())
            reference["days"] = {business_date: reference["days"][source_day]}
            reference["metadata"] = {**reference["metadata"], "display_date_mapping": {business_date: source_day}}
            display_date_mapping[business_date] = source_day
        previous_count = len(payload["services"])
        transit.append_reference(payload, reference, consume=True, modes=tuple(selected))
        schedules.append(payload.pop("transit"))
        for service in payload["services"][previous_count:]:
            mode = service["mode"]
            if city == "java":
                prefix = "java-regional" if mode == "regional_rail" else "java-jakarta"
            elif city == "germany":
                prefix = "de-nv" if mode == "subway" else "de-rv"
            elif city == "us_rail":
                prefix = "us-light-rail" if mode == "light_rail" else "us-commuter"
            else:
                prefix = "gb-london" if mode in {"subway", "light_rail", "commuter_rail"} else "gb-rv"
            service["id"] = f"{prefix}:{mode}:" + service["id"]
            if city in {"great_britain", "java", "us_rail"}:
                trip = service["number"]
                service["source_trip_id"] = trip
                service["number"] = reference.get("train_numbers", {}).get(trip, trip)
    geometry_sources = []
    for schedule in schedules:
        credit = {key: schedule[key] for key in ("geometry_source", "geometry_source_url", "geometry_license", "geometry_license_url") if key in schedule}
        for item in [credit, *schedule.get("additional_geometry_sources", [])]:
            if item and item not in geometry_sources:
                geometry_sources.append(item)
    payload["schedule"] = {**schedules[0],
        "sources": list({json.dumps(source, sort_keys=True): source for schedule in schedules for source in schedule.get("sources", [])}.values()),
        "attribution": " ".join(dict.fromkeys(schedule.get("attribution", "") for schedule in schedules)),
        "license": "; ".join(dict.fromkeys(schedule.get("license", "") for schedule in schedules)),
        "source": "DELFI e.V. / GTFS.de historical railway schedules" if city == "germany" else schedules[0]["source"],
        "source_url": "https://gtfs.de/en/feeds/" if city == "germany" else schedules[0]["source_url"],
        "additional_geometry_sources": geometry_sources[1:],
        "replay_note": note}
    if city in {"java", "us_rail"}:
        if display_date_mapping:
            payload["schedule"]["display_date_mapping"] = display_date_mapping
        # Long journeys belong to their departure day. Let them reach their
        # destination rather than stopping the slider at the next 03:00.
        payload["end"] = max([payload["end"], *[
            service["departure"] + int(payload["transit_patterns"][service["pattern"]]["times"][-1])
            for service in payload["services"]]])
    return payload


@lru_cache(maxsize=1)
def _get_with_buses(city, business_date, rail_path, rail_modified, files, modes=None):
    base = _get_prepared_day(city, business_date, rail_path, rail_modified, modes)
    # Append to fresh containers so the cached rail-only payload remains small.
    payload = {**base, "services": list(base["services"]), "stations": list(base["stations"]),
               "paths": dict(base["paths"]), "transit_patterns": dict(base.get("transit_patterns", {})),
               "transit_stop_patterns": dict(base.get("transit_stop_patterns", {})),
               "bus_data_loaded": True,
               "revision": hashlib.sha256(repr((base["revision"], files)).encode()).hexdigest()[:16]}
    # The merged payload is cached once. Transfer fresh bus arrays directly;
    # retaining a second parsed bus reference would double schedule memory.
    transit.read_reference.cache_clear()
    schedules = []
    for _, bus_path, _ in files:
        with gzip.open(bus_path, "rb") as stream:
            bus_reference = transit.load_reference(stream)
        transit.append_reference(payload, bus_reference, consume=True, modes=modes)
        schedules.append(payload.pop("transit"))
        del bus_reference
    payload["bus_schedule"] = dict(schedules[0])
    if len(schedules) > 1:
        # Jakarta's optional road layers share publisher, archive and licence.
        selected = {mode for mode, _, _ in files}
        labels = [label for label, mode in city_settings(city)["modes"] if mode in selected]
        categories = [s["source"].removeprefix("TransJakarta ").split(" GTFS,", 1)[0] for s in schedules]
        bus_note = ("TransJakarta buses: May 2026 snapshot matched by weekday/weekend, not December 2025 history. "
                    + "Selected: " + ", ".join(labels) + ". Departures are illustrative frequency-based estimates, not live positions. ")
        if "mikrotrans" in selected:
            bus_note += "One Mikrotrans pattern is exact in the source. "
        if "royaltrans" in selected:
            bus_note += "Royaltrans runs on weekdays only. "
        bus_note += "Source operating windows are retained; individual passenger loads are unavailable."
        attribution = ("GTFS Static Transjakarta © 2026 PT Transportasi Jakarta, CC BY 4.0. Changes by SunTrain: "
                       + "; ".join(category + " selection" for category in categories)
                       + "; shared timing/path conversion and illustrative headway-based departures. Archive: MobilityDatabase, 7 May 2026.")
        payload["bus_schedule"].update(
            attribution=attribution, note=bus_note, replay_note=bus_note)
    schedule = base["schedule"] or payload["bus_schedule"]
    note = schedule.get("replay_note", "").replace("Buses, boats and cable car are excluded.", "Boats and cable car are excluded.")
    if city == "boston":
        note = "MBTA rail and Silver Line services, with regular buses included when selected. Rail replacement shuttles and non-MBTA operators are excluded."
        payload["schedule"] = {**schedule, "attribution": "Historical schedules and route geometry: MassDOT / MBTA"}
    else:
        payload["schedule"] = dict(schedule)
    if city in {"chicago", "perth"}:
        note = ("CTA rail and optional buses. Metra is excluded." if city == "chicago" else
                "Transperth trains and optional metropolitan buses, including CAT. Regional operators and ferries are excluded.")
    bus_note = payload["bus_schedule"]["note"]
    payload["schedule"]["replay_note"] = note if note == bus_note else note + " " + bus_note
    return payload


@lru_cache(maxsize=1)
def _get_prepared_day(city, business_date, path, modified, modes=None):
    settings = replay_settings(city)
    zone = ZoneInfo(settings["timezone"])
    day = date.fromisoformat(business_date)
    payload = {**settings, "business_date": business_date,
        "revision": hashlib.sha256(repr((city, path, modified, modes)).encode()).hexdigest()[:16],
        "start": int(datetime.combine(day, time(3), zone).timestamp()),
        "end": int(datetime.combine(day + timedelta(days=1), time(3), zone).timestamp()),
        "initial": int(datetime.combine(day, time(8), zone).timestamp()),
        "services": [], "stations": [], "paths": {}, "geometry": {},
        "approximate_legs": 0, "total_legs": 0, "excluded_services": 0}
    if ((modes and set(modes) <= bus_modes(city))
            or (city in {"germany", "great_britain", "java", "us_rail"} and modes is not None and "train" not in modes)):
        # Optional daily bundles supply their own provenance. Do not open an
        # unselected base timetable just to create the empty replay container.
        payload["schedule"] = {}
        return payload
    reference = transit.read_reference(path, modified)
    if not reference or business_date not in reference.get("days", {}):
        raise ValueError(f"{settings['city_name']} reference does not contain this date")
    transit.append_reference(payload, reference, modes=modes)
    if reference.get("train_numbers"):
        numbers = reference.get("train_numbers", {})
        for service in payload["services"]:
            trip = service["number"]
            service["source_trip_id"] = trip
            service["number"] = numbers.get(trip, trip)
    payload["schedule"] = payload.pop("transit")
    if city == "us_rail":
        payload["end"] = max([payload["end"], *[
            service["departure"] + int(payload["transit_patterns"][service["pattern"]]["times"][-1])
            for service in payload["services"]]])
    return payload


# A day retains snapshot geometry; keep one payload as users switch between archives.
@lru_cache(maxsize=1)
def _get_day(business_date: str, source: str, fingerprint: tuple, geometry_path: str, modified: int, transit_fingerprint: tuple, modes=None) -> dict:
    geometry = _read_geometry(geometry_path, modified)
    # Parameterize the source as well as the date; honor SUNTRAIN_PARQUET_GLOB.
    rows = []
    if modes is None or "train" in modes:
        con = data._connect()
        try:
            rows = con.execute("""
                SELECT Mode, Line_Name, Direction, Train_Number, Origin_Station, Destination_Station,
                       Station_Name, Station_Latitude, Station_Longitude,
                       CAST(Arrival_Time_Scheduled AS TIME), CAST(Departure_Time_Scheduled AS TIME),
                       Passenger_Arrival_Load, Passenger_Departure_Load, Passenger_Boardings, Passenger_Alightings
                FROM read_parquet(?) WHERE Business_Date = CAST(? AS DATE)
                ORDER BY Mode, Line_Name, Direction, Train_Number, Stop_Sequence_Number
            """, [source, business_date]).fetchall()
        finally:
            con.close()

    grouped = {}
    stations, station_ids, paths, services = [], {}, {}, []
    for row in rows:
        grouped.setdefault(row[:4], []).append(row)
    excluded = 0
    approximate_legs = 0
    total_legs = 0
    for key, stops in grouped.items():
        try:
            timestamps, uncertain = normalize_stop_times(business_date, [(r[9], r[10]) for r in stops])
            if any(not math.isfinite(r[7]) or not math.isfinite(r[8]) for r in stops):
                raise ValueError("Invalid station coordinates")
        except (ValueError, TypeError):
            excluded += 1
            LOGGER.warning("Replay omitted invalid service %s %s", business_date, key)
            continue
        operator, line, direction, number = key
        service_stops = []
        for row, (arrival, departure) in zip(stops, timestamps):
            station_key = (row[6], round(row[7], 6), round(row[8], 6))
            if station_key not in station_ids:
                station_ids[station_key] = len(stations)
                stations.append({"name": row[6], "lat": station_key[1], "lon": station_key[2]})
            service_stops.append([station_ids[station_key], arrival, departure, *row[11:15]])
        pattern = geometry.get("patterns", {}).get(pattern_key(operator, line, [r[6] for r in stops]), [])
        legs = []
        for i in range(len(stops) - 1):
            path_id = pattern[i] if i < len(pattern) else None
            reference = geometry.get("paths", {}).get(path_id)
            if reference is None:
                path_id = "unresolved"
                reference = {"coordinates": [], "quality": "approximate", "reason": "unmatched"}
            if path_id not in paths:
                paths[path_id] = {**reference, "distances": cumulative_distances(reference["coordinates"])}
            legs.append(path_id)
            approximate_legs += reference["quality"] != "track"
            total_legs += 1
        services.append({
            "id": json.dumps([business_date, *key], separators=(",", ":")),
            "operator": operator, "line": line, "direction": direction, "number": str(number),
            "mode": "train",
            "origin": stops[0][4], "destination": stops[0][5], "stops": service_stops,
            "legs": legs, "timing_uncertain": uncertain,
        })
    day = date.fromisoformat(business_date)
    start = int(datetime.combine(day, time(3), MELBOURNE).timestamp())
    end = int(datetime.combine(day + timedelta(days=1), time(3), MELBOURNE).timestamp())
    end = max([end, *[s["stops"][-1][2] for s in services]])
    payload = {**replay_settings(), "business_date": business_date, "revision": hashlib.sha256(repr((fingerprint, geometry_path, modified, transit_fingerprint, modes)).encode()).hexdigest()[:16],
            "start": start, "end": end,
            "initial": int(datetime.combine(day, time(8), MELBOURNE).timestamp()),
            "services": services, "stations": stations, "paths": paths,
            "geometry": geometry.get("metadata", {}), "approximate_legs": approximate_legs,
            "total_legs": total_legs, "excluded_services": excluded}
    if transit_fingerprint[1]:
        transit.append_reference(payload, transit.read_reference(*transit_fingerprint), modes=modes)
    else:
        payload["transit"] = {"available": False}
    return payload
