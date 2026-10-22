from schedule_helpers import expanded_reference, expanded_pattern
from datetime import date, datetime
from zoneinfo import ZoneInfo
import gzip
import json
import csv
import io
import pytest
from zipfile import ZipFile

from dashboard import transit
from scripts.prepare_transit_replay import active_services, business_occurrences, seconds


def test_gtfs_service_exceptions_override_weekday_calendar():
    calendar = {"service_id": "weekday", "start_date": "20240601", "end_date": "20240701", "monday": "1"}
    exceptions = [{"service_id": "weekday", "date": "20240624", "exception_type": "2"},
                  {"service_id": "special", "date": "20240624", "exception_type": "1"}]
    assert active_services([calendar], exceptions, date(2024, 6, 24)) == {"special"}


def test_reference_parser_packs_shared_clocks_without_changing_values():
    value = {"stations": [{"lon": 144.1234567890123, "name": "King’s Cross"}],
             "times": [0, 90000, 91000], "epoch": 1790000000, "missing": None}
    with io.BytesIO(json.dumps(value).encode()) as stream:
        assert transit.load_reference(stream) == value
    shared = {"stop_pattern": "one", "times": [0, 1, 90000, 91000]}
    loaded = transit.load_reference(io.BytesIO(json.dumps(shared).encode()))
    assert loaded["times"].tolist() == shared["times"]
    assert loaded["times"].nbytes == len(shared["times"]) * 8
    assert not loaded["times"].flags.writeable
    with pytest.raises(ValueError):
        transit.load_reference(io.BytesIO(b'{"broken":['))


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
    from scripts.prepare_transit_replay import BRANCHES, prepare

    def table(rows):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue()

    archive_path = tmp_path / "gtfs.zip"
    with ZipFile(archive_path, "w") as outer:
        for branch, mode, operator, route_type in BRANCHES:
            content = io.BytesIO()
            with ZipFile(content, "w") as archive:
                archive.writestr("calendar.txt", table([{"service_id": "daily", "start_date": "20240620", "end_date": "20240702",
                    **dict.fromkeys(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], "1")}]))
                archive.writestr("calendar_dates.txt", "service_id,date,exception_type\n")
                archive.writestr("routes.txt", table([{"route_id": "r", "route_type": route_type, "route_short_name": "1", "route_long_name": "Example"}]))
                archive.writestr("trips.txt", table([{"trip_id": "trip", "route_id": "r", "service_id": "daily", "direction_id": "0", "shape_id": "shape"}])
                                 if branch not in {"7", "8"} else "trip_id,route_id,service_id,direction_id,shape_id\n")
                # Mildura is entirely outside the former Melbourne bounding box.
                lon, lat = ("142.16", "-34.18") if mode == "bus" else ("145", "-37.8")
                archive.writestr("stops.txt", table([{"stop_id": "a", "stop_name": "Alpha", "stop_lat": lat, "stop_lon": lon},
                    {"stop_id": "b", "stop_name": "Bravo", "stop_lat": str(float(lat) - .01), "stop_lon": lon}]))
                archive.writestr("stop_times.txt", table([
                    {"trip_id": "trip", "stop_id": "a", "stop_sequence": "1", "arrival_time": "25:00:00", "departure_time": "25:00:00", "shape_dist_traveled": ""},
                    {"trip_id": "trip", "stop_id": "b", "stop_sequence": "2", "arrival_time": "25:10:00", "departure_time": "25:10:00", "shape_dist_traveled": ""}]))
                archive.writestr("shapes.txt", "shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon,shape_dist_traveled\n")
            outer.writestr(f"{branch}/google_transit.zip", content.getvalue())
    output = tmp_path / "reference.json.gz"
    prepare(archive_path, output)
    with gzip.open(output, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    rows = reference["days"]["2024-06-24"]
    assert len(rows) == 5
    # Shared source IDs in different operational branches must not collide.
    assert {row[1] for row in rows} == {"3:trip", "4:trip", "5:trip", "6:trip", "11:trip"}
    assert {p["operator"] for p in reference["patterns"].values()} == {
        "PTV tram", "PTV bus", "V/Line coach", "PTV regional bus", "SkyBus"}
    assert reference["metadata"]["branches"]["7"]["candidate_trips"] == 0
    assert reference["metadata"]["branches"]["8"]["candidate_trips"] == 0
    for pattern in reference["patterns"].values():
        assert pattern["legs"] == ["gtfs-unresolved"]
        assert pattern["direction"] == "A"
        assert reference["paths"][pattern["legs"][0]]["coordinates"] == []
    assert all(row[2] == 25 * 3600 for row in reference["days"]["2024-06-24"])
    assert reference["metadata"]["omitted_trips"] == {"tram": 0, "bus": 0}


def test_period_index_loads_only_the_snapshot_for_the_selected_day(tmp_path, monkeypatch):
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"metadata": {"start_date": "2024-05-27", "end_date": "2024-06-30"}, "chunks": [
        {"start_date": "2024-05-27", "end_date": "2024-06-02", "file": "may.json.gz"},
        {"start_date": "2024-06-24", "end_date": "2024-06-30", "file": "june.json.gz"}]}))
    for filename, day in (("may.json.gz", "2024-05-27"), ("june.json.gz", "2024-06-30")):
        with gzip.open(tmp_path / filename, "wt") as stream:
            json.dump({"metadata": {}, "days": {day: []}, "stations": [], "patterns": {}, "paths": {}}, stream)
    monkeypatch.setenv("SUNTRAIN_TRANSIT_REFERENCE", str(index))
    opened = []
    original_open = gzip.open
    def tracked_open(path, *args, **kwargs):
        opened.append(str(path))
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(gzip, "open", tracked_open)
    assert transit.available_range() == ("2024-05-27", "2024-06-30")
    reference = transit.read_reference(*transit.fingerprint("2024-05-27"))
    assert "2024-05-27" in reference["days"]
    assert opened == [str(tmp_path / "may.json.gz")]
    assert transit.fingerprint("2024-06-30")[0] == str(tmp_path / "june.json.gz")
    # Missing promised data fails visibly instead of silently dropping both modes.
    (tmp_path / "june.json.gz").unlink()
    with pytest.raises(FileNotFoundError):
        transit.fingerprint("2024-06-30")


