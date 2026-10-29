"""A separate, evidence-ranked 300-search follow-up to the completed first pass.

Use `manifest` once, then `collect` at each 100-search review checkpoint. `finalize`
publishes the cumulative supplement and World snapshot without more searches.
The original campaign's source ledger, 1,000-search cap and journal stay intact.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard import international_expansion as adapter, world_flights as world
from scripts import prepare_international_expansion as preparation
from scripts.discover_international_expansion import (
    CACHE as ORIGINAL_CACHE, SOURCE as ORIGINAL_SOURCE, DAY, audit, digest,
    merged_attempts, read, relative, save, validate_query, Airports)
from scripts.prepare_google_flights import capture

CACHE = ROOT / '.cache/international-followup'
SOURCE = ROOT / 'data/sources/world_international_followup.json.gz'
CAPTURES = ROOT / '.cache/google-flights-world-international-usd-followup'
LIMITS = {'europe_airlines': 150, 'intercontinental': 100, 'asia_gulf': 50}


def ranked_candidates(parent, baseline, index):
    """Dated captures outrank map-only evidence; never construct airport pairs."""
    known = {tuple(r['query']) for r in index['queries']}
    charged = {tuple(r['query']) for r in parent['collection']['attempts']}
    rows = {tuple(r['query']): r for r in parent['ledger']}
    dated = Counter((f['origin'], f['destination']) for f in baseline['flights']
                    if DAY in f.get('provenance', {}).get('source_dates', []))
    routes = {(f['origin'], f['destination']) for f in baseline['flights']}
    queues = {name: [] for name in LIMITS}
    for query in parent['remaining_queue']:
        key = tuple(query)
        if key[0] != DAY or key in known or key in charged:
            continue
        row = rows[key]
        if row['stream'] not in queues or not row.get('evidence'):
            continue
        a, b = key[1:]
        evidence = row['evidence']
        queues[row['stream']].append(dict(query=list(key), stream=row['stream'],
            missing_direction=(a,b) not in routes, dated_reverse_flights=dated[(b,a)],
            dated_same_direction_flights=dated[(a,b)], evidence=evidence))
    for rows in queues.values():
        rows.sort(key=lambda r: (
            not bool(r['dated_reverse_flights'] or r['dated_same_direction_flights']),
            not r['missing_direction'], -r['dated_reverse_flights'],
            -sum(e['kind'] in {'airport','airline'} for e in r['evidence']), tuple(r['query'])))
    return queues


def build_manifest(cache=CACHE):
    if SOURCE.exists():
        manifest = read(SOURCE)
        if manifest['search_limit'] != 300 or manifest['workstream_limits'] != LIMITS:
            raise ValueError('Existing follow-up configuration changed; do not reset its budget')
        return manifest
    parent = read(ORIGINAL_SOURCE)
    if len(parent['collection']['attempts']) != 1000 or parent['collection'].get('collection_stop'):
        raise ValueError('The completed, unchallenged first pass is required')
    baseline = world.load_reference(DAY)
    save(cache/'baseline.json.gz', baseline)
    save(cache/'supplement-before.json.gz', adapter.load_reference())
    index = read(ORIGINAL_CACHE/'cache-index.json.gz')
    queues = ranked_candidates(parent, baseline, index)
    chosen = {name: rows[:LIMITS[name]] for name,rows in queues.items()}
    if any(len(chosen[name]) != limit for name,limit in LIMITS.items()):
        raise ValueError('Insufficient validated candidates; do not invent route pairs')
    # Each review samples all streams; the three checkpoint totals are exactly
    # 100 each, with 150 Europe / 100 bridges / 50 Asia-Gulf across the campaign.
    checkpoints = [(50,33,17), (50,34,16), (50,33,17)]
    selected = []
    for counts in checkpoints:
        batch = []
        for (name,_),count in zip(LIMITS.items(),counts):
            batch.extend(chosen[name][:count])
            chosen[name] = chosen[name][count:]
        selected.extend(row for _,_,row in sorted(
            ((i+.5)/len(rows),name,row)
            for name in LIMITS for rows in [[r for r in batch if r['stream']==name]]
            for i,row in enumerate(rows)))
    selected_keys = {tuple(r['query']) for r in selected}
    manifest = dict(profile='world_international_followup', day=DAY, timezone='UTC', currency='USD',
        search_limit=300, concurrency=2, checkpoint_size=100, workstream_limits=LIMITS,
        parent_campaign=dict(path=relative(ORIGINAL_SOURCE), sha256=digest(ORIGINAL_SOURCE.read_bytes()), attempts=1000),
        baseline_inputs=baseline['metadata']['inputs'], baseline_counts=preparation.metrics(baseline),
        baseline_world_sha256=digest(world.reference_path().read_bytes()),
        baseline_supplement_sha256=digest(adapter.reference_path().read_bytes()),
        airports=parent['airports'], candidates=selected, new_searches=[r['query'] for r in selected],
        unresolved_airports=parent['unresolved_airports'], unresolved_routes=parent['unresolved_routes'],
        remaining_queue=[q for q in parent['remaining_queue'] if tuple(q) not in selected_keys],
        ranking='Dated reverse/same-direction captures, missing direction, reverse frequency, published map corroboration, exact IATA tie-break.',
        limitations=['Reverse captures are prioritisation evidence, not proof of a return flight.',
            'Seasonal route maps do not prove service on 2 November.',
            'Only origin-local 2 November; unobserved adjacent-day flights remain gaps.',
            'Empty means not returned; partial worldwide passenger coverage; no new domestic collection.'],
        collection=dict(attempts=[], searches_attempted=0))
    save(SOURCE, manifest)
    print(world.canonical_json(dict(selected=len(selected),
        dated_evidence=sum(bool(r['dated_reverse_flights'] or r['dated_same_direction_flights']) for r in selected),
        workstreams=LIMITS)), flush=True)
    return manifest


def check_parent(manifest):
    if manifest.get('search_limit') != 300 or manifest.get('workstream_limits') != LIMITS:
        raise ValueError('The follow-up is capped at 300 searches with fixed stream allocations')
    keys = [tuple(q) for q in manifest['new_searches']]
    if len(keys) != 300 or len(set(keys)) != 300:
        raise ValueError('The follow-up requires 300 unique queries')
    if dict(Counter(r['stream'] for r in manifest['candidates'])) != LIMITS:
        raise ValueError('Follow-up stream allocations changed')
    if [r['query'] for r in manifest['candidates']] != manifest['new_searches']:
        raise ValueError('Follow-up query evidence changed')
    if digest(ORIGINAL_SOURCE.read_bytes()) != manifest['parent_campaign']['sha256']:
        raise ValueError('The first campaign changed; review before resuming')
    previous = read(ORIGINAL_SOURCE)['collection']['attempts']
    if len(previous) != 1000:
        raise ValueError('The original campaign journal must remain intact')
    if set(keys) & {tuple(a['query']) for a in previous}:
        raise ValueError('Do not repeat a first-pass attempt, including interrupted queries')


def collection_summary(manifest, attempts):
    airports = Airports(read(CACHE/'baseline.json.gz'))
    successful, failed, missing, rejected = [], [], [], []
    for attempt in attempts:
        key = tuple(attempt['query'])
        path = CAPTURES/('-'.join(key)+'.json')
        if path.exists():
            q = read(path)
            try:
                validate_query(q,key,airports)
            except (ValueError,KeyError,TypeError) as error:
                rejected.append(dict(query=list(key),reason=str(error)))
            else:
                successful.append(dict(query=list(key),path=relative(path),sha256=digest(path.read_bytes()),
                    captured_at=q['captured_at'], records=len(q['flights']),
                    priced_records=sum(bool(f.get('price')) for f in q['flights'])))
        elif path.with_suffix('.error.json').exists():
            failed.append(dict(query=list(key),error=read(path.with_suffix('.error.json'))))
        else:
            missing.append(list(key))
    streams = {tuple(r['query']):r['stream'] for r in manifest['candidates']}
    result = dict(attempts=attempts,searches_attempted=len(attempts),successful_captures=len(successful),
        nonempty_queries=sum(q['records']>0 for q in successful),
        empty_results=sum(q['records']==0 for q in successful),
        returned_records=sum(q['records'] for q in successful),
        priced_records=sum(q['priced_records'] for q in successful),captures=successful,
        failed_queries=failed,interrupted_queries=missing,rejected_queries=rejected,
        workstreams=dict(Counter(streams[tuple(a['query'])] for a in attempts)))
    stop=CAPTURES/'collection-stop.json'
    if stop.exists(): result['collection_stop']=read(stop)
    return result


def check_baseline(cache,manifest):
    for filename,field in [('baseline.json.gz','baseline_world_sha256'),
                           ('supplement-before.json.gz','baseline_supplement_sha256')]:
        path=cache/filename
        if not path.exists() or digest(path.read_bytes())!=manifest[field]:
            raise ValueError('Frozen follow-up baseline missing or changed; do not reset the comparison')


def publish_checkpoint(cache=CACHE):
    manifest=read(SOURCE)
    check_parent(manifest)
    check_baseline(cache,manifest)
    parent=read(ORIGINAL_SOURCE)
    manifest['unresolved_airports']=parent['unresolved_airports']
    manifest['unresolved_routes']=parent['unresolved_routes']
    attempts=merged_attempts(manifest,CAPTURES/'attempts.json')
    if len(attempts)>300:
        raise ValueError('The follow-up exceeded its 300-search cap')
    summary=collection_summary(manifest,attempts)
    manifest['collection']=summary
    save(SOURCE,manifest)
    audit(ORIGINAL_CACHE)
    supplement=preparation.prepare(ORIGINAL_CACHE,source=SOURCE)
    result=world.prepare(cache/f'world-after-{len(attempts)}.json.gz')
    before=read(cache/'baseline.json.gz')
    previous={world.identity(f) for f in before['flights']}
    current={world.identity(f) for f in result['flights']}
    query_streams={tuple(r['query']):r['stream'] for r in manifest['candidates']}
    airports={a['code']:a for a in result['airports']}
    added_by_stream=Counter(query_streams.get(preparation.record_query_key(f,airports),'cache_recovery')
        for f in result['flights'] if world.identity(f) not in previous)
    score=dict(before=preparation.metrics(before),after=preparation.metrics(result),
        identities_added=len(current-previous),identities_removed=len(previous-current),
        added_by_workstream=dict(added_by_stream))
    score['delta']={k:score['after'][k]-score['before'][k] for k in score['before']}
    summary.update(score)
    manifest['collection']=summary
    save(SOURCE,manifest)
    supplement['metadata']['source_manifest']=dict(path=relative(SOURCE),sha256=digest(SOURCE.read_bytes()))
    save(adapter.reference_path(),supplement)
    result['metadata']['inputs'][relative(adapter.reference_path())]=dict(
        sha256=digest(adapter.reference_path().read_bytes()),bytes=adapter.reference_path().stat().st_size)
    save(world.reference_path(),result)
    save(cache/f'scorecard-after-{len(attempts)}.json',summary)
    print(world.canonical_json({k:v for k,v in summary.items() if k not in {'attempts','captures'}}),flush=True)
    return summary


def collect(cache=CACHE):
    manifest=read(SOURCE)
    check_parent(manifest)
    CAPTURES.mkdir(parents=True,exist_ok=True)
    with (CAPTURES/'.campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=CAPTURES/'collection-stop.json'
        if stop.exists() or manifest['collection'].get('collection_stop'):
            raise RuntimeError('Collection stopped previously; do not retry an access challenge')
        path=CAPTURES/'attempts.json'
        attempts=merged_attempts(manifest,path)
        if not path.exists() or read(path)['attempts']!=attempts:
            save(path,dict(attempts=attempts))
        budget=preparation.AttemptBudget(path,manifest['new_searches'],limit=manifest['search_limit'])
        remaining=manifest['search_limit']-len(budget.used)
        if not remaining:
            print('Follow-up complete; zero further searches.',flush=True)
            return 0
        check_baseline(cache,manifest)
        known={tuple(r['query']) for r in read(ORIGINAL_CACHE/'cache-index.json.gz')['queries']}
        batch=[tuple(q) for q in manifest['new_searches'] if tuple(q) not in budget.used and tuple(q) not in known][:min(100,remaining)]
        if not batch:
            return 0
        zones={a['code']:a.get('replay_timezone',a['timezone']) for a in manifest['airports']}
        cfg=dict(country='WORLD',scope='international',timezone='UTC',end_date=DAY,max_duration=86400,
            capture_prices=True,currency='USD',zones=zones,reject_invalid_segments=True,
            capture_context=dict(parser='world-international-followup-v1',max_duration=86400,currency='USD',
                adults=1,cabin='economy',trip_type='one_way',airline_filter='none'),on_query_start=budget.start,queries=batch)
        print(world.canonical_json(dict(batch=len(batch),attempted=len(attempts),cap=300)),flush=True)
        stopped=False
        try:
            asyncio.run(capture(CAPTURES,DAY,sorted({q[1:] for q in batch}),2,cfg))
        except RuntimeError as error:
            save(stop,dict(reason=str(error),at=datetime.now(timezone.utc).isoformat()))
            stopped=True
        publish_checkpoint(cache)
        return 2 if stopped else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['manifest','collect','finalize'])
    args=parser.parse_args()
    if args.action=='manifest': build_manifest()
    elif args.action=='finalize': publish_checkpoint()
    else: return collect()
    return 0


if __name__=='__main__':
    sys.exit(main())
