"""Prepare dated national Shinkansen schedules in SunTrain's shared format."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import heapq
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_boston_replay import fetch
from scripts.prepare_france_replay import FranceRailGraph

REVISION = "2e0cd13e5a60dd01238dc4f6ebf41a967eb85d96"
BASE_URL = f"https://raw.githubusercontent.com/manavya-des/shinkansen-live-open/{REVISION}/"
SOURCES = {
    "timetable": ("timetable/data.json", "73ed3276be89dc846237fe1dd588d3606fedee557c7983bbc0e20fa6bba1dcaa"),
}
DAY = "2026-03-10"
CATALOG = ROOT / "data/sources/japan_shinkansen_stations.json"
GEOMETRY = ROOT / "data/reference/japan/shinkansen-tracks-2026-10-21.json.gz"
GEOMETRY_SHA256 = "05fc1fc57f4b43c9267a81c31af1f948d505191a2abd6f0235356128703d6c68"
FAMILIES = {
    "601": ("tokaido", "sanyo", "kyushu"), "901": ("tokaido", "sanyo", "kyushu"),
    "101": ("tohoku", "hokkaido"), "201": ("tohoku", "yamagata"),
    "301": ("tohoku", "akita"), "401": ("tohoku", "joetsu", "gala-yuzawa"),
    "501": ("tohoku", "joetsu", "hokuriku"), "1101": ("nishi-kyushu",),
}
OWNERS = {"tokaido": "JR Central", "sanyo": "JR West", "kyushu": "JR Kyushu",
          "nishi-kyushu": "JR Kyushu", "tohoku": "JR East", "joetsu": "JR East",
          "gala-yuzawa": "JR East", "hokuriku": "JR East / JR West", "hokkaido": "JR Hokkaido",
          "akita": "JR East", "yamagata": "JR East"}
NOTE = ("Shinkansen uses a community timetable dated 10 March 2026, with mapped railway paths. "
        "Undated extra services are excluded. The optional limited-express layer reuses the Tokyo source "
        "from 20 October 2026, matched by weekday, and covers JR East sections only. "
        "Nationwide conventional limited-express and overnight coverage is incomplete. "
        "Japan local time; scheduled estimates, no live positions or passenger loads.")


def clock_pair(value):
    """Keep only printed arrival/departure clocks, never infer pass times."""
    value = value.strip().replace("\\n", "\n")
    if value in {"", "↓", "↑", "レ", "―", "－"}:
        return None
    clocks = value.split()
    if len(clocks) not in {1, 2} or any(not re.fullmatch(r"\d{1,2}:\d{2}", s) for s in clocks):
        raise ValueError("Unrecognised station time")
    times = []
    for stamp in clocks:
        hour, minute = map(int, stamp.split(":"))
        if hour > 47 or minute > 59:
            raise ValueError("Invalid station clock")
        times.append(3600 * hour + 60 * minute)
    return times[0], times[-1]


def scheduled_on(train, day):
    if train.get("caution"):
        return False
    calendar = train.get("serviceDay", "")
    return calendar == "毎日" or calendar == "平日" and day.weekday() < 5


def timetable_trips(data):
    if data["date"] != DAY:
        raise ValueError("Unexpected Shinkansen source date")
    trips, omissions = {}, Counter()
    for line in data["lines"]:
        if line["lineId"] not in FAMILIES:
            raise ValueError("Unreviewed Shinkansen line")
        for direction in line["directions"]:
            for index, train in enumerate(direction["trains"]):
                if not scheduled_on(train, date.fromisoformat(DAY)):
                    omissions["Undated or conditional extra service"] += 1
                    continue
                try:
                    calls = []
                    for station in direction["stations"]:
                        pair = clock_pair(station["times"][index])
                        if pair:
                            calls.append((station["stationName"], *pair))
                    if len(calls) < 2:
                        raise ValueError("Fewer than two printed station clocks")
                    times = [t for _, a, d in calls for t in (a, d)]
                    if any(b < a for a, b in zip(times, times[1:])):
                        raise ValueError("Backwards printed times")
                    identity = (train["name"], train["number"], direction["directionId"])
                    if identity not in trips:
                        trips[identity] = {"name": train["name"], "number": train["number"].removesuffix("号"),
                            "direction": direction["directionId"], "calls": {}, "features": set()}
                    trip = trips[identity]
                    for station, arrival, departure in calls:
                        if station in trip["calls"] and trip["calls"][station] != (arrival, departure):
                            raise RuntimeError("Conflicting cross-line duplicate; review the source before preparing")
                    trip["calls"].update({s: (a, d) for s, a, d in calls})
                    trip["features"].update(FAMILIES[line["lineId"]])
                except (ValueError, IndexError) as error:
                    omissions[str(error)] += 1
    return trips, omissions


class ShinkansenPaths:
    """Route only along the source's operating corridors and explicit stations."""
    def __init__(self, geometry, catalog):
        self.catalog = {s["id"]: s for stops in catalog.values() for s in stops}
        self.graph = defaultdict(list)
        self.cache = {}
        self.audit = Counter()
        self.unresolved = []
        for feature, stops in catalog.items():
            physical = FranceRailGraph(geometry["lines"][feature])
            distance = lambda a, b: cumulative_distances([a, b])[-1]
            for index, (a, b) in enumerate(zip(stops, stops[1:])):
                curve = physical.leg(a["coordinate"], b["coordinate"])
                length = cumulative_distances(curve)[-1] if curve else distance(a["coordinate"], b["coordinate"])
                self.audit["mapped" if curve else "unresolved"] += 1
                if not curve:
                    self.unresolved.append({"corridor": feature, "from": a["id"], "to": b["id"]})
                owner = OWNERS[feature]
                if feature == "hokuriku":
                    boundary = next(i for i, s in enumerate(stops) if s["id"] == "上越妙高")
                    owner = "JR East" if index < boundary else "JR West"
                self.graph[a["id"]].append((b["id"], feature, length, curve, owner))
                self.graph[b["id"]].append((a["id"], feature, length, curve[::-1] if curve else None, owner))

    def leg(self, first, last, features):
        key = first, last, tuple(sorted(features))
        if key in self.cache:
            return self.cache[key]
        queue, best, previous = [(0, first)], {first: 0}, {}
        while queue:
            length, node = heapq.heappop(queue)
            if length != best[node]:
                continue
            if node == last:
                break
            for target, feature, weight, curve, owner in self.graph[node]:
                candidate = length + weight
                if feature in features and candidate < best.get(target, float("inf")):
                    best[target] = candidate
                    previous[target] = node, feature, curve, owner
                    heapq.heappush(queue, (candidate, target))
        if last not in best:
            raise ValueError("Station pair is outside the selected railway corridors")
        sections, used, owners, node = [], set(), set(), last
        while node != first:
            node, feature, curve, owner = previous[node]
            sections.append(curve)
            used.add(feature)
            owners.add(owner)
        curve = None if any(s is None for s in sections) else [point for s in sections[::-1] for point in s]
        self.cache[key] = curve, used, owners
        return curve, used, owners


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for name, (path, digest) in SOURCES.items():
        filename = fetch(BASE_URL + path, cache / (name + ".json"))
        if file_hash(filename) != digest:
            raise ValueError("Japan source differs from its validated pin")
        inputs[name] = json.loads(filename.read_text())
    if file_hash(GEOMETRY) != GEOMETRY_SHA256:
        raise ValueError("Japan railway graph differs from its validated pin")
    with gzip.open(GEOMETRY, "rt") as stream:
        geometry = json.load(stream)
    catalog = json.loads(CATALOG.read_text())
    graph = ShinkansenPaths(geometry, catalog)
    trips, omissions = timetable_trips(inputs["timetable"])
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {DAY: []}, "train_numbers": {}}
    station_ids, coverage = {}, Counter()
    for identity, trip in sorted(trips.items()):
        calls = sorted(((s, *times) for s, times in trip["calls"].items()), key=lambda r: (r[1], r[2]))
        ids, legs, used, owners = [], [], set(), set()
        for station, _, _ in calls:
            if station not in station_ids:
                record = graph.catalog[station]
                station_ids[station] = len(result["stations"])
                result["stations"].append({"name": station + " " + record["name"],
                    "lon": record["coordinate"][0], "lat": record["coordinate"][1], "mode": "train"})
            ids.append(station_ids[station])
        for a, b in zip(calls, calls[1:]):
            curve, features, operators = graph.leg(a[0], b[0], trip["features"])
            used.update(features)
            owners.update(operators)
            key = "jp-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
            result["paths"][key] = {"coordinates": curve or [], "distances": cumulative_distances(curve or []),
                                     "quality": "track" if curve else "approximate"}
            legs.append(key)
            coverage["mapped" if curve else "unresolved"] += 1
        owners = sorted(owners)
        origin = calls[0][1]
        pattern = {"mode": "train", "operator": " / ".join(owners), "line": trip["name"],
            "route_id": "jp-shinkansen:" + trip["name"], "route_short_name": trip["name"], "category": "Shinkansen",
            "source_route_id": "jp-shinkansen:" + trip["name"],
            "color": {"Nozomi": "#F28C28", "Hikari": "#F28C28", "Kodama": "#0072CE",
                      "Mizuho": "#0072CE", "Sakura": "#D81B60", "Tsubame": "#D81B60",
                      "Hayabusa": "#009A62", "Hayate": "#009A62", "Yamabiko": "#009A62", "Nasuno": "#009A62",
                      "Komachi": "#EC407A", "Tsubasa": "#8E24AA", "Toki": "#EF5350", "Tanigawa": "#EF5350",
                      "Kagayaki": "#3F51B5", "Hakutaka": "#3F51B5", "Asama": "#3F51B5", "Tsurugi": "#3F51B5",
                      "Kamome": "#FF7043"}[trip["name"]],
            "direction": "Direction " + ("A" if trip["direction"] == "0" else "B"),
            "origin": result["stations"][ids[0]]["name"], "destination": result["stations"][ids[-1]]["name"],
            "stops": [[s, a - origin, d - origin] for s, (_, a, d) in zip(ids, calls)], "legs": legs,
            "railway_corridors": sorted(used)}
        key = "jp-" + hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
        trip_id = ":".join(identity)
        result["patterns"][key] = pattern
        result["days"][DAY].append([key, trip_id, origin])
        result["train_numbers"][trip_id] = trip["name"] + " " + trip["number"]
    result["days"][DAY].sort(key=lambda r: (r[2], r[1]))
    result["metadata"] = {"start_date": DAY, "end_date": DAY, "timezone": "Asia/Tokyo",
        "source": "Shinkansen Live community timetable, dated 10 March 2026",
        "source_url": f"https://github.com/manavya-des/shinkansen-live-open/tree/{REVISION}",
        "license": "MIT (community timetable); operator rights retained",
        "license_url": BASE_URL + "LICENSE",
        "attribution": "Community timetable: Copyright (c) 2026 Shinkansen Live Contributors. "
                       "Railway geometry © OpenStreetMap contributors, ODbL 1.0. Selected, deduplicated, mapped and compacted by SunTrain.",
        "geometry_source": "Connected operating railway ways © OpenStreetMap contributors, matched by SunTrain",
        "geometry_source_url": "https://www.openstreetmap.org/copyright",
        "geometry_license": "ODbL 1.0", "geometry_license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "geometry_source_date": "2026-10-21", "geometry_sha256": GEOMETRY_SHA256,
        "geometry_references": geometry["metadata"]["sources"],
        "sources": [{"source_url": BASE_URL + path, "source_date": "2026-10-21", "published": "2026-03-11", "sha256": digest}
                    for path, digest in SOURCES.values()],
        "station_catalog_sha256": file_hash(CATALOG), "replay_note": NOTE,
        "daily_services": {DAY: dict(Counter(result["patterns"][k]["line"] for k, _, _ in result["days"][DAY]))},
        "omitted_source_rows": dict(omissions), "geometry_legs": dict(coverage), "geometry_station_sections": dict(graph.audit),
        "unresolved_station_sections": graph.unresolved,
        "note": "Printed stop times only. Undated optional trains and planned railways are excluded. Schedule estimates, not GPS."}
    save_reference(result, output)
    print(f"Saved {output}: {len(result['days'][DAY])} services, geometry {dict(coverage)}, omissions {dict(omissions)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/japan")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/japan/2026-03-10.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
