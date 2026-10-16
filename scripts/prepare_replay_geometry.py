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
from bisect import bisect_right
import heapq
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb
import numpy as np

from dashboard.data import _dataset_path
from dashboard.replay import GEOMETRY_PATH, cumulative_distances, pattern_key


def station_name(name):
    normalized = re.sub(r"[^a-z0-9]", "", re.sub(r"\s+(railway\s+)?station$", "", name.lower()))
    return {"jolimontmcg": "jolimont"}.get(normalized, normalized)


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


def anchored_shape(raw, stops):
    """Keep each stop occurrence anchored to its GTFS distance, including on loops."""
    raw = sorted(raw)
    distances = [row[1] for row in raw]
    points = [row[2] for row in raw]
    if len(points) < 2 or any(b < a for a, b in zip(distances, distances[1:])):
        raise ValueError("Invalid shape distances")
    positions = []
    for distance, _ in stops:
        if distance < distances[0] - 1 or distance > distances[-1] + 1:
            raise ValueError("Stop outside shape distances")
        i = min(max(0, bisect_right(distances, distance) - 1), len(points) - 2)
        length = distances[i + 1] - distances[i]
        positions.append(i + (min(1, max(0, (distance - distances[i]) / length)) if length else 0))
    output, indices = [point_at(points, positions[0])], [0]
    for start, end in zip(positions, positions[1:]):
        section = simplify(clip_path(points, start, end, point_at(points, start), point_at(points, end)))
        output.extend(section[1:])
        indices.append(len(output) - 1)
    return output, indices


def load_variants(filename):
    variants = []
    with ZipFile(filename) as outer:
        for branch, operator in (("1", "VLine"), ("2", "Metro")):
            with ZipFile(io.BytesIO(outer.read(f"{branch}/google_transit.zip"))) as archive:
                routes = {r["route_id"]: r for r in records(archive, "routes.txt")
                          if int(r["route_type"]) in (1, 2) or 100 <= int(r["route_type"]) < 200
                          or 400 <= int(r["route_type"]) < 500}
                trips = {r["trip_id"]: (r["shape_id"], r["route_id"]) for r in records(archive, "trips.txt")
                         if r["route_id"] in routes and r["shape_id"]}
                stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
                trip_stops, rejected = defaultdict(list), set()
                for r in records(archive, "stop_times.txt"):
                    trip = r["trip_id"]
                    if trip not in trips:
                        continue
                    stop = stops.get(r["stop_id"])
                    if stop is None or not r.get("shape_dist_traveled") or \
                            "replacement" in stop["stop_name"].lower() or stop.get("platform_code", "").lower() in ("r-bus", "replacement bus"):
                        rejected.add(trip)
                        continue
                    trip_stops[trip].append((int(r["stop_sequence"]), float(r["shape_dist_traveled"]), station_name(stop["stop_name"])))
                positions, shape_routes = defaultdict(set), defaultdict(set)
                for trip, sequence in trip_stops.items():
                    if trip in rejected:
                        continue
                    ordered = sorted(sequence)
                    if any(b[1] < a[1] for a, b in zip(ordered, ordered[1:])):
                        continue
                    shape, route = trips[trip]
                    positions[shape].update((distance, name) for _, distance, name in ordered)
                    shape_routes[shape].add(routes[route]["route_long_name"])
                points = defaultdict(list)
                for r in records(archive, "shapes.txt"):
                    if r["shape_id"] in positions:
                        points[r["shape_id"]].append((int(r["shape_pt_sequence"]), float(r["shape_dist_traveled"]),
                                                     [round(float(r["shape_pt_lon"]), 6), round(float(r["shape_pt_lat"]), 6)]))
                seen = set()
                for shape, raw in points.items():
                    occurrences = []
                    for distance, name in sorted(positions[shape]):
                        if not occurrences or occurrences[-1][1] != name:
                            occurrences.append((distance, name))
                    if len(occurrences) < 2:
                        continue
                    coordinates, indices = anchored_shape(raw, occurrences)
                    names = [name for _, name in occurrences]
                    signature = hashlib.sha256(json.dumps([names, coordinates, indices]).encode()).hexdigest()
                    if signature not in seen:
                        seen.add(signature)
                        variants.append({"names": names, "points": coordinates, "stop_indices": indices,
                                         "operator": operator, "routes": " ".join(sorted(shape_routes[shape])).lower()})
                print(f"{operator}: {len(points)} rail shapes; {len(seen)} distinct paths; {len(rejected)} replacement/invalid trips excluded", flush=True)
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


