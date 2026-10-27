"""South American exact-airport selection, local dates, regional scopes and USD quotes."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights,international_network,replay_http
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_us_flights import put

DAY='2026-11-02';CITY='south_america_flights';CODE='SOUTH_AMERICA'
CFG=country_config(CODE)
AIR={a['code']:a for a in CFG['manifest']['airports']}


def test_top_twenty_and_all_countries_exact_airports_single_date_all_pairs_and_independent_network():
    assert list(AIR)[:10]==['GRU','BOG','SCL','LIM','CGH','GIG','AEP','BSB','MDE','CNF']
    assert len(AIR)==27 and [a['rank'] for a in AIR.values() if a['rank'] is not None]==list(range(1,21))
    assert set(list(AIR)[10:20])=={'VCP','EZE','REC','SSA','CTG','POA','CLO','SDU','FOR','CWB'}
    gateways=CFG['manifest']['country_gateways']
    assert gateways=={'AR':'AEP','BO':'VVI','BR':'GRU','CL':'SCL','CO':'BOG','EC':'UIO','GY':'GEO','PY':'ASU','PE':'LIM','SR':'PBM','UY':'MVD','VE':'CCS'}
    assert all(AIR[a]['country']==c for c,a in gateways.items())
    assert {a['country'] for a in AIR.values()}=={'BR','CO','CL','PE','AR','EC','UY','PY','BO','VE','GY','SR'}
    assert AIR['GRU']['icao']=='SBGR' and AIR['CGH']['icao']=='SBSP'
    assert AIR['MDE']['icao']=='SKRG' and AIR['BOG']['icao']=='SKBO' and AIR['AEP']['icao']=='SABE'
    assert AIR['VCP']['icao']=='SBKP' and AIR['EZE']['icao']=='SAEZ' and AIR['SDU']['icao']=='SBRJ'
    assert AIR['GEO']['icao']=='SYCJ' and AIR['PBM']['icao']=='SMJP'
    assert not {'EOH','SAO','BUE','OGL','ORG','CAY'}&AIR.keys()
    pairs=CFG['manifest']['routes']
    assert set(map(tuple,pairs))=={(a,b) for a in AIR for b in AIR if a!=b}
    queries=list(expected_queries(DAY,pairs,CFG))
    assert len(queries)==702 and {q[0] for q in queries}=={DAY}
    assert sum(AIR[a]['country']==AIR[b]['country'] for a,b in pairs)==146
    assert CFG['currency']=='USD' and CFG['scope']=='regional' and CFG['max_duration']==28800
    assert CITIES[CITY]['name']=='South America · Flights' and CITIES[CITY]['timezone']=='UTC'
    assert CITIES[CITY]['flight_scopes'] and CITIES[CITY]['default_flight_scope']=='both' and CITIES[CITY]['flight_country_filters']
    bounds=CITIES[CITY]['bounds']
    assert all(bounds[0][0]<=a['lon']<=bounds[1][0] and bounds[0][1]<=a['lat']<=bounds[1][1] for a in AIR.values())
    assert CITY not in international_network.CITIES and CODE not in international_network.CORE_COUNTRIES
    assert not international_network.enabled(DAY,CITY)


def test_airport_clocks_including_chilean_summer_time():
    for c in AIR:
        offset=-5 if c in {'BOG','MDE','LIM','CTG','CLO','UIO'} else (-4 if c in {'VVI','CCS','GEO'} else -3)
        assert datetime(2026,11,2,tzinfo=ZoneInfo(CFG['zones'][c])).utcoffset().total_seconds()==offset*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(CFG['zones']['SCL'])).utcoffset().total_seconds()==-4*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(CFG['zones']['GRU'])).utcoffset().total_seconds()==-3*3600


def fixture(cache):
    examples=[('GRU','GIG',[0,30],[1,30],60),('BOG','MDE',[9,0],[10,0],60),
        ('BOG','GRU',[0,30],[8,30],360),('GRU','BOG',[23,30],[3,30],360),
        ('SCL','LIM',[9,0],[10,0],180),('AEP','GRU',[9,0],[11,30],150)]
    pairs=[]
    for i,(a,b,dep,arr,minutes) in enumerate(examples):
        row=segment(a,b,dep,arr,minutes,carrier='LA',number=str(i+1))
        if (a,b)==('GRU','BOG'):row[21]=[2026,11,3]
        fs=parse_results(scripts(row,row),a,b,DAY,CFG['zones'])
        assert len(fs)==1
        prices=cheapest_prices(scripts([offer(row,200),offer(row,150)]),fs,'USD')
        fs[0]['price']={**prices[fs[0]['id']],'captured_at':'2026-10-27T00:00:00Z'}
        put(cache,a,b,fs);pairs.append((a,b))
    return pairs


def test_usd_scopes_overnight_boundaries_http_and_reproducible_preparation(tmp_path,monkeypatch):
    cache=tmp_path/'cache';out=tmp_path/'week.gz';pairs=fixture(cache)
    put(cache,'GRU','CGH',[]);pairs += [('GRU','CGH'),('CNF','BOG')]
    prepare(cache,out,DAY,pairs,CFG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CFG)
    assert first==out.read_bytes()
    raw=load_domestic(out,CODE);metadata=raw['metadata']
    assert metadata['profile']=='south_america' and 'country' not in metadata
    assert metadata['countries']==CFG['manifest']['countries'] and metadata['scope']=='regional'
    assert metadata['coverage']['queries_not_returned']==1 and metadata['coverage']['failed_or_missing_queries']==1
    assert metadata['uncollected_queries']==[[DAY,'CNF','BOG']]
    bypair={(f['origin'],f['destination']):f for f in raw['flights']}
    assert bypair['GRU','GIG']['flight_scope']==bypair['BOG','MDE']['flight_scope']=='domestic'
    assert all(bypair[p]['flight_scope']=='international' for p in pairs[2:6])
    assert metadata['coverage_by_scope']['domestic']['queries_planned']==3
    assert metadata['coverage_by_scope']['international']['queries_planned']==5
    assert all(f['price']['amount_minor']==15000 and f['price']['currency']=='USD' for f in raw['flights'])
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    replay=flights.replay_day(DAY,CITY)
    assert datetime.fromtimestamp(replay['start'],ZoneInfo('UTC')).isoformat()=='2026-11-02T03:00:00+00:00'
    assert len(replay['services'])==6 and replay['end']>int(datetime(2026,11,3,8,30,tzinfo=ZoneInfo('UTC')).timestamp())
    assert all(replay['start']<=s['stops'][0][1] and s['stops'][1][1]<replay['end'] for s in replay['services'])
    assert all(-90<c[0]<-20 for p in replay['paths'].values() for c in p['coordinates'])
    assert flights.reference_paths(DAY,CITY)==[out]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();url=replay_http.descriptor(DAY,CITY)['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['city']==CITY
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404
    with pytest.raises(ValueError,match='approved manifest'):prepare(cache,out,DAY,[('GRU','EOH')],CFG)
    for change in ['currency','date']:
        bad=json.loads(gzip.decompress(first))
        if change=='currency':bad['flights'][0]['price']['currency']='BRL'
        else:bad['flights'][0]['departure']+=86400;bad['flights'][0]['arrival']+=86400
        with gzip.open(out,'wt') as stream:json.dump(bad,stream)
        with pytest.raises(ValueError,match='USD|origin-local'):load_domestic(out,CODE)


def test_prepared_south_america_snapshot_matches_bounded_search_plan():
    path=flights.reference_path(DAY,CITY)
    if not path.exists():pytest.skip('Capture in progress')
    raw=load_domestic(path,CODE);replay=flights.replay_day(DAY,CITY)
    assert len(raw['metadata']['queries'])+len(raw['metadata']['uncollected_queries'])==702
    assert {a['code'] for a in raw['airports']}==set(AIR)
    assert len(raw['flights'])==len({f['id'] for f in raw['flights']})==len(replay['services'])
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(CFG['zones'][f['origin']])).date().isoformat()==DAY for f in raw['flights'])
    assert all(replay['start']<=s['stops'][0][1] and s['stops'][1][1]<replay['end'] for s in replay['services'])
    assert all(not f.get('price') or f['price']['currency']=='USD' for f in raw['flights'])


def test_empty_gateway_remains_selectable_without_invented_coverage(tmp_path,monkeypatch):
    cache=tmp_path/'cache';out=tmp_path/'day.gz'
    fs=parse_results(scripts(segment('GRU','GIG',[9,0],[10,0],60,carrier='LA',number='1')),'GRU','GIG',DAY,CFG['zones'])
    put(cache,'GRU','GIG',fs);put(cache,'GEO','PBM',[])
    prepare(cache,out,DAY,[('GRU','GIG'),('GEO','PBM')],CFG)
    raw=load_domestic(out,CODE)
    assert {a['code'] for a in raw['airports']}==set(AIR)
    assert raw['metadata']['country_gateways']==CFG['manifest']['country_gateways']
    assert raw['metadata']['coverage']['airports_returned']==2
    assert raw['metadata']['coverage']['queries_not_returned']==1
    assert raw['metadata']['coverage']['island_groups']['GY']['airports_returned']==0
    assert raw['metadata']['coverage']['island_groups']['SR']['airports_returned']==0
    assert raw['metadata']['coverage_by_scope']['international']['airports_returned']==0
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_FLIGHTS_REFERENCE',str(out))
    replay=flights.replay_day(DAY,CITY)
    assert len(replay['stations'])==27 and len(replay['services'])==1
