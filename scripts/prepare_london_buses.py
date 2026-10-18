"""Prepare dated London buses offline with shared schedules and official road paths.

The regional GTFS includes non-TfL buses and other modes. Select only contracts
verified against the official TfL XML operator/line inventory. Never use its
station-to-station sketch shapes or invent exact departures from headways.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_australian_replay import file_hash, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_singapore_replay import match_geometry
from scripts.prepare_transit_replay import active_services, seconds
from scripts.compact_transit import compact_reference

FIRST, LAST = date(2026, 10, 5), date(2026, 10, 11)
ZONE = ZoneInfo("Europe/London")
GTFS_URL = "https://data.datalibrary.uk/transport/BODS-ARCHIVE/timetables/2026/10/05/itm_london_gtfs_20261005.zip"
GTFS_SHA256 = "6e77de9cc3bfd96dc7f50fcbb9063c794eb323419222e48ce0845e35223aa630"
GEOMETRY_URL = "https://s3-eu-west-1.amazonaws.com/bus.data.tfl.gov.uk/bus-geometry/Route_Geometry_20261009.zip"
GEOMETRY_SHA256 = "496e20fb361d385b7e045369d41f8c6d54860537fb80f4418e3ba615759798bd"
REFERENCE = ROOT / "data/reference/london/bus-geometry-2026-10-09.json.gz"
REFERENCE_SHA256 = "dab4ef00c7031c9e3bc4cdbd282b77f97d1e88fe25a98b9b14f2750ceebdb00e"
NATIVE_SHA256 = "83adcb18f62ed4777fb2e5b194de3751f5b4461345756a1cd6578b325ce60f9c"
ALIASES = {"IF": ["ELBG", "LIBC"], "LI": ["LIBC", "ELBG"], "SV": ["LSOV"], "LU": ["LUTD"],
           "UN": ["UNIB"], "BE": ["GAHL"], "DC": ["DLBU", "GAHL"], "FB": ["FB", "FALC"],
           "CX": ["ABLO"], "TE": ["ABLO"], "LO": ["LOTR"], "MN": ["ALNO", "ARVA", "AVLO"],
           "SL": ["ALSO", "AVLO"], "ME": ["METR"], "ML": ["MTLN"], "MT": ["MTLN"],
           "SK": ["ELBG", "LIBC"], "LC": ["GAHL"], "LG": ["GAHL"]}


def save(value, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(value, separators=(",", ":"), allow_nan=False).encode())
    temporary.replace(path)


def compact(reference):
    """Share stop/road sequences across different traffic timing profiles.

    Flat times avoid millions of tiny stop arrays in the browser. No schedule
    is expanded during hydration or copied into individual service records.
    """
    return compact_reference(reference, prefix="lbus-stops-")


def compile_geometry(archive, scope, output):
    if file_hash(archive) != GEOMETRY_SHA256:
        raise ValueError("Bus geometry differs from the audited snapshot")
    routes = {line: sorted({noc for code in codes for noc in ALIASES[code]}) for line, codes in sorted(scope["lines"].items())}
    lines = defaultdict(list)
    with ZipFile(archive) as source:
        for name in source.namelist():
            root = ET.fromstring(source.read(name))
            groups = defaultdict(list)
            for row in root.findall("Route_Geometry"):
                line = row.attrib["aContract_Line_No"].upper()
                if line in routes:
                    groups[(line, row.attrib["aLBSL_Run_No"], row.findtext("Direction"))].append(
                        (int(row.attrib["aSequence_No"]), [float(row.findtext("Location_Longitude")), float(row.findtext("Location_Latitude"))]))
            for (line, run, direction), points in groups.items():
                points.sort()
                if len({i for i, _ in points}) != len(points):
                    raise ValueError("Duplicate bus geometry sequence")
                lines[line].append({"relation": f"{line}:{run}:{direction}", "coordinates": [p for _, p in points]})
    save({"metadata": {"source_url": GEOMETRY_URL, "source_date": "2026-10-09", "sha256": GEOMETRY_SHA256,
          "scope_source": "TfL Journey Planner XML, 15 October 2026; contract scope only, not historical timetable",
          "scope_sha256": "83adcb18f62ed4777fb2e5b194de3751f5b4461345756a1cd6578b325ce60f9c",
          "license_url": "https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service"},
          "operators": routes, "lines": dict(lines)}, output)


def contract_scope(native):
    if file_hash(native) != NATIVE_SHA256:
        raise ValueError("TfL contract inventory differs from the audited snapshot")
    lines = defaultdict(set)
    with ZipFile(native) as outer:
        for name in outer.namelist():
            if not name.startswith("BUSES"):
                continue
            with ZipFile(BytesIO(outer.read(name))) as archive:
                for name in archive.namelist():
                    if not name.endswith(".xml"):
                        continue
                    data = archive.read(name)
                    codes = {c.decode() for c in re.findall(rb"<OperatorCode>(.*?)</OperatorCode>", data)}
                    if len(codes) != 1 or not codes <= ALIASES.keys():
                        raise ValueError("Unrecognised bus contract operator")
                    for line in re.findall(rb"<LineName>(.*?)</LineName>", data):
                        lines[line.decode().upper()].update(codes)
    return {"lines": {line: sorted(codes) for line, codes in lines.items()}}


def selected_route(route, agencies, scope):
    line = route["route_short_name"].upper()
    return route["route_type"] == "3" and agencies[route["agency_id"]]["agency_noc"] in scope.get(line, [])


def resolve_geometry(variants, coordinates):
    try:
        return match_geometry(variants, coordinates)[1]
    except ValueError:
        result = []
        # Keep matched road legs if a short working or diversion misses a run.
        for a, b in zip(coordinates, coordinates[1:]):
            try:
                curve = match_geometry(variants, [a, b])[1][0]
                if cumulative_distances(curve)[-1] > 6 * cumulative_distances([a, b])[-1] + 1000:
                    curve = None
                result.append(curve)
            except ValueError:
                result.append(None)
        return result


def prepare(cache, reference, output):
    if file_hash(reference) != REFERENCE_SHA256:
        raise ValueError("Bus road reference differs from the audited snapshot")
    with gzip.open(reference, "rt") as stream:
        geographic = json.load(stream)
    filename = fetch(GTFS_URL, cache / "itm_london_gtfs_20261005.zip")
    if file_hash(filename) != GTFS_SHA256:
        raise ValueError("Bus GTFS differs from the audited snapshot")
    days = [FIRST + timedelta(days=i) for i in range(7)]
    service_days = [FIRST - timedelta(days=1), *days, LAST + timedelta(days=1)]
    windows = [(str(day), int(datetime.combine(day, time(3), ZONE).timestamp()),
                int(datetime.combine(day + timedelta(days=1), time(3), ZONE).timestamp())) for day in days]
    zero = lambda day: int(datetime.combine(day, time(12), ZONE).timestamp()) - 43200
    zeros = {day: zero(day) for day in service_days}
    window_zeros = {business: zero(date.fromisoformat(business)) for business, _, _ in windows}
    stations, station_ids, paths, patterns, geometry_cache = [], {}, {}, {}, {}
    occurrences, dedup = {str(d): [] for d in days}, {str(d): set() for d in days}
    omitted, duplicates = Counter(), Counter()
    with ZipFile(filename) as archive:
        feed = next(records(archive, "feed_info.txt"))
        if not (feed["feed_start_date"] <= service_days[0].strftime("%Y%m%d") and feed["feed_end_date"] >= service_days[-1].strftime("%Y%m%d")):
            raise ValueError("Bus feed does not cover the replay week")
        agencies = {a["agency_id"]: a for a in records(archive, "agency.txt")}
        routes = {r["route_id"]: r for r in records(archive, "routes.txt") if selected_route(r, agencies, geographic["operators"])}
        calendars, exceptions = list(records(archive, "calendar.txt")), list(records(archive, "calendar_dates.txt"))
        active = {d: active_services(calendars, exceptions, d) for d in service_days}
        relevant = set().union(*active.values())
        frequency_ids = {r["trip_id"] for r in records(archive, "frequencies.txt")}
        trips = {}
        for trip in records(archive, "trips.txt"):
            if trip["route_id"] in routes and trip["service_id"] in relevant:
                if trip["trip_id"] in frequency_ids:
                    omitted["Non-exact frequency service"] += 1
                else:
                    trips[trip["trip_id"]] = trip
        stops = {s["stop_id"]: s for s in records(archive, "stops.txt")}
        print(f"London buses: {len(routes)} route records, {len(trips)} active trip templates", flush=True)
        seen = set()
        # BODS groups calls by trip. Stream one journey at a time, never holding
        # the 1.48 GB stop_times table or millions of per-trip dictionaries.
        for trip_id, group in itertools.groupby(records(archive, "stop_times.txt"), lambda r: r["trip_id"]):
            if trip_id not in trips:
                continue
            if trip_id in seen:
                raise ValueError("Bus stop_times are not grouped by trip; audit ordering before preparation")
            seen.add(trip_id)
            if len(seen) % 25000 == 0:
                print(f"Processed {len(seen):,} bus templates; {len(geometry_cache):,} road patterns", flush=True)
            sequence = sorted(group, key=lambda r: int(r["stop_sequence"]))
            trip = trips[trip_id]
            try:
                if len(sequence) < 2:
                    raise ValueError("Fewer than two stops")
                times = [(seconds(r["arrival_time"]), seconds(r["departure_time"])) for r in sequence]
                flat = [v for pair in times for v in pair]
                if any(b < a for a, b in zip(flat, flat[1:])):
                    raise ValueError("Backwards or missing bus times")
                instances = [(business, zeros[d] + times[0][0] - window_zeros[business])
                             for d in service_days if trip["service_id"] in active[d]
                             for business, start, end in windows
                             if zeros[d] + times[0][0] < end and zeros[d] + times[-1][1] >= start]
                if not instances:
                    continue
                route = routes[trip["route_id"]]
                line = route["route_short_name"].upper()
                coordinates = [[float(stops[r["stop_id"]]["stop_lon"]), float(stops[r["stop_id"]]["stop_lat"])] for r in sequence]
                if not all(math.isfinite(v) and abs(v) <= 180 for p in coordinates for v in p):
                    raise ValueError("Invalid bus stop coordinates")
                stop_keys = tuple(r["stop_id"] for r in sequence)
                geo_key = (line, stop_keys)
                if geo_key not in geometry_cache:
                    curves = resolve_geometry(geographic["lines"].get(line, []), coordinates)
                    legs = []
                    for curve in curves:
                        key = "lbus-" + (hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20] if curve else "unresolved")
                        paths[key] = {"coordinates": curve or [], "distances": cumulative_distances(curve or []), "quality": "shape" if curve else "approximate"}
                        legs.append(key)
                    geometry_cache[geo_key] = legs
                ids = []
                for row, point in zip(sequence, coordinates):
                    key = (row["stop_id"], *point)
                    if key not in station_ids:
                        station_ids[key] = len(stations)
                        stations.append({"name": stops[row["stop_id"]]["stop_name"], "lon": point[0], "lat": point[1], "mode": "bus"})
                    ids.append(station_ids[key])
                operator = agencies[route["agency_id"]]["agency_name"]
                pattern = {"mode": "bus", "operator": operator, "line": f"Bus {line}", "route_id": line,
                    "color": "#DC241F", "direction": "Direction " + {"0": "A", "1": "B"}.get(trip.get("direction_id"), "unknown"),
                    "origin": stops[sequence[0]["stop_id"]]["stop_name"],
                    "destination": trip.get("trip_headsign") or stops[sequence[-1]["stop_id"]]["stop_name"],
                    "stops": [[identifier, a - times[0][0], b - times[0][0]] for identifier, (a, b) in zip(ids, times)],
                    "legs": geometry_cache[geo_key]}
                identifier = "lbus-" + hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
                patterns[identifier] = pattern
                # Different input agency IDs can repeat one physical timetable.
                identity = hashlib.sha256(json.dumps([line, stop_keys, pattern["stops"]]).encode()).hexdigest()
                for business, departure in instances:
                    key = (identity, departure)
                    if key in dedup[business]:
                        duplicates[business] += 1
                    else:
                        dedup[business].add(key)
                        occurrences[business].append([identifier, trip_id, departure])
            except (ValueError, KeyError, TypeError) as error:
                omitted[str(error)] += 1
        omitted["Missing stop_times"] += len(trips.keys() - seen)
    metadata = {"start_date": str(FIRST), "end_date": str(LAST), "timezone": "Europe/London",
        "source": "BODS London GTFS, archived 5 October 2026 by Open Innovations / National Data Library",
        "source_url": GTFS_URL, "sha256": GTFS_SHA256, "feed_version": feed["feed_version"],
        "license": "Open Government Licence v3.0", "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "attribution": "Bus timetables: Bus Open Data Service / DfT, via Open Innovations / National Data Library. Contains public sector information licensed under OGL v3.0. Bus route geometry: Powered by TfL Open Data.",
        "geometry_source_url": GEOMETRY_URL, "geometry_sha256": GEOMETRY_SHA256, "geometry_reference_sha256": REFERENCE_SHA256,
        "omitted_trips": {k: v for k, v in omitted.items() if v}, "deduplicated_occurrences": dict(duplicates),
        "note": "TfL contract buses only. Estimated positions follow official 9 October road geometry; unresolved legs stay as gaps. No passenger loads. Unavailable route labels 246 and 653 are not reconstructed."}
    for business, rows in occurrences.items():
        if not rows:
            raise ValueError(f"No bus services on {business}")
        selected = {p for p, _, _ in rows}
        used_stations = sorted({s[0] for p in selected for s in patterns[p]["stops"]})
        remap = {s: i for i, s in enumerate(used_stations)}
        daily_patterns = {p: {**patterns[p], "stops": [[remap[s], a, b] for s, a, b in patterns[p]["stops"]]} for p in sorted(selected)}
        used_paths = {leg for p in selected for leg in patterns[p]["legs"]}
        result = {"metadata": metadata, "stations": [stations[s] for s in used_stations], "patterns": daily_patterns,
                  "paths": {p: paths[p] for p in sorted(used_paths)}, "days": {business: sorted(rows, key=lambda r: (r[2], r[1]))}}
        save(compact(result), output / (business + ".json.gz"))
        print(business, len(rows), "services", len(selected), "shared patterns", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/london-audit")
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/london/bus")
    parser.add_argument("--compile-geometry", type=Path, metavar="TFL_NATIVE_ZIP", help="Rebuild the pinned road reference and contract scope first")
    args = parser.parse_args()
    if args.compile_geometry:
        archive = fetch(GEOMETRY_URL, args.cache / "bus-geometry-20261009.zip")
        compile_geometry(archive, contract_scope(args.compile_geometry), args.reference)
    prepare(args.cache, args.reference, args.output)
