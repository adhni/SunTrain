"""Exact Thai gateways, shared ownership and independent ICT/UTC day windows."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

from flask import Flask
import pytest

from dashboard import flights, international_network as network, replay_http
from scripts.prepare_international_network import config, prepare
from tests.test_international_network import put, query, quote


def thai_config():
    cfg=config();m=cfg['manifest']
    routes=[['BKK','ICN'],['DMK','KUL'],['HKT','MEL']]
    routes += [[b,a] for a,b in routes[:]]
    codes={c for p in routes for c in p}
    m={**m,'routes':routes,'airports':[a for a in m['airports'] if a['code'] in codes]}
    views={c:network.consumer_queries(m,c) for c in ['international_network',*network.CITIES]}
    return {**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}


def thai_flight(a,b,day,hour,number,duration=7200,currency='USD'):
    air={a['code']:a for a in thai_config()['manifest']['airports']}
    at=int(datetime.fromisoformat(day).replace(hour=hour,tzinfo=ZoneInfo(air[a]['timezone'])).timestamp())
    return dict(id=f'{day}:{number}:{a}:{b}',number=number,origin=a,destination=b,departure=at,arrival=at+duration,
        carrier=number[:2],airline='Test airline',aircraft='Aircraft not specified',source_date=day,price=quote(currency))


def test_thai_candidates_exact_identity_and_bounded_provenance():
    m=json.loads(open('data/sources/thailand_international_routes.json').read());air={a['code']:a for a in m['airports']}
    assert m['base_directional_routes']==176 and len(m['routes'])==264
    assert air['BKK']['icao']!=air['DMK']['icao']
    shared_routes={tuple(p) for p in config()['manifest']['routes']}
    for a,b in m['routes']:
        assert (air[a]['country']=='TH')!=(air[b]['country']=='TH')
        assert [b,a] in m['routes'] and (a,b) in shared_routes
        assert all(x['country'] not in {'AE','QA'} or x['code'] in network.HUBS for x in (air[a],air[b]))
    for p in [('BKK','PEK'),('DMK','TFU'),('CNX','KIX'),('DMK','NRT'),('HKT','ICN')]:assert list(p) in m['routes']
    assert ['BKK','DMK'] not in m['routes']
    assert any('Supplemental' in e['kind'] for e in m['evidence'])
    assert any('Historical' in e['kind'] for e in m['evidence'])
    assert all(a['timezone']=='Asia/Bangkok' for a in air.values() if a['country']=='TH')


def test_ict_utc_overlap_distinct_airports_quotes_and_deterministic_preparation(tmp_path,monkeypatch):
    cfg=thai_config();cache=tmp_path/'capture';out=tmp_path/'network.gz'
    # BKK departure at 01 ICT is still Nov 1 UTC; DMK departure at 23 ICT is
    # Nov 2 UTC but arrives after Thailand's midnight. Keep both exact airports.
    fs=[thai_flight('BKK','ICN',network.DAY,1,'TG1'),
        thai_flight('DMK','KUL',network.DAY,23,'FD2',currency='MYR'),
        thai_flight('ICN','BKK','2026-11-01',23,'TG3',duration=4*3600),
        thai_flight('BKK','ICN','2026-11-03',1,'TG4')]
    for f in fs:put(cache,query(f))
    prepare(cache,out,cfg);first=out.read_bytes();prepare(cache,out,cfg);assert first==out.read_bytes()
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out))
    raw=network.load_archive();th=network.project(raw,'thailand_flights');utc=network.project(raw,'international_network')
    assert network.window('UTC')[0]-network.window('Asia/Bangkok')[0]==7*3600
    thids={f['id'] for f in th['flights']};utcids={f['id'] for f in utc['flights']}
    assert fs[0]['id'] in thids-utcids and fs[3]['id'] in utcids-thids
    assert fs[2]['id'] in thids and fs[1]['id'] in thids & utcids
    assert th['metadata']['priced_flights_by_currency']=={'USD':2,'MYR':1}
    assert th['metadata']['coverage']['failed_or_missing_queries']>0
    assert {'BKK','DMK'}<={a['code'] for a in th['airports']}
    both=network.overlay(dict(airports=[],flights=[],metadata={'coverage':{},'queries':[]}), 'thailand_flights')
    assert both['metadata']['coverage_by_scope']['international']==th['metadata']['coverage']
    assert both['metadata']['priced_flights_by_scope']['international']==3
    assert len({f['id'] for f in both['flights']})==3


def test_previous_archive_does_not_enable_thailand_until_consumer_data_exists(tmp_path,monkeypatch):
    path=tmp_path/'old.gz';monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(path))
    with gzip.open(path,'wt') as out:json.dump({'metadata':{'queries_by_view':{}}},out)
    assert not network.enabled(network.DAY,'thailand_flights')
    with gzip.open(path,'wt') as out:json.dump({'metadata':{'queries_by_view':{'thailand_flights':[]}}},out)
    assert network.enabled(network.DAY,'thailand_flights')


def test_prepared_thai_international_scopes_and_http_fingerprint(tmp_path,monkeypatch):
    raw=network.load_archive()
    if 'thailand_flights' not in raw['metadata']['queries_by_view']:pytest.skip('Collection in progress')
    projected=network.project(raw,'thailand_flights');full=flights.load_reference(network.DAY,'thailand_flights')
    air={a['code']:a for a in full['airports']};intl=projected['flights']
    assert intl and all((air[f['origin']]['country']=='TH')!=(air[f['destination']]['country']=='TH') for f in intl)
    byid={f['id']:f for f in full['flights']}
    assert all(byid[f['id']]==f for f in intl)
    assert {f['flight_scope'] for f in full['flights']}=={'domestic','international'}
    assert sum(f['flight_scope']=='domestic' for f in full['flights'])==615
    assert full['metadata']['coverage_by_scope']['domestic']['queries_planned']==224
    assert full['metadata']['coverage_by_scope']['international']['flights']==len(intl)
    assert full['metadata']['fare_context']['currency']=='mixed'
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    descriptor=replay_http.descriptor(network.DAY,'thailand_flights')
    response=client.get(descriptor['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200
    day=json.loads(gzip.decompress(response.data));assert day['timezone']=='Asia/Bangkok'
    assert day['start']==network.window('Asia/Bangkok')[0]
    assert client.get(descriptor['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    with pytest.raises(ValueError,match='Date outside'):replay_http.descriptor('2026-11-03','thailand_flights')
    # Changing only the shared file changes Thailand's HTTP download revision.
    path=tmp_path/'shared.gz';path.write_bytes(network.reference_path().read_bytes())
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(path))
    before=replay_http.descriptor(network.DAY,'thailand_flights')['url']
    path.write_bytes(path.read_bytes()+b'\x00')
    assert replay_http.descriptor(network.DAY,'thailand_flights')['url']!=before


def test_shared_thai_wrong_zone_and_domestic_leak_are_rejected(tmp_path,monkeypatch):
    cfg=thai_config();cache=tmp_path/'cache';out=tmp_path/'shared.gz'
    put(cache,query(thai_flight('BKK','ICN',network.DAY,9,'TG10')))
    prepare(cache,out,cfg);raw=json.loads(gzip.decompress(out.read_bytes()))
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out))
    thai=next(a for a in raw['airports'] if a['code']=='BKK');thai['timezone']='Asia/Singapore'
    with gzip.open(out,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='Thai airports require ICT'):network.load_archive()
    thai['timezone']='Asia/Bangkok'
    next(a for a in raw['airports'] if a['code']=='ICN')['country']='TH'
    with gzip.open(out,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='outside the international network'):network.load_archive()
