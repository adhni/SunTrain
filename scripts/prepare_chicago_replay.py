"""Prepare CTA rail for 24 November–28 December 2025 from public historical ZIPs.

The requested May–June 2024 ZIP could not be obtained without archive credentials.
These pinned snapshots are an explicitly labelled fallback, never 2024 schedules.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_boston_replay import fetch
from scripts.prepare_replay_geometry import anchored_shape
from scripts.prepare_transit_replay import active_services, records, seconds

FIRST, LAST = date(2025, 11, 24), date(2025, 12, 28)
ZONE = ZoneInfo("America/Chicago")
SOURCE_URL = "https://mobilitydatabase.org/feeds/gtfs/mdb-389"
LICENSE_URL = "https://www.transitchicago.com/downloads/sch_data/developers_license_agreement.htm"
ARCHIVES = [
    (date(2025, 11, 23), "https://files.mobilitydatabase.org/mdb-389/mdb-389-202511230128/mdb-389-202511230128.zip"),
    (date(2025, 12, 19), "https://files.mobilitydatabase.org/mdb-389/mdb-389-202512190112/mdb-389-202512190112.zip"),
]
RAIL_ROUTES = {"Red", "Blue", "Brn", "G", "Org", "Pink", "P", "Y"}


def service_zero(day):
    return int(datetime.combine(day, time(12), ZONE).timestamp()) - 43200


def shape_legs(raw, anchors, stops, paths):
    """Use native distance anchors for every stop occurrence, including the Loop."""
    if any(not math.isfinite(a) for a in anchors) or any(b < a for a, b in zip(anchors, anchors[1:])):
        raise ValueError("Invalid or backwards stop distances")
    points, indices = anchored_shape(raw, [(a, "") for a in anchors])
    if any(cumulative_distances([stop, points[i]])[-1] > 150 for stop, i in zip(stops, indices)):
        raise ValueError("Native stop anchor more than 150 m from station")
    legs = []
    for a, b in zip(indices, indices[1:]):
        curve = points[a:b + 1]
        if len(curve) == 1:
            curve = [curve[0], curve[0]]
        identifier = "cta-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
        paths[identifier] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "shape"}
        legs.append(identifier)
    return legs


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    service_days = [FIRST - timedelta(days=1), *days, LAST + timedelta(days=1)]
    selected = {d: max((captured, url) for captured, url in ARCHIVES if captured <= d)[1] for d in service_days}
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(d): [] for d in days}}
    station_ids, geometry_cache = {}, {}
    omissions, gaps, sources = Counter(), Counter(), []
    for captured, url in ARCHIVES:
        applicable = [d for d in service_days if selected[d] == url]
        if not applicable:
            continue
        path = fetch(url, cache / url.rsplit("/", 1)[1])
        sources.append({"source_date": str(captured), "source_url": url,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        with ZipFile(path) as archive:
            agency_rows = list(records(archive, "agency.txt"))
            agencies = {r["agency_id"] for r in agency_rows if r["agency_name"] == "Chicago Transit Authority" and r["agency_timezone"] == str(ZONE)}
            default_agency = agency_rows[0]["agency_id"] if len(agency_rows) == 1 else None
            routes = {r["route_id"]: r for r in records(archive, "routes.txt") if r["route_type"] == "1" and (r.get("agency_id") or default_agency) in agencies}
            calendars, exceptions = list(records(archive, "calendar.txt")), list(records(archive, "calendar_dates.txt"))
            active = {d: active_services(calendars, exceptions, d) for d in applicable}
            relevant = set().union(*active.values())
            trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes and r["service_id"] in relevant}
            if any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
                raise ValueError("Frequency-based rail service needs explicit handling")
            stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
            calls = defaultdict(list)
            for row in records(archive, "stop_times.txt"):
                if row["trip_id"] in trips:
                    calls[row["trip_id"]].append(row)
            shapes, invalid_shapes = defaultdict(list), set()
            needed = {t["shape_id"] for t in trips.values()}
            for row in records(archive, "shapes.txt"):
                if row["shape_id"] not in needed:
                    continue
                try:
                    shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]), float(row["shape_dist_traveled"]),
                        [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)]))
                except ValueError:
                    invalid_shapes.add(row["shape_id"])
            for key in invalid_shapes:
                shapes[key] = []
            signatures = {key: hashlib.sha256(json.dumps(raw).encode()).hexdigest() for key, raw in shapes.items()}
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
                    occurrences = []
                    for service_day in applicable:
                        if trip["service_id"] not in active[service_day]:
                            continue
                        departure, finish = service_zero(service_day) + times[0][0], service_zero(service_day) + times[-1][1]
                        for day in days:
                            start = int(datetime.combine(day, time(3), ZONE).timestamp())
                            end = int(datetime.combine(day + timedelta(days=1), time(3), ZONE).timestamp())
                            if departure < end and finish >= start:
                                occurrences.append((str(day), departure - service_zero(day)))
                    if not occurrences:
                        continue
                    ids = []
                    for row, coordinate in zip(sequence, coordinates):
                        stop = stops[row["stop_id"]]
                        key = (stop["stop_id"], stop["stop_name"], *coordinate)
                        if key not in station_ids:
                            station_ids[key] = len(result["stations"])
                            result["stations"].append({"name": stop["stop_name"], "lon": coordinate[0], "lat": coordinate[1], "mode": "train"})
                        ids.append(station_ids[key])
                    geometry_key = (signatures.get(trip["shape_id"]), tuple(r.get("shape_dist_traveled", "") for r in sequence), tuple(map(tuple, coordinates)))
                    if geometry_key not in geometry_cache:
                        try:
                            anchors = [float(r["shape_dist_traveled"]) for r in sequence]
                            legs = shape_legs(shapes.get(trip["shape_id"], []), anchors, coordinates, result["paths"])
                        except ValueError as error:
                            gaps[str(error)] += 1
                            result["paths"]["cta-unresolved"] = {"coordinates": [], "distances": [], "quality": "approximate"}
                            legs = ["cta-unresolved"] * (len(sequence) - 1)
                        geometry_cache[geometry_key] = legs
                    route = routes[trip["route_id"]]
                    direction = trip.get("direction", "")
                    if direction not in {"North", "South", "East", "West"}:
                        direction = {"0": "Direction A", "1": "Direction B"}.get(trip["direction_id"], "")
                    pattern = {"mode": "subway", "operator": "CTA", "line": route["route_long_name"],
                        "route_id": route["route_id"], "color": "#" + route["route_color"], "direction": direction,
                        "origin": stops[sequence[0]["stop_id"]]["stop_name"], "destination": stops[sequence[-1]["stop_id"]]["stop_name"],
                        "stops": [[station, a - times[0][0], b - times[0][0]] for station, (a, b) in zip(ids, times)],
                        "legs": geometry_cache[geometry_key]}
                    identifier = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                    result["patterns"][identifier] = pattern
                    for day, departure in occurrences:
                        result["days"][day].append([identifier, trip_id, departure])
                except (ValueError, KeyError) as error:
                    omissions[str(error)] += 1
        print(f"{path.name}: {len(trips)} candidate rail trips; {len(result['patterns'])} shared patterns", flush=True)
    counts = {}
    for day, rows in result["days"].items():
        if len({(trip, departure) for _, trip, departure in rows}) != len(rows):
            raise ValueError(f"Duplicate trip occurrences on {day}")
        counts[day] = dict(Counter(result["patterns"][p]["route_id"] for p, _, _ in rows))
        if set(counts[day]) != RAIL_ROUTES:
            raise ValueError(f"Incomplete CTA rail coverage on {day}")
        rows.sort(key=lambda r: (r[2], r[1]))
    result["metadata"] = {"start_date": str(FIRST), "end_date": str(LAST), "source": "Chicago Transit Authority historical GTFS via MobilityDatabase",
        "source_url": SOURCE_URL, "license": "CTA Developer License Agreement", "license_url": LICENSE_URL,
        "timezone": str(ZONE), "sources": sources, "daily_services": counts, "omitted_trips": dict(omissions),
        "unresolved_geometry_patterns": dict(gaps), "preferred_period_unavailable": "2024-05-27 through 2024-06-30: no downloadable historical ZIP obtained without archive credentials",
        "note": "Historical CTA rail only. Metra, buses and passenger counts are unavailable. These are 2025 schedules, not 2024."}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    temporary.replace(output)
    print(f"Saved {output}: {output.stat().st_size} bytes; omissions {dict(omissions)}; geometry gaps {dict(gaps)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/chicago-archives")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/chicago/2025-11-24.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
