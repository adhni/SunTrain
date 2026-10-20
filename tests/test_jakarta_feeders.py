from collections import defaultdict
from datetime import date
import gzip
import json

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_jakarta_busway import ROOT, SHA256, selected_feeder


def test_feeder_scope_is_the_source_category_without_other_bus_layers():
    assert selected_feeder({'route_type': '3', 'route_desc': 'Angkutan Umum Integrasi'}, {})
    for category in ['BRT', 'Mikrotrans', 'Rusun', 'Royaltrans', 'Transjabodetabek', 'Shuttle', 'Bus Wisata']:
        assert not selected_feeder({'route_type': '3', 'route_desc': category}, {})
    assert not selected_feeder({'route_type': '2', 'route_desc': 'Angkutan Umum Integrasi'}, {})


def test_feeder_bundles_preserve_colours_shared_schedules_paths_and_departure_ownership():
    files = sorted((ROOT / 'data/reference/jakarta/feeder_bus').glob('*.json.gz'))
    assert len(files) == 7
    routes, colours, seen, counts = set(), set(), set(), []
    checked_templates = set()
    expected = {
        '1W-L01': (18000, 79200, 900), '1W-R01': (18000, 79200, 1200),
        '1W-R02': (18000, 79200, 1200), '4K-R08': (18000, 21600, 1300),
        '8K-L02': (18000, 79200, 960), '21ST-L02': (18000, 79200, 360),
    }
    for path in files:
        with gzip.open(path, 'rt') as stream:
            r = json.load(stream)
        day = path.name.removesuffix('.json.gz')
        assert set(r['days']) == {day}
        assert r['metadata']['sources'][0]['sha256'] == SHA256
        assert r['metadata']['snapshot_date'] == '2026-05-07'
        assert r['metadata']['license'] == 'CC BY 4.0'
        assert 'not December 2025 history' in r['metadata']['note']
        assert not r['metadata']['omitted_trips'] and not r['metadata']['unresolved_geometry_trips']
        assert path.stat().st_size < 450_000
        assert len(r['patterns']) <= 159
        for p in r['patterns'].values():
            assert p['mode'] == 'feeder_bus' and p['operator'] == 'TransJakarta' and p['frequency_based']
            assert 'stops' not in p and 'legs' not in p
            assert all(a <= b for a, b in zip(p['times'], p['times'][1:]))
            routes.add(p['route_id']); colours.add(p['color'].upper())
            if p['route_id'] == '1W': assert p['color'].upper() == '#D65E62'
            if p['route_id'] == '8K': assert p['color'].upper() == '#DD6AAB'
            if p['route_id'] == '4K': assert p['color'].upper() == '#512C62'
        counts.append(len(r['days'][day]))
        by_trip = defaultdict(list)
        for key, trip, offset in r['days'][day]:
            departure = offset + r['patterns'][key]['times'][1]
            assert 18000 <= departure < 79200
            assert trip.endswith(':estimate-' + str(departure))
            occurrence = (trip, date.fromisoformat(day).toordinal() * 86400 + offset)
            assert occurrence not in seen
            seen.add(occurrence)
            by_trip[trip.split(':', 1)[0]].append(departure)
        for trip, window in expected.items():
            if trip in by_trip:
                assert sorted(by_trip[trip]) == list(range(*window))
                checked_templates.add(trip)
        assert all(p['quality'] == 'shape' and len(p['coordinates']) >= 2 for p in r['paths'].values())
    assert len(routes) == 66 and {'1W', '4K', '8K', '21ST'} <= routes
    assert len(colours) == 15 and '#FF8200' not in colours
    assert counts == [9336, 9336, 9336, 9336, 9336, 8805, 9171]
    assert checked_templates == set(expected)


def test_feeders_only_open_the_selected_layer_and_retain_provenance(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_JAKARTA_REFERENCE', str(tmp_path / 'missing-rail.gz'))
    monkeypatch.setenv('SUNTRAIN_JAKARTA_BUS_REFERENCE', str(tmp_path / 'missing-busway'))
    monkeypatch.setenv('SUNTRAIN_JAKARTA_MIKROTRANS_REFERENCE', str(tmp_path / 'missing-mikrotrans'))
    info = descriptor('2025-12-15', 'jakarta', ['feeder_bus'])
    assert info['modes'] == ['feeder_bus'] and info['bus_data_loaded']
    payload = replay.get_replay_day('2025-12-15', 'jakarta', modes=('feeder_bus',))
    assert len(payload['services']) == 9336
    assert all(s['mode'] == 'feeder_bus' and 'stops' not in s for s in payload['services'])
    assert 'TransJakarta feeders' in payload['schedule']['replay_note']
    assert payload['bus_schedule']['source_url'] and payload['bus_schedule']['license'] == 'CC BY 4.0'


def test_all_jakarta_layers_can_coexist_without_duplicate_services_or_changing_defaults(monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv('SUNTRAIN_JAKARTA_FEEDER_BUS_REFERENCE', str(tmp_path / 'missing-feeders'))
    defaults = descriptor('2025-12-15', 'jakarta')
    assert 'feeder_bus' not in defaults['modes']
    rail = replay.get_replay_day('2025-12-15', 'jakarta')
    road = replay.get_replay_day('2025-12-15', 'jakarta', modes=('bus', 'mikrotrans'))
    assert len(road['services']) == 52270
    monkeypatch.delenv('SUNTRAIN_JAKARTA_FEEDER_BUS_REFERENCE')
    modes = (*defaults['modes'], 'bus', 'mikrotrans', 'feeder_bus')
    combined = replay.get_replay_day('2025-12-15', 'jakarta', modes=modes)
    assert len(combined['services']) == 2137 + 15073 + 37197 + 9336
    assert len({s['id'] for s in combined['services']}) == len(combined['services'])
    assert len(rail['services']) == 2137 and len(road['services']) == 52270
    assert 'Angkutan Umum Integrasi selection' in combined['bus_schedule']['attribution']
    assert descriptor('2025-12-15', 'jakarta') == defaults


def test_feeder_revision_changes_only_when_selected(monkeypatch, tmp_path):
    day = '2025-12-15'
    before = descriptor(day, 'jakarta')
    micro_before = descriptor(day, 'jakarta', ['mikrotrans'])
    monkeypatch.setenv('SUNTRAIN_JAKARTA_FEEDER_BUS_REFERENCE', str(tmp_path))
    path = tmp_path / (day + '.json.gz')
    path.write_bytes(b'first')
    selected = descriptor(day, 'jakarta', ['feeder_bus'])
    path.write_bytes(b'updated-source')
    assert descriptor(day, 'jakarta') == before
    assert descriptor(day, 'jakarta', ['mikrotrans']) == micro_before
    assert descriptor(day, 'jakarta', ['feeder_bus'])['revision'] != selected['revision']
