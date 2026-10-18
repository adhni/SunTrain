"""Prepare the 1–7 June 2026 domestic Netherlands rail pilot from OVapi GTFS."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_singapore_replay import match_geometry
from scripts.london_rail_graph import RailGraph

GEOMETRY = ROOT / "data/reference/netherlands/ret-osm-2026-10-17.json.gz"
GEOMETRY_SHA256 = "b5ebe6463a3b15f16923126b548afd5fa2b423e48895fdad8bc43aa73f1b587a"

# These are the audited domestic rail agencies in this particular snapshot.
OPERATORS = {
    "IFF:NS": "NS", "IFF:ARRIVA": "Arriva",
    "IFF:BLAUWNET_A": "Blauwnet Arriva", "IFF:BLAUWNET_K": "Blauwnet Keolis",
    "IFF:R-NET_NS": "R-net NS", "IFF:R-NET_QB": "R-net Qbuzz",
    "IFF:RRREIS_A": "RRReis Arriva", "IFF:RRREIS_K": "RRReis Keolis",
}
METRO_OPERATORS = {"GVB": "GVB", "RET": "RET"}
METRO_LINES = {"GVB": {"50", "51", "52", "53", "54"}, "RET": {"A", "B", "C", "D", "E"}}
# The Arriva RE18 routes extend to Belgium/Germany. International services are
# outside this pilot; do not truncate their journeys or infer domestic variants.
INTERNATIONAL_ROUTES = {"124366", "124367"}
# The source leaves rail colours blank. These are SunTrain display colours,
# grouped by operator family, rather than purported official route colours.
DISPLAY_COLORS = {
    "IFF:NS": "003082", "IFF:ARRIVA": "008C95",
    "IFF:BLAUWNET_A": "006BB6", "IFF:BLAUWNET_K": "006BB6",
    "IFF:R-NET_NS": "C8102E", "IFF:R-NET_QB": "C8102E",
    "IFF:RRREIS_A": "71368A", "IFF:RRREIS_K": "71368A",
}
SOURCE = {
    "name": "Netherlands", "first": "2026-06-01", "last": "2026-06-07", "timezone": "Europe/Amsterdam",
    "captured": "2026-05-29", "published": "2026-05-29",
    "url": "https://gtfs.ovapi.nl/nl/archive/NL-20260529.gtfs.zip",
    "sha256": "7b5cb589fb42965b768e6e73c2fedb8639cb417426e5b015f2d2b21d28e6254e",
    "source": "Dutch integrated GTFS Schedule via OVapi / NDOV",
    "source_url": "https://gtfs.ovapi.nl/nl/archive/",
    "license": "OVapi open-data usage conditions", "license_url": "https://gtfs.ovapi.nl/README",
    "attribution": "Historical timetables and railway geometry: Dutch transit operators via NDOV / OVapi · OVapi archive 29 May 2026",
    "assign_by_start": ["train", "subway"],
    "geometry_method": "native_or_ordered_per_leg",
    "geometry_source": "Rotterdam Metro railway geometry © OpenStreetMap contributors",
    "geometry_source_url": "https://www.openstreetmap.org/copyright",
    "geometry_license": "ODbL 1.0", "geometry_license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "geometry_source_date": "2026-10-17 (outer-route supplements accessed 18 October)",
    "note": "Domestic NS and regional trains, Amsterdam Metro 50–54 and Rotterdam Metro A–E, using the 29 May 2026 timetable snapshot and its service calendars. NS/regional and Amsterdam movement follows feed shapes; Rotterdam uses October 2026 OpenStreetMap railway geography as a reference. Unresolved paths stay as gaps. International routes, trams, buses and ferries are excluded. Individual train passenger counts are unavailable.",
}


def selected_route(route, agencies):
    agency = route.get("agency_id", "")
    if route.get("route_type") == "1":
        return (agency in METRO_OPERATORS
                and agencies.get(agency, {}).get("agency_name") == METRO_OPERATORS[agency]
                and route.get("route_short_name") in METRO_LINES[agency])
    return (route.get("route_type") == "2" and agency in OPERATORS
            and agencies.get(agency, {}).get("agency_name") == OPERATORS[agency]
            and route["route_id"] not in INTERNATIONAL_ROUTES)


def describe_route(route, trip):
    if route["agency_id"] in METRO_OPERATORS:
        city = "Amsterdam" if route["agency_id"] == "GVB" else "Rotterdam"
        return {"mode": "subway", "route_id": route["route_id"], "route_short_name": route["route_short_name"],
                "line": f"{city} Metro {route['route_short_name']}",
                "color": route.get("route_color") or "6F818E"}
    return {"mode": "train", "route_id": route["route_id"],
            "line": f"{route['route_short_name']} · {route['route_long_name'].replace('<->', '↔')}",
            "color": route.get("route_color") or DISPLAY_COLORS[route["agency_id"]]}


def metro_geometry_resolver(geographic):
    graphs = {}

    def resolve(route, trip, sequence, coordinates):
        if route["agency_id"] != "RET":
            return NotImplemented
        code = route["route_short_name"]
        try:
            return match_geometry(geographic["lines"].get(code, []), coordinates)[1]
        except ValueError:
            # The 2026 A/B/C and D/E services share physical corridors. Later
            # OSM A relations end at Schiedam, while this timetable continues
            # along the shared A/B track to Vlaardingen. Join only OSM node IDs.
            family = ("A", "B", "C") if code in {"A", "B", "C"} else ("D", "E")
            if family not in graphs:
                graphs[family] = RailGraph([variant for line in family for variant in geographic["lines"].get(line, [])])
            return [graphs[family].leg(a, b) for a, b in zip(coordinates, coordinates[1:])]

    return resolve


def prepare(cache, output, geometry=GEOMETRY):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError("Rotterdam railway geometry differs from the validated reference")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    cache.mkdir(parents=True, exist_ok=True)
    filename = cache / SOURCE["url"].rsplit("/", 1)[1]
    if not filename.exists():
        request = Request(SOURCE["url"], headers={
            "User-Agent": "SunTrain historical replay preparation (github.com/adhni/SunTrain)",
            "Accept-Encoding": "gzip",
        })
        temporary = filename.with_suffix(".zip.tmp")
        try:
            with urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
                content = gzip.GzipFile(fileobj=response) if response.headers.get("Content-Encoding") == "gzip" else response
                while True:
                    chunk = content.read(1024 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)
            temporary.replace(filename)
        finally:
            temporary.unlink(missing_ok=True)
    return prepare_rail("netherlands", {**SOURCE, "geometry_sha256": GEOMETRY_SHA256}, cache, output,
                        selected_route, describe_route, geometry_resolver=metro_geometry_resolver(geographic))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/netherlands")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/netherlands" / (SOURCE["first"] + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.output, args.geometry)
