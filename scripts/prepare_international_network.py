"""Shared exact-airport international captures, original fares, no repeated queries."""
import argparse
import asyncio
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.international_network import CITIES, DAY, NOTE, consumer_queries, window
from scripts.prepare_google_flights import capture


def config():
    manifest=json.loads((ROOT/'data/sources/international_network_routes.json').read_text())
    by_view={city:consumer_queries(manifest,city) for city in ['international_network',*CITIES]}
    expected=sorted({q for qs in by_view.values() for q in qs})
    return dict(country='NETWORK',scope='international',manifest=manifest,timezone='UTC',end_date=DAY,
        max_duration=86400,capture_prices=True,currency='USD',zones={a['code']:a['timezone'] for a in manifest['airports']},
        queries=expected,queries_by_view=by_view)


def valid_price(price):
    return (price.get('currency') in {'USD','MYR'} and type(price.get('amount_minor')) is int and price['amount_minor']>0
        and tuple(price.get(k) for k in ('adults','cabin','trip_type'))==(1,'economy','one_way'))


def validate_query(query, key):
    if (query.get('date'),query.get('origin'),query.get('destination'))!=tuple(key):raise ValueError('Wrong cached query identity')
    datetime.fromisoformat(query['captured_at'])
    if query['status'] not in {'results','no_matching_direct_flights','rejected_source_records'}:raise ValueError('Unsupported cached query status')
    if (query['status']=='results')!=bool(query['flights']):raise ValueError('Cached query status disagrees with its records')
    for f in query['flights']:
        if (f['origin'],f['destination'],f['source_date'])!=(key[1],key[2],key[0]):raise ValueError('Wrong cached segment identity')
        if not 60<=f['arrival']-f['departure']<=86400:raise ValueError('Invalid cached segment duration')
        if f.get('price') and not valid_price(f['price']):raise ValueError('Invalid cached fare context')


