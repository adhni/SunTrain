"""Exact SIN/XSP identities, long-haul dates, USD captures and replay isolation."""
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
from scripts.prepare_singapore_flights import seed_usd_captures
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from scripts.flight_prices import cheapest_prices,verify_fare_context
from tests.test_indonesian_international_flights import write_reference

CONFIG=country_config('SG','international')
AIRPORTS={a['code']:a for a in CONFIG['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Singapore')).timestamp())
CONTEXT=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_manifest_keeps_exact_airports_and_transport_view_separate():
    for code in ['SIN','XSP']:
        assert AIRPORTS[code]['country']=='SG' and AIRPORTS[code]['timezone']=='Asia/Singapore'
    assert AIRPORTS['SIN']['icao']=='WSSS' and AIRPORTS['XSP']['icao']=='WSSL'
    assert AIRPORTS['SIN']['lon']!=AIRPORTS['XSP']['lon']
    assert ['XSP','SZB'] in CONFIG['manifest']['routes']
    for a,b in [('KUL','SZB'),('PEK','PKX'),('NRT','HND')]:
        assert AIRPORTS[a]['icao']!=AIRPORTS[b]['icao']
    for a,b in CONFIG['manifest']['routes']:
        assert (AIRPORTS[a]['country']=='SG')!=(AIRPORTS[b]['country']=='SG')
        assert [b,a] in CONFIG['manifest']['routes']
    assert all(ZoneInfo(a['timezone']) for a in AIRPORTS.values())
    assert not CONFIG['manifest']['unresolved_airports']
    assert CITIES['singapore'].get('replay_kind','transit')=='transit'
    assert CITIES['singapore_flights']['flight_hubs']==['SIN','XSP']
    assert country_config()['manifest'] is None and country_config('MY')['currency']=='MYR'
    with pytest.raises(ValueError,match='international scope'):country_config('SG')


def test_overnight_long_haul_and_adjacent_origin_dates():
    pairs=[('EWR','SIN'),('SIN','EWR'),('AKL','SIN')]
    queries=set(expected_queries('2026-11-02',pairs,CONFIG))
    for a,b in pairs:
        for at in range(START-86400,START+86400,900):
            local=datetime.fromtimestamp(at,ZoneInfo(AIRPORTS[a]['timezone'])).date().isoformat()
            assert (local,a,b) in queries
    row=segment('SIN','EWR',[23,50],[6,50],1200,carrier='SQ',number='22');row[20]=[2026,11,1]
    records=parse_results(scripts(row,row),'SIN','EWR','2026-11-01',CONFIG['zones'],max_duration=86400)
    assert len(records)==1 and records[0]['arrival']-records[0]['departure']==20*3600
    assert records[0]['departure']<START<records[0]['arrival']
    row[11]=1190
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'SIN','EWR','2026-11-01',CONFIG['zones'],max_duration=86400)


def test_short_seletar_flight_has_its_own_cheapest_usd_quote():
    row=segment('XSP','SZB',[8,30],[9,50],80,carrier='FY',number='3123')
    records=parse_results(scripts(row),'XSP','SZB','2026-11-02',CONFIG['zones'])
    verify_fare_context('One way\n1\nEconomy\nCurrencyUSD','USD')
    quote=cheapest_prices(scripts([offer(row,90),offer(row,78.5)]),records,'USD')[records[0]['id']]
    assert quote['amount_minor']==7850 and quote['currency']=='USD'
    with pytest.raises(ValueError,match='Unverified'):
        verify_fare_context('One way\n1\nEconomy\nCurrencySGD','USD')


def test_reused_captures_require_exact_query_and_usd_and_keep_timestamp(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'DXB').mkdir();cache=tmp_path/'cache'
    q=dict(date='2026-11-02',origin='SIN',destination='DXB',captured_at='2026-10-25T00:00:00+00:00',
        url='https://www.google.com/travel/flights?curr=USD',flights=[],status='no_matching_direct_flights')
    p=source/'DXB/2026-11-02-SIN-DXB.json';p.write_text(json.dumps(q))
    assert seed_usd_captures(cache,CONFIG,source)==1
    assert json.loads((cache/p.name).read_text())==q
    assert seed_usd_captures(cache,CONFIG,source)==0
    p=source/'DXB/2026-11-02-DXB-SIN.json';q.update(origin='DXB',destination='SIN',url='https://www.google.com/travel/flights?curr=MYR');p.write_text(json.dumps(q))
    assert seed_usd_captures(cache,CONFIG,source)==0
    q['url']='https://www.google.com/travel/flights?curr=USD';q['flights']=[dict(price=dict(currency='SGD',amount_minor=10000))];p.write_text(json.dumps(q))
    assert seed_usd_captures(cache,CONFIG,source)==0
    q['flights'][0]['price']={**CONTEXT,'amount_minor':10000,'captured_at':q['captured_at']};p.write_text(json.dumps(q))
    assert seed_usd_captures(cache,CONFIG,source)==1
    assert json.loads((cache/p.name).read_text())['flights'][0]['price']==q['flights'][0]['price']


