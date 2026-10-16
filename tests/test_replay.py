from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import cumulative_distances, get_replay_day, normalize_stop_times


def local(timestamp):
    return datetime.fromtimestamp(timestamp, ZoneInfo("Australia/Melbourne"))


def test_journey_unwraps_midnight_and_continues_beyond_business_boundary():
    stops, uncertain = normalize_stop_times("2023-07-10", [
        (time(23, 59), time(0)), (time(2, 59), time(3)), (time(3, 10), time(3, 11)),
    ])
    assert not uncertain
    assert stops[0][1] - stops[0][0] == 60
    assert stops[1][1] - stops[1][0] == 60
    assert local(stops[-1][1]).isoformat() == "2023-07-11T03:11:00+10:00"


def test_early_morning_origin_belongs_to_following_calendar_day():
    stops, _ = normalize_stop_times("2023-07-10", [(time(2, 58), time(2, 59)), (time(3, 1), time(3, 2))])
    assert local(stops[0][0]).day == 11
    assert stops[1][0] - stops[0][1] == 120


def test_autumn_repeated_hour_preserves_stop_order():
    stops, uncertain = normalize_stop_times("2024-04-06", [(time(2, 59, 40), time(2)), (time(2, 2), time(2, 3))])
    assert uncertain
    assert stops[0][1] - stops[0][0] == 20
    assert local(stops[0][0]).fold == 0
    assert local(stops[0][1]).fold == 1
    assert stops[1][0] - stops[0][1] == 120


def test_spring_clock_jump_uses_elapsed_time():
    stops, uncertain = normalize_stop_times("2023-09-30", [(time(1, 59, 40), time(3)), (time(3, 2), time(3, 3))])
    assert not uncertain
    assert stops[0][1] - stops[0][0] == 20


@pytest.mark.parametrize("day,times", [
    ("2023-07-10", [(time(7, 10), time(7, 9))]),
    ("2023-09-30", [(time(2, 30), time(2, 31))]),
])
def test_bad_clock_values_do_not_create_twenty_four_hour_journeys(day, times):
    with pytest.raises(ValueError):
        normalize_stop_times(day, times)


def test_replay_loads_complete_services_from_configured_source(monkeypatch, sample_parquet, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))
    monkeypatch.setenv("SUNTRAIN_RAIL_GEOMETRY", str(tmp_path / "missing.json"))
    day = get_replay_day("2023-07-10")
    assert len(day["services"]) == 1
    service = day["services"][0]
    assert service["number"] == "1001"
    assert service["operator"] == "Metro"
    assert [day["stations"][s[0]]["name"] for s in service["stops"]] == ["Werribee", "Newport"]
    assert service["stops"][0][3:] == [0, 120, 120, 10]
    assert day["approximate_legs"] == day["total_legs"] == 1
    path = day["paths"][service["legs"][0]]
    assert path["quality"] == "approximate"
    assert path["distances"][0] == 0
    assert path["distances"][-1] > 1000
    assert get_replay_day("2023-07-10") is day
    assert get_replay_day("2023-07-11")["services"][0]["number"] == "2002"


def test_replay_empty_day_is_valid_and_dst_day_bounds_are_local(monkeypatch, sample_parquet, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))
    monkeypatch.setenv("SUNTRAIN_RAIL_GEOMETRY", str(tmp_path / "missing.json"))
    day = get_replay_day("2024-04-06")
    assert day["services"] == []
    assert day["end"] - day["start"] == 25 * 3600
    assert local(day["start"]).hour == local(day["end"]).hour == 3


def test_geometry_uses_observed_station_order_to_select_a_branch():
    from scripts.prepare_replay_geometry import build_geometry
    from dashboard.replay import pattern_key

    a, b, c, branch = [144.0, -37.0], [144.01, -37.0], [144.02, -37.0], [144.01, -37.01]
    variants = [
        {"names": ["alpha", "bravo", "charlie"], "points": [a, b, c], "operator": "Metro", "routes": "Example"},
        {"names": ["alpha", "branch", "charlie"], "points": [a, branch, c], "operator": "Metro", "routes": "Example"},
    ]
    patterns, paths = build_geometry(variants, [("Metro", "Example", ["Alpha", "Branch", "Charlie"], [a, branch, c])])
    ids = patterns[pattern_key("Metro", "Example", ["Alpha", "Branch", "Charlie"])]
    assert all(paths[i]["quality"] == "track" for i in ids)
    assert branch in paths[ids[0]]["coordinates"]
    assert b not in paths[ids[0]]["coordinates"]


def test_geometry_flags_unresolvable_express_branch():
    from scripts.prepare_replay_geometry import build_geometry
    from dashboard.replay import pattern_key

    a, b, detour = [144.0, -37.0], [144.04, -37.0], [144.02, -37.05]
    variants = [
        {"names": ["alpha", "bravo"], "points": [a, b], "operator": "Metro", "routes": "Example"},
        {"names": ["alpha", "bravo"], "points": [a, detour, b], "operator": "Metro", "routes": "Example"},
    ]
    patterns, paths = build_geometry(variants, [("Metro", "Example", ["Alpha", "Bravo"], [a, b])])
    identifier = patterns[pattern_key("Metro", "Example", ["Alpha", "Bravo"])][0]
    assert paths[identifier]["quality"] == "approximate"


def test_distances_follow_curve_instead_of_endpoint_shortcut():
    direct = cumulative_distances([[144, -37], [144.01, -37]])[-1]
    curved = cumulative_distances([[144, -37], [144.005, -37.01], [144.01, -37]])[-1]
    assert curved > direct * 2
