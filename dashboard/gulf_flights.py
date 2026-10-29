"""Merge owned Gulf captures into one hub explorer without duplicate flights."""
from dashboard.flight_sources import read_reference
from pathlib import Path
import gzip
import json
import os

HUBS=('DXB','AUH','DOH')
DIRECTORY=Path(__file__).resolve().parents[1]/'data/reference/gulf_flights'


def reference_paths(business_date=None):
    directory=Path(os.getenv('SUNTRAIN_GULF_FLIGHTS_DIRECTORY',str(DIRECTORY)))
    return [directory/f'{business_date or "2026-11-02"}-{hub}.json.gz' for hub in HUBS]


def load_reference(business_date):
    refs=[]
    for path in reference_paths(business_date):
        refs.append(read_reference(path))
    airports={};flights={};queries={};missing=set();failed={}
    for ref in refs:
        context=ref['metadata'].get('fare_context')
        if context and tuple(context.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way'):
            raise ValueError('Gulf fare context must be USD, one adult, economy, one-way')
        for a in ref['airports']:
            if a['code'] in airports and airports[a['code']]!=a:raise ValueError('Conflicting Gulf airport identity')
            airports[a['code']]=a
        for f in ref['flights']:
            if not set((f['origin'],f['destination'])) & set(HUBS) or f['origin']==f['destination']:
                raise ValueError('Flight must touch a selected Gulf hub')
            price=f.get('price')
            if price and (price.get('currency')!='USD' or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
                raise ValueError('Gulf fares require positive USD minor units; no implicit conversion')
            previous=flights.get(f['id'])
            if previous:
                keys=('id','number','carrier','origin','destination','departure','arrival','aircraft')
                if any(previous.get(k)!=f.get(k) for k in keys):raise ValueError('Conflicting Gulf flight snapshot')
                if price and (not previous.get('price') or price['amount_minor']<previous['price']['amount_minor']):
                    flights[f['id']]={**previous,'price':price}
            else:flights[f['id']]=f
        for q in ref['metadata'].get('queries',[]):
            key=(q['date'],q['origin'],q['destination'])
            if key not in queries or q['captured_at']>queries[key]['captured_at']:queries[key]=q
        missing.update(tuple(q) for q in ref['metadata'].get('uncollected_queries',[]))
        for q in ref['metadata'].get('failed_queries',[]):failed[q['date'],q['origin'],q['destination']]=q
    for f in flights.values():
        a,b=airports[f['origin']],airports[f['destination']]
        f['flight_scope']='domestic' if a['country']==b['country'] else 'international'
    missing-=queries.keys();failed={k:q for k,q in failed.items() if k in missing}
    planned=set(queries)|missing
    def coverage(hub=None):
        belongs=lambda a,b:hub is None or hub in (a,b)
        qs=[q for q in queries.values() if belongs(q['origin'],q['destination'])]
        fs=[f for f in flights.values() if belongs(f['origin'],f['destination'])]
        expected={q for q in planned if belongs(q[1],q[2])};pending={q for q in missing if belongs(q[1],q[2])}
        errors=[q for k,q in failed.items() if k in pending]
        routes={(a,b) for _,a,b in expected};attempted={(q['origin'],q['destination']) for q in qs+errors}
        return dict(candidate_airports=len({c for a,b in routes for c in (a,b)}),airports_planned=len({c for a,b in routes for c in (a,b)}),
            airports_searched=len({c for a,b in attempted for c in (a,b)}),airports_returned=len({f[k] for f in fs for k in ('origin','destination')}),
            routes_planned=len(routes),routes_searched=len(attempted),routes_with_search_results=len({(q['origin'],q['destination']) for q in qs if q['status']=='results'}),
            routes_returned=len({(f['origin'],f['destination']) for f in fs}),queries_planned=len(expected),queries_captured=len(qs),
            queries_not_returned=sum(q['status']=='no_matching_direct_flights' for q in qs),
            queries_rejected=sum(q['status']=='rejected_source_records' for q in qs),rejected_records=sum(len(q.get('rejected_flights',[])) for q in qs),
            failed_or_missing_queries=len(pending),failed_queries=len(errors),unattempted_queries=len(pending)-len(errors),
            flights=len(fs),priced_flights=sum('price' in f for f in fs),fare_context_unverified_queries=sum(bool(q.get('price_error')) for q in qs))
    meta={**refs[0]['metadata'],'profile':'gulf','hubs':list(HUBS),'coverage':coverage(),
        'coverage_by_hub':{hub:coverage(hub) for hub in HUBS},'queries':list(queries.values()),
        'uncollected_queries':[list(k) for k in sorted(missing)],'failed_queries':list(failed.values()),
        'priced_flights':sum('price' in f for f in flights.values()),
        'fare_context_unverified_queries':sum(bool(q.get('price_error')) for q in queries.values()),
        'source_date':max(ref['metadata']['source_date'] for ref in refs),
        'airlines':sorted({f['airline'] for f in flights.values()})}
    meta.pop('query_owner',None)
    return dict(airports=sorted(airports.values(),key=lambda a:a['code']),flights=sorted(flights.values(),key=lambda f:(f['departure'],f['id'])),metadata=meta)
