import gzip
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import NYC_PATH, get_replay_day
from scripts.prepare_nyc_replay import day_windows, occurrences, source_for


def test_cross_year_period_label_keeps_both_years_visible():
    from dashboard.replay_view import period_label
    assert period_label("2025-12-15", "2026-01-18") == "15 Dec 2025–18 Jan 2026"
    assert period_label("2024-06-24", "2024-06-30") == "24 Jun–30 Jun 2024"


def test_occurrences_preserve_gtfs_extended_hours_and_business_boundary_carry_ins():
    day = date(2025, 11, 24)
    windows = day_windows([day, day + timedelta(days=1)])
    assert list(occurrences([day], 26 * 3600 + 50 * 60, 27 * 3600 + 10 * 60, windows)) == [
        ("2025-11-24", 96600), ("2025-11-25", 10200)]
    assert list(occurrences([day + timedelta(days=1)], 3600, 4200, windows)) == [("2025-11-24", 90000)]
    assert list(occurrences([day + timedelta(days=1)], 3 * 3600, 4 * 3600, windows)) == [("2025-11-25", 10800)]


def test_nyc_bundled_subway_routes_shuttles_geometry_and_service_calendars():
    with gzip.open(NYC_PATH, "rt") as stream:
        reference = json.load(stream)
    first = date(2025, 12, 15)
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(35)}
    assert not reference["metadata"]["omitted_trips"]
    patterns = reference["patterns"]
    route_ids = {p["route_id"] for p in patterns.values()}
    assert len(route_ids) == 29 and "SI" in route_ids
    assert {"6X", "7X", "FX", "FS", "GS", "H"} <= route_ids
    shuttles = {p["line"] for p in patterns.values() if p["route_id"] in {"FS", "GS", "H"}}
    assert len(shuttles) == 3
    local = [p for p in patterns.values() if p["route_id"] == "7"]
    express = [p for p in patterns.values() if p["route_id"] == "7X"]
    names = lambda p: {reference["stations"][stop[0]]["name"] for stop in p["stops"]}
    assert any(names(e) < names(l) for e in express for l in local
               if (e["origin"], e["destination"], e["direction"]) == (l["origin"], l["destination"], l["direction"]))
    for day, rows in reference["days"].items():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert {"FS", "GS", "H"} <= {patterns[p]["route_id"] for p, _, _ in rows}
    for pattern in patterns.values():
        assert pattern["mode"] == ("commuter_rail" if pattern["route_id"] == "SI" else "subway") and pattern["operator"] == "MTA NYCT"
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert pattern["direction"] in {"Northbound", "Southbound", "Direction A", "Direction B"}
        for identifier in pattern["legs"]:
            path = reference["paths"][identifier]
            if path["quality"] == "approximate":
                assert path["coordinates"] == []
            else:
                assert path["quality"] == "shape" and len(path["coordinates"]) >= 2
    assert len(reference["metadata"]["sources"]) == 1
    assert reference["metadata"]["sources"][0]["valid_from"] == "2025-12-08"
    assert not reference["metadata"]["unresolved_geometry_patterns"]


def test_future_dated_timetable_is_not_applied_on_its_download_date():
    assert source_for(date(2025, 12, 6))["captured"] == "2025-11-01"
    assert source_for(date(2025, 12, 7))["captured"] == "2025-11-01"
    assert source_for(date(2025, 12, 8))["captured"] == "2025-12-05"


def test_nyc_loading_uses_new_york_time_and_shared_patterns_without_other_networks(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    day = get_replay_day("2025-12-15", "nyc")
    assert day["city_name"] == "New York City" and day["passenger_data"] is False
    assert datetime.fromtimestamp(day["initial"], ZoneInfo(day["timezone"])).isoformat() == "2025-12-15T08:00:00-05:00"
    assert all("stops" not in service for service in day["services"])
    assert "MTA NYC Subway" in day["schedule"]["source"]
    assert any(p["route_id"] == "SI" and p["color"] == "#08179C" for p in day["transit_patterns"].values())
    assert get_replay_day("2025-12-15", "nyc") is day
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2024-06-24", "nyc")
