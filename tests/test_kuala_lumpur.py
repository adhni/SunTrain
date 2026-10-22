from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.prepare_kuala_lumpur_replay import selected_route


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.KUALA_LUMPUR_PATH, "rt") as stream:
        return json.load(stream)


def test_scope_keeps_kl_rail_and_excludes_national_trains_and_brt():
    for route in ["KC05_KB18", "KA15_KD19"]:
        assert selected_route("ktmb", {"agency_id": "ktmb", "route_id": route, "route_type": "0"}, {})
    for route in ["ETS", "ERT", "SH", "ST", "SS", "100_9000", "100_47300"]:
        assert not selected_route("ktmb", {"agency_id": "ktmb", "route_id": route, "route_type": "2"}, {})
    for route in ["AG", "PH", "KJ", "SA", "KGL", "PYL", "MR"]:
        assert selected_route("rapid-rail", {"agency_id": "rapidrail", "route_id": route, "route_type": "1"}, {})
    assert not selected_route("rapid-rail", {"agency_id": "rapidrail", "route_id": "BRT", "route_type": "0"}, {})


def test_week_has_source_weekday_and_weekend_services_without_duplicate_departures(reference):
    expected = {f"2026-10-{day}": 2485 for day in range(12, 17)}
    expected.update({"2026-10-17": 2018, "2026-10-18": 2012})
    assert {day: len(rows) for day, rows in reference["days"].items()} == expected
    assert not reference["metadata"]["omitted_trips"]
    assert not reference["metadata"]["unresolved_geometry_patterns"]
    assert len(reference["patterns"]) == 72 and len(reference["stop_patterns"]) == 39
    for day, rows in reference["days"].items():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        exact = 0
        for key, trip, offset in rows:
            pattern = reference["patterns"][key]
            assert 10800 <= offset + pattern["times"][1] < 97200
            if pattern["operator"] == "KTM Komuter":
                exact += 1
                assert not pattern.get("frequency_based")
            else:
                assert pattern["frequency_based"] and ":estimate-" in trip
        assert exact == (90 if day < "2026-10-17" else 74)


def test_rapid_estimates_follow_published_departure_windows_not_first_arrival(reference):
    departures = sorted(offset + reference["patterns"][key]["times"][1]
        for key, trip, offset in reference["days"]["2026-10-12"] if trip.startswith("rapid:AGL_MonFri_0:estimate-"))
    expected = [*range(21600, 32400, 180), *range(32400, 61200, 300),
                *range(61200, 68400, 180), *range(68400, 84300, 300)]
    assert departures == expected


def test_all_nine_lines_keep_source_colours_and_connected_paths(reference):
    colours = {"KC05_KB18": "#3C5A9F", "KA15_KD19": "#DC2420", "AG": "#e57200",
               "KJ": "#D50032", "PH": "#76232f", "KGL": "#047940", "PYL": "#FFCD00",
               "MR": "#84bd00", "SA": "#FF00FF"}
    assert {p["source_route_id"] for p in reference["patterns"].values()} == set(colours)
    for pattern in reference["patterns"].values():
        assert pattern["color"] == colours[pattern["source_route_id"]]
        assert "stops" not in pattern
        assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))
        topology = reference["stop_patterns"][pattern["stop_pattern"]]
        assert len(topology["stations"]) * 2 == len(pattern["times"])
        assert len(topology["legs"]) == len(topology["stations"]) - 1
        assert all(reference["paths"][leg]["coordinates"] for leg in topology["legs"])
    assert replay.KUALA_LUMPUR_PATH.stat().st_size < 250_000


def test_existing_runtime_filters_clock_and_http_descriptor_work_for_kl():
    info = descriptor("2026-10-12", "kuala_lumpur")
    assert info["modes"] == ["light_rail", "subway", "train"]
    with pytest.raises(ValueError, match="Date outside"):
        descriptor("2024-06-24", "kuala_lumpur")
    all_modes = replay.get_replay_day("2026-10-12", "kuala_lumpur")
    assert len(all_modes["services"]) == 2485
    assert all_modes["approximate_legs"] == 0
    assert datetime.fromtimestamp(all_modes["initial"], ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d %H:%M") == "2026-10-12 08:00"
    assert all("stops" not in service and "pattern" in service for service in all_modes["services"])
    assert not CITIES["kuala_lumpur"]["passenger_data"]
    expected = {"train": 90, "subway": 567, "light_rail": 1828}
    ids = set()
    for mode, count in expected.items():
        day = replay.get_replay_day("2026-10-12", "kuala_lumpur", modes=[mode])
        assert len(day["services"]) == count
        assert all(service["mode"] == mode for service in day["services"])
        ids.update(service["id"] for service in day["services"])
    assert ids == {service["id"] for service in all_modes["services"]}
