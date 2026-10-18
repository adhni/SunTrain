"""Prepare one week of TTC rapid transit from a hash-pinned official GTFS file.

Includes subway Lines 1/2/4, light rail Lines 5/6 and daytime/night streetcars.
Excludes replacement buses, other buses, GO and UP Express.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_rail_replay import prepare as prepare_rail

SOURCE = {
    "name": "Toronto", "first": "2026-10-05", "last": "2026-10-11", "timezone": "America/Toronto",
    "captured": "2026-10-18", "published": "2026-09-30",
    "url": "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/b811ead4-6eaf-4adb-8408-d389fb5a069c/resource/c920e221-7a1c-488b-8c5b-6d8cd4e85eaf/download/completegtfs.zip",
    "sha256": "5e0191d59cb991b6c88ba9c1a5f2ca93a5a064a4d258dbc7ba93801d15f3dfca",
    "source": "Toronto Transit Commission official Merged GTFS – TTC Routes and Schedules",
    "source_url": "https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/",
    "license": "Open Government Licence – Toronto", "license_url": "https://open.toronto.ca/open-data-licence/",
    "attribution": "Contains information licensed under the Open Government Licence – Toronto. Timetable and railway geometry: TTC / City of Toronto · source published 30 September 2026",
    "note": "TTC subway Lines 1, 2 and 4, light rail Lines 5 and 6, and daytime/night streetcars. Two Line 1 journey variants have unresolved source geometry; their vehicles appear at stations only. Replacement buses, other buses, GO Transit and UP Express are excluded. Regular schedules, not a reconstruction of every closure. No individual vehicle passenger loads.",
    "assign_by_start": ["tram"],
}


def selected_route(route, agencies):
    agency = route.get("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
    if agencies.get(agency, {}).get("agency_name") != "TTC":
        return False
    return (route["route_type"] == "1" and route["route_short_name"] in {"1", "2", "4"}) or (
        route["route_type"] == "0")


def describe_route(route, trip):
    rapid = route["route_short_name"] in {"1", "2", "4", "5", "6"}
    return {"mode": "subway" if route["route_type"] == "1" else "light_rail" if rapid else "tram",
            "line": f"{'Line ' if rapid else ''}{route['route_short_name']} · {route['route_long_name'].removesuffix(' Line')}",
            "route_id": route["route_short_name"]}


def prepare(cache, output):
    return prepare_rail("toronto", SOURCE, cache, output, selected_route, describe_route)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/toronto-audit")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/toronto" / (SOURCE["first"] + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache, args.output)
