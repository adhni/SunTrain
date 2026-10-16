import csv
import io
from zipfile import ZipFile

import pytest

from dashboard.replay import cumulative_distances, pattern_key
from scripts.prepare_replay_geometry import anchored_shape, build_geometry, load_variants, station_name


def variant(names, points, indices=None, operator="Metro", line="Example"):
    return {"names": names, "points": points, "stop_indices": indices or list(range(len(names))),
            "operator": operator, "routes": line}


def geometry(variants, names, points):
    mappings, paths = build_geometry(variants, [("Metro", "Example", names, points)])
    return [paths[i] for i in mappings[pattern_key("Metro", "Example", names)]]


@pytest.mark.parametrize("reverse", [False, True])
def test_loop_leg_does_not_take_long_way_through_another_recorded_stop(reverse):
    a, b, c, end = [144, -37], [144.01, -37], [144.01, -37.02], [144.02, -37.02]
    bend = [144.005, -37.003]
    variants = [variant(["Alpha", "Bravo", "Charlie"], [a, bend, b, c], [0, 2, 3]),
                variant(["Alpha", "Charlie", "Bravo"], [a, c, b])]
    names, points = ["Alpha", "Bravo", "Charlie", "Terminus"], [a, b, c, end]
    if reverse:
        names, points = names[::-1], points[::-1]
    paths = geometry(variants, names, points)
    leg = paths[-1] if reverse else paths[0]
    assert leg["quality"] == "track"
    assert bend in leg["coordinates"]
    assert c not in leg["coordinates"]
    gap = paths[0] if reverse else paths[-1]
    assert gap["quality"] == "approximate"
    assert gap["coordinates"] == []


@pytest.mark.parametrize("reverse", [False, True])
def test_native_stop_distances_keep_repeated_station_occurrences(reverse):
    a, b, c = [144, -37], [144.01, -37], [144.01, -37.01]
    raw = [(0, 0, a), (1, 1000, b), (2, 2000, c), (3, 3500, a)]
    points, indices = anchored_shape(raw, [(0, "alpha"), (1000, "bravo"), (2000, "charlie"), (3500, "alpha")])
    assert indices == [0, 1, 2, 3]
    names, locations = ["Alpha", "Bravo", "Charlie", "Alpha"], [a, b, c, a]
    if reverse:
        names, locations = names[::-1], locations[::-1]
    paths = geometry([variant(["Alpha", "Bravo", "Charlie", "Alpha"], points, indices)], names, locations)
    assert all(p["quality"] == "track" for p in paths)
    for path, start, end in zip(paths, locations, locations[1:]):
        assert path["coordinates"] == [start, end]
        assert cumulative_distances(path["coordinates"])[-1] > 500


def test_express_service_follows_tracks_through_unrecorded_intermediate_stations():
    a, b, c, d = [144, -37], [144.01, -37.01], [144.02, -37.01], [144.03, -37]
    path, = geometry([variant(["Alpha", "Bravo", "Charlie", "Delta"], [a, b, c, d])], ["Alpha", "Delta"], [a, d])
    assert path["quality"] == "track"
    assert path["coordinates"] == [a, b, c, d]


def test_fallback_does_not_mix_operator_variants():
    a, b, end, detour = [144, -37], [144.01, -37], [144.02, -37], [144.005, -37.04]
    paths = geometry([variant(["Alpha", "Bravo"], [a, b]),
                      variant(["Alpha", "Bravo"], [a, detour, b], [0, 2], operator="VLine")],
                     ["Alpha", "Bravo", "Terminus"], [a, b, end])
    assert paths[0]["quality"] == "track"
    assert detour not in paths[0]["coordinates"]


def test_graph_joins_verified_segments_for_a_unique_corridor():
    a, b, c = [144, -37], [144.01, -37.01], [144.02, -37]
    path, = geometry([variant(["Alpha", "Bravo"], [a, b]), variant(["Bravo", "Charlie"], [b, c])],
                     ["Alpha", "Charlie"], [a, c])
    assert path["quality"] == "track"
    assert path["method"] == "segments"
    assert b in path["coordinates"]


