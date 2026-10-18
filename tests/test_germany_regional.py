from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_germany_regional import (
    COLORS, SCOPE, SOURCE, STATIONS, IndexedRailGraph,
    describe_route, mode_day, selected_route,
)
from scripts.prepare_germany_replay import GermanRailGraph

ROOT = Path(__file__).resolve().parents[1] / "data/reference/germany"
COUNTS = {
    "regional_rail": [23796, 23718, 24178, 20108, 24342, 20276, 18682],
    "commuter_rail": [14268, 14367, 14552, 12523, 14847, 13155, 11800],
}


def test_audited_scope_keeps_rail_modes_separate_from_sleeper_tourist_and_tram_train_entries():
    scope = json.loads(SCOPE.read_text())
    stations = json.loads(STATIONS.read_text())
    assert scope["source_gtfs_sha256"] == stations["source_gtfs_sha256"] == SOURCE["sha256"]
    agencies = {value["agency_id"]: {"agency_name": value["agency_name"]} for value in scope["routes"].values()}
    assert {value["mode"] for value in scope["routes"].values()} == set(COLORS)
    names = {v["agency_name"] for v in scope["routes"].values()}
    assert not names & {"Albtal-Verkehrs-Gesellschaft", "European Sleeper", "Flixtrain", "Parkeisenbahnen", "DB Fernverkehr AG"}
    for key, value in scope["routes"].items():
        route = {"route_id": key, "route_type": "2", **value}
        assert selected_route(route, agencies, scope["routes"])
        assert not selected_route({**route, "route_type": "3"}, agencies, scope["routes"])
        assert not selected_route({**route, "route_short_name": "NJ"}, agencies, scope["routes"])
        description = describe_route(route, {}, scope["routes"])
        assert description["mode"] == value["mode"]
        assert description["color"] == COLORS[value["mode"]]
        assert describe_route({**route, "route_color": "ABCDEF"}, {}, scope["routes"])["color"] == "ABCDEF"
    assert not any(name in {"Apach(fr)", "Forbach(fr)", "Lauterbourg(fr)", "Wissembourg(fr)"} for name in stations["stops"].values())


def test_spatial_index_preserves_exact_projection_candidates_at_cell_boundaries_and_on_long_edges():
    ways = [{"node_ids": ["A", "B", "C"], "coordinates": [[8, 50], [8.1, 50], [8.2, 50.1]], "speed": 100},
            {"node_ids": ["X", "Y"], "coordinates": [[8, 50.0002], [8.1, 50.0002]], "speed": 80}]
    indexed, original = IndexedRailGraph(ways), GermanRailGraph(ways)
    for point in [[8, 50], [8.05, 50], [8.1, 50.0001], [8.15, 50.05], [8.2, 50.1], [8, 51]]:
        aa, bb = indexed.anchors(point), original.anchors(point)
        assert [a[0] for a in aa] == [b[0] for b in bb]
        for a, b in zip(aa, bb):
            np.testing.assert_allclose(a[1:3], b[1:3])
            np.testing.assert_allclose(a[3], b[3])
    assert indexed.leg([8, 50], [8.2, 50.1]) == original.leg([8, 50], [8.2, 50.1])


@pytest.mark.parametrize("mode", list(COUNTS))
def test_all_seven_mode_bundles_keep_shared_schedules_original_trip_ids_and_unique_start_days(mode):
    seen = set()
    for i, expected in enumerate(COUNTS[mode], 1):
        day = f"2026-06-{i:02d}"
        with gzip.open(ROOT / mode / (day + ".json.gz"), "rt") as stream:
            ref = json.load(stream)
        assert list(ref["days"]) == [day]
        assert len(ref["days"][day]) == expected
        assert ref["metadata"]["sources"][0]["sha256"] == SOURCE["sha256"]
        assert ref["metadata"]["schedule_encoding"] == "shared-stops-flat-times-v1"
        assert not ref["metadata"]["omitted_trips"]
        assert all(p["mode"] == mode and "stops" not in p for p in ref["patterns"].values())
        midnight = int(datetime.fromisoformat(day).replace(tzinfo=ZoneInfo("Europe/Berlin")).timestamp())
        for key, trip, offset in ref["days"][day]:
            assert key.startswith("de-rv-" + mode + "-")
            assert trip.isdigit()  # Source IDs stay intact despite runtime namespacing.
            assert 10800 <= offset < 97200
            occurrence = (trip, midnight + offset)
            assert occurrence not in seen
            seen.add(occurrence)
        for p in ref["patterns"].values():
            topology = ref["stop_patterns"][p["stop_pattern"]]
            assert len(p["times"]) == 2 * len(topology["stations"])
            assert len(topology["legs"]) + 1 == len(topology["stations"])
            assert all(0 <= station < len(ref["stations"]) for station in topology["stations"])
        if mode == "commuter_rail" and i == 1:
            operators = {p["operator"] for p in ref["patterns"].values()}
            assert {"S Bahn Berlin GmbH", "S-Bahn Hamburg", "S-Bahn Hannover", "DB Regio AG S-Bahn Stuttgart"} <= operators
            assert any(p["operator"] == "S Bahn Berlin GmbH" and p["route_short_name"] == "S41" for p in ref["patterns"].values())


