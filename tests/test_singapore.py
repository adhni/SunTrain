from schedule_helpers import expanded_reference, expanded_pattern
import gzip
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import SINGAPORE_PATH, cumulative_distances, get_replay_day
from scripts.prepare_singapore_geometry import connected_runs, extract
from scripts.prepare_singapore_replay import match_geometry


def test_osm_extraction_retains_only_connected_operating_railway_ways(tmp_path):
    filename = tmp_path / "small.osm.gz"
    with gzip.open(filename, "wt") as stream:
        stream.write('''<osm version="0.6">
          <node id="1" lon="103.8" lat="1.3"/><node id="2" lon="103.81" lat="1.3"/>
          <node id="3" lon="103.82" lat="1.3"/><node id="4" lon="103.9" lat="1.3"/>
          <node id="5" lon="103.91" lat="1.3"/>
          <way id="10"><nd ref="1"/><nd ref="2"/><tag k="railway" v="subway"/></way>
          <way id="11"><nd ref="3"/><nd ref="2"/><tag k="railway" v="subway"/></way>
          <way id="12"><nd ref="3"/><nd ref="4"/><tag k="railway" v="construction"/></way>
          <way id="13"><nd ref="4"/><nd ref="5"/><tag k="railway" v="subway"/></way>
          <relation id="20"><member type="way" ref="10"/><member type="way" ref="11"/>
          <member type="way" ref="12"/><member type="way" ref="13"/>
          <tag k="type" v="route"/><tag k="ref" v="NSL"/><tag k="route" v="subway"/></relation>
        </osm>''')
    raw = extract(filename)
    assert "12" not in raw["ways"]
    assert connected_runs(raw["relations"][0], raw["ways"]) == [["1", "2", "3"], ["4", "5"]]


def test_closed_loop_matches_a_full_journey_when_osm_starts_midway_round():
    points = [[103.8, 1.3], [103.81, 1.3], [103.81, 1.31], [103.8, 1.31], [103.8, 1.3]]
    stops = [points[1], points[2], points[3], points[0], points[1]]
    _, legs = match_geometry([{"relation": "loop", "coordinates": points}], stops)
    assert len(legs) == 4
    assert sum(cumulative_distances(leg)[-1] for leg in legs) > 4000
    assert legs[0][0] == legs[-1][-1] == points[1]


def test_bundle_covers_mrt_lrt_loops_and_retains_one_unresolved_source_trip():
    with gzip.open(SINGAPORE_PATH, "rt") as stream:
        reference = expanded_reference(json.load(stream))
    patterns, paths = reference["patterns"], reference["paths"]
    codes = {"NS", "EW", "CG", "NE", "CC", "DT", "TE", "BP", "SK", "PG"}
    assert len(reference["days"]) == 7
    assert not reference["metadata"]["omitted_trips"]
    assert set(reference["metadata"]["unresolved_geometry_trips"]) == {"NSL_NB_PH_210_5334"}
    assert reference["metadata"]["geometry"]["license"] == "ODbL 1.0"
    for day, rows in reference["days"].items():
        assert {patterns[p]["route_id"] for p, _, _ in rows} == codes
        assert len({(trip, departure) for _, trip, departure in rows}) == len(rows)
        bad = [p for p, trip, _ in rows if trip == "NSL_NB_PH_210_5334"]
        assert bool(bad) == (day == "2026-10-11")
        for p in bad:
            assert set(patterns[p]["legs"]) == {"sg-unresolved"}
    for pattern in patterns.values():
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        assert pattern["operator"] in {"SMRT", "SBS Transit"}
        assert pattern["mode"] == ("light_rail" if pattern["route_id"] in {"BP", "SK", "PG"} else "subway")
        for i, leg in enumerate(pattern["legs"]):
            curve = paths[leg]["coordinates"]
            if leg == "sg-unresolved":
                assert curve == []
                continue
            assert paths[leg]["quality"] == "track"
            assert len(curve) == len(paths[leg]["distances"]) >= 2
            for stop_index, point in [(i, curve[0]), (i + 1, curve[-1])]:
                stop = reference["stations"][pattern["stops"][stop_index][0]]
                assert cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151
        if pattern["route_id"] in {"BP", "SK", "PG"}:
            assert pattern["stops"][0][0] == pattern["stops"][-1][0]
            assert sum(paths[leg]["distances"][-1] for leg in pattern["legs"]) > 4000


def test_singapore_loader_uses_local_time_and_shared_patterns_without_warehouse(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    day = get_replay_day("2026-10-05", "singapore")
    assert datetime.fromtimestamp(day["initial"], ZoneInfo(day["timezone"])).isoformat() == "2026-10-05T08:00:00+08:00"
    assert not day["passenger_data"]
    assert all("stops" not in service for service in day["services"])
    assert day["approximate_legs"] == 0
    assert len(day["services"]) == 7160
    sunday = get_replay_day("2026-10-11", "singapore")
    assert sunday["approximate_legs"] == 21
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2024-06-24", "singapore")
