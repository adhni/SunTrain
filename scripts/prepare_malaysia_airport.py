"""Convert ERL's dated airport timetables and directional OSM rail relations.

PDF and PBF tooling is preparation-only. Runtime reads shared compact patterns.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import compact_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_jakarta_timetable import extended_times, save
from scripts.prepare_kuala_lumpur_replay import FIRST, LAST, GEOMETRY_URL, TRACK_PIN
from scripts.prepare_switzerland_geometry import compact_ways

DIRECTORY = ROOT / "data/reference/kuala_lumpur"
SOURCE = DIRECTORY / "erl-timetable-2026-03-21.json.gz"
GEOMETRY = DIRECTORY / "erl-tracks-2026-10-22.json.gz"
PINS = {SOURCE: "9f0a43b9aa0f95f5a95710b1ff80fc8a96902bcbed2b7930bc4f468927a38f23",
        GEOMETRY: "363a9c8e628b07bc4d37584f0428ad84774892f5b8885bc36963863c1f578582"}
PDFS = {
    "ekspres": ("https://www.kliaekspres.com/media/14uietk1/train-schedule-08-dec-25-onwards-ke.pdf",
                "58f2e5677526177551a5e8d0e7bd955424d5de78526cc4e3515159d319a296df", "8 December 2025"),
    "transit": ("https://www.kliaekspres.com/media/rojb45mf/kt-train-schedule_effective-21-mar-2026.pdf",
                "0fa011a6eb757bd8e4524a4ba2569af05958041bbcb48e66d0ac5e9d7cdea452", "21 March 2026"),
}
NAMES = {"KL": "KL Sentral", "BTS": "Bandar Tasik Selatan", "PC": "Putrajaya & Cyberjaya",
         "ST": "Salak Tinggi", "T1": "KLIA T1", "T2": "KLIA T2"}
RELATIONS = {"transit:in": 2082100, "transit:out": 8119876,
             "ekspres:out": 8119878, "ekspres:in": 8119879}
COLORS = {"ekspres": "#800080", "transit": "#139593"}  # OSM route colours, credited separately.
NOTE = ("ERL airport trains use published departures from the December 2025 Ekspres and March 2026 Transit tables. "
        "Combined late-night services appear once under KLIA Transit. Intermediate station events use printed times; "
        "separate arrivals and dwell are not supplied. Map movement is interpolated, not live tracking.")


def station_codes(kind, direction):
    codes = list(NAMES) if kind == "transit" else ["KL", "T1", "T2"]
    return codes if direction == "out" else codes[::-1]


def parse_table(table, kind, calendar):
    """Keep the PDF's blank cells and station columns; never generate headways."""
    size = 6 if kind == "transit" else 3
    trips = []
    for row in table:
        if not any(re.fullmatch(r"\d{2}:\d{2}", str(cell or "").strip()) for cell in row):
            continue  # Only heading rows lack clock cells.
        if len(row) != size * 2 + 1 or row[size] not in {None, ""}:
            raise ValueError("Unexpected ERL timetable columns")
        for direction, cells in [("out", row[:size]), ("in", row[size + 1:])]:
            calls = [(code, str(cell or "").strip()) for code, cell in zip(station_codes(kind, direction), cells)]
            calls = [(code, value) for code, value in calls if value not in {"", "-"}]
            if not calls:
                continue
            if len(calls) < 2 or any(not re.fullmatch(r"\d{2}:\d{2}", value) for _, value in calls):
                raise ValueError("Invalid ERL station cell")
            times = extended_times([value for _, value in calls])
            # Midnight departures belong to the preceding 03:00 business day.
            shift = 86400 if times[0] < 10800 else 0
            times = [t + shift for t in times]
            if any(b <= a for a, b in zip(times, times[1:])) or times[-1] - times[0] > 3600:
                raise ValueError("Backwards or implausible ERL journey")
            trips.append({"kind": kind, "direction": direction, "calendar": calendar,
                          "calls": [[code, t] for (code, _), t in zip(calls, times)]})
    if not trips:
        raise ValueError("Empty ERL timetable")
    return trips


def remove_combined_duplicates(ekspres, transit):
    """Grey Ekspres rows describe the same all-stops trains in Transit tables."""
    kept, combined = [], []
    for trip in ekspres:
        if trip["calls"][-1][1] - trip["calls"][0][1] <= 33 * 60:
            kept.append(trip)
            continue
        for calendar in ["weekday", "weekend"]:
            matches = [t for t in transit if t["calendar"] == calendar and t["direction"] == trip["direction"]
                       and [call for call in t["calls"] if call[0] in {"KL", "T1", "T2"}] == trip["calls"]]
            if len(matches) != 1:
                raise ValueError("Combined ERL service does not match exactly one Transit row")
        combined.append(trip)
    if len(combined) != 10:
        raise ValueError("Unexpected count of combined late-night rows")
    return kept, combined


