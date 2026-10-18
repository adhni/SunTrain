"""Prepare pinned rail GTFS snapshots as shared replay schedules and paths.

Source selection and railway scope are explicit in each city wrapper. Invalid
geometry stays empty; no other route or straight connector is substituted.
"""
from __future__ import annotations

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
from scripts.compact_transit import compact_reference, daily_reference, save_reference
from scripts.prepare_australian_replay import file_hash, path_legs, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_transit_replay import active_services, seconds


def source_for(day, archives):
    matches = [source for source in archives if source["start"] <= str(day) <= source["end"]]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one applicable rail archive for {day}")
    return matches[0]


def prepare(city, source, cache, output, selected_route, describe_route, geometry_resolver=None, *, daily=False, select_sequence=None):
    if source.get("geometry_method", "native_or_projected") not in {"native_or_projected", "ordered_projection", "native_or_ordered_per_leg"}:
        raise ValueError("Unsupported railway geometry method")
    first, last = date.fromisoformat(source["first"]), date.fromisoformat(source["last"])
    zone = ZoneInfo(source["timezone"])
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    service_days = [first - timedelta(days=1), *days, last + timedelta(days=1)]
    zero = lambda day: int(datetime.combine(day, time(12), zone).timestamp()) - 43200
    windows = [(str(d), int(datetime.combine(d, time(3), zone).timestamp()), int(datetime.combine(d + timedelta(days=1), time(3), zone).timestamp()), zero(d)) for d in days]
    cache.mkdir(parents=True, exist_ok=True)
    archives = source.get("archives", [{**source, "start": str(service_days[0]), "end": str(service_days[-1])}])
    selected = {day: source_for(day, archives) for day in service_days}
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(d): [] for d in days}}
    station_ids, geometry_cache = {}, {}
    omissions, gaps, gap_trips, native_count = Counter(), Counter(), {}, 0
    sources = []
    for snapshot in archives:
        applicable = [day for day in service_days if selected[day] is snapshot]
        if not applicable:
            continue
        filename = fetch(snapshot["url"], cache / snapshot["url"].rsplit("/", 1)[1])
        if file_hash(filename) != snapshot["sha256"]:
            raise ValueError("Archive differs from the validated source; inspect it before changing the pin")
        with ZipFile(filename) as archive:
            feed = next(records(archive, "feed_info.txt")) if "feed_info.txt" in archive.namelist() else {}
            dated_feed = bool(feed.get("feed_start_date") and feed.get("feed_end_date"))
            if not dated_feed and not source.get("calendar_validity"):
                raise ValueError("Feed validity is missing")
            if dated_feed and not (feed["feed_start_date"] <= min(applicable).strftime("%Y%m%d")
                    and max(applicable).strftime("%Y%m%d") <= feed["feed_end_date"]):
                raise ValueError("Feed validity does not cover the selected service days")
            sources.append({"source_url": snapshot["url"], "source_date": snapshot["captured"], "published": snapshot["published"],
                            "feed_version": feed.get("feed_version", ""), "valid_from": feed.get("feed_start_date", ""),
                            "valid_through": feed.get("feed_end_date", ""), "sha256": snapshot["sha256"]})
            agencies = {r["agency_id"]: r for r in records(archive, "agency.txt")}
            routes = {r["route_id"]: r for r in records(archive, "routes.txt") if selected_route(r, agencies)}
            if not routes:
                raise ValueError("No selected rail routes")
            calendars = list(records(archive, "calendar.txt")) if "calendar.txt" in archive.namelist() else []
            exceptions = list(records(archive, "calendar_dates.txt")) if "calendar_dates.txt" in archive.namelist() else []
            active = {d: active_services(calendars, exceptions, d) for d in applicable}
            if source.get("calendar_validity") and any(not services for services in active.values()):
                raise ValueError("Source calendars do not cover every selected service day")
            relevant = set().union(*active.values())
            trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes and r["service_id"] in relevant}
            if "frequencies.txt" in archive.namelist() and any(r["trip_id"] in trips for r in records(archive, "frequencies.txt")):
                raise ValueError("Frequency-based rail service needs explicit handling")
            directions = {(r["route_id"], r["direction_id"]): r["direction"] for r in records(archive, "directions.txt")} if "directions.txt" in archive.namelist() else {}
            direction_names = defaultdict(set)
            for (route_id, _), label in directions.items():
                direction_names[route_id].add(label)
            # Some BART trip direction bits disagree with their direction-specific
            # route. Its single published direction still identifies that route.
            route_directions = {route_id: next(iter(labels)) for route_id, labels in direction_names.items() if len(labels) == 1}
            stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
            calls = defaultdict(list)
            for row in records(archive, "stop_times.txt"):
                if row["trip_id"] in trips:
                    calls[row["trip_id"]].append(row)
            shapes = defaultdict(list)
            needed = {t.get("shape_id", "") for t in trips.values()}
            for row in records(archive, "shapes.txt") if "shapes.txt" in archive.namelist() else ():
                if row["shape_id"] in needed:
                    shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                        float(row["shape_dist_traveled"]) if row.get("shape_dist_traveled") else None,
                        [round(float(row["shape_pt_lon"]), 6), round(float(row["shape_pt_lat"]), 6)]))
            signatures = {key: hashlib.sha256(json.dumps(raw).encode()).hexdigest() for key, raw in shapes.items()}
            print(f"{city}: {len(routes)} route variants, {len(trips)} candidate trips, {len(shapes)} supplied shapes", flush=True)
            for trip_id, trip in trips.items():
                sequence = sorted(calls[trip_id], key=lambda r: int(r["stop_sequence"]))
                if select_sequence is not None:
                    sequence = select_sequence(sequence, stops)
                    if not sequence:
                        continue
                try:
                    route = routes[trip["route_id"]]
                    description = describe_route(route, trip)
                    if len(sequence) < 2:
                        raise ValueError("Fewer than two stops")
                    coordinates = [[float(stops[r["stop_id"]]["stop_lon"]), float(stops[r["stop_id"]]["stop_lat"])] for r in sequence]
                    if not all(math.isfinite(value) for point in coordinates for value in point):
                        raise ValueError("Invalid station coordinates")
                    times = [(seconds(r["arrival_time"]), seconds(r["departure_time"])) for r in sequence]
                    flat = [v for pair in times for v in pair]
                    if any(b < a for a, b in zip(flat, flat[1:])):
                        raise ValueError("Backwards times")
                    assign_to_start = description.get("mode") in source.get("assign_by_start", [])
                    instances = []
                    for day in applicable:
                        if trip["service_id"] not in active[day]:
                            continue
                        departure, finish = zero(day) + times[0][0], zero(day) + times[-1][1]
                        for business_date, start, end, midnight in windows:
                            matches_window = start <= departure < end if assign_to_start else departure < end and finish >= start
                            if matches_window:
                                instances.append((business_date, departure - midnight))
                    if not instances:
                        continue
                    ids = []
                    station_mode = description.get("mode") if description.get("mode") in {"bus", "tram", "ferry"} else "train"
                    for row, coordinate in zip(sequence, coordinates):
                        stop = stops[row["stop_id"]]
                        key = (stop["stop_id"], stop["stop_name"], *coordinate, station_mode)
                        if key not in station_ids:
                            station_ids[key] = len(result["stations"])
                            result["stations"].append({"name": stop["stop_name"], "lon": coordinate[0], "lat": coordinate[1], "mode": station_mode})
                        ids.append(station_ids[key])
                    raw = shapes.get(trip.get("shape_id", ""), [])
                    route = routes[trip["route_id"]]
                    anchored = source.get("geometry_method") != "ordered_projection" and bool(raw) and all(
                        r.get("shape_dist_traveled", "") != "" for r in sequence) and all(a is not None for _, a, _ in raw)
                    anchors = [float(r["shape_dist_traveled"]) for r in sequence] if anchored else None
                    geometry_key = (trip["route_id"] if geometry_resolver else None, signatures.get(trip.get("shape_id", "")),
                                    tuple(anchors) if anchors is not None else None, tuple(map(tuple, coordinates)))
                    if geometry_key not in geometry_cache:
                        try:
                            curves = geometry_resolver(route, trip, sequence, coordinates) if geometry_resolver else NotImplemented
                            external = curves is not NotImplemented
                            # Mixed sources can retain their own GTFS shapes and
                            # use external geometry only for audited operators.
                            if not external:
                                curves = path_legs(raw, anchors, coordinates,
                                    recover_native=source.get("geometry_method") == "native_or_ordered_per_leg")
                            if external and (len(curves) != len(coordinates) - 1 or any(
                                    curve is not None and (len(curve) < 2 or not all(math.isfinite(value) for point in curve for value in point)
                                    or cumulative_distances([coordinates[i], curve[0]])[-1] > 150
                                    or cumulative_distances([coordinates[i + 1], curve[-1]])[-1] > 150)
                                    for i, curve in enumerate(curves))):
                                raise ValueError("External railway geometry does not match the ordered stops within 150 m")
                            legs = []
                            if any(curve is None for curve in curves):
                                gaps["One or more railway legs lack a connected path within 150 m"] += 1
                            for curve in curves:
                                if curve is None:
                                    key = city + "-unresolved"
                                    result["paths"][key] = {"coordinates": [], "distances": [], "quality": "approximate"}
                                    legs.append(key)
                                    continue
                                key = city + "-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
                                result["paths"][key] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": source.get("geometry_quality", "shape")}
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
                    agency = route.get("agency_id") or next(iter(agencies))
                    operator = agencies[agency]["agency_name"]
                    if agencies[agency]["agency_timezone"] != source["timezone"]:
                        raise ValueError("Unexpected rail operator timezone")
                    color = (description.get("color") or route.get("route_color", "")).lstrip("#") or "6F818E"
                    if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
                        raise ValueError("Invalid route colour")
                    pattern = {**description, "operator": description.get("operator", operator),
                        "source_route_id": trip["route_id"], "color": "#" + color,
                        "direction": description.get("direction") or directions.get((trip["route_id"], trip.get("direction_id"))) or route_directions.get(trip["route_id"]) or
                            "Direction " + {"0": "A", "1": "B"}.get(trip.get("direction_id"), "unknown"),
                        "origin": stops[sequence[0]["stop_id"]]["stop_name"], "destination": description.get("destination") or trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
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
        "sources": sources,
        "daily_services": counts, "omitted_trips": dict(omissions), "unresolved_geometry_patterns": dict(gaps),
        "unresolved_geometry_trips": gap_trips, "native_anchor_patterns": native_count,
        "note": "Scheduled estimates, not GPS or a reconstruction of every historical disruption. Only services active in source calendars appear. No individual vehicle passenger loads."}
    for key in ("geometry_source", "geometry_source_url", "geometry_license", "geometry_license_url", "geometry_source_date", "geometry_sha256", "geometry_method", "geometry_references"):
        if key in source:
            result["metadata"][key] = source[key]
    if daily:
        compact_reference(result)
        for day in result["days"]:
            save_reference(daily_reference(result, day), output / (day + ".json.gz"))
    else:
        save_reference(result, output)
    print(f"Saved {output}: {len(result['patterns'])} shared patterns; omissions {dict(omissions)}; gaps {dict(gaps)}", flush=True)

