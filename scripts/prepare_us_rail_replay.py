"""Prepare Washington Metrorail and Bay Area BART historical replay weeks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_rail_replay import prepare as prepare_rail

SOURCES = {
    "dc": {
        "name": "Washington, DC", "first": "2026-10-05", "last": "2026-10-11", "timezone": "America/New_York",
        # Published distance anchors miss many platform positions by 150–235 m.
        # Match each complete ordered journey to its own shape within 150 m.
        "geometry_method": "ordered_projection",
        "source": "WMATA historical Metrorail GTFS via MobilityDatabase",
        "source_url": "https://www.wmata.com/about/developers.html",
        "license": "WMATA Transit Data Terms of Use", "license_url": "https://developer.wmata.com/license",
        "attribution": "Timetable and railway geometry: Washington Metropolitan Area Transit Authority (WMATA) · historical GTFS via MobilityDatabase",
        "note": "WMATA Metrorail only: Red, Blue, Orange, Silver, Green and Yellow. One Red Line journey variant has unresolved source geometry; its vehicles appear at stations only. Rail replacement shuttles, Metrobus, MARC and VRE are excluded. Scheduled estimates, not observed train movements or every disruption. Individual train passenger loads are unavailable.",
        "archives": [
            {"start": "2026-10-04", "end": "2026-10-06", "captured": "2026-10-03", "published": "",
             "url": "https://files.mobilitydatabase.org/mdb-1847/mdb-1847-202610030015/mdb-1847-202610030015.zip",
             "sha256": "80704345cb03bc58710dec42ad181e796883a1bbf3a6cf95255526c5fb1b724f"},
            {"start": "2026-10-07", "end": "2026-10-12", "captured": "2026-10-07", "published": "",
             "url": "https://files.mobilitydatabase.org/mdb-1847/mdb-1847-202610070121/mdb-1847-202610070121.zip",
             "sha256": "5208ede12b6b6633bbdecffa504f9040076ba525eb8a63fed975734b72ac04cd"},
        ],
    },
    "sf_bay": {
        "name": "SF Bay Area", "first": "2026-08-17", "last": "2026-08-23", "timezone": "America/Los_Angeles",
        "captured": "2026-10-18", "published": "2026-08-04",
        "url": "https://www.bart.gov/sites/default/files/2026-08/google_transit_20260810-20270108_v02.zip",
        "sha256": "affdc4d70cac01f71e54f049c754ba36824a885edcdef2ef8b024820c9e93080",
        "source": "Bay Area Rapid Transit official GTFS schedule, release 72",
        "source_url": "https://www.bart.gov/schedules/developers/gtfs",
        "license": "BART Developer License Agreement", "license_url": "https://www.bart.gov/schedules/developers/developer-license-agreement",
        "attribution": "Timetable and railway geometry: San Francisco Bay Area Rapid Transit District (BART) · August 2026 schedule release",
        "note": "BART only: Yellow, Orange, Green, Red and Blue lines, plus the Oakland Airport connector. One Yellow Line journey variant has unresolved source geometry; its vehicles appear at stations only. Bus bridges, Muni, Caltrain and other operators are excluded. The selected August week is inside both the source calendars and feed validity metadata. Scheduled estimates; no individual train passenger loads.",
    },
}


def selected_route(city, route, agencies):
    agency = route.get("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
    expected = "WMATA" if city == "dc" else "Bay Area Rapid Transit"
    if agencies.get(agency, {}).get("agency_name") != expected or route["route_type"] != "1":
        return False
    if city == "dc":
        return route["route_id"] in {"RED", "BLUE", "ORANGE", "SILVER", "GREEN", "YELLOW"}
    if city == "sf_bay":
        return route["route_short_name"].rsplit("-", 1)[0] in {"Yellow", "Orange", "Green", "Red", "Blue", "Grey"}
    raise ValueError(f"Unsupported city: {city}")


def describe_route(city, route, trip):
    if city == "dc":
        return {"mode": "subway", "line": route["route_long_name"] + " Line", "route_id": route["route_id"]}
    line = route["route_short_name"].rsplit("-", 1)[0]
    return {"mode": "subway", "line": "Oakland Airport connector" if line == "Grey" else line + " Line", "route_id": line}


def prepare(city, cache, output):
    return prepare_rail(city, SOURCES[city], cache, output,
                        lambda route, agencies: selected_route(city, route, agencies),
                        lambda route, trip: describe_route(city, route, trip))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("city", choices=SOURCES)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/us-rail")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    prepare(args.city, args.cache, args.output or ROOT / "data/reference" / args.city / (SOURCES[args.city]["first"] + ".json.gz"))
