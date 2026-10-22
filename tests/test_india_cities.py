import gzip
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from dashboard import replay
from scripts.prepare_india_cities import OPERATORS, describe, merge_chennai, select_route
from scripts.prepare_rail_replay import TimetableArchive


@pytest.mark.parametrize('feed', ['kochi', 'delhi', 'cmrl', 'srr'])
def test_operator_scope_keeps_rail_and_excludes_buses(feed):
    agencies = {'a': {'agency_name': OPERATORS[feed]}}
    row = {'route_type': '1', 'agency_id': 'a'}
    assert select_route(feed, row, agencies)
    assert not select_route(feed, {**row, 'route_type': '3'}, agencies)
    assert not select_route(feed, row, {'a': {'agency_name': 'Another operator'}})
    assert select_route(feed, {'route_type': '1'}, agencies)


def test_suburban_source_type_does_not_turn_into_metro_and_native_colours_survive():
    route = {'route_id': '40001', 'route_short_name': '40001', 'route_long_name': 'MSB-TBM', 'route_color': '000092'}
    assert describe('srr', route, {})['mode'] == 'train'
    assert describe('cmrl', route, {})['mode'] == 'subway'
    assert describe('cmrl', route, {})['color'] == '000092'


def test_official_cumta_outer_archive_reads_one_inner_timetable(tmp_path):
    inner = io.BytesIO()
    with ZipFile(inner, 'w') as z:
        z.writestr('agency.txt', 'agency_id,agency_name\nSR,Southern Railway\n')
    outer = tmp_path/'official.zip'
    with ZipFile(outer, 'w') as z:
        z.writestr('Southern Railways/feed.zip', inner.getvalue())
        z.writestr('Southern Railways/corridor.geojson', '{}')
    with TimetableArchive(outer) as z:
        assert z.namelist() == ['agency.txt']
        assert z.open('agency.txt').read().startswith(b'agency_id,agency_name')


def test_kochi_public_reference_owns_departures_once_and_keeps_sunday_timetable():
    path = Path(__file__).resolve().parents[1]/'data/reference/kochi/2025-12-15.json.gz'
    with gzip.open(path, 'rt') as f:
        r = json.load(f)
    assert {day:len(rows) for day,rows in r['days'].items()} == {
        **{f'2025-12-{d}':255 for d in range(15,21)}, '2025-12-21':195}
    for rows in r['days'].values():
        assert len(rows) == len({(trip,offset) for _,trip,offset in rows})
        for key,trip,offset in rows:
            p = r['patterns'][key]
            assert 'stops' not in p and 10800 <= offset+p['times'][1] < 97200
    assert all(p['coordinates'] and p['quality'] == 'shape' for p in r['paths'].values())
    assert r['metadata']['attribution'] == 'Contains data provided by Kochi Metro Rail Limited'
    day = replay.get_replay_day('2025-12-15', 'kochi')
    assert len(day['services']) == 255 and day['timezone'] == 'Asia/Kolkata'


def test_comparison_maps_weekdays_preserves_offsets_and_does_not_invent_sunday():
    def reference(day, rows):
        return {'metadata': {'start_date':day, 'end_date':day, 'sources':[], 'attribution':'test',
                'geometry_source':'test','geometry_source_url':'https://example.com',
                'geometry_license':'test','geometry_license_url':'https://example.com',
                'omitted_trips':{},'unresolved_geometry_patterns':{},'unresolved_geometry_trips':{},
                'native_anchor_patterns':0}, 'stations': [], 'patterns': {},
                'paths': {}, 'stop_patterns': {}, 'days': {day:rows}}
    suburban = reference('2026-10-12', [])
    metro = reference('2021-12-13', [])
    suburban['days']['2026-10-18'] = []
    metro['days']['2021-12-19'] = []
    metro['patterns']['p'] = {'mode':'subway','route_id':'Blue','stop_pattern':'s','times':[0,60]}
    metro['stop_patterns']['s'] = {'stations':[], 'legs':[]}
    metro['days']['2021-12-13'] = [['p','source-trip',21600]]
    result = merge_chennai(suburban, metro)
    assert result['metadata']['source_date_mappings'] == [
        {'network':'Chennai Metro','display_date':'2026-10-12','source_date':'2021-12-13'},
        {'network':'Chennai Metro','display_date':'2026-10-18','source_date':'2021-12-19'}]
    assert result['days']['2026-10-12'] == [['cmrl-2021:p','cmrl-2021:source-trip',21600]]
    assert result['days']['2026-10-18'] == []
    assert result['metadata']['start_date'] == '2026-10-12'
    assert 'not an October 2026 metro schedule' in result['metadata']['replay_note']
