"""Official timetable clocks, exact quote reuse, coverage and resumability."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import pytest
from scripts import prepare_ryanair_flights as r

AIR={code:dict(code=code,timezone=zone,country=country) for code,zone,country in [
 ('STN','Europe/London','GB'),('DUB','Europe/Dublin','IE'),
 ('BGY','Europe/Rome','IT'),('TFS','Atlantic/Canary','ES')]}


def query(a='STN',b='DUB',day=2,dep='06:35',arr='07:55',carrier='FR',number='203'):
 return dict(origin=a,destination=b,context=r.CONTEXT,url=r.url(a,b),captured_at='2026-10-26T00:00:00Z',body_sha256='fixture',payload=dict(month=11,days=[dict(day=day,flights=[dict(carrierCode=carrier,number=number,departureTime=dep,arrivalTime=arr)])]))


def test_full_manifest_preserves_exact_airports_and_both_catalogues():
 m=r.manifest();assert len(m['routes_by_brand']['ryanair'])==5305
 assert len(m['routes_by_brand']['easyjet'])==2564
 assert len(m['routes'])==9357 and len(m['airports'])==320
 airports={a['code']:a for a in m['airports']}
 assert airports['TFS']['timezone']=='Atlantic/Canary'
 assert airports['BGY']['icao']!=airports['MXP']['icao']
 assert all(airports[a]['europe'] or airports[b]['europe'] for a,b in m['routes'])


@pytest.mark.parametrize('q,hours,offset',[
 (query(carrier='RK'),80/60,0),
 (query(dep='23:30',arr='00:50'),80/60,1),
 (query(a='BGY',b='STN',dep='00:10',arr='23:55'),45/60,-1),
 (query(a='TFS',b='STN',dep='06:05',arr='10:30'),265/60,0),
 (query(dep='12:00',arr='12:01'),1/60,0),
])
def test_unique_utc_clocks_support_midnight_islands_and_short_flights(q,hours,offset):
 fs,errors=r.parse_month(q,AIR);assert not errors and len(fs)==1
 f=fs[0];assert f['arrival']-f['departure']==round(hours*3600)
 assert f['arrival_day_offset']==offset and 'price' not in f
 assert f['carrier']==q['payload']['days'][0]['flights'][0]['carrierCode']
 assert f['aircraft']=='Aircraft not specified'


@pytest.mark.parametrize('body',[None,[],{},dict(month=10,days=[]),dict(month=11,days=[None]),dict(month=11,days=[dict(day=31,flights=[])]),dict(month=11,days=[dict(day=2,flights=[])]*2)])
def test_malformed_months_are_rejected(body):
 with pytest.raises(ValueError):r.validate_payload(body)


def test_duplicates_conflicts_invalid_clocks_and_duration():
 q=query();raw=q['payload']['days'][0]['flights'];raw.append(deepcopy(raw[0]))
 fs,errors=r.parse_month(q,AIR);assert len(fs)==1 and not errors
 raw.append({**raw[0],'arrivalTime':'08:00'});raw.append(deepcopy(raw[0]))
 fs,errors=r.parse_month(q,AIR);assert not fs and errors
 for dep,arr in [('06:00','15:00'),('25:00','06:00'),('06:00','06:00')]:
  fs,errors=r.parse_month(query(dep=dep,arr=arr),AIR);assert not fs and errors
 # Nonexistent/ambiguous wall clocks are never silently assigned a fold.
 from zoneinfo import ZoneInfo
 assert not r.instants(datetime(2026,3,29,1,30,tzinfo=ZoneInfo('Europe/London')))
 assert len(r.instants(datetime(2026,10,25,1,30,tzinfo=ZoneInfo('Europe/London'))))==2


def preparation_fixture(tmp_path):
 cache=tmp_path/'cache';cache.mkdir();q=query();official=r.parse_month(q,AIR)[0][0]
 price=dict(amount_minor=1299,currency='EUR',adults=1,cabin='economy',trip_type='one_way',captured_at='2026-10-26T00:00:00Z')
 old={**official,'price':price,'aircraft':'Existing source aircraft'}
 easy={**old,'id':'easyjet','brand':'easyjet','carrier':'U2','number':'U21'}
 seed=tmp_path/'seed.gz';r.save(seed,dict(airports=list(AIR.values()),flights=[old,easy],metadata=dict(queries=[],fare_context=dict(currency='EUR'))))
 m=dict(airports=list(AIR.values()),routes=[['STN','DUB'],['DUB','STN'],['STN','BGY']],routes_by_brand=dict(ryanair=[['STN','DUB'],['DUB','STN'],['STN','BGY']]),route_source_sha256='fixture',selection='test')
 r.save(r.path_for(cache,'STN','DUB'),q)
 r.path_for(cache,'DUB','STN').with_suffix('.error.json').write_text(json.dumps(dict(origin='DUB',destination='STN',error='503')))
 return cache,tmp_path/'out.gz',m,seed,easy


def test_preparation_keeps_easyjet_and_exact_quotes_reports_missing_and_reproduces(tmp_path):
 cache,out,m,seed,easy=preparation_fixture(tmp_path);r.prepare(cache,out,m,seed);first=out.read_bytes()
 r.prepare(cache,out,m,seed);assert out.read_bytes()==first
 doc=r.read(out);assert next(f for f in doc['flights'] if f['brand']=='easyjet')==easy
 official=next(f for f in doc['flights'] if f['brand']=='ryanair');assert official['price']['amount_minor']==1299 and official['aircraft']=='Existing source aircraft'
 stats=doc['metadata']['coverage_by_source']['ryanair_timetable'];assert (stats['planned'],stats['captured'],stats['failed'],stats['unattempted'])==(3,1,1,1)
 assert doc['metadata']['coverage']['failed_or_missing_queries']==2
 assert doc['metadata']['coverage']['source_counts']==dict(monthly_captured=1,monthly_planned=3,dated_captured=0,dated_planned=0)
 q=r.read(r.path_for(cache,'STN','DUB'));q['payload']['days'][0]['flights'][0]['departureTime']='06:40';r.save(r.path_for(cache,'STN','DUB'),q)
 r.prepare(cache,out,m,seed);doc=r.read(out);assert 'price' not in next(f for f in doc['flights'] if f['brand']=='ryanair')
 assert doc['metadata']['schedule_updates'][0]['quote_removed']
 q['payload']['days']=[];r.save(r.path_for(cache,'STN','DUB'),q);r.prepare(cache,out,m,seed);doc=r.read(out)
 assert doc['metadata']['coverage_by_brand']['ryanair']['google_only_records']==1
 assert next(f for f in doc['flights'] if f['brand']=='ryanair')['price']['amount_minor']==1299


def test_collector_resumes_and_stops_on_access_challenge(tmp_path,monkeypatch):
 m=dict(routes_by_brand=dict(ryanair=[['STN','DUB'],['DUB','STN'],['STN','BGY']]))
 r.save(r.path_for(tmp_path,'STN','DUB'),query());calls=[]
 class Response:
  status_code=429;text='Too many requests'
 class Session:
  def get(self,url,timeout):calls.append(url);return Response()
 monkeypatch.setattr(r.requests,'Session',Session);monkeypatch.setattr(r.time,'sleep',lambda _:None)
 with pytest.raises(RuntimeError,match='stopped'):r.collect(tmp_path,m,workers=1)
 assert calls==[r.url('DUB','STN')]
 assert r.path_for(tmp_path,'DUB','STN').with_suffix('.error.json').exists()


def test_prepared_expansion_keeps_easyjet_and_only_reuses_exact_seed_quotes():
 from dashboard.europe_flights import load_reference
 doc=load_reference(r.DAY);seed=r.read(r.ROOT/'data/sources/europe_flights_google_seed.json.gz')
 prepared={f['id']:f for f in doc['flights']}
 assert all(prepared[f['id']]==f for f in seed['flights'] if f['brand']=='easyjet')
 assert len(doc['flights'])>len(seed['flights'])
 stats=doc['metadata']['coverage_by_source']['ryanair_timetable']
 assert stats['planned']==5305 and stats['captured']+stats['failed']+stats['unattempted']==5305
 assert stats['unattempted']==0
 originals={f['id']:f for f in seed['flights']}
 for f in doc['flights']:
  if f.get('price') and f['id'] in originals:
   old=originals[f['id']];assert (f['departure'],f['arrival'],f['price'])==(old['departure'],old['arrival'],old['price'])
  if f.get('schedule_source')=='ryanair_public_timetable' and f['id'] not in originals:
   assert not f.get('price') and f['aircraft']=='Aircraft not specified'
