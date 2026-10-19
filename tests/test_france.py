from collections import Counter
from datetime import datetime
import gzip
import json
import hashlib
from zoneinfo import ZoneInfo
from zipfile import ZipFile

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_geometry import compile_ways, pk
from scripts.prepare_france_replay import (
    FranceRailGraph, GEOMETRY, GEOMETRY_SHA256, NATIONAL, NATIONAL_AGENCIES,
    SUBURBAN, SUBURBAN_AGENCIES, national_sequence, selected_route,
)
from scripts.prepare_rail_replay import prepare
from test_rail_preparation import external_source
from schedule_helpers import expanded_pattern


def test_scope_excludes_buses_and_coaches_even_when_mislabelled_as_rail():
    agencies = {key: {'agency_name': name} for key, name in NATIONAL_AGENCIES.items()}
    route = {'agency_id': '1187', 'route_type': '2', 'route_short_name': 'test', 'route_long_name': 'test'}
    assert selected_route(route, agencies)
    assert not selected_route({**route, 'route_type': '3'}, agencies)
    assert not selected_route(route, {'1187': {'agency_name': 'Unknown'}})
    for product in ['Car TER', 'Car à réservation', 'TramTrain', 'Navette']:
        sequence = [{'stop_id': f'StopPoint:OCE{product}-{stop}'} for stop in ['87100000', '87200000']]
        assert national_sequence(sequence, route, Counter()) == []
    suburban = {key: {'agency_name': name} for key, name in SUBURBAN_AGENCIES.items()}
    assert selected_route({'agency_id': 'IDFM:71', 'route_type': '2'}, suburban, True)
    assert not selected_route({'agency_id': 'IDFM:93', 'route_type': '2'}, {'IDFM:93': {'agency_name': 'TER'}}, True)


def test_domestic_clipping_preserves_foreign_intermediate_calls_and_overnight_times():
    sequence = [{'stop_id': f'StopPoint:OCEICE-{code}', 'departure_time': f'{i+22}:00:00'}
                for i, code in enumerate(['80100000', '87100000', '85100000', '87200000', '80100001'])]
    assert national_sequence(sequence, {}, Counter()) == sequence[1:4]
    assert national_sequence(sequence[:2], {}, Counter()) == []


def feature(points, fragment=0, kind='VPA'):
    return {'geometry': {'type': 'LineString', 'coordinates': points},
            'properties': {'idgaia': 'repeated', 'rg_troncon': fragment, 'type_voie': kind,
                           'code_ligne': '1', 'pk_debut_r': '0+000', 'pk_fin_r': '1+000'}}


def test_geometry_preserves_junctions_without_joining_interior_crossings_or_repeated_fragment_ids():
    a, middle, b = [2, 48], [2.02, 48], [2.04, 48]
    crossing = [feature([a, middle, b]), feature([[2.02, 47.98], middle, [2.02, 48.02]], 1)]
    ways, _ = compile_ways(crossing, [])
    assert FranceRailGraph(ways).leg(a, [2.02, 48.02]) is None
    # A real original endpoint touching an interior vertex creates a junction.
    ways, _ = compile_ways([crossing[0], feature([middle, [2.02, 48.02]], 1)], [])
    assert FranceRailGraph(ways).leg(a, [2.02, 48.02])
    positions = {}
    for way in ways:
        for node, point in zip(way['node_ids'], way['coordinates']):
            assert node not in positions or positions[node] == point
            positions[node] = point
    assert compile_ways([feature([a, b], kind='VS')], [])[0] == []


def test_negative_chainage_does_not_drop_high_speed_corridor_preference():
    assert pk('000-168') == -168
    assert pk('711+163') == 711163
    f = feature([[2, 48], [3, 47]])
    f['properties'].update(pk_debut_r='000-168', pk_fin_r='711+163')
    ways, _ = compile_ways([f], [{'code_ligne': '000001', 'pkd': '090+765', 'pkf': '205+599', 'v_max': '300'}])
    assert ways[0]['speed'] == 300


@pytest.mark.parametrize('latitude', [43, 49])
def test_station_matching_uses_local_metres_and_includes_long_edge_grid_cells(latitude):
    graph = FranceRailGraph([{'node_ids': ['a', 'b'], 'coordinates': [[1, latitude], [3, latitude]], 'speed': 100}])
    assert graph.anchors([2, latitude + 149 / 111195])
    assert not graph.anchors([2, latitude + 151 / 111195])


