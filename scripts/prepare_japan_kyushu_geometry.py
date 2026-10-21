"""Extract connected conventional Kyushu railway tracks from dated OSM data.

Pyosmium is preparation-only; the PBF and raw API downloads stay in .cache.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_switzerland_geometry import compact_ways

SOURCE_URL = "https://download.geofabrik.de/asia/japan/kyushu-261020.osm.pbf"
SOURCE_SHA256 = "c56764fbe77b66c6dddadc62ebe8f8ea9bb9a0cff8a00f63507c3e731ed88423"
CATALOG = ROOT / "data/sources/japan_kyushu_stations.json"
OUTPUT = ROOT / "data/reference/japan/kyushu-tracks-2026-10-22.json.gz"


def osm_station_name(name):
    return re.sub(r"\d+$", "", re.sub(r"駅.*$", "", name)).replace("ヶ", "ケ")


def prepare(filename, output=OUTPUT):
    import osmium

    if file_hash(filename) != SOURCE_SHA256:
        raise ValueError("Kyushu PBF differs from the validated pin")
    seeds = json.loads(CATALOG.read_text())

    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways, self.stations = {}, {}

        def way(self, way):
            tags = dict(way.tags)
            if (tags.get("railway") == "rail" and tags.get("highspeed") != "yes"
                    and tags.get("gauge", "1067") == "1067"
                    and tags.get("service") != "yard"
                    and tags.get("disused") != "yes" and tags.get("abandoned") != "yes"
                    and tags.get("usage") not in {"industrial", "military", "test"}):
                self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes]}

        def node(self, node):
            tags = dict(node.tags)
            if tags.get("railway") not in {"station", "stop", "halt"}:
                return
            for name in {tags.get("name", ""), tags.get("name:ja", "")}:
                name = osm_station_name(name)
                if name in seeds:
                    point = [node.location.lon, node.location.lat]
                    distance = cumulative_distances([point, seeds[name]["coordinate"]])[-1]
                    if distance < 2000:
                        self.stations.setdefault(name, {})[str(node.id)] = (distance, point)

    inventory = Inventory()
    inventory.apply_file(str(filename), filters=[osmium.filter.KeyFilter("railway")])
    needed = {n for way in inventory.ways.values() for n in way["nodes"]}

    class Locations(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {}

        def node(self, node):
            self.nodes[str(node.id)] = [node.location.lon, node.location.lat]

    locations = Locations()
    locations.apply_file(str(filename), filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    if needed - locations.nodes.keys():
        raise ValueError("Missing native Kyushu track nodes")
    stations = {}
    for name, seed in seeds.items():
        # Prefer an explicitly named stop position on the original railway;
        # source centroids only remain a fallback, never an invented connector.
        options = [(distance, identifier, point) for identifier, (distance, point)
                   in inventory.stations.get(name, {}).items() if identifier in needed]
        if options:
            _, identifier, point = min(options)
            stations[name] = {**seed, "coordinate": point, "osm_node_id": int(identifier)}
        else:
            stations[name] = seed
    result = {"metadata": {
        "source": "Connected conventional railway ways © OpenStreetMap contributors via Geofabrik Kyushu",
        "source_url": SOURCE_URL, "source_date": "2026-10-20", "source_sha256": SOURCE_SHA256,
        "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "station_catalog_sha256": file_hash(CATALOG),
        "sources": [{"source_url": SOURCE_URL, "sha256": SOURCE_SHA256, "source_date": "2026-10-20"}],
        "note": "Operating conventional 1067 mm rails; only native shared node IDs join tracks. "
                "October geography is an alignment reference, not historical platform or running-track evidence."},
        "ways": compact_ways(inventory.ways, locations.nodes), "stations": stations}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
    print(f"Saved {output}: {len(result['ways'])} ways, {output.stat().st_size} bytes, SHA-256 {file_hash(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    prepare(args.extract, args.output)
