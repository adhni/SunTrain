"""Europe's explicit brands, regional membership, EUR fares and replay contract."""
from datetime import datetime
import gzip,json
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from flask import Flask
from dashboard import europe_flights as e,flights,replay_http
from dashboard.cities import CITIES
from scripts.prepare_europe_flights import CONTEXT,config,prepare,seed_pilot
from scripts.prepare_google_flights import parse_results
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
DAY=e.DAY;CFG=config();AIR={a['code']:a for a in CFG['manifest']['airports']};START=int(datetime(2026,11,2,tzinfo=ZoneInfo('UTC')).timestamp())


def put(cache,key,fs):
 cache.mkdir(parents=True,exist_ok=True);q=dict(date=key[0],origin=key[1],destination=key[2],flights=fs,status='results' if fs else 'no_matching_direct_flights',url='https://www.google.com/travel/flights?curr=EUR',captured_at='2026-10-26T00:00:00Z',page_sha256='test',capture_context=CONTEXT)
 (cache/('-'.join(key)+'.json')).write_text(json.dumps(q))


def small_config():
 pairs=[['STN','DUB'],['STN','BFS'],['LGW','BCN'],['BSL','NCE']];m={**CFG['manifest'],'routes':pairs};keys=[(DAY,*p) for p in pairs]
 return {**CFG,'manifest':m,'queries':keys}


def fixture(tmp_path,monkeypatch):
 cfg=small_config();cache=tmp_path/'cache';out=tmp_path/'europe.gz'
 for a,b,carrier,n in [('STN','DUB','FR','1'),('STN','BFS','RK','2'),('LGW','BCN','U2','3'),('BSL','NCE','DS','4')]:
  fs=[dict(id=f'{DAY}:{carrier}{n}:{a}:{b}',number=carrier+n,carrier=carrier,airline='Original source airline',origin=a,destination=b,departure=START+3600,arrival=START+7200,source_date=DAY,price=dict(amount_minor=1299,currency='EUR',adults=1,cabin='economy',trip_type='one_way',captured_at='2026-10-26T00:00:00Z'))]
  if a=='LGW':fs.append({**fs[0],'id':'other','carrier':'VY','number':'VY9'})
  put(cache,(DAY,a,b),fs)
 prepare(cache,out,cfg);monkeypatch.setenv('SUNTRAIN_EUROPE_FLIGHTS_REFERENCE',str(out));return cfg,cache,out


def test_broad_starter_uses_exact_airports_explicit_membership_and_adjacent_dates():
 m=CFG['manifest'];assert len(m['routes'])==306 and len(AIR)==84 and len(CFG['queries'])==744
 assert {'STN','LTN','LGW','CDG','ORY','BVA','FCO','CIA','MXP','LIN','BGY'}<=AIR.keys()
 assert AIR['STN']['icao']!=AIR['LTN']['icao'] and AIR['BSL']['country']=='FR'
 assert AIR['GVA']['country']=='CH' and AIR['RAK']['europe'] is False and AIR['STN']['europe'] is True
 assert AIR['TFS']['timezone']=='Atlantic/Canary' if 'TFS' in AIR else True
 assert all(AIR[a]['europe'] or AIR[b]['europe'] for a,b in m['routes'])
 assert ('2026-11-01','BGY','CTA') in CFG['queries'] and ('2026-11-03','BGY','CTA') in CFG['queries']
 assert CITIES['europe_flights']['default_flight_scope']=='both' and CITIES['europe_flights']['timezone']=='UTC'
 assert CITIES['europe_flights']['flight_country_filters']


def test_source_codes_are_not_inferred_from_names_and_quotes_use_exact_eur_flight():
 assert e.CARRIERS['FR']==e.CARRIERS['RK']==e.CARRIERS['AL']==e.CARRIERS['RR']=='ryanair'
 assert e.CARRIERS['U2']==e.CARRIERS['DS']==e.CARRIERS['EC']=='easyjet'
 assert 'VY' not in e.CARRIERS
 row=segment('STN','DUB',[23,30],[0,45],75,carrier='FR',number='1');row[20]=[2026,11,1]
 fs=parse_results(scripts(row,row),'STN','DUB','2026-11-01',CFG['zones']);assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
 assert cheapest_prices(scripts([offer(row,30),offer(row,12.99)]),fs,'EUR')[fs[0]['id']]['amount_minor']==1299
 # Europe's autumn DST boundary: Dublin and Milan differ by one hour.
 row=segment('STN','BGY',[10,0],[12,50],110,carrier='FR',number='2');row[20]=row[21]=[2026,10,25]
 assert len(parse_results(scripts(row),'STN','BGY','2026-10-25',CFG['zones']))==1


