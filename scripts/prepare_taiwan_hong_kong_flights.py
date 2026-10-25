"""One worldwide query queue, reused by two local views and the shared network."""
import argparse,asyncio,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.international_network import consumer_queries
from dashboard.international_network import NOTE,reference_path
from scripts.prepare_international_network import config as network_config,seed,prepare
from scripts.prepare_google_flights import capture


def config():
 m=json.loads((ROOT/'data/sources/taiwan_hong_kong_worldwide_routes.json').read_text());air={a['code']:a for a in m['airports']}
 views={c:consumer_queries(m,c) for c in ['taiwan_flights','hong_kong_flights']}
 needed={tuple(q) for qs in views.values() for q in qs}
 # Capture extra origin-local dates needed by UTC and existing endpoint-country views once.
 for q in network_config()['queries']:
  if q[1] in air and q[2] in air and {air[q[1]]['country'],air[q[2]]['country']}&{'TW','HK'}:needed.add(q)
 return dict(country='NETWORK',scope='international',manifest=m,timezone='UTC',end_date='2026-11-02',max_duration=86400,capture_prices=True,currency='USD',zones={c:a['timezone'] for c,a in air.items()},queries=sorted(needed),queries_by_view=views,profile='taiwan_hong_kong_worldwide',note=NOTE,route_source_url=m['route_source_url'],browser_cleanup_timeout=1)


def publish(cache,output):
 cfg=network_config();shared_cache=ROOT/'.cache/google-flights-international-network'
 shared_cache.mkdir(parents=True,exist_ok=True)
 seed(shared_cache,cfg,sources=[cache])
 for key in cfg['queries']:
  name='-'.join(key)+'.json';error=(cache/name).with_suffix('.error.json')
  if error.exists() and not (shared_cache/name).exists():
   (shared_cache/name).with_suffix('.error.json').write_bytes(error.read_bytes())
 stop=cache/'collection-stop.json';shared_stop=shared_cache/'collection-stop.json'
 if stop.exists():shared_stop.write_bytes(stop.read_bytes())
 elif all((shared_cache/('-'.join(q)+'.json')).exists() for q in cfg['queries']):shared_stop.unlink(missing_ok=True)
 prepare(shared_cache,output,cfg)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-taiwan-hong-kong-worldwide');p.add_argument('--output',type=Path,default=reference_path());p.add_argument('--prepare-only',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--concurrency',type=int,choices=[1,2],default=2);args=p.parse_args();cfg=config();args.cache.mkdir(parents=True,exist_ok=True)
 if args.prepare_only:publish(args.cache,args.output);return 0
 seed(args.cache,cfg)
 if args.dry_run:return 0
 stopped=None
 (args.cache/'collection-stop.json').unlink(missing_ok=True)
 try:asyncio.run(capture(args.cache,'2026-11-02',cfg['manifest']['routes'],args.concurrency,cfg))
 except RuntimeError as error:
  stopped=error;(args.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error),at=datetime.now(timezone.utc).isoformat())))
 publish(args.cache,args.output)
 if stopped:print(f'{stopped}; successful captures preserved; no challenge retry',file=sys.stderr);return 2
 return 0


if __name__=='__main__':sys.exit(main())
