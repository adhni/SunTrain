"""Prepare one week of KL commuter/urban rail from pinned official GTFS.

KTM keeps published individual departures. Rapid KL keeps explicitly labelled
frequency estimates; neither the app nor the browser downloads source feeds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import merge_references, save_reference
from scripts.prepare_australian_replay import file_hash, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_jakarta_busway import frequency_departures
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.prepare_switzerland_geometry import compact_ways
from scripts.prepare_transit_replay import active_services, seconds

FIRST, LAST = date(2026, 10, 12), date(2026, 10, 18)
KTMB_URL = "https://api.data.gov.my/gtfs-static/ktmb"
RAPID_URL = "https://api.data.gov.my/gtfs-static/prasarana?category=rapid-rail-kl"
PINS = {"ktmb": "4a6e2a3b0640078f6dec0aa17f9fc8ca9e89960f2c780c794af63c6117d93e5f",
        "rapid-rail": "3b00cf0debb428a3533f67c29f9c3c87e09ba9735c05569368a033c9a4491614"}
GEOMETRY = ROOT / "data/reference/kuala_lumpur/ktm-tracks-2026-10-22.json.gz"
TRACK_PIN = "1abfb77758d28dea24ffa4d8ce38527ab7bcdaa0ebacfe074b387cac49bde03a"
GEOMETRY_URL = "https://download.openstreetmap.fr/extracts/asia/malaysia-latest.osm.pbf"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
KTM_ROUTES = {"KC05_KB18", "KA15_KD19"}
RAPID_ROUTES = {"AG", "PH", "KJ", "SA", "KGL", "PYL", "MR"}
NOTE = ("KTM Komuter Seremban and Port Klang lines, four Rapid KL LRT lines, both MRT lines and KL Monorail. "
        "KTM uses scheduled departures; Rapid KL movements are frequency-based estimates, not exact departures. "
        "Official feeds retrieved 22 October 2026, selected using their calendars for 12–18 October; not a record of disruptions. "
        "No buses, airport rail, nationwide KTM services or individual passenger loads. Unresolved railway paths stay gaps.")


def selected_route(feed, route, agencies):
    if feed == "ktmb":
        return route.get("agency_id") == "ktmb" and route.get("route_id") in KTM_ROUTES
    return (route.get("agency_id") == "rapidrail" and route.get("route_type") == "1"
            and route.get("route_id") in RAPID_ROUTES)


def describe_route(feed, route, trip):
    kind = "train" if feed == "ktmb" else "subway" if route["category"] == "MRT" else "light_rail"
    return {"mode": kind, "operator": "KTM Komuter" if feed == "ktmb" else "Rapid KL",
            "route_id": route["route_id"], "route_short_name": route["route_short_name"],
            "line": route["route_long_name"],
            **({"frequency_based": True} if feed != "ktmb" else {})}


def compile_geometry(cache, *, output=GEOMETRY, bounds=(100.8, 2.3, 102.4, 3.9), region="KL"):
    import osmium

    filename = fetch(GEOMETRY_URL, cache / "malaysia.osm.pbf")
    if file_hash(filename) != TRACK_PIN:
        raise ValueError("KTM railway extract differs from the validated pin")
    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}

        def way(self, way):
            tags = dict(way.tags)
            if (tags.get("railway") == "rail" and tags.get("gauge", "1000") == "1000"
                    and tags.get("service") not in {"yard", "spur"}
                    and tags.get("usage") not in {"industrial", "military", "test"}
                    and tags.get("disused") != "yes" and tags.get("abandoned") != "yes"):
                self.ways[str(way.id)] = {"nodes": [str(n.ref) for n in way.nodes], "gauge": tags.get("gauge", "")}

    inventory = Inventory()
    inventory.apply_file(str(filename), filters=[osmium.filter.KeyFilter("railway")])
    needed = {n for w in inventory.ways.values() for n in w["nodes"]}

    class Locations(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.nodes = {}

        def node(self, node):
            self.nodes[str(node.id)] = [node.location.lon, node.location.lat]

    locations = Locations()
    locations.apply_file(str(filename), filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    nodes = locations.nodes
    west, south, east, north = bounds
    ways = {key: way for key, way in inventory.ways.items() if any(
        n in nodes and west <= nodes[n][0] <= east and south <= nodes[n][1] <= north for n in way["nodes"])}
    incomplete = sum(any(n not in nodes for n in way["nodes"]) for way in ways.values())
    ways = {key: way for key, way in ways.items() if all(n in nodes for n in way["nodes"])}
    needed = {n for w in ways.values() for n in w["nodes"]}
    if not ways or not needed <= nodes.keys():
        raise ValueError("Railway extract is empty or missing native track nodes")
    result = {"metadata": {"source": f"© OpenStreetMap contributors · {region} conventional metre-gauge railway alignments",
        "source_url": GEOMETRY_URL, "source_date": "2026-10-21T01:16:18Z; retrieved 2026-10-22",
        "source_sha256": TRACK_PIN, "bounds": list(bounds), "omitted_incomplete_ways": incomplete, "license": "ODbL 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "note": "Only original shared node IDs join tracks. Geographic alignments, not actual running-track records."},
        "ways": compact_ways(ways, nodes)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(result, separators=(",", ":")).encode())
    return result


def source(feed, url, digest):
    rapid = feed == "rapid-rail"
    return {"name": "Kuala Lumpur", "first": str(FIRST), "last": str(LAST), "timezone": "Asia/Kuala_Lumpur",
        "captured": "2026-10-22", "published": "", "url": url, "sha256": digest, "calendar_validity": True,
        "assign_by_start": ["train", "subway", "light_rail"],
        "source": "Prasarana / Rapid KL official frequency GTFS" if rapid else "KTM Berhad official GTFS",
        "source_url": RAPID_URL if rapid else KTMB_URL, "license": "CC BY 4.0", "license_url": LICENSE,
        "attribution": ("Prasarana Malaysia Berhad / Rapid KL" if rapid else "Keretapi Tanah Melayu Berhad")
            + " via data.gov.my, CC BY 4.0. Retrieved 22 October 2026; rail selection and compact replay conversion by SunTrain."
            + (" Rapid KL departures illustrate published headways." if rapid else " Railway alignments © OpenStreetMap contributors, ODbL 1.0."),
        "geometry_source": "Rapid KL official GTFS shapes" if rapid else "© OpenStreetMap contributors · connected KL conventional railway ways",
        "geometry_source_url": RAPID_URL if rapid else GEOMETRY_URL,
        "geometry_license": "CC BY 4.0" if rapid else "ODbL 1.0",
        "geometry_license_url": LICENSE if rapid else "https://opendatacommons.org/licenses/odbl/1-0/",
        "geometry_quality": "shape" if rapid else "track", "geometry_method": "ordered_projection",
        "note": NOTE}


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    for feed, url in [("ktmb", KTMB_URL), ("rapid-rail", RAPID_URL)]:
        filename = fetch(url, cache / (feed + ".zip"))
        if file_hash(filename) != PINS[feed]:
            raise ValueError(f"{feed} feed changed; revalidate dates, scope and geometry before updating the pin")
    geometry = compile_geometry(cache)
    graph = FranceRailGraph(geometry["ways"])

    def resolve(route, trip, sequence, coordinates):
        legs = []
        for a, b in zip(coordinates, coordinates[1:]):
            curve = graph.leg(a, b)
            if curve and cumulative_distances(curve)[-1] > max(3000, 3 * cumulative_distances([a, b])[-1]):
                curve = None
            legs.append(curve)
        return legs

    build = cache / "ktm-build"
    build.mkdir(exist_ok=True)
    shutil.copyfile(cache / "ktmb.zip", build / "ktmb")
    ktm_file = cache / "ktm.json.gz"
    prepare_rail("kl-ktm", source("ktmb", KTMB_URL, PINS["ktmb"]), build, ktm_file,
        lambda r, a: selected_route("ktmb", r, a), lambda r, t: describe_route("ktmb", r, t), resolve)

    template_zip = cache / "rapid-templates.zip"
    with ZipFile(cache / "rapid-rail.zip") as archive, ZipFile(template_zip, "w") as target:
        for name in archive.namelist():
            if name.startswith("__MACOSX/") or name == "frequencies.txt":
                continue
            info = ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
            target.writestr(info, archive.read(name))
        calendars = list(records(archive, "calendar.txt"))
        trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in RAPID_ROUTES}
        dwell = {}
        for r in records(archive, "stop_times.txt"):
            if r["trip_id"] in trips and int(r["stop_sequence"]) == 1:
                dwell[r["trip_id"]] = seconds(r["departure_time"]) - seconds(r["arrival_time"])
        frequencies = defaultdict(list)
        for r in records(archive, "frequencies.txt"):
            if r["trip_id"] in trips:
                frequencies[r["trip_id"]].append(r)
        if set(frequencies) != set(trips) or set(dwell) != set(trips):
            raise ValueError("Missing frequency windows or first-stop timing")
    rapid_file = cache / "rapid.json.gz"
    prepare_rail("kl-rapid", source("rapid-rail", template_zip.as_uri(), file_hash(template_zip)),
        cache / "rapid-build", rapid_file, lambda r, a: selected_route("rapid-rail", r, a),
        lambda r, t: describe_route("rapid-rail", r, t))
    with gzip.open(rapid_file, "rt") as stream:
        rapid = json.load(stream)
    patterns = {trip: key for rows in rapid["days"].values() for key, trip, _ in rows}
    if set(patterns) != set(trips):
        raise ValueError("Some Rapid KL templates were omitted")
    rapid["days"] = {str(FIRST + timedelta(days=i)): [] for i in range(7)}
    for i in range(-1, 8):
        day = FIRST + timedelta(days=i)
        active = active_services(calendars, [], day)
        for trip, data in trips.items():
            if data["service_id"] not in active:
                continue
            for departure in frequency_departures(frequencies[trip]):
                owner = day + timedelta(days=(departure - 10800) // 86400)
                if str(owner) in rapid["days"]:
                    offset = (day - owner).days * 86400 + departure - dwell[trip]
                    rapid["days"][str(owner)].append([patterns[trip], trip + ":estimate-" + str(departure), offset])
    rapid["metadata"].update(sources=[{"source_url": RAPID_URL, "sha256": PINS["rapid-rail"], "source_date": "2026-10-22"}],
        frequency_based=True, daily_services={d: dict(Counter(rapid["patterns"][p]["route_id"] for p, _, _ in rows)) for d, rows in rapid["days"].items()})
    with gzip.open(ktm_file, "rt") as stream:
        ktm = json.load(stream)
    result = merge_references([("ktm", ktm), ("rapid", rapid)],
        source_name="KTM Berhad and Prasarana / Rapid KL via data.gov.my", replay_note=NOTE)
    result["metadata"].update(snapshot_date="2026-10-22", license_statement_url="https://developer.data.gov.my/faq.en",
        frequency_based=True, calendar_basis="Published source calendars applied to the selected week; not an archive of historical revisions")
    save_reference(result, output)
    print("KL daily services", {d: len(rows) for d, rows in result["days"].items()}, "bytes", output.stat().st_size, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/kuala-lumpur")
    parser.add_argument("--output", type=Path, default=GEOMETRY.parent / (str(FIRST) + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache.resolve(), args.output)
