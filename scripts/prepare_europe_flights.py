"""Two-worker EUR capture of selected published Europe routes; cached offline replay."""
import argparse,asyncio,fcntl,gzip,hashlib,json,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import BRANDS,CARRIERS,DAY,NOTE,valid_price,duration_limit
from scripts.prepare_google_flights import capture
CONTEXT=dict(profile='europe_flights',version=1,currency='EUR',adults=1,cabin='economy',trip_type='one_way',airline_filter='none',parser='google-dated-segments-v1',max_duration=28800)


def config(brand=None):
 m=json.loads((ROOT/('data/sources/europe_flights_routes.json' if brand else 'data/sources/europe_flights_starter_routes.json')).read_text())
 if brand:m={**m,'routes':m['routes_by_brand'][brand]}
 zones={a['code']:a['timezone'] for a in m['airports']};start=datetime.fromisoformat(DAY).replace(tzinfo=timezone.utc);end=start+timedelta(days=1);queries=[]
 for a,b in m['routes']:
  # Wizz uses one local departure date; accept the documented UTC-boundary gap.
  if brand=='wizzair':
   queries.append((DAY,a,b));continue
  zone=ZoneInfo(zones[a]);first=(start-timedelta(hours=8)).astimezone(zone).date();last=(end-timedelta(seconds=1)).astimezone(zone).date()
  queries.extend(((first+timedelta(days=n)).isoformat(),a,b) for n in range((last-first).days+1))
 ordered=sorted(set(queries))
 return dict(country='REGION',scope='region',timezone='UTC',end_date=DAY,zones=zones,manifest=m,queries=ordered,query_date_policy=('local_departure_day_only' if brand=='wizzair' else 'utc_day_overlap'),capture_prices=True,currency='EUR',max_duration=28800,capture_context=CONTEXT,reject_invalid_segments=True,allowed_brands=[brand] if brand else ['ryanair','easyjet'])


def seed_pilot(cache,cfg):
 for key in cfg['queries']:
  name='-'.join(key)+'.json';p=cache/name;source=ROOT/'.cache/google-flights-europe-pilot-eur-v1'/name
  if p.exists() or not source.exists():continue
  q=json.loads(source.read_text())
  if (q['date'],q['origin'],q['destination'])!=key or 'curr=EUR' not in q['url'] or q.get('price_error'):continue
  if any(f.get('price') and (not valid_price(f['price']) or f['price']['currency']!='EUR') for f in q['flights']):continue
  q['capture_context']=CONTEXT;q['reused_source']=str(source.relative_to(ROOT));p.write_text(json.dumps(q,separators=(',',':'))+'\n')


def capture_path(cache,key,cfg):
 """Reuse only an exact compatible prior capture with no parser rejections."""
 path=cache/('-'.join(key)+'.json')
 if path.exists():return path
 for directory in cfg.get('reuse_caches',[cfg['legacy_cache']] if cfg.get('legacy_cache') else []):
  legacy=Path(directory)/path.name
  if not legacy.exists():continue
  q=json.loads(legacy.read_text())
  if ((q.get('date'),q.get('origin'),q.get('destination'))==key
      and q.get('capture_context') in cfg.get('reuse_contexts',[])
      and q.get('status') in {'results','no_matching_direct_flights'}
      and not q.get('rejected_flights') and 'curr=EUR' in q.get('url','')):
   return legacy
 return path


