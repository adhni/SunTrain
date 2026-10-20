"""Nationwide intercity scope, shared schedules, geometry and multi-day clocks."""
from collections import Counter
from datetime import date, datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard.replay import US_RAIL_PATH, get_replay_day
from scripts.prepare_american_replay import AMTRAK_ARCHIVES, amtrak_geometry, selected_route, shape_legs
from scripts.prepare_rail_replay import source_for
from schedule_helpers import expanded_reference


def test_scope_excludes_buses_commuter_operators_and_unrelated_canadian_trains():
    agencies = {str(i): {'agency_name': name} for i, name in enumerate(
        ['Amtrak', 'Via Rail Canada', 'MARC Commuter Rail', 'Shore Line East Commuter Rail', 'Brightline'])}
    route = {'agency_id': '0', 'route_type': '2', 'route_long_name': 'California Zephyr'}
    assert selected_route('amtrak', route, agencies)
    assert not selected_route('amtrak', {**route, 'route_type': '3'}, agencies)
    assert selected_route('amtrak', {**route, 'agency_id': '1', 'route_long_name': 'Maple Leaf'}, agencies)
    for identifier in ['1', '2', '3', '4']:
        assert not selected_route('amtrak', {**route, 'agency_id': identifier}, agencies)
    assert selected_route('brightline', {**route, 'agency_id': 'BL'}, {'BL': {'agency_name': 'Brightline'}})
    assert not selected_route('brightline', {**route, 'agency_id': 'EVENT'}, {'EVENT': {'agency_name': 'Event Train'}})


def test_archives_change_only_on_the_validated_service_date():
    assert source_for(date(2026, 10, 17), AMTRAK_ARCHIVES)['published'] == '2026-10-10'
    assert source_for(date(2026, 10, 18), AMTRAK_ARCHIVES)['published'] == '2026-10-17'
    with pytest.raises(ValueError, match='exactly one'):
        source_for(date(2026, 10, 20), AMTRAK_ARCHIVES)


def test_isolated_off_track_stop_keeps_other_legs_without_drawing_connectors():
    points = [[i * .01, 0] for i in range(5)]
    coordinates = [points[0], [.01, .01], *points[2:]]
    legs = shape_legs(points, coordinates)
    assert legs[:2] == [None, None]
    assert legs[2:] == [[points[2], points[3]], [points[3], points[4]]]
    # A later pair must never rewind along a one-way shape after a valid leg.
    assert shape_legs(points, [points[2], points[3], points[1], points[2]])[1:] == [None, None]


def test_missing_shape_uses_only_a_verified_shape_from_the_same_route_and_snapshot():
    points = [[i * .01, 0] for i in range(3)]
    shapes = {'s': [(i, None, p) for i, p in enumerate(points)]}
    trips = {'t': {'route_id': 'A', 'shape_id': 's'}}
    resolve = amtrak_geometry({}, trips, shapes)
    assert all(resolve({'route_id': 'A'}, {}, [], points))
    assert resolve({'route_id': 'B'}, {}, [], points) == [None, None]
    # No geometry from an earlier factory is available in a different snapshot.
    assert amtrak_geometry({}, {}, {})({'route_id': 'A'}, {}, [], points) == [None, None]


