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


def test_regional_exact_airports_all_directions_single_date_and_no_network_expansion():
    assert list(AIR)[:30]==['ATL','DFW','ORD','DEN','LAX','JFK','MCO','LAS','MIA','SFO','CLT','SEA','PHX','EWR','IAH','BOS','MSP','DTW','LGA','FLL','PHL','IAD','SLC','SAN','BNA','BWI','TPA','DCA','AUS','HNL']
    assert [a['rank'] for a in AIR.values() if a['country']=='US']==list(range(1,31))
    assert {c for c,a in AIR.items() if a['country']=='CA'}=={'YYZ','YVR','YUL','YYC','YEG'}
    assert {c for c,a in AIR.items() if a['country']=='MX'}=={'MEX','CUN','GDL','MTY','TIJ'}
    assert set(list(AIR)[40:])=={'PTY','SJU','PUJ','SJO','SDQ','SAL','GUA','MBJ','NAS','AUA'}
    assert len(AIR)==50 and AIR['SJU']['country']=='PR' and AIR['SJU']['icao']=='TJSJ'
    assert AIR['SJO']['icao']=='MROC' and AIR['SJU']['icao']!=AIR['SJO']['icao']
    assert not {'YTZ','NLU','TLC','YOW','HAV','KIN'}&AIR.keys()
    assert AIR['JFK']['icao']=='KJFK' and AIR['ORD']['icao']=='KORD'
    assert {AIR[c]['icao'] for c in ['JFK','EWR','LGA']}=={'KJFK','KEWR','KLGA'}
    assert {AIR[c]['icao'] for c in ['IAD','DCA','BWI']}=={'KIAD','KDCA','KBWI'}
    assert not {'MDW','DAL','SNA','OAK'}&AIR.keys()
    assert len(CFG['manifest']['routes'])==2450
    assert sum(AIR[a]['country']==AIR[b]['country'] for a,b in CFG['manifest']['routes'])==912
    jurisdictions={'PR':'US'}
    assert sum(jurisdictions.get(AIR[a]['country'],AIR[a]['country'])==jurisdictions.get(AIR[b]['country'],AIR[b]['country']) for a,b in CFG['manifest']['routes'])==972
    assert set(map(tuple,CFG['manifest']['routes']))=={(a,b) for a in AIR for b in AIR if a!=b}
    queries=list(expected_queries(DAY,CFG['manifest']['routes'],CFG))
    assert len(queries)==2450 and {d for d,_,_ in queries}=={DAY}
    assert list(expected_queries(DAY,[('JFK','LAX')],CFG))==[(DAY,'JFK','LAX')]
    assert CFG['currency']=='USD' and CITIES[CITY]['flight_scopes'] and CITIES[CITY]['default_flight_scope']=='both'
    assert CITIES[CITY]['flight_country_filters'] and CITIES[CITY]['name']=='North America · Flights'
    assert CFG['capture_wait_until']=='domcontentloaded' and 'capture_wait_until' not in country_config('AU')
    assert CITY not in network.CITIES and 'US' not in network.CORE_COUNTRIES
    assert not network.enabled(DAY,CITY)
    # Existing US endpoints on Taiwan/Hong Kong international routes still load.
    assert network.load_archive()['flights']


def test_four_time_zones_post_dst_red_eye_duplicates_and_cheapest_price():
    zones=CFG['zones']
    assert len(set(zones.values()))==23
    for code,offset in [('JFK',-5),('DFW',-6),('DEN',-7),('LAX',-8)]:
        assert datetime(2026,11,2,tzinfo=ZoneInfo(zones[code])).utcoffset().total_seconds()==offset*3600
    assert zones['PHX']=='America/Phoenix' and zones['DTW']=='America/Detroit'
    assert datetime(2026,7,2,tzinfo=ZoneInfo(zones['PHX'])).utcoffset().total_seconds()==-7*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(zones['DEN'])).utcoffset().total_seconds()==-6*3600
    assert zones['HNL']=='Pacific/Honolulu'
    assert datetime(2026,7,2,tzinfo=ZoneInfo(zones['HNL'])).utcoffset().total_seconds()==-10*3600
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