def point_at(points, position):
    index = min(int(position), len(points) - 2)
    fraction = position - index
    return [round(points[index][axis] + fraction * (points[index + 1][axis] - points[index][axis]), 6) for axis in (0, 1)]


def clip_path(points, start, end, a, b):
    if start > end:
        return clip_path(list(reversed(points)), len(points) - 1 - start, len(points) - 1 - end, a, b)
    result = [a, point_at(points, start), *points[int(start) + 1:math.ceil(end)], point_at(points, end), b]
    return [p for i, p in enumerate(result) if i == 0 or p != result[i - 1]]


def passes_stations(points, stations, tolerance=80):
    """Reject shapes that physically pass recorded stops out of journey order."""
    if not stations:
        return False
    curve = np.asarray(points)
    candidates = np.asarray(stations)
    nearby = candidates[(candidates[:, 0] >= curve[:, 0].min() - 0.001) &
                        (candidates[:, 0] <= curve[:, 0].max() + 0.001) &
                        (candidates[:, 1] >= curve[:, 1].min() - 0.001) &
                        (candidates[:, 1] <= curve[:, 1].max() + 0.001)]
    if not len(nearby):
        return False
    scale = np.array([math.cos(math.radians(float(curve[:, 1].mean()))), 1.0])
    starts, vectors = curve[:-1] * scale, (curve[1:] - curve[:-1]) * scale
    offset = nearby[:, None, :] * scale - starts
    fractions = np.clip(np.sum(offset * vectors, axis=2) / np.maximum(np.sum(vectors ** 2, axis=1), 1e-20), 0, 1)
    distances = np.sum((offset - fractions[:, :, None] * vectors) ** 2, axis=2)
    return bool(np.any(distances < (tolerance / 111_195) ** 2))


def context_size(observed, leg, sequence, start, end):
    """Count the surrounding recorded stops supported by this oriented shape."""
    if start > end:
        return context_size(observed, leg, list(reversed(sequence)), len(sequence) - 1 - start, len(sequence) - 1 - end)
    def prefix_size(needles, haystack):
        count, cursor = 0, 0
        for name in needles:
            try:
                cursor = haystack.index(name, cursor) + 1
            except ValueError:
                break
            count += 1
        return count
    return 2 + prefix_size(observed[:leg][::-1], sequence[:start][::-1]) + prefix_size(observed[leg + 2:], sequence[end + 1:])


