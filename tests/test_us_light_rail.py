from collections import Counter
import gzip
import json

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_us_commuter_replay import selected_route
from scripts.prepare_us_light_rail import SOURCES


def test_selected_light_rail_excludes_commuter_trains_buses_and_other_streetcars():
    for key, config in SOURCES.items():
        agency = config['agency_ids'][0]
        route = {'agency_id': agency, 'route_id': 'example', 'route_type': '0'}
        assert selected_route(key, route, {agency: {}}, sources=SOURCES)
        for kind in ['1', '2', '3', '5']:
            assert not selected_route(key, {**route, 'route_type': kind}, {agency: {}}, sources=SOURCES)
        assert not selected_route(key, {**route, 'agency_id': 'OTHER'}, {'OTHER': {}}, sources=SOURCES)


def test_nine_routes_keep_source_colours_shared_schedules_and_bounded_geometry_gaps():
    with gzip.open(replay.US_LIGHT_RAIL_PATH, 'rt') as stream:
        reference = json.load(stream)
    assert [len(rows) for rows in reference['days'].values()] == [1186, 1185, 1185, 1185, 1195, 1173, 852]
    assert not reference['metadata']['omitted_trips']
    assert len(reference['metadata']['sources']) == 4
    assert len(reference['patterns']) == 74
    colours = {p['color'].upper() for p in reference['patterns'].values()}
    assert colours == {'#004A97', '#BE2036', '#2EB566', '#77777A',
                       '#198BC3', '#006F38', '#F68B1F', '#FD3E3E', '#00AB9B'}
    routes = Counter()
    gaps = Counter()
    for pattern in reference['patterns'].values():
        assert pattern['mode'] == 'light_rail' and 'stops' not in pattern
        routes[pattern['operator'], pattern['source_route_id']] += 1
        topology = reference['stop_patterns'][pattern['stop_pattern']]
        assert len(pattern['times']) == 2 * len(topology['stations'])
        assert all(a <= b for a, b in zip(pattern['times'], pattern['times'][1:]))
        for identifier in topology['legs']:
            path = reference['paths'][identifier]
            if path['quality'] == 'approximate':
                assert pattern['operator'] == 'DART light rail'
                assert path['coordinates'] == path['distances'] == []
                gaps[pattern['operator']] += 1
            else:
                assert path['quality'] == 'shape' and len(path['coordinates']) >= 2
    assert len(routes) == 9 and gaps == {'DART light rail': 3}
    for day, rows in reference['days'].items():
        assert {(reference['patterns'][p]['operator'], reference['patterns'][p]['source_route_id']) for p, _, _ in rows} == set(routes)
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert all(trip in reference['train_numbers'] for _, trip, _ in rows)
    assert reference['metadata']['operator_sources']['TRAX / S-Line']['timezone'] == 'America/Denver'
    assert reference['metadata']['operator_sources']['SPRINTER']['timezone'] == 'America/Los_Angeles'


def test_light_rail_only_does_not_open_intercity_or_commuter_and_all_layers_combine(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    original = replay.transit.read_reference
    def forbidden(*args):
        pytest.fail('light-rail-only request opened an unselected base reference')
    forbidden.cache_clear = original.cache_clear
    with monkeypatch.context() as patch:
        patch.setattr(replay.transit, 'read_reference', forbidden)
        patch.setenv('SUNTRAIN_US_RAIL_REFERENCE', str(tmp_path / 'absent.gz'))
        patch.setenv('SUNTRAIN_US_RAIL_COMMUTER_RAIL_REFERENCE', str(tmp_path / 'absent-commuter.gz'))
        assert descriptor('2026-10-12', 'us_rail', ['light_rail'])['modes'] == ['light_rail']
        light = replay.get_replay_day('2026-10-12', 'us_rail', modes=['light_rail'])
        assert len(light['services']) == 1186
    replay.clear_replay_cache()
    seen = Counter()
    for index in range(12, 19):
        day = f'2026-10-{index}'
        light = replay.get_replay_day(day, 'us_rail', modes=['light_rail'])
        for service in light['services']:
            pattern = light['transit_patterns'][service['pattern']]
            assert 'stops' not in service
            assert light['start'] <= service['departure'] + pattern['times'][1] < light['start'] + 86400
            seen[service['source_trip_id'], service['departure']] += 1
        if index in [12, 18]:
            combined = replay.get_replay_day(day, 'us_rail', modes=['train', 'commuter_rail', 'light_rail'])
            assert len(combined['services']) == (6294 if index == 12 else 4050)
            assert len({s['id'] for s in combined['services']}) == len(combined['services'])
    assert max(seen.values()) == 1


def test_default_http_revision_does_not_depend_on_optional_light_rail(monkeypatch, tmp_path):
    path = tmp_path / 'light-rail.gz'
    path.write_bytes(b'first')
    monkeypatch.setattr(replay, 'US_LIGHT_RAIL_PATH', path)
    base = descriptor('2026-10-12', 'us_rail')
    selected = descriptor('2026-10-12', 'us_rail', ['light_rail'])
    path.write_bytes(b'changed optional source')
    assert descriptor('2026-10-12', 'us_rail') == base
    assert descriptor('2026-10-12', 'us_rail', ['light_rail'])['revision'] != selected['revision']
    path.unlink()
    assert descriptor('2026-10-12', 'us_rail') == base