def test_graph_leaves_a_gap_when_two_corridors_are_possible():
    a, b, c, d = [144, -37], [144.01, -37.01], [144.02, -37], [144.01, -36.99]
    variants = [variant(["Alpha", "Bravo"], [a, b]), variant(["Bravo", "Charlie"], [b, c]),
                variant(["Alpha", "Delta"], [a, d]), variant(["Delta", "Charlie"], [d, c])]
    path, = geometry(variants, ["Alpha", "Charlie"], [a, c])
    assert path["quality"] == "approximate"
    assert path["coordinates"] == []


def test_graph_does_not_bridge_disconnected_station_platforms():
    a, b, wrong_b, c = [144, -37], [144.01, -37.01], [144.01, -37.03], [144.02, -37]
    path, = geometry([variant(["Alpha", "Bravo"], [a, b]), variant(["Bravo", "Charlie"], [wrong_b, c])],
                     ["Alpha", "Charlie"], [a, c])
    assert path["quality"] == "approximate"
    assert path["coordinates"] == []


def test_jolimont_alias_matches_both_gtfs_and_historical_names():
    assert station_name("Jolimont-MCG Railway Station") == station_name("Jolimont")


def test_anchored_shape_rejects_invalid_stop_distances():
    with pytest.raises(ValueError, match="outside"):
        anchored_shape([(0, 0, [144, -37]), (1, 100, [144.01, -37])], [(0, "alpha"), (500, "bravo")])


def test_rail_route_replacement_bus_trip_is_excluded(tmp_path):
    def write_csv(archive, name, fields, rows):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)
        writer.writerows(rows)
        archive.writestr(name, output.getvalue())
    def feed(bus=False):
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            write_csv(archive, "routes.txt", ["route_id", "route_type", "route_long_name"], [["rail", 2, "Example"]])
            write_csv(archive, "trips.txt", ["trip_id", "route_id", "shape_id"],
                      [["train", "rail", "track"], ["bus", "rail", "road"]] if bus else [])
            write_csv(archive, "stops.txt", ["stop_id", "stop_name", "platform_code"],
                      [["a", "Alpha Station", "1"], ["b", "Bravo Station", "2"],
                       ["bus", "Bravo Rail Replacement Bus Stop", "Replacement bus"]])
            write_csv(archive, "stop_times.txt", ["trip_id", "stop_id", "stop_sequence", "shape_dist_traveled"],
                      [["train", "a", 1, 0], ["train", "b", 2, 1000], ["bus", "a", 1, 0], ["bus", "bus", 2, 2000]] if bus else [])
            write_csv(archive, "shapes.txt", ["shape_id", "shape_pt_sequence", "shape_pt_lon", "shape_pt_lat", "shape_dist_traveled"],
                      [["track", 1, 144, -37, 0], ["track", 2, 144.01, -37, 1000],
                       ["road", 1, 144, -37, 0], ["road", 2, 144.01, -37.01, 2000]] if bus else [])
        return output.getvalue()
    filename = tmp_path / "gtfs.zip"
    with ZipFile(filename, "w") as archive:
        archive.writestr("1/google_transit.zip", feed())
        archive.writestr("2/google_transit.zip", feed(True))
    variants = load_variants(filename)
    assert len(variants) == 1
    assert variants[0]["names"] == ["alpha", "bravo"]
    assert variants[0]["points"] == [[144, -37], [144.01, -37]]


def test_surrounding_stops_reject_long_loop_variant_that_omits_intermediate_calls():
    a, b, c, terminus = [144, -37], [144.01, -37], [144.02, -37], [144.03, -37]
    detour = [144.005, -37.03]
    variants = [variant(["Alpha", "Bravo", "Charlie"], [a, b, c]),
                variant(["Alpha", "Bravo"], [a, detour, b], [0, 2])]
    paths = geometry(variants, ["Alpha", "Bravo", "Charlie", "Terminus"], [a, b, c, terminus])
    assert paths[0]["quality"] == "track"
    assert paths[0]["coordinates"] == [a, b]


