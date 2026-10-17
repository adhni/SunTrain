"""A single business day's scheduled services, ready for browser-side replay."""
from __future__ import annotations

import glob
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
LOGGER = logging.getLogger(__name__)


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


def get_replay_day(business_date: str, city: str = "melbourne") -> dict:
    date.fromisoformat(business_date)
    settings = city_settings(city)
    if city != "melbourne":
        if not settings["start_date"] <= business_date <= settings["end_date"]:
            raise ValueError(f"{settings['name']} replay covers {settings['start_date']} through {settings['end_date']}")
        default = {"boston": BOSTON_PATH, "chicago": CHICAGO_PATH, "nyc": NYC_PATH, "singapore": SINGAPORE_PATH}[city]
        path = Path(os.getenv(f"SUNTRAIN_{city.upper()}_REFERENCE", str(default)))
        return _get_prepared_day(city, business_date, str(path), path.stat().st_mtime_ns)
    source = data._dataset_path()
    fingerprint = tuple((name, Path(name).stat().st_mtime_ns, Path(name).stat().st_size)
                        for name in sorted(glob.glob(source)))
    geometry = geometry_file()
    modified = geometry.stat().st_mtime_ns if geometry.exists() else 0
    return _get_day(business_date, source, fingerprint, str(geometry), modified, transit.fingerprint(business_date))


@lru_cache(maxsize=1)
def _get_prepared_day(city, business_date, path, modified):
    settings = replay_settings(city)
    zone = ZoneInfo(settings["timezone"])
    day = date.fromisoformat(business_date)
    payload = {**settings, "business_date": business_date,
        "revision": hashlib.sha256(repr((city, path, modified)).encode()).hexdigest()[:16],
        "start": int(datetime.combine(day, time(3), zone).timestamp()),
        "end": int(datetime.combine(day + timedelta(days=1), time(3), zone).timestamp()),
        "initial": int(datetime.combine(day, time(8), zone).timestamp()),
        "services": [], "stations": [], "paths": {}, "geometry": {},
        "approximate_legs": 0, "total_legs": 0, "excluded_services": 0}
    reference = transit.read_reference(path, modified)
    if not reference or business_date not in reference.get("days", {}):
        raise ValueError(f"{settings['city_name']} reference does not contain this date")
    transit.add_transit(payload, (path, modified))
    payload["schedule"] = payload.pop("transit")
    return payload


# A day retains snapshot geometry; keep one payload as users switch between archives.
@lru_cache(maxsize=1)
def _get_day(business_date: str, source: str, fingerprint: tuple, geometry_path: str, modified: int, transit_fingerprint: tuple) -> dict:
    geometry = _read_geometry(geometry_path, modified)
    # Parameterize the source as well as the date; honor SUNTRAIN_PARQUET_GLOB.
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
    payload = {**replay_settings(), "business_date": business_date, "revision": hashlib.sha256(repr((fingerprint, geometry_path, modified, transit_fingerprint)).encode()).hexdigest()[:16],
            "start": start, "end": end,
            "initial": int(datetime.combine(day, time(8), MELBOURNE).timestamp()),
            "services": services, "stations": stations, "paths": paths,
            "geometry": geometry.get("metadata", {}), "approximate_legs": approximate_legs,
            "total_legs": total_legs, "excluded_services": excluded}
    transit.add_transit(payload, transit_fingerprint)
    return payload
