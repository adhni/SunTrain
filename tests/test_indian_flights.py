"""India airport identity, IST boundaries, scope isolation and USD capture replay."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from scripts.prepare_indian_flights import seed_usd_captures
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment, scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference

DAY='2026-11-02'
CONFIG=country_config('IN')
INTERNATIONAL=country_config('IN','international')
AIRPORTS={a['code']:a for c in [CONFIG,INTERNATIONAL] for a in c['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Kolkata')).timestamp())
CONTEXT=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')


def test_manifest_exact_identity_scope_and_regional_candidates():
    assert CONFIG['currency']==INTERNATIONAL['currency']=='USD'
    assert CITIES['india_flights']['flight_scopes']
    assert CITIES.get('india',{}).get('replay_kind','transit')=='transit'
    for a,b in [('BOM','NMI'),('DEL','DXN'),('GOI','GOX')]:
        assert AIRPORTS[a]['icao']!=AIRPORTS[b]['icao']
        assert AIRPORTS[a]['lon']!=AIRPORTS[b]['lon']
    for c in [CONFIG,INTERNATIONAL]:
        airports={a['code']:a for a in c['manifest']['airports']}
        assert all(ZoneInfo(a['timezone']) for a in airports.values())
        for a,b in c['manifest']['routes']:
            assert [b,a] in c['manifest']['routes']
            assert sum(airports[code]['country']=='IN' for code in (a,b))==(2 if c is CONFIG else 1)
    assert ['COK','AGX'] in CONFIG['manifest']['routes'] and ['GAU','TEI'] in CONFIG['manifest']['routes']
    assert ['NMI','AUH'] in INTERNATIONAL['manifest']['routes']
    assert CONFIG['manifest']['unresolved_airports']==['MUNDRA','PITHORAGARH','PURNEA']
    assert country_config('MY')['currency']=='MYR' and country_config()['manifest'] is None


def test_half_hour_clock_overnight_and_international_adjacent_dates():
    assert START==int(datetime(2026,11,1,18,30,tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY,[('DEL','BOM')],CONFIG))=={('2026-11-01','DEL','BOM'),(DAY,'DEL','BOM')}
    for a,b in [('JFK','DEL'),('DEL','JFK'),('SYD','DEL')]:
        queries=set(expected_queries(DAY,[(a,b)],INTERNATIONAL))
        for instant in range(START-86400,START+86400,900):
            d=datetime.fromtimestamp(instant,ZoneInfo(AIRPORTS[a]['timezone'])).date().isoformat()
            assert (d,a,b) in queries
    row=segment('DEL','BOM',[23,50],[1,50],120,carrier='6E',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row,row),'DEL','BOM','2026-11-01',CONFIG['zones'])
    assert len(f)==1 and f[0]['departure']<START<f[0]['arrival']
    row=segment('DEL','JFK',[23,0],[4,30],960,carrier='AI',number='101');row[21]=[2026,11,3]
    f=parse_results(scripts(row),'DEL','JFK',DAY,INTERNATIONAL['zones'],max_duration=86400)
    assert f[0]['arrival']-f[0]['departure']==960*60
    row[11]=920
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'DEL','JFK',DAY,INTERNATIONAL['zones'],max_duration=86400)


def test_exact_flight_lowest_usd_quote_preserves_distinct_numbers():
    row=segment('COK','AGX',[8,0],[9,25],85,carrier='9I',number='505')
    other=segment('COK','AGX',[8,0],[9,25],85,carrier='9I',number='999')
    records=parse_results(scripts(row,row,other),'COK','AGX',DAY,CONFIG['zones'])
    assert len(records)==2
    quotes=cheapest_prices(scripts([offer(row,95),offer(row,80.25),offer(other,100)]),records,'USD')
    assert quotes[records[0]['id']]['amount_minor']==8025
    assert quotes[records[1]['id']]['amount_minor']==10000


def test_usd_reuse_keeps_timestamp_and_rejects_other_currency(tmp_path):
    source=tmp_path/'source';source.mkdir();cache=tmp_path/'cache'
    q=dict(date=DAY,origin='DEL',destination='LHR',captured_at='2026-10-24T23:00:00+00:00',url='https://www.google.com/travel/flights?curr=USD',status='results',flights=[])
    path=source/f'{DAY}-DEL-LHR.json';path.write_text(json.dumps(q))
    assert seed_usd_captures(cache,INTERNATIONAL,[source])==1
    assert json.loads((cache/path.name).read_text())==q
    q.update(origin='LHR',destination='DEL',url='https://www.google.com/travel/flights?curr=MYR')
    path=source/f'{DAY}-LHR-DEL.json';path.write_text(json.dumps(q))
    assert seed_usd_captures(cache,INTERNATIONAL,[source])==0
    q['url']='https://www.google.com/travel/flights?curr=USD';q['flights']=[dict(price=dict(currency='INR',amount_minor=100))];path.write_text(json.dumps(q))
    assert seed_usd_captures(cache,INTERNATIONAL,[source])==0


def test_cached_preparation_missing_queries_reproducibility_and_http(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();pairs=[('DEL','BOM'),('GAU','TEI')]
    row=segment('DEL','BOM',[23,50],[1,50],120,carrier='6E',number='123');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'DEL','BOM','2026-11-01',CONFIG['zones'])[0]
    f['price']={**CONTEXT,'amount_minor':8025,'captured_at':'2026-10-25T00:00:00+00:00'}
    q=dict(origin='DEL',destination='BOM',date='2026-11-01',status='results',captured_at='2026-10-25T00:00:00+00:00',flights=[f])
    (cache/'2026-11-01-DEL-BOM.json').write_text(json.dumps(q))
    out=tmp_path/'day.gz';prepare(cache,out,DAY,pairs,CONFIG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CONFIG)
    assert first==out.read_bytes()
    r=json.loads(gzip.decompress(first));assert len(r['metadata']['uncollected_queries'])==3
    assert r['metadata']['coverage']['routes_searched']==1 and r['metadata']['scope']=='domestic'
    monkeypatch.setenv('SUNTRAIN_INDIA_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,'india_flights');assert day['start']==START and len(day['services'])==1
    assert day['services'][0]['price']==f['price'] and day['services'][0]['flight_scope']=='domestic'
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'india_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['timezone']=='Asia/Kolkata'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


def test_scope_merge_currency_validation_and_national_endpoints(tmp_path,monkeypatch):
    domestic=tmp_path/'dom.gz';international=tmp_path/'intl.gz'
    airports=[AIRPORTS[k] for k in ['DEL','BOM','JFK','LHR']]
    f=dict(id='dom',number='6E123',carrier='6E',origin='DEL',destination='BOM',departure=START,arrival=START+7200,price={**CONTEXT,'amount_minor':10000})
    g={**f,'id':'intl','origin':'JFK','destination':'DEL','departure':START-7200,'arrival':START+36000}
    write_reference(domestic,airports,[f],dict(country='IN',scope='domestic',fare_context=CONTEXT))
    write_reference(international,airports,[g],dict(country='IN',scope='international',fare_context=CONTEXT))
    monkeypatch.setenv('SUNTRAIN_INDIA_FLIGHTS_REFERENCE',str(domestic));monkeypatch.setenv('SUNTRAIN_INDIA_INTERNATIONAL_REFERENCE',str(international))
    r=flights.load_reference(DAY,'india_flights');assert {f['flight_scope'] for f in r['flights']}=={'domestic','international'}
    assert r['metadata']['priced_flights']==2 and 'IST' in r['metadata']['replay_note']
    g['price']={**g['price'],'currency':'INR'}
    write_reference(international,airports,[g],dict(scope='international',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='no implicit conversion'):flights.load_reference(DAY,'india_flights')
    g.pop('price');g['destination']='LHR'
    write_reference(international,airports,[g],dict(scope='international',fare_context=CONTEXT))
    with pytest.raises(ValueError,match='national endpoint'):flights.load_reference(DAY,'india_flights')


def test_prepared_snapshots_report_real_coverage_and_only_usd():
    day=flights.replay_day(DAY,'india_flights');assert day['services']
    assert {'BOM','NMI','DEL','DXN','GOI','GOX','GAU','AGX','IXZ'} <= {a['code'] for a in day['stations']}
    assert len({f['id'] for f in day['services']})==len(day['services'])
    assert {f['flight_scope'] for f in day['services']}=={'domestic','international'}
    for scope,c in [('domestic',CONFIG),('international',INTERNATIONAL)]:
        coverage=day['schedule']['coverage_by_scope'][scope]
        assert coverage['queries_captured']+coverage['failed_or_missing_queries']==len(list(expected_queries(DAY,c['manifest']['routes'],c)))
    for f in day['services']:
        assert f['stops'][0][2]<day['end'] and f['stops'][1][1]>=day['start']
        if f.get('price'):assert f['price']['currency']=='USD' and f['price']['amount_minor']>0