def test_cached_preparation_reports_missing_queries_and_reproduces_http(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();pairs=[('SIN','KUL'),('XSP','SZB')]
    for a,b in pairs:
        row=segment(a,b,[8,30],[9,50],80,carrier='FY' if a=='XSP' else 'SQ',number='3123' if a=='XSP' else '106')
        record=parse_results(scripts(row),a,b,'2026-11-02',CONFIG['zones'])[0]
        record['price']={**CONTEXT,'amount_minor':7850,'captured_at':'2026-10-25T00:00:00+00:00'}
        (cache/f'2026-11-02-{a}-{b}.json').write_text(json.dumps(dict(date='2026-11-02',origin=a,destination=b,status='results',captured_at='2026-10-25T00:00:00+00:00',flights=[record])))
    out=tmp_path/'day.gz';prepare(cache,out,'2026-11-02',pairs,CONFIG);first=out.read_bytes()
    prepare(cache,out,'2026-11-02',pairs,CONFIG);assert first==out.read_bytes()
    r=json.loads(gzip.decompress(first));assert r['metadata']['uncollected_queries']==[['2026-11-01',a,b] for a,b in pairs]
    assert r['metadata']['scope']=='international' and r['metadata']['country']=='SG'
    monkeypatch.setenv('SUNTRAIN_SINGAPORE_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day('2026-11-02','singapore_flights')
    assert len(day['services'])==2 and day['default_airport']=='SIN' and day['timezone']=='Asia/Singapore'
    assert all(f['price']['currency']=='USD' and f['flight_scope']=='international' for f in day['services'])
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();d=replay_http.descriptor('2026-11-02','singapore_flights')
    response=client.get(d['url'],headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    assert len(json.loads(gzip.decompress(response.data))['services'])==2
    assert client.get(d['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(d['url'].replace('2026-11-02','2026-11-03')).status_code==404


def test_loader_rejects_other_currencies_and_unrelated_routes(tmp_path,monkeypatch):
    out=tmp_path/'day.gz';monkeypatch.setenv('SUNTRAIN_SINGAPORE_FLIGHTS_REFERENCE',str(out))
    f=dict(id='flight',carrier='SQ',number='SQ106',airline='Singapore Airlines',origin='SIN',destination='KUL',departure=START,arrival=START+4800,price=dict(amount_minor=10000,currency='MYR'))
    airports=[AIRPORTS[k] for k in ['SIN','XSP','KUL','SZB']]
    write_reference(out,airports,[f],dict(scope='international',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):flights.load_reference('2026-11-02','singapore_flights')
    f['price']['currency']='USD';f['origin']='KUL';f['destination']='SZB'
    write_reference(out,airports,[f],dict(scope='international',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='must touch SIN or XSP'):flights.load_reference('2026-11-02','singapore_flights')


def test_prepared_snapshot_has_exact_identities_usd_and_auditable_coverage():
    day=flights.replay_day('2026-11-02','singapore_flights');m=day['schedule'];services=day['services']
    assert len({f['id'] for f in services})==len(services)>0
    assert m['coverage']['queries_captured']+len(m['uncollected_queries'])==len(list(expected_queries('2026-11-02',CONFIG['manifest']['routes'],CONFIG)))
    for code in ['SIN','XSP']:
        assert any(any(day['stations'][s[0]]['code']==code for s in f['stops']) for f in services)
    for f in services:
        codes={day['stations'][s[0]]['code'] for s in f['stops']}
        assert codes & {'SIN','XSP'}
        assert f['stops'][0][2]<day['end'] and f['stops'][1][1]>=day['start']
        if 'price' in f:assert f['price']['currency']=='USD' and f['price']['amount_minor']>0
