"""Resume sourced Türkiye flights on one local departure date; reuse compatible captures and original currencies."""
import argparse
import asyncio
import gzip
import json
from pathlib import Path
import sys
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,country_config,prepare
from scripts.prepare_turkiye_routes import CACHE,DAY
from scripts.prepare_africa_flights import validate_query,seed,budget,collection_routes


def prepare_cached(cache,output,cfg):
    if cfg['manifest'].get('archive_reuse_routes'):
        raise ValueError('New official timetable supplements require review; this dated Türkiye manifest has none')
    for a,b in cfg['manifest']['routes']:
        path=cache/f'{DAY}-{a}-{b}.json'
        if path.exists():
            q=json.loads(path.read_text())
            # Retain valid dated rows even when the source rejected other rows.
            checked={**q,'status':'results' if q['flights'] else 'no_matching_direct_flights'}
            checked.pop('rejected_flights',None)
            validate_query(checked,(DAY,a,b),cfg)
    with tempfile.TemporaryDirectory(prefix='suntrain-turkiye-prepare-') as temporary:
        prepared=Path(temporary)/'reference.json.gz'
        prepare(cache,prepared,DAY,cfg['manifest']['routes'],cfg)
        with gzip.open(prepared,'rt') as stream:r=json.load(stream)
    m=r['metadata'];m['fare_context'].update(currency='mixed',currencies=['USD','EUR','MYR'],new_capture_currency='USD')
    m.update(queries_reused=sum(bool(q.get('reused_source')) for q in m['queries']),
        collection_strategy='Sourced Istanbul worldwide and selected domestic routes, one origin-local date; reused quotes unchanged, new captures USD',
        source_gaps=cfg['manifest']['source_gaps'],unresolved_airports=cfg['manifest']['unresolved_airports'])
    air={a['code']:a for a in r['airports']}
    m['coverage_by_geography']={}
    for scope in ['domestic','international']:
        records=[f for f in r['flights'] if (air[f['origin']]['country']==air[f['destination']]['country'])==(scope=='domestic')]
        m['coverage_by_geography'][scope]=dict(flights=len(records),routes=len({(f['origin'],f['destination']) for f in records}),priced_flights=sum(bool(f.get('price')) for f in records))
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp')
    with temporary.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write(json.dumps(r,separators=(',',':')).encode())
    from dashboard.flight_profiles import load_domestic
    load_domestic(temporary,'TR')
    temporary.replace(output)
    return dict(flights=len(r['flights']),airports=len(air),reused=m['queries_reused'],coverage=m['coverage_by_geography'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=CACHE)
    parser.add_argument('--output',type=Path,default=ROOT/f'data/reference/turkiye_flights/{DAY}.json.gz')
    parser.add_argument('--seed',action='store_true');parser.add_argument('--dry-run',action='store_true');parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();cfg=country_config('TR')
    cfg['capture_context']=dict(parser='turkiye-origin-local-v1',max_duration=86400,currency='USD',adults=1,cabin='economy',trip_type='one_way')
    if args.seed:print(json.dumps(seed(args.cache,cfg)),flush=True)
    print(json.dumps(budget(args.cache,cfg)),flush=True)
    if args.dry_run:return 0
    stopped=None
    if not args.prepare_only:
        fresh=args.cache/'new-usd'
        pending=collection_routes(args.cache,cfg)
        collection={**cfg,'queries':[(DAY,a,b) for a,b in pending]}
        try:asyncio.run(capture(fresh,DAY,pending,2,collection))
        except RuntimeError as error:
            stopped=error;(args.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error))))
        finally:
            for path in fresh.glob(f'{DAY}-*.json'):
                target=args.cache/path.name;temporary=target.with_name(target.name+'.tmp')
                shutil.copyfile(path,temporary);temporary.replace(target)
    print(json.dumps(prepare_cached(args.cache,args.output,cfg)),flush=True)
    if stopped:print(str(stopped),file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
