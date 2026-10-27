"""One shared, single-local-date EUR collection for nine European flag carriers."""
import argparse,asyncio,fcntl,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import DAY,FLAG_CARRIERS
from scripts import prepare_europe_flights as google
from scripts.prepare_google_flights import capture
CONTEXT={**google.CONTEXT,'version':2,'max_duration':86400}
CACHE=ROOT/'.cache/google-flights-europe-groups-eur-v1'
LEGACY=ROOT/'.cache/google-flights-europe-eur-v1'


def config():
 m=json.loads((ROOT/'data/sources/europe_groups_routes.json').read_text())
 return dict(country='REGION',scope='region',timezone='UTC',end_date=DAY,zones={a['code']:a['timezone'] for a in m['airports']},manifest=m,queries=[(DAY,a,b) for a,b in m['routes']],query_date_policy='local_departure_day_only',capture_prices=True,currency='EUR',max_duration=86400,capture_context=CONTEXT,reject_invalid_segments=True,allowed_brands=list(FLAG_CARRIERS),legacy_cache=str(LEGACY),reuse_contexts=[google.CONTEXT])


def prepare_all(cache,output,cfg,networks_path=None):
 from scripts import prepare_ryanair_flights as r
 path=cache/'prepared-groups.json.gz';google.prepare(cache,path,cfg)
 # Rebuild all previous brands from their frozen inputs, never from a mutable
 # prior combined archive. The final archive therefore reproduces from caches.
 legacy=Path(cfg['legacy_cache']);legacy.mkdir(parents=True,exist_ok=True)
 with (legacy/'.preparation.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for brand in ['easyjet','wizzair']:google.prepare(legacy,legacy/f'prepared-{brand}.json.gz',google.config(brand))
  if networks_path is None and (ROOT/'data/sources/europe_networks_routes.json').exists():
   from scripts.prepare_europe_networks import CACHE as network_cache,prepare_extra
   network_cache.mkdir(parents=True,exist_ok=True)
   with (network_cache/'.preparation.lock').open('a') as network_lock:
    fcntl.flock(network_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    networks_path=prepare_extra(network_cache)
  r.prepare(ROOT/'.cache/ryanair-timetables-v1',output,r.manifest(),ROOT/'data/sources/europe_flights_google_seed.json.gz',legacy/'prepared-easyjet.json.gz',legacy/'prepared-wizzair.json.gz',path,networks_path)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=ROOT/f'data/reference/europe_flights/{DAY}.json.gz');p.add_argument('--dry-run',action='store_true');p.add_argument('--collect-only',action='store_true');p.add_argument('--prepare-only',action='store_true');a=p.parse_args();cfg=config();a.cache.mkdir(parents=True,exist_ok=True)
 with (a.cache/'.preparation.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if a.prepare_only:prepare_all(a.cache,a.output,cfg);return 0
  new=[q for q in cfg['queries'] if not google.capture_path(a.cache,q,cfg).exists()]
  legacy=sum(google.capture_path(a.cache,q,cfg).parent==Path(cfg['legacy_cache']) for q in cfg['queries'])
  print(json.dumps(dict(airline_directions=sum(len(v) for v in cfg['manifest']['routes_by_brand'].values()),unique_directions=len(cfg['queries']),date=DAY,legacy_cache_hits=legacy,new_cache_hits=len(cfg['queries'])-len(new)-legacy,new_requests=len(new))),flush=True)
  if a.dry_run:return 0
  stop=None;(a.cache/'collection-stop.json').unlink(missing_ok=True)
  try:asyncio.run(capture(a.cache,DAY,cfg['manifest']['routes'],2,{**cfg,'queries':new}))
  except RuntimeError as error:
   stop=error;(a.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error),at=datetime.now(timezone.utc).isoformat())))
  if not a.collect_only:prepare_all(a.cache,a.output,cfg)
  if stop:print(f'{stop}; captures retained; no challenge retry',file=sys.stderr);return 2
 return 0


if __name__=='__main__':sys.exit(main())
