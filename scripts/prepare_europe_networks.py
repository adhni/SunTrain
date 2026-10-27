"""One shared route queue for additional European networks, one local date and EUR."""
import argparse,asyncio,fcntl,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import DAY,OTHER_NETWORKS
from scripts import prepare_europe_flights as google,prepare_europe_groups as groups
from scripts.prepare_google_flights import capture
CACHE=ROOT/'.cache/google-flights-europe-networks-eur-v1'

def config():
 m=json.loads((ROOT/'data/sources/europe_networks_routes.json').read_text())
 return dict(country='REGION',scope='region',timezone='UTC',end_date=DAY,zones={a['code']:a['timezone'] for a in m['airports']},manifest=m,queries=[(DAY,a,b) for a,b in m['routes']],query_date_policy='local_departure_day_only',capture_prices=True,currency='EUR',max_duration=86400,capture_context=groups.CONTEXT,reject_invalid_segments=True,allowed_brands=list(OTHER_NETWORKS),reuse_caches=[str(groups.CACHE),str(groups.LEGACY)],reuse_contexts=[groups.CONTEXT,google.CONTEXT])

def prepare_extra(cache=CACHE):
 cache.mkdir(parents=True,exist_ok=True)
 path=cache/'prepared-networks.json.gz';google.prepare(cache,path,config());return path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=ROOT/f'data/reference/europe_flights/{DAY}.json.gz');p.add_argument('--dry-run',action='store_true');p.add_argument('--collect-only',action='store_true');p.add_argument('--prepare-only',action='store_true');a=p.parse_args();cfg=config();a.cache.mkdir(parents=True,exist_ok=True)
 with (a.cache/'.preparation.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  new=[q for q in cfg['queries'] if not google.capture_path(a.cache,q,cfg).exists()]
  reused=sum(google.capture_path(a.cache,q,cfg).parent!=a.cache for q in cfg['queries'] if google.capture_path(a.cache,q,cfg).exists())
  print(json.dumps(dict(directions=len(cfg['queries']),date=DAY,reused_queries=reused,cached_new=len(cfg['queries'])-len(new)-reused,new_requests=len(new))),flush=True)
  if a.dry_run:return 0
  stopped=None
  if not a.prepare_only:
   (a.cache/'collection-stop.json').unlink(missing_ok=True)
   try:asyncio.run(capture(a.cache,DAY,cfg['manifest']['routes'],2,{**cfg,'queries':new}))
   except RuntimeError as error:
    stopped=error;(a.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error),at=datetime.now(timezone.utc).isoformat())))
  if not a.collect_only:
   path=prepare_extra(a.cache)
   groups.CACHE.mkdir(parents=True,exist_ok=True)
   with (groups.CACHE/'.preparation.lock').open('a') as group_lock:
    fcntl.flock(group_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    groups.prepare_all(groups.CACHE,a.output,groups.config(),networks_path=path)
  if stopped:print(f'{stopped}; captures retained; no challenge retry',file=sys.stderr);return 2
 return 0

if __name__=='__main__':sys.exit(main())
