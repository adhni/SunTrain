"""Prepare one week of TTC rapid transit from a hash-pinned official GTFS file.

Includes subway Lines 1/2/4 and light rail Lines 5/6, excluding streetcars,
replacement buses, GO and UP Express. Downloads are preparation only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_australian_replay import file_hash, path_legs, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_transit_replay import active_services, seconds

SOURCE = {
    "name": "Toronto", "first": "2026-10-05", "last": "2026-10-11", "timezone": "America/Toronto",
    "captured": "2026-10-18", "published": "2026-09-30",
    "url": "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b811ead4-6eaf-4adb-8408-d389fb5a069c/resource/c920e221-7a1c-488b-8c5b-6d8cd4e85eaf/download/completegtfs.zip",
    "sha256": "5e0191d59cb991b6c88ba9c1a5f2ca93a5a064a4d258dbc7ba93801d15f3dfca",
    "source": "Toronto Transit Commission official Merged GTFS – TTC Routes and Schedules",
    "source_url": "https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/",
    "license": "Open Government Licence – Toronto", "license_url": "https://open.toronto.ca/open-data-licence/",
    "attribution": "Contains information licensed under the Open Government Licence – Toronto. Timetable and railway geometry: TTC / City of Toronto · source published 30 September 2026",
    "note": "TTC rapid transit only: subway Lines 1, 2 and 4, and light rail Lines 5 and 6. Two Line 1 journey variants have unresolved source geometry; their vehicles appear at stations only. Streetcars, buses, GO Transit and UP Express are excluded. Regular schedules, not a reconstruction of every closure. No individual train passenger loads.",
}


def selected_route(route, agencies):
    agency = route.get("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
    if agencies.get(agency, {}).get("agency_name") != "TTC":
        return False
    return (route["route_type"] == "1" and route["route_short_name"] in {"1", "2", "4"}) or (
        route["route_type"] == "0" and route["route_short_name"] in {"5", "6"})


def prepare(cache, output):
    city, source = "toronto", SOURCE
    first, last = date.fromisoformat(source["first"]), date.fromisoformat(source["last"])
    zone = ZoneInfo(source["timezone"])
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    service_days = [first - timedelta(days=1), *days, last + timedelta(days=1)]
    zero = lambda day: int(datetime.combine(day, time(12), zone).timestamp()) - 43200
    windows = [(str(d), int(datetime.combine(d, time(3), zone).timestamp()), int(datetime.combine(d + timedelta(days=1), time(3), zone).timestamp()), zero(d)) for d in days]
    cache.mkdir(parents=True, exist_ok=True)
    filename = fetch(source["url"], cache / source["url"].rsplit("/", 1)[1])
    if file_hash(filename) != source["sha256"]:
        raise ValueError("Archive differs from the validated source; inspect it before changing the pin")
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(d): [] for d in days}}
    station_ids, geometry_cache = {}, {}
    omissions, gaps, gap_trips, native_count = Counter(), Counter(), {}, 0
    with ZipFile(filename) as archive:
        feed = next(records(archive, "feed_info.txt"))
        if not (feed["feed_start_date"] <= service_days[0].strftime("%Y%m%d")
                and service_days[-1].strftime("%Y%m%d") <= feed["feed_end_date"]):
            raise ValueError("Feed validity does not cover the replay and adjoining service days")
        agencies = {r["agency_id"]: r for r in records(archive, "agency.txt")}
        routes = {r["route_id"]: r for r in records(archive, "routes.txt") if selected_route(r, agencies)}
        if not routes:
            raise ValueError("No selected rail routes")
        calendars = list(records(archive, "calendar.txt")) if "calendar.txt" in archive.namelist() else []
        exceptions = list(records(archive, "calendar_dates.txt")) if "calendar_dates.txt" in archive.namelist() else []
        active = {d: active_services(calendars, exceptions, d) for d in service_days}
        relevant = set().union(*active.values())
        trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes and r["service_id"] in relevant}
        if "frequencies.txt" in archive.namelist() and any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
            raise ValueError("Frequency-based rail service needs explicit handling")
        stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
        calls = defaultdict(list)
        for row in records(archive, "stop_times.txt"):
            if row["trip_id"] in trips:
                calls[row["trip_id"]].append(row)
        shapes = defaultdict(list)
        needed = {t.get("shape_id", "") for t in trips.values()}
        for row in records(archive, "shapes.txt"):
            if row["shape_id"] in needed:
                shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                    float(row["shape_dist_traveled"]) if row.get("shape_dist_traveled") else None,
                    [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)]))
        signatures = {key: hashlib.sha256(json.dumps(raw).encode()).hexdigest() for key, raw in shapes.items()}
        print(f"{city}: {len(routes)} rail route variants, {len(trips)} candidate trips, {len(shapes)} supplied shapes", flush=True)
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
                instances = []
                for day in service_days:
                    if trip["service_id"] not in active[day]:
                        continue
                    departure, finish = zero(day) + times[0][0], zero(day) + times[-1][1]
                    for business_date, start, end, midnight in windows:
                        if departure < end and finish >= start:
                            instances.append((business_date, departure - midnight))
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
                raw = shapes.get(trip.get("shape_id", ""), [])
                anchored = bool(raw) and all(r.get("shape_dist_traveled", "") != "" for r in sequence) and all(a is not None for _, a, _ in raw)
                anchors = [float(r["shape_dist_traveled"]) for r in sequence] if anchored else None
                geometry_key = (signatures.get(trip.get("shape_id", "")), tuple(anchors) if anchors is not None else None, tuple(map(tuple, coordinates)))
                if geometry_key not in geometry_cache:
                    try:
                        curves = path_legs(raw, anchors, coordinates)
                        legs = []
                        for curve in curves:
                            key = city + "-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
                            result["paths"][key] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "shape"}
                            legs.append(key)
                        native_count += anchored
                    except (ValueError, IndexError) as error:
                        gaps[str(error)] += 1
                        key = city + "-unresolved"
                        result["paths"][key] = {"coordinates": [], "distances": [], "quality": "approximate"}
                        legs = [key] * (len(sequence) - 1)
                    geometry_cache[geometry_key] = legs
                legs = geometry_cache[geometry_key]
                if any(result["paths"][key]["quality"] == "approximate" for key in legs):
                    gap_trips[trip_id] = trip.get("shape_id", "")
                route = routes[trip["route_id"]]
                agency = route.get("agency_id") or next(iter(agencies))
                operator = agencies[agency]["agency_name"]
                if agencies[agency]["agency_timezone"] != source["timezone"]:
                    raise ValueError("Unexpected rail operator timezone")
                short, long = route.get("route_short_name", ""), route.get("route_long_name", "")
                label = f"Line {short} · {long.removesuffix(' Line')}"
                color = route.get("route_color", "").lstrip("#") or "6F818E"
                if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
                    raise ValueError("Invalid route colour")
                pattern = {"mode": "subway" if route["route_type"] == "1" else "light_rail", "operator": operator,
                    "line": label, "route_id": short or trip["route_id"], "source_route_id": trip["route_id"], "color": "#" + color,
                    "direction": "Direction " + {"0": "A", "1": "B"}.get(trip.get("direction_id"), "unknown"),
                    "origin": stops[sequence[0]["stop_id"]]["stop_name"], "destination": trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
                    "stops": [[station, a - times[0][0], b - times[0][0]] for station, (a, b) in zip(ids, times)], "legs": legs}
                key = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                result["patterns"][key] = pattern
                for day, departure in instances:
                    result["days"][day].append([key, trip_id, departure])
            except (ValueError, KeyError) as error:
                omissions[str(error)] += 1
    counts = {}
    for day, rows in result["days"].items():
        if not rows or len({(trip, departure) for _, trip, departure in rows}) != len(rows):
            raise ValueError(f"Empty day or duplicate occurrences on {day}")
        rows.sort(key=lambda row: (row[2], row[1]))
        counts[day] = dict(Counter(result["patterns"][p]["route_id"] for p, _, _ in rows))
    result["metadata"] = {"start_date": source["first"], "end_date": source["last"], "timezone": source["timezone"],
        "source": source["source"], "source_url": source["source_url"], "license": source["license"], "license_url": source["license_url"],
        "attribution": source["attribution"], "replay_note": source["note"],
        "sources": [{"source_url": source["url"], "source_date": source["captured"], "published": source["published"],
                     "feed_version": feed["feed_version"], "valid_from": feed["feed_start_date"],
                     "valid_through": feed["feed_end_date"], "sha256": source["sha256"]}],
        "daily_services": counts, "omitted_trips": dict(omissions), "unresolved_geometry_patterns": dict(gaps),
        "unresolved_geometry_trips": gap_trips, "native_anchor_patterns": native_count,
        "note": "Scheduled estimates, not GPS or a reconstruction of every historical disruption. Only services active in source calendars appear. No individual train passenger loads."}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    temporary.replace(output)
    print(f"Saved {output}: {output.stat().st_size} bytes; {len(result['patterns'])} shared patterns; omissions {dict(omissions)}; gaps {dict(gaps)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/toronto-audit")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/toronto" / (SOURCE["first"] + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.output)