def prepare(cache,output,cfg):
 air={a['code']:a for a in cfg['manifest']['airports']};queries=[];missing=[];failed=[];records={}
 start=int(datetime.fromisoformat(DAY).replace(tzinfo=timezone.utc).timestamp());end=start+86400
 for key in cfg['queries']:
  p=capture_path(cache,key,cfg)
  if not p.exists():
   missing.append(list(key));error=p.with_suffix('.error.json')
   if error.exists():failed.append(json.loads(error.read_text()))
   continue
  q=json.loads(p.read_text())
  if (q['date'],q['origin'],q['destination'])!=key or q.get('capture_context') not in [cfg.get('capture_context',CONTEXT),*cfg.get('reuse_contexts',[])]:raise ValueError('Incompatible European query cache context')
  captured=datetime.fromisoformat(q['captured_at'].replace('Z','+00:00'))
  if captured.tzinfo is None:raise ValueError('Source capture timestamp requires a timezone')
  target=[];others=0
  for f in q['flights']:
   if (f['origin'],f['destination'],f['source_date'])!=(key[1],key[2],key[0]):raise ValueError('Wrong exact European segment identity')
   brand=CARRIERS.get(f['carrier'])
   if not brand or brand not in cfg.get('allowed_brands',BRANDS):others+=1;continue
   if not 60<=f['arrival']-f['departure']<=min(cfg.get('max_duration',28800),duration_limit(brand)):raise ValueError('Invalid European source duration')
   if f.get('price') and (not valid_price(f['price']) or f['price']['currency']!=cfg['currency']):raise ValueError('Invalid European quote')
   a,b=air[f['origin']],air[f['destination']]
   if not (a['europe'] or b['europe']):raise ValueError('Flight outside European membership')
   target.append(f)
   if f['departure']>=end or f['arrival']<start:continue
   f={**f,'brand':brand,'flight_scope':'domestic' if a['country']==b['country'] else 'international'}
   if f['id'] in records and records[f['id']]!=f:raise ValueError('Conflicting European source flight')
   records[f['id']]=f
  queries.append({**{k:v for k,v in q.items() if k!='flights'},'target_records':len(target),'other_carrier_records':others,
   'target_status':'target_results' if target else ('only_other_carriers' if q['flights'] else 'not_returned')})
 fs=sorted(records.values(),key=lambda f:(f['departure'],f['id']));used={f[k] for f in fs for k in ('origin','destination')};priced=sum(bool(f.get('price')) for f in fs)
 def counts(selected):
  return dict(flights=len(selected),priced_flights=sum(bool(f.get('price')) for f in selected),airports_returned=len({f[k] for f in selected for k in ('origin','destination')}),routes_returned=len({(f['origin'],f['destination']) for f in selected}))
 def coverage(scope):
  pairs={tuple(p) for p in cfg['manifest']['routes'] if scope=='both' or ('domestic' if air[p[0]]['country']==air[p[1]]['country'] else 'international')==scope}
  qs=[q for q in queries if (q['origin'],q['destination']) in pairs];absent=[q for q in missing if tuple(q[1:]) in pairs];errors=[q for q in failed if (q['origin'],q['destination']) in pairs];codes={c for p in pairs for c in p}
  return dict(candidate_airports=len(codes),airports_planned=len(codes),airports_searched=len({q[k] for q in qs for k in ('origin','destination')}),routes_planned=len(pairs),routes_searched=len({(q['origin'],q['destination']) for q in qs}),routes_with_search_results=len({(q['origin'],q['destination']) for q in qs if q['target_records']}),queries_planned=len(qs)+len(absent),queries_captured=len(qs),queries_not_returned=sum(q['target_status']=='not_returned' for q in qs),queries_rejected=sum(q['status']=='rejected_source_records' for q in qs),queries_only_other_carriers=sum(q['target_status']=='only_other_carriers' for q in qs),queries_with_target_results=sum(q['target_status']=='target_results' for q in qs),failed_or_missing_queries=len(absent),failed_queries=len(errors),unattempted_queries=len(absent)-len(errors),rejected_records=sum(len(q.get('rejected_flights',[])) for q in qs),**counts([f for f in fs if scope=='both' or f['flight_scope']==scope]))
 cov=coverage('both')
 meta=dict(profile='europe_flights',start_date=DAY,end_date=DAY,timezone='UTC',scope='both',source='Public Google Flights dated nonstop segments',source_url='https://www.google.com/travel/flights',queries=queries,uncollected_queries=missing,failed_queries=failed,coverage=cov,coverage_by_scope={scope:coverage(scope) for scope in ['domestic','international','both']},coverage_by_brand={brand:counts([f for f in fs if f['brand']==brand]) for brand in BRANDS},fare_context=dict(currency='EUR',adults=1,cabin='economy',trip_type='one_way'),priced_flights=priced,airlines=sorted({f['airline'] for f in fs}),replay_note=NOTE,route_source_sha256=cfg['manifest']['route_source_sha256'],route_source_urls=cfg['manifest']['source_urls'],unresolved_airports=[],query_date_policy=cfg.get('query_date_policy','utc_day_overlap'),capture_context=cfg.get('capture_context',CONTEXT),selection=cfg['manifest']['selection'])
 for key in ['source_gaps','excluded_airports']:
  if key in cfg['manifest']:meta[key]=cfg['manifest'][key]
 stop=cache/'collection-stop.json'
 if stop.exists():meta['collection_stop']=json.loads(stop.read_text())
 doc=dict(airports=[air[c] for c in sorted(used)],flights=fs,metadata=meta);payload=gzip.compress(json.dumps(doc,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode(),compresslevel=9,mtime=0);output.parent.mkdir(parents=True,exist_ok=True);tmp=output.with_suffix('.tmp');tmp.write_bytes(payload);tmp.replace(output)
 print(json.dumps(dict(**cov,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())),flush=True)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--brand',choices=['ryanair','easyjet','wizzair']);p.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-europe-eur-v1');p.add_argument('--output',type=Path);p.add_argument('--concurrency',type=int,choices=[1,2],default=2);p.add_argument('--prepare-only',action='store_true');p.add_argument('--collect-only',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args();cfg=config(a.brand);a.cache.mkdir(parents=True,exist_ok=True)
 if a.output is None:a.output=(a.cache/f'prepared-{a.brand}.json.gz') if a.brand else ROOT/'data/sources/europe_flights_google_seed.json.gz'
 with (a.cache/'.preparation.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another Europe preparation is running')
  if a.prepare_only:prepare(a.cache,a.output,cfg);return 0
  seed_pilot(a.cache,cfg)
  print(json.dumps(dict(routes=len(cfg['manifest']['routes']),queries=len(cfg['queries']),cached=sum((a.cache/('-'.join(q)+'.json')).exists() for q in cfg['queries']))),flush=True)
  if a.dry_run:return 0
  stopped=None;(a.cache/'collection-stop.json').unlink(missing_ok=True)
  try:asyncio.run(capture(a.cache,DAY,cfg['manifest']['routes'],a.concurrency,cfg))
  except RuntimeError as e:stopped=e;(a.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(e),at=datetime.now(timezone.utc).isoformat())))
  if not a.collect_only:prepare(a.cache,a.output,cfg)
  if stopped:print(f'{stopped}; captures retained; no challenge retry',file=sys.stderr);return 2
 return 0


if __name__=='__main__':sys.exit(main())
