"""Taiwan domestic USD captures; international uses the shared network."""
import argparse
import asyncio
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,country_config,prepare
DAY='2026-11-02'
PROBES=[('TSA','KNH'),('KHH','MZG'),('TSA','LZN'),('TTT','GNI')]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-taiwan')
    p.add_argument('--output',type=Path,default=ROOT/f'data/reference/taiwan_flights/{DAY}.json.gz')
    p.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    p.add_argument('--validate-only',action='store_true');p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    cfg=country_config('TW');pairs=PROBES if args.validate_only else PROBES+[tuple(v) for v in cfg['manifest']['routes'] if tuple(v) not in PROBES];stopped=None
    if not args.prepare_only:
        try:asyncio.run(capture(args.cache,DAY,pairs,args.concurrency,cfg))
        except RuntimeError as error:stopped=error
    if not args.validate_only:prepare(args.cache,args.output,DAY,cfg['manifest']['routes'],cfg)
    if stopped:
        print(f'{stopped}; captures retained; collection not retried',file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())
