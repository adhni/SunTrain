from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_germany_replay import (
    COLORS, GEOMETRY, GEOMETRY_SHA256, OPERATORS, SCOPE, SOURCE,
    GermanRailGraph, describe_route, domestic_sequence, selected_route,
)
from schedule_helpers import expanded_pattern


def test_scope_accepts_only_audited_long_distance_categories_and_operators():
    agencies = {key: {"agency_name": name} for key, name in OPERATORS.items()}
    route = {"route_id": "test", "agency_id": "6", "route_type": "2", "route_short_name": "ICE 10"}
    for category in COLORS:
        assert selected_route({**route, "route_short_name": category}, agencies)
    for category in ("RE 1", "RB 2", "S 1", "U 1", "Bus 1", "SEV", "IC Bus"):
        assert not selected_route({**route, "route_short_name": category}, agencies)
    for mode in ("0", "1", "3", "4", "700"):
        assert not selected_route({**route, "route_type": mode}, agencies)
    assert not selected_route(route, {"6": {"agency_name": "Unexpected operator"}})
    for agency in OPERATORS:
        assert selected_route({**route, "agency_id": agency}, agencies)
    description = describe_route(route, {})
    assert description["line"] == "ICE 10 · DB Fernverkehr AG"
    assert description["direction"] == "Not specified"
    assert describe_route({**route, "route_color": "ABCDEF"}, {})["color"] == "ABCDEF"


def test_domestic_clipping_preserves_order_times_and_foreign_intermediate_calls():
    sequence = [{"stop_id": stop, "arrival_time": f"{i + 22}:00:00"} for i, stop in enumerate("ABCDE")]
    clipped = domestic_sequence(sequence, {}, {"B", "D"})
    assert clipped == sequence[1:4]
    assert clipped[1]["stop_id"] == "C"  # Never bridge over a foreign detour.
    assert clipped[-1]["arrival_time"] == "25:00:00"
    assert domestic_sequence(sequence, {}, {"C"}) == []
    assert domestic_sequence(sequence, {}, set()) == []


def test_graph_joins_source_ids_and_ice_prefers_the_faster_railway_corridor():
    origin, destination = [10, 51], [10.1, 51]
    ways = [
        {"node_ids": ["A", "B"], "coordinates": [origin, destination], "speed": 60},
        {"node_ids": ["A", "C", "B"], "coordinates": [origin, [10.05, 51.02], destination], "speed": 300},
        # An unrelated coincident track has its own source IDs and cannot join.
        {"node_ids": ["X", "Y"], "coordinates": [[10.05, 51], [10.2, 51]], "speed": 300},
    ]
    slow = GermanRailGraph(ways).leg(origin, destination)
    fast = GermanRailGraph(ways, fast=True).leg(origin, destination)
    assert max(p[1] for p in slow) == 51
    assert max(p[1] for p in fast) > 51.01
    assert GermanRailGraph(ways).leg(origin, [10.2, 51]) is None


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.GERMANY_PATH, "rt") as stream:
        return json.load(stream)


def test_pinned_sources_shared_schedules_and_no_passenger_inference(reference):
    assert file_hash(GEOMETRY) == GEOMETRY_SHA256
    scope = json.loads(SCOPE.read_text())
    assert scope["source_gtfs_sha256"] == SOURCE["sha256"]
    metadata = reference["metadata"]
    assert metadata["sources"][0]["sha256"] == SOURCE["sha256"]
    assert metadata["geometry_sha256"] == GEOMETRY_SHA256
    assert metadata["license"] == metadata["geometry_license"] == "CC BY 4.0"
    assert metadata["schedule_encoding"] == "shared-stops-flat-times-v1"
    assert not metadata["omitted_trips"]
    assert reference["stop_patterns"]
    assert all("stops" not in p for p in reference["patterns"].values())
    assert not city_settings("germany")["passenger_data"]


