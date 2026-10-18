"""Prepare optional Chicago/Perth bus days from their existing pinned archives.

Reuse shared geometry/calendar preparation; only compact daily bundles ship.
No current download is substituted for either historical snapshot.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import SOURCES
from scripts.prepare_chicago_replay import ARCHIVES, LICENSE_URL, SOURCE_URL
from scripts.prepare_rail_replay import prepare as prepare_shared

CHICAGO_HASHES = [
    "4a34e0c78a12d797ae5b3f5075005e91db8b6e6715eda9b146fa3946b1136964",
    "1d49526cbce5bf3188cad4524cafdae581e3ad6a4920d256d4577a51e3c3bb4d",
]


def source_for(city):
    if city == "perth":
        return {**SOURCES[city], "published": "", "calendar_validity": True,
                "assign_by_start": ["bus"],
                "note": "Optional Transperth metropolitan buses, including Perth, Fremantle and Joondalup CAT where scheduled. Regional operators, Transwa and ferries are excluded. Feed route colours are retained. No individual vehicle passenger loads."}
    if city != "chicago":
        raise ValueError(f"Unsupported bus city: {city}")
    windows = [("2025-11-23", "2025-12-18"), ("2025-12-19", "2025-12-29")]
    return {"first": "2025-11-24", "last": "2025-12-28", "timezone": "America/Chicago",
            "source": "Chicago Transit Authority historical GTFS via MobilityDatabase",
            "source_url": SOURCE_URL, "license": "CTA Developer License Agreement", "license_url": LICENSE_URL,
            "attribution": "Timetable and road geometry: Chicago Transit Authority · historical November–December 2025 GTFS",
            "note": "Optional CTA buses, using the same dated archives as CTA rail, including holiday and overnight schedules. Feed route colours are retained. Metra, Pace and individual vehicle passenger loads are excluded.",
            "calendar_validity": True, "assign_by_start": ["bus"],
            "archives": [{"start": first, "end": last, "url": url, "sha256": digest,
                          "captured": str(captured), "published": ""}
                         for (first, last), (captured, url), digest in zip(windows, ARCHIVES, CHICAGO_HASHES)]}


def selected_route(city, route, agencies):
    agency = route.get("agency_id") or (next(iter(agencies)) if len(agencies) == 1 else "")
    name = agencies.get(agency, {}).get("agency_name")
    return route["route_type"] == "3" and name == (
        "Chicago Transit Authority" if city == "chicago" else "Transperth")


def describe_route(city, route, trip):
    short, long = route.get("route_short_name", ""), route.get("route_long_name", "")
    return {"mode": "bus", "operator": "CTA" if city == "chicago" else "Transperth",
            "route_id": short or route["route_id"],
            "line": f"{short} · {long}" if short and long else short or long or route["route_id"],
            "direction": trip.get("direction", "")}


def prepare(city, cache, output):
    prepare_shared(city, source_for(city), cache, output,
                   lambda route, agencies: selected_route(city, route, agencies),
                   lambda route, trip: describe_route(city, route, trip), daily=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("city", choices=["chicago", "perth"])
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cache = args.cache or ROOT / ".cache" / ("chicago-archives" if args.city == "chicago" else "australian-cities/perth")
    prepare(args.city, cache, args.output or ROOT / "data/reference" / args.city / "bus")
