"""One resumable, two-worker Gulf collection with separate per-hub query caches."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,prepare
from scripts.prepare_gulf_airports import HUBS,pair_owner


def gulf_config():
    manifest=json.loads((ROOT/'data/sources/gulf_flights_routes.json').read_text())
    return dict(country='GULF',scope='hubs',hub_codes=HUBS,manifest=manifest,
        zones={a['code']:a['timezone'] for a in manifest['airports']},timezone=manifest['timezone'],
        end_date=manifest['end_date'],max_duration=manifest['max_duration'],capture_prices=True,currency='USD')


def ordered_pairs(config):
    groups={hub:[] for hub in HUBS}
    for pair in config['manifest']['routes']:groups[pair_owner(*pair)].append(tuple(pair))
    for hub in HUBS:
        priority=[(hub,'SIN'),('SIN',hub),(hub,'LHR'),('LHR',hub)]
        groups[hub]=[p for p in priority if p in groups[hub]]+[p for p in groups[hub] if p not in priority]
    return [groups[hub][n] for n in range(max(map(len,groups.values()))) for hub in HUBS if n<len(groups[hub])]


def prepare_all(cache,output,config):
    written=[]
    for hub in HUBS:
        pairs=[p for p in config['manifest']['routes'] if pair_owner(*p)==hub]
        codes={c for pair in pairs for c in pair}
        manifest={**config['manifest'],'routes':pairs,'airports':[a for a in config['manifest']['airports'] if a['code'] in codes]}
        try:
            prepare(cache,output/f'2026-11-02-{hub}.json.gz','2026-11-02',pairs,{**config,'manifest':manifest,'query_owner':hub})
        except ValueError as error:
            if str(error)!='No flights collected':raise
            print(f'{hub}: no usable captures yet; no snapshot invented',flush=True)
        else:written.append(hub)
    return written


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-gulf')
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/gulf_flights')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    args=parser.parse_args();config=gulf_config();stopped=None
    if not args.prepare_only:
        try:asyncio.run(capture(args.cache,'2026-11-02',ordered_pairs(config),args.concurrency,config))
        except RuntimeError as error:stopped=error
    prepare_all(args.cache,args.output,config)
    if stopped:
        print(f'{stopped}; successful captures retained, collection not retried',file=sys.stderr)
        sys.exit(2)
