import csv
import gzip
import io
import json
from datetime import date, datetime
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import get_replay_day
from scripts.prepare_boston_replay import feed_for, prepare, project_stops, replay_mode


def test_shape_projection_preserves_each_occurrence_on_a_loop():
    shape = [[0, 0], [0.01, 0], [0.01, 0.01], [0, 0], [0.02, 0]]
    assert project_stops(shape, shape) == [0, 1, 2, 3, 4]


def test_shape_projection_rejects_backward_stops_and_distant_shapes():
    with pytest.raises(ValueError, match="journey order"):
        project_stops([[0, 0], [0.01, 0], [0.02, 0]], [[0.015, 0], [0.005, 0]])
    with pytest.raises(ValueError):
        project_stops([[0, 0], [0.01, 0]], [[0, 0.01], [0.01, 0.01]])


def test_rail_vehicle_override_excludes_replacement_buses():
    assert replay_mode({"trip_route_type": "3"}, {"route_type": "1"}) is None
    assert replay_mode({"trip_route_type": ""}, {"route_type": "1"}) == "subway"
    assert replay_mode({"trip_route_type": "2"}, {"route_type": "1"}) == "commuter_rail"


def test_silver_line_uses_official_line_groups_and_stays_distinct_from_other_buses():
    for group in ("line-SLWaterfront", "line-SLWashington"):
        assert replay_mode({"trip_route_type": ""}, {"route_type": "3", "line_id": group}) == "silver_line"
    assert replay_mode({"trip_route_type": ""}, {"route_type": "3", "route_long_name": "Silver Street"}) is None
    assert replay_mode({"trip_route_type": "3"}, {"route_type": "1", "line_id": "line-Red"}) is None


def test_archive_selection_uses_official_validity_windows():
    index = [{"feed_start_date": "20240613", "feed_end_date": "20240624", "archive_url": "old"},
             {"feed_start_date": "20240625", "feed_end_date": "20240626", "archive_url": "new"}]
    assert feed_for(date(2024, 6, 24), index)["archive_url"] == "old"
    assert feed_for(date(2024, 6, 25), index)["archive_url"] == "new"
    with pytest.raises(ValueError):
        feed_for(date(2024, 6, 27), index)