@pytest.mark.parametrize("day", [f"2026-06-{i:02d}" for i in range(1, 8)])
def test_full_week_nationwide_categories_and_unique_overnight_start_assignment(reference, day):
    rows = reference["days"][day]
    assert len(rows) > 700
    categories = {reference["patterns"][key]["route_short_name"].split()[0] for key, _, _ in rows}
    # The archive's RJ/EN routes have no active German section in this week.
    assert categories == {"ICE", "IC", "EC", "ECE"}
    zone = ZoneInfo("Europe/Berlin")
    midnight = datetime.fromisoformat(day).replace(tzinfo=zone)
    occurrences = []
    for key, trip, offset in rows:
        assert 3 * 3600 <= offset < 27 * 3600
        instant = int(midnight.timestamp()) + offset
        occurrences.append((trip, instant))
    assert len(occurrences) == len(set(occurrences))
    all_occurrences = [(trip, int(datetime.fromisoformat(d).replace(tzinfo=zone).timestamp()) + offset)
                       for d, rr in reference["days"].items() for _, trip, offset in rr]
    assert len(all_occurrences) == len(set(all_occurrences))
    names = {reference["stations"][station]["name"] for key, _, _ in rows
             for station, *_ in expanded_pattern(reference, reference["patterns"][key])["stops"]}
    for city in ("Berlin", "Hamburg", "München", "Frankfurt", "Köln", "Stuttgart", "Leipzig", "Dresden"):
        assert any(city in name for name in names)


def test_overnight_calls_and_gaps_never_become_straight_connectors(reference):
    overnight = []
    for day, rows in reference["days"].items():
        for key, trip, offset in rows:
            pattern = expanded_pattern(reference, reference["patterns"][key])
            if offset < 86400 < offset + pattern["stops"][-1][-1]:
                overnight.append(trip)
    assert overnight
    for path in reference["paths"].values():
        if path["quality"] == "approximate":
            assert not path["coordinates"] and not path["distances"]
        else:
            assert path["quality"] == "track"
            assert len(path["coordinates"]) >= 2
            assert all(b >= a for a, b in zip(path["distances"], path["distances"][1:]))


@pytest.mark.parametrize("origin,destination,min_km,max_km", [
    ("Nürnberg Hbf", "Erfurt Hbf", 180, 210),
    ("Frankfurt(M) Flughafen Fernbf", "Siegburg/Bonn", 130, 160),
    ("Leipzig Hbf", "Dresden-Neustadt", 100, 135),
])
def test_representative_high_speed_and_eastern_corridors_have_detailed_rail_paths(reference, origin, destination, min_km, max_km):
    paths = []
    for raw in reference["patterns"].values():
        pattern = expanded_pattern(reference, raw)
        for a, b, key in zip(pattern["stops"], pattern["stops"][1:], pattern["legs"]):
            if (reference["stations"][a[0]]["name"], reference["stations"][b[0]]["name"]) == (origin, destination):
                paths.append(reference["paths"][key])
    assert paths
    assert all(len(p["coordinates"]) > 100 and min_km < p["distances"][-1] / 1000 < max_km for p in paths)


def test_germany_runtime_reuses_existing_loader_and_rejects_other_modes(monkeypatch):
    monkeypatch.setattr(replay.data, "get_metadata", lambda: pytest.fail("Germany queried Melbourne warehouse"))
    payload = replay.get_replay_day(SOURCE["first"], "germany")
    assert payload["timezone"] == "Europe/Berlin"
    assert payload["services"] and all(s["mode"] == "train" for s in payload["services"])
    assert descriptor(SOURCE["first"], "germany")["modes"] == ["train"]
    assert city_settings("germany")["start_date"] == city_settings("netherlands")["start_date"]
    with pytest.raises(ValueError):
        descriptor(SOURCE["first"], "germany", ["bus"])
    with pytest.raises(ValueError):
        replay.get_replay_day("2026-06-08", "germany")