def test_shape_geometry_cannot_pass_a_later_stop_even_if_its_station_list_matches():
    a, b, c, d, end = [144, -37], [144.01, -37], [144.02, -37], [144.03, -37], [144.04, -37]
    variants = [variant(["Alpha", "Bravo", "Charlie"], [a, b, c]),
                variant(["Alpha", "Bravo", "Charlie", "Delta"], [a, c, b, c, d], [0, 2, 3, 4])]
    paths = geometry(variants, ["Alpha", "Bravo", "Charlie", "Delta", "Terminus"], [a, b, c, d, end])
    assert paths[0]["quality"] == "track"
    assert paths[0]["coordinates"] == [a, b]


@pytest.mark.parametrize("line,names", [
    ("Hurstbridge", "Flinders Street|Southern Cross|Flagstaff|Melbourne Central|Parliament|Jolimont|West Richmond|North Richmond|Collingwood|Victoria Park|Clifton Hill|Westgarth|Dennis|Fairfield|Alphington|Darebin|Ivanhoe|Eaglemont|Heidelberg|Rosanna|Macleod|Watsonia|Greensborough|Montmorency|Eltham|Diamond Creek|Wattle Glen|Hurstbridge"),
    ("Cranbourne", "Cranbourne|Merinda Park|Lynbrook|Dandenong|Yarraman|Noble Park|Sandown Park|Springvale|Westall|Clayton|Huntingdale|Oakleigh|Hughesdale|Murrumbeena|Carnegie|Caulfield|Malvern|South Yarra|Richmond|Parliament|Melbourne Central|Flagstaff|Southern Cross|Flinders Street"),
    ("Sunbury", "Flinders Street|Parliament|Melbourne Central|Flagstaff|North Melbourne|Footscray|Middle Footscray|West Footscray|Tottenham|Sunshine|Albion|Ginifer|St Albans|Keilor Plains|Watergardens|Diggers Rest|Sunbury"),
])
def test_prepared_reference_repairs_known_historical_city_loop_journeys(line, names):
    import json
    from dashboard.replay import GEOMETRY_PATH

    reference = json.loads(GEOMETRY_PATH.read_text())
    assert reference["metadata"]["matcher_version"] == 2
    names = names.split("|")
    ids = reference["patterns"][pattern_key("Metro", line, names)]
    # These bounds catch both the old two-point chords and the erroneous full laps.
    limits = {
        frozenset(["Flinders Street", "Southern Cross"]): (1500, 1900),
        frozenset(["Southern Cross", "Flagstaff"]): (900, 1400),
        frozenset(["Flagstaff", "Melbourne Central"]): (600, 850),
        frozenset(["Melbourne Central", "Parliament"]): (1050, 1500),
        frozenset(["Flinders Street", "Parliament"]): (1150, 1800),
        frozenset(["Parliament", "Jolimont"]): (1200, 1800),
        frozenset(["Richmond", "Parliament"]): (2000, 2800),
    }
    checked = 0
    for a, b, identifier in zip(names, names[1:], ids):
        bounds = limits.get(frozenset([a, b]))
        if bounds is None:
            continue
        path = reference["paths"][identifier]
        assert path["quality"] == "track", (line, a, b)
        assert len(path["coordinates"]) > 2, (line, a, b)
        assert bounds[0] < cumulative_distances(path["coordinates"])[-1] < bounds[1], (line, a, b)
        checked += 1
    assert checked >= 3


def test_prepared_reference_contains_no_straight_fallback_geometry():
    import json
    from dashboard.replay import GEOMETRY_PATH

    reference = json.loads(GEOMETRY_PATH.read_text())
    unresolved = [p for p in reference["paths"].values() if p["quality"] != "track"]
    assert unresolved
    assert all(p["coordinates"] == [] for p in unresolved)
