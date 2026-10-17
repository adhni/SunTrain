"""Prepare London Underground, DLR and Trams on connected OSM railway paths.

The GTFS publisher's station-to-station sketch shapes are never used for
animation. Timetable preparation needs only the pinned ZIP and bundled geometry.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.prepare_singapore_replay import match_geometry
from scripts.london_rail_graph import RailGraph

GEOMETRY = ROOT / "data/reference/london/osm-rail-2026-10-11.json.gz"
GEOMETRY_SHA256 = "63459c614ad0df422f382f19f6bd14618b0173dbef334630f763924e80e82a3c"
UNDERGROUND = {"BAK", "CEN", "CIR", "DIS", "HAM", "JUB", "MET", "NTN", "PIC", "VIC", "WAC"}
SOURCE = {
    "name": "London", "first": "2026-10-05", "last": "2026-10-11", "timezone": "Europe/London",
    "captured": "2026-10-04", "published": "2026-10-04",
    "url": "https://github.com/planarnetwork/gb-transit/releases/download/feed-2026-10-04/gtfs-rail-and-tfl.zip",
    "sha256": "7bc0854bbc6d5206bfdd51a0e77a7bb1b3af8c627c360e2c5b0823fb03a7c5b7",
    "source": "TfL Journey Planner timetables converted to GTFS by Planar Network, 4 October 2026 release",
    "source_url": "https://github.com/planarnetwork/gb-transit/releases/tag/feed-2026-10-04",
    "license": "TfL transport data licence", "license_url": "https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service",
    "attribution": "Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019]. Timetables converted by Planar Network.",
    "geometry_quality": "track",
    "geometry_source": "Railway geometry © OpenStreetMap contributors",
    "geometry_source_url": "https://www.openstreetmap.org/copyright",
    "geometry_license": "ODbL 1.0", "geometry_license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "geometry_source_date": "2026-10-11 (outer-route supplements accessed 18 October)",
    "note": "London Underground, DLR and London Trams only. Scheduled estimates follow mapped railway paths; unresolved journey legs stay as gaps. Geography does not identify the actual running track. Overground, Elizabeth line, buses, boats and cable car are excluded. No individual train passenger loads; NUMBAT typical-day estimates are not assigned to these trips.",
}


def selected_route(route, agencies):
    if not route["route_id"].startswith("tfl_"):
        return False
    code = route["route_id"].removeprefix("tfl_")
    return ((route.get("agency_id") == "LUL" and route["route_type"] == "1" and code in UNDERGROUND)
            or (route.get("agency_id") == "DLR" and code == "DLR" and route["route_type"] == "2")
            or (route.get("agency_id") == "TCL" and code == "TR" and route["route_type"] == "0"))


def describe_route(route, trip):
    code = route["route_id"].removeprefix("tfl_")
    return {"mode": "subway" if code in UNDERGROUND else "light_rail", "route_id": code,
            "line": "London Trams" if code == "TR" else "DLR" if code == "DLR" else route["route_short_name"] + " line"}


def prepare(cache, geometry, output):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError("London railway geometry differs from the validated reference")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    graphs = {}

    def resolve(route, trip, sequence, coordinates):
        code = route["route_id"].removeprefix("tfl_")
        try:
            _, curves = match_geometry(geographic["lines"].get(code, []), coordinates)
            return curves
        except ValueError:
            # Subsurface services can continue across the shared Circle, District,
            # H&C and Metropolitan railway. Other lines stay in their own network.
            family = ("CIR", "DIS", "HAM", "MET") if code in {"CIR", "DIS", "HAM", "MET"} else (code,)
            if family not in graphs:
                graphs[family] = RailGraph([variant for line in family for variant in geographic["lines"].get(line, [])])
            return [graphs[family].leg(a, b) for a, b in zip(coordinates, coordinates[1:])]

    return prepare_rail("london", {**SOURCE, "geometry_sha256": GEOMETRY_SHA256}, cache, output,
                        selected_route, describe_route, geometry_resolver=resolve)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/london-audit")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/london" / (SOURCE["first"] + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.geometry, args.output)
