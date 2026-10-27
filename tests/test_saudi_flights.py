"""Saudi exact airports, sourced directions, local dates, fares and offline replay."""
from datetime import datetime
from copy import deepcopy
import gzip
import json
import re
from zoneinfo import ZoneInfo
from pathlib import Path
import pytest
from flask import Flask
from dashboard import flights,international_network,replay_http
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from dashboard.i18n import CATALOGUES
from scripts.prepare_saudi_routes import DAY
from scripts.prepare_saudi_flights import prepare_cached,collection_routes,validate_query
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from tests.test_google_flights import segment,scripts

CITY='saudi_flights'

def query(currency='USD'):
    cfg=country_config('SA');row=segment('RUH','JED',[23,30],[1,30],120,carrier='SV',number='100')
    row[21]=[2026,11,3]
    fs=parse_results(scripts(row),'RUH','JED',DAY,cfg['zones'],max_duration=86400)
    for f in fs:f['price']=dict(currency=currency,amount_minor=10000,adults=1,cabin='economy',trip_type='one_way')
    return dict(date=DAY,origin='RUH',destination='JED',captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)


def test_manifest_civilian_airports_sourced_pairs_and_four_worldwide_hubs(tmp_path):
    cfg=country_config('SA');m=cfg['manifest'];a={a['code']:a for a in m['airports']};worldwide={'RUH','JED','DMM','MED'}
    assert set(m['worldwide_hubs'])==worldwide and len(m['launch_airports'])==28
    assert cfg['currency']=='USD' and cfg['max_duration']==86400
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    domestic={(x,y) for x,y in m['routes'] if a[x]['country']==a[y]['country']=='SA'}
    assert len(domestic)==140 and {c for pair in domestic for c in pair}==set(m['launch_airports'])
    assert {('RUH','RSI'),('RSI','RUH'),('JED','GIZ'),('GIZ','JED')}<=domestic
    assert ('URY','SHW') not in domestic and 'KMC' not in m['launch_airports']
    assert {(e['origin'],e['destination']) for e in m['evidence']}==set(map(tuple,m['routes']))
    assert all(e['sources'] for e in m['evidence'])
    for x,y in m['new_collection_routes']:
        assert a[x]['country']=='SA' or a[y]['country']=='SA'
        if a[x]['country']!=a[y]['country']:assert {x,y}&worldwide
    assert a['RUH']['icao']=='OERK' and a['JED']['icao']=='OEJN'
    assert a['DMM']['icao']=='OEDF' and a['MED']['icao']=='OEMA'
    assert a['RSI']['icao']=='OERS' and a['NUM']['icao']=='OENN'
    assert a['HMB']['timezone']=='Africa/Cairo' and a['KSQ']['timezone']=='Asia/Samarkand'
    assert a['NMA']['timezone']=='Asia/Tashkent'
    assert m['source_gaps'] and {r['code'] for r in m['unresolved_airports']}=={'ALY'}
    assert CITY not in international_network.CITIES
    assert CITIES[CITY]['default_flight_scope']=='both' and CITIES[CITY]['regional_start_view']
    assert set(collection_routes(tmp_path,cfg))==set(map(tuple,m['new_collection_routes']))
    assert not m['archive_reuse_routes']


@pytest.mark.parametrize('code',['RUH','JED','MED','DMM','RSI','NUM','GIZ','HOF'])
def test_saudi_airports_share_year_round_utc_three(code):
    cfg=country_config('SA')
    assert cfg['zones'][code]=='Asia/Riyadh'
    for month in [1,7,11]:assert datetime(2026,month,2,12,tzinfo=ZoneInfo(cfg['zones'][code])).utcoffset().total_seconds()==10800


