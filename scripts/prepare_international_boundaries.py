"""Collect 49 missing directions and 51 timing-justified UTC-boundary queries.

This is a separate 100-attempt campaign, reviewed after 50. Prior campaigns and
the 2 November UTC replay window remain unchanged. No whole extra day is fetched.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import prepare_international_followup as runner
from scripts.discover_international_expansion import (
    Airports, DAY, SOURCE as FIRST_SOURCE, CACHE as ORIGINAL_CACHE,
    digest, read, relative, save)
from dashboard import world_flights as world, international_expansion as adapter

SOURCE=ROOT/'data/sources/world_international_boundaries.json.gz'
CACHE=ROOT/'.cache/international-boundaries'
CAPTURES=ROOT/'.cache/google-flights-world-international-usd-boundaries'
LIMITS={'reverse_direction':49,'utc_boundary':51}
ADJACENT={'2026-11-01','2026-11-03'}


def shifted_overlap(flight,origin,destination,offset):
    """A timing clue for a search, never a generated flight record."""
    oz=origin.get('replay_timezone',origin['timezone'])
    dz=destination.get('replay_timezone',destination['timezone'])
    departure=datetime.fromtimestamp(flight['departure'],ZoneInfo(oz))+timedelta(days=offset)
    arrival=datetime.fromtimestamp(flight['arrival'],ZoneInfo(dz))+timedelta(days=offset)
    if (departure.date().isoformat() not in ADJACENT or departure.timestamp()>=world.END
            or arrival.timestamp()<world.START):
        return None
    return dict(number=flight['number'],carrier=flight['carrier'],
        source_departure=flight['departure'],source_arrival=flight['arrival'],
        offset_days=offset,origin_zone=oz,destination_zone=dz,
        candidate_departure=int(departure.timestamp()),candidate_arrival=int(arrival.timestamp()))


def rank_candidates(first,previous,baseline,index):
    ledger={tuple(r['query']):r for r in first['ledger']}
    charged={tuple(a['query']) for m in (first,previous) for a in m['collection']['attempts']}
    known={tuple(r['query']) for r in index['queries']}|charged
    remaining={tuple(q) for q in previous['remaining_queue']}-known
    routes={(f['origin'],f['destination']) for f in baseline['flights']}
    dated=Counter((f['origin'],f['destination']) for f in baseline['flights']
        if DAY in f.get('provenance',{}).get('source_dates',[]))
    reverse=[]
    for key in sorted(remaining):
        row=ledger[key]
        if (key[0]==DAY and row['stream']=='asia_gulf' and key[1:] not in routes
                and dated[key[1:][::-1]]):
            reverse.append(dict(query=list(key),stream='reverse_direction',
                dated_reverse_flights=dated[key[1:][::-1]],evidence=row['evidence']))
    reverse.sort(key=lambda r:(-r['dated_reverse_flights'],tuple(r['query'])))
    airports={a['code']:a for a in baseline['airports']}
    identities={world.identity(f) for f in baseline['flights']}
    timings=defaultdict(dict)
    for flight in baseline['flights']:
        if flight['flight_scope']!='international':continue
        for offset in (-1,1):
            proof=shifted_overlap(flight,airports[flight['origin']],airports[flight['destination']],offset)
            if not proof:continue
            key=(datetime.fromtimestamp(proof['candidate_departure'],ZoneInfo(proof['origin_zone'])).date().isoformat(),
                 flight['origin'],flight['destination'])
            if key not in remaining:continue
            identity=(flight['carrier'],flight['number'],key[1],key[2],proof['candidate_departure'],proof['candidate_arrival'])
            timings[key][identity]=proof
    boundary=[]
    for key,proofs in sorted(timings.items()):
        boundary.append(dict(query=list(key),stream='utc_boundary',
            possible_new_identities=sum(identity not in identities for identity in proofs),
            timing_evidence=[proofs[k] for k in sorted(proofs)],evidence=ledger[key]['evidence']))
    boundary.sort(key=lambda r:(-r['possible_new_identities'],-len(r['timing_evidence']),tuple(r['query'])))
    return reverse,boundary


def check_campaign(manifest):
    if (manifest.get('search_limit')!=100 or manifest.get('workstream_limits')!=LIMITS
            or manifest.get('checkpoint_size')!=50):
        raise ValueError('This campaign is capped at 100 attempts, with 49 reverse and 51 boundary queries')
    keys=[tuple(q) for q in manifest['new_searches']]
    if len(keys)!=100 or len(set(keys))!=100:
        raise ValueError('Expected 100 unique exact-airport/date queries')
    if ([r['query'] for r in manifest['candidates']]!=manifest['new_searches']
            or dict(Counter(r['stream'] for r in manifest['candidates']))!=LIMITS):
        raise ValueError('Candidate evidence or allocation changed')
    if [p['path'] for p in manifest['parent_campaigns']]!=[relative(FIRST_SOURCE),relative(runner.SOURCE)]:
        raise ValueError('Both completed parent campaigns must be pinned')
    past=set()
    for parent,expected in zip(manifest['parent_campaigns'],(1000,300)):
        path=ROOT/parent['path']
        if digest(path.read_bytes())!=parent['sha256']:
            raise ValueError('A completed parent campaign changed')
        old=read(path)['collection']
        if len(old['attempts'])!=expected or old.get('collection_stop'):
            raise ValueError('Incomplete or challenged parent campaign')
        past.update(tuple(a['query']) for a in old['attempts'])
    if set(keys)&past:
        raise ValueError('Do not repeat an earlier attempt, including failed or interrupted queries')
    for row in manifest['candidates']:
        day,a,b=row['query']
        if a==b or not row.get('evidence'):
            raise ValueError('Missing exact-route evidence')
        if row['stream']=='reverse_direction':
            if day!=DAY or row.get('dated_reverse_flights',0)<1:
                raise ValueError('Missing dated reverse evidence')
        else:
            if day not in ADJACENT or not row.get('timing_evidence'):
                raise ValueError('Adjacent dates require observed timing evidence')
            for proof in row['timing_evidence']:
                if proof['offset_days'] not in (-1,1):raise ValueError('Invalid adjacent-date shift')
                original=dict(number=proof['number'],carrier=proof['carrier'],
                    departure=proof['source_departure'],arrival=proof['source_arrival'])
                derived=shifted_overlap(original,dict(timezone=proof['origin_zone']),
                    dict(timezone=proof['destination_zone']),proof['offset_days'])
                if derived!=proof or datetime.fromtimestamp(proof['candidate_departure'],ZoneInfo(proof['origin_zone'])).date().isoformat()!=day:
                    raise ValueError('Timing evidence does not overlap the UTC replay day')


def build_manifest():
    if SOURCE.exists():
        result=read(SOURCE);check_campaign(result);return result
    first,previous=read(FIRST_SOURCE),read(runner.SOURCE)
    baseline=world.load_reference(DAY)
    reverse,boundary=rank_candidates(first,previous,baseline,read(ORIGINAL_CACHE/'cache-index.json.gz'))
    if len(reverse)!=49 or len(boundary)<51:
        raise ValueError('The reviewed 49/51 selection no longer matches the inputs')
    reverse,boundary=reverse[:49],boundary[:51]
    selected=[]
    for rs,bs in ((reverse[:25],boundary[:25]),(reverse[25:],boundary[25:])):
        for i in range(max(len(rs),len(bs))):
            if i<len(rs):selected.append(rs[i])
            if i<len(bs):selected.append(bs[i])
    save(CACHE/'baseline.json.gz',baseline)
    save(CACHE/'supplement-before.json.gz',adapter.load_reference())
    airports=Airports(baseline)
    resolved=[airports.get(code) for code in ('JUB','DJT')]
    if not all(resolved) or airports.get('PBI') is not None:
        raise ValueError('Reviewed airport identity resolutions failed')
    catalogue={a['code']:a for a in first['airports']}
    catalogue.update((a['code'],a) for a in resolved)
    unresolved={k:v for k,v in first['unresolved_airports'].items() if k!='JUB'}
    unresolved.update(airports.unresolved)
    result=dict(profile='world_international_boundaries',day=DAY,timezone='UTC',currency='USD',
        search_limit=100,checkpoint_size=50,concurrency=2,workstream_limits=LIMITS,
        parent_campaigns=[dict(path=relative(path),sha256=digest(path.read_bytes()),attempts=count)
            for path,count in ((FIRST_SOURCE,1000),(runner.SOURCE,300))],
        baseline_inputs=baseline['metadata']['inputs'],baseline_counts=runner.preparation.metrics(baseline),
        baseline_world_sha256=digest(world.reference_path().read_bytes()),
        baseline_supplement_sha256=digest(adapter.reference_path().read_bytes()),
        airports=[catalogue[k] for k in sorted(catalogue)],
        candidates=selected,new_searches=[r['query'] for r in selected],
        remaining_queue=[q for q in previous['remaining_queue'] if q not in [r['query'] for r in selected]],
        unresolved_airports=unresolved,unresolved_routes=[r for r in first['unresolved_routes']
            if 'JUB' not in (r['origin'],r['destination'])],
        airport_resolutions=dict(JUB=dict(icao='HJJJ',legacy_icao='HSSJ',timezone='Africa/Juba',
            source_url='https://sscaa.gov.ss/media/aip/master/aip.pdf'),
            PBI=dict(status='superseded_iata',replacement='DJT',effective_date='2026-08-18',
                source_url='https://flydjt.org/articles/post/president-donald-j-trump-international-airport-name-change-takes-effect/'),
            DJT=dict(icao='KDJT',timezone='America/New_York')),
        limitations=['Shifted timings justify queries, never generated schedules or daily-service assumptions.',
            'Only dated captured flights overlapping 2 November UTC enter World; airport boards keep half-open event windows.',
            'Empty means not returned; worldwide and adjacent-day coverage remain partial.',
            'PBI is not silently rewritten to DJT; no new JUB or DJT flight search is added by airport resolution.'],
        collection=dict(attempts=[],searches_attempted=0))
    check_campaign(result)
    save(SOURCE,result)
    print(world.canonical_json(dict(selected=100,workstreams=LIMITS,
        dates=dict(Counter(q[0] for q in result['new_searches'])),boundary_candidates=len(boundary))),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['manifest','collect','finalize'])
    args=parser.parse_args()
    if args.action=='manifest':build_manifest()
    elif args.action=='collect':
        return runner.collect(CACHE,source=SOURCE,captures=CAPTURES,validate=check_campaign,checkpoint_size=50)
    else:runner.publish_checkpoint(CACHE,source=SOURCE,captures=CAPTURES,validate=check_campaign)
    return 0


if __name__=='__main__':sys.exit(main())
