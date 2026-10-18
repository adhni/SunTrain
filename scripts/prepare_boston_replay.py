"""Prepare the 24–30 June 2024 MBTA rail and Silver Line replay from the historical archive.

Downloads are preparation only. The app serves a compact local reference, never GTFS ZIPs.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.replay import cumulative_distances
from scripts.prepare_replay_geometry import clip_path, point_at, simplify
from scripts.prepare_transit_replay import active_services, records, seconds
from scripts.compact_transit import compact_reference, daily_reference, save_reference

ROOT = Path(__file__).resolve().parents[1]
INDEX_URL = "https://cdn.mbta.com/archive/archived_feeds.txt"
LICENSE_URL = "https://github.com/mbta/gtfs-documentation/blob/master/developers-license-agreement.pdf"
FIRST, LAST = date(2024, 6, 24), date(2024, 6, 30)
ZONE = ZoneInfo("America/New_York")
MODES = {"0": "light_rail", "1": "subway", "2": "commuter_rail"}
SILVER_LINE_GROUPS = {"line-SLWaterfront", "line-SLWashington"}
SUPPORTED_MODES = set(MODES.values()) | {"silver_line"}
BASELINE_REFERENCE = ROOT / "data/reference/boston/2024-06-24.json.gz"


def service_zero(day):
    return int(datetime.combine(day, time(12), ZONE).timestamp()) - 12 * 3600


def project_stops(points, stops, tolerance=150):
    """Match the complete ordered stop sequence to one trip-specific shape.

    MBTA stop_times has no shape distance anchors. Keep all nearby local minima,
    then find the least-error forward sequence, so repeated stops on loops map to
    separate occurrences. Never draw connectors or substitute another route.
    """
    curve = np.asarray(points, dtype=float)
    if len(curve) < 2 or not np.isfinite(curve).all():
        raise ValueError("Missing or invalid shape")
    scale = np.array([math.cos(math.radians(float(curve[:, 1].mean()))), 1.0]) * 111195
    starts, vectors = curve[:-1] * scale, np.diff(curve, axis=0) * scale
    lengths = np.maximum(np.sum(vectors ** 2, axis=1), 1e-20)
    levels, previous = [], []
    for stop_index, stop in enumerate(stops):
        offset = np.asarray(stop) * scale - starts
        fractions = np.clip(np.sum(offset * vectors, axis=1) / lengths, 0, 1)
        errors = np.sum((offset - fractions[:, None] * vectors) ** 2, axis=1)
        indices = np.where((errors <= np.r_[np.inf, errors[:-1]]) &
                           (errors <= np.r_[errors[1:], np.inf]) & (errors <= tolerance ** 2))[0]
        candidates = []
        for index in indices:
            position = float(index + fractions[index])
            if candidates and abs(position - candidates[-1][0]) < 1e-7:
                continue
            if stop_index == 0:
                candidates.append((position, float(errors[index]), None))
                continue
            minimum_step = 0 if stops[stop_index - 1] == stop else 1e-7
            choices = [(entry[1], j) for j, entry in enumerate(previous)
                       if entry[0] + minimum_step <= position]
            if choices:
                cost, parent = min(choices)
                candidates.append((position, cost + float(errors[index]), parent))
        if not candidates:
            raise ValueError("Stops do not match shape in journey order within 150 m")
        levels.append(candidates)
        previous = candidates
    index = min(range(len(previous)), key=lambda j: previous[j][1])
    positions = []
    for level in reversed(levels):
        position, _, parent = level[index]
        positions.append(position)
        index = parent
    return list(reversed(positions))


def is_silver_line(route):
    # Official MBTA line groups include SL1–SL5 and the SLW short-turn service.
    return route.get("line_id") in SILVER_LINE_GROUPS


def is_regular_bus(route):
    return route["route_type"] == "3" and not is_silver_line(route) and route.get("route_desc") != "Rail Replacement Bus"


def replay_mode(trip, route, regular_buses=False):
    # MBTA replacement buses may use a rail route ID. The trip override wins.
    vehicle_type = trip.get("trip_route_type", "").strip() or route["route_type"]
    if vehicle_type == "3" and is_silver_line(route):
        return "silver_line"
    if vehicle_type == "3" and regular_buses and is_regular_bus(route):
        return "bus"
    return MODES.get(vehicle_type)


def feed_for(day, index):
    stamp = day.strftime("%Y%m%d")
    matches = [r for r in index if r["feed_start_date"] <= stamp <= r["feed_end_date"]]
    if len(matches) != 1:
        raise ValueError(f"Expected one official archive for {day}, found {len(matches)}")
    return matches[0]


def fetch(url, path):
    if not path.exists():
        print(f"Downloading {url}", flush=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
        temporary.replace(path)
    return path


def prepare(cache, output, *, buses=False):
    cache.mkdir(parents=True, exist_ok=True)
    index_path = fetch(INDEX_URL, cache / "index.csv")
    with index_path.open(encoding="utf-8-sig") as stream:
        index = list(csv.DictReader(stream))
    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    service_days = [FIRST - timedelta(days=1), *days, LAST + timedelta(days=1)]
    selected = {day: feed_for(day, index) for day in service_days}
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(d): [] for d in days}}
    station_ids, geometry_cache = {}, {}
    omissions, exclusions, geometry_failures = Counter(), Counter(), Counter()
    sources = []
    if buses:
        with gzip.open(BASELINE_REFERENCE, "rt") as stream:
            pins = {r["archive_url"]: r["sha256"] for r in json.load(stream)["metadata"]["sources"]}
    for url in sorted({row["archive_url"] for row in selected.values()}):
        source = next(row for row in selected.values() if row["archive_url"] == url)
        archive_path = fetch(url, cache / url.rsplit("/", 1)[1])
        sources.append({key: source[key] for key in ("feed_start_date", "feed_end_date", "feed_version", "archive_url")})
        sources[-1]["sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if buses and pins.get(url) != sources[-1]["sha256"]:
            raise ValueError("Bus source differs from the validated Boston rail archive")
        applicable = [d for d in service_days if selected[d]["archive_url"] == url]
        with ZipFile(archive_path) as archive:
            calendars = list(records(archive, "calendar.txt")) if "calendar.txt" in archive.namelist() else []
            exceptions = list(records(archive, "calendar_dates.txt"))
            active = {d: active_services(calendars, exceptions, d) for d in applicable}
            relevant = set().union(*active.values())
            agencies = {r["agency_id"] for r in records(archive, "agency.txt") if r["agency_name"] == "MBTA"}
            routes = {r["route_id"]: r for r in records(archive, "routes.txt")
                      if r["agency_id"] in agencies and (is_regular_bus(r) if buses else r["route_type"] in MODES or is_silver_line(r))}
            canonical = {r["route_pattern_id"] for r in records(archive, "route_patterns.txt")
                         if r.get("route_pattern_typicality") == "5"}
            trips = {}
            for trip in records(archive, "trips.txt"):
                if trip["route_id"] not in routes or trip["service_id"] not in relevant:
                    continue
                mode = replay_mode(trip, routes[trip["route_id"]], regular_buses=buses)
                if not mode or buses and mode != "bus":
                    exclusions["replacement_bus_trip_records"] += 1
                elif trip.get("route_pattern_id") not in canonical:
                    trips[trip["trip_id"]] = trip
            if "frequencies.txt" in archive.namelist() and any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
                raise ValueError("Frequency-based MBTA service needs explicit handling")
            directions = {(r["route_id"], r["direction_id"]): r["direction"] for r in records(archive, "directions.txt")}
            stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
            calls = defaultdict(list)
            for row in records(archive, "stop_times.txt"):
                if row["trip_id"] in trips:
                    calls[row["trip_id"]].append(row)
            shapes = defaultdict(list)
            needed = {trip["shape_id"] for trip in trips.values()}
            for row in records(archive, "shapes.txt"):
                if row["shape_id"] in needed:
                    shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                        [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)]))
            shapes = {key: [point for _, point in sorted(rows)] for key, rows in shapes.items()}
            signatures = {key: hashlib.sha256(json.dumps(points).encode()).hexdigest() for key, points in shapes.items()}
            for trip_id, trip in trips.items():
                sequence = sorted(calls[trip_id], key=lambda row: int(row["stop_sequence"]))
                try:
                    if len(sequence) < 2:
                        raise ValueError("Fewer than two stops")
                    coordinates = [[float(stops[r["stop_id"]]["stop_lon"]), float(stops[r["stop_id"]]["stop_lat"])] for r in sequence]
                    if not all(math.isfinite(v) for coordinate in coordinates for v in coordinate):
                        raise ValueError("Invalid coordinates")
                    times = [(seconds(r["arrival_time"]), seconds(r["departure_time"])) for r in sequence]
                    flat = [v for pair in times for v in pair]
                    if any(b < a for a, b in zip(flat, flat[1:])):
                        raise ValueError("Backwards times")
                    occurrences = []
                    for service_day in applicable:
                        if trip["service_id"] not in active[service_day]:
                            continue
                        departure = service_zero(service_day) + times[0][0]
                        finish = service_zero(service_day) + times[-1][1]
                        for day in days:
                            start = int(datetime.combine(day, time(3), ZONE).timestamp())
                            end = int(datetime.combine(day + timedelta(days=1), time(3), ZONE).timestamp())
                            if departure < end and finish >= start:
                                occurrences.append((str(day), departure - service_zero(day)))
                    if not occurrences:
                        continue
                    mode = replay_mode(trip, routes[trip["route_id"]], regular_buses=buses)
                    stop_mode = "bus" if mode in {"silver_line", "bus"} else "train"
                    ids = []
                    for row, coordinate in zip(sequence, coordinates):
                        stop = stops[row["stop_id"]]
                        key = (stop_mode, stop["stop_id"], stop["stop_name"], *coordinate)
                        if key not in station_ids:
                            station_ids[key] = len(result["stations"])
                            result["stations"].append({"name": stop["stop_name"], "lon": coordinate[0], "lat": coordinate[1], "mode": stop_mode})
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
                                    curve *= 2
                                identifier = "mbta-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:16]
                                result["paths"][identifier] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "shape"}
                                legs.append(identifier)
                        except ValueError as error:
                            geometry_failures[str(error)] += 1
                            identifier = "mbta-unresolved"
                            result["paths"][identifier] = {"coordinates": [], "distances": [], "quality": "approximate"}
                            legs = [identifier] * (len(sequence) - 1)
                        geometry_cache[geometry_key] = legs
                    route = routes[trip["route_id"]]
                    line = f"{route['route_short_name']} · {route['route_long_name']}" if mode in {"silver_line", "bus"} else route["route_long_name"]
                    pattern = {"mode": mode, "operator": "MBTA", "line": line,
                        "route_id": route["route_id"], "color": "#" + route["route_color"],
                        "direction": directions.get((trip["route_id"], trip["direction_id"]), ""),
                        "origin": stops[sequence[0]["stop_id"]]["stop_name"],
                        "destination": trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
                        "stops": [[station, a - times[0][0], b - times[0][0]] for station, (a, b) in zip(ids, times)],
                        "legs": geometry_cache[geometry_key]}
                    identifier = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                    result["patterns"][identifier] = pattern
                    for day, offset in occurrences:
                        result["days"][day].append([identifier, trip_id, offset])
                except (ValueError, KeyError) as error:
                    omissions[str(error)] += 1
        scope = "regular bus" if buses else "rail / Silver Line"
        print(f"{archive_path.name}: {len(trips)} candidate {scope} trips; {len(result['patterns'])} shared patterns", flush=True)
    counts = {}
    for day, rows in result["days"].items():
        identities = [(row[1], row[2]) for row in rows]
        if len(set(identities)) != len(identities):
            raise ValueError(f"Duplicate trip occurrences on {day}")
        counts[day] = dict(Counter(result["patterns"][row[0]]["mode"] for row in rows))
        if set(counts[day]) != ({"bus"} if buses else SUPPORTED_MODES):
            raise ValueError(f"Incomplete {'regular bus' if buses else 'rail / Silver Line'} coverage on {day}")
        rows.sort(key=lambda row: (row[2], row[1]))
    result["metadata"] = {"start_date": str(FIRST), "end_date": str(LAST), "source": "MBTA historical GTFS Schedule",
        "source_url": INDEX_URL, "license": "MBTA MassDOT Developer License Agreement", "license_url": LICENSE_URL,
        "timezone": str(ZONE), "sources": sources, "daily_services": counts, "omitted_trips": dict(omissions),
        "excluded": dict(exclusions), "unresolved_geometry_patterns": dict(geometry_failures),
        "note": "Scheduled rail and Silver Line services; other buses, replacement shuttles and non-MBTA operators excluded. Positions are estimates, not recorded movements."}
    if buses:
        result["metadata"].update({"attribution": "Regular bus timetables and road geometry: MassDOT / MBTA historical GTFS · 24–30 June 2024",
            "note": "Regular MBTA buses follow dated road shapes. Rail replacement shuttles, Silver Line and non-MBTA operators are excluded from this bus layer. No passenger loads or observed GPS positions."})
        compact_reference(result, prefix="mbta-bus-stops-")
        output.mkdir(parents=True, exist_ok=True)
        for day in result["days"]:
            destination = output / (day + ".json.gz")
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            with temporary.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
                stream.write(json.dumps(daily_reference(result, day), separators=(",", ":"), allow_nan=False).encode())
            temporary.replace(destination)
        print(json.dumps(result["metadata"], indent=2), flush=True)
        return
    save_reference(result, output)
    print(json.dumps(result["metadata"], indent=2), flush=True)
    print(f"Saved {output}: {output.stat().st_size / 1e6:.2f} MB", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/boston-archives")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/boston/2024-06-24.json.gz")
    parser.add_argument("--buses", action="store_true", help="Prepare separate daily regular-bus bundles using the pinned rail archives")
    args = parser.parse_args()
    prepare(args.cache, ROOT / "data/reference/boston/bus" if args.buses and args.output == BASELINE_REFERENCE else args.output, buses=args.buses)
