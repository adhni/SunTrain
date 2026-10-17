"""Extract connected London railway routes from a pinned OSM city extract.

The resulting geometry database is ODbL 1.0. Pyosmium is only needed when
rebuilding it; the app and timetable preparation use the bundled JSON file.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_singapore_geometry import connected_runs

SOURCE_URL = "https://download.bbbike.org/osm/bbbike/London/London.osm.gz"
SOURCE_DATE = "2026-10-11"
SOURCE_SHA256 = "51a9f096bcd6da2c6435cc2dc8ec663f142ea5649498fb6bf1ac65fd858a7b9e"
LINE_NAMES = {"bakerloo": "BAK", "central": "CEN", "circle": "CIR", "district": "DIS",
              "hammersmithandcity": "HAM", "jubilee": "JUB", "metropolitan": "MET",
              "northern": "NTN", "piccadilly": "PIC", "victoria": "VIC", "waterlooandcity": "WAC"}


def line_code(tags):
    if tags.get("type") != "route" or tags.get("route") not in {"subway", "train", "light_rail", "tram"}:
        return None
    normalize = lambda value: re.sub("[^a-z]", "", value.lower().replace("&", "and"))
    ref = normalize(tags.get("ref", ""))
    if ref in LINE_NAMES:
        return LINE_NAMES[ref]
    name = normalize(tags.get("name", ""))
    network = normalize(tags.get("network", ""))
    if ref == "dlr" or "docklandslightrailway" in network or "docklandslightrailway" in name:
        return "DLR"
    if tags.get("route") == "tram" and any(s in network + name for s in ("tramlink", "londontrams")):
        return "TR"
    if "londonunderground" in network or tags.get("route") == "subway":
        for label, code in LINE_NAMES.items():
            if name.startswith(label):
                return code
    return None


def inventory(filename):
    import osmium

    class Handler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways, self.relations = {}, []

        def way(self, way):
            if way.tags.get("railway") in {"rail", "subway", "light_rail", "tram", "monorail"}:
                self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes], "tags": dict(way.tags)}

        def relation(self, relation):
            tags = dict(relation.tags)
            if line_code(tags):
                self.relations.append({"id": str(relation.id), "tags": tags,
                    "ways": [str(m.ref) for m in relation.members if m.type == "w" and m.role in {"", "forward", "backward"}]})

    handler = Handler()
    handler.apply_file(str(filename))
    return {"relations": handler.relations, "ways": handler.ways, "source_sha256": file_hash(filename)}


def extract(filename, raw, supplement=None):
    import osmium

    extra_nodes = {}
    if supplement:
        for element in supplement["elements"]:
            key = str(element["id"])
            if element["type"] == "way" and element.get("tags", {}).get("railway") in {"rail", "subway", "light_rail", "tram", "monorail"}:
                raw["ways"][key] = {"nodes": [str(n) for n in element["nodes"]], "tags": element["tags"]}
            if element["type"] == "node":
                extra_nodes[key] = [element["lon"], element["lat"]]
    relations = [r for r in raw["relations"] if line_code(r["tags"])]
    selected = {way for relation in relations for way in relation["ways"] if way in raw["ways"]}
    ways = {key: raw["ways"][key] for key in sorted(selected)}
    needed = {node for way in ways.values() for node in way["nodes"]}

    class Nodes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {key: point for key, point in extra_nodes.items() if key in needed}

        def node(self, node):
            if str(node.id) in needed:
                self.nodes[str(node.id)] = [node.location.lon, node.location.lat]

    handler = Nodes()
    handler.apply_file(str(filename))
    if not needed <= handler.nodes.keys():
        raise ValueError("Extract lacks required railway nodes")
    return {"relations": relations, "ways": ways, "nodes": handler.nodes}


def variants(raw):
    result, seen = {}, set()
    for relation in raw["relations"]:
        code = line_code(relation["tags"])
        if not code:
            continue
        for run in connected_runs(relation, raw["ways"]):
            points = [raw["nodes"][key] for key in run]
            key = (code, tuple(run))
            if key in seen or len(points) < 2:
                continue
            seen.add(key)
            result.setdefault(code, []).append({"relation": relation["id"], "name": relation["tags"].get("name", ""),
                                               "node_ids": run, "coordinates": points})
    return result


def save(raw, output, digest, supplement_hash=None):
    result = {"metadata": {"source": "OpenStreetMap contributors via BBBike London extract", "source_url": SOURCE_URL,
        "source_date": SOURCE_DATE, "source_sha256": digest, "license": "ODbL 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "note": "Connected operating railway ways from London route relations; a geography reference, not proof of historical running-track use."},
        "lines": variants(raw)}
    if supplement_hash:
        result["metadata"]["supplement"] = {"source": "OpenStreetMap API bulk railway ways/nodes",
            "source_url": "https://api.openstreetmap.org/api/0.6/", "source_date": "2026-10-18", "sha256": supplement_hash}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    print({line: len(rows) for line, rows in result["lines"].items()}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path)
    parser.add_argument("--inventory", type=Path, help="Optional cached inventory with matching source_sha256")
    parser.add_argument("--supplement", type=Path, help="Cached OSM ways/nodes for outer branches and missing route members")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/london/osm-rail-2026-10-11.json.gz")
    args = parser.parse_args()
    digest = file_hash(args.extract)
    if digest != SOURCE_SHA256:
        raise ValueError("OSM extract differs from the validated geographic snapshot")
    if args.inventory and args.inventory.exists():
        with gzip.open(args.inventory, "rt") as stream:
            raw = json.load(stream)
        if raw.get("source_sha256") != digest:
            raise ValueError("Cached inventory differs from the OSM extract")
    else:
        raw = inventory(args.extract)
    supplement = json.loads(args.supplement.read_text()) if args.supplement else None
    save(extract(args.extract, raw, supplement), args.output, digest, file_hash(args.supplement) if args.supplement else None)
