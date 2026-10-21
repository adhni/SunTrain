from collections import Counter
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_us_commuter_replay import SOURCES, geometry_factory, selected_route


def read():
    with gzip.open(replay.US_COMMUTER_PATH, 'rt') as stream:
        return json.load(stream)


def test_scope_excludes_buses_urban_rail_and_mbta_with_explicit_texrail_exception():
    for key, source in SOURCES.items():
        agency = source['agency_ids'][0]
        agencies = {agency: {'agency_name': source['name']}}
        route = {'agency_id': agency, 'route_type': source['route_types'][0],
                 'route_id': source.get('route_ids', ['R'])[0]}
        assert selected_route(key, route, agencies)
        for kind in ['3', '1', '5']:
            assert not selected_route(key, {**route, 'route_type': kind}, agencies)
        assert not selected_route(key, {**route, 'agency_id': 'MBTA'}, {'MBTA': {'agency_name': 'MBTA'}})
        if key == 'texrail':
            assert not selected_route(key, {**route, 'route_id': 'OTHER_LIGHT_RAIL'}, agencies)
        else:
            assert not selected_route(key, {**route, 'route_type': '0'}, agencies)
    assert 'boston' not in SOURCES and len(SOURCES) == 20
    # LIRR legitimately omits route.agency_id in its single-agency feed.
    assert selected_route('lirr', {'route_type': '2', 'route_id': '1'}, {'LI': {}})
    assert not selected_route('lirr', {'route_type': '2', 'route_id': '1'}, {'LI': {}, 'OTHER': {}})


def test_unassigned_metrolink_shapes_are_bound_to_their_audited_line():
    points = [[0, 0], [.01, 0], [.02, 0]]
    shapes = {'AVin': [(i, None, p) for i, p in enumerate(points)],
              'SBin': [(i, None, p) for i, p in enumerate(points)]}
    resolver = geometry_factory({'route_shapes': {'Antelope Valley Line': ['AVin']}})({}, {}, shapes)
    assert all(resolver({'route_id': 'Antelope Valley Line'}, {}, [], points))
    assert resolver({'route_id': 'San Bernardino Line'}, {}, [], points) == [None, None]


def test_reference_has_all_requested_operator_groups_and_shared_verified_geometry():
    reference = read()
    assert reference['metadata']['timezone'] == 'America/New_York'
    assert not reference['metadata']['omitted_trips']
    assert {p['operator'] for p in reference['patterns'].values()} == {s['name'] for s in SOURCES.values()}
    assert len(reference['metadata']['sources']) == 21  # DART's dated validity changes on 19 October.
    assert [len(rows) for rows in reference['days'].values()] == [4775, 4805, 4805, 4806, 4815, 3040, 2876]
    for pattern in reference['patterns'].values():
        assert pattern['mode'] == 'commuter_rail' and 'stops' not in pattern
        topology = reference['stop_patterns'][pattern['stop_pattern']]
        assert len(pattern['times']) == 2 * len(topology['stations'])
        assert all(a <= b for a, b in zip(pattern['times'], pattern['times'][1:]))
        paths = [reference['paths'][p] for p in topology['legs']]
        if pattern['operator'] == 'Metrolink':
            assert any(path['quality'] == 'shape' for path in paths)
        for path in paths:
            if path['quality'] == 'approximate':
                assert path['coordinates'] == path['distances'] == []
            else:
                assert path['quality'] == 'shape' and len(path['coordinates']) >= 2
    for rows in reference['days'].values():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        assert all(trip in reference['train_numbers'] for _, trip, _ in rows)
    weekend = reference['days']['2026-10-18']
    sunday_ops = {reference['patterns'][p]['operator'] for p, _, _ in weekend}
    assert not {'ACE', 'VRE', 'SunRail', 'Sounder', 'FrontRunner'} & sunday_ops
    monday = reference['days']['2026-10-12']
    assert 'VRE' not in {reference['patterns'][p]['operator'] for p, _, _ in monday}  # Columbus Day closure.
    nj = {p['source_route_id'] for p in reference['patterns'].values() if p['operator'] == 'NJ Transit'}
    assert {'6', '14'} <= nj  # Port Jervis and Pascack Valley belong to NJT, not Metro-North GTFS.


