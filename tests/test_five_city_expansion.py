import gzip
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay, replay_http
from scripts.compact_transit import compact_reference, daily_reference
from scripts.prepare_boston_replay import is_regular_bus, replay_mode

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("business,count", [("2024-06-24", 10950), ("2024-06-29", 7517), ("2024-06-30", 5026)])
def test_boston_regular_buses_keep_daily_compact_schedules_and_city_colours(business, count):
    path = ROOT / "data/reference/boston/bus" / (business + ".json.gz")
    with gzip.open(path, "rt") as stream:
        reference = json.load(stream)
    assert path.stat().st_size < 1200000
    assert len(reference["days"][business]) == count
    assert len({(trip, offset) for _, trip, offset in reference["days"][business]}) == count
    assert not reference["metadata"]["omitted_trips"] and not reference["metadata"]["unresolved_geometry_patterns"]
    assert len(reference["stop_patterns"]) <= 482
    for pattern in reference["patterns"].values():
        assert pattern["mode"] == "bus" and pattern["color"] == "#FFC72C"
        assert pattern["operator"] == "MBTA" and not pattern["route_id"].startswith("Shuttle")
        assert pattern["route_id"] not in {"741", "742", "743", "746", "749", "751"}
        assert "stops" not in pattern
        topology = reference["stop_patterns"][pattern["stop_pattern"]]
        assert len(pattern["times"]) == len(topology["stations"]) * 2
        assert len(topology["legs"]) + 1 == len(topology["stations"])
        assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))


def test_boston_default_never_opens_bus_bundle_and_bus_selection_preserves_rail(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_BOSTON_BUS_REFERENCE", str(tmp_path / "missing"))
    info = replay_http.descriptor("2024-06-24", "boston")
    assert not info["bus_data_loaded"] and "bus" not in info["modes"]
    rail = replay.get_replay_day("2024-06-24", "boston")
    count = len(rail["services"])
    monkeypatch.delenv("SUNTRAIN_BOSTON_BUS_REFERENCE")
    info = replay_http.descriptor("2024-06-24", "boston", ["bus"])
    assert info["bus_data_loaded"] and info["modes"] == ["bus"]
    buses = replay.get_replay_day("2024-06-24", "boston", modes=["bus"])
    assert buses["bus_data_loaded"] and len(buses["services"]) == 10950
    assert len(rail["services"]) == count and all(s["mode"] != "bus" for s in rail["services"])
    assert all(s["mode"] == "bus" and "stops" not in s for s in buses["services"])
    service = buses["services"][0]
    pattern = buses["transit_patterns"][service["pattern"]]
    first = buses["transit_stop_patterns"][pattern["stop_pattern"]]["stations"][0]
    assert buses["stations"][first]["mode"] == "bus"
    assert datetime.fromtimestamp(buses["initial"], ZoneInfo(buses["timezone"])).hour == 8


def test_regular_bus_scope_excludes_replacements_and_keeps_silver_separate():
    route = {"route_type": "3", "route_desc": "Local Bus", "line_id": "line-1"}
    assert is_regular_bus(route) and replay_mode({}, route, regular_buses=True) == "bus"
    assert not is_regular_bus({**route, "route_desc": "Rail Replacement Bus"})
    silver = {**route, "line_id": "line-SLWaterfront"}
    assert not is_regular_bus(silver) and replay_mode({}, silver, regular_buses=True) == "silver_line"
    assert replay_mode({"trip_route_type": "3"}, {"route_type": "1"}, regular_buses=True) is None


def test_daily_compact_split_remaps_stops_without_mutating_other_days():
    reference = {"metadata": {}, "stations": [{"name": "unused"}, {"name": "A"}, {"name": "B"}],
        "patterns": {"one": {"route_id": "1", "operator": "MBTA", "stops": [[1, 0, 0], [2, 10, 10]], "legs": ["road"]},
                     "two": {"route_id": "1", "operator": "MBTA", "stops": [[1, 0, 1], [2, 11, 11]], "legs": ["road"]}},
        "paths": {"road": {}}, "days": {"a": [["one", "trip", 100]], "b": [["two", "other", 200]]}}
    compact_reference(reference)
    assert len(reference["stop_patterns"]) == 1
    day = daily_reference(reference, "a")
    assert [s["name"] for s in day["stations"]] == ["A", "B"]
    assert next(iter(day["stop_patterns"].values()))["stations"] == [0, 1]
    assert next(iter(reference["stop_patterns"].values()))["stations"] == [1, 2]


@pytest.mark.parametrize("city,first,mode,routes", [
    ("adelaide", "2024-05-27", "light_rail", {"GLNELG", "BTANIC", "FESTVL"}),
    ("brisbane", "2026-10-05", "light_rail", {"L1"}),
    ("nyc", "2025-12-15", "commuter_rail", {"SI"}),
])
def test_new_rail_modes_follow_actual_calendars_and_have_matching_shapes(city, first, mode, routes):
    with gzip.open(ROOT / "data/reference" / city / (first + ".json.gz"), "rt") as stream:
        reference = json.load(stream)
    patterns = reference["patterns"]
    assert {p["route_id"] for p in patterns.values() if p["mode"] == mode} == routes
    assert not reference["metadata"]["omitted_trips"] and not reference["metadata"]["unresolved_geometry_patterns"]
    for day, rows in reference["days"].items():
        assert any(patterns[p]["mode"] == mode for p, _, _ in rows)
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
    if city == "adelaide":
        # Festival Plaza is calendar-driven, not copied onto every weekday.
        active = lambda day: {patterns[p]["route_id"] for p, _, _ in reference["days"][day]}
        assert "FESTVL" not in active("2024-05-27") and "FESTVL" in active("2024-06-01")
