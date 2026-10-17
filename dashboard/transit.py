"""Prepared historical tram/bus schedules; no external requests at replay time."""
from __future__ import annotations

import gzip
import json
import os
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

REFERENCE = Path(__file__).resolve().parents[1] / "data/reference/transit/index.json"
PERIOD_START = "2024-05-27"
PERIOD_END = "2024-06-30"


def reference_file():
    return Path(os.getenv("SUNTRAIN_TRANSIT_REFERENCE", str(REFERENCE)))


def fingerprint(business_date=None):
    path = reference_file()
    if path.exists() and path.suffix != ".gz" and business_date:
        index = read_reference(str(path), path.stat().st_mtime_ns)
        for chunk in index.get("chunks", []):
            if chunk["start_date"] <= business_date <= chunk["end_date"]:
                path = path.parent / chunk["file"]
                if not path.exists():
                    raise FileNotFoundError(f"Missing transit snapshot bundle: {path}")
                break
    return (str(path), path.stat().st_mtime_ns if path.exists() else 0)


@lru_cache(maxsize=2)
def read_reference(path, modified):
    if not modified:
        return None
    opener = gzip.open if Path(path).suffix == ".gz" else open
    with opener(path, "rt") as stream:
        return json.load(stream)


def available_range():
    reference = read_reference(*fingerprint())
    if not reference:
        return None
    metadata = reference.get("metadata", {})
    return metadata.get("start_date", PERIOD_START), metadata.get("end_date", PERIOD_END)


def add_transit(day, reference_fingerprint):
    reference = read_reference(*reference_fingerprint)
    append_reference(day, reference)


def append_reference(day, reference, *, consume=False, modes=None):
    """Append shared schedules; consume only a freshly parsed, uncached reference."""
    day["transit"] = {"available": False, "start_date": PERIOD_START, "end_date": PERIOD_END}
    if not reference or day["business_date"] not in reference.get("days", {}):
        return
    day["transit"] = {**reference["metadata"], "available": True}
    occurrences = [row for row in reference["days"][day["business_date"]]
                   if modes is None or reference["patterns"][row[0]]["mode"] in modes]
    selected_patterns = {row[0] for row in occurrences}
    packed = reference.get("stop_patterns", {})
    packed_ids = {reference["patterns"][p]["stop_pattern"] for p in selected_patterns if "stop_pattern" in reference["patterns"][p]}
    station_ids = sorted({s for p in packed_ids for s in packed[p]["stations"]} |
                         {s[0] for p in selected_patterns if "stops" in reference["patterns"][p] for s in reference["patterns"][p]["stops"]})
    station_map = {identifier: len(day["stations"]) + i for i, identifier in enumerate(station_ids)}
    day["stations"].extend(reference["stations"][identifier] for identifier in station_ids)
    remapped = {}
    for key in packed_ids:
        topology = packed[key] if consume else dict(packed[key])
        topology["stations"] = [station_map[s] for s in topology["stations"]]
        remapped[key] = topology
    if remapped:
        day.setdefault("transit_stop_patterns", {}).update(remapped)
    patterns = {}
    for identifier in selected_patterns:
        pattern = reference["patterns"][identifier]
        if "stop_pattern" in pattern:
            patterns[identifier] = pattern
        elif consume:
            for stop in pattern["stops"]:
                stop[0] = station_map[stop[0]]
            patterns[identifier] = pattern
        else:
            patterns[identifier] = {**pattern, "stops": [[station_map[s[0]], s[1], s[2]] for s in pattern["stops"]]}
        legs = packed[pattern["stop_pattern"]]["legs"] if "stop_pattern" in pattern else pattern["legs"]
        for leg in legs:
            day["paths"][leg] = reference["paths"][leg]
    day.setdefault("transit_patterns", {}).update(patterns)
    # GTFS service-day zero is noon minus 12 elapsed hours (also correct on DST days).
    midnight = int(datetime.combine(date.fromisoformat(day["business_date"]), time(12),
                                    ZoneInfo(day.get("timezone", "Australia/Melbourne"))).timestamp()) - 12 * 3600
    for identifier, trip, seconds in occurrences:
        pattern = reference["patterns"][identifier]
        departure = midnight + seconds
        day["services"].append({"mode": pattern["mode"],
                                "id": f"gtfs:{day['business_date']}:{trip}:{seconds}", "number": trip,
                                "pattern": identifier, "departure": departure, "timing_uncertain": False})
        legs = packed[pattern["stop_pattern"]]["legs"] if "stop_pattern" in pattern else pattern["legs"]
        day["total_legs"] += len(legs)
        day["approximate_legs"] += sum(reference["paths"][p]["quality"] == "approximate" for p in legs)
