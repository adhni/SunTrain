import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.compact_transit import save_reference
from scripts.prepare_germany_regional import mode_day
from scripts.prepare_india_replay import selected_route, selected_regional_route, describe_regional

AGENCIES = {'1': {'agency_name': 'Indian Railways'}}
DAY = '2026-08-31'


def route(number, name):
    return {'agency_id':'1', 'route_type':'2', 'route_id':number,
            'route_short_name':number, 'route_long_name':name}


@pytest.mark.parametrize('number,name,mode,category', [
    ('30111','BLN-BP LOCAL','commuter_rail','Suburban / local'),
    ('40001','MSB-TBM EMU LOCAL','commuter_rail','Suburban / local'),
    ('93001','VR-DRD LOCAL','commuter_rail','Suburban / local'),
    ('61001','BOR-BSR MEMU','regional_rail','MEMU'),
    ('70101','MAO-KAWR MEMU','regional_rail','MEMU'),
    ('71404','DD-PUNE DEMU','regional_rail','DEMU / DMU'),
    ('51101','JM-KMN PAS','regional_rail','Regional passenger'),
    ('50107','SWV MADGAON EXP','regional_rail','Regional passenger'),
    ('03201','MEMU SPECIAL','regional_rail','MEMU'),
    ('15753','SIFHUNG PASSENGER','regional_rail','Regional passenger'),
])
def test_explicit_regional_and_suburban_scope_does_not_duplicate_intercity(number,name,mode,category):
    r = route(number,name)
    assert selected_regional_route(r,AGENCIES) and not selected_route(r,AGENCIES)
    p = describe_regional(r,{})
    assert (p['mode'],p['category'],p['route_short_name'],p['service_name']) == (mode,category,number,name)


@pytest.mark.parametrize('number,name', [
    ('20101','SC VANDE BHARAT'), ('82501','IRCTC TEJAS EXP'),
    ('00487','PARCEL EXPRESS'), ('00629','YPR MEMU PCET'),
    ('50123','GOODS'), ('60123','RAPID CARGO'), ('70123','JPP RCS'),
    ('00103','MAO-VLNK FTR SPL'), ('not-a-number','MEMU'),
])
def test_nonpassenger_unknown_and_out_of_scope_services_stay_out(number,name):
    assert not selected_regional_route(route(number,name),AGENCIES)


def fixture_reference(mode):
    return {'metadata': {'source':'test','source_url':'https://example.com', 'license':'test',
            'attribution':'test','sources':[], 'start_date':DAY,'end_date':DAY},
            'stations':[{'name':'Alpha','lon':77,'lat':20,'mode':'train'},
                        {'name':'Bravo','lon':77.1,'lat':20,'mode':'train'}],
            'patterns':{'p':{'mode':mode,'operator':'Indian Railways','route_id':mode,'line':mode,
                'origin':'Alpha','destination':'Bravo','direction':'Not specified','color':'#3079B8',
                'stops':[[0,0,60],[1,100000,100000]],'legs':['l']}},
            'paths':{'l':{'coordinates':[[77,20],[77.1,20]],'distances':[0,10000],'quality':'track'}},
            'days':{DAY:[['p','same-source-id',21600]]}}


@pytest.fixture
def layers(monkeypatch,tmp_path):
    monkeypatch.setitem(CITIES,'india', {'name':'India','timezone':'Asia/Kolkata','bounds':[[68,8],[98,36]],
        'passenger_data':False,'start_date':DAY,'end_date':DAY,'default_modes':['train'],
        'modes':[('Intercity','train'),('Regional','regional_rail'),('Suburban','commuter_rail')]})
    base = tmp_path/'base.json.gz'
    monkeypatch.setenv('SUNTRAIN_INDIA_REFERENCE',str(base))
    save_reference(fixture_reference('train'),base)
    for mode in ['regional_rail','commuter_rail']:
        r = fixture_reference(mode)
        save_reference(r,tmp_path/(mode+'-week.json.gz'))
        save_reference(mode_day(r,DAY,mode,prefix='in-'+mode+'-'),tmp_path/mode/(DAY+'.json.gz'))
    replay.clear_replay_cache()
    yield tmp_path
    replay.clear_replay_cache()


def test_optional_layers_are_not_read_by_default_and_can_open_without_base(layers,monkeypatch):
    monkeypatch.setenv('SUNTRAIN_INDIA_REGIONAL_RAIL_REFERENCE',str(layers/'absent'))
    monkeypatch.setenv('SUNTRAIN_INDIA_COMMUTER_RAIL_REFERENCE',str(layers/'absent'))
    assert descriptor(DAY,'india')['modes'] == ['train']
    assert len(replay.get_replay_day(DAY,'india')['services']) == 1
    monkeypatch.setenv('SUNTRAIN_INDIA_REFERENCE',str(layers/'missing-base.json.gz'))
    monkeypatch.delenv('SUNTRAIN_INDIA_REGIONAL_RAIL_REFERENCE')
    replay.clear_replay_cache()
    assert descriptor(DAY,'india',['regional_rail'])['modes'] == ['regional_rail']
    r = replay.get_replay_day(DAY,'india',modes=['regional_rail'])
    assert len(r['services']) == 1 and r['services'][0]['mode'] == 'regional_rail'
    assert r['end'] == r['services'][0]['departure']+100000


def test_combining_layers_keeps_original_numbers_unique_ids_and_station_maps(layers):
    original = replay.get_replay_day(DAY,'india')
    topology = dict(original['transit_stop_patterns'])
    r = replay.get_replay_day(DAY,'india',modes=['train','regional_rail','commuter_rail'])
    assert len(r['services']) == len({s['id'] for s in r['services']}) == 3
    assert all(s['number'] == 'same-source-id' for s in r['services'])
    for s in r['services']:
        p = r['transit_patterns'][s['pattern']]
        stations = r['transit_stop_patterns'][p['stop_pattern']]['stations']
        assert r['stations'][stations[0]]['name'] == p['origin']
        assert r['stations'][stations[-1]]['name'] == p['destination']
        assert 'stops' not in p
    assert original['transit_stop_patterns'] == topology and len(original['services']) == 1
