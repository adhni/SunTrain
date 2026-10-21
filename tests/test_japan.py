from datetime import date, datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_japan_geometry import operating_ways
from scripts.prepare_japan_replay import DAY, clock_pair, scheduled_on, timetable_trips


def test_printed_clocks_and_explicit_operating_days_do_not_create_departures():
    assert clock_pair("06:06\\n06:07") == (21960, 22020)
    assert clock_pair("10:52") == (39120, 39120)
    assert clock_pair("↓") is None and clock_pair("") is None
    for value in ["06:61", "48:00", "TBC"]:
        with pytest.raises(ValueError):
            clock_pair(value)
    assert scheduled_on({"serviceDay": "毎日"}, date(2026, 3, 10))
    assert scheduled_on({"serviceDay": "平日"}, date(2026, 3, 10))
    assert not scheduled_on({"serviceDay": "平日"}, date(2026, 3, 8))
    assert not scheduled_on({"serviceDay": ""}, date(2026, 3, 10))
    assert not scheduled_on({"serviceDay": "毎日", "caution": "◆"}, date(2026, 3, 10))


def test_overlapping_timetable_sections_merge_once_and_conflicts_fail():
    def line(identifier, names, times):
        return {"lineId": identifier, "directions": [{"directionId": "0",
            "trains": [{"name": "Nozomi", "number": "1号", "serviceDay": "毎日"}],
            "stations": [{"stationName": name, "times": [stamp]} for name, stamp in zip(names, times)]}]}
    first = line("601", ["東京", "新大阪", "博多"], ["06:00", "08:22\\n08:24", "10:52"])
    second = line("901", ["新大阪", "博多"], ["08:22\\n08:24", "10:52"])
    trips, omitted = timetable_trips({"date": DAY, "lines": [first, second]})
    assert len(trips) == 1 and not omitted
    assert len(next(iter(trips.values()))["calls"]) == 3
    second["directions"][0]["stations"][0]["times"][0] = "08:25"
    with pytest.raises(RuntimeError, match="Conflicting"):
        timetable_trips({"date": DAY, "lines": [first, second]})


def test_osm_compilation_excludes_construction_and_preserves_native_node_ids():
    raw = {"elements": [
        {"type": "node", "id": 1, "lon": 139.0, "lat": 35.0},
        {"type": "node", "id": 2, "lon": 139.1, "lat": 35.1},
        {"type": "node", "id": 3, "lon": 139.0, "lat": 35.0},
        {"type": "way", "id": 10, "nodes": [1, 2], "tags": {"railway": "rail"}},
        {"type": "way", "id": 11, "nodes": [3, 2], "tags": {"railway": "construction"}},
        {"type": "way", "id": 12, "nodes": [1, 2], "tags": {"railway": "platform"}},
    ]}
    assert operating_ways(raw) == [{"node_ids": [1, 2], "coordinates": [[139.0, 35.0], [139.1, 35.1]]}]


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.JAPAN_PATH, "rt") as stream:
        return json.load(stream)


def test_national_shinkansen_snapshot_deduplicates_trains_and_covers_operating_corridors(reference):
    rows = reference["days"][DAY]
    assert len(rows) == 927 and len({(trip, offset) for _, trip, offset in rows}) == 927
    assert reference["metadata"]["omitted_source_rows"] == {"Undated or conditional extra service": 193}
    corridors = {c for p in reference["patterns"].values() for c in p["railway_corridors"]}
    assert {"tokaido", "sanyo", "kyushu", "nishi-kyushu", "tohoku", "hokkaido",
            "hokuriku", "joetsu", "akita", "yamagata"} <= corridors
    assert not {"chuo", "hokkaido-extension"} & corridors
    for key, _, offset in rows:
        p = reference["patterns"][key]
        assert p["mode"] == "train" and p["category"] == "Shinkansen"
        assert "stops" not in p
        assert all(a <= b for a, b in zip(p["times"], p["times"][1:]))
        assert 10800 <= offset + p["times"][1] < 97200
    assert reference["metadata"]["geometry_legs"]["mapped"] / sum(reference["metadata"]["geometry_legs"].values()) > .98
    for path in reference["paths"].values():
        if path["quality"] == "approximate":
            assert path["coordinates"] == path["distances"] == []
        else:
            assert path["quality"] == "track" and len(path["coordinates"]) >= 2
    assert replay.JAPAN_PATH.stat().st_size < 1_000_000


def test_nozomi_through_journey_retains_printed_times_and_distinct_sendai_stations(reference):
    matches = [(p, t, o) for p, t, o in reference["days"][DAY] if reference["train_numbers"][t] == "Nozomi 1"]
    assert len(matches) == 1
    key, _, offset = matches[0]
    p = reference["patterns"][key]
    topology = reference["stop_patterns"][p["stop_pattern"]]
    names = [reference["stations"][s]["name"] for s in topology["stations"]]
    assert names[0] == "東京 Tokyo" and names[-1] == "博多 Hakata"
    assert offset + p["times"][1] == 6 * 3600
    assert offset + p["times"][-2] == 10 * 3600 + 52 * 60
    assert p["operator"] == "JR Central / JR West"
    assert all(reference["paths"][leg]["coordinates"] for leg in topology["legs"])
    stations = {s["name"]: s for s in reference["stations"]}
    assert 31 < stations["川内 Sendai"]["lat"] < 32
    assert 38 < stations["仙台 Sendai"]["lat"] < 39


def test_japan_reuses_only_limited_express_from_tokyo_without_mutating_tokyo():
    tokyo = replay.get_replay_day("2026-10-20", "tokyo")
    original = {s["id"] for s in tokyo["services"]}
    shinkansen = replay.get_replay_day(DAY, "japan", modes=["train"])
    limited = replay.get_replay_day(DAY, "japan", modes=["limited_express"])
    combined = replay.get_replay_day(DAY, "japan")
    assert len(shinkansen["services"]) == 927
    assert len(limited["services"]) == 527
    assert len(combined["services"]) == 1454
    assert all(s["mode"] == "limited_express" and "Toll Limited Express" in
               limited["transit_patterns"][s["pattern"]]["destination"] for s in limited["services"])
    assert combined["schedule"]["display_date_mapping"] == {DAY: "2026-10-20"}
    assert datetime.fromtimestamp(combined["initial"], ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M") == DAY + " 08:00"
    assert original == {s["id"] for s in replay.get_replay_day("2026-10-20", "tokyo")["services"]}


def test_limited_express_only_uses_existing_tokyo_file_when_shinkansen_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_JAPAN_REFERENCE", str(tmp_path / "missing.gz"))
    info = descriptor(DAY, "japan", ["limited_express"])
    assert info["modes"] == ["limited_express"]
    files = replay.rail_reference_files("japan", DAY, ["limited_express"])
    assert files[0][1] == str(replay.TOKYO_PATH)
    assert len(replay.get_replay_day(DAY, "japan", modes=["limited_express"])["services"]) == 527