def test_snapshot_ranges_use_melbourne_capture_dates_and_cover_five_full_weeks():
    from scripts.prepare_transit_period import ARCHIVES, period_chunks, snapshot_date
    chunks = period_chunks(ARCHIVES, date(2024, 5, 27), date(2024, 6, 30))
    assert snapshot_date(ARCHIVES[2]) == date(2024, 6, 8)  # 15:11 UTC on 7 June.
    days = []
    for chunk in chunks:
        first, last = date.fromisoformat(chunk["start_date"]), date.fromisoformat(chunk["end_date"])
        assert chunk["source_date"] <= chunk["start_date"]
        days.extend(date.fromordinal(n) for n in range(first.toordinal(), last.toordinal() + 1))
    assert len(days) == len(set(days)) == 35
    assert days[0] == date(2024, 5, 27) and days[-1] == date(2024, 6, 30)
    assert days[0].weekday() == 0 and days[-1].weekday() == 6


@pytest.mark.parametrize("compact", [False, True])
def test_regional_coach_can_finish_after_next_business_boundary(tmp_path, monkeypatch, compact):
    from dashboard import replay
    from scripts.compact_transit import save_reference

    reference = {"metadata": {}, "stations": [{"name": "A"}, {"name": "B"}],
        "paths": {"gap": {"quality": "approximate", "coordinates": []}},
        "patterns": {"coach": {"mode": "bus", "operator": "V/Line coach", "line": "Bus · Overnight coach",
            "stops": [[0, 0, 0], [1, 7200, 7200]], "legs": ["gap"]}},
        "days": {"2024-06-24": [["coach", "5:overnight", 26 * 3600]]}}
    path = tmp_path / "coach.json.gz"
    if compact:
        save_reference(reference, path)
    else:
        with gzip.open(path, "wt") as stream:
            json.dump(reference, stream)
    monkeypatch.setenv("SUNTRAIN_TRANSIT_REFERENCE", str(path))
    monkeypatch.setenv("SUNTRAIN_RAIL_GEOMETRY", str(tmp_path / "absent.json"))
    monkeypatch.setattr(replay.data, "_connect", lambda: pytest.fail("bus-only replay queried train warehouse"))
    day = replay.get_replay_day("2024-06-24", modes=["bus"])
    assert len(day["services"]) == 1
    assert datetime.fromtimestamp(day["end"], ZoneInfo("Australia/Melbourne")).isoformat() == "2024-06-25T04:00:00+10:00"


def test_archive_downloader_upgrades_legacy_metro_only_cache(tmp_path, monkeypatch):
    from scripts.prepare_transit_period import download_archive
    from scripts.prepare_transit_replay import BRANCHES

    url = "https://example.test/ptv.zip"
    cached = tmp_path / "ptv.zip"
    with ZipFile(cached, "w") as archive:
        for branch in ("3", "4"):
            archive.writestr(f"{branch}/google_transit.zip", b"legacy")
    source = io.BytesIO()
    with ZipFile(source, "w") as archive:
        for branch in ("1", "2", *[b for b, *_ in BRANCHES]):
            archive.writestr(f"{branch}/google_transit.zip", branch.encode())
    calls = []
    def download(requested, **kwargs):
        calls.append(requested)
        return io.BytesIO(source.getvalue())
    monkeypatch.setattr("urllib.request.urlopen", download)
    assert download_archive(url, tmp_path) == cached
    with ZipFile(cached) as archive:
        assert set(archive.namelist()) == {f"{branch}/google_transit.zip" for branch, *_ in BRANCHES}
        assert archive.read("6/google_transit.zip") == b"6"
    assert download_archive(url, tmp_path) == cached
    assert calls == [url]