def test_new_york_airports_remain_three_exact_source_identities():
    rows=scripts(*(segment(a,'BOS',[9,0],[10,0],60,carrier='UA',number='100') for a in ['JFK','EWR','LGA']))
    records=[parse_results(rows,a,'BOS',DAY,CFG['zones'])[0] for a in ['JFK','EWR','LGA']]
    assert [f['origin'] for f in records]==['JFK','EWR','LGA']
    assert len({f['id'] for f in records})==3


def test_hawaii_long_overnight_flights_source_duration_and_runtime_limit(tmp_path):
    row=segment('HNL','BOS',[14,0],[6,0],660,carrier='AS',number='100');row[21]=[2026,11,3]
    assert CFG['max_duration']==57600 and country_config('NZ')['max_duration']==28800
    with pytest.raises(ValueError,match='duration'):parse_results(scripts(row),'HNL','BOS',DAY,CFG['zones'])
    fs=parse_results(scripts(row),'HNL','BOS',DAY,CFG['zones'],max_duration=CFG['max_duration'])
    assert fs[0]['arrival']-fs[0]['departure']==11*3600
    cache=tmp_path/'cache';out=tmp_path/'day.gz';put(cache,'HNL','BOS',fs)
    prepare(cache,out,DAY,[('HNL','BOS')],CFG)
    assert load_domestic(out,'US')['flights'][0]['flight_scope']=='domestic'
    bounds=CITIES[CITY]['bounds']
    assert all(bounds[0][0]<=a['lon']<=bounds[1][0] and bounds[0][1]<=a['lat']<=bounds[1][1] for a in AIR.values())
    row[11]=600
    with pytest.raises(ValueError,match='duration'):parse_results(scripts(row),'HNL','BOS',DAY,CFG['zones'],max_duration=CFG['max_duration'])


def test_canadian_and_mexican_domestic_and_cross_border_usd(tmp_path):
    cache=tmp_path/'cache';out=tmp_path/'day.gz';pairs=[]
    examples=[('YYZ','YVR',[9,0],[12,0],300),('YYC','YYZ',[9,0],[14,0],240),
        ('MEX','CUN',[9,0],[12,0],120),('TIJ','MTY',[9,0],[14,0],180),('YYZ','MEX',[9,0],[13,0],300),('LAX','MEX',[9,0],[15,0],240)]
    for i,(a,b,d,arr,minutes) in enumerate(examples):
        row=segment(a,b,d,arr,minutes,carrier='AC',number=str(i))
        fs=parse_results(scripts(row),a,b,DAY,CFG['zones']);prices=cheapest_prices(scripts([offer(row,200),offer(row,150)]),fs,'USD')
        fs[0]['price']={**prices[fs[0]['id']],'captured_at':'2026-10-27T00:00:00Z'}
        put(cache,a,b,fs);pairs.append((a,b))
    prepare(cache,out,DAY,pairs,CFG);raw=load_domestic(out,'US')
    bypair={(f['origin'],f['destination']):f for f in raw['flights']}
    assert all(bypair[p]['flight_scope']=='domestic' for p in pairs[:4])
    assert all(bypair[p]['flight_scope']=='international' for p in pairs[4:])
    assert all(f['price']['currency']=='USD' and f['price']['amount_minor']==15000 for f in raw['flights'])
    assert raw['metadata']['countries']==CFG['manifest']['countries'] and raw['metadata']['scope']=='regional' and 'country' not in raw['metadata']
    assert raw['metadata']['coverage_by_scope']['domestic']['queries_planned']==4
    assert raw['metadata']['coverage_by_scope']['international']['queries_planned']==2
    for currency in ['CAD','MXN']:
        raw['flights'][0]['price']['currency']=currency
        with gzip.open(out,'wt') as stream:json.dump(raw,stream)
        with pytest.raises(ValueError,match='USD'):load_domestic(out,'US')