def extract_pdf(cache):
    import pdfplumber
    groups = {}
    for kind, (_, digest, edition) in PDFS.items():
        filename = cache / (kind + ".pdf")
        if file_hash(filename) != digest:
            raise ValueError("Official ERL PDF edition changed: " + kind)
        with pdfplumber.open(filename) as doc:
            if len(doc.pages) != (1 if kind == "ekspres" else 2):
                raise ValueError("Unexpected ERL PDF page count")
            groups[kind] = []
            for index, page in enumerate(doc.pages):
                text = page.extract_text()
                if "Effective " + edition not in text:
                    raise ValueError("Unexpected ERL effective date")
                calendar = "daily" if kind == "ekspres" else "weekday" if index == 0 else "weekend"
                if calendar == "weekday" and "Monday - Friday" not in text:
                    raise ValueError("Missing weekday calendar")
                if calendar == "weekend" and "Saturday - Sunday" not in text:
                    raise ValueError("Missing weekend calendar")
                groups[kind].extend(parse_table(page.extract_tables()[-1], kind, calendar))
    ekspres, combined = remove_combined_duplicates(groups["ekspres"], groups["transit"])
    save({"metadata": {"source": "Express Rail Link Sdn Bhd official departure tables", "note": NOTE,
           "schedule_page": "https://www.kliaekspres.com/schedule", "retrieved": "2026-10-22",
           "sources": [{"source_url": url, "sha256": digest, "effective": edition} for url, digest, edition in PDFS.values()],
           "combined_ekspres_rows_stored_under_transit": combined}, "trips": ekspres + groups["transit"]}, SOURCE)
    print("ERL parsed rows", dict(Counter((t["kind"], t["calendar"]) for t in ekspres + groups["transit"])), flush=True)


def prepare_geometry(pbf):
    import osmium
    if file_hash(pbf) != TRACK_PIN:
        raise ValueError("ERL railway extract differs from the validated pin")

    class Routes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.routes = {}
        def relation(self, relation):
            tags = dict(relation.tags)
            if tags.get("route") != "train" or tags.get("operator") != "Express Rail Link":
                raise ValueError("ERL route identity changed")
            self.routes[str(relation.id)] = {"stops": [str(m.ref) for m in relation.members if m.type == "n" and m.role == "stop"],
                "ways": [str(m.ref) for m in relation.members if m.type == "w"], "tags": tags}
    routes = Routes()
    routes.apply_file(str(pbf), filters=[osmium.filter.IdFilter(RELATIONS.values()).enable_for(osmium.osm.RELATION)])
    if set(routes.routes) != {str(v) for v in RELATIONS.values()}:
        raise ValueError("Missing ERL route relation")
    wanted = {n for r in routes.routes.values() for n in r["ways"]}

    class Ways(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}
        def way(self, way):
            tags = dict(way.tags)
            if tags.get("railway") != "rail" or tags.get("gauge", "1435") != "1435":
                raise ValueError("Non-ERL track in airport relation")
            self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes], "gauge": "1435"}
    ways = Ways()
    ways.apply_file(str(pbf), filters=[osmium.filter.IdFilter(int(n) for n in wanted).enable_for(osmium.osm.WAY)])
    if set(ways.ways) != wanted:
        raise ValueError("Missing ERL railway ways")
    wanted = {n for w in ways.ways.values() for n in w["nodes"]} | {n for r in routes.routes.values() for n in r["stops"]}

    class Nodes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.nodes = {}; self.names = {}
        def node(self, node):
            key = str(node.id); self.nodes[key] = [node.location.lon, node.location.lat]
            self.names[key] = node.tags.get("name", "")
    nodes = Nodes()
    nodes.apply_file(str(pbf), filters=[osmium.filter.IdFilter(int(n) for n in wanted).enable_for(osmium.osm.NODE)])
    if set(nodes.nodes) != wanted:
        raise ValueError("Missing ERL track nodes")
    directions = {}
    for key, identifier in RELATIONS.items():
        kind, direction = key.split(":"); route = routes.routes[str(identifier)]; codes = station_codes(kind, direction)
        if len(codes) != len(route["stops"]):
            raise ValueError("ERL station sequence changed")
        stations = {code: {"name": NAMES[code], "coordinates": nodes.nodes[n], "osm_node_id": n,
                           "osm_name": nodes.names[n]} for code, n in zip(codes, route["stops"])}
        directions[key] = {"stations": stations, "relation_id": identifier,
            "ways": compact_ways({n: ways.ways[n] for n in route["ways"]}, nodes.nodes)}
    save({"metadata": {"source": "© OpenStreetMap contributors; directional Express Rail Link route relations",
         "source_url": GEOMETRY_URL, "source_sha256": TRACK_PIN, "source_date": "2026-10-21T01:16:18Z",
         "license": "ODbL 1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/"}, "directions": directions}, GEOMETRY)
    print("ERL geometry bytes", GEOMETRY.stat().st_size, flush=True)


