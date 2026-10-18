"""Prepare DB InfraGO's connected passenger railway alignment (offline only)."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_replay_geometry import simplify

BASE_URL = "https://geoviewer.deutschebahn.com/geoviewer-geoserver/ows"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
OUTPUT = ROOT / "data/reference/germany/db-rail-2026-10-18.json.gz"


def prepare(cache, output=OUTPUT):
    # The timetable is historical; this geographic reference was accessed in
    # October. Native DB junction IDs, rather than nearby coordinates, connect
    # railway links. Cargo-only links and fictitious lines are excluded.
    passenger = {}
    sources = []
    for name in ("TN.RailwayLinkMixed", "TN.RailwayLinkPassengers"):
        filename = cache / ("db-" + name + ".json")
        data = json.loads(filename.read_text())
        if data["numberReturned"] != data["numberMatched"]:
            raise ValueError("Incomplete passenger railway attribute download")
        for feature in data["features"]:
            p = feature["properties"]
            if p["RAILTYPE"] == "train" and str(p["FICT"]).lower() == "false":
                passenger[p["LINKID"].split(".")[-1]] = p
        sources.append({"file": filename.name, "sha256": file_hash(filename), "typeNames": "DBInspire:" + name})
    features, ids = [], set()
    for filename in sorted(cache.glob("db-topology-*.json"), key=lambda p: int(p.stem.rsplit("-", 1)[1])):
        data = json.loads(filename.read_text())
        for feature in data["features"]:
            key = feature["properties"]["inspireId"]["localId"]
            if key in ids:
                raise ValueError("Duplicate DB railway link in paginated download")
            ids.add(key)
            features.append(feature)
        sources.append({"file": filename.name, "sha256": file_hash(filename), "typeNames": "tn-ra:RailwayLink",
                        "startIndex": int(filename.stem.rsplit("-", 1)[1]), "count": 5000})
    if len(ids) != data["numberMatched"] or not passenger.keys() <= ids:
        raise ValueError("Incomplete DB railway topology")
    junctions = {}
    for name, kind in (("db-nodes.json", "RailwayNode"), ("db-station-nodes.json", "RailwayStationNode")):
        filename = cache / name
        nodes = json.loads(filename.read_text())
        if nodes["numberReturned"] != nodes["numberMatched"]:
            raise ValueError("Incomplete DB junction positions")
        for feature in nodes["features"]:
            if feature["geometry"] and feature["geometry"]["type"] == "Point":
                junctions["#" + feature["properties"]["inspireId"]["localId"]] = feature["geometry"]["coordinates"]
        sources.append({"file": name, "sha256": file_hash(filename), "typeNames": "tn-ra:" + kind})
    ways, max_error, excluded = [], 0, Counter()
    for feature in features:
        p = feature["properties"]
        key = p["inspireId"]["localId"]
        if key not in passenger or p.get("fictitious") is not False:
            continue
        attr = passenger[key]
        if not feature["geometry"]:
            excluded["missing_geometry"] += 1
            continue
        points = feature["geometry"]["coordinates"]
        if feature["geometry"]["type"] != "LineString" or len(points) < 2:
            raise ValueError("Unexpected DB link geometry")
        points = simplify(points)
        start, end = p["startNode"]["@href"], p["endNode"]["@href"]
        if start not in junctions or end not in junctions:
            excluded["missing_junction"] += 1
            continue
        # Geometry order need not follow the startNode/endNode attributes.
        if cumulative_distances([points[-1], junctions[start]])[-1] < cumulative_distances([points[0], junctions[start]])[-1]:
            points.reverse()
        errors = [cumulative_distances([junctions[node], points[i]])[-1] for i, node in ((0, start), (-1, end))]
        # DB centreline geometry and junction points have small generalisation
        # differences. Use only the same published junction ID within 50 m;
        # incomplete or contradictory links never get a synthetic connector.
        if max(errors) > 50:
            excluded["junction_mismatch_over_50m"] += 1
            continue
        max_error = max(max_error, *errors)
        for i, node in ((0, start), (-1, end)):
            points[i] = junctions[node]
        ways.append({"id": key, "line": attr["LINECODE"], "name": attr["LINENAME"],
                     "speed": max(20, min(350, float(attr.get("SPEED") or 80))),
                     "node_ids": [start, *[key + ":" + str(i) for i in range(1, len(points) - 1)], end],
                     "coordinates": points})
    result = {"metadata": {"source": "DB InfraGO AG · INSPIRE railway links and junctions",
        "source_url": BASE_URL, "source_date": "2026-10-18", "license": "CC BY 4.0", "license_url": LICENSE_URL,
        "license_metadata_url": "https://www.govdata.de/suche/daten/wms-schienenverkehrsnetz-db-infrago",
        "downloads": sources, "max_junction_adjustment_m": max_error, "excluded_links": dict(excluded),
        "note": "Geographic railway alignment accessed October 2026 for June schedules. Passenger/mixed-use links join only at published DB node IDs. No assertion of exact historical running tracks."}, "ways": ways}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file, gzip.GzipFile(filename="", fileobj=file, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":"), allow_nan=False).encode())
    print({"ways": len(ways), "junctions": len(junctions), "max_junction_adjustment_m": max_error,
           "bytes": output.stat().st_size}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/germany")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    prepare(args.cache, args.output)
