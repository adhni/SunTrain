from collections import Counter
from datetime import datetime
import gzip
import json
import math
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_germany_ubahn import (
    GEOMETRY, GEOMETRY_SHA256, SCOPE, SOURCE, LocalRailGraph,
    describe_route, geometry_resolver, selected_route,
)
from scripts.prepare_germany_ubahn_geometry import route_ways

ROOT = SCOPE.parent
# Independently counted from the pinned GTFS calendars and first stop times.
COUNTS = [25765, 25765, 26143, 20268, 25542, 22539, 17568]


def test_scope_keeps_ubahn_and_stadtbahn_separate_from_mislabelled_buses_and_trams():
    scope = json.loads(SCOPE.read_text())
    assert scope['source_gtfs_sha256'] == SOURCE['sha256']
    routes = scope['routes']
    agencies = {r['agency_id']: {'agency_name': r['agency_name']} for r in routes.values()}
    assert len({r['city'] for r in routes.values()}) == 14
    assert {r['route_short_name'] for r in routes.values() if r['agency_id'] == '271'} == {'U1', 'U2', 'U3'}
    assert not {r['route_short_name'] for r in routes.values() if r['agency_id'] == '294'} & {'61', '62', '65'}
    assert {r['route_short_name'] for r in routes.values() if r['agency_id'] == '275' and r['route_type'] == '0'} == {'U71', 'U72', 'U73', 'U83'}
    for key, audit in routes.items():
        route = {'route_id': key, **audit}
        assert selected_route(route, agencies, routes)
        assert not selected_route({**route, 'route_type': '3'}, agencies, routes)
        assert not selected_route({**route, 'agency_id': 'other'}, agencies, routes)
        assert not selected_route({**route, 'route_short_name': 'SEV'}, agencies, routes)
    assert not selected_route({'route_id': 'unreviewed', 'route_type': '1', 'route_short_name': '20', 'agency_id': '271'}, agencies, routes)


@pytest.mark.parametrize('latitude', [47.3, 50.0, 52.7, 54.8])
def test_station_cutoff_measures_local_metres_without_widening_tolerance(latitude):
    way = {'node_ids': ['a', 'b'], 'coordinates': [[10, latitude - .01], [10, latitude + .01]]}
    graph = LocalRailGraph([way])
    lon_scale = math.cos(math.radians(latitude)) * 111195
    accepted = graph.anchors([10 + 149.8 / lon_scale, latitude])
    assert len(accepted) == 1
    assert accepted[0][2] == pytest.approx(149.8, abs=.001)
    assert not graph.anchors([10 + 150.2 / lon_scale, latitude])


def test_route_geometry_preserves_native_node_connections_and_excludes_platforms():
    response = {'elements': [
        {'type': 'relation', 'id': 1, 'tags': {'type': 'route', 'route': 'subway', 'ref': 'U1', 'colour': '#abcdef'},
         'members': [{'type': 'way', 'ref': 2, 'role': ''}, {'type': 'way', 'ref': 3, 'role': 'platform'}]},
        {'type': 'way', 'id': 2, 'tags': {'railway': 'subway'}, 'nodes': [10, 11], 'geometry': [{'lon': 10, 'lat': 50}, {'lon': 10.01, 'lat': 50}]},
        {'type': 'way', 'id': 3, 'tags': {'railway': 'subway'}, 'nodes': [11, 12], 'geometry': [{'lon': 10.01, 'lat': 50}, {'lon': 10.02, 'lat': 50}]},
    ]}
    ways, color, relations = route_ways(response, 'U1')
    assert len(ways) == 1 and ways[0]['node_ids'] == ['10', '11']
    assert color == 'ABCDEF' and relations == ['1']
    disconnected = [ways[0], {'node_ids': ['different', 'end'], 'coordinates': [[10.01, 50], [10.03, 50]]}]
    graph = LocalRailGraph(disconnected)
    assert graph.leg([10, 50], [10.03, 50]) is None
    missing = geometry_resolver({'lines': {'44:U1': {'ways': []}}})
    assert missing({'agency_id': '44', 'route_short_name': 'U1'}, {}, [], [[10, 50], [11, 50]]) == [None]


