"""Prepare Europe–Americas from existing exact-date captures, with zero network requests."""
import argparse
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import parse_qs,urlparse
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import country_config,prepare
from scripts.prepare_europe_groups import CONTEXT as GROUP_CONTEXT
from scripts.prepare_europe_flights import CONTEXT as LEGACY_CONTEXT

DAY='2026-11-02'
CACHE=ROOT/'.cache/google-flights-europe-groups-eur-v1'
LEGACY=ROOT/'.cache/google-flights-europe-eur-v1'


def validate_query(query,key,cfg):
    if (query['date'],query['origin'],query['destination'])!=tuple(key):
        raise ValueError('Wrong cached query identity')
    if query.get('capture_context') not in [GROUP_CONTEXT,LEGACY_CONTEXT]:
        raise ValueError('Incompatible parser or fare context')
    if parse_qs(urlparse(query['url']).query).get('curr')!=['EUR']:
        raise ValueError('Capture did not request EUR')
    if datetime.fromisoformat(query['captured_at'].replace('Z','+00:00')).tzinfo is None:
        raise ValueError('Capture timestamp needs a time zone')
    if query.get('rejected_flights') or query['status'] not in {'results','no_matching_direct_flights'}:
        raise ValueError('Source has rejected or unsuccessful results')
    if bool(query['flights'])!=(query['status']=='results'):
        raise ValueError('Capture status disagrees with records')
    for f in query['flights']:
        if (f['source_date'],f['origin'],f['destination'])!=tuple(key):
            raise ValueError('Wrong exact segment')
        if not 60<=f['arrival']-f['departure']<=query['capture_context']['max_duration']:
            raise ValueError('Invalid cached duration')
        if datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()!=DAY:
            raise ValueError('Wrong origin-local departure date')
        price=f.get('price')
        if price and (query.get('price_error') or type(price.get('amount_minor')) is not int or price['amount_minor']<=0
            or tuple(price.get(k) for k in ('currency','adults','cabin','trip_type'))!=('EUR',1,'economy','one_way')):
            raise ValueError('Invalid or unverified cached fare')


def selected_captures(cfg,cache=CACHE,fallback=LEGACY):
    selected={};missing=[]
    for a,b in cfg['manifest']['routes']:
        key=(DAY,a,b);filename=f'{DAY}-{a}-{b}.json'
        path=next((base/filename for base in [cache,fallback] if base is not None and (base/filename).exists()),None)
        if path is None:
            missing.append(list(key));continue
        q=json.loads(path.read_text());validate_query(q,key,cfg)
        selected[key]=(path,q)
    return selected,missing


def budget(cfg,cache=CACHE,fallback=LEGACY):
    selected,missing=selected_captures(cfg,cache,fallback)
    return dict(directions=len(cfg['manifest']['routes']),cached=len(selected),missing_queries=missing,
        flights=sum(len(q['flights']) for _,q in selected.values()),new_network_requests=0,
        dates=[DAY],currency='EUR',policy='Reuse exact-date all-airline captures; no network collection in this command')


def prepare_cached(output,cfg,cache=CACHE,fallback=LEGACY):
    selected,missing=selected_captures(cfg,cache,fallback)
    with tempfile.TemporaryDirectory(prefix='suntrain-europe-americas-') as temporary:
        staging=Path(temporary)
        for key,(path,q) in selected.items():
            # Source JSON stays untouched. Record its byte hash alongside its original context.
            try:label=str(path.relative_to(ROOT))
            except ValueError:label=str(path)
            target=staging/f'{key[0]}-{key[1]}-{key[2]}.json'
            target.write_text(json.dumps({**q,'reused_source':label,
                'reused_capture_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},separators=(',',':'))+'\n')
        prepared=staging/'prepared.json.gz'
        prepare(staging,prepared,DAY,cfg['manifest']['routes'],cfg)
        with gzip.open(prepared,'rt') as stream:reference=json.load(stream)
    reference['metadata'].update(scope='international',queries_reused=len(selected),new_network_requests=0,
        input_manifests=cfg['manifest']['input_manifests'],
        collection_strategy='Reuse all returned airlines from existing dated European captures on sourced cross-region routes; original EUR quotes, no conversion',
        regions=cfg['manifest']['regions'])
    output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_suffix('.tmp')
    with temporary.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(reference,separators=(',',':')).encode())
    temporary.replace(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=CACHE)
    parser.add_argument('--fallback-cache',type=Path,default=LEGACY)
    parser.add_argument('--output',type=Path,default=ROOT/f'data/reference/europe_americas_flights/{DAY}.json.gz')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();cfg=country_config('EUROPE_AMERICAS')
    if not args.dry_run:prepare_cached(args.output,cfg,args.cache,args.fallback_cache)
    print(json.dumps(budget(cfg,args.cache,args.fallback_cache)))