def test_frozen_canadian_rules_and_mexican_border_time_zones():
    assert AIR['YVR']['timezone']=='America/Vancouver' and CFG['zones']['YVR']=='Etc/GMT+7'
    assert AIR['YYC']['timezone']=='America/Edmonton' and CFG['zones']['YYC']=='Etc/GMT+6'
    for c,offset in [('YVR',-7),('YYC',-6),('YEG',-6),('YYZ',-5),('MEX',-6),('GDL',-6),('MTY',-6),('CUN',-5),('TIJ',-8)]:
        assert datetime(2026,11,2,tzinfo=ZoneInfo(CFG['zones'][c])).utcoffset().total_seconds()==offset*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(CFG['zones']['MEX'])).utcoffset().total_seconds()==-6*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(CFG['zones']['TIJ'])).utcoffset().total_seconds()==-7*3600
    row=segment('YVR','YYZ',[0,30],[7,30],300,carrier='AC',number='99')
    fs=parse_results(scripts(row),'YVR','YYZ',DAY,CFG['zones'])
    assert datetime.fromtimestamp(fs[0]['departure'],ZoneInfo('Etc/GMT+7')).hour==0


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
    with pytest.raises(ValueError,match='approved manifest'):prepare(cache,out,DAY,[('JFK','OAK')],CFG)


@pytest.mark.parametrize('change',[{'country':'CA'},{'timezone':'America/New_York'},{'code':'OAK'}])
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
    assert len(raw['metadata']['queries'])+len(raw['metadata']['uncollected_queries'])==2450
    assert len({f['id'] for f in raw['flights']})==len(raw['flights'])
    assert all(f['origin'] in AIR and f['destination'] in AIR for f in raw['flights'])
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(AIR[f['origin']].get('replay_timezone',AIR[f['origin']]['timezone']))).date().isoformat()==DAY for f in raw['flights'])
    replay=flights.replay_day(DAY,CITY)
    assert len(replay['services'])==len(raw['flights'])
    assert all(s['stops'][0][1]>=replay['start'] and s['stops'][1][1]<replay['end'] for s in replay['services'])


def test_atlantic_midnight_domestic_territory_scope_and_regional_clocks(tmp_path,monkeypatch):
    cache=tmp_path/'cache';out=tmp_path/'day.gz'
    examples=[('SJU','MIA',[0,30],[2,30],180),('MIA','SJU',[9,0],[13,0],180),
              ('SJU','PUJ',[9,0],[10,0],60),('SDQ','PUJ',[9,0],[9,30],30),
              ('PTY','SJO',[9,0],[9,30],90),('GUA','SAL',[9,0],[10,0],60),
              ('NAS','MBJ',[9,0],[10,0],60),('AUA','YYZ',[9,0],[13,0],300)]
    pairs=[]
    for i,(a,b,d,arr,minutes) in enumerate(examples):
        row=segment(a,b,d,arr,minutes,carrier='CM',number=str(i))
        put(cache,a,b,parse_results(scripts(row),a,b,DAY,CFG['zones']));pairs.append((a,b))
    prepare(cache,out,DAY,pairs,CFG);raw=load_domestic(out,'US')
    bypair={(f['origin'],f['destination']):f for f in raw['flights']}
    for pair in [('SJU','MIA'),('MIA','SJU'),('SDQ','PUJ')]:assert bypair[pair]['flight_scope']=='domestic'
    assert bypair['SJU','PUJ']['flight_scope']=='international'
    assert raw['metadata']['coverage_by_scope']['domestic']['queries_planned']==3
    assert raw['metadata']['coverage_by_scope']['international']['queries_planned']==5
    monkeypatch.setenv('SUNTRAIN_UNITED_STATES_FLIGHTS_REFERENCE',str(out))
    replay=flights.replay_day(DAY,CITY)
    assert datetime.fromtimestamp(replay['start'],ZoneInfo('UTC')).isoformat()=='2026-11-02T04:00:00+00:00'
    assert len(replay['services'])==8
    assert min(s['stops'][0][1] for s in replay['services'])==replay['start']+1800
    for code,offset in [('SJU',-4),('PUJ',-4),('SDQ',-4),('AUA',-4),('PTY',-5),('MBJ',-5),('NAS',-5),('SJO',-6),('SAL',-6),('GUA',-6)]:
        assert datetime(2026,11,2,tzinfo=ZoneInfo(CFG['zones'][code])).utcoffset().total_seconds()==offset*3600
    # Puerto Rico stays selectable under PR; scope follows US flight jurisdiction.
    assert next(a for a in replay['stations'] if a['code']=='SJU')['country']=='PR'
