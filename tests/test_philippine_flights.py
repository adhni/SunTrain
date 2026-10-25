"""Recovered candidates never become schedules without dated exact-airport captures."""
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

DAY='2026-11-02';CFG=country_config('PH')
AIR={a['code']:a for a in CFG['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Manila')).timestamp())
CONTEXT=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_recovered_package_identity_correction_separate_airports_and_provenance():
    seed=json.loads(Path('data/sources/philippines_recovered_candidates.json').read_text())
    assert seed['source_metadata']['timetable_rows']==0
    assert len(seed['philippines_domestic_routes'])==150 and len(seed['philippines_international_routes'])==128
    assert any(a['code']=='NAG' and a['country']=='PH' for a in seed['philippines_airports'])
    assert len(AIR)==37 and len(CFG['manifest']['routes'])==150
    assert 'NAG' not in AIR and AIR['WNP']['icao']=='RPUN'
    assert AIR['MNL']['icao']!=AIR['CRK']['icao'] and AIR['MNL']['lat']!=AIR['CRK']['lat']
    assert AIR['USU']['country']==AIR['TAG']['country']=='PH'
    assert all(a['timezone']=='Asia/Manila' and a['country']=='PH' for a in AIR.values())
    assert {a['island_group'] for a in AIR.values()}=={'Luzon','Visayas','Mindanao'}
    assert all('Recovered' in e['kind'] for e in CFG['manifest']['evidence'])
    assert CFG['manifest']['identity_corrections'][0]['resolved']=='WNP'
    assert CITIES['philippines_flights']['flight_scopes'] and CFG['currency']=='USD'
    # An actual Indian NAG row is unaffected by the package-specific correction.
    indian={a['code']:a for a in country_config('IN')['manifest']['airports']}
    assert indian['NAG']['country']=='IN' and indian['NAG']['icao']=='VANP'


def test_manila_day_overnight_adjacent_queries_short_duration_duplicate_and_lowest_quote():
    assert START==int(datetime(2026,11,1,16,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('MNL','CEB')],CFG))=={('2026-11-01','MNL','CEB'),(DAY,'MNL','CEB')}
    row=segment('MNL','CEB',[23,30],[0,50],80,carrier='5J',number='123');row[20]=[2026,11,1]
    fs=parse_results(scripts(row,row),'MNL','CEB','2026-11-01',CFG['zones'])
    assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
    quotes=cheapest_prices(scripts([offer(row,100),offer(row,70.25)]),fs,'USD')
    assert quotes[fs[0]['id']]['amount_minor']==7025
    short=segment('CEB','ILO',[9,0],[9,30],30,carrier='DG',number='99')
    assert len(parse_results(scripts(short),'CEB','ILO',DAY,CFG['zones']))==1
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(short),'CEB','ILO',DAY,{**CFG['zones'],'ILO':'Asia/Bangkok'})


