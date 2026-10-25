"""Singapore international flights, exact SIN/XSP identities and captured USD fares."""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import parse_qs,urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,country_config,expected_queries,prepare


def seed_usd_captures(cache,config,source=None):
    """Reuse complete exact-date USD searches; never relabel other currencies."""
    source=source or ROOT/'.cache/google-flights-gulf'
    expected=set(expected_queries('2026-11-02',config['manifest']['routes'],config));copied=0
    cache.mkdir(parents=True,exist_ok=True)
    for path in sorted(source.glob('*/*.json')):
        if path.name.endswith('.error.json'):continue
        q=json.loads(path.read_text());key=(q['date'],q['origin'],q['destination'])
        if key not in expected or parse_qs(urlparse(q.get('url','')).query).get('curr')!=['USD']:continue
        if any(f.get('price') and tuple(f['price'].get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way') for f in q['flights']):continue
        target=cache/path.name
        if not target.exists():
            temporary=target.with_suffix('.tmp');shutil.copyfile(path,temporary);temporary.replace(target);copied+=1
    return copied


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-singapore')
    p.add_argument('--output',type=Path,default=ROOT/'data/reference/singapore_flights/2026-11-02.json.gz')
    p.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    config=country_config('SG','international');pairs=config['manifest']['routes'];stopped=None
    priority=[('SIN','KUL'),('XSP','SZB'),('SZB','XSP'),('SIN','EWR'),('EWR','SIN'),('SIN','SYD'),('SYD','SIN')]
    pairs=[x for x in priority if list(x) in pairs]+[tuple(x) for x in pairs if tuple(x) not in priority]
    if not args.prepare_only:
        print(f'Reused {seed_usd_captures(args.cache,config)} exact-date USD captures',flush=True)
        try:asyncio.run(capture(args.cache,'2026-11-02',pairs,args.concurrency,config))
        except RuntimeError as error:stopped=error
    prepare(args.cache,args.output,'2026-11-02',pairs,config)
    if stopped:
        print(f'{stopped}; successful captures retained, collection not retried',file=sys.stderr);sys.exit(2)
