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
TRAM_GEOMETRY = ROOT / "data/reference/netherlands/ret-tram-osm-2026-10-17.json.gz"
TRAM_GEOMETRY_SHA256 = "fb26e181cb992322accbf6205c4709630a8d3422fc5ceb094d3be0af622f1dff"

# These are the audited domestic rail agencies in this particular snapshot.
OPERATORS = {
    "IFF:NS": "NS", "IFF:ARRIVA": "Arriva",
    "IFF:BLAUWNET_A": "Blauwnet Arriva", "IFF:BLAUWNET_K": "Blauwnet Keolis",
    "IFF:R-NET_NS": "R-net NS", "IFF:R-NET_QB": "R-net Qbuzz",
    "IFF:RRREIS_A": "RRReis Arriva", "IFF:RRREIS_K": "RRReis Keolis",
}
METRO_OPERATORS = {"GVB": "GVB", "RET": "RET"}
METRO_LINES = {"GVB": {"50", "51", "52", "53", "54"}, "RET": {"A", "B", "C", "D", "E"}}
TRAM_OPERATORS = {"GVB": "GVB", "RET": "RET", "HTM": "HTM", "UOV": "U-OV"}
TRAM_LINES = {
    "GVB": {"1", "2", "4", "5", "6", "7", "12", "13", "14", "17", "19", "23", "24", "25", "26", "27", "29"},
    "RET": {"1", "2", "3", "4", "5", "6", "7", "8", "11", "12", "24"},
    "HTM": {"1", "2", "3", "4", "6", "9", "10", "11", "12", "15", "16", "17", "19", "34"},
    "UOV": {"20", "21", "22"},
}
# GVB/RET tram colours are blank in this snapshot. These are SunTrain display
# colours, not official individual line colours or Melbourne's tram palette.
TRAM_COLORS = {"GVB": "008ACD", "RET": "008C5A", "HTM": "6F818E", "UOV": "FF0010"}
FERRY_LINES = {"F1", "F2", "F3", "F4", "F6", "F7", "F9", "F20", "F21", "F22"}
FERRY_COLOR = "0077B6"  # SunTrain display colour; the source leaves ferry colours blank.
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
    "assign_by_start": ["train", "subway", "tram", "ferry"],
    "geometry_method": "native_or_ordered_per_leg",
    "geometry_source": "Rotterdam metro/tram railway geometry © OpenStreetMap contributors",
    "geometry_source_url": "https://www.openstreetmap.org/copyright",
    "geometry_license": "ODbL 1.0", "geometry_license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
    "geometry_source_date": "2026-10-17 (outer-route supplements accessed 18 October)",
    "note": "Domestic trains, Amsterdam/Rotterdam metros, optional trams/light rail in four cities and GVB ferries across the IJ/North Sea Canal. Schedules follow the 29 May 2026 archive calendars. Feed shapes supply native rail/water paths; Rotterdam metros/trams use October 2026 OSM railway geography. Unresolved paths stay as gaps. Buses and international services are excluded. Vehicle passenger counts are unavailable.",
}


def selected_route(route, agencies):
    agency = route.get("agency_id", "")
    if route.get("route_type") == "4":
        return (agency == "GVB" and agencies.get(agency, {}).get("agency_name") == "GVB"
                and route.get("route_short_name") in FERRY_LINES)
    if route.get("route_type") == "0":
        return (agency in TRAM_OPERATORS
                and agencies.get(agency, {}).get("agency_name") == TRAM_OPERATORS[agency]
                and route.get("route_short_name") in TRAM_LINES[agency])
    if route.get("route_type") == "1":
        return (agency in METRO_OPERATORS
                and agencies.get(agency, {}).get("agency_name") == METRO_OPERATORS[agency]
                and route.get("route_short_name") in METRO_LINES[agency])
    return (route.get("route_type") == "2" and agency in OPERATORS
            and agencies.get(agency, {}).get("agency_name") == OPERATORS[agency]
            and route["route_id"] not in INTERNATIONAL_ROUTES)


def describe_route(route, trip):
    if route.get("route_type") == "4":
        return {"mode": "ferry", "route_id": route["route_id"], "route_short_name": route["route_short_name"],
                "line": f"GVB Ferry {route['route_short_name']}", "color": route.get("route_color") or FERRY_COLOR}
    if route.get("route_type") == "0":
        agency = route["agency_id"]
        city = {"GVB": "Amsterdam", "RET": "Rotterdam", "HTM": "The Hague", "UOV": "Utrecht"}[agency]
        return {"mode": "tram", "route_id": route["route_id"], "route_short_name": route["route_short_name"],
                "line": f"{city} Tram {route['route_short_name']}",
                "color": route.get("route_color") or TRAM_COLORS[agency]}
    if route["agency_id"] in METRO_OPERATORS:
        city = "Amsterdam" if route["agency_id"] == "GVB" else "Rotterdam"
        return {"mode": "subway", "route_id": route["route_id"], "route_short_name": route["route_short_name"],
                "line": f"{city} Metro {route['route_short_name']}",
                "color": route.get("route_color") or "6F818E"}
    return {"mode": "train", "route_id": route["route_id"],
            "line": f"{route['route_short_name']} · {route['route_long_name'].replace('<->', '↔')}",
            "color": route.get("route_color") or DISPLAY_COLORS[route["agency_id"]]}


def metro_geometry_resolver(geographic, tram_geographic=None):
    graphs = {}

    def resolve(route, trip, sequence, coordinates):
        if route["agency_id"] != "RET":
            return NotImplemented
        code = route["route_short_name"]
        tram = route.get("route_type") == "0"
        geometry = tram_geographic if tram else geographic
        if geometry is None:
            raise ValueError("RET tram railway geometry is missing")
        try:
            return match_geometry(geometry["lines"].get(code, []), coordinates)[1]
        except ValueError:
            # The 2026 A/B/C and D/E services share physical corridors. Later
            # OSM A relations end at Schiedam, while this timetable continues
            # along the shared A/B track to Vlaardingen. Join only OSM node IDs.
            family = tuple(sorted(geometry["lines"])) if tram else ("A", "B", "C") if code in {"A", "B", "C"} else ("D", "E")
            key = ("tram" if tram else "metro", family)
            if key not in graphs:
                graphs[key] = RailGraph([variant for line in family for variant in geometry["lines"].get(line, [])])
            return [graphs[key].leg(a, b) for a, b in zip(coordinates, coordinates[1:])]

    return resolve


def prepare(cache, output, geometry=GEOMETRY, tram_geometry=TRAM_GEOMETRY):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError("Rotterdam railway geometry differs from the validated reference")
    with gzip.open(geometry, "rt") as stream:
        geographic = json.load(stream)
    if file_hash(tram_geometry) != TRAM_GEOMETRY_SHA256:
        raise ValueError("Rotterdam tram geometry differs from the validated reference")
    with gzip.open(tram_geometry, "rt") as stream:
        tram_geographic = json.load(stream)
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
    return prepare_rail("netherlands", {**SOURCE, "geometry_sha256": GEOMETRY_SHA256,
                        "geometry_references": [geographic["metadata"], {**tram_geographic["metadata"], "sha256": TRAM_GEOMETRY_SHA256}]},
                        cache, output, selected_route, describe_route,
                        geometry_resolver=metro_geometry_resolver(geographic, tram_geographic))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/netherlands")
    parser.add_argument("--geometry", type=Path, default=GEOMETRY)
    parser.add_argument("--tram-geometry", type=Path, default=TRAM_GEOMETRY)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/netherlands" / (SOURCE["first"] + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.output, args.geometry, args.tram_geometry)
