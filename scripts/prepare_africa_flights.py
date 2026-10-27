"""Resume one-date Africa collection; preserve compatible cached quotes without conversion."""
import argparse
import asyncio
from collections import Counter,defaultdict
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import shutil
import tempfile
from urllib.parse import parse_qs,urlparse
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_google_flights import capture,country_config,prepare
from scripts.prepare_africa_routes import AFRICAN,CACHE,DAY,REGIONS


def validate_query(q,key,cfg):
    if tuple(q.get(k) for k in ('date','origin','destination'))!=tuple(key):raise ValueError('Wrong exact query')
    if datetime.fromisoformat(q['captured_at'].replace('Z','+00:00')).tzinfo is None:raise ValueError('Undated capture')
    if q.get('rejected_flights') or q.get('status') not in {'results','no_matching_direct_flights'}:raise ValueError('Rejected capture')
    if bool(q.get('flights'))!=(q['status']=='results'):raise ValueError('Capture status mismatch')
    # Empty old eight-hour searches cannot establish an empty long-haul result.
    if not q['flights'] and q.get('capture_context',{}).get('max_duration',28800)<86400:raise ValueError('Short parser empty result')
    identities={}
    for f in q['flights']:
        if tuple(f.get(k) for k in ('source_date','origin','destination'))!=tuple(key):raise ValueError('Wrong dated segment')
        if not 60<=f['arrival']-f['departure']<=86400:raise ValueError('Invalid duration')
        if datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()!=DAY:raise ValueError('Wrong local departure day')
        if f['id'] in identities and identities[f['id']]!=f:raise ValueError('Conflicting source identity')
        identities[f['id']]=f
        price=f.get('price')
        if price:
            currency=price.get('currency')
            if (q.get('price_error') or currency not in {'USD','EUR','MYR'} or
                parse_qs(urlparse(q['url']).query).get('curr')!=[currency] or
                tuple(price.get(k) for k in ('adults','cabin','trip_type'))!=(1,'economy','one_way') or
                type(price.get('amount_minor')) is not int or price['amount_minor']<=0):raise ValueError('Unverified fare')
    return q


def seed(cache,cfg):
    """Choose one intact most-recent compatible source per exact query; never merge schedules."""
    allowed=set(map(tuple,cfg['manifest']['routes']));candidates={};rejected=Counter()
    for directory in sorted((ROOT/'.cache').glob('google-flights*')):
        if not directory.is_dir() or directory.resolve()==cache.resolve():continue
        for path in sorted(directory.rglob(f'{DAY}-*.json')):
            parts=path.stem.split('-')
            if len(parts)!=5 or tuple(parts[-2:]) not in allowed:continue
            a,b=parts[-2:];key=(DAY,a,b)
            target=cache/path.name
            refresh=(a,b) in set(map(tuple,cfg.get('refresh_empty_queries',[])))
            if target.exists() and (not refresh or json.loads(target.read_text()).get('flights')):continue
            try:
                q=validate_query(json.loads(path.read_text()),key,cfg)
            except (ValueError,KeyError,TypeError) as e:
                rejected[str(e)]+=1;continue
            if target.exists() and not q['flights']:continue
            previous=candidates.get(key)
            instant=lambda record:datetime.fromisoformat(record['captured_at'].replace('Z','+00:00')).timestamp()
            if previous is None or instant(q)>instant(previous[1]):candidates[key]=(path,q)
    cache.mkdir(parents=True,exist_ok=True)
    for key,(path,q) in sorted(candidates.items()):
        target=cache/f'{DAY}-{key[1]}-{key[2]}.json'
        payload={**q,'reused_source':str(path.relative_to(ROOT)),'reused_capture_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if target.exists():payload['previous_empty_capture']=json.loads(target.read_text())
        temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(payload,separators=(',',':'))+'\n');temporary.replace(target)
    return dict(seeded=len(candidates),incompatible_sources=dict(sorted(rejected.items())))


def budget(cache,cfg):
    routes=cfg['manifest']['routes'];archive=set(map(tuple,cfg['manifest'].get('archive_reuse_routes',[])))
    found=[(a,b) for a,b in routes if (cache/f'{DAY}-{a}-{b}.json').exists() or (a,b) in archive]
    new_queries=sum(not (cache/'new-usd'/f'{DAY}-{a}-{b}.json').exists() for a,b in collection_routes(cache,cfg))
    return dict(directions=len(routes),cached=len(found),missing=len(routes)-len(found),new_queries_needed=new_queries,dates=[DAY],new_capture_currency='USD')


