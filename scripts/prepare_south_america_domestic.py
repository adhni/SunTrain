"""Evidence-led domestic expansion: 200 new searches, reviewed every 50."""
import argparse
import asyncio
from collections import Counter,defaultdict
from datetime import datetime,timezone
import fcntl
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs,urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard import flights,world_flights as world,south_america_domestic as domestic
from scripts.discover_international_expansion import Airports,digest,merged_attempts,read,relative,save,timestamp,validate_query
from scripts.prepare_international_expansion import AttemptBudget
from scripts.prepare_google_flights import capture

DAY=world.DAY
CACHE=ROOT/'.cache/south-america-domestic'
CAPTURES=ROOT/'.cache/google-flights-south-america-domestic-usd'
SOURCE=ROOT/'data/sources/south_america_domestic.json.gz'
MAIN={'AR':['AEP','EZE'],'PE':['LIM','CUZ'],'CL':['SCL']}
LIMITS={'AR':90,'PE':60,'CL':50}
BASE=ROOT/f'data/reference/south_america_flights/{DAY}.json.gz'
CHILE_ZONES={'CPO':'America/Santiago','ZCO':'America/Santiago',
    'BBA':'America/Coyhaique','PUQ':'America/Punta_Arenas','PNT':'America/Punta_Arenas'}


def airport_catalogue(baseline):
    airports=Airports(baseline)
    # Explicit IANA regions, not a Chile-wide offset. Current CPO/ZCO identities
    # differ from old OpenFlights aerodromes; Aysen/Magallanes have own zones.
    for code,zone in CHILE_ZONES.items():
        if code in airports.known and airports.known[code]['timezone']!=zone:
            raise ValueError(f'Existing airport timezone needs review: {code}')
        airports.zones[code]=zone
    return airports


def cached_queries(airports,keys):
    found=defaultdict(list)
    pattern=re.compile(r'2026-11-02-([A-Z0-9]{3})-([A-Z0-9]{3})\.json')
    for directory in sorted((ROOT/'.cache').glob('google-flights*')):
        if directory==CAPTURES:continue
        for path in directory.rglob(f'{DAY}-*.json'):
            match=pattern.fullmatch(path.name)
            if not match:continue
            key=(DAY,*match.groups())
            if key not in keys:continue
            try:
                q=read(path)
                validate_query(q,key,airports,scope='domestic')
                if parse_qs(urlparse(q['url']).query).get('curr')!=['USD']:
                    continue
            except (ValueError,KeyError,TypeError):continue
            found[key].append(dict(path=relative(path),sha256=digest(path.read_bytes()),captured_at=q['captured_at']))
    return {key:sorted(rows,key=lambda r:(timestamp(r['captured_at']),r['path']))[-1] for key,rows in found.items()}


def build_manifest():
    if SOURCE.exists():m=read(SOURCE);check(m);return m
    baseline=world.load_reference(DAY);airports=airport_catalogue(baseline)
    original=read(BASE);existing={(q['date'],q['origin'],q['destination']) for q in original['metadata']['queries']}
    evidence=defaultdict(list);unresolved=[]
    discovery=read(CACHE/'discovery.json')
    for source in discovery['maps']:
        for a,b in source['routes']:
            if airports.country(a) not in domestic.COUNTRIES or airports.country(a)!=airports.country(b):continue
            aa,bb=airports.get(a),airports.get(b)
            if not aa or not bb:
                unresolved.append([a,b]);continue
            if (DAY,a,b) in existing:continue
            evidence[(DAY,a,b)].append({k:source[k] for k in ('code','url','sha256','evidence')})
    reused=cached_queries(airports,set(evidence))
    queues={country:[] for country in MAIN}
    for key,sources in sorted(evidence.items()):
        country=airports.country(key[1])
        row=dict(query=list(key),country=country,evidence=sources)
        if key in reused:continue
        queues[country].append(row)
    for country,rows in queues.items():
        def priority(r):
            a,b=r['query'][1:];hub=next((i for i,c in enumerate(MAIN[country]) if c in (a,b)),99)
            return hub,-len(r['evidence']),tuple(sorted((a,b))),a not in MAIN[country],a,b
        rows.sort(key=priority)
    chosen={c:rows[:LIMITS[c]] for c,rows in queues.items()}
    for c,rows in queues.items():
        more=rows[len(chosen[c]):][:max(0,200-sum(map(len,chosen.values())))]
        chosen[c].extend(more)
    if sum(map(len,chosen.values()))!=200:
        raise ValueError('Fewer than 200 resolvable published candidates; do not invent airport pairs')
    selected=[row for _,c,row in sorted(((i+.5)/len(rows),c,row) for c,rows in chosen.items() for i,row in enumerate(rows))]
    used={x for r in selected for x in r['query'][1:]}|{x for key in reused for x in key[1:]}
    save(CACHE/'baseline-world.json.gz',baseline);save(CACHE/'baseline-south-america.json.gz',flights.load_reference(DAY,'south_america_flights'))
    m=dict(profile='south_america_domestic',day=DAY,timezone='UTC',currency='USD',search_limit=200,checkpoint_size=50,
        baseline_world_sha256=digest(world.reference_path().read_bytes()),baseline_south_america_sha256=digest(BASE.read_bytes()),
        baseline_inputs=baseline['metadata']['inputs'],baseline_world_flights=len(baseline['flights']),
        candidates=selected,new_searches=[r['query'] for r in selected],
        reused=[dict(query=list(k),**v) for k,v in sorted(reused.items())],
        airports=[airports.known[c] for c in sorted(used)],country_allocations={c:len(rows) for c,rows in chosen.items()},
        airport_zone_resolutions=CHILE_ZONES,timezone_source='https://data.iana.org/time-zones/tzdb/zone1970.tab',
        discovery=discovery,unresolved_airports=airports.unresolved,unresolved_routes=sorted(map(list,set(map(tuple,unresolved)))),
        deferred=[r for rows in queues.values() for r in rows if r['query'] not in [s['query'] for s in selected]],
        limitations=['Published routes are candidates, not dated service evidence.','One origin-local date only; no all-pairs sweep.',
            'Empty means not returned, not no service. Coverage remains partial.'],collection=dict(attempts=[]))
    check(m);save(SOURCE,m)
    print(world.canonical_json(dict(new_searches=200,countries=m['country_allocations'],reused=len(reused),airports=len(used),deferred=len(m['deferred']))),flush=True)
    return m


