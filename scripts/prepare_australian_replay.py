"""Prepare pinned Australian rail GTFS archives using SunTrain's shared patterns.

Only the selected railway operators/types are included; replacement buses and
other modes are not inferred from a rail route name. All geometry is supplied
by the same historical timetable archive, with unresolved paths left empty.
"""
from __future__ import annotations

import argparse
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
from scripts.compact_transit import save_reference
from scripts.prepare_boston_replay import fetch, project_stops
from scripts.prepare_replay_geometry import anchored_shape, clip_path, point_at, simplify
from scripts.prepare_transit_replay import active_services, records as raw_records, seconds

SOURCES = {
    "brisbane": {
        "name": "Brisbane", "first": "2026-10-05", "last": "2026-10-11", "timezone": "Australia/Brisbane",
        "captured": "2026-10-03", "url": "https://files.mobilitydatabase.org/mdb-3048/mdb-3048-202610030017/mdb-3048-202610030017.zip",
        "sha256": "cdc4d9e4a5731cef518a34c519e6ce91d93f8484574d0b37457308def887b940",
        "source": "Translink / Queensland Department of Transport and Main Roads historical GTFS via MobilityDatabase",
        "source_url": "https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink",
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Timetable and railway geometry: Translink, Department of Transport and Main Roads, Queensland Government · archive captured 3 October 2026",
        "note": "Queensland Rail and G:link light rail, using October 2026 route patterns. Brisbane Metro buses, other buses and ferries are excluded. No individual vehicle passenger loads.",
    },
    "perth": {
        "name": "Perth", "first": "2026-10-05", "last": "2026-10-11", "timezone": "Australia/Perth",
        "captured": "2026-10-01", "url": "https://files.mobilitydatabase.org/mdb-1086/mdb-1086-202610010042/mdb-1086-202610010042.zip",
        "sha256": "9f4482331fb37dbd71708ccdd187f092be42ad7f2e3536e798416bf99422b9fa",
        "source": "Public Transport Authority (WA) historical GTFS via MobilityDatabase",
        "source_url": "https://www.transperth.wa.gov.au/About/Spatial-Data-Access",
        "license": "PTA Spatial Data Licence", "license_url": "https://www.transperth.wa.gov.au/About/Spatial-Data-Access",
        "attribution": "Source data is available free of charge from www.transperth.wa.gov.au · Public Transport Authority (WA) · archive captured 1 October 2026",
        "note": "Perth suburban rail uses the October 2026 network, after the Yanchep, Ellenbrook and Thornlie–Cockburn openings. Transwa, buses and ferries are excluded. No individual train passenger loads.",
    },
    "adelaide": {
        "name": "Adelaide", "first": "2024-05-27", "last": "2024-06-30", "timezone": "Australia/Adelaide",
        "captured": "2024-05-24", "url": "https://gtfs.adelaidemetro.com.au/v1/static/1430/google_transit.zip",
        "sha256": "289277fd965f672fe252d685caafb78abc7611c7dfb6324a8df5eef61dc0330f",
        "source": "Adelaide Metro official historical GTFS version 1430",
        "source_url": "https://gtfs.adelaidemetro.com.au/",
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Timetable and railway geometry: Adelaide Metro / Department for Infrastructure and Transport, Government of South Australia · historical GTFS version 1430",
        "note": "Adelaide suburban trains and Torrens Connect trams, using May–June 2024 calendars and planned closures. Port Dock, which opened later, is absent. Buses are excluded. No individual vehicle passenger loads.",
    },
    "sydney": {
        "name": "Sydney", "first": "2026-10-05", "last": "2026-10-11", "timezone": "Australia/Sydney",
        "captured": "2026-10-04", "url": "https://files.mobilitydatabase.org/mdb-2449/mdb-2449-202610040107/mdb-2449-202610040107.zip",
        "sha256": "85adf1e81eaa396ca005a3c6a090ab8b03e8eebb8c1168d9f5d9a5517860fd64",
        "source": "Transport for NSW historical GTFS via MobilityDatabase",
        "source_url": "https://opendata.transport.nsw.gov.au/dataset/timetables-complete-gtfs",
        "license": "Creative Commons Attribution", "license_url": "https://opendata.transport.nsw.gov.au/dataset/timetables-complete-gtfs",
        "attribution": "Timetable and railway geometry: Transport for NSW · archive captured 4 October 2026",
        "note": "Sydney Trains, Sydney Metro, NSW TrainLink intercity BMT/CCN/SCO and Sydney light rail L1–L4, including scheduled special-event variants, use October 2026 calendars. Regional trains/coaches, Newcastle light rail, buses and ferries are excluded. Metro and light-rail timings are indicative in the source. No individual vehicle passenger loads.",
    },
}


