"""Prepare a date range of tram/bus replay from an archived PTV GTFS bundle."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_replay_geometry import anchored_shape

SOURCE_URL = "https://files.mobilitydatabase.org/mdb-657/mdb-657-202406240001/mdb-657-202406240001.zip"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data/reference/transit/2024-06-24.json.gz"
# Keep complete journeys serving the Melbourne map extent, including outer termini.
MELBOURNE = (144.55, -38.15, 145.6, -37.48)


def records(archive, filename):
    with archive.open(filename) as stream:
        yield from csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))


def seconds(clock):
    hours, minutes, secs = map(int, clock.split(":"))
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= secs < 60:
        raise ValueError("Invalid GTFS time")
    return hours * 3600 + minutes * 60 + secs


def active_services(calendars, exceptions, day):
    stamp = day.strftime("%Y%m%d")
    weekday = day.strftime("%A").lower()
    active = {r["service_id"] for r in calendars if r["start_date"] <= stamp <= r["end_date"] and r[weekday] == "1"}
    for row in exceptions:
        if row["date"] == stamp:
            if row["exception_type"] == "1":
                active.add(row["service_id"])
            elif row["exception_type"] == "2":
                active.discard(row["service_id"])
    return active


def business_occurrences(day, active_dates, start, end):
    """GTFS hours can exceed 24; include carry-in and next-day early services."""
    for service_day in active_dates:
        shift = (service_day - day).days * 86400
        if start + shift < 27 * 3600 and end + shift >= 3 * 3600:
            yield shift


def prepare(filename, output, *, start_date="2024-06-24", end_date="2024-06-30", source_date="2024-06-24",
            source_url=SOURCE_URL, geometry_cache=None, path_cache=None):
    first, last = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if first > last:
        raise ValueError("Start date must precede end date")
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    calendar_days = [first - timedelta(days=1), *days, last + timedelta(days=1)]
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {d.isoformat(): [] for d in days}}
    omitted = defaultdict(int)
    invalid_reasons = defaultdict(int)
    geometry_cache = {} if geometry_cache is None else geometry_cache
    path_cache = {} if path_cache is None else path_cache
    with ZipFile(filename) as outer:
        for branch, mode, operator, route_type in (("3", "tram", "PTV tram", "0"), ("4", "bus", "PTV bus", "3")):
            with ZipFile(io.BytesIO(outer.read(f"{branch}/google_transit.zip"))) as archive:
                calendars, exceptions = list(records(archive, "calendar.txt")), list(records(archive, "calendar_dates.txt"))
                active = {d: active_services(calendars, exceptions, d) for d in calendar_days}
                relevant = set().union(*active.values())
                routes = {r["route_id"]: r for r in records(archive, "routes.txt") if r["route_type"] == route_type}
                trips = {r["trip_id"]: r for r in records(archive, "trips.txt")
                         if r["service_id"] in relevant and r["route_id"] in routes}
                stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
                station_ids = {}
                for key, stop in stops.items():
                    lon, lat = float(stop["stop_lon"]), float(stop["stop_lat"])
                    if math.isfinite(lon) and math.isfinite(lat):
                        station_ids[key] = len(result["stations"])
                        result["stations"].append({"name": stop["stop_name"], "lat": round(lat, 6), "lon": round(lon, 6), "mode": mode})
                calls = defaultdict(list)
                for row in records(archive, "stop_times.txt"):
                    if row["trip_id"] in trips:
                        calls[row["trip_id"]].append(row)
                needed_shapes = {t["shape_id"] for t in trips.values()}
                shapes = defaultdict(list)
                for r in records(archive, "shapes.txt"):
                    if r["shape_id"] in needed_shapes:
                        shapes[r["shape_id"]].append((int(r["shape_pt_sequence"]), float(r["shape_dist_traveled"]),
                            [round(float(r["shape_pt_lon"]), 6), round(float(r["shape_pt_lat"]), 6)]))
                shape_signatures = {key: hashlib.sha256(json.dumps(raw, separators=(",", ":")).encode()).hexdigest()
                                    for key, raw in shapes.items()}
                for trip_id, trip in trips.items():
                    sequence = sorted(calls[trip_id], key=lambda r: int(r["stop_sequence"]))
                    try:
                        if len(sequence) < 2 or any(s["stop_id"] not in station_ids for s in sequence):
                            raise ValueError("Missing stops")
                        coordinates = [result["stations"][station_ids[s["stop_id"]]] for s in sequence]
                        if mode == "bus" and not any(MELBOURNE[0] <= s["lon"] <= MELBOURNE[2] and MELBOURNE[1] <= s["lat"] <= MELBOURNE[3] for s in coordinates):
                            continue
                        times = [(seconds(s["arrival_time"]), seconds(s["departure_time"])) for s in sequence]
                        flattened = [v for pair in times for v in pair]
                        if any(b < a for a, b in zip(flattened, flattened[1:])):
                            raise ValueError("Backwards times")
                        start, end = times[0][0], times[-1][1]
                        dates = [d for d in calendar_days if trip["service_id"] in active[d]]
                        occurrences = [(d, shift) for d in days for shift in business_occurrences(d, dates, start, end)]
                        if not occurrences:
                            continue
                        anchors = tuple(float(s["shape_dist_traveled"]) if s["shape_dist_traveled"].strip() else None for s in sequence)
                        geometry_key = (shape_signatures.get(trip["shape_id"], "missing"), anchors)
                        if geometry_key not in geometry_cache:
                            legs = []
                            try:
                                if any(x is None or not math.isfinite(x) for x in anchors):
                                    raise ValueError("Missing shape anchors")
                                if any(b < a for a, b in zip(anchors, anchors[1:])):
                                    raise ValueError("Backwards shape anchors")
                                points, indices = anchored_shape(shapes[trip["shape_id"]], [(x, "") for x in anchors])
                                for a, b in zip(indices, indices[1:]):
                                    curve = points[a:b + 1]
                                    if len(curve) == 1:
                                        curve = [curve[0], curve[0]]
                                    identifier = "gtfs-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:16]
                                    path_cache[identifier] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "shape"}
                                    legs.append(identifier)
                            except (ValueError, IndexError):
                                identifier = "gtfs-unresolved"
                                path_cache[identifier] = {"coordinates": [], "distances": [], "quality": "approximate"}
                                legs = [identifier] * (len(sequence) - 1)
                            geometry_cache[geometry_key] = legs
                        for identifier in geometry_cache[geometry_key]:
                            result["paths"][identifier] = path_cache[identifier]
                        route = routes[trip["route_id"]]
                        pattern = {"mode": mode, "operator": operator,
                                   "line": f"{mode.title()} {route['route_short_name']} · {route['route_long_name']}",
                                   "direction": {"0": "A", "1": "B"}.get(trip["direction_id"], ""),
                                   "origin": coordinates[0]["name"], "destination": coordinates[-1]["name"],
                                   "stops": [[station_ids[s["stop_id"]], arrival - start, departure - start]
                                             for s, (arrival, departure) in zip(sequence, times)], "legs": geometry_cache[geometry_key]}
                        identifier = hashlib.sha256(json.dumps(pattern).encode()).hexdigest()[:16]
                        result["patterns"][identifier] = pattern
                        for d, shift in occurrences:
                            result["days"][d.isoformat()].append([identifier, trip_id, start + shift])
                    except (ValueError, KeyError, TypeError) as error:
                        omitted[mode] += 1
                        invalid_reasons[str(error)] += 1
                print(f"{mode}: {len(trips)} candidate trips; {len(geometry_cache)} route patterns; {omitted[mode]} invalid trips omitted", flush=True)
    for day, rows in result["days"].items():
        if {result["patterns"][row[0]]["mode"] for row in rows} != {"tram", "bus"}:
            raise ValueError(f"No shared tram/bus coverage for {day}; use an archive covering this date")
    result["metadata"] = {"start_date": start_date, "end_date": end_date, "source": "PTV GTFS Schedule",
        "source_date": source_date, "source_url": source_url, "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/", "bus_area": "Complete journeys serving the Melbourne map extent",
        "omitted_trips": dict(omitted), "invalid_reasons": dict(invalid_reasons)}
    save_reference(result, output)
    print(f"Saved {output}: {output.stat().st_size / 1e6:.1f} MB; {len(result['patterns'])} patterns; {len(result['paths'])} paths", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-date", default="2024-06-24")
    parser.add_argument("--end-date", default="2024-06-30")
    parser.add_argument("--source-date", default="2024-06-24")
    parser.add_argument("--source-url", default=SOURCE_URL)
    args = parser.parse_args()
    prepare(args.archive, args.output, start_date=args.start_date, end_date=args.end_date,
            source_date=args.source_date, source_url=args.source_url)
