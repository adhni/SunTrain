from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.prepare_thailand_srt import clock, passenger_trips


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.THAILAND_PATH, "rt") as stream:
        return json.load(stream)


def test_working_clock_retains_explicit_next_day_and_seconds():
    assert clock("1  7:15:01") == 31 * 3600 + 15 * 60 + 1
    assert clock("9:05:00") == 9 * 3600 + 5 * 60
    for value in ["25:00:00", "1 09:99:00", "unknown"]:
        with pytest.raises(ValueError):
            clock(value)


def test_passenger_scope_keeps_overnight_calls_and_excludes_other_model_runs():
    def row(number, index, name, arrival, departure, day, stop):
        return {"หมายเลขขบวนรถ": number, "_id": index, "สถานี": name, "อักษรย่อ": name,
                "Arrival time": arrival, "Departure time": departure, "Public Day of Operation": day, "Stop type": stop}
    rows = [row("9", 1, "Origin", None, "18:40:00", "Daily", "No stop"),
            row("9", 2, "Passing point", None, "19:00:00", "Daily", "No stop"),
            row("9", 3, "Operational call", "23:30:00", "23:35:00", "Daily", "Scheduled stop"),
            row("9", 4, "Destination", "1 7:15:00", "1 7:15:01", "Not defined", "Scheduled stop")]
    rows += [{**r, "หมายเลขขบวนรถ": n} for n in ["552", "D.607", "1121"] for r in rows[:2]]
    trips, omitted = passenger_trips(rows)
    assert set(trips) == {"9"} and not omitted
    assert [c["name"] for c in trips["9"]] == ["Origin", "Operational call", "Destination"]
    assert trips["9"][-1]["departure"] == 112501


def test_illustrative_dates_and_source_calendar_are_explicit(reference):
    m = reference["metadata"]
    assert m["illustrative_dates"] and not m["effective_dates_confirmed"]
    assert m["approximate_period"] == "April 2023"
    assert "illustrative" in CITIES["thailand"]["description"] and "illustrative" in m["replay_note"]
    assert len(reference["days"]) == 7 and all(len(rows) == 178 for rows in reference["days"].values())
    assert not m["omitted_trips"]
    assert len(reference["patterns"]) == 178 and len(reference["stations"]) == 604
    assert sum(map(len, m["source_call_rows"].values())) == 5787
    for rows in reference["days"].values():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        for key, trip, offset in rows:
            p = reference["patterns"][key]
            assert trip.isdigit() and 0 < int(trip) < 500
            assert p["working_timetable"] and not p.get("frequency_based") and "stops" not in p
            assert 10800 <= offset + p["times"][1] < 97200
            assert all(a <= b for a, b in zip(p["times"], p["times"][1:]))
            topology = reference["stop_patterns"][p["stop_pattern"]]
            assert len(topology["stations"]) == len(m["source_call_rows"][trip])
    assert replay.THAILAND_PATH.stat().st_size < 600_000


def test_source_daytime_and_overnight_clocks_are_not_changed(reference):
    expected = {"7": (32700, 70201), "9": (67200, 112501), "21": (22200, 50401), "171": (47400, 125401)}
    for number, (departure, finish) in expected.items():
        key, _, offset = next(row for row in reference["days"]["2023-04-03"] if row[1] == number)
        pattern = reference["patterns"][key]
        assert offset + pattern["times"][1] == departure
        assert offset + pattern["times"][-1] == finish
    day = replay.get_replay_day("2023-04-03", "thailand")
    assert len(day["services"]) == 178
    zone = ZoneInfo("Asia/Bangkok")
    assert datetime.fromtimestamp(day["end"], zone).strftime("%Y-%m-%d %H:%M:%S") == "2023-04-04 14:45:01"
    assert datetime.fromtimestamp(day["initial"], zone).strftime("%H:%M") == "08:00"
    assert descriptor("2023-04-03", "thailand")["modes"] == ["train"]


def test_unknown_station_coordinates_keep_every_call_and_never_make_map_shortcuts(reference):
    unlocated = {i for i, s in enumerate(reference["stations"]) if s["lon"] is None or s["lat"] is None}
    assert len(unlocated) == 62
    for p in reference["patterns"].values():
        stops = reference["stop_patterns"][p["stop_pattern"]]
        for i, leg in enumerate(stops["legs"]):
            path = reference["paths"][leg]
            if stops["stations"][i] in unlocated or stops["stations"][i + 1] in unlocated:
                assert path["quality"] == "approximate"
            if path["quality"] == "approximate":
                assert path["coordinates"] == path["distances"] == []
            else:
                assert path["quality"] == "track" and len(path["coordinates"]) >= 2
    day = replay.get_replay_day("2023-04-03", "thailand")
    assert 1 - day["approximate_legs"] / day["total_legs"] > .8
    assert reference["metadata"]["geometry_license"] == "ODbL 1.0"
    assert reference["metadata"]["license"] != "CC BY 4.0"
