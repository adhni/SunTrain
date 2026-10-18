"""Decode shared patterns for calendar/geometry assertions in tests only."""


def expanded_pattern(reference, pattern):
    if "stop_pattern" not in pattern:
        return pattern
    topologies = reference.get("stop_patterns", reference.get("transit_stop_patterns", {}))
    topology = topologies[pattern["stop_pattern"]]
    return {**pattern, "legs": topology["legs"],
            "stops": [[station, *pattern["times"][2 * i:2 * i + 2]]
                      for i, station in enumerate(topology["stations"])]}


def expanded_reference(reference):
    if "patterns" not in reference:
        return reference
    return {**reference, "patterns": {key: expanded_pattern(reference, pattern)
                                     for key, pattern in reference["patterns"].items()}}
