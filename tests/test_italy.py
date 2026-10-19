from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_italy_replay import AGENCY,PRODUCTS,SOURCES,selected_route,domestic_sequence,train_number,remove_duplicate_occurrences,single_train_itinerary
from scripts.prepare_italy_geometry import passenger_track,speed


def test_scope_rejects_mislabelled_freccialink_and_replacement_buses():
    agencies={AGENCY:{'agency_name':'TRENITALIA'}}
    route={'agency_id':AGENCY,'route_type':'2','route_short_name':'FR','route_id':'IT::Line:railTRENITALIA:680083'}
    assert selected_route('trenitalia',route,agencies)
    for change in [{'route_short_name':'FL'},{'route_short_name':'BUS'},{'route_type':'3'},{'route_type':'1'},{'agency_id':'other'}]:
        assert not selected_route('trenitalia',{**route,**change},agencies)
    tn={'1':{'agency_name':'Trenord'}}
    assert selected_route('trenord',{'agency_id':'1','route_type':'2','route_id':'S13'},tn)
    assert not selected_route('trenord',{'agency_id':'1','route_type':'3','route_id':'RE_4'},tn)
    assert not selected_route('trenord',{'agency_id':'1','route_type':'3','route_id':'TN_Bus'},tn)
    italo={'IT::Operator:1':{'agency_name':'Italo - Nuovo Trasporto Viaggiatori'}}
    av={'agency_id':'IT::Operator:1','route_type':'2','route_short_name':'Italo','route_id':'IT::Line:RAIL-AAV-MC--22a08b'}
    assert selected_route('italo',av,italo)
    assert not selected_route('italo',{**av,'route_type':'3'},italo)
    assert not selected_route('italo',{**av,'route_id':'IT::Line:BUS-ABC'},italo)


def test_country_clipping_preserves_intermediate_foreign_calls_and_actual_train_numbers():
    calls=[{'stop_id':s} for s in ['fr','it1','ch','it2','at']]
    stops={s:{'stop_code':code} for s,code in [('fr','87'),('it1','830001'),('ch','85'),('it2','830002'),('at','81')]}
    assert domestic_sequence('trenitalia',calls,stops)==calls[1:4]
    tn=[{'stop_id':s} for s in ['S05214','S01110','S05400','S01113','S19919']]
    assert domestic_sequence('trenord',tn,{})==tn[1:4]
    assert domestic_sequence('trenitalia',calls[:2],stops)==[]
    assert train_number('S13 - 24311')=='24311'
    assert train_number('02800')=='2800'
    assert single_train_itinerary('IT::ServiceJourney:8953-1-1-1')
    assert not single_train_itinerary('IT::ServiceJourney:8953-8974-1-1-1_rail2')
    assert not single_train_itinerary('IT::ServiceJourney:1021-9920-1-1-1_rail')


def test_duplicate_journeys_require_same_number_clocks_and_endpoints():
    r={'metadata':{},'stations':[{'name':'MILANO CENTRALE','lon':9.2,'lat':45.5},{'name':'Bologna Centrale','lon':11.3,'lat':44.5}],
       'patterns':{'a':{'mode':'train','operator':'Trenitalia','stop_pattern':'s','times':[0,0,3600,3600]},
                   'b':{'mode':'train','operator':'Trenord','stop_pattern':'s','times':[0,0,3600,3600]}},
       'stop_patterns':{'s':{'stations':[0,1]}},'train_numbers':{'it-trenitalia:a':'0123','it-trenord:b':'S13 - 123','it-trenord:c':'S13 - 124'},
       'days':{'2026-10-05':[['b','it-trenord:b',0],['a','it-trenitalia:a',0],['b','it-trenord:c',0],['b','it-trenord:b',100]]}}
    remove_duplicate_occurrences(r)
    assert len(r['days']['2026-10-05'])==3
    assert r['metadata']['deduplicated_occurrences']=={'Trenord':1}


def test_mapping_scope_and_high_speed_weights():
    assert passenger_track({'railway':'rail','highspeed':'yes'})
    assert passenger_track({'railway':'narrow_gauge'})
    for tags in [{'railway':'tram'},{'railway':'subway'},{'railway':'rail','service':'yard'},{'railway':'rail','usage':'industrial'}]:
        assert not passenger_track(tags)
    assert speed({'maxspeed':'300'})==300
    assert speed({'highspeed':'yes'})>speed({})


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.ITALY_PATH,'rt') as f:return json.load(f)


def test_historical_dates_nationwide_coverage_and_optional_operators(reference):
    meta=reference['metadata']
    assert meta['start_date']=='2026-10-05' and meta['end_date']=='2026-10-11' and meta['timezone']=='Europe/Rome'
    assert {s['sha256'] for s in meta['sources']}=={s['sha256'] for s in SOURCES.values()}
    assert meta['license']=='CC BY 4.0' and meta['geometry_license']=='ODbL 1.0'
    assert meta['schedule_encoding']=='shared-stops-flat-times-v1'
    patterns=list(reference['patterns'].values())
    assert all(p['mode']=='train' and 'stops' not in p for p in patterns)
    assert {p['operator'] for p in patterns}=={'Trenitalia','Trenord','Italo'}
    assert {'FR','FA','FB','IC','ICN','REG','RV'}<={p['category'] for p in patterns}
    names={s['name'].upper() for s in reference['stations']}
    for place in ['ROMA','MILANO','TORINO','VENEZIA','NAPOLI','BARI','REGGIO','PALERMO','CATANIA','CAGLIARI']:
        assert any(place in n for n in names),place


def test_windows_overnight_and_no_straight_fallback(reference):
    occurrences=[];overnight=False
    for day,rows in reference['days'].items():
        assert len(rows)>4000
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Rome')).timestamp()
        for p,t,o in rows:
            times=reference['patterns'][p]['times']
            assert 10800<=o+times[1]<97200
            occurrences.append((t,midnight+o));overnight|=o+times[-1]>86400
    assert len(occurrences)==len(set(occurrences)) and overnight
    assert all(single_train_itinerary(t) for rows in reference['days'].values() for p,t,o in rows if reference['patterns'][p]['operator']=='Italo')
    for p in reference['paths'].values():
        if p['quality']=='approximate':assert p['coordinates']==p['distances']==[]
        else:assert p['quality']=='track' and len(p['coordinates'])>=2


def test_loader_validates_transport_and_period():
    day=replay.get_replay_day('2026-10-05','italy')
    assert day['services'] and day['timezone']=='Europe/Rome'
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert descriptor('2026-10-05','italy')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2026-10-05','italy',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-01','italy')
