"""Worldwide scope, exact Taiwan/HK identities and DST/UTC ownership."""
from datetime import datetime
import gzip,json
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from flask import Flask
from dashboard import flights,international_network as n,replay_http
world=n
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.prepare_taiwan_hong_kong_flights import config
from scripts.prepare_international_network import config as shared_config,prepare as prepare_world
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_international_network import put,query,quote
DAY=n.DAY;DOM=country_config('TW');AIR={a['code']:a for a in DOM['manifest']['airports']};START=n.window('Asia/Taipei')[0]


def small_config():
 cfg=config();pairs=[['TPE','SFO'],['SFO','TPE'],['HKG','LHR'],['LHR','HKG'],['TPE','HKG'],['HKG','TPE']];codes={c for p in pairs for c in p}
 m={**cfg['manifest'],'routes':pairs,'airports':[a for a in cfg['manifest']['airports'] if a['code'] in codes]}
 views={city:n.consumer_queries(m,city) for city in ['taiwan_flights','hong_kong_flights']}
 return {**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}


def make_world(tmp_path,monkeypatch):
 cfg=small_config();cache=tmp_path/'cache';p=tmp_path/'world.gz'
 fs=[]
 for a,b,num in [('TPE','SFO','CI1'),('HKG','LHR','CX1'),('HKG','TPE','CX2')]:
  f=dict(id=num,number=num,carrier=num[:2],airline='Test',origin=a,destination=b,departure=START+3600,arrival=START+7200,source_date=DAY,price=quote('MYR'))
  fs.append(f);put(cache,query(f))
 prepare_world(cache,p,cfg);monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(p))
 return cfg,cache,p,fs


def test_worldwide_inventory_is_not_restricted_to_old_network_and_keeps_exact_airports():
 cfg=config();m=cfg['manifest'];air={a['code']:a for a in m['airports']}
 assert len(m['routes'])==690 and len(air)==203 and len(cfg['queries'])==2260
 assert {'TPE','TSA','KHH','RMQ','HUN','TNN','HKG','LHR','LAX','SFO','JFK','JNB','ADD','NAN','GUM','MFM'}<=air.keys()
 assert air['TPE']['icao']=='RCTP' and air['TSA']['icao']=='RCSS'
 assert air['HKG']['icao']=='VHHH' and air['MYJ']['country']=='JP'
 assert ['HKG','ALA'] not in m['routes'] and ['HKG','EHU'] not in m['routes']
 assert ['TPE','SFO'] in m['routes'] and ['HKG','LHR'] in m['routes']
 shared=shared_config()['manifest'];bycode={a['code']:a for a in shared['airports']}
 assert ['HKG','LHR'] in shared['routes'] and ['TPE','SFO'] in shared['routes']
 assert ['AUH','LHR'] not in shared['routes'] and ['MEL','LAX'] not in shared['routes']
 assert ['HKG','TPE'] in shared['routes'] and all(a['country'] in n.COUNTRIES for a in bycode.values())
 assert CITIES['taiwan_flights']['flight_scopes'] and not CITIES['hong_kong_flights']['flight_scopes']
 assert CITIES['hong_kong_flights']['default_flight_scope']=='both'
 assert 'worldwide' in CITIES['taiwan_flights']['description']
 assert 'worldwide' in CITIES['hong_kong_flights']['description'].lower()


def test_taiwan_domestic_islands_do_not_substitute_taoyuan_for_songshan():
 assert len(AIR)==13 and len(DOM['manifest']['routes'])==40
 assert 'TSA' in AIR and 'TPE' not in AIR and {'LZN','MFK','KNH','MZG','GNI','KYD'}<=AIR.keys()
 assert AIR['LZN']['icao']!=AIR['MFK']['icao'] and all(a['timezone']=='Asia/Taipei' and a['country']=='TW' for a in AIR.values())
 assert set(expected_queries(DAY,[('TSA','KNH')],DOM))=={('2026-11-01','TSA','KNH'),(DAY,'TSA','KNH')}
 assert START==int(datetime(2026,11,1,16,tzinfo=ZoneInfo('UTC')).timestamp())
 with pytest.raises(ValueError,match='worldwide'):country_config('HK')


