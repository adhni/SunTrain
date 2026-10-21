from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.prepare_tokyo_replay import railway_geometry, selected_route

PRIVATE_OPERATORS = {"Tokyu", "Keio", "Keikyu", "Odakyu", "Seibu", "Tobu", "Keisei", "Sotetsu"}
OPERATOR_AGENCIES = {"JR East": "JR-East", "Tokyo Metro": "TokyoMetro", "Toei Subway": "Toei",
                     **{name: name for name in PRIVATE_OPERATORS}}


def test_rail_scope_keeps_selected_operators_and_excludes_unselected_modes():
    route = {"route_id": "JR-East.Yamanote", "agency_id": "JR-East", "route_type": "2"}
    agencies = {"JR-East": {}, "TokyoMetro": {}, "Toei": {}}
    assert selected_route(route, agencies)
    for change in [{"agency_id": "TokyoMetro"}, {"route_type": "3"}, {"route_type": "1"},
                   {"route_id": "JR-Central.TokaidoShinkansen"}]:
        assert not selected_route({**route, **change}, agencies)
    for agency, route_id in [("TokyoMetro", "TokyoMetro.Ginza"), ("TokyoMetro", "TokyoMetro.MarunouchiBranch"),
                             ("Toei", "Toei.Oedo")]:
        assert selected_route({"agency_id": agency, "route_id": route_id, "route_type": "1"}, agencies)
    for route_id, kind in [("Toei.Arakawa", "0"), ("Toei.NipporiToneri", "1"), ("Toei.Bus", "3")]:
        assert not selected_route({"agency_id": "Toei", "route_id": route_id, "route_type": kind}, agencies)
    for agency in PRIVATE_OPERATORS:
        route = {"agency_id": agency, "route_id": agency + ".Main", "route_type": "2"}
        available = {**agencies, agency: {}}
        assert selected_route(route, available)
        for kind in ["0", "1", "3"]:
            assert not selected_route({**route, "route_type": kind}, available)
        assert not selected_route({**route, "route_id": "JR-East.Yamanote"}, available)
    assert not selected_route({"agency_id": "OdakyuHakone", "route_id": "OdakyuHakone.HakoneTozan", "route_type": "2"},
                              {"OdakyuHakone": {}})


def test_native_track_edges_keep_straight_rail_and_reject_inserted_shortcuts():
    points = [[139.0, 35.0], [139.02, 35.0], [139.04, 35.0]]
    raw = [(i, float(i), point) for i, point in enumerate(points)]
    edges = {frozenset(map(tuple, points[:2]))}
    resolve = railway_geometry({"shape": raw}, edges)
    sequence = [{"shape_dist_traveled": str(i)} for i in range(3)]
    curves = resolve({}, {"shape_id": "shape"}, sequence, points)
    assert curves[0] == points[:2]  # Real, long straight track is retained.
    assert curves[1] is None  # Matching endpoints alone cannot validate a path.


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.TOKYO_PATH, "rt") as stream:
        return json.load(stream)


def test_snapshot_has_scoped_rail_networks_with_compact_schedules_and_local_departure_days(reference):
    assert set(reference["days"]) == {"2026-10-20"}
    assert len(reference["days"]["2026-10-20"]) == 39346
    assert len({p["source_route_id"] for p in reference["patterns"].values()}) == 122
    assert not reference["metadata"]["omitted_trips"]
    assert "not official historical validity" in reference["metadata"]["calendar_basis"]
    seen = set()
    late = False
    for key, trip, offset in reference["days"]["2026-10-20"]:
        p = reference["patterns"][key]
        agency = OPERATOR_AGENCIES[p["operator"]]
        mode = "subway" if agency in {"TokyoMetro", "Toei"} else "train"
        assert p["mode"] == mode and p["source_route_id"].startswith(agency + ".")
        assert "stops" not in p
        topology = reference["stop_patterns"][p["stop_pattern"]]
        assert len(p["times"]) == 2 * len(topology["stations"])
        assert all(a <= b for a, b in zip(p["times"], p["times"][1:]))
        assert 10800 <= offset + p["times"][1] < 97200
        assert (trip, offset) not in seen
        seen.add((trip, offset))
        assert reference["train_numbers"][trip]
        late |= offset + p["times"][-1] > 86400
    assert late
    assert replay.TOKYO_PATH.stat().st_size < 3_000_000


def test_yamanote_repeated_terminal_uses_the_full_loop_and_correct_direction(reference):
    key, _, _ = next(row for row in reference["days"]["2026-10-20"]
                      if row[1] == "JR-East.Yamanote.400G.Weekday")
    pattern = reference["patterns"][key]
    assert pattern["direction"] == "Inner loop" and pattern["color"] == "#80C747"
    topology = reference["stop_patterns"][pattern["stop_pattern"]]
    assert topology["stations"][0] == topology["stations"][-1]
    paths = [reference["paths"][key] for key in topology["legs"]]
    assert all(path["coordinates"] for path in paths)
    assert 30_000 < sum(path["distances"][-1] for path in paths) < 40_000


