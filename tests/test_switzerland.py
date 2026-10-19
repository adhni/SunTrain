from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_switzerland_geometry import compact_ways, passenger_track
from scripts.prepare_switzerland_replay import (
    GEOMETRY, GEOMETRY_SHA256, OPERATORS, RAIL_TYPES, SOURCE,
    domestic_sequence, selected_route,
)
from schedule_helpers import expanded_pattern


def test_scope_accepts_swiss_rail_categories_and_excludes_other_modes_and_unknown_agencies():
    agencies = {key: {'agency_name': name} for key,name in OPERATORS.items()}
    route = {'agency_id':'11','route_type':'102','route_desc':'IC'}
    assert selected_route(route,agencies)
    for mode,categories in RAIL_TYPES.items():
        for category in categories:
            assert selected_route({**route,'route_type':mode,'route_desc':category},agencies)
    for mode,category in [('700','EV'),('401','M'),('900','T'),('1400','FUN'),('1300','GB'),('1000','BAT'),('104','AT')]:
        assert not selected_route({**route,'route_type':mode,'route_desc':category},agencies)
    assert not selected_route(route,{'11':{'agency_name':'Unexpected operator'}})
    assert not selected_route({**route,'agency_id':'7258'},agencies)
    assert not selected_route({**route,'route_desc':'BUS'},agencies)


def test_domestic_clipping_keeps_border_detours_and_original_overnight_times():
    sequence = [{'stop_id':s,'departure_time':f'{i+22}:00:00'}
                for i,s in enumerate(['8000001','8503000:0:1','8010000','8507000','8700001'])]
    assert domestic_sequence(sequence) == sequence[1:4]
    assert domestic_sequence(sequence[:2]) == []
    assert domestic_sequence([]) == []


def test_geometry_keeps_native_junctions_without_connecting_coincident_unrelated_tracks():
    nodes = {'a':[8,47],'j':[8.01,47],'b':[8.02,47],'c':[8.01,47.02],
             'x':[8.01,47],'y':[8.01,46.98]}
    ways = {'1':{'nodes':['a','j','b']},'2':{'nodes':['j','c']},'3':{'nodes':['x','y']}}
    packed=compact_ways(ways,nodes)
    graph=FranceRailGraph(packed)
    assert graph.leg(nodes['a'],nodes['c'])
    assert graph.leg(nodes['a'],nodes['y']) is None
    assert any('j' in way['node_ids'] for way in packed)
    assert passenger_track({'railway':'narrow_gauge'})
    assert passenger_track({'railway':'rail','rack':'abtrich'})
    for mode in ['funicular','tram','subway','abandoned','construction']:
        assert not passenger_track({'railway':mode})
    assert not passenger_track({'railway':'rail','service':'yard'})


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.SWITZERLAND_PATH,'rt') as stream:
        return json.load(stream)


def test_pinned_sources_compact_schedules_and_nationwide_operators(reference):
    assert file_hash(GEOMETRY)==GEOMETRY_SHA256
    metadata=reference['metadata']
    assert metadata['sources'][0]['sha256']==SOURCE['sha256']
    assert metadata['sources'][0]['feed_version']=='20260530'
    assert metadata['schedule_encoding']=='shared-stops-flat-times-v1'
    assert not metadata['omitted_trips']
    assert all('stops' not in p for p in reference['patterns'].values())
    assert {p['mode'] for p in reference['patterns'].values()}=={'train'}
    operators={p['operator'] for p in reference['patterns'].values()}
    assert {OPERATORS[k] for k in ['11','33','82','72','48','93','86','65']} <= operators
    assert {'IC','IR','RE','R','S','CC','NJ','PE'} <= {p['category'] for p in reference['patterns'].values()}
    names={s['name'] for s in reference['stations']}
    assert {'Zürich HB','Bern','Basel SBB','Genève','Lausanne','Luzern','Lugano','St. Moritz','Zermatt'} <= names
    assert not city_settings('switzerland')['passenger_data']


def test_overnight_occurrences_have_only_one_business_day_and_gaps_are_empty(reference):
    assert len(reference['days'])==7
    occurrences=[];overnight=[]
    for day,rows in reference['days'].items():
        assert len(rows)>5000
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Zurich')).timestamp()
        for key,trip,offset in rows:
            assert 10800<=offset<97200
            occurrences.append((trip,midnight+offset))
            if offset<86400<offset+reference['patterns'][key]['times'][-1]:overnight.append(trip)
    assert len(occurrences)==len(set(occurrences))
    assert overnight
    for p in reference['paths'].values():
        if p['quality']=='approximate':assert p['coordinates']==p['distances']==[]
        else:assert p['quality']=='track' and len(p['coordinates'])>=2


@pytest.mark.parametrize('fragment', ['Rhätische','Gotthard','Südostbahn','Jungfrau','Gornergrat'])
def test_regional_and_alpine_operators_have_mapped_train_legs(reference,fragment):
    paths=[reference['paths'][key] for p in reference['patterns'].values() if fragment in p['operator']
           for key in reference['stop_patterns'][p['stop_pattern']]['legs']]
    assert paths and any(len(p['coordinates'])>10 for p in paths)


def test_runtime_reuses_selected_day_loader_with_train_numbers_and_correct_dates(monkeypatch):
    monkeypatch.setattr(replay.data,'get_metadata',lambda:pytest.fail('Swiss replay queried Melbourne warehouse'))
    day=replay.get_replay_day('2026-06-01','switzerland')
    assert day['timezone']=='Europe/Zurich' and day['services']
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert any(s['number'].isdigit() for s in day['services'])
    assert city_settings('switzerland')['start_date']==city_settings('france')['start_date']
    assert descriptor('2026-06-01','switzerland')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2026-06-01','switzerland',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-08','switzerland')
