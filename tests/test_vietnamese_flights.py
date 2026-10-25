"""Vietnam exact identities, dated schedules and independent ICT/UTC ownership."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, international_network as network, replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment, scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference
from scripts.prepare_international_network import config, prepare as prepare_network
from tests.test_international_network import put, query, quote

DAY='2026-11-02';CFG=country_config('VN')
AIR={a['code']:a for a in CFG['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh')).timestamp())
CONTEXT=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_exact_airports_published_vs_probe_provenance_and_no_city_substitution():
    assert len(AIR)==22 and len(CFG['manifest']['routes'])==122
    assert AIR['HAN']['icao']=='VVNB' and AIR['SGN']['icao']=='VVTS'
    assert AIR['DAD']['icao']=='VVDN' and AIR['DLI']['icao']=='VVDL'
    assert AIR['CXR']['icao']=='VVCR' and 'NHA' not in AIR
    assert all(a['timezone']=='Asia/Ho_Chi_Minh' and a['country']=='VN' for a in AIR.values())
    assert {a['island_group'] for a in AIR.values()}=={'North','Central and Highlands','South'}
    assert any('Supplemental' in e['kind'] for e in CFG['manifest']['evidence'])
    assert any('promotional route table' in e['kind'] for e in CFG['manifest']['evidence'])
    assert CITIES['vietnam_flights']['flight_scopes'] and CFG['currency']=='USD'
    assert 'Long Thanh is not substituted' in ' '.join(CFG['manifest']['airport_notes'])


def test_vietnam_day_overnight_adjacent_queries_short_duration_duplicate_and_lowest_quote():
    assert START==int(datetime(2026,11,1,17,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('HAN','SGN')],CFG))=={('2026-11-01','HAN','SGN'),(DAY,'HAN','SGN')}
    row=segment('HAN','SGN',[23,30],[0,50],80,carrier='VJ',number='123');row[20]=[2026,11,1]
    fs=parse_results(scripts(row,row),'HAN','SGN','2026-11-01',CFG['zones'])
    assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
    quotes=cheapest_prices(scripts([offer(row,100),offer(row,70.25)]),fs,'USD')
    assert quotes[fs[0]['id']]['amount_minor']==7025
    short=segment('SGN','CXR',[9,0],[9,30],30,carrier='VN',number='99')
    assert len(parse_results(scripts(short),'SGN','CXR',DAY,CFG['zones']))==1
    with pytest.raises(ValueError,match='duration'):
        parse_results(scripts(short),'SGN','CXR',DAY,{**CFG['zones'],'CXR':'Asia/Singapore'})


def test_preparation_missing_queries_reproducibility_http_and_fixture_isolation(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();out=tmp_path/'day.gz'
    row=segment('HAN','SGN',[9,0],[10,20],80,carrier='VN',number='1')
    f=parse_results(scripts(row),'HAN','SGN',DAY,CFG['zones'])[0]
    (cache/f'{DAY}-HAN-SGN.json').write_text(json.dumps(query(f)))
    prepare(cache,out,DAY,[('HAN','SGN'),('DAD','DLI')],CFG);first=out.read_bytes()
    prepare(cache,out,DAY,[('HAN','SGN'),('DAD','DLI')],CFG);assert out.read_bytes()==first
    raw=json.loads(gzip.decompress(first));assert len(raw['metadata']['uncollected_queries'])==3
    monkeypatch.setenv('SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    assert not network.enabled(DAY,'vietnam_flights')
    day=flights.replay_day(DAY,'vietnam_flights');assert day['start']==START and len(day['services'])==1
    assert flights.reference_paths(DAY,'vietnam_flights')==[out]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'vietnam_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Asia/Ho_Chi_Minh'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_foreign_airport_wrong_zone_and_relabelled_fares_rejected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='approved manifest'):prepare(tmp_path,tmp_path/'bad.gz',DAY,[('VCS','DIN')],CFG)
    out=tmp_path/'fixture.gz';monkeypatch.setenv('SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE',str(out))
    f=dict(id='test',number='VN1',origin='HAN',destination='SGN',carrier='VN',airline='Vietnam Airlines',departure=START+3600,arrival=START+7200,source_date=DAY)
    for field,value in [('country','IN'),('timezone','Asia/Bangkok')]:
        write_reference(out,[AIR['HAN'],{**AIR['SGN'],field:value}],[f],dict(scope='domestic',fare_context=CONTEXT))
        with pytest.raises(ValueError,match='two Vietnamese airports'):flights.load_reference(DAY,'vietnam_flights')
    f['price']={**quote(),'currency':'VND'}
    write_reference(out,[AIR['HAN'],AIR['SGN']],[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):flights.load_reference(DAY,'vietnam_flights')
    f.pop('price');write_reference(out,[AIR['HAN'],AIR['SGN']],[f],dict(scope='domestic',fare_context={**CONTEXT,'currency':'VND'}))
    with pytest.raises(ValueError,match='fares require USD'):flights.load_reference(DAY,'vietnam_flights')


def test_international_candidates_stay_in_footprint_with_exact_vietnamese_endpoint():
    m=json.loads(Path('data/sources/vietnam_international_routes.json').read_text());air={a['code']:a for a in m['airports']}
    assert len(m['routes'])==190 and m['base_directional_routes']==78
    shared={tuple(p) for p in config()['manifest']['routes']}
    assert any('Supplemental' in e['kind'] for e in m['evidence'])
    for a,b in m['routes']:
        assert (air[a]['country']=='VN')!=(air[b]['country']=='VN') and (a,b) in shared
        assert all(x['country'] in network.COUNTRIES for x in (air[a],air[b]))
    assert not {'HKG','TPE','MFM','YYZ','SPN'} & air.keys()


def test_shared_vietnam_vs_utc_windows_and_original_myr_quotes(tmp_path,monkeypatch):
    cfg=config();m=cfg['manifest'];pairs=[['HAN','KUL'],['KUL','HAN'],['DAD','SIN'],['SIN','DAD']];codes={c for p in pairs for c in p}
    m={**m,'routes':pairs,'airports':[a for a in m['airports'] if a['code'] in codes]}
    views={c:network.consumer_queries(m,c) for c in ['international_network',*network.CITIES]}
    cfg={**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}
    start=START+3600
    f=dict(id='VN1',number='VN1',carrier='VN',airline='Vietnam Airlines',origin='HAN',destination='KUL',departure=start,arrival=start+7200,source_date=DAY,price=quote('MYR'))
    cache=tmp_path/'cache';put(cache,query(f));out=tmp_path/'shared.gz';prepare_network(cache,out,cfg)
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out));raw=network.load_archive()
    vn=network.project(raw,'vietnam_flights');utc=network.project(raw,'international_network')
    assert len(vn['flights'])==1 and not utc['flights']
    assert vn['flights'][0]['price']['currency']=='MYR' and vn['metadata']['coverage']['failed_or_missing_queries']>0
    next(a for a in raw['airports'] if a['code']=='HAN')['timezone']='Asia/Bangkok'
    with gzip.open(out,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='Vietnamese airports require Asia/Ho_Chi_Minh'):network.load_archive()


def test_prepared_vietnamese_snapshots_scopes_and_shared_consistency(monkeypatch):
    if not flights.reference_path(city='vietnam_flights').exists():pytest.skip('Domestic collection in progress')
    monkeypatch.setenv('SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE',str(flights.reference_path(city='vietnam_flights')))
    domestic=flights.replay_day(DAY,'vietnam_flights')
    assert domestic['services'] and all(f['flight_scope']=='domestic' for f in domestic['services'])
    assert {'HAN','DAD','SGN','PQC','CXR'}<={a['code'] for a in domestic['stations']}
    assert domestic['schedule']['coverage']['queries_planned']==244
    assert domestic['schedule']['route_source_sha256']==CFG['manifest']['route_source_sha256']
    assert domestic['start']==START and domestic['end']==START+86400
    monkeypatch.delenv('SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE')
    raw=network.load_archive()
    if 'vietnam_flights' not in raw['metadata']['queries_by_view']:pytest.skip('International collection in progress')
    assert raw['metadata']['route_source_sha256']==config()['manifest']['route_source_sha256']
    full=flights.load_reference(DAY,'vietnam_flights');shared=network.project(raw,'vietnam_flights')
    byid={f['id']:f for f in full['flights']};assert len(byid)==len(full['flights'])
    assert shared['flights'] and all(byid[f['id']]==f for f in shared['flights'])
    assert {f['flight_scope'] for f in full['flights']}=={'domestic','international'}
    assert full['metadata']['coverage_by_scope']['international']==shared['metadata']['coverage']
