"""Prepare 5–11 October 2026 LTA train schedules on validated OSM rail paths.

This uses the pinned 17 October snapshot, not an archive of every disruption.
GTFS times and stop sequences are never corrected to fit the geometry.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_boston_replay import project_stops
from scripts.prepare_replay_geometry import clip_path, point_at, simplify
from scripts.prepare_transit_replay import active_services, business_occurrences, records, seconds

FIRST, LAST = date(2026, 10, 5), date(2026, 10, 11)
GTFS_SHA256 = "d825c9021f0bad4241cee0a4cef10c23a4434a2d2521169cde2fb81d332e1a9e"
GEOMETRY = ROOT / "data/reference/singapore/osm-rail-2026-10-17.json.gz"
SOURCE_URL = "https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html"
LICENSE_URL = "https://datamall.lta.gov.sg/content/datamall/en/SingaporeOpenDataLicence.html"


def match_geometry(variants, stops):
    """Match a complete ordered journey to one connected, directional OSM run."""
    choices = []
    for variant in variants:
        points = variant["coordinates"]
        # OSM may begin a closed loop midway around it. One additional traversal
        # permits terminal-to-terminal journeys without inventing a closing edge.
        if points[0] == points[-1]:
            points = points + points[1:]
        try:
            positions = project_stops(points, stops)
        except ValueError:
            continue
        error = sum(cumulative_distances([stop, point_at(points, position)])[-1] ** 2
                    for stop, position in zip(stops, positions))
        length = cumulative_distances(clip_path(points, positions[0], positions[-1],
                                  point_at(points, positions[0]), point_at(points, positions[-1])))[-1]
        choices.append((error, length, str(variant["relation"]), points, positions))
    if not choices:
        raise ValueError("No connected OSM route matches the complete ordered stop sequence within 150 m")
    _, _, relation, points, positions = min(choices, key=lambda row: row[:3])
    legs = [simplify(clip_path(points, a, b, point_at(points, a), point_at(points, b)))
            for a, b in zip(positions, positions[1:])]
    return relation, [leg if len(leg) >= 2 else [leg[0], leg[0]] for leg in legs]


def prepare(filename, geometry, output):
    digest = hashlib.sha256(filename.read_bytes()).hexdigest()
    if digest != GTFS_SHA256:
        raise ValueError("GTFS differs from the validated snapshot; audit dates and coverage before changing the pin")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    calendar_days = [FIRST - timedelta(days=1), *days, LAST + timedelta(days=1)]
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(day): [] for day in days}}
    station_ids, geometry_cache = {}, {}
    omissions, unresolved, matched_relations = Counter(), {}, set()
    with ZipFile(filename) as archive:
        agencies = {r["agency_id"]: r for r in records(archive, "agency.txt")}
        if any(r["agency_timezone"] != "Asia/Singapore" for r in agencies.values()):
            raise ValueError("Unexpected agency timezone")
        routes = {r["route_id"]: r for r in records(archive, "routes.txt")
                  if r["route_type"] in {"0", "1"} and r["agency_id"] in {"SMRT", "SBST"}}
        calendars, exceptions = list(records(archive, "calendar.txt")), list(records(archive, "calendar_dates.txt"))
        active = {day: active_services(calendars, exceptions, day) for day in calendar_days}
        relevant = set().union(*active.values())
        trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes and r["service_id"] in relevant}
        if "frequencies.txt" in archive.namelist() and any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
            raise ValueError("Frequency-based services need explicit handling")
        stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
        calls = defaultdict(list)
        for row in records(archive, "stop_times.txt"):
            if row["trip_id"] in trips:
                calls[row["trip_id"]].append(row)
        for trip_id, trip in trips.items():
            sequence = sorted(calls[trip_id], key=lambda r: int(r["stop_sequence"]))
            try:
                if len(sequence) < 2:
                    raise ValueError("Fewer than two stops")
                coordinates = [[float(stops[r["stop_id"]]["stop_lon"]), float(stops[r["stop_id"]]["stop_lat"])] for r in sequence]
                if not all(math.isfinite(value) for point in coordinates for value in point):
                    raise ValueError("Invalid station coordinates")
                times = [(seconds(r["arrival_time"]), seconds(r["departure_time"])) for r in sequence]
                flat = [v for pair in times for v in pair]
                if any(b < a for a, b in zip(flat, flat[1:])):
                    raise ValueError("Backwards times")
                service_days = [day for day in calendar_days if trip["service_id"] in active[day]]
                instances = [(str(day), times[0][0] + shift) for day in days
                             for shift in business_occurrences(day, service_days, times[0][0], times[-1][1])]
                if not instances:
                    continue
                route = routes[trip["route_id"]]
                code = route["route_short_name"]
                ids = []
                for row, point in zip(sequence, coordinates):
                    key = row["stop_id"]
                    if key not in station_ids:
                        station_ids[key] = len(result["stations"])
                        result["stations"].append({"name": stops[key]["stop_name"], "lon": point[0], "lat": point[1], "mode": "train"})
                    ids.append(station_ids[key])
                geometry_key = (code, tuple(r["stop_id"] for r in sequence))
                if geometry_key not in geometry_cache:
                    try:
                        relation, curves = match_geometry(geographic["lines"].get(code, []), coordinates)
                        matched_relations.add(relation)
                        legs = []
                        for curve in curves:
                            identifier = "sg-osm-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
                            result["paths"][identifier] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "track"}
                            legs.append(identifier)
                    except ValueError as error:
                        result["paths"]["sg-unresolved"] = {"coordinates": [], "distances": [], "quality": "approximate"}
                        legs = ["sg-unresolved"] * (len(sequence) - 1)
                    geometry_cache[geometry_key] = legs
                legs = geometry_cache[geometry_key]
                if "sg-unresolved" in legs:
                    unresolved[trip_id] = {"line": code, "stops": [r["stop_id"] for r in sequence],
                        "reason": "Complete stop sequence does not match a connected directional OSM path; no movement interpolated"}
                pattern = {"mode": "light_rail" if route["route_type"] == "0" else "subway",
                    "operator": "SBS Transit" if route["agency_id"] == "SBST" else "SMRT",
                    "line": f"{code} · {route['route_long_name']}", "route_id": code, "source_route_id": route["route_id"],
                    "color": "#" + route["route_color"], "direction": "Direction " + {"0": "A", "1": "B"}[trip["direction_id"]],
                    "origin": stops[sequence[0]["stop_id"]]["stop_name"],
                    "destination": trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
                    "stops": [[identifier, a - times[0][0], b - times[0][0]] for identifier, (a, b) in zip(ids, times)], "legs": legs}
                identifier = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                result["patterns"][identifier] = pattern
                for day, departure in instances:
                    result["days"][day].append([identifier, trip_id, departure])
            except (ValueError, KeyError) as error:
                omissions[str(error)] += 1
    counts = {}
    for day, rows in result["days"].items():
        if len({(trip, departure) for _, trip, departure in rows}) != len(rows):
            raise ValueError(f"Duplicate trip occurrence on {day}")
        counts[day] = dict(Counter(result["patterns"][p]["route_id"] for p, _, _ in rows))
        if set(counts[day]) != {"NS", "EW", "CG", "NE", "CC", "DT", "TE", "BP", "SK", "PG"}:
            raise ValueError(f"Incomplete line coverage on {day}")
        rows.sort(key=lambda row: (row[2], row[1]))
    if omissions:
        raise ValueError(f"Invalid timetable trips: {dict(omissions)}")
    result["metadata"] = {"start_date": str(FIRST), "end_date": str(LAST), "timezone": "Asia/Singapore",
        "source": "LTA DataMall GTFS Schedule (Train)", "source_url": SOURCE_URL, "source_date": "2026-10-17",
        "license": "Singapore Open Data Licence v1.0", "license_url": LICENSE_URL,
        "sha256": digest, "geometry": geographic["metadata"], "matched_osm_relations": sorted(matched_relations),
        "daily_services": counts, "omitted_trips": {}, "unresolved_geometry_trips": unresolved,
        "note": "LTA snapshot calendars applied to 5–11 October 2026, not a reconstruction of every past disruption. Estimated movement follows OSM geography from 17 October. No individual train loads. One anomalous Sunday NS stop sequence is retained without interpolated movement."}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    temporary.replace(output)
    print(f"Saved {output}: {output.stat().st_size} bytes; {len(result['patterns'])} shared patterns; {len(unresolved)} unresolved trips", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtfs", type=Path, default=ROOT / ".cache/singapore-audit/train-gtfs.zip")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/singapore/2026-10-05.json.gz")
    args = parser.parse_args()
    prepare(args.gtfs, args.geometry, args.output)