def test_dated_overnight_and_cross_zone_long_haul():
    cfg=country_config('SA');q=query();validate_query(q,(DAY,'RUH','JED'),cfg)
    assert datetime.fromtimestamp(q['flights'][0]['arrival'],ZoneInfo('Asia/Riyadh')).date().isoformat()=='2026-11-03'
    row=segment('MNL','JED',[15,0],[22,0],720,carrier='SV',number='200')
    fs=parse_results(scripts(row),'MNL','JED',DAY,cfg['zones'],[],86400)
    assert len(fs)==1 and fs[0]['arrival']-fs[0]['departure']==43200
    row[11]=700;rejected=[]
    assert not parse_results(scripts(row),'MNL','JED',DAY,cfg['zones'],rejected,86400) and rejected


@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_offline_missing_queries_mixed_prices_and_replay_http(tmp_path,monkeypatch,currency):
    cfg=country_config('SA');pairs=[['RUH','JED'],['JED','RUH']]
    cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    cache=tmp_path/'cache';cache.mkdir();q=query(currency);q['reused_source']='original.json'
    path=cache/f'{DAY}-RUH-JED.json';path.write_text(json.dumps(q));original=path.read_bytes()
    out=tmp_path/'day.gz';prepare_cached(cache,out,cfg);first=out.read_bytes();prepare_cached(cache,out,cfg)
    assert out.read_bytes()==first and path.read_bytes()==original
    raw=load_domestic(out,'SA');assert raw['flights'][0]['flight_scope']=='domestic'
    assert raw['flights'][0]['price']['currency']==currency and raw['metadata']['queries_reused']==1
    assert raw['metadata']['uncollected_queries']==[[DAY,'JED','RUH']]
    assert 'Saudi' in raw['metadata']['collection_strategy'] and 'Istanbul' not in raw['metadata']['collection_strategy']
    monkeypatch.setenv('SUNTRAIN_SAUDI_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,CITY)
    assert day['timezone']=='Asia/Riyadh' and day['regional_start_view'] and len(day['services'])==1
    assert day['services'][0]['color']==flights.AIRLINES['SV'][1]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();url=replay_http.descriptor(DAY,CITY)['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['city']==CITY
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404
    bad=deepcopy(raw);bad['flights'][0]['price']['currency']='SAR'
    with gzip.open(out,'wt') as stream:json.dump(bad,stream)
    with pytest.raises(ValueError):load_domestic(out,'SA')


def test_every_note_sentence_translated_and_carriers_distinct():
    for sentence in re.split(r'(?<=[.!?])\s+',country_config('SA')['manifest']['replay_note']):
        assert sentence in CATALOGUES['id'] and CATALOGUES['id'][sentence]!=sentence
    assert len({flights.AIRLINES[c][1] for c in ['SV','XY','F3']})==3
    assert CATALOGUES['id']['Saudi Arabia · Flights']=='Arab Saudi · Penerbangan'


def test_reference_unique_dated_records_prices_and_reported_gaps():
    raw=load_domestic(flights.reference_path(DAY,CITY),'SA');cfg=country_config('SA');fs=raw['flights'];m=raw['metadata']
    assert len(fs)==len({f['id'] for f in fs})==1153
    assert len({f['carrier'] for f in fs})==51
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in fs)
    assert m['queries_reused']==159 and m['coverage']['queries_captured']==880
    assert m['coverage']['routes_returned']==381 and m['coverage']['queries_not_returned']==499
    assert not m['failed_queries'] and not m['uncollected_queries'] and m['coverage']['rejected_records']==0
    dom=[f for f in fs if f['flight_scope']=='domestic'];international=[f for f in fs if f['flight_scope']=='international']
    assert len(dom)==396 and len(international)==757
    assert len({c for f in dom for c in (f['origin'],f['destination'])})==24
    assert all(f.get('price',{}).get('currency')=='USD' for f in dom)
    assert sum(bool(f.get('price')) for f in fs)==1097
    missing=set(cfg['manifest']['launch_airports'])-{c for f in dom for c in (f['origin'],f['destination'])}
    assert missing=={'EJH','HOF','NUM','TUI'}
    checks=[q['domestic_recheck'] for q in m['queries'] if 'domestic_recheck' in q]
    assert len(checks)==8 and sum(q['flights_returned']-q['previous_flights'] for q in checks)==11