def test_prepare_filters_competitors_preserves_source_and_counts_scopes(tmp_path,monkeypatch):
 cfg,cache,out=fixture(tmp_path,monkeypatch);first=out.read_bytes();prepare(cache,out,cfg);assert out.read_bytes()==first
 r=e.load_reference(DAY);assert len(r['flights'])==4 and {f['carrier'] for f in r['flights']}=={'FR','RK','U2','DS'}
 assert all(f['airline']=='Original source airline' for f in r['flights'])
 assert next(f for f in r['flights'] if f['carrier']=='RK')['flight_scope']=='domestic'
 assert next(f for f in r['flights'] if f['carrier']=='DS')['flight_scope']=='domestic','BSL is physically in France'
 assert r['metadata']['coverage_by_scope']['domestic']['queries_planned']==2
 assert r['metadata']['coverage']['flights']==sum(v['flights'] for v in r['metadata']['coverage_by_brand'].values())
 assert next(q for q in r['metadata']['queries'] if q['origin']=='LGW')['other_carrier_records']==1


def test_other_carriers_empty_and_missing_are_distinct(tmp_path,monkeypatch):
 cfg,cache,out=fixture(tmp_path,monkeypatch);cfg={**cfg,'manifest':{**cfg['manifest'],'routes':cfg['manifest']['routes']+[['DUB','STN']]},'queries':cfg['queries']+[(DAY,'DUB','STN')]}
 put(cache,(DAY,'STN','DUB'),[])
 q=json.loads((cache/f'{DAY}-LGW-BCN.json').read_text());put(cache,(DAY,'LGW','BCN'),[f for f in q['flights'] if f['carrier']=='VY'])
 prepare(cache,out,cfg);r=e.load_reference(DAY);qs=r['metadata']['queries'];assert next(q for q in qs if q['origin']=='STN' and q['destination']=='DUB')['target_status']=='not_returned';assert next(q for q in qs if q['origin']=='LGW')['target_status']=='only_other_carriers'
 assert r['metadata']['uncollected_queries']==[[DAY,'DUB','STN']]


@pytest.mark.parametrize('mutation',['brand','member','currency','scope','duplicate','context'])
def test_runtime_rejects_wrong_region_brand_fare_scope_or_duplicate(tmp_path,monkeypatch,mutation):
 _,_,out=fixture(tmp_path,monkeypatch);r=e.load_reference(DAY)
 if mutation=='brand':r['flights'][0]['carrier']='VY'
 if mutation=='member':r['airports'][0]['europe']=not r['airports'][0]['europe']
 if mutation=='currency':r['flights'][0]['price']['currency']='ZZZ'
 if mutation=='scope':r['flights'][0]['flight_scope']='wrong'
 if mutation=='duplicate':r['flights'].append(r['flights'][0])
 if mutation=='context':r['metadata']['fare_context']['currency']='USD'
 with gzip.open(out,'wt') as f:json.dump(r,f)
 with pytest.raises(ValueError):e.load_reference(DAY)


def test_cache_identity_http_revision_date_rejection_and_existing_network_isolation(tmp_path,monkeypatch):
 cfg,cache,out=fixture(tmp_path,monkeypatch);monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'));day=flights.replay_day(DAY,'europe_flights')
 assert day['timezone']=='UTC' and day['start']==START and day['flight_brands']==e.BRANDS
 assert {s['flight_brand'] for s in day['services']}==set(e.BRANDS)
 assert flights.reference_paths(DAY,'europe_flights')==[out]
 app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'europe_flights');response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
 assert response.status_code==200 and json.loads(gzip.decompress(response.data))['city']=='europe_flights'
 assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
 assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
 out.write_bytes(out.read_bytes()+b' ');assert replay_http.descriptor(DAY,'europe_flights')['url']!=info['url']
 q=cache/f'{DAY}-STN-DUB.json';d=json.loads(q.read_text());d['capture_context']={**CONTEXT,'currency':'USD'};q.write_text(json.dumps(d))
 with pytest.raises(ValueError,match='context'):prepare(cache,out,cfg)


def test_prepared_europe_both_brands_scopes_and_clean_source_identity():
 r=e.load_reference(DAY);assert r['flights'] and {f['brand'] for f in r['flights']}==set(e.BRANDS)
 assert {f['flight_scope'] for f in r['flights']}=={'domestic','international'}
 assert not r['metadata']['uncollected_queries'] and len({f['id'] for f in r['flights']})==len(r['flights'])