def test_mode_day_namespaces_topologies_and_preserves_the_source_reference():
    shared = {"stations": [{"name": "A"}, {"name": "B"}], "stop_patterns": {"s": {"stations": [0, 1], "legs": ["gap"]}},
        "patterns": {"p": {"mode": "commuter_rail", "stop_pattern": "s", "times": [0, 0, 60, 60]}},
        "paths": {"gap": {"coordinates": [], "distances": [], "quality": "approximate"}},
        "days": {"2026-06-01": [["p", "123", 10800]]}, "metadata": {}}
    result = mode_day(shared, "2026-06-01", "commuter_rail")
    assert result["days"]["2026-06-01"] == [["de-rv-commuter_rail-p", "123", 10800]]
    assert result["patterns"]["de-rv-commuter_rail-p"]["stop_pattern"] == "de-rv-commuter_rail-s"
    assert shared["patterns"]["p"]["stop_pattern"] == "s"
    assert shared["days"]["2026-06-01"][0][0] == "p"


def test_default_does_not_touch_regional_files_and_sbahn_only_does_not_open_long_distance(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv("SUNTRAIN_GERMANY_REGIONAL_RAIL_REFERENCE", str(tmp_path / "absent-regional"))
    monkeypatch.setenv("SUNTRAIN_GERMANY_COMMUTER_RAIL_REFERENCE", str(tmp_path / "absent-sbahn"))
    assert descriptor(SOURCE["first"], "germany")["modes"] == ["train"]
    assert len(replay.get_replay_day(SOURCE["first"], "germany")["services"]) == 803
    monkeypatch.delenv("SUNTRAIN_GERMANY_COMMUTER_RAIL_REFERENCE")
    monkeypatch.setenv("SUNTRAIN_GERMANY_REFERENCE", str(tmp_path / "absent-long-distance.gz"))
    assert descriptor(SOURCE["first"], "germany", ["commuter_rail"])["modes"] == ["commuter_rail"]
    result = replay.get_replay_day(SOURCE["first"], "germany", modes=["commuter_rail"])
    assert len(result["services"]) == 14268
    assert all(s["id"].startswith("de-rv:commuter_rail:") and s["number"].isdigit() for s in result["services"])
    replay.clear_replay_cache()


def test_combined_services_have_unique_ids_and_resolve_their_own_topologies_without_mutating_default():
    replay.clear_replay_cache()
    default = replay.get_replay_day(SOURCE["first"], "germany")
    original_patterns = dict(default["transit_stop_patterns"])
    result = replay.get_replay_day(SOURCE["first"], "germany", modes=["train", "regional_rail", "commuter_rail"])
    assert len(result["services"]) == len({s["id"] for s in result["services"]}) == 38867
    for service in result["services"]:
        p = result["transit_patterns"][service["pattern"]]
        topo = result["transit_stop_patterns"][p["stop_pattern"]]
        assert result["stations"][topo["stations"][0]]["name"] == p["origin"]
        assert result["stations"][topo["stations"][-1]]["name"] == p["destination"]
    assert len(default["services"]) == 803
    assert default["transit_stop_patterns"] == original_patterns
    assert city_settings("germany")["default_modes"] == ["train"]
    replay.clear_replay_cache()
