"""India domestic/international USD captures, two workers and resumable caches."""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import parse_qs, urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture, country_config, expected_queries, prepare

DAY='2026-11-02'
PROBES={'domestic':[('DEL','BOM'),('BLR','MAA'),('COK','AGX'),('GAU','TEI'),('NMI','BLR'),('DXN','BLR')],
        'international':[('DEL','LHR'),('CCJ','SHJ'),('DEL','JFK'),('TRZ','SIN')]}


def seed_usd_captures(cache, config, sources=None):
    """Copy exact-date USD normalized captures, preserving their source timestamps."""
    sources=sources if sources is not None else [ROOT/'.cache/google-flights-gulf', ROOT/'.cache/google-flights-singapore']
    expected=set(expected_queries(DAY,config['manifest']['routes'],config));copied=0
    cache.mkdir(parents=True,exist_ok=True)
    for source in sources:
        for path in sorted(source.rglob('*.json')):
            if path.name.endswith('.error.json'):continue
            q=json.loads(path.read_text())
            if (q.get('date'),q.get('origin'),q.get('destination')) not in expected:continue
            if parse_qs(urlparse(q.get('url','')).query).get('curr')!=['USD']:continue
            if any(f.get('price') and tuple(f['price'].get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way') for f in q['flights']):continue
            target=cache/f"{q['date']}-{q['origin']}-{q['destination']}.json"
            if not target.exists():
                temporary=target.with_suffix('.tmp');shutil.copyfile(path,temporary);temporary.replace(target);copied+=1
    return copied


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',choices=['domestic','international','both'],default='both')
    p.add_argument('--cache-root',type=Path,default=ROOT/'.cache')
    p.add_argument('--output-dir',type=Path,default=ROOT/'data/reference/india_flights')
    p.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    p.add_argument('--validate-only',action='store_true',help='Capture representative routes before the full manifest')
    p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    scopes=['domestic','international'] if args.scope=='both' else [args.scope]
    for scope in scopes:
        config=country_config('IN',scope);pairs=config['manifest']['routes'];priority=PROBES[scope]
        if args.validate_only:pairs=priority
        else:pairs=[x for x in priority if list(x) in pairs]+[tuple(x) for x in pairs if tuple(x) not in priority]
        cache=args.cache_root/f'google-flights-india{"-international" if scope=="international" else ""}'
        output=args.output_dir/f'{DAY}{"-international" if scope=="international" else ""}.json.gz'
        stopped=None
        if not args.prepare_only:
            print(f'{scope}: reused {seed_usd_captures(cache,config)} exact-date USD captures',flush=True)
            try:asyncio.run(capture(cache,DAY,pairs,args.concurrency,config))
            except RuntimeError as error:stopped=error
        # Validation captures stay in the cache. Published output always reports
        # the whole manifest so a small probe run cannot imply full coverage.
        if not args.validate_only:prepare(cache,output,DAY,config['manifest']['routes'],config)
        if stopped:
            print(f'{stopped}; successful captures retained, collection not retried',file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())
