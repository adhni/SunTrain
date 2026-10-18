"""Extract RET railway geometry from a pinned Rotterdam OSM extract (ODbL)."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_singapore_geometry import connected_runs

SOURCE_URL = "https://download.bbbike.org/osm/bbbike/Rotterdam/Rotterdam.osm.pbf"
SOURCE_DATE = "2026-10-17"
SOURCE_SHA256 = "964daa57328d7abfd43791da46073759a849915a24b8664597f9cb4a4171cba5"
OUTPUT = ROOT / "data/reference/netherlands/ret-osm-2026-10-17.json.gz"


def selected_relation(tags):
    return (tags.get("type") == "route" and tags.get("route") == "subway"
            and tags.get("operator") == "RET" and tags.get("ref") in {"A", "B", "C", "D", "E"})


def prepare(filename, output, supplements=()):
    import osmium  # Offline preparation only, as for London's railway extract.

    digest = file_hash(filename)
    if digest != SOURCE_SHA256:
        raise ValueError("Rotterdam OSM extract differs from the validated snapshot")

    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways, self.relations = {}, []

        def way(self, way):
            if way.tags.get("railway") in {"subway", "light_rail", "rail"} and way.tags.get("service") not in {"yard", "siding", "spur"}:
                self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes]}

        def relation(self, relation):
            tags = dict(relation.tags)
            if selected_relation(tags):
                self.relations.append({"id": str(relation.id), "tags": tags,
                    "ways": [str(m.ref) for m in relation.members if m.type == "w" and m.role in {"", "forward", "backward"}]})

    raw = Inventory()
    raw.apply_file(str(filename))
    extra_nodes, provenance = {}, []
    for supplement in supplements:
        elements = json.loads(supplement.read_text())["elements"]
        for element in elements:
            key = str(element["id"])
            if element["type"] == "way" and element.get("tags", {}).get("railway") in {"subway", "light_rail", "rail"} and element.get("tags", {}).get("service") not in {"yard", "siding", "spur"}:
                raw.ways[key] = {"nodes": [str(node) for node in element["nodes"]]}
            elif element["type"] == "node":
                extra_nodes[key] = [element["lon"], element["lat"]]
            elif element["type"] == "relation" and selected_relation(element.get("tags", {})):
                raw.relations = [r for r in raw.relations if r["id"] != key]
                raw.relations.append({"id": key, "tags": element["tags"],
                    "ways": [str(m["ref"]) for m in element["members"] if m["type"] == "way" and m.get("role", "") in {"", "forward", "backward"}]})
                provenance.append({"source_url": f"https://api.openstreetmap.org/api/0.6/relation/{key}/full.json",
                    "source_date": "2026-10-18", "sha256": file_hash(supplement)})
    needed = {node for relation in raw.relations for way in relation["ways"] for node in raw.ways.get(way, {}).get("nodes", [])}

    class Nodes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {}

        def node(self, node):
            key = str(node.id)
            if key in needed:
                self.nodes[key] = [node.location.lon, node.location.lat]

    locations = Nodes()
    locations.apply_file(str(filename))
    locations.nodes.update({key: point for key, point in extra_nodes.items() if key in needed})
    # Missing extract members split runs instead of being bridged.
    ways = {key: way for key, way in raw.ways.items() if all(n in locations.nodes for n in way["nodes"])}
    lines = {}
    for relation in raw.relations:
        for run in connected_runs(relation, ways):
            if len(run) >= 2:
                lines.setdefault(relation["tags"]["ref"], []).append({"relation": relation["id"],
                    "name": relation["tags"].get("name", ""), "node_ids": run,
                    "coordinates": [locations.nodes[node] for node in run]})
    if set(lines) != {"A", "B", "C", "D", "E"}:
        raise ValueError("Rotterdam extract lacks one or more metro lines")
    result = {"metadata": {"source": "OpenStreetMap contributors via BBBike Rotterdam extract",
        "source_url": SOURCE_URL, "source_date": SOURCE_DATE, "source_sha256": digest,
        "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "supplements": provenance,
        "note": "October 2026 geographic reference for June schedules; not proof of historical running-track use. Only connected RET route ways are retained."}, "lines": lines}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    print({line: len(variants) for line, variants in lines.items()}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--supplement", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    prepare(args.extract, args.output, args.supplement)
