from datetime import date, datetime
from zoneinfo import ZoneInfo
import gzip
import json
import csv
import io
from zipfile import ZipFile

from dashboard import transit
from scripts.prepare_transit_replay import active_services, business_occurrences, seconds


def test_gtfs_service_exceptions_override_weekday_calendar():
    calendar = {"service_id": "weekday", "start_date": "20240601", "end_date": "20240701", "monday": "1"}
    exceptions = [{"service_id": "weekday", "date": "20240624", "exception_type": "2"},
                  {"service_id": "special", "date": "20240624", "exception_type": "1"}]
    assert active_services([calendar], exceptions, date(2024, 6, 24)) == {"special"}


def test_gtfs_extended_hours_and_business_boundary_do_not_shift_midnight_twice():
    day = date(2024, 6, 24)
    assert seconds("25:10:00") == 25 * 3600 + 600
    # Yesterday's 26:50 service runs into today's 03:00 business boundary.
    assert list(business_occurrences(day, [date(2024, 6, 23)], seconds("26:50:00"), seconds("27:10:00"))) == [-86400]
    assert list(business_occurrences(day, [day], seconds("01:00:00"), seconds("02:00:00"))) == []
    assert list(business_occurrences(day, [date(2024, 6, 25)], seconds("01:00:00"), seconds("02:00:00"))) == [86400]
    assert list(business_occurrences(day, [date(2024, 6, 25)], seconds("03:00:00"), seconds("04:00:00"))) == []


def test_transit_merges_station_ids_without_overwriting_trains_and_has_no_passenger_counts(tmp_path):
    reference = {"metadata": {"source_date": "2024-06-24"},
        "stations": [{"name": "Tram stop", "lat": -37.8, "lon": 145}, {"name": "Bus stop", "lat": -37.9, "lon": 145}],
        "paths": {"gtfs-x": {"coordinates": [[145, -37.8], [145, -37.9]], "quality": "shape", "distances": [0, 100]}},
        "patterns": {"p": {"mode": "tram", "operator": "PTV tram", "line": "Tram 1", "direction": "A",
            "origin": "Tram stop", "destination": "Bus stop", "stops": [[0, 0, 0], [1, 600, 600]], "legs": ["gtfs-x"]}},
        "days": {"2024-06-24": [["p", "trip-1", 8 * 3600]]}}
    path = tmp_path / "transit.json.gz"
    with gzip.open(path, "wt") as stream:
        json.dump(reference, stream)
    day = {"business_date": "2024-06-24", "stations": [{"name": "Train station"}], "services": [{"mode": "train"}],
           "paths": {"rail": {}}, "approximate_legs": 0, "total_legs": 1}
    transit.add_transit(day, (str(path), path.stat().st_mtime_ns))
    assert len(day["services"]) == 2
    service = day["services"][1]
    assert "load" not in service and "stops" not in service
    assert day["transit_patterns"]["p"]["stops"] == [[1, 0, 0], [2, 600, 600]]
    assert datetime.fromtimestamp(service["departure"], ZoneInfo("Australia/Melbourne")).hour == 8
    assert day["paths"]["rail"] == {}
    assert day["transit"]["available"]
    assert day["total_legs"] == 2 and day["approximate_legs"] == 0


def test_outside_shared_week_and_missing_reference_preserve_train_replay(tmp_path):
    day = {"business_date": "2023-07-10", "services": [{"mode": "train"}]}
    transit.add_transit(day, (str(tmp_path / "absent.json.gz"), 0))
    assert day["services"] == [{"mode": "train"}]
    assert not day["transit"]["available"]


def test_preparation_keeps_valid_schedules_with_missing_shapes_as_gaps(tmp_path):
    from scripts.prepare_transit_replay import prepare

    def table(rows):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue()

    archive_path = tmp_path / "gtfs.zip"
    with ZipFile(archive_path, "w") as outer:
        for branch, route_type in (("3", "0"), ("4", "3")):
            content = io.BytesIO()
            with ZipFile(content, "w") as archive:
                archive.writestr("calendar.txt", table([{"service_id": "daily", "start_date": "20240620", "end_date": "20240702",
                    **dict.fromkeys(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], "1")}]))
                archive.writestr("calendar_dates.txt", "service_id,date,exception_type\n")
                archive.writestr("routes.txt", table([{"route_id": "r", "route_type": route_type, "route_short_name": "1", "route_long_name": "Example"}]))
                archive.writestr("trips.txt", table([{"trip_id": "trip", "route_id": "r", "service_id": "daily", "direction_id": "0", "shape_id": "shape"}]))
                archive.writestr("stops.txt", table([{"stop_id": "a", "stop_name": "Alpha", "stop_lat": "-37.8", "stop_lon": "145"},
                    {"stop_id": "b", "stop_name": "Bravo", "stop_lat": "-37.81", "stop_lon": "145"}]))
                archive.writestr("stop_times.txt", table([
                    {"trip_id": "trip", "stop_id": "a", "stop_sequence": "1", "arrival_time": "25:00:00", "departure_time": "25:00:00", "shape_dist_traveled": ""},
                    {"trip_id": "trip", "stop_id": "b", "stop_sequence": "2", "arrival_time": "25:10:00", "departure_time": "25:10:00", "shape_dist_traveled": ""}]))
                archive.writestr("shapes.txt", "shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon,shape_dist_traveled\n")
            outer.writestr(f"{branch}/google_transit.zip", content.getvalue())
    output = tmp_path / "reference.json.gz"
    prepare(archive_path, output)
    with gzip.open(output, "rt") as stream:
        reference = json.load(stream)
    assert len(reference["days"]["2024-06-24"]) == 2
    for pattern in reference["patterns"].values():
        assert pattern["legs"] == ["gtfs-unresolved"]
        assert pattern["direction"] == "A"
        assert reference["paths"][pattern["legs"][0]]["coordinates"] == []
    assert all(row[2] == 25 * 3600 for row in reference["days"]["2024-06-24"])
    assert reference["metadata"]["omitted_trips"] == {"tram": 0, "bus": 0}
