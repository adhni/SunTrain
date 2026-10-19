from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_portugal_replay import SOURCES,GEOMETRY,GEOMETRY_SHA256,selected_route,domestic_sequence


def test_scope_rejects_buses_metros_and_unknown_operators():
    agencies={'1094_CP':{'agency_name':'CP - Comboios de Portugal'}}
    route={'agency_id':'1094_CP','route_type':'2','route_short_name':'AP'}
    assert selected_route('cp',route,agencies)
    assert selected_route('cp',{**route,'route_type':'109','route_short_name':'Linha de Sintra'},agencies)
    for mode in ['0','1','3','700']:
        assert not selected_route('cp',{**route,'route_type':mode},agencies)
    assert not selected_route('cp',{**route,'route_short_name':'Bus'},agencies)
    assert not selected_route('cp',route,{'1094_CP':{'agency_name':'Other'}})
    assert selected_route('fertagus',{'agency_id':'15','route_type':'2'},{'15':{'agency_name':'Fertagus'}})


def test_cross_border_clipping_keeps_intermediate_calls():
    calls=[{'stop_id':s} for s in ['71_a','94_a','71_b','94_b','71_c']]
    assert domestic_sequence(calls)==calls[1:4]
    assert domestic_sequence(calls[:2])==[]
    assert domestic_sequence([])==[]


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.PORTUGAL_PATH,'rt') as f:return json.load(f)


def test_sources_licences_and_nationwide_train_coverage(reference):
    meta=reference['metadata']
    assert file_hash(GEOMETRY)==GEOMETRY_SHA256
    assert {s['sha256'] for s in meta['sources']}=={s['sha256'] for s in SOURCES.values()}
    assert meta['start_date']=='2026-06-01' and meta['end_date']=='2026-06-07'
    assert meta['timezone']=='Europe/Lisbon' and meta['schedule_encoding']=='shared-stops-flat-times-v1'
    assert 'No licence / no contract' in meta['license']
    assert meta['geometry_license']=='CC BY 4.0' and 'Infraestruturas' in meta['attribution']
    assert 'Fertagus' in meta['attribution'] and not meta['omitted_trips']
    patterns=list(reference['patterns'].values())
    assert all(p['mode'] in {'train','subway'} and 'stops' not in p for p in patterns)
    assert {p['operator'] for p in patterns}=={'CP','Fertagus','Lisbon Metro'}
    assert {'Alfa Pendular','Intercidades','InterRegional','Regional','Linha de Sintra','Linha de Cascais','Linha de Braga','Fertagus'} <= {p['category'] for p in patterns}
    names={s['name'].lower() for s in reference['stations']}
    for fragment in ['lisboa','porto','faro','coimbra','braga','guimara','evora','beja','guarda','setúbal']:
        assert any(fragment in n for n in names),fragment


def test_unique_business_days_overnight_trains_and_real_geometry(reference):
    occurrences=[];overnight=[];good=total=0;fertagus_good=0
    for day,rows in reference['days'].items():
        assert len(rows)>900
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Lisbon')).timestamp()
        for key,trip,offset in rows:
            pattern=reference['patterns'][key];times=pattern['times']
            assert 10800<=offset+times[1]<97200
            occurrences.append((trip,midnight+offset))
            if offset<86400<offset+times[-1]:overnight.append(trip)
            for leg in reference['stop_patterns'][pattern['stop_pattern']]['legs']:
                path=reference['paths'][leg];total+=1
                if path['quality']=='approximate':assert path['coordinates']==path['distances']==[]
                else:
                    good+=1
                    assert len(path['coordinates'])>=2
                    if pattern['operator']=='Fertagus':fertagus_good+=1
    assert len(occurrences)==len(set(occurrences)) and overnight
    assert good/total>.97 and fertagus_good>11000
    for category in ['Alfa Pendular','Intercidades','Regional','Fertagus']:
        paths=[reference['paths'][leg] for p in reference['patterns'].values() if p['category']==category
            for leg in reference['stop_patterns'][p['stop_pattern']]['legs']]
        assert any(len(p['coordinates'])>30 for p in paths),category


def test_city_loader_filters_and_date_validation(monkeypatch):
    monkeypatch.setattr(replay.data,'get_metadata',lambda:pytest.fail('Portugal queried Melbourne warehouse'))
    day=replay.get_replay_day('2026-06-01','portugal',modes=['train'])
    assert len(day['services'])==1517 and day['timezone']=='Europe/Lisbon'
    assert {day['transit_patterns'][s['pattern']]['operator'] for s in day['services']}=={'CP','Fertagus'}
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert not city_settings('portugal')['passenger_data']
    assert city_settings('portugal')['start_date']==city_settings('netherlands')['start_date']
    assert descriptor('2026-06-01','portugal')['modes']==['subway','train']
    with pytest.raises(ValueError):descriptor('2026-06-01','portugal',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-08','portugal')