def build():
    for filename, digest in PINS.items():
        if file_hash(filename) != digest:
            raise ValueError("Validated ERL reference changed: " + str(filename))
    with gzip.open(SOURCE, "rt") as stream:
        source = json.load(stream)
    with gzip.open(GEOMETRY, "rt") as stream:
        geo = json.load(stream)
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {str(FIRST + timedelta(days=i)): [] for i in range(7)}}
    ids = {}; graphs = {key: FranceRailGraph(value["ways"]) for key, value in geo["directions"].items()}
    for trip in source["trips"]:
        kind, direction, calls = trip["kind"], trip["direction"], trip["calls"]
        route = kind + ":" + direction; stations = geo["directions"][route]["stations"]; start = calls[0][1]; legs = []
        for code, _ in calls:
            if (route, code) not in ids:
                ids[route, code] = len(result["stations"]); point = stations[code]["coordinates"]
                result["stations"].append({"name": NAMES[code], "lon": point[0], "lat": point[1], "mode": "train"})
        for (a, _), (b, _) in zip(calls, calls[1:]):
            key = route + ":" + a + ":" + b
            if key not in result["paths"]:
                points = [stations[c]["coordinates"] for c in [a, b]]; curve = graphs[route].leg(*points)
                if not curve or cumulative_distances(curve)[-1] > 3 * cumulative_distances(points)[-1]:
                    raise ValueError("Missing or implausible ERL railway path: " + key)
                result["paths"][key] = {"coordinates": curve, "distances": cumulative_distances(curve), "quality": "track"}
            legs.append(key)
        pattern = {"mode": "airport_rail", "operator": "Express Rail Link", "line": "KLIA " + kind.title(),
            "route_id": "KE" if kind == "ekspres" else "KT", "color": COLORS[kind],
            "direction": "To airport" if direction == "out" else "To KL Sentral", "origin": NAMES[calls[0][0]],
            "destination": NAMES[calls[-1][0]], "stops": [[ids[route, c], t - start, t - start] for c, t in calls], "legs": legs}
        key = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]; result["patterns"][key] = pattern
        trip_id = route + ":" + str(start)
        for day, rows in result["days"].items():
            weekday = date.fromisoformat(day).weekday() < 5
            if trip["calendar"] == "daily" or (trip["calendar"] == "weekday") == weekday:
                rows.append([key, trip_id, start])
    for rows in result["days"].values():
        rows.sort(key=lambda row: (row[2], row[1]))
        if len(rows) != len({(t, o) for _, t, o in rows}):
            raise ValueError("Duplicate ERL departure")
    result["metadata"] = {**source["metadata"], "start_date": str(FIRST), "end_date": str(LAST), "timezone": "Asia/Kuala_Lumpur",
        "source_url": "https://www.kliaekspres.com/schedule", "source_date": "2025-12-08 / 2026-03-21; retrieved 2026-10-22",
        "license": "Published ERL timetable facts; operator rights retained", "license_url": "https://www.kliaekspres.com/schedule",
        "attribution": "Timetable facts: Express Rail Link Sdn Bhd, official dated publications; operator rights retained. "
            "SunTrain table conversion. Railway geometry, station positions and route colours © OpenStreetMap contributors, ODbL 1.0.",
        "geometry_source": geo["metadata"]["source"], "geometry_source_url": GEOMETRY_URL,
        "geometry_license": geo["metadata"]["license"], "geometry_license_url": geo["metadata"]["license_url"],
        "geometry_sha256": file_hash(GEOMETRY), "timetable_sha256": file_hash(SOURCE),
        "replay_note": NOTE, "omitted_trips": {}, "unresolved_geometry_patterns": {}, "unresolved_geometry_trips": {},
        "calendar_basis": "Official weekday/weekend tables applied to 12–18 October 2026 (no national public holiday). "
            "Temporary 2–4 October all-stops notice is outside this week; disruptions are not replayed."}
    return compact_reference(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-pdf", action="store_true")
    parser.add_argument("--prepare-geometry", action="store_true")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/malaysia-airport")
    parser.add_argument("--pbf", type=Path, default=ROOT / ".cache/kuala-lumpur/malaysia.osm.pbf")
    args = parser.parse_args()
    if args.extract_pdf:
        extract_pdf(args.cache)
    elif args.prepare_geometry:
        prepare_geometry(args.pbf)
    else:
        print({d: len(rows) for d, rows in build()["days"].items()})