def collection_routes(cache,cfg):
    # Never turn an unusable/missing reuse-only capture into a new search outside
    # the starter footprint. Its absence remains a reported coverage gap.
    return [(a,b) for a,b in cfg['manifest']['new_collection_routes'] if not (cache/f'{DAY}-{a}-{b}.json').exists()]


def prepare_cached(cache,output,cfg):
    supplements=defaultdict(list);snapshot=cfg['manifest'].get('archive_snapshot')
    if snapshot:
        source=ROOT/snapshot['path']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=snapshot['sha256']:raise ValueError('Pinned timetable archive changed')
        with gzip.open(source,'rt') as stream:archived=json.load(stream)
        allowed=set(map(tuple,cfg['manifest']['routes']))
        for f in archived['flights']:
            if f.get('schedule_source')=='ryanair_public_timetable' and f.get('source_date')==DAY and (f['origin'],f['destination']) in allowed:
                supplements[(f['origin'],f['destination'])].append({k:v for k,v in f.items() if k!='flight_scope'})
    for a,b in cfg['manifest']['routes']:
        path=cache/f'{DAY}-{a}-{b}.json'
        if path.exists():
            q=json.loads(path.read_text())
            # Retain valid dated rows even when the source rejected other rows.
            checked={**q,'status':'results' if q['flights'] else 'no_matching_direct_flights'}
            checked.pop('rejected_flights',None)
            validate_query(checked,(DAY,a,b),cfg)
    with tempfile.TemporaryDirectory(prefix='suntrain-africa-prepare-') as temporary:
        staging=Path(temporary);added_ids=[];overlap_ids=[];archive_only=0
        for a,b in cfg['manifest']['routes']:
            filename=f'{DAY}-{a}-{b}.json';path=cache/filename
            extras=supplements.get((a,b),[])
            if not extras:
                if path.exists():(staging/filename).symlink_to(path.resolve())
            else:
                if path.exists():
                    q=json.loads(path.read_text());q['google_status']=q['status'];q['collection_kind']='google_with_archived_timetable'
                else:
                    archive_only+=1
                    q=dict(date=DAY,origin=a,destination=b,url=extras[0]['source_page'],captured_at=max(f['source_captured_at'] for f in extras),
                        flights=[],status='results',collection_kind='reused_official_timetable',reused_source=snapshot['path'])
                known={f['id'] for f in q['flights']}
                added=[f for f in extras if f['id'] not in known]
                overlap_ids.extend(f['id'] for f in extras if f['id'] in known)
                q['flights'].extend(added);added_ids.extend(f['id'] for f in added)
                q.update(status='results',archive_snapshot=snapshot,archive_added_flight_ids=[f['id'] for f in added])
                # Google wins overlapping identities; archive-only dated records
                # keep their original source and never acquire an inferred fare.
                checked={**q};checked.pop('rejected_flights',None)
                validate_query(checked,(DAY,a,b),cfg)
                (staging/filename).write_text(json.dumps(q,separators=(',',':'))+'\n')
            error=cache/f'{DAY}-{a}-{b}.error.json'
            if error.exists():(staging/error.name).symlink_to(error.resolve())
        stop=cache/'collection-stop.json'
        if stop.exists():(staging/stop.name).symlink_to(stop.resolve())
        prepared=staging/'reference.json.gz'
        prepare(staging,prepared,DAY,cfg['manifest']['routes'],cfg)
        with gzip.open(prepared,'rt') as stream:r=json.load(stream)
    m=r['metadata'];m['fare_context'].update(currency='mixed',currencies=['USD','EUR','MYR'],new_capture_currency='USD')
    google_queries=[q for q in m['queries'] if q.get('collection_kind')!='reused_official_timetable']
    m.update(source='Google Flights and reused official Ryanair dated timetable captures',
        archive_supplement=dict(snapshot=snapshot,added_flights=len(added_ids),added_flight_ids=sorted(added_ids),
            overlapping_identities=len(overlap_ids),overlap_policy='Prefer the Google capture for overlapping identities; no implicit fare transfer',directions_without_google_capture=archive_only),
        google_capture_coverage=dict(queries=len(google_queries),reused=sum(bool(q.get('reused_source')) for q in google_queries),
            not_returned=sum(q.get('google_status',q['status'])=='no_matching_direct_flights' for q in google_queries)))
    air={a['code']:a for a in r['airports']}
    def region(f):
        a,b=(air[f[k]]['country'] for k in ('origin','destination'))
        return 'domestic' if a==b else 'intra_african' if a in AFRICAN and b in AFRICAN else 'intercontinental'
    m.update(queries_reused=sum(bool(q.get('reused_source')) for q in m['queries']),
        collection_strategy='Sourced routes, one origin-local date, all returned airlines; reuse original currencies; new captures USD',
        coverage_by_geography={k:dict(flights=len(fs),routes=len({(f['origin'],f['destination']) for f in fs}),priced_flights=sum(bool(f.get('price')) for f in fs)) for k in ('domestic','intra_african','intercontinental') if (fs:=[f for f in r['flights'] if region(f)==k])},
        source_gaps=cfg['manifest']['source_gaps'],unresolved_airports=cfg['manifest']['unresolved_airports'])
    regional={}
    for name,countries in REGIONS.items():
        codes={c for c,a in air.items() if a['country'] in countries}
        def touches(a,b):return bool({a,b}&codes)
        planned=[p for p in cfg['manifest']['routes'] if touches(*p)]
        queries=[q for q in m['queries'] if touches(q['origin'],q['destination'])]
        records=[f for f in r['flights'] if touches(f['origin'],f['destination'])]
        failed=[q for q in m['failed_queries'] if touches(q['origin'],q['destination'])]
        regional[name]=dict(airports_planned=len(codes),airports_returned=len(codes & {f[k] for f in records for k in ('origin','destination')}),
            routes_planned=len(planned),queries_captured=len(queries),routes_returned=len({(f['origin'],f['destination']) for f in records}),
            queries_not_returned=sum(q['status']=='no_matching_direct_flights' for q in queries),failed_queries=len(failed),
            unattempted_queries=len(planned)-len(queries)-len(failed),flights=len(records))
    m['coverage_by_african_region']=regional
    if cfg['manifest'].get('starter_record_audit'):
        records={f['id']:f for f in r['flights']}
        for key in ['starter_record_audit','offline_recovery_audit']:
            audit=cfg['manifest'][key]
            if not set(audit['ids'])<=records.keys():raise ValueError('Previously preserved African flight records are missing')
            original=[records[key] for key in audit['ids']]
            digest=hashlib.sha256(json.dumps(sorted(original,key=lambda f:f['id']),sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if len(original)!=audit['count'] or digest!=audit['sha256']:raise ValueError('Previously preserved African flight records changed')
        m['expansion']=dict(starter_manifest=cfg['manifest']['starter_manifest'],original_records_preserved=cfg['manifest']['starter_record_audit']['count'],offline_recovered_flights=cfg['manifest']['offline_recovery_audit']['count'],deferred_directions_reviewed=658,deferred_directions_selected=len(cfg['manifest']['expanded_routes']),excluded=cfg['manifest']['expansion_exclusions'],resolved_starter_airports=cfg['manifest']['resolved_starter_airports'])
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp')
    with temporary.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write(json.dumps(r,separators=(',',':')).encode())
    from dashboard.flight_profiles import load_domestic
    load_domestic(temporary,'AFRICA')
    temporary.replace(output)
    return dict(flights=len(r['flights']),airports=len(air),reused=m['queries_reused'],coverage=m['coverage_by_geography'])


def publish_captures(fresh,cache,pairs):
    """Publish only this run's pending queries, preserving reviewed reused results."""
    allowed={f'{DAY}-{a}-{b}{suffix}' for a,b in pairs for suffix in ('.json','.error.json')}
    for path in fresh.glob(f'{DAY}-*.json'):
        if path.name not in allowed:continue
        target=cache/path.name;temporary=target.with_name(target.name+'.tmp')
        shutil.copyfile(path,temporary);temporary.replace(target)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=CACHE)
    parser.add_argument('--output',type=Path,default=ROOT/f'data/reference/africa_flights/{DAY}.json.gz')
    parser.add_argument('--seed',action='store_true');parser.add_argument('--dry-run',action='store_true');parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();cfg=country_config('AFRICA')
    cfg['refresh_empty_queries']=cfg['manifest'].get('refresh_empty_queries',[])
    cfg['capture_context']=dict(parser='africa-origin-local-v1',max_duration=86400,currency='USD',adults=1,cabin='economy',trip_type='one_way')
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
            publish_captures(fresh,args.cache,pending)
    print(json.dumps(prepare_cached(args.cache,args.output,cfg)),flush=True)
    if stopped:print(str(stopped),file=sys.stderr);return 2
    return 0

if __name__=='__main__':sys.exit(main())
