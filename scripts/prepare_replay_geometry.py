"""Prepare small, local rail paths from a pinned official Victorian GTFS archive.

Usage: .venv/bin/python scripts/prepare_replay_geometry.py /tmp/gtfs.zip --source-date 2026-10-15
The archive supplies geography only. Historical services and times stay in the warehouse.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from datetime import timedelta
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb
import numpy as np

from dashboard.data import _dataset_path
from dashboard.replay import GEOMETRY_PATH, cumulative_distances, pattern_key


def station_name(name):
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\s+(railway\s+)?station$", "", name.lower()))


def records(archive, name):
    with archive.open(name) as content:
        yield from csv.DictReader(io.TextIOWrapper(content, encoding="utf-8-sig"))


def simplify(points, tolerance=0.000065):
    """Douglas–Peucker, approximately 6 m tolerance at Victoria's latitudes."""
    points = np.asarray(points)
    if len(points) < 3:
        return points.tolist()
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        vector = points[end] - points[start]
        length = float(np.dot(vector, vector))
        middle = points[start + 1:end]
        t = np.clip(((middle - points[start]) @ vector) / length, 0, 1) if length else np.zeros(len(middle))
        distances = np.sum((middle - (points[start] + t[:, None] * vector)) ** 2, axis=1)
        index = int(np.argmax(distances))
        if distances[index] > tolerance ** 2:
            index += start + 1
            keep.add(index)
            stack.extend([(start, index), (index, end)])
    return points[sorted(keep)].tolist()


def load_variants(filename):
    variants = []
    with ZipFile(filename) as outer:
        for branch, operator in (("1", "VLine"), ("2", "Metro")):
            with ZipFile(io.BytesIO(outer.read(f"{branch}/google_transit.zip"))) as archive:
                routes = {r["route_id"]: r for r in records(archive, "routes.txt")
                          if int(r["route_type"]) in (1, 2) or 100 <= int(r["route_type"]) < 200
                          or 400 <= int(r["route_type"]) < 500}
                trips = {r["trip_id"]: r["shape_id"] for r in records(archive, "trips.txt")
                         if r["route_id"] in routes and r["shape_id"]}
                shape_routes = defaultdict(set)
                for r in records(archive, "trips.txt"):
                    if r["trip_id"] in trips:
                        shape_routes[r["shape_id"]].add(routes[r["route_id"]]["route_long_name"])
                stops = {r["stop_id"]: station_name(r["stop_name"]) for r in records(archive, "stops.txt")
                         if r.get("platform_code", "") != "R-Bus"}
                positions = defaultdict(set)
                for r in records(archive, "stop_times.txt"):
                    shape = trips.get(r["trip_id"])
                    if shape and r["stop_id"] in stops and r.get("shape_dist_traveled"):
                        positions[shape].add((float(r["shape_dist_traveled"]), stops[r["stop_id"]]))
                points = defaultdict(list)
                for r in records(archive, "shapes.txt"):
                    if r["shape_id"] in positions:
                        points[r["shape_id"]].append((int(r["shape_pt_sequence"]),
                                                     [round(float(r["shape_pt_lon"]), 6), round(float(r["shape_pt_lat"]), 6)]))
                seen = set()
                for shape, shape_points in points.items():
                    names = []
                    for _, name in sorted(positions[shape]):
                        if not names or names[-1] != name:
                            names.append(name)
                    coordinates = simplify([p for _, p in sorted(shape_points)])
                    signature = hashlib.sha256(json.dumps([names, coordinates]).encode()).hexdigest()
                    if len(names) > 1 and signature not in seen:
                        seen.add(signature)
                        variants.append({"names": names, "points": coordinates, "operator": operator,
                                         "routes": " ".join(sorted(shape_routes[shape])).lower()})
                print(f"{operator}: {len(points)} railway shapes; {len(seen)} distinct paths", flush=True)
    return variants


def ordered_indices(needles, haystack):
    indices, start = [], 0
    for name in needles:
        try:
            found = haystack.index(name, start)
        except ValueError:
            return None
        indices.append(found)
        start = found + 1
    return indices


def project(point, coordinates):
    """Nearest segment and fraction, with longitude scaled at Victorian latitudes."""
    points = np.asarray(coordinates)
    scale = np.array([math.cos(math.radians(point[1])), 1.0])
    starts = points[:-1] * scale
    vectors = (points[1:] - points[:-1]) * scale
    lengths = np.sum(vectors ** 2, axis=1)
    fraction = np.clip(np.sum((np.array(point) * scale - starts) * vectors, axis=1) / np.maximum(lengths, 1e-20), 0, 1)
    distance = np.sum((starts + vectors * fraction[:, None] - np.array(point) * scale) ** 2, axis=1)
    index = int(np.argmin(distance))
    return index + float(fraction[index]), math.sqrt(float(distance[index])) * 111_195


def clip_path(points, start, end, a, b):
    if start > end:
        return clip_path(list(reversed(points)), len(points) - 1 - start, len(points) - 1 - end, a, b)
    def at(position):
        index = min(int(position), len(points) - 2)
        fraction = position - index
        return [round(points[index][axis] + fraction * (points[index + 1][axis] - points[index][axis]), 6) for axis in (0, 1)]
    result = [a, at(start), *points[int(start) + 1:math.ceil(end)], at(end), b]
    return [p for i, p in enumerate(result) if i == 0 or p != result[i - 1]]


