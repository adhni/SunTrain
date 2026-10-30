"""Additive, validated Argentina/Peru/Chile captures for South America and World."""
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dashboard.flight_sources import read_reference
from dashboard import world_flights as world

DAY=world.DAY
COUNTRIES={'AR','PE','CL'}
NOTE=('Selected South American airports, plus captured domestic routes in Argentina, Peru and Chile. '
      'Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. '
      'Timeline: UTC; airport boards use local time. Captured fares use USD. Coverage and prices are partial; paths are illustrative.')


def reference_path():
    return Path(os.getenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(
        world.ROOT/f'data/reference/south_america_domestic/{DAY}.json.gz')))


def enabled():
    # Custom country fixtures keep their original isolated behavior.
    return (not os.getenv('SUNTRAIN_SOUTH_AMERICA_FLIGHTS_REFERENCE')
            or bool(os.getenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE'))) and reference_path().exists()


def load_reference():
    result=read_reference(reference_path())
    meta=result['metadata']
    if (meta.get('profile')!='south_america_domestic' or meta.get('start_date')!=DAY
            or meta.get('end_date')!=DAY or meta.get('scope')!='domestic'
            or tuple(meta.get('fare_context',{}).get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way')):
        raise ValueError('Invalid South American domestic capture context')
    airports={}
    for a in result['airports']:
        if a['country'] not in COUNTRIES or a['code'] in airports:
            raise ValueError('Invalid domestic airport identity')
        ZoneInfo(a['timezone']);world.merge_airport(airports,a)
    queries={}
    for q in meta['queries']:
        key=(q['date'],q['origin'],q['destination'])
        if (key in queries or key[0]!=DAY or key[1]==key[2]
                or airports[key[1]]['country']!=airports[key[2]]['country']
                or q['status'] not in {'results','no_matching_direct_flights'}):
            raise ValueError('Invalid domestic query ownership')
        queries[key]=q
    seen={}
    for f in result['flights']:
        a,b=airports[f['origin']],airports[f['destination']]
        key=(f['source_date'],f['origin'],f['destination'])
        if (key not in queries or queries[key]['status']!='results' or a['country']!=b['country']
                or f.get('flight_scope')!='domestic'
                or any(type(f.get(k)) is not int for k in ('departure','arrival'))
                or not 60<=f['arrival']-f['departure']<=28800
                or datetime.fromtimestamp(f['departure'],ZoneInfo(a['timezone'])).date().isoformat()!=DAY):
            raise ValueError('Invalid dated domestic flight')
        p=f.get('price')
        if p and (p.get('currency')!='USD' or type(p.get('amount_minor')) is not int or p['amount_minor']<=0
                or tuple(p.get(k) for k in ('adults','cabin','trip_type'))!=(1,'economy','one_way')):
            raise ValueError('Domestic fares require verified USD; no conversion')
        if seen.setdefault(f['id'],world.identity(f))!=world.identity(f):
            raise ValueError('Conflicting domestic source identity')
    return result


def overlay(base,extra):
    airports={}
    for a in [*base['airports'],*extra['airports']]:world.merge_airport(airports,a)
    records={f['id']:f for f in base['flights']}
    identities={world.identity(f):f['id'] for f in base['flights']}
    for f in extra['flights']:
        f={**f,'flight_scope':'domestic'}
        if f['id'] in records and world.identity(records[f['id']])!=world.identity(f):
            raise ValueError('Domestic extension conflicts with original flight identity')
        if world.identity(f) not in identities:
            records[f['id']]=f;identities[world.identity(f)]=f['id']
    queries={(q['date'],q['origin'],q['destination']):q for q in base['metadata'].get('queries',[])}
    for q in extra['metadata']['queries']:
        key=(q['date'],q['origin'],q['destination'])
        if key in queries:raise ValueError('Domestic extension must not replace original queries')
        queries[key]=q
    metadata={**base['metadata'],'replay_note':NOTE,'coverage_scope':NOTE,
        'source_date':max(base['metadata'].get('source_date',''),extra['metadata'].get('source_date','')),
        'queries':[queries[k] for k in sorted(queries)],
        'uncollected_queries':base['metadata'].get('uncollected_queries',[])+extra['metadata'].get('uncollected_queries',[]),
        'domestic_expansion':{k:v for k,v in extra['metadata'].items() if k not in {'queries','uncollected_queries'}},
        'airlines':sorted({f['airline'] for f in records.values()})}
    result=dict(airports=list(airports.values()),flights=sorted(records.values(),key=lambda f:(f['departure'],f['id'])),metadata=metadata)
    from dashboard.flights import snapshot_coverage
    metadata['coverage']=snapshot_coverage(result)
    # Retain the original per-country coverage breakdown, including empty gateways.
    groups={}
    represented={f[k] for f in result['flights'] for k in ('origin','destination')}
    for country in sorted({a['country'] for a in airports.values()}):
        own={a['code'] for a in airports.values() if a['country']==country}
        groups[country]=dict(candidate_airports=len(own),airports_returned=len(own&represented))
    metadata['coverage']['island_groups']=groups
    scopes={'both':metadata['coverage']}
    for scope in ('domestic','international'):
        belongs=lambda a,b:(airports[a]['country']==airports[b]['country'])==(scope=='domestic')
        projected={**result,'flights':[f for f in result['flights'] if f['flight_scope']==scope],
            'metadata':{**metadata,'queries':[q for q in metadata['queries'] if belongs(q['origin'],q['destination'])],
                'uncollected_queries':[q for q in metadata['uncollected_queries'] if belongs(q[1],q[2])]}}
        scopes[scope]=snapshot_coverage(projected)
    metadata['coverage_by_scope']=scopes
    return result