def test_date_line_overnight_short_duration_and_cheapest_exact_usd_quote():
 cfg=config();row=segment('SFO','TPE',[23,30],[4,30],14*60,carrier='CI',number='1');row[20]=[2026,10,31];row[21]=[2026,11,2]
 fs=parse_results(scripts(row,row),'SFO','TPE','2026-10-31',cfg['zones'],max_duration=86400)
 assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
 offers=cheapest_prices(scripts([offer(row,950),offer(row,800)]),fs,'USD');assert offers[fs[0]['id']]['amount_minor']==80000
 short=segment('TSA','MZG',[9,0],[9,50],50,carrier='B7',number='1')
 assert len(parse_results(scripts(short),'TSA','MZG',DAY,DOM['zones']))==1


def test_repeated_us_clock_hour_uses_source_duration_and_never_guesses():
 cfg=config();row=segment('SFO','TPE',[1,30],[7,30],14*60,carrier='CI',number='2');row[20]=[2026,11,1];row[21]=[2026,11,2]
 fs=parse_results(scripts(row),'SFO','TPE','2026-11-01',cfg['zones'],max_duration=86400)
 assert len(fs)==1 and fs[0]['departure']==int(datetime(2026,11,1,1,30,tzinfo=ZoneInfo('America/Los_Angeles'),fold=1).timestamp())
 ambiguous=segment('SFO','LAX',[1,0],[1,40],40);ambiguous[20]=ambiguous[21]=[2026,11,1]
 with pytest.raises(ValueError,match='Ambiguous'):parse_results(scripts(ambiguous),'SFO','LAX','2026-11-01',cfg['zones'])
 spring=segment('SFO','TPE',[2,30],[7,30],14*60);spring[20]=[2026,3,8];spring[21]=[2026,3,9]
 with pytest.raises(ValueError,match='Nonexistent'):parse_results(scripts(spring),'SFO','TPE','2026-03-08',cfg['zones'],max_duration=86400)


def test_world_fixture_retains_foreign_countries_original_fares_and_missing_queries(tmp_path,monkeypatch):
 cfg,cache,p,fs=make_world(tmp_path,monkeypatch);first=p.read_bytes();prepare_world(cache,p,cfg);assert first==p.read_bytes()
 raw=world.load_archive();hk=n.project(raw,'hong_kong_flights');tw=n.project(raw,'taiwan_flights')
 assert {f['origin'] for f in hk['flights']}=={'HKG'} and any(f['destination']=='LHR' for f in hk['flights'])
 assert any(f['destination']=='SFO' for f in tw['flights']) and all(f['price']['currency']=='MYR' for f in tw['flights'])
 assert tw['metadata']['coverage']['failed_or_missing_queries']>0
 assert all('HKG' in (f['origin'],f['destination']) for f in hk['flights'])


@pytest.mark.parametrize('mutation',['currency','zone','endpoint'])
def test_world_archive_rejects_wrong_context_zone_unrelated_flight_and_conflicts(tmp_path,monkeypatch,mutation):
 _,_,p,_=make_world(tmp_path,monkeypatch);raw=world.load_archive()
 if mutation=='currency':raw['flights'][0]['price']['currency']='HKD'
 if mutation=='zone':next(a for a in raw['airports'] if a['code']=='TPE')['timezone']='Asia/Tokyo'
 if mutation=='endpoint':raw['flights'][0].update(origin='SFO',destination='LHR')
 with gzip.open(p,'wt') as stream:json.dump(raw,stream)
 with pytest.raises(ValueError):world.load_archive()


