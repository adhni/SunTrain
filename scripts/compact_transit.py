"""Compact shared timetable topologies and select independent daily bundles."""
import hashlib
import json


def compact_reference(reference, prefix="stops-"):
    if "stop_patterns" in reference:
        return reference
    topologies, ordered = {}, {}
    rows = sorted(reference["patterns"].items(), key=lambda item: (item[1]["route_id"], item[1]["operator"],
                  tuple(s[0] for s in item[1]["stops"]), tuple(v for s in item[1]["stops"] for v in s[1:])))
    for key, pattern in rows:
        topology = {"stations": [s[0] for s in pattern["stops"]], "legs": pattern.pop("legs")}
        identifier = prefix + hashlib.sha256(json.dumps(topology).encode()).hexdigest()[:20]
        topologies.setdefault(identifier, topology)
        pattern["stop_pattern"] = identifier
        pattern["times"] = [v for stop in pattern.pop("stops") for v in stop[1:]]
        ordered[key] = pattern
    reference["patterns"], reference["stop_patterns"] = ordered, topologies
    reference["metadata"]["schedule_encoding"] = "shared-stops-flat-times-v1"
    return reference


def daily_reference(reference, day):
    rows = reference["days"][day]
    patterns = {key: reference["patterns"][key] for key in sorted({r[0] for r in rows})}
    keys = {p["stop_pattern"] for p in patterns.values()}
    station_ids = sorted({s for key in keys for s in reference["stop_patterns"][key]["stations"]})
    remap = {old: new for new, old in enumerate(station_ids)}
    topologies = {key: {**reference["stop_patterns"][key],
        "stations": [remap[s] for s in reference["stop_patterns"][key]["stations"]]} for key in sorted(keys)}
    paths = {leg for topology in topologies.values() for leg in topology["legs"]}
    return {"metadata": {**reference["metadata"], "bundle_date": day},
        "stations": [reference["stations"][s] for s in station_ids], "patterns": patterns,
        "stop_patterns": topologies, "paths": {key: reference["paths"][key] for key in sorted(paths)}, "days": {day: rows}}
