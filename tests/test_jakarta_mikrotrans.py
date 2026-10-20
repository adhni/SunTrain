from datetime import date
import gzip
import json

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_jakarta_busway import ROOT, SHA256, frequency_departures, selected_mikrotrans


def test_mikrotrans_scope_and_explicit_exact_frequency_support():
    route = {'route_type': '3', 'route_desc': 'Mikrotrans', 'route_short_name': 'JAK.01'}
    assert selected_mikrotrans(route, {})
    for change in [{'route_desc': 'BRT'}, {'route_desc': 'Royaltrans'},
                   {'route_short_name': '1'}, {'route_type': '2'}]:
        assert not selected_mikrotrans({**route, **change}, {})
    row = {'start_time': '22:00:00', 'end_time': '23:59:59', 'headway_secs': '1200', 'exact_times': '1'}
    assert frequency_departures([row], allow_exact=True) == list(range(79200, 86400, 1200))
    with pytest.raises(ValueError):
        frequency_departures([row])  # BRT retains its existing strict scope.
    for bad in [{**row, 'exact_times': '2'}, {**row, 'headway_secs': '0'},
                {**row, 'end_time': '21:00:00'}]:
        with pytest.raises(ValueError):
            frequency_departures([bad], allow_exact=True)
    with pytest.raises(ValueError):
        frequency_departures([row, row], allow_exact=True)


def test_mikrotrans_days_keep_shared_schedules_hours_exactness_and_geometry_gaps():
    seen, routes, counts = set(), set(), []
    files = sorted((ROOT / 'data/reference/jakarta/mikrotrans').glob('*.json.gz'))
    assert len(files) == 7
    for path in files:
        with gzip.open(path, 'rt') as stream:
            r = json.load(stream)
        day = path.name.removesuffix('.json.gz')
        assert set(r['days']) == {day}
        metadata = r['metadata']
        assert metadata['sources'][0]['sha256'] == SHA256
        assert metadata['snapshot_date'] == '2026-05-07'
        assert metadata['exact_templates'] == 1 and metadata['estimated_templates'] == 247
        assert not metadata['omitted_trips']
        assert set(metadata['unresolved_geometry_trips']) == {
            'JAK.89-R02', 'JAK.89-L01', 'JAK.27-R01', 'JAK.27-L01', 'JAK.30-R01'}
        assert metadata['license'] == 'CC BY 4.0'
        assert 'not December 2025 history' in metadata['note']
        assert len(r['patterns']) <= 248
        assert path.stat().st_size < 1_200_000
        for p in r['patterns'].values():
            assert p['mode'] == 'mikrotrans' and p['operator'] == 'TransJakarta'
            assert p['color'].upper() == '#00609C'
            assert 'stops' not in p and 'legs' not in p
            assert all(a <= b for a, b in zip(p['times'], p['times'][1:]))
            routes.add(p['route_id'])
            if not p['frequency_based']:
                assert p['route_id'] == 'JAK.20'
        counts.append(len(r['days'][day]))
        for key, trip, offset in r['days'][day]:
            p = r['patterns'][key]
            departure = offset + p['times'][1]
            assert 10800 <= departure < 97200
            assert (':estimate-' in trip) == p['frequency_based']
            assert (':scheduled-' in trip) == (not p['frequency_based'])
            start, end = (79200, 86400) if trip.startswith(('JAK.52-R13:', 'JAK.52-R10:')) else (18000, 79200)
            if trip.startswith('JAK.43B-L02:'):
                start, end = 21600, 36000
            assert start <= departure < end
            occurrence = (trip, date.fromisoformat(day).toordinal() * 86400 + offset)
            assert occurrence not in seen
            seen.add(occurrence)
        for p in r['paths'].values():
            if p['quality'] == 'approximate':
                assert p['coordinates'] == [] and p['distances'] == []
            else:
                assert p['quality'] == 'shape' and len(p['coordinates']) >= 2
    assert counts == [37197, 37197, 37197, 37197, 37197, 37146, 37248]
    assert len(routes) == 99 and {'JAK.01', 'JAK.03', 'JAK.44', 'JAK.52'} <= routes


def test_mikrotrans_only_does_not_open_busway_or_rail(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_JAKARTA_REFERENCE', str(tmp_path / 'missing-rail.gz'))
    monkeypatch.setenv('SUNTRAIN_JAKARTA_BUS_REFERENCE', str(tmp_path / 'missing-busway'))
    info = descriptor('2025-12-15', 'jakarta', ['mikrotrans'])
    assert info['modes'] == ['mikrotrans'] and info['bus_data_loaded']
    payload = replay.get_replay_day('2025-12-15', 'jakarta', modes=('mikrotrans',))
    assert len(payload['services']) == 37197
    assert all(s['mode'] == 'mikrotrans' and 'stops' not in s for s in payload['services'])
    assert payload['schedule']['source_url'] and 'Mikrotrans' in payload['schedule']['replay_note']


def test_three_jakarta_layers_filter_independently_without_mutating_cached_rail(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_JAKARTA_MIKROTRANS_REFERENCE', str(tmp_path / 'missing'))
    rail_info = descriptor('2025-12-15', 'jakarta')
    assert 'mikrotrans' not in rail_info['modes'] and not rail_info['bus_data_loaded']
    rail = replay.get_replay_day('2025-12-15', 'jakarta')
    bus = replay.get_replay_day('2025-12-15', 'jakarta', modes=('bus',))
    assert len(bus['services']) == 15073
    monkeypatch.delenv('SUNTRAIN_JAKARTA_MIKROTRANS_REFERENCE')
    modes = (*rail_info['modes'], 'bus', 'mikrotrans')
    combined = replay.get_replay_day('2025-12-15', 'jakarta', modes=modes)
    assert len(combined['services']) == 2137 + 15073 + 37197
    assert len({s['id'] for s in combined['services']}) == len(combined['services'])
    assert len(rail['services']) == 2137
    assert 'BRT selection' in combined['bus_schedule']['attribution'] or 'BRT-only selection' in combined['bus_schedule']['attribution']
    assert 'Mikrotrans selection' in combined['bus_schedule']['attribution']
    assert 'Mikrotrans' in combined['schedule']['replay_note']
    assert descriptor('2025-12-15', 'jakarta') == rail_info


def test_descriptor_tracks_only_selected_road_layers(monkeypatch, tmp_path):
    day = '2025-12-15'
    before = descriptor(day, 'jakarta')
    bus_before = descriptor(day, 'jakarta', ['bus'])
    monkeypatch.setenv('SUNTRAIN_JAKARTA_MIKROTRANS_REFERENCE', str(tmp_path))
    path = tmp_path / (day + '.json.gz')
    path.write_bytes(b'first')
    selected = descriptor(day, 'jakarta', ['mikrotrans'])
    path.write_bytes(b'updated-source')
    assert descriptor(day, 'jakarta') == before
    assert descriptor(day, 'jakarta', ['bus']) == bus_before
    assert descriptor(day, 'jakarta', ['mikrotrans'])['revision'] != selected['revision']