def check(m):
    if m.get('search_limit')!=200 or m.get('checkpoint_size')!=50:raise ValueError('The domestic campaign is capped at 200 searches')
    keys=[tuple(q) for q in m['new_searches']]
    if len(keys)!=200 or len(set(keys))!=200:raise ValueError('Expected 200 unique exact queries')
    if [r['query'] for r in m['candidates']]!=m['new_searches']:raise ValueError('Query evidence changed')
    if digest(BASE.read_bytes())!=m['baseline_south_america_sha256']:raise ValueError('Original South American archive changed')
    air={a['code']:a for a in m['airports']}
    for r in m['candidates']:
        day,a,b=r['query']
        if day!=DAY or a==b or not r['evidence'] or air[a]['country'] not in domestic.COUNTRIES or air[a]['country']!=air[b]['country']:
            raise ValueError('Only evidenced domestic routes on the selected local date are allowed')
    for p,v in m['baseline_inputs'].items():
        if digest((ROOT/p).read_bytes())!=v['sha256']:raise ValueError(f'Frozen input changed: {p}')


def publish():
    m=read(SOURCE);check(m)
    if digest((CACHE/'baseline-world.json.gz').read_bytes())!=m['baseline_world_sha256']:
        raise ValueError('Frozen World baseline changed')
    attempts=merged_attempts(m,CAPTURES/'attempts.json')
    if len(attempts)>200:raise ValueError('Domestic search cap exceeded')
    if domestic.reference_path().exists():
        # A portable snapshot must never shrink just because ignored captures
        # were removed locally. Collection can resume only with its evidence.
        for q in domestic.load_reference()['metadata']['queries']:
            path=ROOT/q['source_path']
            if not path.exists() or digest(path.read_bytes())!=q['sha256']:
                raise ValueError('Published domestic capture missing or changed')
    airport_resolver=airport_catalogue(read(CACHE/'baseline-world.json.gz'))
    sources={tuple(r['query']):r for r in m['reused']}
    for a in attempts:
        key=tuple(a['query']);path=CAPTURES/('-'.join(key)+'.json')
        if path.exists():sources[key]=dict(path=relative(path),sha256=digest(path.read_bytes()))
    records={};queries=[];rejected=[]
    for key,source in sorted(sources.items()):
        path=ROOT/source['path']
        if digest(path.read_bytes())!=source['sha256']:raise ValueError('A captured query changed')
        q=read(path)
        try:validate_query(q,key,airport_resolver,scope='domestic')
        except (ValueError,KeyError,TypeError) as error:
            rejected.append(dict(query=list(key),reason=str(error)));continue
        queries.append({**{k:v for k,v in q.items() if k!='flights'},'source_path':relative(path),'sha256':source['sha256']})
        for f in q['flights']:
            row={**f,'flight_scope':'domestic'}
            if f['id'] in records and records[f['id']]!=row:raise ValueError('Conflicting source identity')
            records[f['id']]=row
    successful={tuple(q[k] for k in ('date','origin','destination')) for q in queries}
    missing=[list(tuple(a['query'])) for a in attempts if tuple(a['query']) not in successful]
    failed=[dict(query=a['query'],error=read(CAPTURES/('-'.join(a['query'])+'.error.json')))
        for a in attempts if (CAPTURES/('-'.join(a['query'])+'.error.json')).exists()]
    flights_list=sorted(records.values(),key=lambda f:(f['departure'],f['id']))
    base=read(CACHE/'baseline-world.json.gz');known={world.identity(f) for f in base['flights']}
    new_overlap=[f for f in flights_list if f['departure']<world.END and f['arrival']>=world.START and world.identity(f) not in known]
    coverage=dict(flights=len(flights_list),routes_returned=len({(f['origin'],f['destination']) for f in flights_list}),
        airports_returned=len({c for f in flights_list for c in (f['origin'],f['destination'])}),new_world_identities=len(new_overlap),
        by_country=dict(Counter(airport_resolver.country(f['origin']) for f in flights_list)))
    meta=dict(profile='south_america_domestic',start_date=DAY,end_date=DAY,timezone='UTC',scope='domestic',
        source='Published-route domestic Google Flights captures',source_url='https://www.google.com/travel/flights',
        source_date=max((q['captured_at'][:10] for q in queries),default=''),queries=queries,uncollected_queries=missing,
        fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way'),coverage=coverage,
        priced_flights=sum(bool(f.get('price')) for f in flights_list),replay_note=domestic.NOTE)
    collection=dict(attempts=attempts,searches_attempted=len(attempts),queries_captured=len(queries),
        nonempty_queries=sum(q['status']=='results' for q in queries),
        empty_results=sum(q['status']=='no_matching_direct_flights' for q in queries),
        failed_queries=failed,rejected_queries=rejected,missing_queries=missing,coverage=coverage,
        priced_records=meta['priced_flights'],reused_queries=len(m['reused']))
    stop=CAPTURES/'collection-stop.json'
    if stop.exists():collection['collection_stop']=read(stop)
    m['collection']=collection;save(SOURCE,m)
    meta['source_manifest']=dict(path=relative(SOURCE),sha256=digest(SOURCE.read_bytes()))
    save(domestic.reference_path(),dict(airports=m['airports'],flights=flights_list,metadata=meta))
    domestic.load_reference()
    result=world.prepare(CACHE/f'world-after-{len(attempts)}.json.gz')
    collection['world_flights']=len(result['flights']);collection['world_added']=len(result['flights'])-len(base['flights'])
    collection['south_america_flights']=len(flights.load_reference(DAY,'south_america_flights')['flights'])
    m['collection']=collection;save(SOURCE,m)
    meta['source_manifest']['sha256']=digest(SOURCE.read_bytes())
    save(domestic.reference_path(),dict(airports=m['airports'],flights=flights_list,metadata=meta))
    result['metadata']['inputs'][relative(domestic.reference_path())]=dict(sha256=digest(domestic.reference_path().read_bytes()),bytes=domestic.reference_path().stat().st_size)
    save(world.reference_path(),result);save(CACHE/f'scorecard-after-{len(attempts)}.json',collection)
    print(world.canonical_json({k:v for k,v in collection.items() if k!='attempts'}),flush=True)
    return collection


