"""Extract only Singapore MRT/LRT OSM route geometry from a BBBike XML extract.

OSM data and this derived geometry database are licensed under ODbL 1.0.
No routing across disconnected ways or invented station connectors is allowed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE_URL = "https://download.bbbike.org/osm/bbbike/Singapore/Singapore.osm.gz"
LINE_REFS = {"NSL": "NS", "EWL": "EW", "NEL": "NE", "CCL": "CC", "DTL": "DT",
             "TEL": "TE", "BPLRT": "BP", "SKLRT": "SK", "PGLRT": "PG"}
LICENSE_URL = "https://opendatacommons.org/licenses/odbl/1-0/"


def elements(filename):
    """Stream top-level elements with bounded memory even for a city extract."""
    with gzip.open(filename, "rb") as stream:
        context = ET.iterparse(stream, events=("start", "end"))
        _, root = next(context)
        for event, element in context:
            if event == "end" and element.tag in {"node", "way", "relation"}:
                yield element
                element.clear()
                root.clear()


def extract(filename):
    ways, relations = {}, []
    for element in elements(filename):
        if element.tag == "node":
            continue
        tags = {t.attrib["k"]: t.attrib["v"] for t in element.findall("tag")}
        if element.tag == "way" and tags.get("railway") in {"rail", "subway", "light_rail", "monorail", "tram"} and tags.get("service") not in {"yard", "siding", "spur"}:
            ways[element.attrib["id"]] = {"nodes": [n.attrib["ref"] for n in element.findall("nd")], "tags": tags}
        if element.tag == "relation" and tags.get("type") == "route" and tags.get("ref") in LINE_REFS:
            relations.append({"id": element.attrib["id"], "tags": tags,
                "ways": [m.attrib["ref"] for m in element.findall("member")
                         if m.attrib["type"] == "way" and m.attrib.get("role", "") in {"", "forward", "backward"}]})
    selected = {key for relation in relations for key in relation["ways"] if key in ways}
    ways = {key: ways[key] for key in sorted(selected)}
    needed = {node for way in ways.values() for node in way["nodes"]}
    nodes = {}
    for element in elements(filename):
        if element.tag == "node" and element.attrib["id"] in needed:
            nodes[element.attrib["id"]] = [float(element.attrib["lon"]), float(element.attrib["lat"])]
    if not needed <= nodes.keys():
        raise ValueError("Extract is missing railway nodes")
    return {"relations": relations, "ways": ways, "nodes": nodes}


def connected_runs(relation, ways):
    """Respect relation order and OSM node identity; split rather than bridge gaps."""
    runs, current = [], []
    for key in relation["ways"]:
        nodes = ways.get(key, {}).get("nodes", [])
        if len(nodes) < 2:
            if current:
                runs.append(current)
            current = []
            continue
        if not current:
            current = nodes[:]
        elif current[-1] == nodes[0]:
            current.extend(nodes[1:])
        elif current[-1] == nodes[-1]:
            current.extend(nodes[-2::-1])
        elif current[0] == nodes[0] and len(runs) == 0:
            # The first way's stored direction may oppose the route traversal.
            current.reverse()
            current.extend(nodes[1:])
        elif current[0] == nodes[-1] and len(runs) == 0:
            current.reverse()
            current.extend(nodes[-2::-1])
        else:
            runs.append(current)
            current = nodes[:]
    if current:
        runs.append(current)
    return runs


def variants(raw):
    result = defaultdict(list)
    seen = set()
    for relation in raw["relations"]:
        code = LINE_REFS.get(relation["tags"].get("ref"))
        if not code:
            continue
        for run in connected_runs(relation, raw["ways"]):
            points = [raw["nodes"][key] for key in run]
            signature = json.dumps([code, points])
            if signature not in seen and len(points) >= 2:
                seen.add(signature)
                result[code].append({"relation": relation["id"], "name": relation["tags"].get("name"), "coordinates": points})
    # The airport branch is represented by EWL route relations; keep only those
    # explicitly identified by their termini, rather than unrelated EW tracks.
    result["CG"] = [v for v in result["EW"] if "Changi Airport" in (v["name"] or "")]
    return dict(result)


def save(raw, output, source_hash, source_date):
    result = {"metadata": {"source": "OpenStreetMap contributors via BBBike Singapore extract",
        "source_url": SOURCE_URL, "source_date": source_date, "source_sha256": source_hash,
        "license": "ODbL 1.0", "license_url": LICENSE_URL,
        "note": "OSM geography snapshot, not proof of historical track use. Only connected operating railway ways from MRT/LRT route relations are retained."},
        "lines": variants(raw)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    print({code: len(rows) for code, rows in result["lines"].items()}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path)
    parser.add_argument("--source-date", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/singapore/osm-rail-2026-10-17.json.gz")
    args = parser.parse_args()
    save(extract(args.extract), args.output, hashlib.sha256(args.extract.read_bytes()).hexdigest(), args.source_date)
