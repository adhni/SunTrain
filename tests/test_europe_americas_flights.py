"""Offline cross-Atlantic reuse, route provenance, prices, local dates and independent views."""
from copy import deepcopy
from datetime import datetime
import gzip
import hashlib
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights,replay_http,international_network
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from scripts.prepare_europe_americas_routes import build,ROOT,DAY
from scripts.prepare_europe_americas_flights import prepare_cached,validate_query,budget,GROUP_CONTEXT
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from tests.test_google_flights import segment,scripts

CODE='EUROPE_AMERICAS';CITY='europe_americas_flights'


def test_exact_published_pairs_no_cartesian_routes_or_extra_dates():
    m=build();cfg=country_config(CODE)
    assert m==cfg['manifest']
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))==444
    assert len(m['airports'])==72 and len(m['regions']['europe'])==14 and len(m['regions']['americas'])==58
    europe,americas=map(set,[m['regions']['europe'],m['regions']['americas']])
    assert all((a in europe and b in americas) or (a in americas and b in europe) for a,b in m['routes'])
    assert {(e['origin'],e['destination']) for e in m['evidence']}==set(map(tuple,m['routes']))
    assert all(e['discovery_brands'] and e['source_urls'] for e in m['evidence'])
    assert not {'LGA','DCA','CGH','SDU','AEP','HNL'} & {c for p in m['routes'] for c in p}
    assert ['LHR','JFK'] in m['routes'] and ['LHR','EWR'] in m['routes']
    assert ['LGW','MCO'] in m['routes'] and ['MAD','GRU'] in m['routes']
    assert ['LGW','JFK'] not in m['routes']
    assert {q[0] for q in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert cfg['currency']=='EUR' and country_config('US')['currency']=='USD'
    assert CITIES[CITY]['default_flight_scope']=='both' and not CITIES[CITY]['flight_scopes']
    assert CITY not in international_network.CITIES
    air={a['code']:a for a in m['airports']}
    assert air['YVR']['timezone']=='America/Vancouver' and 'replay_timezone' not in air['YVR']
    assert country_config('US')['zones']['YVR']=='Etc/GMT+7'


def query_fixture():
    cfg=country_config(CODE)
    rows=[segment('LHR','JFK',[12,0],[15,0],480,carrier=c,number=str(i)) for i,c in enumerate(['BA','AA'],1)]
    fs=parse_results(scripts(*rows),'LHR','JFK',DAY,cfg['zones'],max_duration=86400)
    for f in fs:
        f['price']=dict(currency='EUR',amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    return dict(date=DAY,origin='LHR',destination='JFK',captured_at='2026-10-26T00:00:00Z',
        url='https://www.google.com/travel/flights?curr=EUR',capture_context=GROUP_CONTEXT,
        status='results',flights=fs,page_sha256='0'*64)


@pytest.mark.parametrize('mutation',['currency','parser','identity','naive_timestamp','rejection','segment','duration','departure_date','price_currency','price_context','unverified_price'])
def test_incompatible_captures_never_reused(mutation):
    q=deepcopy(query_fixture());cfg=country_config(CODE)
    if mutation=='currency':q['url']=q['url'].replace('EUR','USD')
    if mutation=='parser':q['capture_context']={**GROUP_CONTEXT,'max_duration':28800}
    if mutation=='identity':q['destination']='LGA'
    if mutation=='naive_timestamp':q['captured_at']='2026-10-26T00:00:00'
    if mutation=='rejection':q['rejected_flights']=[{'reason':'Ambiguous timestamps'}]
    if mutation=='segment':q['flights'][0]['destination']='LGA'
    if mutation=='duration':q['flights'][0]['arrival']=q['flights'][0]['departure']+86401
    if mutation=='departure_date':q['flights'][0]['departure']+=86400;q['flights'][0]['arrival']+=86400
    if mutation=='price_currency':q['flights'][0]['price']['currency']='USD'
    if mutation=='price_context':q['flights'][0]['price']['adults']=2
    if mutation=='unverified_price':q['price_error']='Unverified context'
    with pytest.raises(ValueError):validate_query(q,(DAY,'LHR','JFK'),cfg)


def test_offline_all_airline_reuse_missing_queries_reproducibility_and_http(tmp_path,monkeypatch):
    cfg=country_config(CODE);pairs=[['LHR','JFK'],['JFK','LHR']]
    cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    cache=tmp_path/'cache';cache.mkdir();q=query_fixture();source=cache/f'{DAY}-LHR-JFK.json';source.write_text(json.dumps(q))
    original=source.read_bytes();out=tmp_path/'day.gz'
    before=budget(cfg,cache,None)
    assert before['cached']==1 and before['missing_queries']==[[DAY,'JFK','LHR']] and before['new_network_requests']==0
    prepare_cached(out,cfg,cache,None);first=out.read_bytes();prepare_cached(out,cfg,cache,None)
    assert out.read_bytes()==first and source.read_bytes()==original
    raw=load_domestic(out,CODE)
    assert {f['carrier'] for f in raw['flights']}=={'BA','AA'}
    assert all(f['price']['currency']=='EUR' and f['price']['amount_minor']==12345 for f in raw['flights'])
    assert raw['metadata']['new_network_requests']==0 and raw['metadata']['scope']=='international'
    assert raw['metadata']['uncollected_queries']==[[DAY,'JFK','LHR']]
    assert raw['metadata']['queries'][0]['reused_capture_sha256']==hashlib.sha256(original).hexdigest()
    monkeypatch.setenv('SUNTRAIN_EUROPE_AMERICAS_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    replay=flights.replay_day(DAY,CITY)
    assert len(replay['services'])==2 and all(s['flight_scope']=='international' for s in replay['services'])
    assert len(replay['stations'])==72
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();url=replay_http.descriptor(DAY,CITY)['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['city']==CITY
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404
    bad=json.loads(gzip.decompress(first));bad['flights'][0]['price']['currency']='USD'
    with gzip.open(out,'wt') as f:json.dump(bad,f)
    with pytest.raises(ValueError,match='EUR'):load_domestic(out,CODE)


def test_frozen_snapshot_keeps_all_dated_captures_and_original_europe_view():
    raw=load_domestic(flights.reference_path(DAY,CITY),CODE);cfg=country_config(CODE)
    assert len(raw['flights'])==len({f['id'] for f in raw['flights']})==748
    assert len({f['carrier'] for f in raw['flights']})==31
    assert raw['metadata']['queries_reused']==len(raw['metadata']['queries'])==444
    assert not raw['metadata']['uncollected_queries'] and not raw['metadata']['failed_queries']
    assert sum(bool(f.get('price')) for f in raw['flights'])==743
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in raw['flights'])
    assert any(datetime.fromtimestamp(f['departure'],ZoneInfo('UTC')).date().isoformat()=='2026-11-03' for f in raw['flights'])
    replay=flights.replay_day(DAY,CITY)
    assert len(replay['services'])==748
    assert all(replay['start']<=s['stops'][0][1]<s['stops'][1][1]<replay['end'] for s in replay['services'])
    pairs=set(map(tuple,cfg['manifest']['routes']));records={f['id']:f for f in raw['flights']}
    with gzip.open(ROOT/'data/reference/europe_flights/2026-11-02.json.gz','rt') as stream:old=json.load(stream)
    selected=[f for f in old['flights'] if (f['origin'],f['destination']) in pairs and f['source_date']==DAY]
    assert len(selected)==314
    for f in selected:
        for field in ['id','number','carrier','origin','destination','departure','arrival','price']:
            assert records[f['id']].get(field)==f.get(field)
