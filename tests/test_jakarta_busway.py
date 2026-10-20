from datetime import date
import gzip
import json

import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_jakarta_busway import frequency_departures, selected_route, SHA256, ROOT


def test_brt_scope_and_half_open_frequency_windows():
    assert selected_route({'route_type': '3', 'route_desc': 'BRT'}, {})
    for kind in ['Mikrotrans', 'Angkutan Umum Integrasi', 'Royaltrans', 'Bus Wisata']:
        assert not selected_route({'route_type': '3', 'route_desc': kind}, {})
    row = {'start_time': '23:50:00', 'end_time': '24:10:00', 'headway_secs': '600', 'exact_times': '0'}
    assert frequency_departures([row]) == [85800, 86400]
    for bad in [{**row, 'headway_secs': '0'}, {**row, 'exact_times': '1'}, {**row, 'end_time': '23:00:00'}]:
        with pytest.raises(ValueError): frequency_departures([bad])
    with pytest.raises(ValueError): frequency_departures([row, row])


def test_busway_days_are_shared_estimates_with_own_colours_and_road_shapes():
    seen, routes, colours = set(), set(), set()
    counts = []
    for path in sorted((ROOT / 'data/reference/jakarta/bus').glob('*.json.gz')):
        with gzip.open(path, 'rt') as stream:
            r = json.load(stream)
        day = path.name.removesuffix('.json.gz')
        assert set(r['days']) == {day}
        assert r['metadata']['frequency_based'] and r['metadata']['snapshot_date'] == '2026-05-07'
        assert r['metadata']['sources'][0]['sha256'] == SHA256
        assert not r['metadata']['omitted_trips'] and not r['metadata']['unresolved_geometry_trips']
        assert len(r['patterns']) < 200
        assert 'not exact departures' in r['metadata']['note']
        counts.append(len(r['days'][day]))
        for p in r['patterns'].values():
            assert p['mode'] == 'bus' and p['operator'] == 'TransJakarta' and p['frequency_based']
            assert 'stops' not in p
            routes.add(p['route_id']); colours.add(p['color'])
            if p['route_id'] == '1': assert p['color'] == '#D62126'
        for key, trip, offset in r['days'][day]:
            p = r['patterns'][key]
            assert 10800 <= offset + p['times'][1] < 97200
            occurrence = (trip, date.fromisoformat(day).toordinal() * 86400 + offset)
            assert occurrence not in seen
            seen.add(occurrence)
        assert all(p['quality'] == 'shape' and len(p['coordinates']) >= 2 for p in r['paths'].values())
    assert counts == [15073, 15073, 15073, 15073, 15043, 14250, 15534]
    assert len(routes) == 32 and {str(i) for i in range(1,15)} <= routes
    assert len(colours) >= 14 and '#FF8200' not in colours


def test_buses_load_only_when_selected_and_do_not_mutate_rail(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_JAKARTA_BUS_REFERENCE', str(tmp_path / 'missing'))
    assert descriptor('2025-12-15', 'jakarta')['modes'] == ['commuter_rail', 'light_rail', 'subway', 'train']
    rail = replay.get_replay_day('2025-12-15', 'jakarta')
    assert len(rail['services']) == 2137
    monkeypatch.delenv('SUNTRAIN_JAKARTA_BUS_REFERENCE')
    assert descriptor('2025-12-15', 'jakarta', ['bus'])['bus_data_loaded']
    combined = replay.get_replay_day('2025-12-15', 'jakarta', modes=('commuter_rail', 'subway', 'light_rail', 'train', 'bus'))
    assert len(combined['services']) == 2137 + 15073
    assert len(rail['services']) == 2137
    bus = replay.get_replay_day('2025-12-15', 'jakarta', modes=('bus',))
    assert len(bus['services']) == 15073
    assert all(s['mode'] == 'bus' for s in bus['services'])
    assert 'frequency-based' in bus['schedule']['replay_note']
    assert bus['bus_schedule']['license'] == 'CC BY 4.0'
