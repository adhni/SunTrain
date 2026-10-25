"""Thai exact airports, ICT replay ownership and positive original USD quotes."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights,replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference

DAY='2026-11-02';CONFIG=country_config('TH')
AIRPORTS={a['code']:a for a in CONFIG['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Bangkok')).timestamp())
CONTEXT=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_exact_domestic_airports_routes_and_explicit_probe_provenance():
    m=CONFIG['manifest'];assert len(AIRPORTS)==30 and len(m['routes'])==112
    assert AIRPORTS['BKK']['icao']!=AIRPORTS['DMK']['icao']
    assert all(a['country']=='TH' and a['timezone']=='Asia/Bangkok' for a in AIRPORTS.values())
    assert {a['island_group'] for a in AIRPORTS.values()}=={'Central','North','Northeast','East','South'}
    for a,b in m['routes']:
        assert [b,a] in m['routes'] and a!=b and set((a,b))<=AIRPORTS.keys()
    assert ['BKK','DMK'] not in m['routes']
    assert {'HGN','PRH'}=={a['code'] for a in m['deferred_airports']}
    assert any('Supplemental exact-airport' in e['kind'] for e in m['evidence'])
    assert any('Historical Airpass' in e['kind'] for e in m['evidence'])
    assert not CITIES['thailand_flights'].get('flight_scopes')
    with pytest.raises(ValueError,match='planned; only domestic'):country_config('TH','international')
    assert CONFIG['currency']=='USD' and country_config()['manifest'] is None


def test_ict_midnight_overnight_adjacent_day_short_flights_and_lowest_exact_quote():
    assert START==int(datetime(2026,11,1,17,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('BKK','HKT')],CONFIG))=={('2026-11-01','BKK','HKT'),(DAY,'BKK','HKT')}
    row=segment('BKK','HKT',[23,30],[0,50],80,carrier='TG',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row,row),'BKK','HKT','2026-11-01',CONFIG['zones'])
    assert len(f)==1 and f[0]['departure']<START<f[0]['arrival']
    assert f[0]['arrival']-f[0]['departure']==80*60
    quotes=cheapest_prices(scripts([offer(row,100),offer(row,79.25)]),f,'USD')
    assert quotes[f[0]['id']]['amount_minor']==7925
    short=segment('HKT','USM',[9,0],[9,30],30,carrier='PG',number='99')
    assert len(parse_results(scripts(short),'HKT','USM',DAY,CONFIG['zones']))==1
    wrong={**CONFIG['zones'],'HKT':'Asia/Singapore'}
    with pytest.raises(ValueError,match='duration differs'):parse_results(scripts(row),'BKK','HKT','2026-11-01',wrong)


def test_cached_missing_queries_determinism_and_gzip_http(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir()
    row=segment('BKK','HKT',[23,30],[0,50],80,carrier='TG',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'BKK','HKT','2026-11-01',CONFIG['zones'])[0]
    q=dict(origin='BKK',destination='HKT',date='2026-11-01',status='results',captured_at='2026-10-25T00:00:00+00:00',flights=[f],price_error='Unverified fare context')
    (cache/'2026-11-01-BKK-HKT.json').write_text(json.dumps(q))
    out=tmp_path/'day.gz';prepare(cache,out,DAY,[('BKK','HKT'),('DMK','CNX')],CONFIG)
    first=out.read_bytes();prepare(cache,out,DAY,[('BKK','HKT'),('DMK','CNX')],CONFIG);assert first==out.read_bytes()
    ref=json.loads(gzip.decompress(first));assert len(ref['metadata']['uncollected_queries'])==3
    assert ref['metadata']['priced_flights']==0 and ref['metadata']['fare_context_unverified_queries']==1
    monkeypatch.setenv('SUNTRAIN_THAILAND_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,'thailand_flights');assert day['start']==START and len(day['services'])==1
    assert flights.reference_paths(DAY,'thailand_flights')==[out]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    info=replay_http.descriptor(DAY,'thailand_flights');response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Asia/Bangkok'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_foreign_airport_metro_substitution_wrong_zone_and_currency_are_rejected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='approved manifest'):prepare(tmp_path,tmp_path/'bad.gz',DAY,[('BKK','DMK')],CONFIG)
    path=tmp_path/'fixture.gz';monkeypatch.setenv('SUNTRAIN_THAILAND_FLIGHTS_REFERENCE',str(path))
    f=dict(id='test',number='TG1',origin='BKK',destination='HKT',carrier='TG',airline='THAI',departure=START+3600,arrival=START+7200,source_date=DAY)
    airports=[AIRPORTS['BKK'],{**AIRPORTS['HKT'],'country':'MY'}]
    write_reference(path,airports,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='two Thai airports'):flights.load_reference(DAY,'thailand_flights')
    airports=[AIRPORTS['BKK'],{**AIRPORTS['HKT'],'timezone':'Asia/Singapore'}]
    write_reference(path,airports,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='using ICT'):flights.load_reference(DAY,'thailand_flights')
    airports=[AIRPORTS['BKK'],AIRPORTS['HKT']]
    f['price']=dict(currency='THB',amount_minor=20000,adults=1,cabin='economy',trip_type='one_way')
    write_reference(path,airports,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):flights.load_reference(DAY,'thailand_flights')
    f.pop('price');write_reference(path,airports,[f],dict(scope='domestic',fare_context={**CONTEXT,'currency':'THB'}))
    with pytest.raises(ValueError,match='fares require USD'):flights.load_reference(DAY,'thailand_flights')


def test_prepared_thai_snapshot_preserves_scope_and_reports_actual_coverage():
    if not flights.reference_path(city='thailand_flights').exists():pytest.skip('Collection in progress')
    day=flights.replay_day(DAY,'thailand_flights');codes={a['code'] for a in day['stations']}
    assert {'BKK','DMK','CNX','HKT','USM','HDY','UBP'}<=codes
    assert day['services'] and all(f['flight_scope']=='domestic' for f in day['services'])
    assert len({f['id'] for f in day['services']})==len(day['services'])
    c=day['schedule']['coverage'];assert c['queries_planned']==224
    assert c['queries_captured']+c['failed_or_missing_queries']==224
    assert c['candidate_airports']==30 and c['airports_planned']==30
    assert day['schedule']['priced_flights']==sum(bool(f.get('price')) for f in day['services'])
    for f in day['services']:
        assert f['stops'][0][2]<day['end'] and f['stops'][1][1]>=day['start']
        if f.get('price'):assert f['price']['currency']=='USD' and f['price']['amount_minor']>0
