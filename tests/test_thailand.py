from collections import Counter
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.prepare_thailand_replay import ROUTES, selected_route, select_templates


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.BANGKOK_PATH, "rt") as stream:
        return json.load(stream)


def test_explicit_scope_keeps_eight_bangkok_lines_and_excludes_unreliable_networks():
    for route, (agency, kind, *_) in ROUTES.items():
        assert selected_route({"route_id": route, "agency_id": agency, "route_type": kind}, {})
        assert not selected_route({"route_id": route, "agency_id": agency, "route_type": "3"}, {})
    for route, agency in [("6", "SRT"), ("2734", "SRT"), ("5", "SRTET"), ("2436", "MRTA")]:
        assert not selected_route({"route_id": route, "agency_id": agency, "route_type": "2"}, {})


def test_template_audit_rejects_zero_time_conflicts_and_duplicate_departures():
    trips = {tid: {"route_id": "3", "service_id": "1", "direction_id": "0"} for tid in ["1", "2", "3"]}
    calls = [{"stop_id": "a", "arrival_time": "00:00:00", "departure_time": "00:00:00"},
             {"stop_id": "b", "arrival_time": "00:02:00", "departure_time": "00:02:00"}]
    frequencies = {"1": [{"start_time": "06:00:00", "end_time": "08:00:00", "headway_secs": "600"}],
        "2": [{"start_time": "06:00:00", "end_time": "07:00:00", "headway_secs": "600"},
              {"start_time": "07:00:00", "end_time": "08:00:00", "headway_secs": "300"}]}
    frequencies["3"] = frequencies["1"]
    stops = {"a": {"stop_lon": "100.5", "stop_lat": "13.7"}, "b": {"stop_lon": "100.51", "stop_lat": "13.7"}}
    selected, omitted = select_templates({}, trips, {"1": calls, "2": calls,
        "3": [calls[0], {**calls[1], "arrival_time": "00:00:00"}]}, frequencies, stops)
    assert selected == {"2"} and "Duplicate" in omitted["1"] and "Zero-time" in omitted["3"]
    changed = [calls[0], {**calls[1], "arrival_time": "00:03:00", "departure_time": "00:03:00"}]
    selected, omitted = select_templates({}, {t: trips[t] for t in ["1", "2"]}, {"1": calls, "2": changed}, frequencies, stops)
    assert not selected and all("Conflicting" in reason for reason in omitted.values())


def test_october_holiday_uses_source_exceptions_and_schedules_remain_shared(reference):
    expected = {f"2026-10-{d}": 3687 for d in [12, 14, 15, 16]}
    expected.update({f"2026-10-{d}": 2652 for d in [13, 17, 18]})
    assert {d: len(v) for d, v in reference["days"].items()} == expected
    assert reference["days"]["2026-10-13"] == reference["days"]["2026-10-17"]
    assert len(reference["patterns"]) == 36 and len(reference["stop_patterns"]) == 30
    assert len(reference["metadata"]["selected_templates"]) == 40
    assert len(reference["metadata"]["excluded_templates"]) == 12
    assert not reference["metadata"]["omitted_trips"]
    assert {p["source_route_id"] for p in reference["patterns"].values()} == set(ROUTES)
    for rows in reference["days"].values():
        assert len(rows) == len({(t, o) for _, t, o in rows})
        for key, trip, offset in rows:
            pattern = reference["patterns"][key]
            assert pattern["frequency_based"] and ":estimate-" in trip and "stops" not in pattern
            assert 10800 <= offset + pattern["times"][1] < 97200
            assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))
    assert replay.BANGKOK_PATH.stat().st_size < 200_000


def test_frequency_start_is_departure_with_initial_dwell_retained(reference):
    first = min((row for row in reference["days"]["2026-10-12"] if row[1].startswith("5276:estimate-")), key=lambda row: row[2])
    pattern = reference["patterns"][first[0]]
    assert pattern["times"][:2] == [0, 60]
    assert first[2] == 5 * 3600 + 59 * 60
    assert first[2] + pattern["times"][1] == 6 * 3600
    assert all(not row[1].startswith("5276:") for row in reference["days"]["2026-10-13"])


def test_source_colours_are_retained_and_unmatched_shapes_never_become_straight_lines(reference):
    colors = {"1": "#65b724", "2": "#246B5B", "3": "#1964B7", "4": "#660066",
              "2025": "#A3862A", "2026": "#e10506", "2027": "#fd5353", "2224": "#FFE547"}
    assert all(p["color"] == colors[p["source_route_id"]] for p in reference["patterns"].values())
    for path in reference["paths"].values():
        if path["quality"] == "approximate":
            assert path["coordinates"] == path["distances"] == []
        else:
            assert path["quality"] == "shape" and len(path["coordinates"]) >= 2
    assert reference["metadata"]["license"] == reference["metadata"]["geometry_license"] == "CC BY 4.0"


def test_existing_filters_http_and_bangkok_clock_work_without_other_city_files(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_MALAYSIA_REFERENCE", str(tmp_path / "absent.json.gz"))
    replay.clear_replay_cache()
    info = descriptor("2026-10-12", "bangkok")
    assert info["modes"] == ["commuter_rail", "light_rail", "subway"]
    day = replay.get_replay_day("2026-10-12", "bangkok")
    assert len(day["services"]) == 3687
    assert datetime.fromtimestamp(day["initial"], ZoneInfo(day["timezone"])).strftime("%Y-%m-%d %H:%M") == "2026-10-12 08:00"
    assert not CITIES["bangkok"]["passenger_data"]
    ids = set()
    expected = Counter(s["mode"] for s in day["services"])
    for mode, count in expected.items():
        selected = replay.get_replay_day("2026-10-12", "bangkok", modes=[mode])
        assert len(selected["services"]) == count and all(s["mode"] == mode for s in selected["services"])
        ids.update(s["id"] for s in selected["services"])
    assert ids == {s["id"] for s in day["services"]}
    with pytest.raises(ValueError, match="Date outside"):
        descriptor("2024-06-24", "bangkok")
