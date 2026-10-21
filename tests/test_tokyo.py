from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_tokyo_replay import railway_geometry, selected_route


def test_jr_east_scope_excludes_other_operators_and_modes():
    route = {"route_id": "JR-East.Yamanote", "agency_id": "JR-East", "route_type": "2"}
    agencies = {"JR-East": {}, "TokyoMetro": {}}
    assert selected_route(route, agencies)
    for change in [{"agency_id": "TokyoMetro"}, {"route_type": "3"}, {"route_type": "1"},
                   {"route_id": "JR-Central.TokaidoShinkansen"}]:
        assert not selected_route({**route, **change}, agencies)


def test_native_track_edges_keep_straight_rail_and_reject_inserted_shortcuts():
    points = [[139.0, 35.0], [139.02, 35.0], [139.04, 35.0]]
    raw = [(i, float(i), point) for i, point in enumerate(points)]
    edges = {frozenset(map(tuple, points[:2]))}
    resolve = railway_geometry({"shape": raw}, edges)
    sequence = [{"shape_dist_traveled": str(i)} for i in range(3)]
    curves = resolve({}, {"shape_id": "shape"}, sequence, points)
    assert curves[0] == points[:2]  # Real, long straight track is retained.
    assert curves[1] is None  # Matching endpoints alone cannot validate a path.


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.TOKYO_PATH, "rt") as stream:
        return json.load(stream)


def test_snapshot_has_only_jr_east_with_compact_schedules_and_local_departure_days(reference):
    assert set(reference["days"]) == {"2026-10-20"}
    assert len(reference["days"]["2026-10-20"]) == 9998
    assert len({p["source_route_id"] for p in reference["patterns"].values()}) == 47
    assert not reference["metadata"]["omitted_trips"]
    assert "not official historical validity" in reference["metadata"]["calendar_basis"]
    seen = set()
    late = False
    for key, trip, offset in reference["days"]["2026-10-20"]:
        p = reference["patterns"][key]
        assert p["operator"] == "JR East" and p["mode"] == "train"
        assert p["source_route_id"].startswith("JR-East.")
        assert "stops" not in p
        topology = reference["stop_patterns"][p["stop_pattern"]]
        assert len(p["times"]) == 2 * len(topology["stations"])
        assert all(a <= b for a, b in zip(p["times"], p["times"][1:]))
        assert 10800 <= offset + p["times"][1] < 97200
        assert (trip, offset) not in seen
        seen.add((trip, offset))
        assert reference["train_numbers"][trip]
        late |= offset + p["times"][-1] > 86400
    assert late
    assert replay.TOKYO_PATH.stat().st_size < 2_000_000


def test_yamanote_repeated_terminal_uses_the_full_loop_and_correct_direction(reference):
    key, _, _ = next(row for row in reference["days"]["2026-10-20"]
                      if row[1] == "JR-East.Yamanote.400G.Weekday")
    pattern = reference["patterns"][key]
    assert pattern["direction"] == "Inner loop" and pattern["color"] == "#80C747"
    topology = reference["stop_patterns"][pattern["stop_pattern"]]
    assert topology["stations"][0] == topology["stations"][-1]
    paths = [reference["paths"][key] for key in topology["legs"]]
    assert all(path["coordinates"] for path in paths)
    assert 30_000 < sum(path["distances"][-1] for path in paths) < 40_000


def test_runtime_descriptor_uses_tokyo_clock_and_keeps_shared_schedules():
    info = descriptor("2026-10-20", "tokyo")
    assert info["modes"] == ["train"]
    with pytest.raises(ValueError, match="Date outside"):
        descriptor("2024-06-24", "tokyo")
    day = replay.get_replay_day("2026-10-20", "tokyo")
    assert len(day["services"]) == 9998
    assert datetime.fromtimestamp(day["initial"], ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M") == "2026-10-20 08:00"
    assert all("stops" not in s and "pattern" in s for s in day["services"])
    train = next(s for s in day["services"] if s["source_trip_id"] == "JR-East.Yamanote.400G.Weekday")
    assert train["number"] == "400G"
    assert day["transit_patterns"][train["pattern"]]["direction"] == "Inner loop"