def test_preparation_missing_queries_reproducibility_http_and_fixture_isolation(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();out=tmp_path/'day.gz'
    row=segment('MNL','CEB',[9,0],[10,20],80,carrier='PR',number='1')
    f=parse_results(scripts(row),'MNL','CEB',DAY,CFG['zones'])[0]
    (cache/f'{DAY}-MNL-CEB.json').write_text(json.dumps(query(f)))
    prepare(cache,out,DAY,[('MNL','CEB'),('CRK','USU')],CFG);first=out.read_bytes()
    prepare(cache,out,DAY,[('MNL','CEB'),('CRK','USU')],CFG);assert out.read_bytes()==first
    raw=json.loads(gzip.decompress(first));assert len(raw['metadata']['uncollected_queries'])==3
    monkeypatch.setenv('SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    assert not network.enabled(DAY,'philippines_flights')
    day=flights.replay_day(DAY,'philippines_flights');assert day['start']==START and len(day['services'])==1
    assert flights.reference_paths(DAY,'philippines_flights')==[out]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'philippines_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Asia/Manila'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_foreign_airport_wrong_zone_and_relabelled_fares_rejected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='approved manifest'):prepare(tmp_path,tmp_path/'bad.gz',DAY,[('MNL','CRK')],CFG)
    out=tmp_path/'fixture.gz';monkeypatch.setenv('SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE',str(out))
    f=dict(id='test',number='PR1',origin='MNL',destination='CEB',carrier='PR',airline='PAL',departure=START+3600,arrival=START+7200,source_date=DAY)
    for field,value in [('country','IN'),('timezone','Asia/Bangkok')]:
        write_reference(out,[AIR['MNL'],{**AIR['CEB'],field:value}],[f],dict(scope='domestic',fare_context=CONTEXT))
        with pytest.raises(ValueError,match='two Philippine airports'):flights.load_reference(DAY,'philippines_flights')
    f['price']={**quote(),'currency':'PHP'}
    write_reference(out,[AIR['MNL'],AIR['CEB']],[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):flights.load_reference(DAY,'philippines_flights')
    f.pop('price');write_reference(out,[AIR['MNL'],AIR['CEB']],[f],dict(scope='domestic',fare_context={**CONTEXT,'currency':'PHP'}))
    with pytest.raises(ValueError,match='fares require USD'):flights.load_reference(DAY,'philippines_flights')


def test_international_candidates_stay_in_footprint_with_exact_philippine_endpoint():
    m=json.loads(Path('data/sources/philippines_international_routes.json').read_text());air={a['code']:a for a in m['airports']}
    assert len(m['routes'])==90 and m['base_directional_routes']==52 and len(m['deferred_international_routes'])==38
    shared={tuple(p) for p in config()['manifest']['routes']}
    assert any(r['target_date_status']=='not_established_for_2026_11_02' for r in m['evidence'] if 'target_date_status' in r)
    for a,b in m['routes']:
        assert (air[a]['country']=='PH')!=(air[b]['country']=='PH') and (a,b) in shared
        assert all(x['country'] in network.COUNTRIES for x in (air[a],air[b]))
    assert not {'HKG','TPE','MFM','YYZ','SPN'} & air.keys()


def test_shared_manila_vs_utc_windows_and_original_myr_quotes(tmp_path,monkeypatch):
    cfg=config();m=cfg['manifest'];pairs=[['MNL','KUL'],['KUL','MNL'],['CRK','SIN'],['SIN','CRK']];codes={c for p in pairs for c in p}
    m={**m,'routes':pairs,'airports':[a for a in m['airports'] if a['code'] in codes]}
    views={c:network.consumer_queries(m,c) for c in ['international_network',*network.CITIES]}
    cfg={**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}
    start=START+3600
    f=dict(id='PR1',number='PR1',carrier='PR',airline='PAL',origin='MNL',destination='KUL',departure=start,arrival=start+7200,source_date=DAY,price=quote('MYR'))
    cache=tmp_path/'cache';put(cache,query(f));out=tmp_path/'shared.gz';prepare_network(cache,out,cfg)
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out));raw=network.load_archive()
    ph=network.project(raw,'philippines_flights');utc=network.project(raw,'international_network')
    assert len(ph['flights'])==1 and not utc['flights']
    assert ph['flights'][0]['price']['currency']=='MYR' and ph['metadata']['coverage']['failed_or_missing_queries']>0
    next(a for a in raw['airports'] if a['code']=='MNL')['timezone']='Asia/Bangkok'
    with gzip.open(out,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='Philippine airports require Asia/Manila'):network.load_archive()


def test_prepared_philippine_snapshots_scopes_and_shared_consistency(monkeypatch):
    if not flights.reference_path(city='philippines_flights').exists():pytest.skip('Domestic collection in progress')
    monkeypatch.setenv('SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE',str(flights.reference_path(city='philippines_flights')))
    domestic=flights.replay_day(DAY,'philippines_flights')
    assert domestic['services'] and all(f['flight_scope']=='domestic' for f in domestic['services'])
    assert {'MNL','CRK','CEB','DVO','ILO'}<={a['code'] for a in domestic['stations']}
    assert domestic['schedule']['coverage']['queries_planned']==300
    assert domestic['start']==START and domestic['end']==START+86400
    monkeypatch.delenv('SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE')
    raw=network.load_archive()
    if 'philippines_flights' not in raw['metadata']['queries_by_view']:pytest.skip('International collection in progress')
    full=flights.load_reference(DAY,'philippines_flights');shared=network.project(raw,'philippines_flights')
    byid={f['id']:f for f in full['flights']};assert len(byid)==len(full['flights'])
    assert shared['flights'] and all(byid[f['id']]==f for f in shared['flights'])
    assert {f['flight_scope'] for f in full['flights']}=={'domestic','international'}
    assert full['metadata']['coverage_by_scope']['international']==shared['metadata']['coverage']
