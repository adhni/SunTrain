"""Collect the complete published Ryanair route catalogue's public November timetable."""
import argparse,concurrent.futures,fcntl,gzip,hashlib,json,re,sys,threading,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import CARRIERS,DAY,NOTE,valid_price
CONTEXT=dict(source='ryanair_public_timetable',version=1,year=2026,month=11)
BASE='https://services-api.ryanair.com/timtbl/3/schedules'
LABELS={'FR':'Ryanair','RK':'Ryanair UK','RR':'Buzz','AL':'Malta Air'}


def manifest():return json.loads((ROOT/'data/sources/europe_flights_routes.json').read_text())
def url(a,b):return f'{BASE}/{a}/{b}/years/2026/months/11'
def path_for(cache,a,b):return cache/f'2026-11-{a}-{b}.json.gz'
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_bytes(gzip.compress(json.dumps(value,separators=(',',':'),sort_keys=True).encode(),mtime=0));tmp.replace(path)
def read(path):return json.loads(gzip.decompress(path.read_bytes()))


def validate_payload(body):
 if not isinstance(body,dict) or body.get('month')!=11 or not isinstance(body.get('days'),list):raise ValueError('Unexpected official timetable schema')
 days=set()
 for row in body['days']:
  if not isinstance(row,dict) or type(row.get('day')) is not int or not 1<=row['day']<=30 or row['day'] in days or not isinstance(row.get('flights'),list):raise ValueError('Invalid or duplicate timetable day')
  days.add(row['day'])


def collect(cache,m,workers=2):
 pending=[(a,b) for a,b in m['routes_by_brand']['ryanair'] if not path_for(cache,a,b).exists()];stopped=threading.Event();local=threading.local();checked=0
 print(json.dumps(dict(routes=len(m['routes_by_brand']['ryanair']),pending=len(pending),workers=workers)),flush=True)
 def fetch(pair):
  a,b=pair;p=path_for(cache,a,b)
  if stopped.is_set():return
  if not hasattr(local,'session'):local.session=requests.Session()
  try:
   response=local.session.get(url(a,b),timeout=(10,30))
   if response.status_code in {401,403,429} or 'captcha' in response.text[:2000].lower():
    p.with_suffix('.error.json').write_text(json.dumps(dict(origin=a,destination=b,url=url(a,b),error=f'Access challenge ({response.status_code})',captured_at=datetime.now(timezone.utc).isoformat())))
    stopped.set();raise RuntimeError(f'Official timetable access limited ({response.status_code}); collection stopped')
   response.raise_for_status();body=response.json();validate_payload(body)
   save(p,dict(origin=a,destination=b,context=CONTEXT,url=url(a,b),captured_at=datetime.now(timezone.utc).isoformat(),http_status=response.status_code,body_sha256=hashlib.sha256(response.content).hexdigest(),payload=body))
   p.with_suffix('.error.json').unlink(missing_ok=True)
  except RuntimeError:raise
  except (requests.RequestException,ValueError) as error:
   p.with_suffix('.error.json').write_text(json.dumps(dict(origin=a,destination=b,url=url(a,b),error=str(error)[:300],captured_at=datetime.now(timezone.utc).isoformat())))
   print(f'Uncollected {a}-{b}: {str(error)[:120]}',flush=True)
  finally:time.sleep(.15)
 it=iter(pending)
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  futures={pool.submit(fetch,pair) for pair in [next(it,None) for _ in range(workers)] if pair is not None}
  try:
   while futures:
    done,futures=concurrent.futures.wait(futures,return_when=concurrent.futures.FIRST_COMPLETED)
    for future in done:
     future.result();checked+=1
     if checked%100==0 or checked==len(pending):print(f'{checked}/{len(pending)} timetable requests checked',flush=True)
     pair=next(it,None)
     if pair is not None and not stopped.is_set():futures.add(pool.submit(fetch,pair))
  except RuntimeError:
   stopped.set()
   for future in futures:future.cancel()
   raise


def instants(local):
 return {int(local.replace(fold=fold).timestamp()) for fold in (0,1) if datetime.fromtimestamp(local.replace(fold=fold).timestamp(),local.tzinfo).replace(tzinfo=None)==local.replace(tzinfo=None)}


