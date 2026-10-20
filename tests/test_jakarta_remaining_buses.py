from datetime import date
import gzip
import json

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_jakarta_busway import ROAD_LAYERS, ROOT, SHA256, frequency_departures, selected_layer


LAYERS = {
    'transjabodetabek': (18, [3495, 3495, 3495, 3495, 3495, 3381, 3993], {'#FFFF6D'}),
    'rusun_bus': (17, [1731] * 7, {'#5C5062', '#717092', '#78809C', '#85A4A2', '#9B7172', '#A8BFA8', '#FDECB4'}),
    'royaltrans': (10, [198] * 5 + [0, 0], {'#9C4782'}),
    'shuttle_bus': (8, [370] * 5 + [374, 374], {'#0754D2', '#184E9E', '#B7342D'}),
    'tourist_bus': (3, [105] * 7, {'#FFB6DB'}),
}


def test_category_selection_stays_disjoint():
    for mode, (category, _, _) in ROAD_LAYERS.items():
        route = {'route_type': '3', 'route_desc': category, 'route_short_name': 'JAK.01' if mode == 'mikrotrans' else 'example'}
        assert {m for m in ROAD_LAYERS if selected_layer(m, route, {})} == {mode}
        assert not selected_layer(mode, {**route, 'route_type': '2'}, {})


def test_audited_midnight_window_has_no_missing_or_duplicate_departures():
    rows = [{'start_time': start, 'end_time': end, 'headway_secs': '600', 'exact_times': '0'}
            for start, end in [('07:00:00', '19:00:00'), ('19:00:00', '00:00:00'), ('00:00:00', '07:00:00')]]
    with pytest.raises(ValueError):
        frequency_departures(rows)
    assert frequency_departures(rows, midnight_end=True) == list(range(0, 86400, 600))
    with pytest.raises(ValueError):
        frequency_departures(rows + [rows[0]], midnight_end=True)
    with pytest.raises(ValueError):
        frequency_departures([{**rows[0], 'end_time': '06:00:00'}], midnight_end=True)


@pytest.mark.parametrize('mode', LAYERS)
def test_remaining_bundles_keep_calendars_colours_shared_schedules_and_road_paths(mode):
    route_count, counts, colours = LAYERS[mode]
    files = sorted((ROOT / 'data/reference/jakarta' / mode).glob('*.json.gz'))
    assert len(files) == 7
    seen, routes, actual_colours = set(), set(), set()
    actual_counts = []
    for path in files:
        day = path.name.removesuffix('.json.gz')
        with gzip.open(path, 'rt') as stream:
            r = json.load(stream)
        assert set(r['days']) == {day}
        m = r['metadata']
        assert m['sources'][0]['sha256'] == SHA256 and m['snapshot_date'] == '2026-05-07'
        assert m['license'] == 'CC BY 4.0' and 'not December 2025 history' in m['note']
        assert not m['omitted_trips'] and not m['unresolved_geometry_trips']
        assert path.stat().st_size < 150_000
        actual_counts.append(len(r['days'][day]))
        for p in r['patterns'].values():
            assert p['mode'] == mode and p['operator'] == 'TransJakarta' and p['frequency_based']
            assert 'stops' not in p and 'legs' not in p
            assert all(a <= b for a, b in zip(p['times'], p['times'][1:]))
            routes.add(p['route_id']); actual_colours.add(p['color'].upper())
        for key, trip, offset in r['days'][day]:
            departure = offset + r['patterns'][key]['times'][1]
            assert 10800 <= departure < 97200 and ':estimate-' in trip
            if mode == 'royaltrans':
                assert departure < 33600 or departure >= 57600
            occurrence = (trip, date.fromisoformat(day).toordinal() * 86400 + offset)
            assert occurrence not in seen
            seen.add(occurrence)
        assert all(p['quality'] == 'shape' and len(p['coordinates']) >= 2 for p in r['paths'].values())
        if mode == 'shuttle_bus':
            assert 'SOE-L01' in m['source_corrections'][0]
            airport = sorted(offset + r['patterns'][key]['times'][1]
                             for key, trip, offset in r['days'][day] if trip.startswith('SOE-L01:'))
            assert airport == list(range(10800, 97200, 600))
        if mode == 'royaltrans' and date.fromisoformat(day).weekday() >= 5:
            assert not any(r[k] for k in ['patterns', 'stop_patterns', 'paths', 'stations'])
    assert actual_counts == counts
    assert len(routes) == route_count and actual_colours == colours


@pytest.mark.parametrize('mode', LAYERS)
def test_each_new_layer_is_independent_and_optional(mode, monkeypatch, tmp_path):
    replay.clear_replay_cache()
    default = descriptor('2025-12-15', 'jakarta')
    # Neither rail nor any unselected bus category is required for this request.
    monkeypatch.setenv('SUNTRAIN_JAKARTA_REFERENCE', str(tmp_path / 'missing-rail.gz'))
    for other in replay.bus_modes('jakarta') - {mode}:
        monkeypatch.setenv(f'SUNTRAIN_JAKARTA_{other.upper()}_REFERENCE', str(tmp_path / other))
    info = descriptor('2025-12-15', 'jakarta', [mode])
    assert info['modes'] == [mode] and info['bus_data_loaded']
    assert mode not in default['modes']
    payload = replay.get_replay_day('2025-12-15', 'jakarta', modes=(mode,))
    assert len(payload['services']) == LAYERS[mode][1][0]
    assert all(s['mode'] == mode and 'stops' not in s for s in payload['services'])
    assert payload['schedule']['license'] == 'CC BY 4.0'


def test_all_eight_bus_categories_combine_without_collisions_or_mutating_rail():
    replay.clear_replay_cache()
    default = descriptor('2025-12-15', 'jakarta')
    rail = replay.get_replay_day('2025-12-15', 'jakarta')
    combined = replay.get_replay_day('2025-12-15', 'jakarta', modes=(*default['modes'], *ROAD_LAYERS))
    assert len(combined['services']) == 2137 + 67505
    assert len({s['id'] for s in combined['services']}) == len(combined['services'])
    assert len(rail['services']) == 2137
    assert len({p['route_id'] for p in combined['transit_patterns'].values() if p['mode'] in ROAD_LAYERS}) == 249
    for mode in LAYERS:
        assert ROAD_LAYERS[mode][0] + ' selection' in combined['bus_schedule']['attribution']
    assert combined['bus_schedule']['attribution'].count('GTFS Static Transjakarta') == 1
    assert combined['schedule']['replay_note'].count('TransJakarta buses:') == 1
    assert 'Royaltrans runs on weekdays only' in combined['schedule']['replay_note']
    royal_weekend = replay.get_replay_day('2025-12-20', 'jakarta', modes=('royaltrans',))
    assert royal_weekend['services'] == [] and royal_weekend['bus_schedule']['available']
    assert 'weekdays only' in royal_weekend['schedule']['replay_note']
