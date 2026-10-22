"""Prepare SRT working-timetable replay with explicitly illustrative dates."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_jakarta_timetable import save
from scripts.prepare_switzerland_geometry import compact_ways

DIRECTORY = ROOT / "data/reference/thailand"
GEOMETRY = DIRECTORY / "srt-tracks-2026-10-22.json.gz"
OUTPUT = DIRECTORY / "2023-04-03.json.gz"
FIRST, LAST = date(2023, 4, 3), date(2023, 4, 9)
CATALOG = "https://datagov.mot.go.th/en/dataset/after32"
RESOURCE = "da06de08-1c8d-4ecd-88f1-67652f65cb95"
API = "https://datagov.mot.go.th/api/3/action/datastore_search?resource_id=" + RESOURCE
OSM_URL = "https://download.geofabrik.de/asia/thailand-latest.osm.pbf"
OSM_SHA256 = "68a665cc5f618f63c6afe5cde011d783c3838ea27b1ebaceb857946626ded939"
PAGES = {"records.json": "ff95ee5b0d45415efd7b24cb8c93ee70d7b9e8cbd51e01b35fb1885ded1e2acd",
    "records-10000.json": "496266b0a110d61dede0bf5944acfa7562bda20ce565753692fc2a08da84c4be",
    "records-20000.json": "54a01f7d87fbf224e16380d96ad624f61079d5009efb4f231d3e03e27d9e9ac8"}
NOTE = ("Approximate period: April 2023. Replay dates are illustrative, based on the SRT spreadsheet publication period; "
        "the timetable's effective dates are unconfirmed and it may describe older workings. "
        "Original working-timetable clocks are retained, including overnight journeys. "
        "Daily operation follows the source origin record, not a verified historical calendar. "
        "Scheduled calls can include operational stops. All source calls are retained; unlocated calls and disconnected tracks stay map gaps. "
        "Inferred railway paths, not live tracking or passenger counts.")


def normalized(value):
    value = value.lower().strip().removeprefix("srt ")
    for a, b in [("railway station", ""), (" station", ""), (" junction", ""), ("(n)", ""), ("(e)", ""),
                 ("khlong", "klong"), ("muang", "mueang"), ("nakorn", "nakhon"), ("sri", "si"),
                 ("yommaraj", "yommarat"), ("don muang", "don mueang")]:
        value = value.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", value)


def clock(value):
    match = re.fullmatch(r"\s*(?:(\d+)\s+)?(\d{1,2}):(\d{2}):(\d{2})\s*", value or "")
    if not match:
        raise ValueError("Invalid SRT day/clock: " + str(value))
    day, hour, minute, second = (int(v or 0) for v in match.groups())
    if hour >= 24 or minute >= 60 or second >= 60:
        raise ValueError("Invalid SRT clock range")
    return day * 86400 + hour * 3600 + minute * 60 + second


def source_rows(cache):
    rows = []
    for name, digest in PAGES.items():
        if file_hash(cache / name) != digest:
            raise ValueError("SRT datastore page changed: " + name)
        page = json.loads((cache / name).read_bytes())
        if not page["success"] or page["result"]["total"] != 21841:
            raise ValueError("Incomplete SRT datastore response")
        rows.extend(page["result"]["records"])
    if len(rows) != 21841 or len({r["_id"] for r in rows}) != 21841:
        raise ValueError("Missing or duplicate SRT rows")
    return rows


def passenger_trips(rows):
    groups = defaultdict(list)
    for row in rows:
        number = str(row["หมายเลขขบวนรถ"])
        # SRT conventional passenger numbering: special/express/rapid,
        # ordinary, suburban and local/mixed passenger services, below 500.
        # Cargo, depot/empty-stock D identifiers and other model runs stay out.
        if number.isdigit() and 0 < int(number) < 500:
            groups[number].append(row)
    result = {}; omitted = {}
    for number, sequence in sorted(groups.items(), key=lambda item: int(item[0])):
        sequence.sort(key=lambda r: r["_id"])
        if sequence[0]["Public Day of Operation"] != "Daily":
            omitted[number] = "Origin operating-day value is not Daily"
            continue
        calls = []
        for index, row in enumerate(sequence):
            if row["Stop type"] != "Scheduled stop" and index not in {0, len(sequence) - 1}:
                continue
            arrival = clock(row["Arrival time"] or row["Departure time"])
            departure = clock(row["Departure time"] or row["Arrival time"])
            calls.append({"name": row["สถานี"], "code": row["อักษรย่อ"], "arrival": arrival,
                          "departure": departure, "source_row": row["_id"], "stop_type": row["Stop type"]})
        flat = [t for call in calls for t in (call["arrival"], call["departure"])]
        if len(calls) < 2 or any(b < a for a, b in zip(flat, flat[1:])):
            omitted[number] = "Incomplete or backwards source clocks"
            continue
        result[number] = calls
    return result, omitted


def prepare_geometry(pbf, output=GEOMETRY):
    import osmium
    if file_hash(pbf) != OSM_SHA256:
        raise ValueError("Thailand railway extract changed; revalidate before updating its pin")
    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}; self.stations = []
        def way(self, way):
            tags = dict(way.tags)
            if (tags.get("railway") == "rail" and tags.get("gauge", "1000") == "1000"
                    and tags.get("service") not in {"yard", "spur"} and tags.get("usage") not in {"industrial", "military", "test"}
                    and tags.get("disused") != "yes" and tags.get("abandoned") != "yes"):
                self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes], "gauge": tags.get("gauge", "")}
        def node(self, node):
            tags = dict(node.tags)
            if tags.get("railway") in {"station", "halt", "stop"}:
                names = list(dict.fromkeys(tags.get(k, "") for k in ["name:en", "name", "alt_name", "official_name", "loc_name"] if tags.get(k)))
                if names:
                    self.stations.append({"osm_node_id": str(node.id), "names": names, "ref": tags.get("ref", ""),
                        "coordinates": [node.location.lon, node.location.lat], "railway": tags["railway"]})
    inventory = Inventory(); inventory.apply_file(str(pbf), filters=[osmium.filter.KeyFilter("railway")])
    needed = {n for w in inventory.ways.values() for n in w["nodes"]}
    class Nodes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.nodes = {}
        def node(self, node):
            self.nodes[str(node.id)] = [node.location.lon, node.location.lat]
    nodes = Nodes(); nodes.apply_file(str(pbf), filters=[osmium.filter.IdFilter(int(n) for n in needed).enable_for(osmium.osm.NODE)])
    complete = {k: w for k, w in inventory.ways.items() if all(n in nodes.nodes for n in w["nodes"])}
    reader = osmium.io.Reader(str(pbf)); header = reader.header(); stamp = header.get("osmosis_replication_timestamp"); reader.close()
    geo = {"metadata": {"source": "© OpenStreetMap contributors via Geofabrik Thailand", "source_url": OSM_URL,
        "source_sha256": file_hash(pbf), "source_date": stamp, "retrieved": "2026-10-22", "license": "ODbL 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/", "omitted_incomplete_ways": len(inventory.ways) - len(complete),
        "note": "Current geographic reference for an illustrative older working timetable; not historical running-track assignments. "
                "Only shared original OSM nodes join tracks. No proximity joins or straight fallback links."},
        "ways": compact_ways(complete, nodes.nodes), "stations": inventory.stations}
    save(geo, output)
    print("SRT graph", len(geo["ways"]), "ways", len(geo["stations"]), "stations", output.stat().st_size, "bytes", flush=True)


def match_stations(trips, geo):
    graph = FranceRailGraph(geo["ways"]); index = defaultdict(list)
    for station in geo["stations"]:
        if not graph.anchors(station["coordinates"]):
            continue
        for name in station["names"]:
            for alias in re.split(r"[;/]", name):
                key = normalized(alias)
                if key:
                    index[key].append(station)
    matches, missing = {}, []
    names = sorted({c["name"] for calls in trips.values() for c in calls})
    for name in names:
        key = normalized(name); candidates = index.get(key, [])
        match_kind = "normalized source/OSM name"
        if not candidates:
            scores = sorted(((difflib.SequenceMatcher(None, key, alias).ratio(), alias) for alias in index), reverse=True)
            if scores and scores[0][0] >= .94:
                score, alias = scores[0]; proposed = index[alias]
                different = next((s for s, other in scores[1:] if any(
                    cumulative_distances([p["coordinates"], q["coordinates"]])[-1] > 500
                    for p in proposed for q in index[other])), 0)
                if score - different >= .05:
                    candidates = proposed
                    match_kind = f"unique spelling variant ({score:.3f})"
            if not candidates:
                missing.append(name)
                continue
        # Multiple platforms/stop positions at one station are equivalent.
        # Same-name stations far apart require explicit resolution instead.
        points = [s["coordinates"] for s in candidates]
        if any(cumulative_distances([points[0], p])[-1] > 500 for p in points[1:]):
            missing.append(name)
            continue
        chosen = min(candidates, key=lambda s: (0 if s["railway"] == "stop" else 1, int(s["osm_node_id"])))
        matches[name] = {**chosen, "match": match_kind}
    return graph, matches, missing


def prepare(cache, output):
    trips, omitted = passenger_trips(source_rows(cache))
    with gzip.open(GEOMETRY, "rt") as stream:
        geo = json.load(stream)
    if geo["metadata"]["source_sha256"] != OSM_SHA256:
        raise ValueError("Unexpected SRT geometry source")
    graph, stations, missing = match_stations(trips, geo)
    print("SRT station matches", len(stations), "missing", missing, flush=True)
    audit = {"candidate_trips": len(trips), "missing_stations": missing, "stations": stations}
    (cache / "station-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(FIRST + timedelta(days=i)): [] for i in range(7)}, "train_numbers": {}}
    station_ids = {}; gaps = []; path_cache = {}
    def corridor(calls):
        names = " ".join(c["name"].lower() for c in calls)
        for label, terms in [("Northeastern", ["ubon", "nong khai", "khon kaen", "bua yai", "nakhon ratchasima", "kaeng khoi"]),
                ("Northern", ["chiang mai", "phitsanulok", "den chai", "sila at", "lop buri", "nakhon sawan", "taphan hin", "ban takhli"]),
                ("Western", ["nam tok", "suphan buri"]),
                ("Southern", ["surat", "hat yai", "sungai", "chumphon", "ratchaburi", "nakhon pathom", "lang suan", "thon buri"]),
                ("Eastern", ["chachoengsao", "pattaya", "prachin", "hua takhe", "kabin buri", "plu ta luang", "klong luang phaeng"])]:
            if any(term in names for term in terms):
                return label
        return "Bangkok suburban"
    for number, calls in trips.items():
        ids = []; legs = []; start = calls[0]["arrival"]
        for call in calls:
            name = call["name"]
            if name not in station_ids:
                station_ids[name] = len(result["stations"]); point = stations.get(name, {}).get("coordinates", [None, None])
                result["stations"].append({"name": name, "lon": point[0], "lat": point[1], "mode": "train"})
            ids.append(station_ids[name])
        for a, b in zip(calls, calls[1:]):
            pair = (a["name"], b["name"])
            if pair not in path_cache:
                curve = None
                if all(n in stations for n in pair):
                    points = [stations[n]["coordinates"] for n in pair]
                    curve = graph.leg(*points)
                    if curve and cumulative_distances(curve)[-1] > max(5000, 3 * cumulative_distances(points)[-1]):
                        curve = None
                key = "srt-" + hashlib.sha256(json.dumps(pair).encode()).hexdigest()[:20]
                result["paths"][key] = {"coordinates": curve or [], "distances": cumulative_distances(curve) if curve else [],
                                         "quality": "track" if curve else "approximate"}
                if not curve:
                    gaps.append(list(pair))
                path_cache[pair] = key
            legs.append(path_cache[pair])
        pattern = {"mode": "train", "operator": "State Railway of Thailand", "route_id": "SRT-" + corridor(calls).lower().replace(" ", "-"),
            "line": "SRT " + corridor(calls), "color": "#B22222", "direction": "Not specified",
            "origin": calls[0]["name"], "destination": calls[-1]["name"], "working_timetable": True,
            "stops": [[identifier, c["arrival"] - start, c["departure"] - start] for identifier, c in zip(ids, calls)], "legs": legs}
        key = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]; result["patterns"][key] = pattern
        # After-midnight departures belong once to the preceding business day;
        # explicit source day offsets remain unchanged inside their journeys.
        offset = start - ((calls[0]["departure"] - 10800) // 86400) * 86400
        for rows in result["days"].values():
            rows.append([key, number, offset])
        result["train_numbers"][number] = number
    for rows in result["days"].values():
        rows.sort(key=lambda row: (row[2], int(row[1])))
    metadata = {"start_date": str(FIRST), "end_date": str(LAST), "timezone": "Asia/Bangkok",
        "source": "State Railway of Thailand working timetable via Ministry of Transport datastore",
        "source_url": CATALOG, "source_date": "Undated working timetable; resource published 5 April 2023; retrieved 22 October 2026",
        "sources": [{"source_url": API + "&offset=" + str(i * 10000) + "&limit=10000", "sha256": digest,
                      "resource_created": "2023-04-05", "retrieved": "2026-10-22"} for i, digest in enumerate(PAGES.values())],
        "license": "Ministry catalogue: Open Data Common / Creative Commons Attributions (version unspecified); source rights retained",
        "license_url": CATALOG, "attribution": "Working timetable: State Railway of Thailand via Ministry of Transport, Thailand. "
            "Source clocks retained; SunTrain passenger-number selection, shared schedule conversion and illustrative April 2023 replay dates. "
            "Railway geography and station locations © OpenStreetMap contributors, ODbL 1.0; spelling variants matched by SunTrain. "
            "SRT display colour follows the separately licensed OTP / Namtang rail palette (CC BY 4.0).",
        "replay_note": NOTE, "illustrative_dates": True, "approximate_period": "April 2023", "effective_dates_confirmed": False,
        "source_calendar": "Daily at each selected source origin; not a verified historical operating calendar",
        "geometry_source": geo["metadata"]["source"], "geometry_source_url": OSM_URL,
        "geometry_license": "ODbL 1.0", "geometry_license_url": geo["metadata"]["license_url"],
        "geometry_source_date": geo["metadata"]["source_date"], "geometry_sha256": file_hash(GEOMETRY),
        "omitted_trips": omitted, "unresolved_geometry_patterns": {"Unlocated calls / disconnected railway": len(gaps)},
        "unresolved_geometry_trips": {n: True for n, calls in trips.items() if any(
            [a["name"], b["name"]] in gaps for a, b in zip(calls, calls[1:]))},
        "unresolved_stop_pairs": gaps, "unlocated_stations": missing, "station_position_matches": stations,
        "source_call_rows": {n: [c["source_row"] for c in calls] for n, calls in trips.items()},
        "scope": "Numeric conventional passenger services 1–499; depot, cargo and other model identifiers excluded",
        "daily_services": {d: dict(Counter(result["patterns"][p]["line"] for p, _, _ in rows)) for d, rows in result["days"].items()}}
    result["metadata"] = metadata; save_reference(result, output)
    print("SRT journeys/day", len(trips), "omissions", omitted, "unresolved pairs", len(gaps), "bytes", output.stat().st_size, flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/thailand/srt")
    parser.add_argument("--prepare-geometry", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.prepare_geometry:
        prepare_geometry(args.prepare_geometry)
    else:
        prepare(args.cache, args.output)