def records(archive, filename):
    # Some official feeds, notably PTA shapes, put spaces in CSV field names.
    for row in raw_records(archive, filename):
        yield {key.strip(): value.strip() if isinstance(value, str) else value for key, value in row.items() if key is not None}


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_route(city, route, agencies):
    agency = route.get("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
    if city == "sydney":
        return (agency in {"x0001", "X0000"} and route["route_type"] == "2") or (agency == "SMNW" and route["route_type"] in {"1", "401"}) or (agency in {"LR", "SLR", "PLR"} and route["route_type"] == "900")
    if city == "adelaide":
        return (agency == "2" and route["route_type"] == "2") or (agency == "3" and route["route_type"] == "0")
    if city == "perth":
        return agency == "WES-RAI" and route["route_type"] == "2"
    if city == "brisbane":
        return (agency == "5" and route["route_type"] == "2") or (agency == "32" and route["route_type"] == "0")
    raise ValueError(f"Unsupported city: {city}")


def path_legs(raw, anchors, coordinates, *, recover_native=False):
    """Native distances preserve branches/loops. Default behaviour rejects bad
    anchors; an audited opt-in can recover against the same ordered shape and
    preserve verified native legs where a complete match is unavailable.
    """
    if anchors is not None:
        if any(not math.isfinite(a) for a in anchors) or any(b < a for a, b in zip(anchors, anchors[1:])):
            raise ValueError("Invalid or backwards native stop distances")
        points, indices = anchored_shape(raw, [(a, "") for a in anchors])
        matched = [cumulative_distances([stop, points[i]])[-1] <= 150 for stop, i in zip(coordinates, indices)]
        if not all(matched):
            if not recover_native:
                raise ValueError("Native stop anchor more than 150 m from station")
            # An explicitly audited source may have inaccurate distance anchors.
            # Recover only by matching the complete stop order to its own shape.
            try:
                return path_legs(raw, None, coordinates)
            except ValueError:
                pass
        curves = [points[a:b + 1] if matched[j] and matched[j + 1] else None
                  for j, (a, b) in enumerate(zip(indices, indices[1:]))]
    else:
        points = [p for _, _, p in sorted(raw)]
        positions = project_stops(points, coordinates)
        curves = [simplify(clip_path(points, a, b, point_at(points, a), point_at(points, b))) for a, b in zip(positions, positions[1:])]
    return [None if curve is None else curve if len(curve) >= 2 else [curve[0], curve[0]] for curve in curves]


def prepare(city, cache, output):
    source = SOURCES[city]
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
        agencies = {r["agency_id"]: r for r in records(archive, "agency.txt")}
        routes = {r["route_id"]: r for r in records(archive, "routes.txt") if selected_route(city, r, agencies)}
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
                route = routes[trip["route_id"]]
                mode = "light_rail" if route["route_type"] in {"0", "900"} else "subway" if route["route_type"] in {"1", "401"} else "commuter_rail" if city == "sydney" and route.get("agency_id") == "X0000" else "train"
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
                label = long if long.startswith(short) else f"{short} · {long}" if short else long
                color = route.get("route_color", "").lstrip("#") or "6F818E"
                if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
                    raise ValueError("Invalid route colour")
                pattern = {"mode": mode, "operator": operator,
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
        "sources": [{"source_url": source["url"], "source_date": source["captured"], "sha256": source["sha256"]}],
        "daily_services": counts, "omitted_trips": dict(omissions), "unresolved_geometry_patterns": dict(gaps),
        "unresolved_geometry_trips": gap_trips, "native_anchor_patterns": native_count,
        "note": "Scheduled estimates, not GPS or a reconstruction of every historical disruption. Only services active in source calendars appear. No individual train passenger loads."}
    save_reference(result, output)
    print(f"Saved {output}: {output.stat().st_size} bytes; {len(result['patterns'])} shared patterns; omissions {dict(omissions)}; gaps {dict(gaps)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("city", choices=SOURCES)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    prepare(args.city, args.cache or ROOT / ".cache/australian-cities" / args.city,
            args.output or ROOT / "data/reference" / args.city / (SOURCES[args.city]["first"] + ".json.gz"))
