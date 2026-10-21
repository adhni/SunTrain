"""Compile pinned operating Shinkansen OSM ways; never join unrelated nodes."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_boston_replay import fetch

MANIFEST = ROOT / "data/sources/japan_shinkansen_geometry.json"


def operating_ways(raw):
    nodes = {e["id"]: [e["lon"], e["lat"]] for e in raw["elements"] if e["type"] == "node"}
    ways = [e for e in raw["elements"] if e["type"] == "way" and e.get("tags", {}).get("railway") == "rail"]
    return [{"node_ids": way["nodes"], "coordinates": [nodes[node] for node in way["nodes"]]}
            for way in sorted(ways, key=lambda w: w["id"]) if len(way["nodes"]) >= 2]


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    sources = json.loads(MANIFEST.read_text())
    result = {"metadata": {"source": "OpenStreetMap contributors, operating Shinkansen railway ways",
        "source_url": "https://www.openstreetmap.org/copyright", "source_date": "2026-10-21",
        "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "sources": sources}, "lines": {}}
    for source in sources:
        filename = fetch(source["source_url"], cache / (source["line"] + "-osm.json"))
        if file_hash(filename) != source["sha256"]:
            raise ValueError("Japan OSM source changed; inspect before updating the geometry pin")
        result["lines"][source["line"]] = operating_ways(json.loads(filename.read_text()))
    result["lines"]["gala-yuzawa"] = result["lines"]["joetsu"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":")).encode())
    print(f"Saved {output}: {output.stat().st_size} bytes; SHA-256 {file_hash(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/japan")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/japan/shinkansen-tracks-2026-10-21.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
