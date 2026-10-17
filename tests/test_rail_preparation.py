import csv
import gzip
import hashlib
import io
import json
from zipfile import ZipFile

import pytest

from scripts.prepare_rail_replay import prepare
from scripts.prepare_us_rail_replay import describe_route, selected_route


def archive_fixture(path, normal_trip, service_dates):
    """Two snapshots have different trips; one old trip runs across 03:00."""
    tables = {
        "feed_info.txt": [{"feed_start_date": "20261004", "feed_end_date": "20261007", "feed_version": normal_trip}],
        "agency.txt": [{"agency_id": "1", "agency_name": "WMATA", "agency_timezone": "America/New_York"}],
        "routes.txt": [{"agency_id": "1", "route_id": "RED", "route_short_name": "R", "route_long_name": "Red", "route_type": "1", "route_color": "C80F2D"}],
        "stops.txt": [{"stop_id": "a", "stop_name": "Alpha", "stop_lon": "-77.00", "stop_lat": "38.90"},
                      {"stop_id": "b", "stop_name": "Bravo", "stop_lon": "-76.99", "stop_lat": "38.90"}],
        "calendar_dates.txt": [{"service_id": "regular", "date": day, "exception_type": "1"} for day in service_dates],
        "trips.txt": [{"route_id": "RED", "trip_id": normal_trip, "service_id": "regular", "shape_id": "curve", "direction_id": "0"}],
        "shapes.txt": [{"shape_id": "curve", "shape_pt_lon": "-77.00", "shape_pt_lat": "38.90", "shape_pt_sequence": "0", "shape_dist_traveled": "0"},
                       {"shape_id": "curve", "shape_pt_lon": "-76.99", "shape_pt_lat": "38.90", "shape_pt_sequence": "1", "shape_dist_traveled": "1"}],
        "stop_times.txt": [],
    }
    if normal_trip == "old":
        tables["trips.txt"].append({**tables["trips.txt"][0], "trip_id": "late"})
    for trip in tables["trips.txt"]:
        for index, (stop, clock) in enumerate(zip(("a", "b"), ("26:55:00", "27:10:00") if trip["trip_id"] == "late" else ("06:00:00", "06:10:00"))):
            tables["stop_times.txt"].append({"trip_id": trip["trip_id"], "stop_id": stop, "stop_sequence": str(index),
                                            "arrival_time": clock, "departure_time": clock, "shape_dist_traveled": str(index)})
    with ZipFile(path, "w") as archive:
        for filename, rows in tables.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(filename, stream.getvalue())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preparation_selects_snapshots_by_service_date_and_keeps_boundary_carry_ins(tmp_path):
    old_hash = archive_fixture(tmp_path / "old.zip", "old", ["20261004", "20261005"])
    new_hash = archive_fixture(tmp_path / "new.zip", "new", ["20261006", "20261007"])
    source = {"first": "2026-10-05", "last": "2026-10-06", "timezone": "America/New_York",
              "source": "fixture", "source_url": "https://example.test", "license": "fixture",
              "license_url": "https://example.test/license", "attribution": "fixture", "note": "fixture",
              "archives": [{"start": "2026-10-04", "end": "2026-10-05", "url": "https://example.test/old.zip", "sha256": old_hash, "captured": "2026-10-03", "published": ""},
                           {"start": "2026-10-06", "end": "2026-10-07", "url": "https://example.test/new.zip", "sha256": new_hash, "captured": "2026-10-06", "published": ""}]}
    output = tmp_path / "prepared.json.gz"
    prepare("dc", source, tmp_path, output,
            lambda route, agencies: selected_route("dc", route, agencies), lambda route, trip: describe_route("dc", route, trip))
    with gzip.open(output, "rt") as stream:
        reference = json.load(stream)
    assert {trip for _, trip, _ in reference["days"]["2026-10-05"]} == {"old", "late"}
    assert {trip for _, trip, _ in reference["days"]["2026-10-06"]} == {"new", "late"}
    assert sorted(offset for _, trip, offset in reference["days"]["2026-10-05"] if trip == "late") == [10500, 96900]
    assert [offset for _, trip, offset in reference["days"]["2026-10-06"] if trip == "late"] == [10500]
    assert not reference["metadata"]["omitted_trips"]
    assert not reference["metadata"]["unresolved_geometry_patterns"]
    assert len(reference["patterns"]) == 2
    # Reject a different ZIP rather than silently changing the historical timetable.
    source["archives"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="validated source"):
        prepare("dc", source, tmp_path, output, lambda route, agencies: True, lambda route, trip: {})


def test_preparation_rejects_dates_outside_declared_feed_validity(tmp_path):
    digest = archive_fixture(tmp_path / "old.zip", "old", ["20261004", "20261005"])
    source = {"first": "2026-10-07", "last": "2026-10-08", "timezone": "America/New_York",
              "url": "https://example.test/old.zip", "sha256": digest, "captured": "2026-10-03", "published": ""}
    with pytest.raises(ValueError, match="Feed validity"):
        prepare("dc", source, tmp_path, tmp_path / "invalid.json.gz", lambda route, agencies: True, lambda route, trip: {})
    assert not (tmp_path / "invalid.json.gz").exists()
