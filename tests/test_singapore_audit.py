import csv
import io
from datetime import date
from zipfile import ZipFile

import pytest

from scripts.audit_singapore_gtfs import audit, download


def timetable(tmp_path, *, backwards=False):
    filename = tmp_path / "train.zip"
    files = {
        "agency.txt": [{"agency_id": "SMRT", "agency_name": "SMRT", "agency_timezone": "Asia/Singapore"}],
        "routes.txt": [{"route_id": "NS", "agency_id": "SMRT", "route_short_name": "NS",
                        "route_long_name": "North-South Line", "route_type": "1", "route_color": "D62821"}],
        "trips.txt": [{"route_id": "NS", "service_id": "normal", "trip_id": "overnight"}],
        "stops.txt": [{"stop_id": "A", "stop_lon": "103.8", "stop_lat": "1.3"},
                      {"stop_id": "B", "stop_lon": "103.81", "stop_lat": "1.31"}],
        "stop_times.txt": [
            {"trip_id": "overnight", "stop_id": "A", "stop_sequence": "1", "arrival_time": "23:55:00", "departure_time": "23:56:00"},
            {"trip_id": "overnight", "stop_id": "B", "stop_sequence": "2", "arrival_time": "23:00:00" if backwards else "24:05:00", "departure_time": "24:06:00"}],
        "calendar.txt": [{"service_id": "normal", "start_date": "20260101", "end_date": "20261231",
                          **{d: "1" for d in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")}}],
        "calendar_dates.txt": [{"service_id": "normal", "date": "20261011", "exception_type": "2"}],
    }
    with ZipFile(filename, "w") as archive:
        for name, rows in files.items():
            content = io.StringIO()
            writer = csv.DictWriter(content, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name, content.getvalue())
    return filename


def test_real_timetable_without_shapes_remains_blocked_and_honours_exceptions(tmp_path):
    report = audit(timetable(tmp_path), date(2026, 10, 10), date(2026, 10, 11))
    assert report["counts"]["trips_without_shapes"] == 1
    assert report["validation_issues"] == {}
    assert report["timetable_checks_passed"]
    assert not report["ready_for_replay"]
    assert report["daily_service_date_trip_counts"] == {"2026-10-10": {"NS": 1}, "2026-10-11": {}}
    assert any("without active services" in reason for reason in report["blockers"])


def test_backwards_times_are_reported_without_inventing_a_fix(tmp_path):
    report = audit(timetable(tmp_path, backwards=True), date(2026, 10, 10), date(2026, 10, 10))
    assert report["validation_issues"] == {"backwards_trip_times": 1}
    assert not report["timetable_checks_passed"]


def test_signed_download_errors_do_not_leak_secrets_or_replace_cached_zip(monkeypatch, tmp_path):
    monkeypatch.setenv("LTA_ACCOUNT_KEY", "private-test-key")
    destination = tmp_path / "train.zip"
    destination.write_bytes(b"previous download")
    calls = []

    def open_url(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            assert request.get_header("Accountkey") == "private-test-key"
            return io.BytesIO(b'{"value":[{"link":"https://bucket.amazonaws.com/file.zip?private-signed-token"}]}')
        raise OSError("private-signed-token and private-test-key")

    monkeypatch.setattr("scripts.audit_singapore_gtfs.urlopen", open_url)
    with pytest.raises(RuntimeError) as error:
        download(destination, tmp_path / "missing-key")
    assert "private" not in str(error.value)
    assert destination.read_bytes() == b"previous download"


def test_public_response_sample_is_not_accepted_as_gtfs(tmp_path):
    filename = tmp_path / "sample.zip"
    with ZipFile(filename, "w") as archive:
        archive.writestr("GTFSScheduleTrain.json", '{"value":[]}')
    with pytest.raises(ValueError, match="Missing required GTFS"):
        audit(filename, date(2026, 10, 5), date(2026, 10, 11))
