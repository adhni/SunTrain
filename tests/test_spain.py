from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_spain_replay import SOURCES, GEOMETRY, GEOMETRY_SHA256, selected_route, domestic_sequence


def test_train_scope_rejects_mislabelled_buses_and_other_modes():
    agencies={'1071':{'agency_name':'RENFE OPERADORA'}}
    route={'agency_id':'1071','route_type':'2','route_short_name':'AVE'}
    assert selected_route('national',route,agencies)
    assert not selected_route('national',{**route,'route_short_name':'Bus'},agencies)
    for mode in ['0','1','3','7','700']:
        assert not selected_route('national',{**route,'route_type':mode},agencies)
    assert not selected_route('national',route,{'1071':{'agency_name':'changed'}})
    fgc={'':{'agency_name':'FGC'}}
    assert selected_route('fgc',{'route_type':'2','route_short_name':'S1'},fgc)
    assert not selected_route('fgc',{'route_type':'1','route_short_name':'L6'},fgc)
    assert not selected_route('fgc',{'route_type':'7','route_short_name':'MM'},fgc)


def test_foreign_clipping_keeps_spanish_stations_with_similar_codes_and_intermediate_calls():
    calls=[{'stop_id':s,'arrival_time':f'{20+i}:00:00'} for i,s in enumerate(
        ['94346','94002','94021','94004','79316'])]
    assert domestic_sequence(calls)==calls[1:4]
    assert domestic_sequence([{'stop_id':'94346'},{'stop_id':'17000'}])==[]
    assert domestic_sequence([])==[]


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.SPAIN_PATH,'rt') as stream:return json.load(stream)


def test_historical_sources_nationwide_products_and_compact_week(reference):
    meta=reference['metadata']
    assert file_hash(GEOMETRY)==GEOMETRY_SHA256
    assert {s['sha256'] for s in meta['sources']}=={s['sha256'] for s in SOURCES.values()}
    assert meta['start_date']=='2024-06-24' and meta['end_date']=='2024-06-30'
    assert meta['license']==meta['geometry_license']=='CC BY 4.0'
    assert 'Obra derivada de' in meta['attribution'] and 'FGC' in meta['attribution']
    assert meta['schedule_encoding']=='shared-stops-flat-times-v1'
    assert not meta['omitted_trips']
    patterns=list(reference['patterns'].values())
    assert all(p['mode']=='train' and 'stops' not in p for p in patterns)
    assert {p['operator'] for p in patterns}=={'Renfe','Renfe Cercanías / Rodalies','FGC'}
    assert {'AVE','AVLO','ALVIA','EUROMED','MD','AVANT','REGIONAL','C1','R1','S1','RL2'} <= {p['category'] for p in patterns}
    names={s['name'].lower() for s in reference['stations']}
    for fragment in ['madrid','barcelona','valencia','sevilla','málaga','bilbao','santander','zaragoza','coru','murcia']:
        assert any(fragment in n for n in names),fragment


def test_business_windows_keep_overnight_calls_and_ids_unique(reference):
    occurrences=[];overnight=[]
    assert len(reference['days'])==7
    for day,rows in reference['days'].items():
        assert len(rows)>4000
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Madrid')).timestamp()
        for p,t,o in rows:
            times=reference['patterns'][p]['times']
            assert 10800<=o+times[1]<97200
            occurrences.append((t,midnight+o))
            if o<86400<o+times[-1]:overnight.append(t)
    assert len(occurrences)==len(set(occurrences)) and overnight
    for path in reference['paths'].values():
        if path['quality']=='approximate':assert path['coordinates']==path['distances']==[]
        else:assert path['quality'] in {'shape','track'} and len(path['coordinates'])>=2


def test_core_high_speed_and_regional_products_have_detailed_track_paths(reference):
    for category in ['AVE','ALVIA','MD','C1','R1','S1']:
        paths=[reference['paths'][leg] for p in reference['patterns'].values() if p['category']==category
               for leg in reference['stop_patterns'][p['stop_pattern']]['legs']]
        assert any(len(p['coordinates'])>10 for p in paths),category


def test_existing_loader_filters_and_overview_coverage_are_independent_of_melbourne(monkeypatch):
    monkeypatch.setattr(replay.data,'get_metadata',lambda:pytest.fail('Spain queried Melbourne warehouse'))
    day=replay.get_replay_day('2024-06-24','spain')
    assert day['timezone']=='Europe/Madrid' and len(day['services'])==5538
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert any(s['number'].isdigit() for s in day['services'])
    assert not city_settings('spain')['passenger_data']
    assert descriptor('2024-06-24','spain')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2024-06-24','spain',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-01','spain')
