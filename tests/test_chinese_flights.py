"""Mainland major-airport identity, UTC+8 timing and partial USD fare evidence."""
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
CONFIG = country_config('CN')
AIRPORTS = {a['code']:a for a in CONFIG['manifest']['airports']}
START = int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp())
CONTEXT = dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_exact_airports_focused_mainland_manifest_and_expanded_candidate_provenance():
    manifest=CONFIG['manifest']
    assert len(AIRPORTS)==30 and len(manifest['routes'])==276
    assert CONFIG['currency']=='USD' and CONFIG['max_duration']==8*3600
    for a,b in [('PEK','PKX'),('SHA','PVG'),('CTU','TFU')]:
        assert AIRPORTS[a]['icao']!=AIRPORTS[b]['icao']
        assert AIRPORTS[a]['lon']!=AIRPORTS[b]['lon']
        assert [a,b] not in manifest['routes']
    assert all(a['country']=='CN' and a['timezone']=='Asia/Shanghai' for a in AIRPORTS.values())
    assert {a['island_group'] for a in AIRPORTS.values()}=={'North','Northeast','East','Central','South','Southwest','Northwest'}
    assert any('Historical 2018 city-pair' in e['kind'] for e in manifest['evidence'])
    assert any('2025 route candidate' in e['kind'] for e in manifest['evidence'])
    for a,b in manifest['routes']:
        assert [b,a] in manifest['routes']
        assert not {a,b} & {'BJS','NAY','HKG','MFM','TPE','TSA'}
    for pair in [('PEK','SHA'),('PKX','PVG'),('CTU','CAN'),('TFU','SZX'),('CAN','URC'),('PVG','LHW')]:
        assert list(pair) in manifest['routes']
    assert CITIES['china_flights']['replay_kind']=='flights'
    assert CITIES['china_flights'].get('flight_scopes')
    with pytest.raises(ValueError,match='planned; only domestic'):
        country_config('CN','international')
    assert country_config()['manifest'] is None and country_config('MY')['currency']=='MYR'


def test_urumqi_uses_airline_utc8_not_utc6_and_overnight_replay_overlap():
    assert START==int(datetime(2026,11,1,16,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('CAN','URC')],CONFIG))=={('2026-11-01','CAN','URC'),(DAY,'CAN','URC')}
    row=segment('CAN','URC',[21,30],[3,15],345,carrier='CZ',number='123');row[20]=[2026,11,1]
    records=parse_results(scripts(row,row),'CAN','URC','2026-11-01',CONFIG['zones'])
    assert len(records)==1 and records[0]['departure']<START<records[0]['arrival']
    assert records[0]['arrival']-records[0]['departure']==345*60
    wrong={**CONFIG['zones'],'URC':'Asia/Urumqi'}
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'CAN','URC','2026-11-01',wrong)


def test_cheapest_exact_flight_quotes_leave_source_unpriced_records_missing():
    row=segment('PEK','SHA',[8,0],[10,15],135,carrier='HU',number='123')
    other=segment('PEK','SHA',[8,0],[10,15],135,carrier='CA',number='999');other[17]=None
    records=parse_results(scripts(row,row,other),'PEK','SHA',DAY,CONFIG['zones'])
    assert len(records)==2 and any(f['aircraft']=='Aircraft not specified' for f in records)
    prices=cheapest_prices(scripts([offer(row,120),offer(row,95.25)]),records,'USD')
    by_number={f['number']:prices.get(f['id']) for f in records}
    assert by_number['HU123']['amount_minor']==9525
    assert by_number['CA999'] is None


def test_missing_queries_unverified_context_rebuild_and_compressed_http(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir()
    row=segment('CAN','URC',[21,30],[3,15],345,carrier='CZ',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'CAN','URC','2026-11-01',CONFIG['zones'])[0]
    q=dict(origin='CAN',destination='URC',date='2026-11-01',status='results',captured_at='2026-10-25T00:00:00+00:00',flights=[f],price_error='Unverified fare context')
    (cache/'2026-11-01-CAN-URC.json').write_text(json.dumps(q))
    pairs=[('CAN','URC'),('PEK','SHA')];out=tmp_path/'day.gz'
    prepare(cache,out,DAY,pairs,CONFIG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CONFIG)
    assert first==out.read_bytes()
    reference=json.loads(gzip.decompress(first));metadata=reference['metadata']
    assert len(metadata['uncollected_queries'])==3 and metadata['fare_context_unverified_queries']==1
    assert metadata['priced_flights']==0 and 'price' not in reference['flights'][0]
    monkeypatch.setenv('SUNTRAIN_CHINA_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,'china_flights')
    assert day['start']==START and len(day['services'])==1
    assert 'price' not in day['services'][0]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    info=replay_http.descriptor(DAY,'china_flights');response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['timezone']=='Asia/Shanghai'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_scope_currency_and_wrong_timezone_are_rejected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='approved manifest'):
        prepare(tmp_path,tmp_path/'out.gz',DAY,[('PEK','PKX')],CONFIG)
    path=tmp_path/'reference.gz';monkeypatch.setenv('SUNTRAIN_CHINA_FLIGHTS_REFERENCE',str(path))
    monkeypatch.setenv('SUNTRAIN_CHINA_INTERNATIONAL_REFERENCE',str(tmp_path/'missing.gz'))
    assert flights.reference_paths(DAY,'china_flights')==[path]
    f=dict(id='flight',number='CZ123',carrier='CZ',origin='CAN',destination='URC',departure=START,arrival=START+20700,price={**CONTEXT,'amount_minor':12000})
    airports=list(AIRPORTS.values())
    for field,value in [('country','HK'),('timezone','Asia/Urumqi')]:
        invalid=[{**a,field:value} if a['code']=='URC' else a for a in airports]
        write_reference(path,invalid,[f],dict(scope='domestic',fare_context=CONTEXT))
        with pytest.raises(ValueError,match='mainland airports using China standard time'):
            flights.load_reference(DAY,'china_flights')
    f['price']={**f['price'],'currency':'CNY'}
    write_reference(path,airports,[f],dict(scope='domestic',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):
        flights.load_reference(DAY,'china_flights')


def test_prepared_snapshot_reports_actual_coverage_and_missing_fares(monkeypatch):
    monkeypatch.setenv("SUNTRAIN_CHINA_FLIGHTS_REFERENCE",str(flights.reference_path(city="china_flights")))
    day=flights.replay_day(DAY,'china_flights')
    assert {'PEK','PKX','SHA','PVG','CTU','TFU','CAN','SZX','URC','LHW'} <= {a['code'] for a in day['stations']}
    assert day['services'] and all(s['flight_scope']=='domestic' for s in day['services'])
    assert len({s['id'] for s in day['services']})==len(day['services'])
    coverage=day['schedule']['coverage']
    assert coverage['queries_planned']==552
    assert coverage['queries_captured']+coverage['failed_or_missing_queries']==552
    assert coverage['candidate_airports']==30 and coverage['airports_planned']==30
    assert day['schedule']['priced_flights']==sum(bool(s.get('price')) for s in day['services'])
    assert any(not s.get('price') for s in day['services'])
    for s in day['services']:
        assert s['stops'][0][2]<day['end'] and s['stops'][1][1]>=START
        if s.get('price'):
            assert s['price']['currency']=='USD' and s['price']['amount_minor']>0
