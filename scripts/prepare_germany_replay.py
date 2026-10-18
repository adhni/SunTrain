"""Prepare German long-distance trains for 1–7 June 2026 from a pinned archive."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.london_rail_graph import RailGraph
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY = ROOT / "data/reference/germany/db-rail-2026-10-18.json.gz"
GEOMETRY_SHA256 = "de35f91112ce6f6ce6878d21f7e78fac2a2bfe45e61a181a55e153ddcbf5147a"
SCOPE = ROOT / "data/reference/germany/station-scope.json"
OPERATORS = {
    "1": "Ceske Drahy", "2": "SBB", "3": "MAV", "4": "SÜWEX", "5": "HZZP",
    "6": "DB Fernverkehr AG", "7": "ZSSK", "8": "DB Fernverkehr (Codesharing)",
    "9": "SNCF", "10": "ÖBB", "11": "PKP Intercity", "12": "Dänische Staatsbahnen",
    "13": "Nederlandse Spoorwegen",
}
# SunTrain category colours; these are not official individual line colours.
COLORS = {"ICE": "E32219", "IC": "B32636", "EC": "007A87", "ECE": "007A87", "RJ": "9A1434", "EN": "34478C"}
SOURCE = {
    "name": "Germany", "first": "2026-06-01", "last": "2026-06-07", "timezone": "Europe/Berlin",
    "captured": "2026-05-31", "published": "",
    "url": "https://files.mobilitydatabase.org/mdb-768/mdb-768-202605310001/mdb-768-202605310001.zip",
    "sha256": "9da51452d56f80cbae493af56ac023aab7e4daee2836f12d8721dfaa74738ebe",
    "source": "DELFI e.V. / GTFS.de historical long-distance GTFS via Mobility Database",
    "source_url": "https://gtfs.de/en/feeds/de_fv/", "calendar_validity": True,
    "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Timetables: DELFI e.V. / GTFS.de · archive captured 31 May 2026. Railway alignment: DB InfraGO AG · CC BY 4.0. Paths matched and simplified by SunTrain.",
    "assign_by_start": ["train"], "geometry_quality": "track",
    "geometry_source": "DB InfraGO AG · INSPIRE railway network, matched and simplified by SunTrain",
    "geometry_source_url": "https://www.govdata.de/suche/daten/wms-schienenverkehrsnetz-db-infrago",
    "geometry_license": "CC BY 4.0", "geometry_license_url": "https://creativecommons.org/licenses/by/4.0/",
    "geometry_source_date": "accessed 2026-10-18; geographic reference for June schedules",
    "note": "German portions of ICE, IC, EC and ECE journeys from the 31 May archive, including overnight services. The archive's Railjet/EuroNight entries have no active German sections in this week. Foreign-only sections, regional/urban transport and buses are excluded. Original station times are retained. DB railway paths are inferred geographic alignments, not historical running-track records; unresolved sections remain gaps. No individual passenger counts.",
}


def selected_route(route, agencies):
    agency = route.get("agency_id")
    return (route.get("route_type") == "2" and bool(re.fullmatch(r"(?:ICE|IC|EC|ECE|RJ|EN)(?: \d+)?", route.get("route_short_name", "")))
            and agency in OPERATORS and agencies.get(agency, {}).get("agency_name") == OPERATORS[agency])


def describe_route(route, trip):
    category = route["route_short_name"].split()[0]
    return {"mode": "train", "route_id": route["route_id"], "route_short_name": route["route_short_name"],
            "line": route["route_short_name"] + " · " + OPERATORS[route["agency_id"]],
            "direction": "Not specified", "color": route.get("route_color") or COLORS[category]}


def domestic_sequence(sequence, stops, scope):
    indices = [i for i, row in enumerate(sequence) if row["stop_id"] in scope]
    if len(indices) < 2:
        return []
    # Keep order and all intermediate calls. In particular, never join two
    # German sections across a foreign detour by removing the calls in between.
    return sequence[indices[0]:indices[-1] + 1]


class GermanRailGraph(RailGraph):
    def __init__(self, ways, fast=False):
        super().__init__(ways)
        if fast:
            # ICE routing favours faster published railway corridors rather
            # than the geographically shorter classic line. Other categories
            # use distance routing constrained by their intermediate calls.
            speeds = {}
            for way in ways:
                for a, b in zip(way["node_ids"], way["node_ids"][1:]):
                    key = tuple(sorted((a, b)))
                    speeds[key] = max(speeds.get(key, 20), way["speed"])
            self.lengths = [length * 160 / speeds[edge] for edge, length in zip(self.edges, self.lengths)]
            self.neighbours.clear()
            for (a, b), cost in zip(self.edges, self.lengths):
                self.neighbours[a].append((b, cost))
                self.neighbours[b].append((a, cost))


def geometry_resolver(geometry):
    graphs = {}

    def resolve(route, trip, sequence, coordinates):
        fast = route["route_short_name"].split()[0] in {"ICE", "ECE"}
        if fast not in graphs:
            graphs[fast] = GermanRailGraph(geometry["ways"], fast=fast)
        curves = []
        for a, b in zip(coordinates, coordinates[1:]):
            curve = graphs[fast].leg(a, b)
            # Reject implausible detours; disconnected sections stay gaps.
            if curve and cumulative_distances(curve)[-1] > max(5000, 3 * cumulative_distances([a, b])[-1]):
                curve = None
            curves.append(curve)
        return curves

    return resolve


def prepare(cache, output, geometry=GEOMETRY):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError("DB railway geometry differs from the validated reference")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    scope = json.loads(SCOPE.read_text())
    if scope["source_gtfs_sha256"] != SOURCE["sha256"]:
        raise ValueError("Station scope belongs to a different timetable")
    audit = Counter()

    def select(sequence, stops):
        for row in sequence:
            key = row["stop_id"]
            if key in scope["stops"] and stops[key]["stop_name"] != scope["stops"][key]:
                raise ValueError("Audited station name changed")
        trimmed = domestic_sequence(sequence, stops, scope["stops"])
        audit["included_candidate_trips" if trimmed else "outside_domestic_scope_or_single_call"] += 1
        if trimmed and len(trimmed) < len(sequence):
            audit["clipped_candidate_trips"] += 1
        return trimmed

    prepare_rail("germany", {**SOURCE, "geometry_sha256": GEOMETRY_SHA256,
                 "geometry_references": [geographic["metadata"]]}, cache, output, selected_route, describe_route,
                 geometry_resolver=geometry_resolver(geographic), select_sequence=select)
    with gzip.open(output, "rt") as stream:
        result = json.load(stream)
    result["metadata"]["domestic_scope"] = {**dict(audit), "station_scope_sha256": file_hash(SCOPE),
        "note": "First through last audited German/border call; foreign-only trips and trips with fewer than two such calls are excluded. Original stop times and source trip IDs remain intact."}
    save_reference(result, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/germany")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/germany/2026-06-01.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output, args.geometry)
