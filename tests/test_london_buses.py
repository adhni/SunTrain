import csv
import gzip
import io
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import pytest
from dash.exceptions import PreventUpdate

from dashboard import replay, transit
from scripts import prepare_london_buses as buses
from scripts.prepare_australian_replay import file_hash


def test_bus_scope_excludes_same_number_regional_routes_other_modes_and_replacements():
    agencies = {"london": {"agency_noc": "GAHL"}, "regional": {"agency_noc": "OXBC"}}
    route = {"route_id": "one", "route_short_name": "1", "route_type": "3", "agency_id": "london"}
    assert buses.selected_route(route, agencies, {"1": ["GAHL"]})
    for change in ({"agency_id": "regional"}, {"route_type": "200"}, {"route_type": "1"}, {"route_short_name": "UL1"}):
        assert not buses.selected_route({**route, **change}, agencies, {"1": ["GAHL"]})


def test_bus_paths_follow_ordered_road_curves_and_leave_unmatched_legs_empty():
    a, bend, b, c = [-0.1, 51.5], [-0.095, 51.502], [-0.09, 51.5], [-0.08, 51.5]
    variants = [{"relation": "1:1:1", "coordinates": [a, bend, b, c]}]
    curves = buses.resolve_geometry(variants, [a, b, c])
    assert curves[0][1] == bend
    partial = buses.resolve_geometry(variants, [a, b, [-0.08, 51.6]])
    assert partial[0] and partial[1] is None


def fixture(tmp_path):
    a, b = [-0.1, 51.5], [-0.09, 51.5]
    reference = tmp_path / "roads.json.gz"
    buses.save({"operators": {"1": ["GAHL"]}, "lines": {"1": [{"relation": "1:1:1", "coordinates": [a, [-0.095, 51.501], b]}]}}, reference)
    tables = {
        "feed_info.txt": [{"feed_start_date": "20261004", "feed_end_date": "20261012", "feed_version": "fixture"}],
        "agency.txt": [{"agency_id": "london", "agency_name": "Go Ahead London", "agency_noc": "GAHL", "agency_timezone": "Europe/London"}],
        "routes.txt": [{"route_id": "one", "route_short_name": "1", "route_type": "3", "agency_id": "london"}],
        "trips.txt": [{"route_id": "one", "trip_id": t, "service_id": "daily" if t == "night" else "regular", "direction_id": "0", "trip_headsign": "Bravo"} for t in ["normal", "duplicate", "night", "frequency"]],
        "stops.txt": [{"stop_id": key, "stop_name": name, "stop_lon": lon, "stop_lat": lat} for key, name, (lon, lat) in [("a", "Alpha", a), ("b", "Bravo", b)]],
        "calendar.txt": [{"service_id": service, "start_date": "20261004", "end_date": "20261012", **dict.fromkeys(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], "1")} for service in ["daily", "regular"]],
        "calendar_dates.txt": [{"service_id": "regular", "date": "20261007", "exception_type": "2"}],
        "frequencies.txt": [{"trip_id": "frequency", "start_time": "08:00:00", "end_time": "09:00:00", "headway_secs": "600", "exact_times": "0"}],
        "stop_times.txt": [],
    }
    for trip in tables["trips.txt"]:
        for i, clock in enumerate(["26:55:00", "27:10:00"] if trip["trip_id"] == "night" else ["08:00:00", "08:10:00"]):
            tables["stop_times.txt"].append({"trip_id": trip["trip_id"], "stop_id": ["a", "b"][i], "stop_sequence": i,
                                            "arrival_time": clock, "departure_time": clock})
    archive_path = tmp_path / "itm_london_gtfs_20261005.zip"
    with ZipFile(archive_path, "w") as archive:
        for name, rows in tables.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name, stream.getvalue())
    return archive_path, reference