def collect():
    m=read(SOURCE);check(m);CAPTURES.mkdir(parents=True,exist_ok=True)
    with (CAPTURES/'.campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stop=CAPTURES/'collection-stop.json'
        if stop.exists() or m['collection'].get('collection_stop'):raise RuntimeError('Collection stopped; do not retry an access challenge')
        path=CAPTURES/'attempts.json';attempts=merged_attempts(m,path)
        if not path.exists() or read(path)['attempts']!=attempts:save(path,dict(attempts=attempts))
        budget=AttemptBudget(path,m['new_searches'],limit=200)
        if len(budget.used)==200:print('Domestic campaign complete; zero further searches.',flush=True);return 0
        batch=[tuple(q) for q in m['new_searches'] if tuple(q) not in budget.used][:min(50,200-len(budget.used))]
        cfg=dict(country='SOUTH_AMERICA',scope='domestic',timezone='UTC',end_date=DAY,max_duration=28800,
            capture_prices=True,currency='USD',zones={a['code']:a['timezone'] for a in m['airports']},
            reject_invalid_segments=True,queries=batch,on_query_start=budget.start,
            capture_context=dict(parser='south-america-domestic-v1',max_duration=28800,currency='USD',
                adults=1,cabin='economy',trip_type='one_way',airline_filter='none'))
        stopped=False
        try:asyncio.run(capture(CAPTURES,DAY,sorted({q[1:] for q in batch}),2,cfg))
        except RuntimeError as error:
            save(stop,dict(reason=str(error),at=datetime.now(timezone.utc).isoformat()));stopped=True
        publish()
        return 2 if stopped else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['manifest','collect','prepare'])
    action=parser.parse_args().action
    if action=='manifest':build_manifest()
    elif action=='collect':return collect()
    else:publish()
    return 0


if __name__=='__main__':sys.exit(main())