def test_default_view_never_opens_commuter_reference_and_commuter_only_never_opens_intercity(monkeypatch):
    original = replay.transit.read_reference
    calls = []
    def checked(path, modified):
        calls.append(path)
        assert path != str(replay.US_COMMUTER_PATH)
        return original(path, modified)
    checked.cache_clear = original.cache_clear
    replay.clear_replay_cache()
    monkeypatch.setattr(replay.transit, 'read_reference', checked)
    assert len(replay.get_replay_day('2026-10-12', 'us_rail')['services']) == 333
    assert calls == [str(replay.US_RAIL_PATH)]
    def forbidden(*args):
        pytest.fail('commuter-only opened intercity')
    forbidden.cache_clear = original.cache_clear
    monkeypatch.setattr(replay.transit, 'read_reference', forbidden)
    payload = replay.get_replay_day('2026-10-12', 'us_rail', modes=['commuter_rail'])
    assert len(payload['services']) == 4775 and all(s['mode'] == 'commuter_rail' for s in payload['services'])
    assert descriptor('2026-10-12', 'us_rail')['url'] != descriptor('2026-10-12', 'us_rail', ['commuter_rail'])['url']
    replay.clear_replay_cache()


def test_all_seven_days_combine_without_duplicates_and_keep_native_timezone_instants(monkeypatch, tmp_path):
    monkeypatch.setenv('SUNTRAIN_PARQUET_GLOB', str(tmp_path / 'absent.parquet'))
    seen = Counter()
    for index in range(12, 19):
        day = f'2026-10-{index}'
        intercity = replay.get_replay_day(day, 'us_rail', modes=['train'])
        regional = replay.get_replay_day(day, 'us_rail', modes=['commuter_rail'])
        combined = replay.get_replay_day(day, 'us_rail', modes=['train', 'commuter_rail'])
        assert len(combined['services']) == len(intercity['services']) + len(regional['services'])
        assert len({s['id'] for s in combined['services']}) == len(combined['services'])
        if index == 12:
            credits = [combined['schedule'], *combined['schedule']['additional_geometry_sources']]
            assert {source['license_url'] for source in SOURCES.values()} <= {c['geometry_license_url'] for c in credits}
            assert len(combined['schedule']['sources']) == 24
        for service in regional['services']:
            pattern = regional['transit_patterns'][service['pattern']]
            assert 'stops' not in service and 'source_trip_id' in service
            instant = service['departure'] + pattern['times'][1]
            assert regional['start'] <= instant < regional['start'] + 86400
            seen[service['source_trip_id'], service['departure']] += 1
            assert service['departure'] + pattern['times'][-1] <= combined['end']
        if index == 12:
            coaster = next(s for s in regional['services'] if s['number'] == '620' and
                           regional['transit_patterns'][s['pattern']]['operator'] == 'COASTER')
            assert datetime.fromtimestamp(coaster['departure'], ZoneInfo('America/New_York')).strftime('%H:%M') == '08:00'
            assert datetime.fromtimestamp(coaster['departure'], ZoneInfo('America/Los_Angeles')).strftime('%H:%M') == '05:00'
            overnight = next(s for s in regional['services'] if s['number'] == '668' and
                             regional['transit_patterns'][s['pattern']]['operator'] == 'Caltrain')
            native = datetime.fromtimestamp(overnight['departure'], ZoneInfo('America/Los_Angeles'))
            assert native.strftime('%Y-%m-%d %H:%M') == '2026-10-12 00:05'
    assert max(seen.values()) == 1


def test_optional_reference_changes_only_invalidate_selected_layers(monkeypatch, tmp_path):
    base, regional = tmp_path / 'intercity.gz', tmp_path / 'regional.gz'
    base.write_bytes(b'intercity')
    regional.write_bytes(b'regional')
    monkeypatch.setattr(replay, 'US_RAIL_PATH', base)
    monkeypatch.setattr(replay, 'US_COMMUTER_PATH', regional)
    before = descriptor('2026-10-12', 'us_rail')
    selected = descriptor('2026-10-12', 'us_rail', ['commuter_rail'])
    regional.write_bytes(b'changed regional snapshot')
    assert descriptor('2026-10-12', 'us_rail') == before
    assert descriptor('2026-10-12', 'us_rail', ['commuter_rail'])['revision'] != selected['revision']
    regional.unlink()
    assert descriptor('2026-10-12', 'us_rail') == before
