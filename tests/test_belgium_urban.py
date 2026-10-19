from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from scripts.prepare_belgium_urban import SOURCES, OPERATORS, describe_route, merge_references, selected_route


def test_merging_identical_local_ids_keeps_independent_schedules_and_stations():
    metadata={'sources':[],'attribution':'fixture','omitted_trips':{},'unresolved_geometry_patterns':{},
              'unresolved_geometry_trips':{},'geometry_source':'GTFS','geometry_source_url':'https://example.test',
              'geometry_license':'CC BY 4.0','geometry_license_url':'https://creativecommons.org/licenses/by/4.0/'}
    r={'metadata':metadata,'stations':[{'name':'A'},{'name':'B'}],
       'patterns':{'same':{'route_id':'1','stop_pattern':'stops','mode':'tram','times':[0,0,60,60]}},
       'stop_patterns':{'stops':{'stations':[0,1],'legs':['path']}},
       'paths':{'path':{'coordinates':[[1,2],[2,3]],'quality':'shape'}},
       'days':{'2026-06-01':[['same','trip',10800]]}}
    merged=merge_references([('first',r),('second',r)])
    assert len(merged['days']['2026-06-01'])==2
    assert {trip for _,trip,_ in merged['days']['2026-06-01']}=={'first:trip','second:trip'}
    assert merged['stop_patterns']['first:stops']['stations']==[0,1]
    assert merged['stop_patterns']['second:stops']['stations']==[2,3]
    assert merged['stop_patterns']['second:stops']['legs']==['second:path']
    assert r['stop_patterns']['stops']['stations']==[0,1]
    with pytest.raises(ValueError,match='Duplicate'):
        merge_references([('same',r),('same',r)])


def test_selected_routes_reject_all_bus_and_replacement_variants():
    for feed,operators in OPERATORS.items():
        agencies={k:{'agency_name':v} for k,v in operators.items()}
        agency=next(iter(operators))
        route={'agency_id':agency,'route_short_name':'1','route_type':'3'}
        for mode in ['3','700','4','1400']:
            assert not selected_route(feed,{**route,'route_type':mode},agencies)
        assert not selected_route(feed,route,{agency:{'agency_name':'Unknown'}})
    stib={'STIB/MIVB':{'agency_name':'STIB'}}
    assert selected_route('stib-mivb',{'agency_id':'STIB/MIVB','route_type':'1','route_short_name':'2'},stib)
    tec={'C':{'agency_name':'TEC Charleroi'},'L':{'agency_name':'TEC Liège - Verviers'}}
    assert selected_route('tec',{'agency_id':'C','route_type':'1','route_short_name':'M4'},tec)
    assert selected_route('tec',{'agency_id':'L','route_type':'0','route_short_name':'T1'},tec)
    assert not selected_route('tec',{'agency_id':'C','route_type':'3','route_short_name':'M1'},tec)


def test_source_line_colours_and_city_labels_are_preserved():
    r={'agency_id':'STIB/MIVB','route_type':'1','route_id':'3','route_short_name':'1','route_color':'B5378C'}
    assert describe_route('stib-mivb',r,{'direction_id':'0'})['color']=='B5378C'
    assert describe_route('stib-mivb',r,{})['line']=='Brussels Metro 1'
    for route,city in [('10010','Antwerp'),('20070','Ghent'),('55000','Coastal')]:
        p=describe_route('delijn',{**r,'route_id':route,'route_type':'0','route_color':'E40521'},{})
        assert p['line'].startswith(city+' Tram') and p['color']=='E40521'


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.BELGIUM_PATH,'rt') as stream:return json.load(stream)


def test_all_requested_urban_networks_and_four_pinned_sources_are_present(reference):
    assert {s['sha256'] for s in reference['metadata']['sources']} >= {s['sha256'] for s in SOURCES.values()}
    patterns=reference['patterns'].values();lines={p['line'] for p in patterns}
    for n in ['1','2','5','6']:assert 'Brussels Metro '+n in lines
    for n in ['M2','M3','M4']:assert 'Charleroi '+n in lines
    assert 'Liège Tram T1' in lines
    for city in ['Brussels','Antwerp','Ghent','Coastal']:
        assert any(line.startswith(city+' Tram ') for line in lines)
    assert {p['mode'] for p in patterns}=={'train','subway','tram'}
    assert not reference['metadata']['omitted_trips']
    assert all('stops' not in p for p in patterns)
    for p in patterns:
        if p['mode']!='train':
            assert all(reference['paths'][k]['quality'] in {'shape','approximate'}
                       for k in reference['stop_patterns'][p['stop_pattern']]['legs'])


def test_namespaces_keep_occurrences_unique_across_feeds_and_days(reference):
    occurrences=[]
    for day,rows in reference['days'].items():
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Brussels')).timestamp()
        for key,t,offset in rows:
            assert t.startswith(('be-nmbs:','be-stib-mivb:','be-delijn:','be-tec:'))
            assert 10800<=offset<97200
            occurrences.append((t,midnight+offset))
    assert len(occurrences)==len(set(occurrences))


def test_brussels_metro_ring_retains_its_full_loop(reference):
    lengths=[sum(reference['paths'][leg]['distances'][-1]
                 for leg in reference['stop_patterns'][p['stop_pattern']]['legs'])
             for p in reference['patterns'].values() if p['line']=='Brussels Metro 2']
    assert lengths and 9000<max(lengths)<12000


def test_default_is_trains_and_metro_with_trams_requested_separately():
    default=replay.get_replay_day('2026-06-01','belgium')
    assert {s['mode'] for s in default['services']}=={'train','subway'}
    trams=replay.get_replay_day('2026-06-01','belgium',modes=('tram',))
    assert trams['services'] and {s['mode'] for s in trams['services']}=={'tram'}
    assert len(default['services'])>3786
    all_modes=replay.get_replay_day('2026-06-01','belgium',modes=('train','subway','tram'))
    assert len(all_modes['services'])==len(default['services'])+len(trams['services'])
    assert len({s['id'] for s in all_modes['services']})==len(all_modes['services'])
