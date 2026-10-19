import gzip
import json

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_austria_ubahn import ARCHIVES, LINES, selected_route, describe_route
from scripts.prepare_rail_replay import source_for


def test_only_wiener_linien_metro_is_selected_with_source_colours():
    agencies = {'04': {'agency_name': 'Wiener Linien GmbH & Co KG'}}
    route = {'agency_id': '04', 'route_type': '1', 'route_short_name': 'U1',
             'route_id': 'u1', 'route_color': 'E3000F'}
    for line in LINES:
        assert selected_route({**route, 'route_short_name': line}, agencies)
    for mode in ['0', '2', '3', '700']:
        assert not selected_route({**route, 'route_type': mode}, agencies)
    assert not selected_route({**route, 'agency_id': '03'}, agencies)
    assert not selected_route({**route, 'route_short_name': 'U5'}, agencies)
    assert not selected_route(route, {'04': {'agency_name': 'changed'}})
    assert describe_route(route, {})['color'] == 'E3000F'
    assert describe_route(route, {})['line'] == 'Vienna U1'


def test_each_service_date_uses_its_pinned_weekly_snapshot():
    from datetime import date
    assert source_for(date(2026, 6, 1), ARCHIVES)['captured'] == '2026-05-26'
    assert source_for(date(2026, 6, 2), ARCHIVES)['captured'] == '2026-06-02'
    assert source_for(date(2026, 6, 8), ARCHIVES)['captured'] == '2026-06-02'
    with pytest.raises(ValueError): source_for(date(2026, 6, 9), ARCHIVES)


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.AUSTRIA_PATH, 'rt') as stream: return json.load(stream)


def test_historical_metro_has_all_five_lines_and_attributed_source_shapes(reference):
    meta = reference['metadata']
    assert {a['sha256'] for a in ARCHIVES} <= {s['sha256'] for s in meta['sources']}
    assert 'Wiener Linien' in meta['attribution'] and meta['license'] == 'CC BY 4.0'
    patterns = [p for p in reference['patterns'].values() if p['mode'] == 'subway']
    assert {p['line'] for p in patterns} == {'Vienna '+line for line in LINES}
    assert {p['operator'] for p in patterns} == {'Wiener Linien'}
    assert {p['line']: p['color'] for p in patterns} == {
        'Vienna U1': '#E3000F', 'Vienna U2': '#A862A4', 'Vienna U3': '#EF7C00',
        'Vienna U4': '#319F49', 'Vienna U6': '#9D6830'}
    assert all('stops' not in p for p in patterns)
    for p in patterns:
        legs = reference['stop_patterns'][p['stop_pattern']]['legs']
        assert all(reference['paths'][leg]['quality'] == 'shape' for leg in legs)
    assert not meta['omitted_trips']
    for rows in reference['days'].values():
        assert sum(reference['patterns'][p]['mode'] == 'subway' for p, _, _ in rows) > 2000


def test_train_and_metro_ids_do_not_collide_and_modes_filter_independently(reference):
    for rows in reference['days'].values():
        assert len(rows) == len({(t, offset) for _, t, offset in rows})
        assert all(t.startswith(('at-oebb:', 'at-vienna:')) for _, t, _ in rows)
    trains = replay.get_replay_day('2026-06-01', 'austria', modes=('train',))
    assert len(trains['services']) == 5831
    metro = replay.get_replay_day('2026-06-01', 'austria', modes=('subway',))
    assert all(s['mode'] == 'subway' for s in metro['services'])
    assert {metro['transit_patterns'][s['pattern']]['line'] for s in metro['services']} == {'Vienna '+line for line in LINES}
    assert metro['timezone'] == 'Europe/Vienna'
    assert descriptor('2026-06-01', 'austria')['modes'] == ['subway', 'train']
    for mode in ['bus', 'tram']:
        with pytest.raises(ValueError): descriptor('2026-06-01', 'austria', [mode])
