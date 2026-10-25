"""Major-airport Japanese domestic replay: exact identity, JST and USD quotes."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment, scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference

DAY = '2026-11-02'
CONFIG = country_config('JP')
AIRPORTS = {a['code']:a for a in CONFIG['manifest']['airports']}
START = int(datetime(2026, 11, 2, tzinfo=ZoneInfo('Asia/Tokyo')).timestamp())
CONTEXT = dict(currency='USD', adults=1, cabin='economy', trip_type='one_way')


def test_distinct_airports_and_major_route_scope():
    manifest = CONFIG['manifest']
    assert CONFIG['currency']=='USD' and CONFIG['max_duration']==8*3600
    for codes in [('HND','NRT'), ('ITM','KIX','UKB'), ('NGO','NKM'), ('CTS','OKD'), ('MMY','SHI')]:
        assert len({AIRPORTS[c]['icao'] for c in codes})==len(codes)
        assert len({AIRPORTS[c]['lon'] for c in codes})==len(codes)
    assert all(a['country']=='JP' and a['timezone']=='Asia/Tokyo' for a in AIRPORTS.values())
    assert {a['island_group'] for a in AIRPORTS.values()}=={'Hokkaido','Honshu','Shikoku','Kyushu','Okinawa'}
    assert len(manifest['routes'])==302
    assert len({c for pair in manifest['routes'] for c in pair})==45
    for a,b in manifest['routes']:
        assert [b,a] in manifest['routes']
        assert not {a,b} & {'TYO','OSA','SPK','NKM','OKD','KTD','MMD','AGJ','HTR'}
    for pair in [('HND','CTS'),('NRT','FUK'),('ITM','SDJ'),('KIX','OKA'),('OKA','MMY'),('UKB','SHI')]:
        assert list(pair) in manifest['routes']
    assert CITIES['japan_flights']['replay_kind']=='flights'
    assert CITIES['japan_flights'].get('flight_scopes')
    for city in ['japan','tokyo']:
        assert CITIES[city].get('replay_kind','transit')=='transit'
    with pytest.raises(ValueError, match='planned; only domestic'):
        country_config('JP','international')
    assert country_config()['manifest'] is None
    assert country_config('MY')['currency']=='MYR' and country_config('KR')['currency']=='USD'


def test_jst_midnight_overnight_duration_and_exact_cheapest_quote():
    assert START==int(datetime(2026,11,1,15,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('HND','CTS')],CONFIG))=={('2026-11-01','HND','CTS'),(DAY,'HND','CTS')}
    row=segment('HND','CTS',[23,30],[1,0],90,carrier='NH',number='123');row[20]=[2026,11,1]
    record=parse_results(scripts(row,row),'HND','CTS','2026-11-01',CONFIG['zones'])
    assert len(record)==1 and record[0]['departure']<START<record[0]['arrival']
    row=segment('OKA','MMY',[8,0],[8,45],45,carrier='NU',number='123');row[17]=None
    other=segment('OKA','MMY',[8,0],[8,45],45,carrier='NH',number='999')
    records=parse_results(scripts(row,row,other),'OKA','MMY',DAY,CONFIG['zones'])
    assert len(records)==2 and any(f['aircraft']=='Aircraft not specified' for f in records)
    prices=cheapest_prices(scripts([offer(row,95),offer(row,65.25),offer(other,120)]),records,'USD')
    by_number={f['number']:prices[f['id']]['amount_minor'] for f in records}
    assert by_number=={'NU123':6525,'NH999':12000}
    row[11]=20
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'OKA','MMY',DAY,CONFIG['zones'])


def test_cached_preparation_missing_queries_and_http(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir()
    row=segment('HND','CTS',[23,30],[1,0],90,carrier='NH',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'HND','CTS','2026-11-01',CONFIG['zones'])[0]
    f['price']={**CONTEXT,'amount_minor':6525,'captured_at':'2026-10-25T00:00:00+00:00'}
    q=dict(origin='HND',destination='CTS',date='2026-11-01',status='results',captured_at='2026-10-25T00:00:00+00:00',flights=[f])
    (cache/'2026-11-01-HND-CTS.json').write_text(json.dumps(q))
    pairs=[('HND','CTS'),('NRT','FUK')];out=tmp_path/'day.gz'
    prepare(cache,out,DAY,pairs,CONFIG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CONFIG)
    assert first==out.read_bytes()
    reference=json.loads(gzip.decompress(first))
    assert len(reference['metadata']['uncollected_queries'])==3
    assert reference['metadata']['coverage']['queries_captured']==1
    assert reference['metadata']['coverage_scope']==CONFIG['manifest']['coverage_scope']
    monkeypatch.setenv('SUNTRAIN_JAPAN_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,'japan_flights')
    assert day['start']==START and len(day['services'])==1
    assert day['services'][0]['price']==f['price']
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    info=replay_http.descriptor(DAY,'japan_flights');response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['timezone']=='Asia/Tokyo'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_deferred_and_foreign_routes_cannot_enter_the_domestic_snapshot(tmp_path,monkeypatch):
    for pair in [('NKM','FUK'),('OKD','HKD')]:
        with pytest.raises(ValueError,match='approved manifest'):
            prepare(tmp_path,tmp_path/'out.gz',DAY,[pair],CONFIG)
    path=tmp_path/'reference.gz';monkeypatch.setenv('SUNTRAIN_JAPAN_FLIGHTS_REFERENCE',str(path))
    monkeypatch.setenv('SUNTRAIN_JAPAN_INTERNATIONAL_REFERENCE',str(tmp_path/'missing.gz'))
    assert flights.reference_paths(DAY,'japan_flights')==[path]
    f=dict(id='flight',number='JL123',carrier='JL',origin='HND',destination='CTS',departure=START,arrival=START+5400,price={**CONTEXT,'amount_minor':6525})
    airports=list(AIRPORTS.values())
    foreign=[{**a,'country':'KR'} if a['code']=='CTS' else a for a in airports]
    write_reference(path,foreign,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='excludes foreign'):
        flights.load_reference(DAY,'japan_flights')
    f['price']={**f['price'],'currency':'JPY'}
    write_reference(path,airports,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):
        flights.load_reference(DAY,'japan_flights')
    f.pop('price');write_reference(path,airports,[f],dict(scope='domestic',fare_context={**CONTEXT,'currency':'JPY'}))
    with pytest.raises(ValueError,match='fares require USD'):
        flights.load_reference(DAY,'japan_flights')


def test_prepared_domestic_coverage_and_prices(monkeypatch):
    monkeypatch.setenv("SUNTRAIN_JAPAN_FLIGHTS_REFERENCE",str(flights.reference_path(city="japan_flights")))
    day=flights.replay_day(DAY,'japan_flights')
    codes={a['code'] for a in day['stations']}
    assert {'HND','NRT','ITM','KIX','UKB','NGO','CTS','FUK','OKA','MMY','SHI'}<=codes
    assert not codes & {'NKM','OKD','KTD','MMD','AGJ','HTR'}
    assert day['services'] and all(s['flight_scope']=='domestic' for s in day['services'])
    assert len({s['id'] for s in day['services']})==len(day['services'])
    coverage=day['schedule']['coverage']
    assert coverage['queries_planned']==604
    assert coverage['queries_captured']+coverage['failed_or_missing_queries']==604
    assert coverage['candidate_airports']==47 and coverage['airports_planned']==45
    assert day['schedule']['priced_flights']==sum(bool(s.get('price')) for s in day['services'])
    for s in day['services']:
        assert s['stops'][0][2]<day['end'] and s['stops'][1][1]>=START
        if s.get('price'):
            assert s['price']['currency']=='USD' and s['price']['amount_minor']>0
