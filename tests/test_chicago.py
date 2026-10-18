from schedule_helpers import expanded_reference, expanded_pattern
import gzip
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import CHICAGO_PATH, get_replay_day
from scripts.prepare_chicago_replay import RAIL_ROUTES, shape_legs


def test_native_anchors_preserve_repeated_loop_stops_and_each_curve():
    points = [[-87.63, 41.88], [-87.62, 41.88], [-87.62, 41.89], [-87.63, 41.88], [-87.64, 41.88]]
    raw = [(i, i * 1000, point) for i, point in enumerate(points)]
    paths = {}
    legs = shape_legs(raw, [0, 1000, 2000, 3000, 4000], points, paths)
    assert [paths[p]["coordinates"] for p in legs] == [[a, b] for a, b in zip(points, points[1:])]
    assert paths[legs[2]]["coordinates"][-1] == points[0]
    assert all(paths[p]["quality"] == "shape" for p in legs)


def test_bad_native_anchors_and_distant_stations_are_rejected():
    raw = [(0, 0, [-87.63, 41.88]), (1, 1000, [-87.62, 41.88])]
    with pytest.raises(ValueError, match="backwards"):
        shape_legs(raw, [1000, 0], [[-87.62, 41.88], [-87.63, 41.88]], {})
    with pytest.raises(ValueError, match="150 m"):
        shape_legs(raw, [0, 1000], [[-87.63, 41.90], [-87.62, 41.90]], {})


def test_chicago_bundle_has_five_historical_weeks_all_eight_lines_and_no_bus_data():
    with gzip.open(CHICAGO_PATH, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    first = date(2025, 11, 24)
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(35)}
    assert reference["metadata"]["timezone"] == "America/Chicago"
    assert len(reference["metadata"]["sources"]) == 2
    assert not reference["metadata"]["omitted_trips"]
    assert not reference["metadata"]["unresolved_geometry_patterns"]
    assert {p["operator"] for p in reference["patterns"].values()} == {"CTA"}
    for day, rows in reference["days"].items():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert {reference["patterns"][p]["route_id"] for p, _, _ in rows} == RAIL_ROUTES
    for pattern in reference["patterns"].values():
        assert pattern["mode"] == "subway"
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert all(reference["paths"][leg]["quality"] == "shape" for leg in pattern["legs"])
    # The real Brown Line revisits Merchandise Mart on different platform IDs.
    # Its two visits must enclose the complete downtown Loop, not a shortcut.
    brown = next(p for p in reference["patterns"].values() if p["route_id"] == "Brn" and p["origin"] == p["destination"])
    names = [reference["stations"][s[0]]["name"] for s in brown["stops"]]
    first_mart, second_mart = [i for i, name in enumerate(names) if name == "Merchandise Mart"]
    loop = brown["legs"][first_mart:second_mart]
    assert len(loop) >= 8
    assert sum(reference["paths"][leg]["distances"][-1] for leg in loop) > 3000


def test_chicago_day_is_local_compact_and_independent_of_melbourne_warehouse(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    day = get_replay_day("2025-11-24", "chicago")
    assert day["city"] == "chicago" and day["passenger_data"] is False
    zone = ZoneInfo("America/Chicago")
    assert datetime.fromtimestamp(day["initial"], zone).isoformat() == "2025-11-24T08:00:00-06:00"
    assert datetime.fromtimestamp(day["end"], zone).isoformat() == "2025-11-25T03:00:00-06:00"
    assert all("stops" not in service for service in day["services"])
    assert get_replay_day("2025-11-24", "chicago") is day
    assert day["schedule"]["source"].startswith("Chicago Transit Authority")
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2024-06-24", "chicago")
    # Same browser date must still respect each city's distinct supported period.
    assert get_replay_day("2024-06-24", "boston")["city"] == "boston"
    assert get_replay_day("2025-11-24", "chicago")["city"] == "chicago"
