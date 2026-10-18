from schedule_helpers import expanded_reference, expanded_pattern
import gzip
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dashboard.cities import city_settings
from dashboard.replay import TORONTO_PATH, cumulative_distances, get_replay_day
from scripts.prepare_toronto_replay import SOURCE, selected_route


def test_ttc_scope_keeps_rapid_transit_but_not_streetcars_or_replacement_buses():
    agencies = {"1": {"agency_name": "TTC"}, "2": {"agency_name": "Another operator"}}
    route = lambda line, kind, agency="1": {"agency_id": agency, "route_short_name": line, "route_type": kind}
    for line in ("1", "2", "4"):
        assert selected_route(route(line, "1"), agencies)
    for line in ("5", "6"):
        assert selected_route(route(line, "0"), agencies)
        assert not selected_route(route(line, "3"), agencies)
    for line in ("501", "504", "510", "301"):
        assert not selected_route(route(line, "0"), agencies)
    assert not selected_route(route("3", "1"), agencies)
    assert not selected_route(route("1", "1", "2"), agencies)


def test_toronto_bundle_covers_one_week_with_complete_compact_schedules_and_paths():
    with gzip.open(TORONTO_PATH, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    first = date.fromisoformat(SOURCE["first"])
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(7)}
    metadata, patterns = reference["metadata"], reference["patterns"]
    assert not metadata["omitted_trips"]
    assert metadata["unresolved_geometry_patterns"] == {
        "Stops do not match shape in journey order within 150 m": 1,
        "Native stop anchor more than 150 m from station": 1,
    }
    assert len(metadata["unresolved_geometry_trips"]) == 30
    assert metadata["sources"][0]["sha256"] == SOURCE["sha256"]
    assert "Contains information licensed under the Open Government Licence" in metadata["attribution"]
    assert {p["route_id"] for p in patterns.values()} == {"1", "2", "4", "5", "6"}
    colors = {"1": "#D5C82B", "2": "#008000", "4": "#B300B3", "5": "#FF8000", "6": "#808080"}
    for pattern in patterns.values():
        assert pattern["operator"] == "TTC"
        assert pattern["mode"] == ("light_rail" if pattern["route_id"] in {"5", "6"} else "subway")
        assert pattern["color"] == colors[pattern["route_id"]]
        assert pattern["direction"] in {"Direction A", "Direction B"}
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert pattern["stops"][0][1] == 0
        times = [t for stop in pattern["stops"] for t in stop[1:]]
        assert all(b >= a for a, b in zip(times, times[1:]))
        assert len(pattern["legs"]) == len(pattern["stops"]) - 1
        for index, key in enumerate(pattern["legs"]):
            path = reference["paths"][key]
            if path["quality"] == "approximate":
                assert pattern["route_id"] == "1"
                assert path["coordinates"] == path["distances"] == []
                assert pattern["origin"] in {"Sheppard West Station - Northbound Platform", "St Clair Station - Southbound Platform"}
                continue
            assert path["quality"] == "shape"
            assert len(path["coordinates"]) == len(path["distances"]) >= 2
            assert path["distances"][0] == 0
            assert all(b >= a for a, b in zip(path["distances"], path["distances"][1:]))
            for stop_index, point in ((index, path["coordinates"][0]), (index + 1, path["coordinates"][-1])):
                station = reference["stations"][pattern["stops"][stop_index][0]]
                assert cumulative_distances([[station["lon"], station["lat"]], point])[-1] <= 151
    for day, rows in reference["days"].items():
        assert rows and len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert {patterns[p]["route_id"] for p, _, _ in rows} == set(colors)
        assert sum(trip in metadata["unresolved_geometry_trips"] for _, trip, _ in rows) == (
            4 if day == "2026-10-10" else 10 if day == "2026-10-11" else 16)
    # The U-shaped Line 1 must travel around downtown, rather than cut between its northern arms.
    through = [p for p in patterns.values() if p["route_id"] == "1" and len(p["stops"]) >= 38]
    assert through
    for pattern in through:
        assert sum(reference["paths"][leg]["distances"][-1] for leg in pattern["legs"]) > 35000
        points = [point for leg in pattern["legs"] for point in reference["paths"][leg]["coordinates"]]
        assert min(lat for lon, lat in points) < 43.65


@pytest.mark.parametrize("day", [f"2026-10-{i:02}" for i in range(5, 12)])
def test_toronto_days_load_locally_with_toronto_clock_and_no_passenger_claims(day, monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    payload = get_replay_day(day, "toronto")
    assert payload["city_name"] == "Toronto" and payload["passenger_data"] is False
    assert datetime.fromtimestamp(payload["initial"], ZoneInfo(payload["timezone"])).isoformat() == day + "T08:00:00-04:00"
    assert payload["end"] - payload["start"] == 86400
    assert payload["services"] and all("stops" not in s for s in payload["services"])
    assert len(payload["transit_patterns"]) < len(payload["services"])
    assert payload["approximate_legs"] < payload["total_legs"] / 100
    assert "Two Line 1 journey variants" in payload["schedule"]["replay_note"]
    assert city_settings("toronto")["start_date"] == SOURCE["first"]
    assert payload["schedule"]["license_url"] == "https://open.toronto.ca/open-data-licence/"
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2026-10-12", "toronto")
