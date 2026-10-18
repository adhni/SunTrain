from schedule_helpers import expanded_reference, expanded_pattern
import gzip
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dashboard.cities import city_settings
from dashboard.replay import DC_PATH, SF_BAY_PATH, cumulative_distances, get_replay_day
from scripts.prepare_rail_replay import source_for
from scripts.prepare_us_rail_replay import SOURCES, selected_route


def test_rail_scopes_exclude_replacement_buses_and_other_operators():
    dc_agency = {"1": {"agency_name": "WMATA"}}
    rail = {"agency_id": "1", "route_id": "RED", "route_type": "1"}
    assert selected_route("dc", rail, dc_agency)
    assert not selected_route("dc", {**rail, "route_id": "SHUTTLE", "route_type": "3"}, dc_agency)
    assert not selected_route("dc", rail, {"1": {"agency_name": "VRE"}})
    bart_agency = {"BART": {"agency_name": "Bay Area Rapid Transit"}}
    bart = {"route_id": "19", "route_short_name": "Grey-N", "route_type": "1"}
    assert selected_route("sf_bay", bart, bart_agency)
    assert not selected_route("sf_bay", {**bart, "route_short_name": "BridgeA", "route_type": "3"}, bart_agency)
    assert not selected_route("sf_bay", bart, {"BART": {"agency_name": "Caltrain"}})


def test_dc_uses_each_snapshot_only_for_its_selected_service_dates():
    archives = SOURCES["dc"]["archives"]
    assert source_for(date(2026, 10, 6), archives)["captured"] == "2026-10-03"
    assert source_for(date(2026, 10, 7), archives)["captured"] == "2026-10-07"
    with pytest.raises(ValueError, match="exactly one"):
        source_for(date(2026, 10, 13), archives)
    with pytest.raises(ValueError, match="exactly one"):
        source_for(date(2026, 10, 7), [archives[1], archives[1]])


@pytest.mark.parametrize("city,path", [("dc", DC_PATH), ("sf_bay", SF_BAY_PATH)])
def test_bundled_weeks_have_complete_shared_schedules_and_verified_geometry(city, path):
    with gzip.open(path, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    source = SOURCES[city]
    first = date.fromisoformat(source["first"])
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(7)}
    metadata, patterns = reference["metadata"], reference["patterns"]
    assert not metadata["omitted_trips"]
    assert metadata["unresolved_geometry_patterns"] == {"Stops do not match shape in journey order within 150 m": 1}
    expected = {"RED", "BLUE", "ORANGE", "SILVER", "GREEN", "YELLOW"} if city == "dc" else {"Red", "Blue", "Orange", "Grey", "Green", "Yellow"}
    assert {p["route_id"] for p in patterns.values()} == expected
    for pattern in patterns.values():
        assert pattern["mode"] == "subway"
        assert pattern["direction"] in ({"Direction A", "Direction B"} if city == "dc" else {"North", "South"})
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert pattern["stops"][0][1] == 0
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        times = [t for stop in pattern["stops"] for t in stop[1:]]
        assert all(b >= a for a, b in zip(times, times[1:]))
        for index, leg in enumerate(pattern["legs"]):
            path = reference["paths"][leg]
            if path["quality"] == "approximate":
                assert path["coordinates"] == path["distances"] == []
                assert pattern["route_id"] == ("RED" if city == "dc" else "Yellow")
                continue
            assert path["quality"] == "shape" and len(path["coordinates"]) >= 2
            assert path["distances"][0] == 0 and len(path["coordinates"]) == len(path["distances"])
            assert all(b >= a for a, b in zip(path["distances"], path["distances"][1:]))
            for station_index, point in ((index, path["coordinates"][0]), (index + 1, path["coordinates"][-1])):
                stop = reference["stations"][pattern["stops"][station_index][0]]
                assert cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151
    for day, rows in reference["days"].items():
        assert rows and len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert {patterns[p]["route_id"] for p, _, _ in rows} == expected
        affected = sum(trip in metadata["unresolved_geometry_trips"] for _, trip, _ in rows)
        assert affected == (4 if city == "sf_bay" else 2 if day == source["last"] else 3)
    if city == "dc":
        assert [s["sha256"] for s in metadata["sources"]] == [s["sha256"] for s in source["archives"]]
        assert metadata["native_anchor_patterns"] == 0
        assert {p["color"] for p in patterns.values() if p["route_id"] == "SILVER"} == {"#919D9D"}
    else:
        assert metadata["sources"][0]["sha256"] == source["sha256"]
        # Keep the airport connector as rail while grouping the direction-specific routes.
        assert {p["source_route_id"] for p in patterns.values() if p["route_id"] == "Grey"} == {"19", "20"}
        assert {p["line"] for p in patterns.values() if p["route_id"] == "Grey"} == {"Oakland Airport connector"}
        assert metadata["sources"][0]["valid_through"] == "20260830"


@pytest.mark.parametrize("city", ["dc", "sf_bay"])
def test_all_us_rail_days_load_with_local_time_and_without_passenger_warehouse(city, monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    source = SOURCES[city]
    first = date.fromisoformat(source["first"])
    for i in range(7):
        day = str(first + timedelta(days=i))
        payload = get_replay_day(day, city)
        clock = datetime.fromtimestamp(payload["initial"], ZoneInfo(payload["timezone"]))
        assert clock.hour == 8 and str(clock.date()) == day
        assert clock.utcoffset().total_seconds() == (-4 if city == "dc" else -7) * 3600
        assert payload["passenger_data"] is False and payload["services"]
        assert all("stops" not in service for service in payload["services"])
        assert len(payload["transit_patterns"]) < len(payload["services"])
        unresolved = sum(any(payload["paths"][leg]["quality"] == "approximate" for leg in
                             expanded_pattern(payload, payload["transit_patterns"][service["pattern"]])["legs"]) for service in payload["services"])
        assert unresolved == (4 if city == "sf_bay" else 2 if day == source["last"] else 3)
        assert "variant has unresolved source geometry" in payload["schedule"]["replay_note"]
        assert payload["schedule"]["license_url"] == source["license_url"]
        assert city_settings(city)["start_date"] == source["first"]
    with pytest.raises(ValueError, match="covers"):
        get_replay_day(str(first - timedelta(days=1)), city)
