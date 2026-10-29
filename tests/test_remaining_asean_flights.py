"""Five ASEAN profiles, retired-airport discovery and honest empty snapshots."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights,international_network as network,replay_http
from dashboard.asean_flights import PROFILES,BY_CITY,RETIRED_AIRPORTS,load_domestic
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.prepare_international_network import config,seed
from tests.test_google_flights import segment,scripts
from tests.test_international_network import bundle,quote

DAY='2026-11-02'


def test_all_eleven_asean_countries_and_exact_new_airports():
    assert {'ID','MY','SG','TH','PH','VN','BN','KH','LA','MM','TL'}<=network.COUNTRIES.keys()
    manifest=config()['manifest'];air={a['code']:a for a in manifest['airports']}
    assert air['KTI']['icao']=='VDTI' and air['SAI']['icao']=='VDSA'
    assert not RETIRED_AIRPORTS.keys() & air.keys()
    for c,p in PROFILES.items():
        city=p['slug']+'_flights';assert CITIES[city]['timezone']==p['zone']
        assert CITIES[city]['flight_scopes']==p['domestic']
        assert CITIES[city]['default_flight_scope']=='both'
        assert all(a['timezone']==p['zone'] for a in air.values() if a['country']==c)
        m=json.loads(Path(f"data/sources/{p['slug']}_international_routes.json").read_text());bycode={a['code']:a for a in m['airports']}
        assert m['flight_records_remapped'] is False
        assert all((bycode[a]['country']==c)!=(bycode[b]['country']==c) for a,b in m['routes'])
    with pytest.raises(ValueError,match='international'):country_config('BN')


@pytest.mark.parametrize('country,origin,destination',[('KH','KTI','SAI'),('LA','VTE','LPQ'),('MM','RGN','MDL'),('TL','DIL','OEC')])
def test_domestic_dates_durations_and_exact_national_endpoint(country,origin,destination):
    cfg=country_config(country)
    assert set(expected_queries(DAY,[(origin,destination)],cfg))=={('2026-11-01',origin,destination),(DAY,origin,destination)}
    row=segment(origin,destination,[23,30],[0,30],60,carrier='ZZ',number='1');row[20]=[2026,11,1]
    fs=parse_results(scripts(row,row),origin,destination,'2026-11-01',cfg['zones'])
    start=network.window(PROFILES[country]['zone'])[0]
    assert len(fs)==1 and fs[0]['departure']<start<fs[0]['arrival']
    assert cfg['currency']=='USD' and cfg['allow_empty_snapshot']


@pytest.mark.parametrize('country,expected_hour,expected_minute',[('BN',16,0),('KH',17,0),('LA',17,0),('MM',17,30),('TL',15,0)])
def test_local_midnight_windows(country,expected_hour,expected_minute):
    start,end=network.window(PROFILES[country]['zone'])
    assert datetime.fromtimestamp(start,ZoneInfo('UTC'))==datetime(2026,11,1,expected_hour,expected_minute,tzinfo=ZoneInfo('UTC'))
    assert end-start==86400


def test_empty_captures_are_not_invented_flights_and_are_reproducible(tmp_path,monkeypatch):
    cfg=country_config('TL');cache=tmp_path/'cache';cache.mkdir();out=tmp_path/'empty.gz'
    for day,a,b in expected_queries(DAY,cfg['manifest']['routes'],cfg):
        (cache/f'{day}-{a}-{b}.json').write_text(json.dumps(dict(date=day,origin=a,destination=b,status='no_matching_direct_flights',captured_at='2026-10-26T00:00:00+00:00',flights=[])))
    prepare(cache,out,DAY,cfg['manifest']['routes'],cfg);first=out.read_bytes()
    prepare(cache,out,DAY,cfg['manifest']['routes'],cfg);assert first==out.read_bytes()
    raw=json.loads(gzip.decompress(first));assert raw['flights']==[] and raw['airports']==[]
    assert raw['metadata']['coverage']['queries_not_returned']==4 and not raw['metadata']['uncollected_queries']
    monkeypatch.setenv('SUNTRAIN_TIMOR_LESTE_FLIGHTS_REFERENCE',str(out))
    day=flights.replay_day(DAY,'timor_leste_flights');assert day['services']==[] and day['timezone']=='Asia/Dili'
    assert not network.enabled(DAY,'timor_leste_flights')


@pytest.mark.parametrize('country',['KH','LA','MM','TL'])
def test_strict_domestic_identity_zone_currency_context_and_duplicate_conflicts(tmp_path,country):
    cfg=country_config(country);a,b=cfg['manifest']['routes'][0];air={x['code']:x for x in cfg['manifest']['airports']}
    at=network.window(PROFILES[country]['zone'])[0]+3600
    f=dict(id='one',number='ZZ1',origin=a,destination=b,departure=at,arrival=at+3600,carrier='ZZ',airline='Test',price=quote())
    path=tmp_path/'day.gz';doc=dict(airports=[air[a],air[b]],flights=[f],metadata=dict(scope='domestic',fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')))
    def write():
        with gzip.open(path,'wt') as stream:json.dump(doc,stream)
    write();assert load_domestic(path,country)['flights'][0]['flight_scope']=='domestic'
    doc['airports'][0]={**air[a],'country':'AU'};write()
    with pytest.raises(ValueError,match='national identities'):load_domestic(path,country)
    doc['airports'][0]={**air[a],'timezone':'UTC'};write()
    with pytest.raises(ValueError,match='national identities'):load_domestic(path,country)
    doc['airports'][0]=air[a];f['price']={**quote(),'currency':'JPY'};write()
    with pytest.raises(ValueError,match='no implicit conversion'):load_domestic(path,country)
    f['price']=quote();doc['flights']=[f,{**f,'arrival':f['arrival']+60}];write()
    with pytest.raises(ValueError,match='Conflicting'):load_domestic(path,country)


def test_retired_airport_captures_are_not_relabelled_or_reused(tmp_path,monkeypatch):
    cfg,_,_=bundle(tmp_path,monkeypatch)
    old=dict(id='old',number='ZZ1',origin='PNH',destination='KUL',departure=1,arrival=3601,source_date=DAY,carrier='ZZ',airline='Test',flight_scope='international')
    base=dict(airports=[dict(code='PNH',country='KH',icao='VDPP',lat=11.5,lon=104.8)],flights=[old],metadata=dict(coverage={},queries=[]))
    overlaid=network.overlay(base,'malaysia_flights')
    assert not overlaid['flights'] and not overlaid['airports']
    assert old['origin']=='PNH' and base['airports'][0]['code']=='PNH'
    cache=tmp_path/'fresh';cache.mkdir();source=tmp_path/'old';source.mkdir()
    (source/f'{DAY}-PNH-KUL.json').write_text(json.dumps(dict(date=DAY,origin='PNH',destination='KUL',captured_at='2026-10-26T00:00:00+00:00',status='results',flights=[old])))
    assert seed(cache,{**cfg,'queries':[(DAY,'KTI','KUL')]},[source])['reused']==0


def test_prepared_five_country_views_http_and_shared_original_prices(tmp_path,monkeypatch):
    raw=network.load_archive()
    if any(city not in raw['metadata']['queries_by_view'] for city in BY_CITY):pytest.skip('Collection in progress')
    if any(not flights.reference_path(city=city).exists() for city,(c,p) in BY_CITY.items() if p['domestic']):pytest.skip('Domestic collection in progress')
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    for city,(c,p) in BY_CITY.items():
        projected=network.project(raw,city);loaded=flights.load_reference(DAY,city)
        byid={f['id']:f for f in loaded['flights']}
        assert projected['flights'] and all(byid[f['id']]==f for f in projected['flights'])
        assert not RETIRED_AIRPORTS.keys() & {a['code'] for a in loaded['airports']}
        desc=replay_http.descriptor(DAY,city);response=client.get(desc['url'],headers={'Accept-Encoding':'gzip'})
        assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']==p['zone']
        assert client.get(desc['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
        assert client.get(desc['url'].replace(DAY,'2026-11-03')).status_code==404