def parse_month(q,air):
 """Only a unique UTC interpretation of source-local clocks is eligible."""
 validate_payload(q['payload']);a,b=q['origin'],q['destination'];fs={};rejected=[];conflicts=set()
 for row in q['payload']['days']:
  if row['day'] not in {1,2,3}:continue
  day=f"2026-11-{row['day']:02}";local_day=datetime.fromisoformat(day)
  for raw in row['flights']:
   try:
    carrier=raw['carrierCode'];number=raw['number']
    if CARRIERS.get(carrier)!='ryanair' or not isinstance(number,str) or not re.fullmatch(r'\d+',number):raise ValueError('Unknown timetable carrier or flight identity')
    times=[]
    for key in ['departureTime','arrivalTime']:
     if not re.fullmatch(r'\d{2}:\d{2}',raw[key]):raise ValueError('Unsupported source clock')
     times.append(tuple(map(int,raw[key].split(':'))))
    dep=local_day.replace(hour=times[0][0],minute=times[0][1],tzinfo=ZoneInfo(air[a]['timezone']));matches=set()
    for offset in [-1,0,1,2]:
     arr=(local_day+timedelta(days=offset)).replace(hour=times[1][0],minute=times[1][1],tzinfo=ZoneInfo(air[b]['timezone']))
     matches.update((d,t,offset) for d in instants(dep) for t in instants(arr) if 60<=t-d<=28800)
    if len(matches)!=1:raise ValueError('No unique UTC arrival day within the eight-hour regional limit')
    departure,arrival,offset=matches.pop();identity=f'{day}:{carrier}{number}:{a}:{b}'
    f=dict(id=identity,number=carrier+number,carrier=carrier,airline=LABELS.get(carrier,carrier),origin=a,destination=b,departure=departure,arrival=arrival,source_date=day,brand='ryanair',flight_scope='domestic' if air[a]['country']==air[b]['country'] else 'international',aircraft='Aircraft not specified',source_page=q['url'],schedule_source='ryanair_public_timetable',source_captured_at=q['captured_at'],arrival_day_offset=offset,timing_basis='unique_utc_pair_from_official_local_clocks')
    if identity in fs and fs[identity]!=f:conflicts.add(identity);fs.pop(identity,None);raise ValueError('Conflicting official flight identity')
    if identity not in conflicts:fs[identity]=f
   except (ValueError,TypeError,KeyError) as error:rejected.append(dict(date=day,flight=raw,error=str(error)))
 return list(fs.values()),rejected