def build_geometry(variants, patterns):
    """Match ordered journeys; compose rail segments only when the corridor is unique."""
    index, graph = defaultdict(set), defaultdict(dict)
    for i, variant in enumerate(variants):
        variant = dict(variant)
        variants[i] = variant
        variant["names"] = list(map(station_name, variant["names"]))
        for name in variant["names"]:
            index[name].add(i)
        for j, (a, b) in enumerate(zip(variant["names"], variant["names"][1:])):
            if a == b:
                continue
            start, end = variant["stop_indices"][j:j + 2]
            if start >= end:
                continue
            curve = clip_path(variant["points"], start, end, point_at(variant["points"], start), point_at(variant["points"], end))
            length = cumulative_distances(curve)[-1]
            for origin, destination, points in ((a, b, curve), (b, a, list(reversed(curve)))):
                graph[(variant["operator"], origin)].setdefault(destination, []).append((length, points, variant["routes"]))

    paths, mappings, pair_cache = {}, {}, {}

    def save(points, reason=None, method="shape"):
        quality = "track" if points else "approximate"
        identifier = hashlib.sha256(json.dumps([quality, points, reason]).encode()).hexdigest()[:20]
        paths[identifier] = {"coordinates": points, "quality": quality}
        if reason:
            paths[identifier]["reason"] = reason
        else:
            paths[identifier]["method"] = method
        return identifier

    def choose(choices):
        if not choices:
            return None
        choices = sorted(choices, key=lambda item: item[0])
        if any(length > choices[0][0] * 1.3 + 500 for length, _ in choices[1:]):
            return None
        return choices[0][1]

    def unique_corridor(operator, line, origin, destination, blocked, blocked_points, limit):
        """A graph fallback may join shapes, but must not guess between corridors."""
        def route(omit=None):
            queue, best = [(0, origin, [])], {origin: 0}
            while queue:
                distance, node, chain = heapq.heappop(queue)
                if distance > best[node] or distance > limit:
                    continue
                if node == destination:
                    return chain
                for neighbor, edges in graph.get((operator, node), {}).items():
                    if neighbor in blocked or (node, neighbor) == omit or (neighbor, node) == omit:
                        continue
                    matching = [edge for edge in edges if station_name(line) in station_name(edge[2])]
                    edges = matching or edges
                    curve = choose([(length, points) for length, points, _ in edges if not passes_stations(points, blocked_points)])
                    if curve is None:
                        continue
                    candidate = distance + cumulative_distances(curve)[-1]
                    if candidate < best.get(neighbor, float("inf")):
                        best[neighbor] = candidate
                        heapq.heappush(queue, (candidate, neighbor, chain + [(node, neighbor, curve)]))
            return None
        chain = route()
        if not chain or any(route((a, b)) is not None for a, b, _ in chain):
            return None
        points = []
        for _, _, curve in chain:
            if points and cumulative_distances([points[-1], curve[0]])[-1] > 100:
                return None
            points.extend(curve if not points or points[-1] != curve[0] else curve[1:])
        return points

    for n, (operator, line, names, points) in enumerate(patterns):
        normalized = list(map(station_name, names))
        full = []
        candidates = set.intersection(*(index[name] for name in normalized)) if normalized else set()
        for i in sorted(candidates):
            if variants[i]["operator"] != operator:
                continue
            for reverse in (False, True):
                sequence = list(reversed(variants[i]["names"])) if reverse else variants[i]["names"]
                indices = ordered_indices(normalized, sequence)
                if indices is not None:
                    full.append((i, [len(sequence) - 1 - k if reverse else k for k in indices]))
        matching = [match for match in full if station_name(line) in station_name(variants[match[0]]["routes"])]
        full = matching or full
        legs = []
        for j, (a, b) in enumerate(zip(points, points[1:])):
            a_name, b_name = normalized[j:j + 2]
            blocked = frozenset(normalized) - {a_name, b_name}
            blocked_points = [point for name, point in zip(normalized, points) if name in blocked]
            cache_key = (operator, line, a_name, b_name, tuple(a), tuple(b), blocked, tuple((i, tuple(indices[j:j + 2])) for i, indices in full))
            if cache_key in pair_cache:
                legs.append(pair_cache[cache_key])
                continue
            spans = [(i, indices[j], indices[j + 1]) for i, indices in full]
            if not spans:
                for i in sorted(index[a_name] & index[b_name]):
                    v = variants[i]
                    if v["operator"] != operator:
                        continue
                    spans.extend((i, start, end) for start, name in enumerate(v["names"]) if name == a_name
                                 for end, other in enumerate(v["names"]) if other == b_name and start != end)
            choices = []
            direct = cumulative_distances([a, b])[-1]
            limit = max(direct * 5, direct + 10_000)
            for i, start, end in spans:
                v = variants[i]
                if blocked.intersection(v["names"][min(start, end) + 1:max(start, end)]):
                    continue
                first, last = v["stop_indices"][start], v["stop_indices"][end]
                if cumulative_distances([a, point_at(v["points"], first)])[-1] > 500 or cumulative_distances([point_at(v["points"], last), b])[-1] > 500:
                    continue
                curve = clip_path(v["points"], first, last, a, b)
                length = cumulative_distances(curve)[-1]
                if 0 < length <= limit and not passes_stations(curve, blocked_points):
                    choices.append((context_size(normalized, j, v["names"], start, end), length, curve, v["routes"]))
            if choices:
                # Extra outer-line overlap must not outweigh a valid local corridor.
                if any(choice[0] > 2 for choice in choices):
                    choices = [choice for choice in choices if choice[0] > 2]
            preferred = [choice for choice in choices if station_name(line) in station_name(choice[3])]
            choices = preferred or choices
            curve = choose([(length, curve) for _, length, curve, _ in choices])
            method = "shape"
            if not choices:
                curve = unique_corridor(operator, line, a_name, b_name, blocked, blocked_points, limit)
                if curve:
                    # Keep joins inside each station's platform area.
                    if cumulative_distances([a, curve[0]])[-1] > 500 or cumulative_distances([curve[-1], b])[-1] > 500:
                        curve = None
                    else:
                        curve = [a, *curve, b]
                        method = "segments"
            identifier = save(curve, method=method) if curve else save([], reason="ambiguous" if choices else "unmatched")
            pair_cache[cache_key] = identifier
            legs.append(identifier)
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
    cache = Path(__file__).resolve().parents[1] / ".cache" / f"rail-variants-v2-{archive_checksum[:16]}.json"
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
    metadata = {"matcher_version": 2, "source": "Transport Victoria GTFS Schedule", "source_date": args.source_date,
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
