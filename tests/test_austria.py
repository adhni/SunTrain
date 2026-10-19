from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_austria_replay import SOURCE, OPERATORS, domestic_sequence, selected_route


def test_rail_scope_excludes_other_modes_and_unvalidated_operators():
    agencies = {key: {'agency_name': name} for key, name in OPERATORS.items()}
    for agency in agencies:
        assert selected_route({'agency_id': agency, 'route_type': '2'}, agencies)
    for mode in ['0', '1', '3', '4', '700', '100']:
        assert not selected_route({'agency_id': '01', 'route_type': mode}, agencies)
    assert not selected_route({'agency_id': 'unknown', 'route_type': '2'}, agencies)
    assert not selected_route({'agency_id': '01', 'route_type': '2', 'route_id': '11-220-A-j26-1'}, agencies)
    assert not selected_route({'agency_id': '01', 'route_type': '2'}, {'01': {'agency_name': 'changed'}})


def test_domestic_portion_preserves_foreign_intermediate_calls_and_times():
    calls = [{'stop_id': stop, 'arrival_time': f'{22+i}:00:00'} for i, stop in enumerate(
        ['de:1', 'at:salzburg', 'de:rosenheim', 'at:innsbruck', 'ch:1'])]
    assert domestic_sequence(calls) == calls[1:4]
    assert domestic_sequence(calls[:2]) == []
    assert domestic_sequence([]) == []


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.AUSTRIA_PATH, 'rt') as stream: return json.load(stream)


def test_pinned_annual_source_compact_schedules_and_nationwide_scope(reference):
    meta = reference['metadata']
    assert meta['sources'][0]['sha256'] == SOURCE['sha256']
    assert meta['sources'][0]['published'] == '2025-12-12'
    assert meta['schedule_encoding'] == 'shared-stops-flat-times-v1'
    assert meta['license'] == 'CC BY 4.0'
    assert 'annual' in meta['replay_note'] and 'amendments' in meta['replay_note']
    assert not meta['omitted_trips']
    assert {p['mode'] for p in reference['patterns'].values()} == {'train', 'subway'}
    assert all('stops' not in p for p in reference['patterns'].values())
    patterns = [p for p in reference['patterns'].values() if p['mode'] == 'train']
    assert {p['operator'] for p in patterns} == set(OPERATORS.values())
    assert {'RJ', 'RJX', 'IC', 'EC', 'ICE', 'NJ', 'EN', 'REX', 'R', 'S', 'CAT'} <= {p['category'] for p in patterns}
    names = {s['name'] for s in reference['stations']}
    for fragment in ['Wien', 'Linz', 'Salzburg', 'Graz', 'Innsbruck', 'Bregenz', 'Klagenfurt', 'Schruns']:
        assert any(fragment in name for name in names), fragment


def test_unique_start_windows_and_overnight_services(reference):
    seen, overnight = [], []
    assert len(reference['days']) == 7
    for day, rows in reference['days'].items():
        assert len(rows) > 3000
        midnight = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Vienna')).timestamp()
        for key, trip, offset in rows:
            assert 10800 <= offset + reference['patterns'][key]['times'][1] < 97200
            seen.append((trip, midnight+offset))
            if offset < 86400 < offset+reference['patterns'][key]['times'][-1]:
                overnight.append(trip)
    assert len(seen) == len(set(seen)) and overnight


def test_source_shapes_cover_long_distance_suburban_and_alpine_services(reference):
    total, matched = 0, 0
    for rows in reference['days'].values():
        for key, _, _ in rows:
            p = reference['patterns'][key]
            for leg in reference['stop_patterns'][p['stop_pattern']]['legs']:
                total += 1
                matched += bool(reference['paths'][leg]['coordinates'])
    assert matched/total > .95
    for category in ['RJX', 'NJ', 'S', 'REX']:
        paths = [reference['paths'][leg] for p in reference['patterns'].values() if p['category'] == category
                 for leg in reference['stop_patterns'][p['stop_pattern']]['legs']]
        assert any(len(p['coordinates']) > 10 for p in paths), category
    for path in reference['paths'].values():
        if path['quality'] == 'approximate':
            assert path['coordinates'] == path['distances'] == []
        else:
            assert path['quality'] == 'shape' and len(path['coordinates']) >= 2


def test_loader_reuses_city_replay_and_preserves_commercial_numbers(monkeypatch):
    monkeypatch.setattr(replay.data, 'get_metadata', lambda: pytest.fail('Austria queried Melbourne'))
    day = replay.get_replay_day('2026-06-01', 'austria', modes=('train',))
    assert day['services'] and day['timezone'] == 'Europe/Vienna'
    assert all(s['mode'] == 'train' and s['source_trip_id'] for s in day['services'])
    assert any(s['number'].startswith('RJX ') for s in day['services'])
    assert city_settings('austria')['start_date'] == city_settings('switzerland')['start_date']
    assert not city_settings('austria')['passenger_data']
    assert descriptor('2026-06-01', 'austria')['modes'] == ['subway', 'train']
    with pytest.raises(ValueError): descriptor('2026-06-01', 'austria', ['bus'])
    with pytest.raises(ValueError): replay.get_replay_day('2026-06-08', 'austria')