def prepare(cache,output,m,seed_path):
 seed=read(seed_path);air={a['code']:a for a in m['airports']};air.update({a['code']:a for a in seed['airports']});records={f['id']:f for f in seed['flights']};requests_meta=[];missing=[];failed=[];rejected=[];updates=[];official_ids=set();start=int(datetime.fromisoformat(DAY).replace(tzinfo=timezone.utc).timestamp());end=start+86400
 for a,b in m['routes_by_brand']['ryanair']:
  p=path_for(cache,a,b)
  if not p.exists():
   missing.append([a,b]);error=p.with_suffix('.error.json')
   if error.exists():failed.append(json.loads(error.read_text()))
   continue
  q=read(p)
  if (q['origin'],q['destination'])!=(a,b) or q['context']!=CONTEXT:raise ValueError('Incompatible official timetable cache')
  if q['url']!=url(a,b) or not datetime.fromisoformat(q['captured_at'].replace('Z','+00:00')).utcoffset()==timedelta(0):raise ValueError('Invalid timetable provenance')
  fs,errors=parse_month(q,air);rejected.extend(dict(origin=a,destination=b,**e) for e in errors);eligible=[f for f in fs if f['departure']<end and f['arrival']>=start]
  for f in eligible:
   old=records.get(f['id'])
   if old:
    same=(old['departure'],old['arrival'])==(f['departure'],f['arrival'])
    if same:
     f={**old,**{k:f[k] for k in ['source_page','schedule_source','source_captured_at','arrival_day_offset','timing_basis']}}
     if old.get('price') and not valid_price(old['price']):raise ValueError('Invalid preserved quote')
    else:updates.append(dict(id=f['id'],previous_departure=old['departure'],previous_arrival=old['arrival'],departure=f['departure'],arrival=f['arrival'],quote_removed=bool(old.get('price'))))
   records[f['id']]=f;official_ids.add(f['id'])
  requests_meta.append(dict(source='ryanair_public_timetable',request_unit='airport_pair_month',date=DAY,origin=a,destination=b,url=q['url'],captured_at=q['captured_at'],page_sha256=q['body_sha256'],status='results' if fs else 'no_returned_timetable_records',overlapping_records=len(eligible),dated_records=len(fs),rejected_records=len(errors)))
 fs=sorted(records.values(),key=lambda f:(f['departure'],f['id']));codes={f[k] for f in fs for k in ['origin','destination']};queries=seed['metadata']['queries']+requests_meta
 def counts(selected):return dict(flights=len(selected),priced_flights=sum(bool(f.get('price')) for f in selected),airports_returned=len({f[k] for f in selected for k in ['origin','destination']}),routes_returned=len({(f['origin'],f['destination']) for f in selected}))
 def coverage(scope):
  pairs={tuple(p) for p in m['routes'] if scope=='both' or ('domestic' if air[p[0]]['country']==air[p[1]]['country'] else 'international')==scope};qs=[q for q in queries if (q['origin'],q['destination']) in pairs];absent=[p for p in missing if tuple(p) in pairs];errors=[q for q in failed if (q['origin'],q['destination']) in pairs];selected=[f for f in fs if scope=='both' or f['flight_scope']==scope]
  return dict(candidate_airports=len({c for p in pairs for c in p}),airports_planned=len({c for p in pairs for c in p}),airports_searched=len({q[k] for q in qs for k in ['origin','destination']}),routes_planned=len(pairs),routes_searched=len({(q['origin'],q['destination']) for q in qs}),source_counts=dict(monthly_captured=sum(q.get('source')=='ryanair_public_timetable' for q in qs),monthly_planned=sum(q.get('source')=='ryanair_public_timetable' for q in qs)+len(absent),dated_captured=sum(q.get('source')!='ryanair_public_timetable' for q in qs),dated_planned=sum(q.get('source')!='ryanair_public_timetable' for q in qs)),queries_planned=len(qs)+len(absent),queries_captured=len(qs),query_unit='source_request; monthly timetables and dated Google searches reported separately',queries_not_returned=sum(q.get('status') in {'no_returned_timetable_records','no_matching_direct_flights'} for q in qs),queries_rejected=sum(q.get('status')=='rejected_source_records' or q.get('rejected_records',0)>0 for q in qs),failed_or_missing_queries=len(absent),failed_queries=len(errors),unattempted_queries=len(absent)-len(errors),rejected_records=sum(q.get('rejected_records',len(q.get('rejected_flights',[]))) for q in qs),**counts(selected))
 bybrand={brand:counts([f for f in fs if f['brand']==brand]) for brand in ['ryanair','easyjet']};bybrand['ryanair'].update(routes_planned=len(m['routes_by_brand']['ryanair']),official_records=len(official_ids),google_only_records=sum(f['brand']=='ryanair' and f['id'] not in official_ids for f in fs));meta={**seed['metadata'],'capture_context':dict(profile='europe_flights',version=2,sources=dict(google_starter=seed['metadata'].get('capture_context'),ryanair_timetable=CONTEXT)),'airlines':sorted({f['airline'] for f in fs}),'source':'Ryanair public timetables plus preserved Google Flights starter quotes and easyJet sample','source_url':BASE,'queries':queries,'coverage':coverage('both'),'coverage_by_scope':{s:coverage(s) for s in ['both','domestic','international']},'coverage_by_brand':bybrand,'coverage_by_source':dict(ryanair_timetable=dict(request_unit='airport_pair_month',planned=len(m['routes_by_brand']['ryanair']),captured=len(requests_meta),failed=len(failed),unattempted=len(missing)-len(failed),routes_with_day_flights=sum(q['overlapping_records']>0 for q in requests_meta),dated_flights=len(official_ids)),google_starter=dict(request_unit='airport_pair_date',planned=len(seed['metadata']['queries']),captured=len(seed['metadata']['queries']),easyjet='unchanged starter')),'uncollected_queries':[[DAY,a,b] for a,b in missing],'failed_queries':failed,'official_rejected_records':rejected,'schedule_updates':updates,'priced_flights':sum(bool(f.get('price')) for f in fs),'replay_note':NOTE,'route_source_sha256':m['route_source_sha256'],'selection':m['selection'],'quote_policy':'Original seed quotes retained only for identical source flight identity and UTC schedule; new timetable-only records have no invented price','seed_sha256':hashlib.sha256(seed_path.read_bytes()).hexdigest()}
 stop=cache/'collection-stop.json'
 if stop.exists():meta['collection_stop']=json.loads(stop.read_text())
 doc=dict(airports=[air[c] for c in sorted(codes)],flights=fs,metadata=meta);save(output,doc)
 print(json.dumps(dict(records=len(fs),brands=bybrand,timetable_requests=len(requests_meta),missing=len(missing),rejected=len(rejected),updates=len(updates),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())),flush=True)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/ryanair-timetables-v1');p.add_argument('--output',type=Path,default=ROOT/f'data/reference/europe_flights/{DAY}.json.gz');p.add_argument('--seed',type=Path,default=ROOT/'data/sources/europe_flights_google_seed.json.gz');p.add_argument('--concurrency',type=int,choices=[1,2],default=2);p.add_argument('--prepare-only',action='store_true');p.add_argument('--collect-only',action='store_true');a=p.parse_args();a.cache.mkdir(parents=True,exist_ok=True);m=manifest()
 with (a.cache/'.collection.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another official timetable collector is running')
  stopped=None
  if not a.prepare_only:
   (a.cache/'collection-stop.json').unlink(missing_ok=True)
   try:collect(a.cache,m,a.concurrency)
   except RuntimeError as error:stopped=error;(a.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error),at=datetime.now(timezone.utc).isoformat())))
  if not a.collect_only:prepare(a.cache,a.output,m,a.seed)
  if stopped:print(f'{stopped}; captures preserved; no access-challenge retry',file=sys.stderr);return 2
 return 0


if __name__=='__main__':sys.exit(main())