def test_pinned_geometry_and_route_colours_keep_osm_licensing_separate():
    assert file_hash(GEOMETRY) == GEOMETRY_SHA256
    with gzip.open(GEOMETRY, 'rt') as stream:
        geo = json.load(stream)
    assert geo['metadata']['license'] == 'ODbL 1.0'
    assert all(r['sha256'] and r['osm_timestamp'] for r in geo['metadata']['references'])
    routes = json.loads(SCOPE.read_text())['routes']
    for key, audited in routes.items():
        route = {'route_id': key, **audited, 'route_color': '123456'}
        description = describe_route(route, {}, routes, geo)
        assert description['color'] == '123456'
        assert description['mode'] == 'subway' and description['line'].startswith(audited['city'])


def test_week_retains_shared_schedules_unique_business_days_and_all_networks():
    seen = set()
    networks = Counter()
    total_legs = matched_legs = 0
    expected_operators = set(json.loads((ROOT / 'ubahn-operators.json').read_text()))
    for i in range(1, 8):
        day = f'2026-06-{i:02d}'
        with gzip.open(ROOT / 'subway' / (day + '.json.gz'), 'rt') as stream:
            ref = json.load(stream)
        assert list(ref['days']) == [day] and len(ref['days'][day]) == COUNTS[i - 1]
        assert not ref['metadata']['omitted_trips']
        assert ref['metadata']['sources'][0]['sha256'] == SOURCE['sha256']
        assert ref['metadata']['license'] == 'CC BY 4.0' and ref['metadata']['geometry_license'] == 'ODbL 1.0'
        assert ref['metadata']['schedule_encoding'] == 'shared-stops-flat-times-v1'
        midnight = int(datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Berlin')).timestamp())
        moving_operators = set()
        matched = {key: sum(bool(ref['paths'][leg]['coordinates']) for leg in ref['stop_patterns'][p['stop_pattern']]['legs'])
                   for key, p in ref['patterns'].items()}
        for key, trip, offset in ref['days'][day]:
            p = ref['patterns'][key]
            assert key.startswith('de-nv-subway-') and p['mode'] == 'subway' and 'stops' not in p
            assert 10800 <= offset < 97200
            occurrence = trip, midnight + offset
            assert occurrence not in seen
            seen.add(occurrence)
            topology = ref['stop_patterns'][p['stop_pattern']]
            assert len(p['times']) == 2 * len(topology['stations'])
            assert len(topology['legs']) + 1 == len(topology['stations'])
            networks[p['operator']] += 1
            total_legs += len(topology['legs'])
            matched_legs += matched[key]
            if matched[key]:
                moving_operators.add(p['operator'])
        assert moving_operators == expected_operators
        assert all(path['coordinates'] or path['quality'] == 'approximate' for path in ref['paths'].values())
    assert set(networks) == expected_operators
    assert len(networks) == 14
    assert matched_legs / total_legs > .99


def test_optional_subway_only_skips_other_schedules_and_mixed_mode_ids_do_not_collide(monkeypatch):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_GERMANY_REFERENCE', '/unselected-long-distance')
    monkeypatch.setenv('SUNTRAIN_GERMANY_REGIONAL_RAIL_REFERENCE', '/unselected-regional')
    monkeypatch.setenv('SUNTRAIN_GERMANY_COMMUTER_RAIL_REFERENCE', '/unselected-sbahn')
    info = descriptor('2026-06-01', 'germany', ['subway'])
    assert info['modes'] == ['subway']
    subway = replay.get_replay_day('2026-06-01', 'germany', modes=['subway'])
    assert subway['services'] and all(s['mode'] == 'subway' and s['id'].startswith('de-nv:subway:') for s in subway['services'])
    assert subway['schedule']['geometry_license'] == 'ODbL 1.0'
    assert city_settings('germany')['default_modes'] == ['train']
    replay.clear_replay_cache()
    monkeypatch.undo()
    both = replay.get_replay_day('2026-06-01', 'germany', modes=['train', 'subway'])
    assert len(both['services']) == len(subway['services']) + 803
    assert len({s['id'] for s in both['services']}) == len(both['services'])
    credits = [both['schedule'], *both['schedule']['additional_geometry_sources']]
    assert {c['geometry_license'] for c in credits} == {'CC BY 4.0', 'ODbL 1.0'}
    assert any('openstreetmap.org' in c['geometry_source_url'] for c in credits)
    replay.clear_replay_cache()