def test_bus_preparation_applies_calendars_deduplicates_and_does_not_invent_frequency_departures(tmp_path, monkeypatch):
    archive, reference = fixture(tmp_path)
    monkeypatch.setattr(buses, "GTFS_SHA256", file_hash(archive))
    monkeypatch.setattr(buses, "REFERENCE_SHA256", file_hash(reference))
    output = tmp_path / "days"
    buses.prepare(tmp_path, reference, output)
    with gzip.open(output / "2026-10-05.json.gz", "rt") as stream:
        monday = json.load(stream)
    with gzip.open(output / "2026-10-07.json.gz", "rt") as stream:
        wednesday = json.load(stream)
    assert len(monday["days"]["2026-10-05"]) == 3  # One regular trip, previous and current night carry-ins.
    assert all(trip == "night" for _, trip, _ in wednesday["days"]["2026-10-07"])
    assert monday["metadata"]["omitted_trips"] == {"Non-exact frequency service": 1}
    assert monday["metadata"]["deduplicated_occurrences"]["2026-10-05"] == 1
    assert all("stops" not in p and len(p["times"]) == 2 * len(monday["stop_patterns"][p["stop_pattern"]]["stations"]) for p in monday["patterns"].values())
    assert all(p["color"] == "#DC241F" and p["mode"] == "bus" for p in monday["patterns"].values())
    assert all(path["quality"] == "shape" and len(path["coordinates"]) == 3 for path in monday["paths"].values())


def test_london_rail_only_never_reads_bus_bundle_and_append_does_not_mutate_it(tmp_path, monkeypatch):
    base = replay.get_replay_day("2026-10-05", "london")
    rail_services, rail_stations, rail_patterns = len(base["services"]), len(base["stations"]), len(base["transit_patterns"])
    archive, reference = fixture(tmp_path)
    monkeypatch.setattr(buses, "GTFS_SHA256", file_hash(archive))
    monkeypatch.setattr(buses, "REFERENCE_SHA256", file_hash(reference))
    buses.prepare(tmp_path, reference, tmp_path / "bus")
    monkeypatch.setenv("SUNTRAIN_LONDON_BUS_REFERENCE", str(tmp_path / "bus"))
    assert replay.get_replay_day("2026-10-05", "london") is base

    payload = replay.get_replay_day("2026-10-05", "london", include_buses=True)
    assert payload["bus_data_loaded"] and payload["revision"] != base["revision"]
    assert len(payload["services"]) == rail_services + 3
    assert len(payload["transit_patterns"]) > rail_patterns
    assert len(base["services"]) == rail_services and len(base["stations"]) == rail_stations
    assert len(base["transit_patterns"]) == rail_patterns
    assert not any(s["mode"] == "bus" for s in base["services"])
    assert all("stops" not in s for s in payload["services"])
    bus = next(s for s in payload["services"] if s["mode"] == "bus")
    assert datetime.fromtimestamp(bus["departure"], ZoneInfo("Europe/London")).utcoffset().total_seconds() == 3600
    pattern = payload["transit_patterns"][bus["pattern"]]
    assert payload["stations"][payload["transit_stop_patterns"][pattern["stop_pattern"]]["stations"][0]]["name"] == "Alpha"
    monkeypatch.setenv("SUNTRAIN_LONDON_BUS_REFERENCE", str(tmp_path / "absent"))
    assert replay.get_replay_day("2026-10-05", "london") is base


@pytest.mark.parametrize("business,count", [("2026-10-05", 105876), ("2026-10-11", 81656)])
def test_prepared_bus_days_keep_flat_times_road_paths_and_unique_occurrences(business, count):
    path = Path(__file__).resolve().parents[1] / "data/reference/london/bus" / (business + ".json.gz")
    assert path.stat().st_size < 13000000
    with gzip.open(path, "rt") as stream:
        reference = json.load(stream)
    rows, patterns, topologies = reference["days"][business], reference["patterns"], reference["stop_patterns"]
    assert len(rows) == count and len({(trip, offset) for _, trip, offset in rows}) == count
    assert reference["metadata"]["sha256"] == buses.GTFS_SHA256
    assert not reference["metadata"]["omitted_trips"]
    assert len(topologies) < len(patterns) / 10
    assert not {"246", "653"} & {p["route_id"] for p in patterns.values()}
    assert any(p["route_id"].startswith("N") for p in patterns.values())
    for pattern in patterns.values():
        assert pattern["mode"] == "bus" and pattern["color"] == "#DC241F"
        assert "stops" not in pattern and "legs" not in pattern
        stops = topologies[pattern["stop_pattern"]]["stations"]
        assert len(stops) * 2 == len(pattern["times"])
        assert all(b >= a for a, b in zip(pattern["times"], pattern["times"][1:]))
    for topology in topologies.values():
        assert len(topology["legs"]) + 1 == len(topology["stations"])
        assert all(0 <= s < len(reference["stations"]) for s in topology["stations"])
    for path in reference["paths"].values():
        assert path["quality"] in {"shape", "approximate"}
        assert bool(path["coordinates"]) == (path["quality"] == "shape")