def seed(cache,cfg,sources=None):
    """Newest successful schedule wins; keep same-schedule offers by currency."""
    expected=set(cfg['queries']); candidates={};rejected=[]
    sources=sources if sources is not None else sorted(p for p in (ROOT/'.cache').glob('google-flights*') if p.is_dir() and p!=cache)
    for source in sources:
        for path in sorted(source.rglob('*.json')):
            if path.name.endswith('.error.json'):continue
            try:
                q=json.loads(path.read_text());key=(q.get('date'),q.get('origin'),q.get('destination'))
                if key not in expected:continue
                validate_query(q,key)
                if q['status']=='rejected_source_records':raise ValueError('Source records were rejected; query needs a fresh capture')
            except (ValueError,KeyError,TypeError) as error:
                rejected.append(dict(path=str(path),reason=str(error)));continue
            candidates.setdefault(key,[]).append((path,q))
    reused=0
    for key,items in sorted(candidates.items()):
        target=cache/('-'.join(key)+'.json')
        if target.exists():continue
        items.sort(key=lambda item:(item[1]['captured_at'],str(item[0])))
        q=dict(items[-1][1]);offers={}
        for path,old in items:
            for f in old['flights']:
                if f.get('price'):
                    identity=(f['id'],f['departure'],f['arrival']);offers.setdefault(identity,[]).append(f['price'])
        q['flights']=[dict(f) for f in q['flights']]
        for f in q['flights']:
            prices=offers.get((f['id'],f['departure'],f['arrival']),[])
            if prices:f['price']=min(prices,key=lambda p:(p['currency']!='USD',p['amount_minor'],p['captured_at']))
        q['reused_sources']=[dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),url=x.get('url'),captured_at=x['captured_at'],page_sha256=x.get('page_sha256')) for p,x in items]
        latest={f['id']:(f['departure'],f['arrival']) for f in q['flights']}
        q['superseded_schedule_records']=sorted({f['id'] for _,old in items[:-1] for f in old['flights']
            if latest.get(f['id'])!=(f['departure'],f['arrival'])})
        temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(q,separators=(',',':')));temporary.replace(target);reused+=1
    report=dict(routes=len(cfg['manifest']['routes']),airports=len(cfg['manifest']['airports']),queries=len(expected),
        reused=reused,cached=sum((cache/('-'.join(q)+'.json')).exists() for q in expected),rejected_caches=rejected)
    report['required_searches']=report['queries']-report['cached']
    (cache/'preflight-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return report


def prepare(cache,output,cfg):
    queries=[];records={};missing=[];failed=[];conflicts=[]
    for key in cfg['queries']:
        path=cache/('-'.join(key)+'.json')
        if not path.exists():
            missing.append(list(key));error=path.with_suffix('.error.json')
            if error.exists():failed.append(json.loads(error.read_text()))
            continue
        q=json.loads(path.read_text());validate_query(q,key)
        queries.append({k:v for k,v in q.items() if k!='flights'})
        for f in q['flights']:
            previous=records.get(f['id'])
            if previous and previous!=f:conflicts.append(dict(id=f['id'],reason='Conflicting exact flight identity across queries'))
            if previous and previous!=f:raise ValueError(f"Conflicting flight snapshots: {f['id']}")
            records[f['id']]=f
    if not records:raise ValueError('No international flights collected')
    windows=[window('UTC'),*(window(zone) for _,zone in CITIES.values())]
    start=min(w[0] for w in windows);end=max(w[1] for w in windows)
    fs=sorted((f for f in records.values() if f['departure']<end and f['arrival']>=start),key=lambda f:(f['departure'],f['id']))
    airports=cfg['manifest']['airports']
    metadata=dict(profile='international_network',scope='international',start_date=DAY,end_date=DAY,timezone='UTC',
        archive_start=start,archive_end=end,queries=queries,queries_by_view=cfg['queries_by_view'],countries=cfg['manifest']['countries'],
        uncollected_queries=missing,failed_queries=failed,unresolved_airports=[],schedule_conflicts=conflicts,
        source='Google Flights airport-specific search snapshot',source_url='https://www.google.com/travel/flights',
        source_date=max(q['captured_at'][:10] for q in queries),replay_note=NOTE,
        fare_context=dict(currency='mixed',currencies=['USD','MYR'],adults=1,cabin='economy',trip_type='one_way',
            basis='Lowest returned quote in its original currency; USD preferred when both USD and MYR exist; no conversion'),
        airport_source='OurAirports',airport_source_url='https://ourairports.com/data/',
        route_source_sha256=cfg['manifest']['route_source_sha256'],route_source_url='https://www.narita-airport.jp/en/discover/citylist/',
        fare_context_unverified_queries=sum(bool(q.get('price_error')) for q in queries),
        airlines=sorted({f['airline'] for f in fs}))
    stop=cache/'collection-stop.json'
    if stop.exists():metadata['collection_stop']=json.loads(stop.read_text())
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix('.tmp')
    with temp.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(dict(metadata=metadata,airports=airports,flights=fs),separators=(',',':')).encode())
    temp.replace(output)
    print(json.dumps(dict(archive_flights=len(fs),queries=len(queries),missing=len(missing),bytes=output.stat().st_size,
        sha256=hashlib.sha256(output.read_bytes()).hexdigest())),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/google-flights-international-network')
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/international_network/2026-11-02.json.gz')
    parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    args=parser.parse_args();cfg=config();args.cache.mkdir(parents=True,exist_ok=True)
    if args.prepare_only:prepare(args.cache,args.output,cfg);return 0
    seed(args.cache,cfg)
    if args.dry_run:return 0
    stopped=None
    (args.cache/'collection-stop.json').unlink(missing_ok=True)
    try:asyncio.run(capture(args.cache,DAY,cfg['manifest']['routes'],args.concurrency,cfg))
    except RuntimeError as error:
        stopped=error
        (args.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error),at=datetime.now(timezone.utc).isoformat())))
    prepare(args.cache,args.output,cfg)
    if stopped:
        print(f'{stopped}; successful captures retained; no challenge retries',file=sys.stderr);return 2
    return 0


if __name__=='__main__':sys.exit(main())