def test_runtime_descriptor_uses_tokyo_clock_and_keeps_shared_schedules():
    info = descriptor("2026-10-20", "tokyo")
    assert info["modes"] == ["subway", "train"]
    with pytest.raises(ValueError, match="Date outside"):
        descriptor("2024-06-24", "tokyo")
    day = replay.get_replay_day("2026-10-20", "tokyo")
    assert len(day["services"]) == 39346
    assert datetime.fromtimestamp(day["initial"], ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M") == "2026-10-20 08:00"
    assert all("stops" not in s and "pattern" in s for s in day["services"])
    train = next(s for s in day["services"] if s["source_trip_id"] == "JR-East.Yamanote.400G.Weekday")
    assert train["number"] == "400G"
    assert day["transit_patterns"][train["pattern"]]["direction"] == "Inner loop"


def test_all_thirteen_subway_lines_and_marunouchi_branch_keep_their_colours_and_geometry(reference):
    colours = {
        "TokyoMetro.Ginza": "#FF9500", "TokyoMetro.Marunouchi": "#F62E36",
        "TokyoMetro.MarunouchiBranch": "#F62E36", "TokyoMetro.Hibiya": "#B5B5AC",
        "TokyoMetro.Tozai": "#009BBF", "TokyoMetro.Chiyoda": "#00BB85",
        "TokyoMetro.Yurakucho": "#C1A470", "TokyoMetro.Hanzomon": "#8F76D6",
        "TokyoMetro.Namboku": "#00AC9B", "TokyoMetro.Fukutoshin": "#9C5E31",
        "Toei.Asakusa": "#EC6E65", "Toei.Mita": "#006AB8",
        "Toei.Shinjuku": "#B0BF1E", "Toei.Oedo": "#CE045B",
    }
    patterns = [p for p in reference["patterns"].values() if p["mode"] == "subway"]
    assert {p["source_route_id"] for p in patterns} == set(colours)
    for p in patterns:
        assert p["color"] == colours[p["source_route_id"]]
        topology = reference["stop_patterns"][p["stop_pattern"]]
        assert all(reference["paths"][leg]["coordinates"] for leg in topology["legs"])
    # Ōedo's lollipop has repeated Tochōmae calls: retain the long loop between
    # them rather than snapping the second call back to the first occurrence.
    loops = []
    for p in patterns:
        if p["source_route_id"] != "Toei.Oedo":
            continue
        topology = reference["stop_patterns"][p["stop_pattern"]]
        stations = [reference["stations"][s]["name"] for s in topology["stations"]]
        for i, station in enumerate(stations):
            if station in stations[:i]:
                start = stations.index(station)
                loops.append(sum(reference["paths"][leg]["distances"][-1] for leg in topology["legs"][start:i]))
    assert loops and min(loops) > 20_000


def test_metro_and_train_filters_preserve_shared_services():
    metro = replay.get_replay_day("2026-10-20", "tokyo", modes=["subway"])
    trains = replay.get_replay_day("2026-10-20", "tokyo", modes=["train"])
    combined = replay.get_replay_day("2026-10-20", "tokyo")
    assert len(metro["services"]) == 7474 and len(trains["services"]) == 31872
    assert all(metro["transit_patterns"][s["pattern"]]["operator"] in {"Tokyo Metro", "Toei Subway"}
               for s in metro["services"])
    assert {s["id"] for s in combined["services"]} == {s["id"] for s in metro["services"] + trains["services"]}


def test_eight_private_operators_have_selectable_schedules_colours_and_connected_paths(reference):
    expected = {"Tokyu": 3768, "Keio": 2767, "Keikyu": 2327, "Odakyu": 1882,
                "Seibu": 3361, "Tobu": 4195, "Keisei": 2251, "Sotetsu": 1323}
    actual = dict.fromkeys(expected, 0)
    colours = {"Tokyu.DenEnToshi": "#20A288", "Keio.Inokashira": "#103675",
               "Keikyu.Airport": "#00BFFF", "Odakyu.Odawara": "#0483C8",
               "Seibu.Ikebukuro": "#F07B00", "Tobu.Isesaki": "#E71212",
               "Keisei.Chiba": "#005AAA", "Sotetsu.Main": "#0072C2"}
    for key, _, _ in reference["days"]["2026-10-20"]:
        p = reference["patterns"][key]
        if p["operator"] in actual:
            actual[p["operator"]] += 1
    assert actual == expected
    assert {value for _, value in CITIES["tokyo"]["operators"]} == set(OPERATOR_AGENCIES)
    found = set()
    for p in reference["patterns"].values():
        if p["operator"] not in PRIVATE_OPERATORS:
            continue
        assert p["mode"] == "train"
        topology = reference["stop_patterns"][p["stop_pattern"]]
        assert all(reference["paths"][leg]["coordinates"] for leg in topology["legs"])
        if p["source_route_id"] in colours:
            assert p["color"] == colours[p["source_route_id"]]
            found.add(p["source_route_id"])
    assert found == set(colours)
