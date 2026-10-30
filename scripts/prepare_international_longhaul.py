"""Capped 200-query long-haul pass: exact routes and timing-justified UTC gaps."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard import world_flights as world,international_expansion as adapter
from scripts import prepare_international_followup as runner
from scripts import prepare_international_boundaries as boundaries
from scripts.discover_international_expansion import DAY,CACHE as ORIGINAL_CACHE,SOURCE as FIRST,read,save,digest,relative

SOURCE=ROOT/'data/sources/world_international_longhaul.json.gz'
CACHE=ROOT/'.cache/international-longhaul'
CAPTURES=ROOT/'.cache/google-flights-world-international-usd-longhaul'
PARENTS=[FIRST,runner.SOURCE,boundaries.SOURCE]
NA={'US','CA','MX'}
EAST_ASIA={'CN','JP','KR','TW','HK','MO','MN'}
EUROPE=set('FR GB DE ES NL IT CH AT BE FI DK SE NO PL CZ PT HU IE'.split())
LIMITS={'north_america_east_asia':80,'europe_east_asia':69,'utc_boundary':50,'official_recheck':1}
CHECKPOINTS=[(20,16,13,1),(20,18,12,0),(20,17,13,0),(20,18,12,0)]
RECHECK=(DAY,'HND','LHR')
ANA_URL='https://www.ana.co.jp/en/us/plan-book/routes/international-route-information/'
ANA_SHA='a9b1d7277357e1de3a88b1458beb84c770096b226b2ac23504da9c236a1bdf1b'


def previous_attempts():
    return {tuple(a['query']) for p in PARENTS for a in read(p)['collection']['attempts']}


def candidate_pools(baseline,first,last,index):
    air={a['code']:a for a in [*first['airports'],*baseline['airports']]}
    ledger={tuple(r['query']):r for r in first['ledger']}
    charged=previous_attempts();known={tuple(r['query']) for r in index['queries']}
    routes=Counter((f['origin'],f['destination']) for f in baseline['flights'] if f['flight_scope']=='international')
    identities={world.identity(f) for f in baseline['flights']}
    hubs=Counter(c for f in baseline['flights'] if f['flight_scope']=='international' for c in (f['origin'],f['destination']))
    pools={k:[] for k in LIMITS}
    for q in last['remaining_queue']:
        key=tuple(q);day,a,b=key
        if day!=DAY or key in charged or key in known or (a,b) in routes:continue
        aa,bb=air[a]['country'],air[b]['country']
        stream=('north_america_east_asia' if (aa in NA and bb in EAST_ASIA or bb in NA and aa in EAST_ASIA)
            else 'europe_east_asia' if (aa in EUROPE and bb in EAST_ASIA or bb in EUROPE and aa in EAST_ASIA) else None)
        if stream:
            pools[stream].append(dict(query=list(key),stream=stream,evidence=ledger[key]['evidence'],
                dated_reverse_flights=routes[b,a],hub_capture_count=hubs[a]+hubs[b]))
    for stream in ('north_america_east_asia','europe_east_asia'):
        pools[stream].sort(key=lambda r:(-r['dated_reverse_flights'],-len(r['evidence']),-r['hub_capture_count'],tuple(r['query'])))
    timings=defaultdict(dict)
    for item in index['queries']:
        day,a,b=item['query']
        if day!=DAY or a not in air or b not in air or air[a]['country'] not in NA or air[b]['country'] not in EUROPE|EAST_ASIA:
            continue
        info=item['latest']
        if not info['flights']:continue
        path=ROOT/info['path']
        if digest(path.read_bytes())!=info['sha256']:raise ValueError('Boundary source changed after indexing')
        q=read(path)
        for f in q['flights']:
            proof=boundaries.shifted_overlap(f,air[a],air[b],-1)
            if not proof:continue
            key=('2026-11-01',a,b)
            if key in charged or key in known:continue
            identity=(f['carrier'],f['number'],a,b,proof['candidate_departure'],proof['candidate_arrival'])
            if identity in identities:continue
            timings[key][identity]=dict(**proof,source_path=info['path'],source_sha256=info['sha256'],source_query=item['query'])
    for key,proofs in timings.items():
        pools['utc_boundary'].append(dict(query=list(key),stream='utc_boundary',
            missing_direction=key[1:] not in routes,dated_reverse_flights=routes[key[2],key[1]],
            possible_new_identities=len(proofs),timing_evidence=[proofs[k] for k in sorted(proofs)],
            evidence=[dict(kind='dated_capture',url=p['source_path'],sha256=p['source_sha256']) for p in [next(iter(proofs.values()))]]))
    pools['utc_boundary'].sort(key=lambda r:(not r['missing_direction'],-r['possible_new_identities'],-r['dated_reverse_flights'],tuple(r['query'])))
    if RECHECK in charged:raise ValueError('Do not repeat a charged international campaign query')
    if RECHECK[1:] in routes:raise ValueError('Haneda–Heathrow is no longer absent')
    pools['official_recheck']=[dict(query=list(RECHECK),stream='official_recheck',
        evidence=[dict(kind='official_timetable',url=ANA_URL,sha256=ANA_SHA,
            hash_basis='Downloaded timetable HTML',flight_number='NH211',operation='daily',
            valid_from='2026-10-25',valid_to='2027-03-27')],
        reason='Prior empty capture conflicts with ANA published daily NH211 during replay period; recheck once only.')]
    return pools


def build_manifest():
    if SOURCE.exists():m=read(SOURCE);check_campaign(m);return m
    first,last,index=read(FIRST),read(boundaries.SOURCE),read(ORIGINAL_CACHE/'cache-index.json.gz')
    baseline=world.load_reference(DAY)
    proof=CACHE/'ana-winter-2026.html'
    if not proof.exists() or digest(proof.read_bytes())!=ANA_SHA:raise ValueError('Pinned official ANA timetable required')
    pools=candidate_pools(baseline,first,last,index)
    available={k:len(v) for k,v in pools.items()}
    if any(available[k]<LIMITS[k] for k in LIMITS):raise ValueError(f'Insufficient evidenced candidates: {available}')
    chosen={k:v[:LIMITS[k]] for k,v in pools.items()};selected=[]
    for counts in CHECKPOINTS:
        batch=[]
        for (stream,_),count in zip(LIMITS.items(),counts):
            rows=chosen[stream][:count];chosen[stream]=chosen[stream][count:]
            batch.extend(((i+.5)/len(rows),stream,r) for i,r in enumerate(rows))
        selected.extend(r for _,_,r in sorted(batch))
    catalogue={}
    for a in [*first['airports'],*last['airports'],*baseline['airports']]:world.merge_airport(catalogue,a)
    save(CACHE/'baseline.json.gz',baseline);save(CACHE/'supplement-before.json.gz',adapter.load_reference())
    m=dict(profile='world_international_longhaul',day=DAY,timezone='UTC',currency='USD',search_limit=200,checkpoint_size=50,concurrency=2,
        workstream_limits=LIMITS,parent_campaigns=[dict(path=relative(p),sha256=digest(p.read_bytes()),attempts=n) for p,n in zip(PARENTS,(1000,300,100))],
        baseline_inputs=baseline['metadata']['inputs'],baseline_counts=runner.preparation.metrics(baseline),
        baseline_world_sha256=digest(world.reference_path().read_bytes()),baseline_supplement_sha256=digest(adapter.reference_path().read_bytes()),
        airports=[catalogue[k] for k in sorted(catalogue)],candidates=selected,new_searches=[r['query'] for r in selected],
        verified_recheck_queries=[list(RECHECK)],candidate_pool_counts=available,
        remaining_queue=[q for q in last['remaining_queue'] if q not in [r['query'] for r in selected]],
        unresolved_airports=last['unresolved_airports'],unresolved_routes=last['unresolved_routes'],
        limitations=['Published maps are candidates, not proof of dated service.','Observed timings justify adjacent-date queries only; never generated flights.',
            'One official timetable-backed recheck; no blind retries of prior failed or empty campaign attempts.',
            'UTC replay date unchanged; prices captured in USD without conversion; coverage remains partial.'],
        collection=dict(attempts=[],searches_attempted=0))
    check_campaign(m);save(SOURCE,m)
    print(world.canonical_json(dict(selected=200,pools=available,workstreams=LIMITS,dates=dict(Counter(q[0] for q in m['new_searches'])))),flush=True)
    return m


def check_campaign(m):
    if m.get('search_limit')!=200 or m.get('checkpoint_size')!=50 or m.get('workstream_limits')!=LIMITS:
        raise ValueError('The long-haul pass is capped at 200 queries, reviewed every 50')
    keys=[tuple(q) for q in m['new_searches']]
    if len(keys)!=200 or len(set(keys))!=200 or [r['query'] for r in m['candidates']]!=m['new_searches']:
        raise ValueError('Expected 200 unique, evidenced exact queries')
    if Counter(r['stream'] for r in m['candidates'])!=LIMITS or m.get('verified_recheck_queries')!=[list(RECHECK)]:
        raise ValueError('Long-haul allocations or official recheck changed')
    for start,counts in zip(range(0,200,50),CHECKPOINTS):
        if Counter(r['stream'] for r in m['candidates'][start:start+50])!={k:v for k,v in zip(LIMITS,counts) if v}:
            raise ValueError('Checkpoint allocation changed')
    if [p['path'] for p in m['parent_campaigns']]!=[relative(p) for p in PARENTS]:raise ValueError('All three parent campaigns must remain pinned')
    for row,path,expected in zip(m['parent_campaigns'],PARENTS,(1000,300,100)):
        if digest(path.read_bytes())!=row['sha256']:raise ValueError('Historical campaign changed')
        parent=read(path)['collection']
        if row.get('attempts')!=expected or len(parent['attempts'])!=expected or parent.get('collection_stop'):
            raise ValueError('Completed, unchallenged parent campaigns required')
    if set(keys)&previous_attempts():raise ValueError('Do not repeat previous campaign attempts')
    air={a['code']:a for a in m['airports']}
    for row in m['candidates']:
        day,a,b=row['query'];aa,bb=air[a]['country'],air[b]['country']
        if not row.get('evidence') or a==b or not adapter.is_international(air[a],air[b]):raise ValueError('Invalid international route evidence')
        if row['stream']=='official_recheck':
            e=row['evidence'][0]
            if tuple(row['query'])!=RECHECK or e.get('url')!=ANA_URL or e.get('sha256')!=ANA_SHA or e.get('flight_number')!='NH211' or e.get('operation')!='daily' or not e['valid_from']<=DAY<=e['valid_to']:
                raise ValueError('Official recheck needs the pinned dated ANA timetable')
        elif row['stream']=='utc_boundary':
            if day!='2026-11-01' or aa not in NA or bb not in EUROPE|EAST_ASIA or not row.get('timing_evidence'):
                raise ValueError('Adjacent dates need observed North American timing evidence')
            for proof in row['timing_evidence']:
                original=dict(number=proof['number'],carrier=proof['carrier'],departure=proof['source_departure'],arrival=proof['source_arrival'])
                actual=boundaries.shifted_overlap(original,air[a],air[b],-1)
                if actual is None or any(proof.get(k)!=v for k,v in actual.items()) or proof.get('source_query')!=[DAY,a,b]:
                    raise ValueError('Invalid UTC-overlap timing proof')
        else:
            group=NA if row['stream']=='north_america_east_asia' else EUROPE
            if day!=DAY or not (aa in group and bb in EAST_ASIA or bb in group and aa in EAST_ASIA):
                raise ValueError('Wrong long-haul country corridor')
    for p,info in m['baseline_inputs'].items():
        if p==relative(adapter.reference_path()):continue  # Intentionally updated cumulative supplement.
        if digest((ROOT/p).read_bytes())!=info['sha256']:raise ValueError(f'Frozen view changed: {p}')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['manifest','collect','finalize']);action=p.parse_args().action
    if action=='manifest':build_manifest()
    elif action=='collect':return runner.collect(CACHE,SOURCE,CAPTURES,check_campaign,50)
    else:runner.publish_checkpoint(CACHE,SOURCE,CAPTURES,check_campaign)
    return 0


if __name__=='__main__':sys.exit(main())
