import gzip
import hashlib
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import LONDON_PATH, cumulative_distances, get_replay_day
from scripts.london_rail_graph import RailGraph
from scripts.prepare_london_geometry import line_code, SOURCE_SHA256
from scripts.prepare_london_replay import GEOMETRY, GEOMETRY_SHA256, SOURCE, UNDERGROUND, selected_route


def test_london_scope_excludes_cif_tube_links_replacement_buses_and_other_modes():
    route = {"route_id": "tfl_BAK", "agency_id": "LUL", "route_type": "1"}
    assert selected_route(route, {})
    assert selected_route({"route_id": "tfl_DLR", "agency_id": "DLR", "route_type": "2"}, {})
    assert selected_route({"route_id": "tfl_TR", "agency_id": "TCL", "route_type": "0"}, {})
    for changed in ({"agency_id": "=LT"}, {"route_id": "BAK"}, {"route_type": "3"}, {"route_id": "tfl_CAB"}):
        assert not selected_route({**route, **changed}, {})
    for agency, code in (("=LO", "WIN"), ("=XR", "XR"), ("CV", "tfl_RB1")):
        assert not selected_route({"route_id": code, "agency_id": agency, "route_type": "2"}, {})


def test_london_osm_classification_requires_operating_route_modes():
    tags = {"type": "route", "route": "subway", "ref": "Waterloo & City"}
    assert line_code(tags) == "WAC"
    assert line_code({**tags, "route": "bus"}) is None
    assert line_code({**tags, "type": "route_master"}) is None
    assert line_code({"type": "route", "route": "light_rail", "network": "Docklands Light Railway"}) == "DLR"
    assert line_code({"type": "route", "route": "tram", "network": "London Trams"}) == "TR"


def test_rail_graph_joins_only_identical_osm_nodes_and_preserves_a_closed_route():
    a, b, c, d = [-0.10, 51.50], [-0.09, 51.50], [-0.09, 51.51], [-0.10, 51.51]
    disconnected = RailGraph([{"node_ids": ["a", "b"], "coordinates": [a, b]},
                              {"node_ids": ["other-b", "c"], "coordinates": [b, c]}])
    assert disconnected.leg(a, c) is None
    connected = RailGraph([{"node_ids": ["a", "b"], "coordinates": [a, b]},
                           {"node_ids": ["b", "c"], "coordinates": [b, c]}])
    assert connected.leg(a, c)[0] == pytest.approx(a)
    assert connected.leg(a, c)[-1] == pytest.approx(c)
    assert b == pytest.approx(connected.leg(a, c)[1])
    assert connected.leg([-0.11, 51.49], c) is None
    loop = RailGraph([{"node_ids": ["a", "b", "c", "d", "a"], "coordinates": [a, b, c, d, a]}])
    legs = [loop.leg(start, end) for start, end in zip([a, b, c, d], [b, c, d, a])]
    assert sum(cumulative_distances(leg)[-1] for leg in legs) > 3000
    with pytest.raises(ValueError, match="conflicting coordinates"):
        RailGraph([{"node_ids": ["a", "a"], "coordinates": [a, b]}])


def test_london_geometry_reference_has_node_provenance_and_both_osm_sources():
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest() == GEOMETRY_SHA256
    with gzip.open(GEOMETRY, "rt") as stream:
        geometry = json.load(stream)
    assert geometry["metadata"]["source_sha256"] == SOURCE_SHA256
    assert geometry["metadata"]["supplement"]["source_date"] == "2026-10-18"
    assert geometry["metadata"]["license"] == "ODbL 1.0"
    assert set(geometry["lines"]) == UNDERGROUND | {"DLR", "TR"}
    for variants in geometry["lines"].values():
        for variant in variants:
            assert len(variant["node_ids"]) == len(variant["coordinates"]) >= 2


def test_london_bundle_has_all_eleven_lines_plus_dlr_and_trams_with_track_paths():
    with gzip.open(LONDON_PATH, "rt") as stream:
        reference = json.load(stream)
    patterns, paths, metadata = reference["patterns"], reference["paths"], reference["metadata"]
    first = date(2026, 10, 5)
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(7)}
    assert {p["route_id"] for p in patterns.values()} == UNDERGROUND | {"DLR", "TR"}
    assert not metadata["omitted_trips"]
    assert metadata["sources"][0]["sha256"] == SOURCE["sha256"]
    assert metadata["geometry_sha256"] == GEOMETRY_SHA256
    assert metadata["geometry_license"] == "ODbL 1.0"
    for day, rows in reference["days"].items():
        assert rows and len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert {"DLR", "TR"} <= {patterns[p]["route_id"] for p, _, _ in rows}
        legs = [leg for p, _, _ in rows for leg in patterns[p]["legs"]]
        assert sum(paths[leg]["quality"] == "approximate" for leg in legs) / len(legs) < 0.01
    for pattern in patterns.values():
        assert pattern["mode"] == ("subway" if pattern["route_id"] in UNDERGROUND else "light_rail")
        assert len(pattern["stops"]) == len(pattern["legs"]) + 1
        assert all(len(stop) == 3 for stop in pattern["stops"])
        times = [t for stop in pattern["stops"] for t in stop[1:]]
        assert all(b >= a for a, b in zip(times, times[1:]))
        for index, leg in enumerate(pattern["legs"]):
            path = paths[leg]
            if path["quality"] == "approximate":
                assert path["coordinates"] == path["distances"] == []
                continue
            assert path["quality"] == "track" and len(path["coordinates"]) >= 2
            assert len(path["coordinates"]) == len(path["distances"])
            for stop_index, point in ((index, path["coordinates"][0]), (index + 1, path["coordinates"][-1])):
                stop = reference["stations"][pattern["stops"][stop_index][0]]
                assert cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151
    circles = [p for p in patterns.values() if p["route_id"] == "CIR" and len({s[0] for s in p["stops"]}) < len(p["stops"])]
    assert any(sum(paths[leg]["distances"][-1] for leg in p["legs"] if paths[leg]["distances"]) > 20000 for p in circles)


def test_all_london_days_use_british_summer_time_and_shared_stops_without_passenger_claims(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(tmp_path / "missing.parquet"))
    for i in range(7):
        day = str(date(2026, 10, 5) + timedelta(days=i))
        payload = get_replay_day(day, "london")
        assert datetime.fromtimestamp(payload["initial"], ZoneInfo("Europe/London")).isoformat() == day + "T08:00:00+01:00"
        assert payload["passenger_data"] is False and payload["services"]
        assert all("stops" not in service for service in payload["services"])
        assert len(payload["transit_patterns"]) < len(payload["services"])
        assert payload["schedule"]["geometry_source_url"] == "https://www.openstreetmap.org/copyright"
    with pytest.raises(ValueError, match="covers"):
        get_replay_day("2024-05-27", "london")
