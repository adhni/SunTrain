"""Prepare optional German regional and S-Bahn days for 1–7 June 2026."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import daily_reference, save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_germany_replay import GEOMETRY, GEOMETRY_SHA256, GermanRailGraph, SOURCE as LONG_DISTANCE, domestic_sequence
from scripts.prepare_rail_replay import prepare as prepare_rail

SCOPE = ROOT / "data/reference/germany/regional-scope.json"
STATIONS = ROOT / "data/reference/germany/regional-station-scope.json"
SOURCE = {**LONG_DISTANCE,
    "url": "https://files.mobilitydatabase.org/mdb-1089/mdb-1089-202605310104/mdb-1089-202605310104.zip",
    "sha256": "cffefa8a878d5846514ff472123060ca44d1cb356f0a93e575cf90fd4305c913",
    "source": "DELFI e.V. / GTFS.de historical regional/S-Bahn GTFS via Mobility Database",
    "source_url": "https://gtfs.de/en/feeds/de_rv/", "assign_by_start": ["regional_rail", "commuter_rail"],
    "note": "Optional German regional and S/Regio-S-Bahn services from the 31 May 2026 archive. International journeys retain their German/border portions and original call times. Long-distance, sleeper, tourist/museum, tram-train-only operators and other urban modes are excluded from this layer. DB railway paths are inferred geographical alignments; unavailable private/urban infrastructure and other unmatched sections stay gaps. Passenger counts are unavailable.",
}
COLORS = {"regional_rail": "C83038", "commuter_rail": "008D4F"}  # SunTrain fallback colours.


def selected_route(route, agencies, scope):
    audited = scope.get(route.get("route_id"))
    return bool(audited and route.get("route_type") == "2"
        and route.get("agency_id") == audited["agency_id"]
        and route.get("route_short_name") == audited["route_short_name"]
        and agencies.get(audited["agency_id"], {}).get("agency_name") == audited["agency_name"])


def describe_route(route, trip, scope):
    audited = scope[route["route_id"]]
    mode = audited["mode"]
    return {"mode": mode, "route_id": route["route_id"], "route_short_name": route["route_short_name"],
        "line": route["route_short_name"] + " · " + audited["agency_name"], "direction": "Not specified",
        "color": route.get("route_color") or COLORS[mode]}


class IndexedRailGraph(GermanRailGraph):
    """Use the same 150 m projections, indexed offline for thousands of stops."""
    def __init__(self, ways):
        super().__init__(ways)
        self.grid = defaultdict(list)
        # Index every edge's complete bounds, including the matching margin;
        # neither long edges nor points near cell boundaries are lost.
        lower = np.floor((np.minimum(self.starts, self.starts + self.vectors) - 150) / 2000).astype(int)
        upper = np.floor((np.maximum(self.starts, self.starts + self.vectors) + 150) / 2000).astype(int)
        for i, (lo, hi) in enumerate(zip(lower, upper)):
            for x in range(lo[0], hi[0] + 1):
                for y in range(lo[1], hi[1] + 1):
                    self.grid[x, y].append(i)

    def anchors(self, point):
        key = tuple(point)
        if key not in self.anchor_cache:
            projected = np.array(point) * self.scale
            cell = tuple(np.floor(projected / 2000).astype(int))
            indices = np.asarray(self.grid.get(cell, []), dtype=int)
            if not len(indices):
                self.anchor_cache[key] = []
                return []
            offset = projected - self.starts[indices]
            vectors = self.vectors[indices]
            fractions = np.clip(np.sum(offset * vectors, axis=1) / self.squares[indices], 0, 1)
            errors = np.sqrt(np.sum((offset - fractions[:, None] * vectors) ** 2, axis=1))
            candidates = sorted(np.where(errors <= 150)[0], key=lambda j: (errors[j], indices[j]))[:8]
            self.anchor_cache[key] = [(int(indices[j]), float(fractions[j]), float(errors[j]),
                ((self.starts[indices[j]] + fractions[j] * vectors[j]) / self.scale).tolist()) for j in candidates]
        return self.anchor_cache[key]


def geometry_resolver(geographic):
    graph = IndexedRailGraph(geographic["ways"])

    def resolve(route, trip, sequence, coordinates):
        curves = []
        for a, b in zip(coordinates, coordinates[1:]):
            curve = graph.leg(a, b)
            if curve and cumulative_distances(curve)[-1] > max(5000, 3 * cumulative_distances([a, b])[-1]):
                curve = None
            curves.append(curve)
        return curves
    return resolve


def mode_day(reference, day, mode, *, prefix=None):
    rows = [row for row in reference["days"][day] if reference["patterns"][row[0]]["mode"] == mode]
    result = daily_reference({**reference, "days": {day: rows}}, day)
    # Independent bundles must not overwrite shared schedule/topology keys in a
    # combined replay. Original trip IDs remain untouched in the occurrence rows.
    prefix = prefix or "de-rv-" + mode + "-"
    result["stop_patterns"] = {prefix + key: value for key, value in result["stop_patterns"].items()}
    result["patterns"] = {prefix + key: {**value, "stop_pattern": prefix + value["stop_pattern"]}
                          for key, value in result["patterns"].items()}
    result["days"][day] = [[prefix + key, trip, offset] for key, trip, offset in rows]
    return result


def prepare(cache, output, geometry=GEOMETRY):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError("DB railway geometry differs from the validated reference")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    scope, stations = json.loads(SCOPE.read_text()), json.loads(STATIONS.read_text())
    if any(s["source_gtfs_sha256"] != SOURCE["sha256"] for s in (scope, stations)):
        raise ValueError("Regional scope belongs to a different archive")
    audit = Counter()

    def select(sequence, stops):
        for row in sequence:
            key = row["stop_id"]
            if key in stations["stops"] and stations["stops"][key] != stops[key]["stop_name"]:
                raise ValueError("Audited regional station name changed")
        clipped = domestic_sequence(sequence, stops, stations["stops"])
        audit["included_candidates" if clipped else "outside_domestic_scope_or_single_call"] += 1
        return clipped

    weekly = cache / "regional-week.json.gz"
    prepare_rail("germany-regional", {**SOURCE, "geometry_sha256": GEOMETRY_SHA256,
                 "geometry_references": [geographic["metadata"]]}, cache, weekly,
                 lambda route, agencies: selected_route(route, agencies, scope["routes"]),
                 lambda route, trip: describe_route(route, trip, scope["routes"]),
                 geometry_resolver=geometry_resolver(geographic), select_sequence=select)
    with gzip.open(weekly, "rt") as stream:
        reference = json.load(stream)
    reference["metadata"]["regional_scope"] = {**dict(audit), "route_scope_sha256": file_hash(SCOPE), "station_scope_sha256": file_hash(STATIONS)}
    save_reference(reference, weekly)
    operators = sorted({p["operator"] for p in reference["patterns"].values()})
    output.mkdir(parents=True, exist_ok=True)
    (output / "regional-operators.json").write_text(json.dumps(operators, ensure_ascii=False, indent=2) + "\n")
    for day in reference["days"]:
        for mode in COLORS:
            filename = output / mode / (day + ".json.gz")
            result = mode_day(reference, day, mode)
            save_reference(result, filename)
            print(day, mode, len(result["days"][day]), filename.stat().st_size, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/germany")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/germany")
    args = parser.parse_args()
    prepare(args.cache, args.output, args.geometry)
