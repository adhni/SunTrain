"""Prepare historical NYC Subway and Staten Island Railway replay.

2024 ZIP access was unavailable; the permitted fallback is 15 December 2025–
18 January 2026. These are regular, not supplemented, schedules.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_boston_replay import fetch, project_stops
from scripts.prepare_replay_geometry import clip_path, point_at, simplify
from scripts.prepare_transit_replay import active_services, records, seconds

FIRST, LAST = date(2025, 12, 15), date(2026, 1, 18)
ZONE = ZoneInfo("America/New_York")
SOURCE_URL = "https://mobilitydatabase.org/feeds/gtfs/mdb-516"
LICENSE_URL = "https://www.mta.info/developers/terms-and-conditions"
# The December feed was captured on Dec 5 but becomes valid only on Dec 8.
ARCHIVES = [
    {"start": date(2025, 11, 2), "end": date(2025, 12, 7), "captured": "2025-11-01",
     "url": "https://files.mobilitydatabase.org/mdb-516/mdb-516-202511010043/mdb-516-202511010043.zip"},
    {"start": date(2025, 12, 8), "end": date(2026, 5, 16), "captured": "2025-12-05",
     "url": "https://files.mobilitydatabase.org/mdb-516/mdb-516-202512050000/mdb-516-202512050000.zip"},
]


def service_zero(day):
    return int(datetime.combine(day, time(12), ZONE).timestamp()) - 43200


def source_for(day):
    matches = [source for source in ARCHIVES if source["start"] <= day <= source["end"]]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one applicable NYC archive for {day}")
    return matches[0]


def day_windows(days):
    return [(str(day), int(datetime.combine(day, time(3), ZONE).timestamp()),
             int(datetime.combine(day + timedelta(days=1), time(3), ZONE).timestamp()), service_zero(day)) for day in days]


def occurrences(service_days, start, finish, windows):
    """Find overlapping windows without scanning the whole period for each trip."""
    starts, ends = [w[1] for w in windows], [w[2] for w in windows]
    for day in service_days:
        departure, arrival = service_zero(day) + start, service_zero(day) + finish
        for business_date, _, _, zero in windows[bisect_right(ends, departure):bisect_right(starts, arrival)]:
            yield business_date, departure - zero


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    calendar_days = [FIRST - timedelta(days=1), *days, LAST + timedelta(days=1)]
    windows = day_windows(days)
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(d): [] for d in days}}
    station_ids, geometry_cache = {}, {}
    omissions, gaps, sources = Counter(), Counter(), []
    for source in ARCHIVES:
        applicable = [d for d in calendar_days if source_for(d) == source]
        if not applicable:
            continue
        path = fetch(source["url"], cache / source["url"].rsplit("/", 1)[1])
        sources.append({"source_url": source["url"], "source_date": source["captured"],
            "valid_from": str(source["start"]), "valid_through": str(source["end"]),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with ZipFile(path) as archive:
            agencies = {r["agency_id"] for r in records(archive, "agency.txt") if r["agency_timezone"] == str(ZONE)}
            routes = {r["route_id"]: r for r in records(archive, "routes.txt")
                      if (r["route_type"] == "1" or r["route_id"] == "SI" and r["route_type"] == "2") and r["agency_id"] in agencies}
            calendars, exceptions = list(records(archive, "calendar.txt")), list(records(archive, "calendar_dates.txt"))
            active = {d: active_services(calendars, exceptions, d) for d in applicable}
            relevant = set().union(*active.values())
            trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes and r["service_id"] in relevant}
            if "frequencies.txt" in archive.namelist() and any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
                raise ValueError("Frequency-based subway schedules need explicit handling")
            stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
            calls = defaultdict(list)
            for row in records(archive, "stop_times.txt"):
                if row["trip_id"] in trips:
                    calls[row["trip_id"]].append(row)
            shapes = defaultdict(list)
            needed = {t["shape_id"] for t in trips.values()}
            for row in records(archive, "shapes.txt"):
                if row["shape_id"] in needed:
                    shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                        [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)]))
            shapes = {key: [point for _, point in sorted(rows)] for key, rows in shapes.items()}
            signatures = {key: hashlib.sha256(json.dumps(points).encode()).hexdigest() for key, points in shapes.items()}
            for trip_id, trip in trips.items():
                sequence = sorted(calls[trip_id], key=lambda r: int(r["stop_sequence"]))
                try:
                    if len(sequence) < 2:
                        raise ValueError("Fewer than two stops")
                    coordinates = [[float(stops[r["stop_id"]]["stop_lon"]), float(stops[r["stop_id"]]["stop_lat"])] for r in sequence]
                    if not all(math.isfinite(v) for point in coordinates for v in point):
                        raise ValueError("Invalid station coordinates")
                    times = [(seconds(r["arrival_time"]), seconds(r["departure_time"])) for r in sequence]
                    flat = [v for pair in times for v in pair]
                    if any(b < a for a, b in zip(flat, flat[1:])):
                        raise ValueError("Backwards times")
                    running_dates = [d for d in applicable if trip["service_id"] in active[d]]
                    instances = list(occurrences(running_dates, times[0][0], times[-1][1], windows))
                    if not instances:
                        continue
                    ids = []
                    for row, coordinate in zip(sequence, coordinates):
                        stop = stops[row["stop_id"]]
                        key = (stop["stop_id"], stop["stop_name"], *coordinate)
                        if key not in station_ids:
                            station_ids[key] = len(result["stations"])
                            result["stations"].append({"name": stop["stop_name"], "lon": coordinate[0], "lat": coordinate[1], "mode": "train"})
                        ids.append(station_ids[key])
                    geometry_key = (signatures.get(trip["shape_id"]), tuple(map(tuple, coordinates)))
                    if geometry_key not in geometry_cache:
                        try:
                            points = shapes.get(trip["shape_id"], [])
                            positions = project_stops(points, coordinates)
                            legs = []
                            for a, b in zip(positions, positions[1:]):
                                curve = simplify(clip_path(points, a, b, point_at(points, a), point_at(points, b)))
                                if len(curve) == 1:
                                    curve = [curve[0], curve[0]]
                                identifier = "nyct-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
                                result["paths"][identifier] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "shape"}
                                legs.append(identifier)
                        except ValueError as error:
                            gaps[str(error)] += 1
                            result["paths"]["nyct-unresolved"] = {"coordinates": [], "distances": [], "quality": "approximate"}
                            legs = ["nyct-unresolved"] * (len(sequence) - 1)
                        geometry_cache[geometry_key] = legs
                    route = routes[trip["route_id"]]
                    suffixes = {r["stop_id"][-1:] for r in sequence}
                    direction = "Northbound" if suffixes == {"N"} else "Southbound" if suffixes == {"S"} else "Direction " + {"0": "A", "1": "B"}.get(trip["direction_id"], "unknown")
                    pattern = {"mode": "commuter_rail" if route["route_id"] == "SI" else "subway", "operator": "MTA NYCT", "line": f"{route['route_short_name']} · {route['route_long_name']}",
                        "route_id": route["route_id"], "color": "#" + route["route_color"], "direction": direction,
                        "origin": stops[sequence[0]["stop_id"]]["stop_name"], "destination": trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
                        "stops": [[station, a - times[0][0], b - times[0][0]] for station, (a, b) in zip(ids, times)],
                        "legs": geometry_cache[geometry_key]}
                    identifier = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                    result["patterns"][identifier] = pattern
                    for day, departure in instances:
                        result["days"][day].append([identifier, trip_id, departure])
                except (ValueError, KeyError) as error:
                    omissions[str(error)] += 1
        print(f"{path.name}: {len(trips)} candidate subway trips; {len(result['patterns'])} shared patterns", flush=True)
    counts = {}
    for day, rows in result["days"].items():
        if len({(trip, departure) for _, trip, departure in rows}) != len(rows):
            raise ValueError(f"Duplicate trip occurrences on {day}")
        counts[day] = dict(Counter(result["patterns"][p]["route_id"] for p, _, _ in rows))
        if not {"1", "2", "3", "4", "5", "6", "7", "A", "C", "D", "E", "F", "G", "J", "L", "M", "N", "Q", "R", "FS", "GS", "H"} <= set(counts[day]):
            raise ValueError(f"Missing core subway routes on {day}")
        rows.sort(key=lambda r: (r[2], r[1]))
    result["metadata"] = {"start_date": str(FIRST), "end_date": str(LAST), "source": "MTA NYC Subway regular GTFS via MobilityDatabase",
        "source_url": SOURCE_URL, "license": "MTA data feed terms and conditions", "license_url": LICENSE_URL,
        "timezone": str(ZONE), "sources": sources, "daily_services": counts, "omitted_trips": dict(omissions),
        "unresolved_geometry_patterns": dict(gaps), "preferred_period_unavailable": "2024-05-27 through 2024-06-30: archive ZIP required credentials; MyTransit schedules stop at 2016",
        "note": "Regular historical NYC Subway and Staten Island Railway schedules, not a reconstruction of temporary service changes or individual express/local tracks. LIRR, Metro-North, buses and ferries are excluded. No train passenger loads."}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    temporary.replace(output)
    print(f"Saved {output}: {output.stat().st_size} bytes; omissions {dict(omissions)}; geometry gaps {dict(gaps)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/nyc-archives")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/nyc/2025-12-15.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
