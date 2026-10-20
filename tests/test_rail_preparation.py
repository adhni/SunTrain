import csv
from schedule_helpers import expanded_reference
import gzip
import hashlib
import io
import json
from zipfile import ZipFile

import pytest

from scripts.prepare_rail_replay import prepare
from scripts.prepare_us_rail_replay import describe_route, selected_route
from scripts.prepare_australian_replay import path_legs


def test_audited_native_recovery_matches_only_the_original_shape_and_keeps_other_legs():
    raw = [(i, i * 1000, [i * .01, 0]) for i in range(4)]
    coordinates = [[i * .01, 0] for i in range(4)]
    anchors = [0, 500, 2000, 3000]
    with pytest.raises(ValueError, match="Native stop anchor"):
        path_legs(raw, anchors, coordinates)
    recovered = path_legs(raw, anchors, coordinates, recover_native=True)
    assert all(curve[0] == a and curve[-1] == b for curve, a, b in zip(recovered, coordinates, coordinates[1:]))
    # One station is genuinely off the shape. It gets two gaps, while the
    # verified final leg remains available; no connector or new path is made.
    coordinates[1] = [.01, .01]
    partial = path_legs(raw, [0, 1000, 2000, 3000], coordinates, recover_native=True)
    assert partial[:2] == [None, None]
    assert partial[2] == [[.02, 0], [.03, 0]]


