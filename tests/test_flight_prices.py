import copy
import gzip
import json
from pathlib import Path

import pytest
from flask import Flask
from dashboard import flights,replay_http
from scripts.flight_prices import cheapest_prices,verify_fare_context
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from tests.test_google_flights import segment,scripts


def offer(row,amount,other=None):
    legs=[row] if other is None else [row,other]
    itinerary=[None]*24;itinerary[2]=legs;itinerary[3]=row[3];itinerary[6]=row[6]
    return [itinerary,[[None,amount],'booking-token']]


def test_fare_context_requires_displayed_currency_and_one_adult_economy_one_way():
    verify_fare_context('One way\n1\nEconomy\nCurrencyMYR','MYR')
    for body in ['One way\n1\nEconomy\nCurrencyUSD','One way\n2\nEconomy\nCurrencyMYR','Round trip\n1\nEconomy\nCurrencyMYR','One way\n1\nBusiness\nCurrencyMYR','One way\n1\nEconomy\nCurrencyMYRfoo']:
        with pytest.raises(ValueError,match='Unverified'):
            verify_fare_context(body,'MYR')


def test_cheapest_exact_flight_quote_ignores_page_minima_connections_and_missing_prices():
    row=segment('KUL','PEN',[10,40],[11,40],60,carrier='AK',number='6142')
    config=country_config('MY')
    f=parse_results(scripts(row),'KUL','PEN','2026-11-02',config['zones'])
    data=[offer(row,134),offer(row,120.5),offer(row,None),offer(row,0),offer(row,True),offer(row,-1),offer(row,0.001),offer(row,10,copy.deepcopy(row)),[None,1]]
    quote=cheapest_prices(scripts(data),f,'MYR')[f[0]['id']]
    assert quote['amount_minor']==12050 and quote['currency']=='MYR'
    assert quote['adults']==1 and quote['cabin']=='economy' and quote['trip_type']=='one_way'
    other=copy.deepcopy(row);other[22][1]='9999'
    assert cheapest_prices(scripts(offer(other,1)),f,'MYR')=={}
    other=copy.deepcopy(row);other[20][2]=3
    assert cheapest_prices(scripts(offer(other,1)),f,'MYR')=={}
    other=copy.deepcopy(row);other[3]='SZB'
    assert cheapest_prices(scripts(offer(other,1)),f,'MYR')=={}
    assert cheapest_prices(scripts(offer(row,None)),f,'MYR')=={}


def test_malaysia_manifest_exact_airports_east_west_zones_and_adjacent_queries():
    c=country_config('MY');a={a['code']:a for a in c['manifest']['airports']}
    assert a['KUL']['lon']!=a['SZB']['lon']
    assert a['BKI']['timezone']==a['KCH']['timezone']=='Asia/Kuching'
    assert a['KUL']['timezone']=='Asia/Kuala_Lumpur'
    assert c['capture_prices'] and c['currency']=='MYR'
    assert {'Peninsular Malaysia','Sabah & Labuan','Sarawak'}=={p['island_group'] for p in a.values()}
    for x,y in c['manifest']['routes']:
        assert a[x]['country']==a[y]['country']=='MY'
        assert [y,x] in c['manifest']['routes']
    assert set(expected_queries('2026-11-02',[('KUL','PEN')],c))=={('2026-11-01','KUL','PEN'),('2026-11-02','KUL','PEN')}


def test_previous_day_short_flight_preserves_its_own_quote(tmp_path):
    c=country_config('MY')
    row=segment('KUL','PEN',[23,50],[0,10],20,carrier='AK',number='6142');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'KUL','PEN','2026-11-01',c['zones'])[0]
    f['price']={**cheapest_prices(scripts(offer(row,134)),[f],'MYR')[f['id']],'captured_at':'2026-10-25T00:00:00+00:00'}
    cache=tmp_path/'cache';cache.mkdir()
    (cache/'2026-11-01-KUL-PEN.json').write_text(json.dumps(dict(origin='KUL',destination='PEN',date='2026-11-01',captured_at='2026-10-25T00:00:00+00:00',flights=[f],status='results')))
    out=tmp_path/'day.gz';prepare(cache,out,'2026-11-02',[('KUL','PEN')],c)
    reference=json.loads(gzip.decompress(out.read_bytes()))
    assert reference['flights']==[f]
    assert reference['metadata']['uncollected_queries']==[['2026-11-02','KUL','PEN']]
    with pytest.raises(ValueError,match='two Malaysian airports'):
        prepare(cache,out,'2026-11-02',[('KUL','SIN')],c)


def test_prepared_quotes_are_deterministic_survive_replay_and_http(tmp_path,monkeypatch):
    c=country_config('MY');cache=tmp_path/'cache';cache.mkdir()
    row=segment('KUL','PEN',[10,40],[11,40],60,carrier='AK',number='6142')
    f=parse_results(scripts(row),'KUL','PEN','2026-11-02',c['zones'])[0]
    f['price']={**cheapest_prices(scripts(offer(row,134)),[f],'MYR')[f['id']],'captured_at':'2026-10-25T00:00:00+00:00'}
    (cache/'2026-11-02-KUL-PEN.json').write_text(json.dumps(dict(origin='KUL',destination='PEN',date='2026-11-02',url='https://example.org',captured_at='2026-10-25T00:00:00+00:00',flights=[f],status='results')))
    out=tmp_path/'day.gz';prepare(cache,out,'2026-11-02',[('KUL','PEN')],c);first=out.read_bytes()
    prepare(cache,out,'2026-11-02',[('KUL','PEN')],c);assert first==out.read_bytes()
    reference=json.loads(gzip.decompress(first));assert reference['metadata']['priced_flights']==1
    monkeypatch.setenv('SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day('2026-11-02','malaysia_flights');assert day['services'][0]['price']==f['price']
    assert day['services'][0]['flight_scope']=='domestic'
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor('2026-11-02','malaysia_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    payload=json.loads(gzip.decompress(response.data));assert payload['services'][0]['price']==f['price']
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace('2026-11-02','2026-11-03')).status_code==404


def test_committed_malaysia_capture_has_exact_domestic_identities_and_fare_context():
    path=Path(__file__).resolve().parents[1]/'data/reference/malaysia_flights/2026-11-02.json.gz'
    reference=json.loads(gzip.decompress(path.read_bytes()))
    airports={a['code']:a for a in reference['airports']};records=reference['flights'];meta=reference['metadata']
    assert airports['KUL']['lon']!=airports['SZB']['lon']
    assert {a['country'] for a in airports.values()}=={'MY'}
    assert len({f['id'] for f in records})==len(records)
    assert sum('price' in f for f in records)==meta['priced_flights']>0
    assert any('price' not in f for f in records)
    assert meta['fare_context']['currency']=='MYR'
    for f in records:
        assert 60<=f['arrival']-f['departure']<=28800
        if 'price' in f:
            price=f['price']
            assert type(price['amount_minor']) is int and price['amount_minor']>0
            assert (price['currency'],price['adults'],price['cabin'],price['trip_type'])==('MYR',1,'economy','one_way')
            assert price['captured_at']