def test_country_loading_http_cache_and_custom_domestic_isolation(tmp_path,monkeypatch):
 _,_,p,_=make_world(tmp_path,monkeypatch);cache=tmp_path/'dom';f=parse_results(scripts(segment('TSA','KNH',[9,0],[10,0],60,carrier='B7',number='1')),'TSA','KNH',DAY,DOM['zones'])[0];put(cache,query(f));out=tmp_path/'dom.gz';prepare(cache,out,DAY,[('TSA','KNH')],DOM)
 monkeypatch.setenv('SUNTRAIN_TAIWAN_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
 tw=flights.load_reference(DAY,'taiwan_flights');hk=flights.load_reference(DAY,'hong_kong_flights')
 assert {f['flight_scope'] for f in tw['flights']}=={'domestic','international'}
 assert any(f['destination']=='SFO' for f in tw['flights']) and any(f['destination']=='LHR' for f in hk['flights'])
 assert flights.reference_paths(DAY,'taiwan_flights')==[out,p]
 assert flights.reference_paths(DAY,'hong_kong_flights')==[p]
 app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();desc=replay_http.descriptor(DAY,'taiwan_flights');response=client.get(desc['url'],headers={'Accept-Encoding':'gzip'})
 assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Asia/Taipei'
 assert client.get(desc['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
 assert client.get(desc['url'].replace(DAY,'2026-11-03')).status_code==404
 monkeypatch.delenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE')
 assert flights.reference_paths(DAY,'taiwan_flights')==[out]
 assert {f['flight_scope'] for f in flights.load_reference(DAY,'taiwan_flights')['flights']}=={'domestic'}


def test_prepared_worldwide_views_are_not_limited_to_shared_countries():
 raw=world.load_archive()
 assert {'taiwan_flights','hong_kong_flights'}<=raw['metadata']['queries_by_view'].keys()
 for city,country in [('taiwan_flights','TW'),('hong_kong_flights','HK')]:
  r=flights.load_reference(DAY,city);air={a['code']:a for a in r['airports']}
  intl=[f for f in r['flights'] if f['flight_scope']=='international']
  assert intl and any(air[f['destination']]['country']=='US' or air[f['origin']]['country']=='US' for f in intl)
  assert any(air[f['destination']]['country'] in {'GB','FR','DE','NL'} or air[f['origin']]['country'] in {'GB','FR','DE','NL'} for f in intl)
  assert all(country in {air[f['origin']]['country'],air[f['destination']]['country']} for f in intl)
  projected=n.project(raw,city);byid={f['id']:f for f in intl};assert all(byid[f['id']]==f for f in projected['flights'])


def test_access_challenge_publishes_saved_records_and_failed_query_diagnostics_once(tmp_path,monkeypatch):
 from scripts import prepare_taiwan_hong_kong_flights as collector
 cfg,cache,_,_=make_world(tmp_path,monkeypatch);key=next(q for q in cfg['queries'] if not (cache/('-'.join(q)+'.json')).exists())
 (cache/('-'.join(key)+'.error.json')).write_text(json.dumps(dict(date=key[0],origin=key[1],destination=key[2],error='Readiness timeout')))
 calls=[]
 async def stop(*args,**kwargs):calls.append(1);raise RuntimeError('Search access limited; collection stopped')
 original_seed=collector.seed
 monkeypatch.setattr(collector,'seed',lambda target,config,sources=None:original_seed(target,config,[] if sources is None else sources))
 monkeypatch.setattr(collector,'ROOT',tmp_path);monkeypatch.setattr(collector,'config',lambda:cfg);monkeypatch.setattr(collector,'network_config',lambda:cfg);monkeypatch.setattr(collector,'capture',stop)
 out=tmp_path/'published.gz';monkeypatch.setattr('sys.argv',['collector','--cache',str(cache),'--output',str(out)])
 assert collector.main()==2 and calls==[1]
 raw=json.loads(gzip.decompress(out.read_bytes()))
 assert len(raw['flights'])==3 and raw['metadata']['uncollected_queries']
 assert len(raw['metadata']['failed_queries'])==1 and raw['metadata']['collection_stop']['reason'].startswith('Search access limited')