def archive_fixture(path, normal_trip, service_dates, extra_route=False):
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
    if extra_route:
        tables["routes.txt"].append({**tables["routes.txt"][0], "route_id": "BLUE"})
        tables["trips.txt"].append({**tables["trips.txt"][0], "route_id": "BLUE", "trip_id": "blue"})
        tables["stops.txt"].append({"stop_id": "c", "stop_name": "Charlie", "stop_lon": "-76.98", "stop_lat": "38.90"})
    for trip in tables["trips.txt"]:
        for index, (stop, clock) in enumerate(zip(("a", "b", "c") if extra_route else ("a", "b"),
                ("26:55:00", "27:10:00") if trip["trip_id"] == "late" else ("06:00:00", "06:10:00", "06:20:00"))):
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
            lambda route, agencies: selected_route("dc", route, agencies),
            lambda route, trip: {**describe_route("dc", route, trip), "color": "#123456"},
            geometry_resolver=lambda *_: NotImplemented)
    with gzip.open(output, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    assert {trip for _, trip, _ in reference["days"]["2026-10-05"]} == {"old", "late"}
    assert {trip for _, trip, _ in reference["days"]["2026-10-06"]} == {"new", "late"}
    assert sorted(offset for _, trip, offset in reference["days"]["2026-10-05"] if trip == "late") == [10500, 96900]
    assert [offset for _, trip, offset in reference["days"]["2026-10-06"] if trip == "late"] == [10500]
    assert not reference["metadata"]["omitted_trips"]
    assert not reference["metadata"]["unresolved_geometry_patterns"]
    assert len(reference["patterns"]) == 2
    assert {p["color"] for p in reference["patterns"].values()} == {"#123456"}
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


def test_explicit_weekday_only_feed_can_keep_empty_weekend_days(tmp_path):
    digest = archive_fixture(tmp_path / "weekday.zip", "regular", ["20261005"])
    source = {"first": "2026-10-05", "last": "2026-10-06", "timezone": "America/New_York",
              "url": "https://example.test/weekday.zip", "sha256": digest,
              "captured": "2026-10-04", "published": "", "source": "fixture", "source_url": "https://example.test",
              "license": "fixture", "license_url": "https://example.test/license", "attribution": "fixture", "note": "fixture"}
    output = tmp_path / "weekdays.json.gz"
    select = lambda route, agencies: True
    describe = lambda route, trip: {"mode": "bus", "route_id": "R", "line": "Bus R"}
    with pytest.raises(ValueError, match="Empty day"):
        prepare("fixture", source, tmp_path, output, select, describe)
    source["allow_empty_days"] = True
    prepare("fixture", source, tmp_path, output, select, describe)
    with gzip.open(output, "rt") as stream:
        reference = json.load(stream)
    assert reference["days"]["2026-10-05"]
    assert reference["days"]["2026-10-06"] == []
    source["first"] = source["last"] = "2026-10-06"
    with pytest.raises(ValueError, match="No active services"):
        prepare("fixture", source, tmp_path, output, select, describe)


def test_optional_bus_preparation_uses_one_start_day_and_writes_self_contained_days(tmp_path):
    digest = archive_fixture(tmp_path / "old.zip", "old", ["20261004", "20261005", "20261006", "20261007"])
    source = {"first": "2026-10-05", "last": "2026-10-06", "timezone": "America/New_York",
              "url": "https://example.test/old.zip", "sha256": digest, "captured": "2026-10-03", "published": "",
              "source": "fixture", "source_url": "https://example.test", "license": "fixture",
              "license_url": "https://example.test/license", "attribution": "fixture", "note": "fixture",
              "assign_by_start": ["bus"]}
    output = tmp_path / "bus"
    prepare("dc", source, tmp_path, output, lambda route, agencies: True,
            lambda route, trip: {"mode": "bus", "route_id": "R", "line": "Bus R"}, daily=True)
    days = []
    for day in ("2026-10-05", "2026-10-06"):
        with gzip.open(output / (day + ".json.gz"), "rt") as stream:
            reference = json.load(stream)
        assert set(reference["days"]) == {day}
        late = [offset for _, trip, offset in reference["days"][day] if trip == "late"]
        assert late == [96900]  # 02:55 starts this business day; 03:10 finish does not assign it twice.
        assert all(stop["mode"] == "bus" for stop in reference["stations"])
        assert reference["metadata"]["schedule_encoding"] == "shared-stops-flat-times-v1"
        days.append(reference)
    assert len(days) == 2


def test_missing_feed_info_requires_explicit_calendar_validation(tmp_path):
    path = tmp_path / "old.zip"
    archive_fixture(path, "regular", ["20261004", "20261005", "20261006"])
    with ZipFile(path) as archive:
        tables = {name: archive.read(name) for name in archive.namelist() if name != "feed_info.txt"}
    with ZipFile(path, "w") as archive:
        for name, contents in tables.items():
            archive.writestr(name, contents)
    source = {"first": "2026-10-05", "last": "2026-10-05", "timezone": "America/New_York",
              "url": "https://example.test/old.zip", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "captured": "2026-10-03", "published": "", "source": "fixture", "source_url": "https://example.test",
              "license": "fixture", "license_url": "https://example.test/license", "attribution": "fixture", "note": "fixture"}
    selected = lambda route, agencies: True
    describe = lambda route, trip: {"mode": "bus", "route_id": "R", "line": "Bus R"}
    output = tmp_path / "prepared.json.gz"
    with pytest.raises(ValueError, match="Feed validity is missing"):
        prepare("dc", source, tmp_path, output, selected, describe)
    source["calendar_validity"] = True
    prepare("dc", source, tmp_path, output, selected, describe)
    source["last"] = "2026-10-07"
    with pytest.raises(ValueError, match="calendars do not cover"):
        prepare("dc", source, tmp_path, output, selected, describe)


def external_source(tmp_path, extra_route=False):
    digest = archive_fixture(tmp_path / "external.zip", "regular", ["20261005"], extra_route)
    return {"first": "2026-10-05", "last": "2026-10-05", "timezone": "America/New_York",
            "url": "https://example.test/external.zip", "sha256": digest, "captured": "2026-10-04", "published": "",
            "source": "fixture", "source_url": "https://example.test", "license": "fixture",
            "license_url": "https://example.test/license", "attribution": "fixture", "note": "fixture",
            "geometry_quality": "track"}


def test_external_geometry_keeps_resolved_legs_and_caches_each_route_separately(tmp_path):
    source = external_source(tmp_path, extra_route=True)
    calls = []

    def resolve(route, trip, sequence, points):
        calls.append(route["route_id"])
        curve = [points[0], [-76.995, 38.901], points[1]]
        return [curve, None] if route["route_id"] == "RED" else [None, [points[1], points[2]]]

    output = tmp_path / "prepared.json.gz"
    prepare("fixture", source, tmp_path, output, lambda route, agencies: True,
            lambda route, trip: {"route_id": route["route_id"], "direction": "Not specified"}, geometry_resolver=resolve)
    with gzip.open(output, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    assert sorted(calls) == ["BLUE", "RED"]
    patterns = {p["route_id"]: p for p in reference["patterns"].values()}
    assert all(p["direction"] == "Not specified" for p in patterns.values())
    red = [reference["paths"][key] for key in patterns["RED"]["legs"]]
    blue = [reference["paths"][key] for key in patterns["BLUE"]["legs"]]
    assert red[0]["quality"] == blue[1]["quality"] == "track"
    assert red[0]["coordinates"][1] == [-76.995, 38.901]
    assert red[1]["coordinates"] == blue[0]["coordinates"] == []
    assert not reference["metadata"]["omitted_trips"]


def test_geometry_factory_is_scoped_to_each_snapshot_even_when_shape_and_stops_match(tmp_path):
    old_hash = archive_fixture(tmp_path / 'old.zip', 'old', ['20261004', '20261005'])
    new_hash = archive_fixture(tmp_path / 'new.zip', 'new', ['20261006', '20261007'])
    source = external_source(tmp_path)
    source.update(first='2026-10-05', last='2026-10-06', archives=[
        {'start': '2026-10-04', 'end': '2026-10-05', 'url': 'https://example.test/old.zip',
         'sha256': old_hash, 'captured': '2026-10-03', 'published': ''},
        {'start': '2026-10-06', 'end': '2026-10-07', 'url': 'https://example.test/new.zip',
         'sha256': new_hash, 'captured': '2026-10-06', 'published': ''}])
    snapshots = []

    def factory(routes, trips, shapes):
        snapshots.append(set(trips))
        bend = 38.9001 if 'old' in trips else 38.9002
        return lambda route, trip, sequence, points: [[points[0], [-76.995, bend], points[1]]]

    output = tmp_path / 'factory.json.gz'
    prepare('fixture', source, tmp_path, output, lambda route, agencies: True,
            lambda route, trip: {'route_id': route['route_id']}, geometry_resolver_factory=factory)
    with gzip.open(output, 'rt') as stream:
        reference = expanded_reference(json.load(stream))
    assert snapshots == [{'old', 'late'}, {'new'}]
    assert {p['coordinates'][1][1] for p in reference['paths'].values()} == {38.9001, 38.9002}


@pytest.mark.parametrize("invalid", [[], [[[-77.1, 38.9], [-76.99, 38.9]]], [[[float("nan"), 38.9], [-76.99, 38.9]]]])
def test_invalid_external_geometry_stays_a_gap_without_using_the_gtfs_sketch(tmp_path, invalid):
    source = external_source(tmp_path)
    output = tmp_path / "prepared.json.gz"
    prepare("fixture", source, tmp_path, output, lambda route, agencies: True,
            lambda route, trip: {"route_id": route["route_id"]}, geometry_resolver=lambda *args: invalid)
    with gzip.open(output, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    assert reference["days"]["2026-10-05"] and not reference["metadata"]["omitted_trips"]
    assert all(p["coordinates"] == [] and p["quality"] == "approximate" for p in reference["paths"].values())


def test_undated_feed_info_without_shapes_uses_explicit_calendars_and_external_geometry(tmp_path):
    source = external_source(tmp_path, extra_route=True)
    path = tmp_path / "external.zip"
    with ZipFile(path) as archive:
        tables = {name: archive.read(name) for name in archive.namelist() if name not in {"shapes.txt", "feed_info.txt"}}
    tables["calendar_dates.txt"] = b"service_id,date,exception_type\nregular,20261004,1\nregular,20261005,1\nregular,20261006,1\n"
    with ZipFile(path, "w") as archive:
        for name, contents in tables.items():
            archive.writestr(name, contents)
        archive.writestr("feed_info.txt", "feed_publisher_name,feed_version\nFixture,undated\n")
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    output = tmp_path / "prepared.json.gz"
    selected = lambda route, agencies: True
    describe = lambda route, trip: {"mode": "train", "route_id": route["route_id"], "line": route["route_id"]}
    with pytest.raises(ValueError, match="Feed validity is missing"):
        prepare("fixture", source, tmp_path, output, selected, describe)
    source["calendar_validity"] = True
    prepare("fixture", source, tmp_path, output, selected, describe,
            geometry_resolver=lambda route, trip, sequence, points: [[points[0], points[1]]],
            select_sequence=lambda sequence, stops: sequence[1:])
    with gzip.open(output, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    assert len(reference["patterns"]) == 2
    assert all(len(p["stops"]) == 2 for p in reference["patterns"].values())
    assert all(p["origin"] == "Bravo" for p in reference["patterns"].values())
    assert all(offset == 6 * 3600 + 10 * 60 for _, _, offset in reference["days"]["2026-10-05"])
    assert not reference["metadata"]["omitted_trips"]


def test_official_feed_in_enclosing_directory_is_read_without_repacking(tmp_path):
    from scripts.prepare_rail_replay import TimetableArchive
    original = tmp_path / 'original.zip'
    archive_fixture(original, 'new', ['20261005', '20261006'])
    nested = tmp_path / 'annual.zip'
    with ZipFile(original) as source, ZipFile(nested, 'w') as target:
        for name in source.namelist():
            target.writestr('GTFS_Fahrplan_2026/' + name, source.read(name))
    with TimetableArchive(nested) as archive, ZipFile(original) as source:
        assert 'calendar_dates.txt' in archive.namelist()
        assert archive.read('agency.txt') == source.read('agency.txt')
        assert archive.read('trips.txt') == source.read('trips.txt')
    ambiguous = tmp_path / 'ambiguous.zip'
    with ZipFile(ambiguous, 'w') as archive:
        archive.writestr('first/agency.txt', '')
        archive.writestr('second/agency.txt', '')
    with pytest.raises(ValueError, match='exactly one GTFS'):
        TimetableArchive(ambiguous)


def test_start_day_uses_departure_when_origin_dwell_crosses_three_am(tmp_path):
    path = tmp_path / 'dwell.zip'
    archive_fixture(path, 'regular', ['20261005', '20261006'])
    with ZipFile(path) as archive:
        tables = {name: archive.read(name) for name in archive.namelist()}
    tables['stop_times.txt'] = tables['stop_times.txt'].replace(
        b'06:00:00,06:00:00', b'02:59:00,03:01:00').replace(
        b'06:10:00,06:10:00', b'03:10:00,03:10:00')
    with ZipFile(path, 'w') as archive:
        for name, contents in tables.items(): archive.writestr(name, contents)
    source = {'first': '2026-10-05', 'last': '2026-10-06', 'timezone': 'America/New_York',
              'url': 'https://example.test/dwell.zip', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'captured': '2026-10-03', 'published': '', 'source': 'fixture', 'source_url': 'https://example.test',
              'license': 'fixture', 'license_url': 'https://example.test/license',
              'attribution': 'fixture', 'note': 'fixture', 'assign_by_start': ['train']}
    output = tmp_path / 'reference.json.gz'
    prepare('dc', source, tmp_path, output, lambda route, agencies: True,
            lambda route, trip: {'mode': 'train', 'route_id': 'R', 'line': 'Train R'})
    with gzip.open(output, 'rt') as stream: reference = json.load(stream)
    for rows in reference['days'].values():
        assert len(rows) == 1
        key, trip, arrival_offset = rows[0]
        assert trip == 'regular' and arrival_offset == 10740
        # Keep the source arrival/dwell; assignment follows the 03:01 departure.
        assert reference['patterns'][key]['times'][1] == 120


def test_single_agency_gtfs_may_omit_agency_ids(tmp_path):
    path=tmp_path/'single.zip'
    archive_fixture(path,'regular',['20261005'])
    with ZipFile(path) as archive:tables={n:archive.read(n) for n in archive.namelist()}
    for name in ['agency.txt','routes.txt']:
        rows=list(csv.DictReader(io.StringIO(tables[name].decode())))
        for row in rows:row.pop('agency_id')
        text=io.StringIO();writer=csv.DictWriter(text,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows);tables[name]=text.getvalue().encode()
    with ZipFile(path,'w') as archive:
        for name,contents in tables.items():archive.writestr(name,contents)
    source={'first':'2026-10-05','last':'2026-10-05','timezone':'America/New_York',
            'url':'https://example.test/single.zip','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'captured':'2026-10-03','published':'','source':'fixture','source_url':'https://example.test',
            'license':'fixture','license_url':'https://example.test/license','attribution':'fixture','note':'fixture'}
    output=tmp_path/'reference.json.gz'
    prepare('dc',source,tmp_path,output,lambda route,agencies:True,
            lambda route,trip:{'mode':'train','route_id':'R','line':'Train R'})
    with gzip.open(output,'rt') as stream:reference=json.load(stream)
    assert len(reference['days']['2026-10-05'])==1
    assert {p['operator'] for p in reference['patterns'].values()}=={'WMATA'}
    # An omitted ID must not silently collapse a multi-agency feed.
    rows=list(csv.DictReader(io.StringIO(tables['agency.txt'].decode())))
    text=io.StringIO();writer=csv.DictWriter(text,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows+rows);tables['agency.txt']=text.getvalue().encode()
    with ZipFile(path,'w') as archive:
        for name,contents in tables.items():archive.writestr(name,contents)
    source['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='Multiple agencies'):
        prepare('dc',source,tmp_path,output,lambda route,agencies:True,lambda route,trip:{})


@pytest.mark.parametrize('zone,first,last', [
    ('America/Chicago', '2026-10-05', '2026-10-06'),
    ('America/Los_Angeles', '2026-10-05', '2026-10-06'),
    ('America/Los_Angeles', '2026-10-31', '2026-11-02')])
def test_replay_timezone_converts_instants_and_assigns_overnight_departures_once(tmp_path, zone, first, last):
    from datetime import date, datetime, time, timedelta
    from zoneinfo import ZoneInfo

    start, finish = date.fromisoformat(first), date.fromisoformat(last)
    dates = [start + timedelta(days=i) for i in range(-1, (finish - start).days + 2)]
    path = tmp_path / 'zone.zip'
    archive_fixture(path, 'regular', [d.strftime('%Y%m%d') for d in dates])
    with ZipFile(path) as archive:
        tables = {n: archive.read(n) for n in archive.namelist() if n != 'feed_info.txt'}
    tables['agency.txt'] = tables['agency.txt'].replace(b'America/New_York', zone.encode())
    tables['stop_times.txt'] = tables['stop_times.txt'].replace(b'06:00:00', b'23:30:00').replace(b'06:10:00', b'24:30:00')
    with ZipFile(path, 'w') as archive:
        for name, contents in tables.items(): archive.writestr(name, contents)
    source = external_source(tmp_path)
    source.update(first=first, last=last, url='https://example.test/zone.zip', timezone=zone,
                  replay_timezone='America/New_York', sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  calendar_validity=True, assign_by_start=['commuter_rail'])
    output = tmp_path / 'zone.json.gz'
    prepare('fixture', source, tmp_path, output, lambda *args: True,
            lambda route, trip: {'route_id': 'R', 'mode': 'commuter_rail'})
    with gzip.open(output, 'rt') as stream: reference = json.load(stream)
    assert reference['metadata']['timezone'] == 'America/New_York'
    assert reference['metadata']['schedule_timezone'] == zone
    expected = {int(datetime.combine(d, time(12), ZoneInfo(zone)).timestamp()) - 43200 + 84600 for d in dates}
    observed = []
    for day, rows in reference['days'].items():
        d = date.fromisoformat(day)
        midnight = int(datetime.combine(d, time(12), ZoneInfo('America/New_York')).timestamp()) - 43200
        left = int(datetime.combine(d, time(3), ZoneInfo('America/New_York')).timestamp())
        right = int(datetime.combine(d + timedelta(days=1), time(3), ZoneInfo('America/New_York')).timestamp())
        for _, trip, offset in rows:
            instant = midnight + offset
            assert trip == 'regular' and instant in expected and left <= instant < right
            observed.append(instant)
    assert len(observed) == len(set(observed))
    assert set(observed) == {instant for instant in expected if
        int(datetime.combine(start, time(3), ZoneInfo('America/New_York')).timestamp()) <= instant <
        int(datetime.combine(finish + timedelta(days=1), time(3), ZoneInfo('America/New_York')).timestamp())}


def test_undated_weekday_calendar_defines_valid_empty_weekends(tmp_path):
    source = external_source(tmp_path)
    path = tmp_path / 'external.zip'
    with ZipFile(path) as archive:
        tables = {n: archive.read(n) for n in archive.namelist() if n not in {'feed_info.txt', 'calendar_dates.txt'}}
    tables['calendar.txt'] = (b'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n'
                              b'regular,1,1,1,1,1,0,0,20261001,20261031\n')
    with ZipFile(path, 'w') as archive:
        for name, contents in tables.items(): archive.writestr(name, contents)
    source.update(first='2026-10-09', last='2026-10-11', calendar_validity=True,
                  allow_empty_days=True, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    output = tmp_path / 'weekend.json.gz'
    prepare('fixture', source, tmp_path, output, lambda *args: True, lambda route, trip: {'route_id': 'R'})
    with gzip.open(output, 'rt') as stream: reference = json.load(stream)
    assert len(reference['days']['2026-10-09']) == 1
    assert reference['days']['2026-10-10'] == reference['days']['2026-10-11'] == []


def test_audited_additional_shapes_are_available_when_trip_shape_ids_are_missing(tmp_path):
    source = external_source(tmp_path)
    path = tmp_path / 'external.zip'
    with ZipFile(path) as archive:
        tables = {n: archive.read(n) for n in archive.namelist()}
    tables['trips.txt'] = tables['trips.txt'].replace(b'curve', b'')
    with ZipFile(path, 'w') as archive:
        for name, contents in tables.items(): archive.writestr(name, contents)
    source.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), additional_shape_ids=['curve'])
    observed = []
    def factory(routes, trips, shapes):
        observed.append(set(shapes))
        assert all(not t['shape_id'] for t in trips.values())
        return lambda route, trip, sequence, points: [[p for _, _, p in shapes['curve']]]
    output = tmp_path / 'shapes.json.gz'
    prepare('fixture', source, tmp_path, output, lambda *args: True,
            lambda route, trip: {'route_id': 'R'}, geometry_resolver_factory=factory)
    assert observed == [{'curve'}]
    with gzip.open(output, 'rt') as stream: reference = json.load(stream)
    assert all(p['quality'] == 'track' and p['coordinates'] for p in reference['paths'].values())
