"""Hub identities, query ownership, USD quotes, timezone boundaries and replay caching."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import json

import pytest
from flask import Flask
from dashboard import flights,gulf_flights,replay_http
from scripts.prepare_gulf_airports import HUBS,pair_owner
from scripts.prepare_gulf_flights import gulf_config,ordered_pairs,prepare_all
from scripts.prepare_google_flights import expected_queries,query_path,prepare
from scripts.flight_prices import cheapest_prices,verify_fare_context
from tests.test_flight_prices import offer
from tests.test_google_flights import segment,scripts
from scripts.prepare_google_flights import parse_results
from tests.test_indonesian_international_flights import write_reference

CONFIG=gulf_config()
AIRPORTS={a['code']:a for a in CONFIG['manifest']['airports']}
START=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Dubai')).timestamp())
PRICE=dict(amount_minor=15000,currency='USD',adults=1,cabin='economy',trip_type='one_way',captured_at='2026-10-25T00:00:00+00:00')


def flight(origin='DXB',destination='SIN',identity='flight',amount=15000):
    return dict(id=identity,carrier='EK',number='EK1',airline='Emirates',origin=origin,destination=destination,
        departure=START+3600,arrival=START+7200,price={**PRICE,'amount_minor':amount})


def test_exact_hubs_current_iata_codes_and_verified_airport_zones():
    assert AIRPORTS['DXB']['country']==AIRPORTS['AUH']['country']=='AE'
    assert AIRPORTS['DOH']['country']=='QA'
    assert AIRPORTS['DXB']['timezone']==AIRPORTS['AUH']['timezone']=='Asia/Dubai'
    assert AIRPORTS['DOH']['timezone']=='Asia/Qatar'
    assert AIRPORTS['DXB']['lon']!=AIRPORTS['AUH']['lon']
    assert AIRPORTS['BSZ']['icao']=='UCFM' and AIRPORTS['BSZ']['timezone']=='Asia/Bishkek'
    assert 'FRU' not in AIRPORTS
    assert AIRPORTS['LAX']['timezone']=='America/Los_Angeles'
    assert AIRPORTS['JFK']['timezone']=='America/New_York'
    assert AIRPORTS['AKL']['timezone']=='Pacific/Auckland'
    assert all(ZoneInfo(a['timezone']) for a in AIRPORTS.values())
    assert not CONFIG['manifest']['unresolved_airports']
    assert CONFIG['currency']=='USD'


def test_inter_hub_queries_have_one_owner_and_round_robin_covers_all_three():
    routes=CONFIG['manifest']['routes'];pairs=ordered_pairs(CONFIG)
    assert len(set(pairs))==len(routes)
    assert pairs[:3]==[('DXB','SIN'),('AUH','SIN'),('DOH','SIN')]
    assert pair_owner('DOH','DXB')==pair_owner('DXB','DOH')=='DXB'
    assert pair_owner('AUH','DOH')==pair_owner('DOH','AUH')=='AUH'
    for a,b in routes:
        assert a in HUBS or b in HUBS
        assert [b,a] in routes
        assert pair_owner(a,b)==pair_owner(b,a)
    assert query_path(Path('/tmp'), '2026-11-02','DOH','DXB',CONFIG)==Path('/tmp/DXB/2026-11-02-DOH-DXB.json')
    with pytest.raises(ValueError,match='selected hub'):
        query_path(Path('/tmp'),'2026-11-02','LHR','JFK',CONFIG)


def test_adjacent_origin_dates_and_one_hour_hub_difference():
    pairs=[('LAX','DXB'),('DXB','LAX'),('AKL','DOH'),('DOH','AUH')]
    queries=set(expected_queries('2026-11-02',pairs,CONFIG))
    for a,b in pairs:
        for at in range(START-86400,START+86400,900):
            local=datetime.fromtimestamp(at,ZoneInfo(CONFIG['zones'][a])).date().isoformat()
            assert (local,a,b) in queries
    assert datetime.fromtimestamp(START,ZoneInfo('Asia/Dubai')).strftime('%Y-%m-%d %H:%M')=='2026-11-02 00:00'
    assert datetime.fromtimestamp(START,ZoneInfo('Asia/Qatar')).strftime('%Y-%m-%d %H:%M')=='2026-11-01 23:00'


def test_usd_source_context_and_cheapest_quote_for_exact_inter_hub_flight():
    verify_fare_context('One way\n1\nEconomy\nCurrencyUSD','USD')
    with pytest.raises(ValueError,match='Unverified'):
        verify_fare_context('One way\n1\nEconomy\nCurrencyMYR','USD')
    row=segment('DXB','DOH',[10,0],[10,15],75,carrier='QR',number='1003')
    records=parse_results(scripts(row),'DXB','DOH','2026-11-02',CONFIG['zones'])
    assert records[0]['arrival']-records[0]['departure']==4500
    quote=cheapest_prices(scripts([offer(row,230),offer(row,199.5)]),records,'USD')[records[0]['id']]
    assert quote['currency']=='USD' and quote['amount_minor']==19950


def test_merged_inter_hub_flight_is_counted_once_with_cheapest_same_currency_quote(tmp_path,monkeypatch):
    a=flight('DXB','DOH','shared',20000);b=flight('DXB','DOH','shared',15000)
    metadata=dict(source_date='2026-10-25',fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way'))
    write_reference(tmp_path/'2026-11-02-DXB.json.gz',[AIRPORTS['DXB'],AIRPORTS['DOH']],[a],metadata)
    write_reference(tmp_path/'2026-11-02-AUH.json.gz',[AIRPORTS['AUH'],AIRPORTS['SIN']],[flight('AUH','SIN','auh')],metadata)
    marketing={**b,'id':'different-number','carrier':'AA','number':'AA8112'}
    write_reference(tmp_path/'2026-11-02-DOH.json.gz',[AIRPORTS['DXB'],AIRPORTS['DOH']],[b,marketing],metadata)
    monkeypatch.setenv('SUNTRAIN_GULF_FLIGHTS_DIRECTORY',str(tmp_path))
    r=gulf_flights.load_reference('2026-11-02')
    assert len(r['flights'])==3  # Different flight numbers stay distinct despite matching times.
    assert next(f for f in r['flights'] if f['id']=='shared')['price']['amount_minor']==15000
    assert r['metadata']['coverage_by_hub']['DXB']['flights']==r['metadata']['coverage_by_hub']['DOH']['flights']==2
    b['price']['currency']='MYR'
    write_reference(tmp_path/'2026-11-02-DOH.json.gz',[AIRPORTS['DXB'],AIRPORTS['DOH']],[b],metadata)
    with pytest.raises(ValueError,match='no implicit conversion'):gulf_flights.load_reference('2026-11-02')
    b['price']['currency']='USD';b['arrival']+=60
    write_reference(tmp_path/'2026-11-02-DOH.json.gz',[AIRPORTS['DXB'],AIRPORTS['DOH']],[b],metadata)
    with pytest.raises(ValueError,match='Conflicting Gulf flight'):gulf_flights.load_reference('2026-11-02')


def test_cached_shards_reproduce_prices_and_http_revision_tracks_every_hub(tmp_path,monkeypatch):
    cache=tmp_path/'cache';out=tmp_path/'out'
    for hub in HUBS:
        f=flight(hub,'SIN',hub)
        path=query_path(cache,'2026-11-02',hub,'SIN',CONFIG);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(origin=hub,destination='SIN',date='2026-11-02',captured_at='2026-10-25T00:00:00+00:00',status='results',flights=[f])))
    assert prepare_all(cache,out,CONFIG)==HUBS
    original={p.name:p.read_bytes() for p in out.glob('*.gz')}
    prepare_all(cache,out,CONFIG)
    assert original=={p.name:p.read_bytes() for p in out.glob('*.gz')}
    monkeypatch.setenv('SUNTRAIN_GULF_FLIGHTS_DIRECTORY',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day('2026-11-02','gulf_flights')
    assert len(day['services'])==3 and day['flight_hubs']==HUBS and day['timezone']=='Asia/Dubai'
    assert day['schedule']['coverage']['queries_captured']==3
    assert all(s['price']['currency']=='USD' for s in day['services'])
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    info=replay_http.descriptor('2026-11-02','gulf_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    payload=json.loads(gzip.decompress(response.data));assert len(payload['services'])==3
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace('2026-11-02','2026-11-03')).status_code==404
    p=out/'2026-11-02-DOH.json.gz';r=json.loads(gzip.decompress(p.read_bytes()));r['flights'][0]['price']['amount_minor']=14000
    with gzip.open(p,'wt') as stream:json.dump(r,stream)
    assert replay_http.descriptor('2026-11-02','gulf_flights')['revision']!=info['revision']
    with pytest.raises(ValueError,match='selected hub'):
        prepare(cache,out/'bad.gz','2026-11-02',[('LHR','JFK')],CONFIG)


def test_committed_captures_keep_hub_endpoints_exact_and_all_fares_in_usd():
    day=flights.replay_day('2026-11-02','gulf_flights');services=day['services']
    assert len({s['id'] for s in services})==len(services)>0
    assert day['schedule']['coverage']['queries_planned']==len(list(expected_queries('2026-11-02',ordered_pairs(CONFIG),CONFIG)))
    for hub in HUBS:
        assert any(any(day['stations'][stop[0]]['code']==hub for stop in s['stops']) for s in services)
    for s in services:
        codes=[day['stations'][stop[0]]['code'] for stop in s['stops']]
        assert set(codes)&set(HUBS)
        assert s['stops'][0][2]<day['end'] and s['stops'][1][1]>=day['start']
        if 'price' in s:
            assert s['price']['currency']=='USD' and type(s['price']['amount_minor']) is int and s['price']['amount_minor']>0
