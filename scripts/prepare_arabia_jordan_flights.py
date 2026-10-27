"""Collect or reproduce four country views sequentially, reusing captures between countries."""
import argparse,json,asyncio,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.arabia_jordan_flights import COUNTRIES
from scripts.sourced_flights import prepare_cached,seed,budget,collection_routes
from scripts.prepare_google_flights import capture,country_config
from scripts.sourced_flight_routes import DAY

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    for code,p in COUNTRIES.items():
        slug=p['slug'];cache=ROOT/f'.cache/google-flights-{slug}-usd-v1';cfg=country_config(code)
        cfg['capture_context']=dict(parser=f'{slug}-origin-local-v1',max_duration=86400,currency='USD',adults=1,cabin='economy',trip_type='one_way')
        if not args.prepare_only:print(json.dumps(dict(country=code,**seed(cache,cfg))),flush=True)
        print(json.dumps(dict(country=code,**budget(cache,cfg))),flush=True)
        if args.dry_run:continue
        stopped=None
        if not args.prepare_only:
            fresh=cache/'new-usd';pending=collection_routes(cache,cfg);collection={**cfg,'queries':[(DAY,a,b) for a,b in pending]}
            try:asyncio.run(capture(fresh,DAY,pending,2,collection))
            except RuntimeError as error:
                stopped=error;(cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error))))
            finally:
                for path in fresh.glob(f'{DAY}-*.json'):
                    target=cache/path.name;temp=target.with_suffix('.tmp');shutil.copyfile(path,temp);temp.replace(target)
        print(json.dumps(dict(country=code,**prepare_cached(cache,ROOT/f'data/reference/{slug}_flights/{DAY}.json.gz',cfg))),flush=True)
        if stopped:print(str(stopped),file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
