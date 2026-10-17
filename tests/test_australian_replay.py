import gzip
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from dashboard.cities import city_settings
from dashboard.replay import cumulative_distances, get_replay_day
from scripts.prepare_australian_replay import SOURCES, path_legs, selected_route

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("city", SOURCES)
def test_bundled_rail_has_valid_calendars_references_geometry_and_shared_schedules(city):
    source = SOURCES[city]
    filename = ROOT / "data/reference" / city / (source["first"] + ".json.gz")
    with gzip.open(filename, "rt") as stream:
        reference = json.load(stream)
    patterns, paths = reference["patterns"], reference["paths"]
    first, last = date.fromisoformat(source["first"]), date.fromisoformat(source["last"])
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range((last - first).days + 1)}
    assert reference["metadata"]["sources"][0]["sha256"] == source["sha256"]
    assert not reference["metadata"]["omitted_trips"]
    for day, rows in reference["days"].items():
        assert rows and len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert all(p in patterns for p, _, _ in rows)
    for pattern in patterns.values():
        assert pattern["mode"] in {"train", "subway"}
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert pattern["stops"][0][1] == 0
        flat = [t for stop in pattern["stops"] for t in stop[1:]]
        assert all(b >= a for a, b in zip(flat, flat[1:]))
        for i, key in enumerate(pattern["legs"]):
            path = paths[key]
            if path["quality"] == "approximate":
                assert path["coordinates"] == path["distances"] == []
                continue
            assert len(path["coordinates"]) == len(path["distances"]) >= 2
            assert path["distances"][0] == 0
            for index, point in ((i, path["coordinates"][0]), (i + 1, path["coordinates"][-1])):
                stop = reference["stations"][pattern["stops"][index][0]]
                assert cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151


@pytest.mark.parametrize("city", SOURCES)
def test_city_loader_has_correct_local_clock_and_never_queries_melbourne_warehouse(city, monkeypatch, tmp_path):
    source = SOURCES[city]
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "unavailable.parquet"))
    day = get_replay_day(source["first"], city)
    clock = datetime.fromtimestamp(day["initial"], ZoneInfo(source["timezone"]))
    assert clock.date().isoformat() == source["first"] and clock.hour == 8
    assert day["timezone"] == source["timezone"]
    assert not day["passenger_data"]
    assert all("stops" not in service for service in day["services"])
    assert len(day["transit_patterns"]) < len(day["services"])
    assert day["schedule"]["attribution"] == source["attribution"]
    assert city_settings(city)["start_date"] == source["first"]
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2000-01-01", city)


def test_sydney_scope_excludes_trainlink_and_replacement_buses():
    assert selected_route("sydney", {"agency_id": "x0001", "route_type": "2"}, {})
    assert selected_route("sydney", {"agency_id": "SMNW", "route_type": "401"}, {})
    assert not selected_route("sydney", {"agency_id": "x0001", "route_type": "700"}, {})
    assert not selected_route("sydney", {"agency_id": "X0000", "route_type": "2"}, {})
    assert not selected_route("sydney", {"agency_id": "711", "route_type": "106"}, {})
    with gzip.open(ROOT / "data/reference/sydney/2026-10-05.json.gz", "rt") as stream:
        reference = json.load(stream)
    assert {p["route_id"] for p in reference["patterns"].values()} == {"M1", *[f"T{i}" for i in range(1, 10)]}
    assert {p["operator"] for p in reference["patterns"].values()} == {"Sydney Trains", "Sydney Metro"}
    assert not reference["metadata"]["unresolved_geometry_patterns"]


def test_native_distance_anchors_preserve_long_loop_instead_of_shortcut():
    points = [[151, -33], [151.01, -33], [151.01, -33.01], [151, -33.01], [151, -33]]
    raw = [(i, i * 1000, p) for i, p in enumerate(points)]
    legs = path_legs(raw, [0, 4000], [points[0], points[0]])
    assert len(legs[0]) == 5
    assert cumulative_distances(legs[0])[-1] > 4000
    with pytest.raises(ValueError, match="backwards"):
        path_legs(raw, [4000, 0], [points[0], points[0]])