def test_numeric_train_headsign_does_not_replace_terminal_name(tmp_path):
    source = external_source(tmp_path)
    archive_path = tmp_path / 'external.zip'
    with ZipFile(archive_path) as archive:
        tables = {name: archive.read(name) for name in archive.namelist()}
    lines = tables['trips.txt'].decode().splitlines()
    tables['trips.txt'] = ('\n'.join([lines[0] + ',trip_headsign', *[line + ',12345' for line in lines[1:]]]) + '\n').encode()
    with ZipFile(archive_path, 'w') as archive:
        for name, contents in tables.items():
            archive.writestr(name, contents)
    source['sha256'] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    output = tmp_path / 'day.json.gz'
    prepare('fixture', source, tmp_path, output, lambda *_: True,
            lambda route, trip: {'route_id': 'R', 'destination': 'Bravo'})
    with gzip.open(output, 'rt') as stream:
        reference = json.load(stream)
    assert {p['destination'] for p in reference['patterns'].values()} == {'Bravo'}


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.FRANCE_PATH, 'rt') as stream:
        return json.load(stream)


def test_pinned_week_shared_patterns_scope_and_unique_overnight_assignment(reference):
    assert file_hash(GEOMETRY) == GEOMETRY_SHA256
    assert {s['sha256'] for s in reference['metadata']['sources']} == {NATIONAL['sha256'], SUBURBAN['sha256']}
    assert reference['metadata']['license'] == reference['metadata']['geometry_license'] == 'ODbL 1.0'
    assert reference['metadata']['schedule_encoding'] == 'shared-stops-flat-times-v1'
    assert not reference['metadata']['omitted_trips']
    assert all('stops' not in p for p in reference['patterns'].values())
    assert len(reference['days']) == 7
    assert {p['product'] for p in reference['patterns'].values() if p['mode'] == 'train'} >= {
        'Train TER', 'TGV INOUI', 'OUIGO', 'INTERCITES', 'INTERCITES de nuit', 'ICE', 'Lyria'}
    occurrences = []
    overnight = []
    names = {s['name'] for s in reference['stations']}
    for city in ['Paris', 'Lyon', 'Marseille', 'Bordeaux', 'Lille', 'Strasbourg', 'Rennes', 'Toulouse']:
        assert any(city in name for name in names)
    for day, rows in reference['days'].items():
        midnight = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Paris')).timestamp()
        for key, trip, offset in rows:
            assert 10800 <= offset < 97200
            occurrences.append((trip, midnight + offset))
            p = reference['patterns'][key]
            if p.get('product') == 'INTERCITES de nuit' and offset < 86400 < offset + p['times'][-1]:
                overnight.append(trip)
    assert len(occurrences) == len(set(occurrences))
    assert overnight
    for path in reference['paths'].values():
        if path['quality'] == 'approximate':
            assert not path['coordinates'] and not path['distances']
        else:
            assert path['quality'] == 'track' and len(path['coordinates']) >= 2


@pytest.mark.parametrize('origin,destination,minimum,maximum', [
    ('Paris Gare de Lyon Hall 1 - 2', 'Lyon Part Dieu', 420, 440),
    ('Paris Montparnasse Hall 1 - 2', 'Bordeaux Saint-Jean', 525, 550),
    ('Paris Gare du Nord', 'Lille Flandres', 215, 235),
    ('Paris Est', 'Strasbourg', 425, 450),
])
def test_major_tgv_corridors_follow_detailed_plausible_railways(reference, origin, destination, minimum, maximum):
    paths = []
    for raw in reference['patterns'].values():
        if raw.get('product') != 'TGV INOUI':
            continue
        p = expanded_pattern(reference, raw)
        for a, b, key in zip(p['stops'], p['stops'][1:], p['legs']):
            if (reference['stations'][a[0]]['name'], reference['stations'][b[0]]['name']) == (origin, destination):
                paths.append(reference['paths'][key])
    assert paths
    assert all(len(p['coordinates']) > 100 and minimum < p['distances'][-1]/1000 < maximum for p in paths)


def test_france_runtime_loads_selected_modes_without_melbourne_and_has_real_destinations(monkeypatch):
    monkeypatch.setattr(replay.data, 'get_metadata', lambda: pytest.fail('France queried Melbourne warehouse'))
    payload = replay.get_replay_day('2026-06-01', 'france')
    assert len(payload['services']) == 8946
    assert all(s['mode'] == 'train' for s in payload['services'])
    assert all(payload['transit_patterns'][s['pattern']]['destination'] != s['number'] for s in payload['services'])
    assert any(s['number'].isdigit() for s in payload['services'])
    assert all(s['source_trip_id'] for s in payload['services'])
    assert descriptor('2026-06-01', 'france')['modes'] == ['train']
    assert city_settings('france')['start_date'] == city_settings('netherlands')['start_date']
    suburban = replay.get_replay_day('2026-06-01', 'france', modes=('commuter_rail',))
    assert len(suburban['services']) == 4849
    assert {p['route_short_name'] for p in suburban['transit_patterns'].values()} == set('ABCDEHJKLNPRUV')
    with pytest.raises(ValueError):
        descriptor('2026-06-01', 'france', ['bus'])
    with pytest.raises(ValueError):
        replay.get_replay_day('2026-06-08', 'france')
