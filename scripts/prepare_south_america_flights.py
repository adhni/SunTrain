"""Capture 702 selected South American airport directions on one local departure date, in USD."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,country_config,prepare,expected_queries

DAY='2026-11-02'
PROBES=[('GRU','CGH'),('BOG','MDE'),('SCL','LIM'),('LIM','SCL'),('BOG','GRU'),('AEP','GIG'),('VCP','REC'),('UIO','BOG'),('MVD','ASU'),('VVI','GRU'),('CCS','BOG'),('GEO','PBM')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-south-america-usd-v1')
    parser.add_argument('--output',type=Path,default=ROOT/f'data/reference/south_america_flights/{DAY}.json.gz')
    parser.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    cfg=country_config('SOUTH_AMERICA')
    pairs=PROBES if args.validate_only else PROBES+[tuple(p) for p in cfg['manifest']['routes'] if tuple(p) not in PROBES]
    if args.dry_run:
        queries=list(expected_queries(DAY,pairs,cfg))
        cached=sum((args.cache/f'{d}-{a}-{b}.json').exists() for d,a,b in queries)
        print(json.dumps(dict(airports=len(cfg['manifest']['airports']),queries=len(queries),dates=sorted({q[0] for q in queries}),cached=cached,new_searches=len(queries)-cached)))
        return 0
    stopped=None
    if not args.prepare_only:
        try:asyncio.run(capture(args.cache,DAY,pairs,args.concurrency,cfg))
        except RuntimeError as error:
            stopped=error
            (args.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error))))
    if not args.validate_only:prepare(args.cache,args.output,DAY,cfg['manifest']['routes'],cfg)
    if stopped:
        print(f'{stopped}; captures retained; collection not retried',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':sys.exit(main())
