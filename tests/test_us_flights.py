"""Bounded US airport identity, local-day ownership and unchanged shared networks."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, international_network as network, replay_http
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from tests.test_google_flights import segment, scripts
from tests.test_flight_prices import offer
from scripts.flight_prices import cheapest_prices

DAY='2026-11-02'
CITY='united_states_flights'
CFG=country_config('US')
AIR={a['code']:a for a in CFG['manifest']['airports']}


def put(cache, origin, destination, records):
    cache.mkdir(exist_ok=True)
    query=dict(origin=origin,destination=destination,date=DAY,captured_at='2026-10-27T00:00:00+00:00',
        status='results' if records else 'no_matching_direct_flights',flights=records,url='https://www.google.com/travel/flights?curr=USD')
    (cache/f'{DAY}-{origin}-{destination}.json').write_text(json.dumps(query))


def test_top_ten_exact_airports_all_directions_single_date_and_no_network_expansion():
    assert list(AIR)==['ATL','DFW','ORD','DEN','LAX','JFK','MCO','LAS','MIA','SFO']
    assert [a['rank'] for a in AIR.values()]==list(range(1,11))
    assert AIR['JFK']['icao']=='KJFK' and AIR['ORD']['icao']=='KORD'
    assert not {'EWR','LGA','MDW','DAL','SNA','OAK'}&AIR.keys()
    assert len(CFG['manifest']['routes'])==90
    assert set(map(tuple,CFG['manifest']['routes']))=={(a,b) for a in AIR for b in AIR if a!=b}
    queries=list(expected_queries(DAY,CFG['manifest']['routes'],CFG))
    assert len(queries)==90 and {d for d,_,_ in queries}=={DAY}
    assert list(expected_queries(DAY,[('JFK','LAX')],CFG))==[(DAY,'JFK','LAX')]
    assert CFG['currency']=='USD' and not CITIES[CITY]['flight_scopes']
    assert CFG['capture_wait_until']=='domcontentloaded' and 'capture_wait_until' not in country_config('AU')
    assert CITY not in network.CITIES and 'US' not in network.CORE_COUNTRIES
    assert not network.enabled(DAY,CITY)
    # Existing US endpoints on Taiwan/Hong Kong international routes still load.
    assert network.load_archive()['flights']


def test_four_time_zones_post_dst_red_eye_duplicates_and_cheapest_price():
    zones=CFG['zones']
    assert len(set(zones.values()))==4
    for code,offset in [('JFK',-5),('DFW',-6),('DEN',-7),('LAX',-8)]:
        assert datetime(2026,11,2,tzinfo=ZoneInfo(zones[code])).utcoffset().total_seconds()==offset*3600
    row=segment('LAX','JFK',[23,30],[7,45],315,carrier='B6',number='100')
    row[21]=[2026,11,3]
    fs=parse_results(scripts(row,row),'LAX','JFK',DAY,zones)
    assert len(fs)==1 and datetime.fromtimestamp(fs[0]['departure'],ZoneInfo('America/New_York')).date().isoformat()=='2026-11-03'
    prices=cheapest_prices(scripts([offer(row,230),offer(row,199.50)]),fs,'USD')
    assert prices[fs[0]['id']]['amount_minor']==19950
    other=segment('LAX','JFK',[23,30],[7,45],315,carrier='AA',number='101');other[21]=[2026,11,3]
    assert len(parse_results(scripts(row,other),'LAX','JFK',DAY,zones))==2
    with pytest.raises(ValueError,match='duration'):
        parse_results(scripts(row),'LAX','JFK',DAY,{**zones,'LAX':'America/New_York'})


def test_late_west_coast_and_early_east_coast_both_replay_all_arrivals_http_and_reproducibility(tmp_path,monkeypatch):
    cache=tmp_path/'cache';out=tmp_path/'day.gz'
    late=segment('LAX','JFK',[23,30],[7,45],315,carrier='B6',number='100');late[21]=[2026,11,3]
    early=segment('JFK','LAX',[0,30],[3,0],330,carrier='AA',number='101')
    for row,a,b in [(late,'LAX','JFK'),(early,'JFK','LAX')]:put(cache,a,b,parse_results(scripts(row),a,b,DAY,CFG['zones']))
    pairs=[('LAX','JFK'),('JFK','LAX'),('MIA','SFO')]
    prepare(cache,out,DAY,pairs,CFG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CFG)
    assert out.read_bytes()==first
    raw=json.loads(gzip.decompress(first))
    assert len(raw['flights'])==2 and raw['metadata']['uncollected_queries']==[[DAY,'MIA','SFO']]
    assert raw['metadata']['query_date_policy']=='origin_local_departure_day_only'
    assert raw['metadata']['coverage']['failed_or_missing_queries']==1
    monkeypatch.setenv('SUNTRAIN_UNITED_STATES_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(DAY,CITY)
    assert len(day['services'])==2 and day['end']-day['start']>27*3600
    assert min(s['stops'][0][1] for s in day['services'])>=day['start']
    assert max(s['stops'][1][1] for s in day['services'])<day['end']
    assert all(-180<=p[0]<=0 for path in day['paths'].values() for p in path['coordinates'])
    assert flights.reference_paths(DAY,CITY)==[out]
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,CITY)
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='America/New_York'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
    with pytest.raises(ValueError,match='approved manifest'):prepare(cache,out,DAY,[('JFK','EWR')],CFG)


@pytest.mark.parametrize('change',[{'country':'CA'},{'timezone':'America/New_York'},{'code':'EWR'}])
def test_wrong_country_zone_or_unselected_airport_rejected(tmp_path,change):
    raw=dict(metadata=dict(fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')),
        airports=[{**AIR['LAX'],**change}],flights=[])
    p=tmp_path/'bad.gz'
    with gzip.open(p,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='national identities'):load_domestic(p,'US')


def test_empty_and_failed_queries_are_distinct_and_wrong_cache_identity_rejected(tmp_path):
    cache=tmp_path/'cache';out=tmp_path/'day.gz'
    put(cache,'MIA','SFO',[])
    (cache/f'{DAY}-LAX-JFK.error.json').write_text(json.dumps(dict(date=DAY,origin='LAX',destination='JFK',error='Network timeout')))
    prepare(cache,out,DAY,[('MIA','SFO'),('LAX','JFK')],CFG)
    raw=json.loads(gzip.decompress(out.read_bytes()));coverage=raw['metadata']['coverage']
    assert coverage['queries_not_returned']==1 and coverage['failed_queries']==1 and coverage['unattempted_queries']==0
    assert raw['metadata']['uncollected_queries']==[[DAY,'LAX','JFK']]
    p=cache/f'{DAY}-MIA-SFO.json';q=json.loads(p.read_text());q['destination']='OAK';p.write_text(json.dumps(q))
    with pytest.raises(ValueError,match='identity'):prepare(cache,out,DAY,[('MIA','SFO')],CFG)


def test_prepared_snapshot_matches_bounded_search_plan():
    path=flights.reference_path(DAY,CITY)
    if not path.exists():pytest.skip('US capture in progress')
    with gzip.open(path,'rt') as stream:raw=json.load(stream)
    assert len(raw['metadata']['queries'])+len(raw['metadata']['uncollected_queries'])==90
    assert len({f['id'] for f in raw['flights']})==len(raw['flights'])
    assert all(f['origin'] in AIR and f['destination'] in AIR for f in raw['flights'])
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(AIR[f['origin']]['timezone'])).date().isoformat()==DAY for f in raw['flights'])
    replay=flights.replay_day(DAY,CITY)
    assert len(replay['services'])==len(raw['flights'])
    assert all(s['stops'][0][1]>=replay['start'] and s['stops'][1][1]<replay['end'] for s in replay['services'])
