"""Prepare the JR East portion of a pinned community Tokyo GTFS snapshot."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash, path_legs, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_rail_replay import prepare as prepare_rail

GRAPH_URL = "https://raw.githubusercontent.com/MKuranowski/TokyoGTFS/main/data/rail_geo.osm"
GRAPH_SHA256 = "8809cab8a2e5eb499411c98d5285c1913ae1afebdd85ba0f02fbf89b95918bd8"

SOURCE = {
    "first": "2026-10-20", "last": "2026-10-20", "timezone": "Asia/Tokyo",
    "url": "https://mkuran.pl/gtfs/tokyo/rail.zip",
    "sha256": "e08cae7c18915b4aede6da51bb24b01e0c308c8f4bde7dc101ca1de922bf14b2",
    "captured": "2026-10-21", "published": "", "calendar_validity": True,
    "assign_by_start": ["train"],
    "source": "TokyoGTFS community railway conversion of Mini Tokyo 3D timetables",
    "source_url": "https://mkuran.pl/gtfs/",
    "license": "MIT (railway data, as declared by TokyoGTFS)",
    "license_url": "https://github.com/MKuranowski/TokyoGTFS#license",
    "attribution": "Schedules: Copyright (c) 2019-2025 Akihiko Kusanagi, MIT. "
                   "GTFS conversion: Mikołaj Kuranowski / TokyoGTFS. "
                   "JR East selection and geometry filtering by SunTrain. Independent community timetable replay.",
    "geometry_source": "TokyoGTFS supplied railway shapes, generated from its CC0 railway graph",
    "geometry_source_url": "https://github.com/MKuranowski/TokyoGTFS/tree/main/data",
    "geometry_license": "CC0 1.0 (source graph); MIT (published railway feed)",
    "geometry_license_url": "https://github.com/MKuranowski/TokyoGTFS#license",
    "geometry_source_date": "Retrieved 2026-10-21",
    "geometry_sha256": GRAPH_SHA256,
    "geometry_method": "native_or_projected", "geometry_quality": "shape",
    "note": "JR East conventional trains only, 20 October 2026, from a community timetable snapshot. "
            "Its generated calendar is not an official historical archive or a record of disruptions. "
            "Other operators and Shinkansen are excluded. Through-running sections remain separate scheduled journeys. "
            "Tokyo local time; journeys belong to their 03:00–03:00 departure day. "
            "Unsupported railway sections stay gaps. No live tracking or passenger loads.",
}


def selected_route(route, agencies):
    return (route.get("agency_id") == "JR-East" and "JR-East" in agencies
            and route.get("route_type") == "2" and route.get("route_id", "").startswith("JR-East."))


def describe_route(route, trip):
    name = route["route_long_name"]
    if " JR " in name:
        name = "JR " + name.split(" JR ", 1)[1]
    direction = None
    if route["route_id"] == "JR-East.Yamanote":
        direction = {"0": "Outer loop", "1": "Inner loop"}.get(trip.get("direction_id"))
    return {"mode": "train", "operator": "JR East", "route_id": route["route_id"],
            "route_short_name": route.get("route_short_name", ""), "line": name,
            "category": "JR East", "direction": direction}


def railway_edges(filename):
    root = ET.parse(filename).getroot()
    nodes = {node.attrib["id"]: (round(float(node.attrib["lon"]), 6), round(float(node.attrib["lat"]), 6))
             for node in root.findall("node")}
    edges = set()
    for way in root.findall("way"):
        refs = [node.attrib["ref"] for node in way.findall("nd")]
        edges.update(frozenset((nodes[a], nodes[b])) for a, b in zip(refs, refs[1:]))
    return edges


def railway_geometry(shapes, edges):
    gaps = {}
    for key, raw in shapes.items():
        raw = sorted(raw)
        gaps[key] = [(a[1], b[1]) for a, b in zip(raw, raw[1:])
                     if a[2] != b[2] and frozenset((tuple(a[2]), tuple(b[2]))) not in edges]
    def resolve(route, trip, sequence, coordinates):
        key = trip.get("shape_id")
        raw = shapes.get(key, [])
        if not raw:
            return [None] * (len(sequence) - 1)
        anchors = [float(row["shape_dist_traveled"]) for row in sequence]
        curves = path_legs(raw, anchors, coordinates, recover_native=True)
        # The upstream converter can insert a straight node-to-node fallback
        # when routing fails. Validate original edges before simplification:
        # a genuinely straight railway remains valid, regardless of length.
        return [None if any(start < b - 1e-8 and end > a + 1e-8 for a, b in gaps[key]) else curve
                for curve, start, end in zip(curves, anchors, anchors[1:])]
    return resolve


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    graph = fetch(GRAPH_URL, cache / "rail_geo.osm")
    if file_hash(graph) != GRAPH_SHA256:
        raise ValueError("Tokyo railway graph differs from the validated source")
    edges = railway_edges(graph)
    prepare_rail("tokyo", SOURCE, cache, output, selected_route, describe_route,
                 geometry_resolver_factory=lambda routes, trips, shapes: railway_geometry(shapes, edges))
    filename = fetch(SOURCE["url"], cache / "rail.zip")
    with ZipFile(filename) as archive:
        numbers = {r["trip_id"]: r.get("trip_short_name") or r["trip_id"]
                   for r in records(archive, "trips.txt")}
    with gzip.open(output, "rt") as stream:
        reference = json.load(stream)
    used = {trip for rows in reference["days"].values() for _, trip, _ in rows}
    reference["train_numbers"] = {trip: numbers[trip] for trip in sorted(used)}
    reference["metadata"]["calendar_basis"] = "Community-generated weekday/holiday calendar, 19 October 2026–19 October 2027; not official historical validity."
    save_reference(reference, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/tokyo")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/tokyo/2026-10-20.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