def test_bundled_week_has_authentic_operators_train_numbers_and_compact_schedules():
    with gzip.open(US_RAIL_PATH, 'rt') as stream:
        packed = json.load(stream)
    assert len(packed['patterns']) == 453
    assert all('stops' not in p and p['stop_pattern'] in packed['stop_patterns'] for p in packed['patterns'].values())
    reference = expanded_reference(packed)
    assert [len(rows) for rows in reference['days'].values()] == [333, 336, 334, 335, 330, 319, 322]
    assert not reference['metadata']['omitted_trips']
    assert [s['sha256'] for s in reference['metadata']['sources'][:2]] == [s['sha256'] for s in AMTRAK_ARCHIVES]
    lines = {p['line'] for p in reference['patterns'].values()}
    assert lines >= {'Acela', 'Northeast Regional', 'California Zephyr', 'Empire Builder', 'Southwest Chief',
                     'Coast Starlight', 'Sunset Limited', 'Crescent', 'Lake Shore Limited', 'Silver Meteor',
                     'Floridian', 'Pacific Surfliner', 'Amtrak Cascades', 'Capitol Corridor', 'Downeaster',
                     'Maple Leaf', 'Brightline · Miami–Orlando'}
    assert {p['operator'] for p in reference['patterns'].values()} == {'Amtrak', 'Brightline', 'VIA Rail (Maple Leaf)'}
    for p in reference['patterns'].values():
        assert p['mode'] == 'train' and len(p['stops']) == len(p['legs']) + 1
        assert all(a <= b for a, b in zip(p['times'], p['times'][1:]))
        for leg in p['legs']:
            path = reference['paths'][leg]
            if path['quality'] == 'approximate':
                assert path['coordinates'] == path['distances'] == []
            else:
                assert path['quality'] == 'shape' and len(path['coordinates']) >= 2
    brightline = [p for p in reference['patterns'].values() if p['operator'] == 'Brightline']
    assert {p['color'] for p in brightline} == {'#F2E205'}
    assert all(reference['paths'][leg]['quality'] == 'shape' for p in brightline for leg in p['legs'])
    assert {reference['stations'][s[0]]['name'] for p in brightline for s in p['stops']} == {
        'Miami', 'Aventura', 'Fort Lauderdale', 'Boca Raton', 'West Palm Beach', 'Orlando'}


def test_all_days_keep_one_departure_owner_and_allow_multiday_arrivals_without_expansion(monkeypatch, tmp_path):
    monkeypatch.setenv('SUNTRAIN_PARQUET_GLOB', str(tmp_path / 'absent.parquet'))
    occurrences = Counter()
    for index in range(12, 19):
        day = f'2026-10-{index}'
        payload = get_replay_day(day, 'us_rail')
        assert payload['timezone'] == 'America/New_York' and not payload['passenger_data']
        assert datetime.fromtimestamp(payload['initial'], ZoneInfo(payload['timezone'])).hour == 8
        assert payload['end'] > payload['start'] + 2 * 86400
        for service in payload['services']:
            assert 'stops' not in service and service['number']
            p = payload['transit_patterns'][service['pattern']]
            departure = service['departure'] + p['times'][1]
            assert payload['start'] <= departure < payload['start'] + 86400
            assert service['departure'] + p['times'][-1] <= payload['end']
            occurrences[service['source_trip_id'], service['departure']] += 1
        zephyr = next(s for s in payload['services'] if s['number'] == '5' and
                      payload['transit_patterns'][s['pattern']]['line'] == 'California Zephyr')
        p = payload['transit_patterns'][zephyr['pattern']]
        assert datetime.fromtimestamp(zephyr['departure'], ZoneInfo('America/New_York')).strftime('%H:%M') == '15:00'
        assert datetime.fromtimestamp(zephyr['departure'], ZoneInfo('America/Chicago')).strftime('%H:%M') == '14:00'
        arrival = datetime.fromtimestamp(zephyr['departure'] + p['times'][-1], ZoneInfo('America/Los_Angeles'))
        assert arrival.strftime('%H:%M') == '16:57' and (arrival.date() - date.fromisoformat(day)).days == 2
    assert max(occurrences.values()) == 1
    with pytest.raises(ValueError, match='covers'):
        get_replay_day('2026-10-19', 'us_rail')


def test_us_http_bundle_is_compressed_shared_and_reusable_without_rebuilding(monkeypatch, tmp_path):
    from flask import Flask
    from dashboard import replay, replay_http

    monkeypatch.setenv('SUNTRAIN_PARQUET_GLOB', str(tmp_path / 'absent.parquet'))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE', str(tmp_path / 'cache'))
    app = Flask(__name__)
    replay_http.register_replay_routes(app)
    client = app.test_client()
    info = replay_http.descriptor('2026-10-12', 'us_rail')
    assert len(json.dumps(info)) < 600
    response = client.get(info['url'], headers={'Accept-Encoding': 'gzip'})
    assert response.status_code == 200 and response.headers['Content-Encoding'] == 'gzip'
    payload = json.loads(gzip.decompress(response.data))
    assert len(payload['services']) == 333 and len(response.data) < 3_000_000
    assert all('stops' not in service for service in payload['services'])
    monkeypatch.setattr(replay, 'get_replay_day', lambda *a, **k: pytest.fail('cached response rebuilt'))
    assert client.get(info['url'], headers={'Accept-Encoding': 'gzip',
                                          'If-None-Match': response.headers['ETag']}).status_code == 304
