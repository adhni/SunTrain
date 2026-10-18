import gzip
import json
import re
from pathlib import Path

import pytest

from scripts.compact_transit import compact_reference, save_reference
from schedule_helpers import expanded_reference

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = sorted(path for path in (ROOT / "data/reference").glob("*/*.json.gz")
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json\.gz", path.name))
REFERENCES += sorted((ROOT / "data/reference").glob("*/bus/*.json.gz"))


@pytest.mark.parametrize("path", REFERENCES, ids=lambda p: str(p.relative_to(ROOT / "data/reference")))
def test_all_bundled_schedules_share_stop_sequences_without_expansion(path):
    with gzip.open(path, "rt") as stream:
        reference = json.load(stream)
    assert reference["metadata"]["schedule_encoding"] == "shared-stops-flat-times-v1"
    patterns, topologies = reference["patterns"], reference["stop_patterns"]
    assert topologies and len(topologies) <= len(patterns)
    for pattern in patterns.values():
        assert "stops" not in pattern and "legs" not in pattern
        topology = topologies[pattern["stop_pattern"]]
        assert len(topology["stations"]) == len(pattern["times"]) // 2
        assert len(pattern["times"]) % 2 == 0 and pattern["times"][0] == 0
        assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))
    for topology in topologies.values():
        assert len(topology["legs"]) + 1 == len(topology["stations"])
        assert all(0 <= station < len(reference["stations"]) for station in topology["stations"])
        assert all(leg in reference["paths"] for leg in topology["legs"])
    for rows in reference["days"].values():
        assert all(pattern in patterns for pattern, _, _ in rows)
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)


def test_compaction_preserves_loop_occurrences_distinct_times_and_geometry(tmp_path):
    # Route IDs are optional in the Melbourne source. Identical stop order can
    # share a topology, but different paths through a loop must remain distinct.
    reference = {"metadata": {"start_date": "2024-05-27"}, "stations": [{}, {}],
        "patterns": {
            "one": {"line": "Tram 1", "operator": "PTV tram", "stops": [[0, 0, 0], [1, 10, 11], [0, 20, 20]], "legs": ["out", "back"]},
            "two": {"line": "Tram 1", "operator": "PTV tram", "stops": [[0, 0, 2], [1, 12, 13], [0, 22, 22]], "legs": ["out", "back"]},
            "other-track": {"line": "Tram 1", "operator": "PTV tram", "stops": [[0, 0, 0], [1, 10, 11], [0, 20, 20]], "legs": ["other", "back"]}},
        "paths": {"out": {}, "back": {}, "other": {}},
        "days": {"2024-05-27": [["one", "t1", 90000], ["two", "t2", 90100]]}}
    expected = json.loads(json.dumps(reference))
    compact_reference(reference)
    assert len(reference["stop_patterns"]) == 2
    assert reference["patterns"]["one"]["stop_pattern"] == reference["patterns"]["two"]["stop_pattern"]
    restored = expanded_reference(reference)
    for key, pattern in expected["patterns"].items():
        assert all(restored["patterns"][key][field] == value for field, value in pattern.items())
    assert reference["days"] == expected["days"] and reference["stations"] == expected["stations"]
    path = tmp_path / "reference.json.gz"
    save_reference(reference, path)
    before = path.read_bytes()
    save_reference(reference, path)
    assert path.read_bytes() == before and not list(tmp_path.glob("*.tmp"))