def build_geometry(variants, patterns):
    index = defaultdict(set)
    for i, variant in enumerate(variants):
        for name in variant["names"]:
            index[name].add(i)
    projection_cache, pair_cache, paths, mappings = {}, {}, {}, {}
    def projection(i, point):
        key = (i, tuple(point))
        if key not in projection_cache:
            projection_cache[key] = project(point, variants[i]["points"])
        return projection_cache[key]

    def pick_path(a_name, b_name, a, b, candidates):
        candidates = tuple(sorted(candidates))
        key = (a_name, b_name, tuple(a), tuple(b), candidates)
        if key in pair_cache:
            return pair_cache[key]
        choices = []
        for i in candidates:
            start, da = projection(i, a)
            end, db = projection(i, b)
            if da > 500 or db > 500 or abs(start - end) < 0.001:
                continue
            points = clip_path(variants[i]["points"], start, end, a, b)
            length = cumulative_distances(points)[-1]
            direct = cumulative_distances([a, b])[-1]
            if length > max(direct * 5, direct + 10_000):
                continue
            choices.append((length, points))
        choices.sort(key=lambda item: item[0])
        # Distinct alternatives cannot be established from sparse historical stops.
        ambiguous = choices and any(length > choices[0][0] * 1.3 + 500 for length, _ in choices[1:])
        points = choices[0][1] if choices and not ambiguous else [a, b]
        quality = "track" if choices and not ambiguous else "approximate"
        identifier = hashlib.sha256(json.dumps([quality, points]).encode()).hexdigest()[:20]
        paths[identifier] = {"coordinates": points, "quality": quality}
        pair_cache[key] = identifier
        return identifier

    for n, (operator, line, names, coordinates) in enumerate(patterns):
        normalized = [station_name(name) for name in names]
        full = set.intersection(*(index[name] for name in normalized)) if normalized else set()
        full = {i for i in full if variants[i]["operator"] == operator and
                (ordered_indices(normalized, variants[i]["names"]) is not None or
                 ordered_indices(normalized, list(reversed(variants[i]["names"]))) is not None)}
        matching_line = {i for i in full if station_name(line) in station_name(variants[i]["routes"])}
        if matching_line:
            full = matching_line
        legs = []
        for j, (a, b) in enumerate(zip(coordinates, coordinates[1:])):
            candidates = full or (index[normalized[j]] & index[normalized[j + 1]])
            legs.append(pick_path(normalized[j], normalized[j + 1], a, b, candidates))
        mappings[pattern_key(operator, line, names)] = legs
        if n % 200 == 0:
            print(f"Matched {n + 1}/{len(patterns)} historical stop patterns", flush=True)
    return mappings, paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source-date", required=True)
    parser.add_argument("--output", type=Path, default=GEOMETRY_PATH)
    args = parser.parse_args()
    archive_checksum = _checksum(args.archive)
    cache = Path(__file__).resolve().parents[1] / ".cache" / f"rail-variants-{archive_checksum[:16]}.json"
    if cache.exists():
        variants = json.loads(cache.read_text())
    else:
        variants = load_variants(args.archive)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(variants, separators=(",", ":")))
    con = duckdb.connect()
    try:
        # A nested coordinate list per service consumes considerably more memory
        # than the station sequence. Fetch station locations separately.
        con.execute("SET threads=2")
        coordinates = {name: [round(lon, 6), round(lat, 6)] for name, lon, lat in con.execute("""
            SELECT Station_Name, AVG(Station_Longitude), AVG(Station_Latitude)
            FROM read_parquet(?) GROUP BY Station_Name
        """, [_dataset_path()]).fetchall()}
        start, end = con.execute("SELECT MIN(Business_Date), MAX(Business_Date) FROM read_parquet(?)", [_dataset_path()]).fetchone()
        unique = {}
        current = start
        while current is not None and current <= end:
            sequences = con.execute("""
                SELECT Mode, Line_Name, LIST(Station_Name ORDER BY Stop_Sequence_Number) AS station_names
                FROM read_parquet(?) WHERE Business_Date = ?
                GROUP BY Mode, Line_Name, Direction, Train_Number
            """, [_dataset_path(), current]).fetchall()
            for operator, line, names in sequences:
                unique[(operator, line, tuple(names))] = (operator, line, names, [coordinates[name] for name in names])
            if current.day == 1:
                print(f"Scanned through {current}; {len(unique)} distinct stop patterns", flush=True)
            current += timedelta(days=1)
        patterns = list(unique.values())
    finally:
        con.close()
    mappings, paths = build_geometry(variants, patterns)
    metadata = {"source": "Transport Victoria GTFS Schedule", "source_date": args.source_date,
                "source_url": "https://opendata.transport.vic.gov.au/dataset/gtfs-schedule",
                "download_url": "https://data.ptv.vic.gov.au/downloads/gtfs.zip",
                "archive_sha256": archive_checksum,
                "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "note": "Geographic reference only; historical timetable and passenger data are unchanged."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"metadata": metadata, "patterns": mappings, "paths": paths}, separators=(",", ":")))
    print(f"Saved {len(paths)} paths ({sum(p['quality'] == 'track' for p in paths.values())} track) to {args.output}")


def _checksum(path):
    checksum = hashlib.sha256()
    with path.open("rb") as content:
        for chunk in iter(lambda: content.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


if __name__ == "__main__":
    main()