def test_preparation_and_loading_preserve_calendars_overnight_shared_stops_and_colors(tmp_path, monkeypatch):
    def table(rows):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    (tmp_path / "index.csv").write_text(table([{"feed_start_date": "20240623", "feed_end_date": "20240701",
        "feed_version": "fixture", "archive_url": "https://example.test/fixture.zip"}]))
    with ZipFile(tmp_path / "fixture.zip", "w") as archive:
        archive.writestr("agency.txt", table([{"agency_id": "1", "agency_name": "MBTA"}]))
        routes = [{"route_id": f"r{kind}", "agency_id": "1", "route_type": kind, "route_short_name": "",
            "route_long_name": f"Line {kind}", "route_color": "DA291C", "line_id": ""} for kind in ("0", "1", "2")]
        routes.extend([{**routes[0], "route_id": "741", "route_type": "3", "route_short_name": "SL1",
                        "route_long_name": "Airport - South Station", "route_color": "7C878E", "line_id": "line-SLWaterfront"},
                       {**routes[0], "route_id": "regular", "route_type": "3", "route_long_name": "Silver Street"}])
        archive.writestr("routes.txt", table(routes))
        archive.writestr("calendar.txt", table([{"service_id": service, "start_date": "20240623", "end_date": "20240701",
            **dict.fromkeys(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], "1")}
            for service in ("daily", "cancelled")]))
        archive.writestr("calendar_dates.txt", table([{"service_id": "cancelled", "date": "20240625", "exception_type": "2"}]))
        trips = [{"route_id": f"r{kind}", "service_id": "daily", "trip_id": f"t{kind}", "shape_id": "s",
                  "direction_id": "0", "trip_headsign": "Bravo", "trip_route_type": "", "route_pattern_id": "p"}
                 for kind in ("0", "1", "2")]
        trips.extend([{**trips[1], "trip_id": "replacement", "trip_route_type": "3"},
                      {**trips[1], "trip_id": "cancelled", "service_id": "cancelled"},
                      {**trips[1], "trip_id": "canonical", "route_pattern_id": "reference"},
                      {**trips[1], "trip_id": "silver", "route_id": "741"},
                      {**trips[1], "trip_id": "regular-bus", "route_id": "regular"}])
        archive.writestr("trips.txt", table(trips))
        archive.writestr("route_patterns.txt", table([{"route_pattern_id": "p", "route_pattern_typicality": "1"},
                                                     {"route_pattern_id": "reference", "route_pattern_typicality": "5"}]))
        archive.writestr("directions.txt", table([{"route_id": route["route_id"], "direction_id": "0", "direction": "North"}
                                                for route in routes]))
        archive.writestr("stops.txt", table([{"stop_id": stop, "stop_name": name, "stop_lon": lon, "stop_lat": "42"}
                                           for stop, name, lon in (("a", "Alpha", "-71"), ("b", "Bravo", "-70.99"))]))
        archive.writestr("shapes.txt", table([{"shape_id": "s", "shape_pt_sequence": i, "shape_pt_lon": lon, "shape_pt_lat": lat}
                                            for i, lon, lat in ((0, "-71", "42"), (1, "-70.995", "42.003"), (2, "-70.99", "42"))]))
        archive.writestr("stop_times.txt", table([{"trip_id": t["trip_id"], "stop_id": stop, "stop_sequence": i,
            "arrival_time": clock.replace("25:", "01:") if t["trip_id"] == "cancelled" else clock,
            "departure_time": clock.replace("25:", "01:") if t["trip_id"] == "cancelled" else clock} for t in trips
            for i, stop, clock in ((1, "a", "25:00:00"), (2, "b", "25:10:00"))]))
    output = tmp_path / "boston.json.gz"
    prepare(tmp_path, output)
    monkeypatch.setenv("SUNTRAIN_BOSTON_REFERENCE", str(output))
    # An inaccessible Melbourne dataset must not affect Boston.
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    day = get_replay_day("2024-06-24", "boston")
    assert day["city"] == "boston" and day["timezone"] == "America/New_York"
    assert day["passenger_data"] is False and len(day["services"]) == 4
    assert day["schedule"]["excluded"]["replacement_bus_trip_records"] == 1
    assert {s["mode"] for s in day["services"]} == {"subway", "light_rail", "commuter_rail", "silver_line"}
    for service in day["services"]:
        assert service["number"] not in ("replacement", "canonical", "cancelled", "regular-bus")
        assert "stops" not in service
        pattern = day["transit_patterns"][service["pattern"]]
        assert pattern["color"] == ("#7C878E" if service["mode"] == "silver_line" else "#DA291C")
        assert pattern["direction"] == "North"
        assert {day["stations"][s[0]]["mode"] for s in pattern["stops"]} == ({"bus"} if service["mode"] == "silver_line" else {"train"})
        if service["mode"] == "silver_line":
            assert pattern["line"] == "SL1 · Airport - South Station"
        assert all(len(stop) == 3 for stop in pattern["stops"])
        assert len(day["paths"][pattern["legs"][0]]["coordinates"]) == 3
        departure = datetime.fromtimestamp(service["departure"], ZoneInfo("America/New_York"))
        assert (departure.day, departure.hour) == (25, 1)
    assert get_replay_day("2024-06-24", "boston") is day
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2024-07-01", "boston")
    with pytest.raises(ValueError, match="Unknown"):
        get_replay_day("2024-06-24", "unknown")


def test_bundled_boston_week_has_rail_and_silver_line_with_resolved_geometry():
    from dashboard.replay import BOSTON_PATH
    with gzip.open(BOSTON_PATH, "rt") as stream:
        reference = json.load(stream)
    assert len(reference["days"]) == 7
    assert not reference["metadata"]["omitted_trips"]
    assert not reference["metadata"]["unresolved_geometry_patterns"]
    silver_routes = {p["route_id"] for p in reference["patterns"].values() if p["mode"] == "silver_line"}
    assert silver_routes == {"741", "742", "743", "746", "749", "751"}  # SL1–SL5 and SLW.
    for day, services in reference["days"].items():
        assert len({(s[1], s[2]) for s in services}) == len(services)
        assert {reference["patterns"][s[0]]["mode"] for s in services} == {"subway", "light_rail", "commuter_rail", "silver_line"}
        for pattern, _, _ in services:
            assert len(reference["patterns"][pattern]["stops"]) == len(reference["patterns"][pattern]["legs"]) + 1
    assert all(path["quality"] == "shape" for path in reference["paths"].values())
