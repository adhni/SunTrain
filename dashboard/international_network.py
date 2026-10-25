"""One shared capture archive, projected into UTC and country-local replay days."""
from datetime import datetime, timedelta
from functools import lru_cache
import gzip
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-11-02'
COUNTRIES = {'AU':'Australia','ID':'Indonesia','MY':'Malaysia','SG':'Singapore','IN':'India',
             'TH':'Thailand','CN':'China','JP':'Japan','KR':'South Korea','AE':'United Arab Emirates','QA':'Qatar'}
CITIES = {'australia_flights':('AU','Australia/Melbourne'),'indonesia_flights':('ID','Asia/Jakarta'),
          'malaysia_flights':('MY','Asia/Kuala_Lumpur'),'singapore_flights':('SG','Asia/Singapore'),
          'india_flights':('IN','Asia/Kolkata'),'china_flights':('CN','Asia/Shanghai'),
          'japan_flights':('JP','Asia/Tokyo'),'south_korea_flights':('KR','Asia/Seoul'),
          'gulf_flights':(None,'Asia/Dubai'),'thailand_flights':('TH','Asia/Bangkok')}
HUBS = {'DXB','AUH','DOH'}
# Earlier Indonesian snapshots stored OurAirports' stable `ident`; newer
# catalogues use the same row's `icao_code`. These are exact pinned row aliases,
# not permission to merge airports sharing a municipality or similar name.
ICAO_ALIASES = {'PDG':{'WIPT','WIEE'},'SRG':{'WARS','WAHS'},'TJQ':{'WIOD','WIKT'}}
NOTE = 'International flights between selected SunTrain flight locations · 2 November 2026. The network clock uses UTC; airport boards use local dates and times. Captured USD/MYR fares are shown in their original currency without conversion. Coverage and prices are partial; paths are illustrative.'


def reference_path():
    return Path(os.getenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(ROOT/'data/reference/international_network/2026-11-02.json.gz')))


@lru_cache(maxsize=8)
def _has_consumer(path, mtime_ns, size, city):
    # A previous shared snapshot may predate this country. Fingerprints keep this
    # inexpensive while allowing an atomically replaced archive to enable it.
    with gzip.open(path, "rt") as stream:
        return city in json.load(stream)["metadata"].get("queries_by_view", {})


def enabled(business_date, city):
    if business_date!=DAY or city not in CITIES or not reference_path().exists():return False
    if city=='thailand_flights':
        path=reference_path();stamp=path.stat()
        if not _has_consumer(str(path),stamp.st_mtime_ns,stamp.st_size,city):return False
    # Existing custom reference fixtures stay isolated unless a shared reference
    # is explicitly provided as well.
    prefix={'gulf_flights':'GULF','south_korea_flights':'SOUTH_KOREA'}.get(city,city.removesuffix('_flights').upper())
    custom=any(os.getenv(f'SUNTRAIN_{prefix}_{suffix}') for suffix in ('FLIGHTS_REFERENCE','INTERNATIONAL_REFERENCE','FLIGHTS_DIRECTORY'))
    return not custom or bool(os.getenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE'))


def window(zone):
    start = datetime.fromisoformat(DAY).replace(tzinfo=ZoneInfo(zone))
    return int(start.timestamp()), int((start+timedelta(days=1)).timestamp())


def belongs(a, b, city, airports):
    if city=='international_network':return True
    if city=='gulf_flights':return bool({a,b} & HUBS)
    country = CITIES[city][0]
    return country in {airports[a]['country'],airports[b]['country']}


def consumer_queries(manifest, city):
    """All origin-local dates potentially overlapping this consumer's day."""
    zone = 'UTC' if city=='international_network' else CITIES[city][1]
    start,end = window(zone); airports = {a['code']:a for a in manifest['airports']}
    result = []
    for a,b in manifest['routes']:
        if not belongs(a,b,city,airports):continue
        origin_zone = ZoneInfo(airports[a]['timezone'])
        first = datetime.fromtimestamp(start-manifest['max_duration'],origin_zone).date()
        last = datetime.fromtimestamp(end-1,origin_zone).date()
        for n in range((last-first).days+1):result.append(((first+timedelta(days=n)).isoformat(),a,b))
    return sorted(result)


def coverage(queries, expected, flights, airports):
    captured = {(q['date'],q['origin'],q['destination']) for q in queries}
    routes = {(a,b) for _,a,b in expected}
    attempted = {(q['origin'],q['destination']) for q in queries}
    missing = set(map(tuple,expected))-captured
    return dict(candidate_airports=len({c for p in routes for c in p}),airports_planned=len({c for p in routes for c in p}),
        airports_searched=len({c for p in attempted for c in p}),airports_returned=len({f[k] for f in flights for k in ('origin','destination')}),
        routes_planned=len(routes),routes_searched=len(attempted),routes_with_search_results=len({(q['origin'],q['destination']) for q in queries if q['status']=='results'}),
        routes_returned=len({(f['origin'],f['destination']) for f in flights}),queries_planned=len(expected),queries_captured=len(captured),
        queries_not_returned=sum(q['status']=='no_matching_direct_flights' for q in queries),
        queries_rejected=sum(q['status']=='rejected_source_records' for q in queries),rejected_records=sum(len(q.get('rejected_flights',[])) for q in queries),
        failed_or_missing_queries=len(missing),failed_queries=0,unattempted_queries=len(missing),
        flights=len(flights),priced_flights=sum(bool(f.get('price')) for f in flights))


def project(reference, city):
    """Projection never mutates archive or another country's cached response."""
    airports = {a['code']:a for a in reference['airports']}
    zone = 'UTC' if city=='international_network' else CITIES[city][1]
    start,end = window(zone)
    flights = [{**f,'flight_scope':'international'} for f in reference['flights']
        if belongs(f['origin'],f['destination'],city,airports) and f['departure']<end and f['arrival']>=start]
    expected = reference['metadata']['queries_by_view'][city]
    expected_keys = set(map(tuple,expected))
    queries = [q for q in reference['metadata']['queries'] if (q['date'],q['origin'],q['destination']) in expected_keys]
    counts = coverage(queries,expected,flights,airports)
    failed = [q for q in reference['metadata'].get('failed_queries',[]) if (q['date'],q['origin'],q['destination']) in expected_keys]
    counts.update(failed_queries=len(failed),unattempted_queries=counts['failed_or_missing_queries']-len(failed))
    captured = {(q['date'],q['origin'],q['destination']) for q in queries}
    meta = {**reference['metadata'],'timezone':zone,'queries':queries,'coverage':counts,'scope':'international',
        'uncollected_queries':[list(q) for q in sorted(expected_keys-captured)],'failed_queries':failed,
        'priced_flights':counts['priced_flights'],'airlines':sorted({f['airline'] for f in flights})}
    meta.pop('queries_by_view',None)
    meta['coverage_by_country_pair'] = {}
    for pair in sorted({tuple(sorted((airports[a]['country'],airports[b]['country']))) for _,a,b in expected}):
        match = lambda a,b: tuple(sorted((airports[a]['country'],airports[b]['country'])))==pair
        qs=[q for q in queries if match(q['origin'],q['destination'])]
        es=[q for q in expected if match(q[1],q[2])]
        fs=[f for f in flights if match(f['origin'],f['destination'])]
        pair_counts=coverage(qs,es,fs,airports)
        pair_failed=sum(match(q['origin'],q['destination']) for q in failed)
        pair_counts.update(failed_queries=pair_failed,unattempted_queries=pair_counts['failed_or_missing_queries']-pair_failed)
        meta['coverage_by_country_pair']['-'.join(pair)] = pair_counts
    meta['priced_flights_by_currency'] = {c:sum(f.get('price',{}).get('currency')==c for f in flights) for c in ('USD','MYR')}
    codes = {f[k] for f in flights for k in ('origin','destination')}
    return dict(airports=[airports[c] for c in sorted(codes)],flights=flights,metadata=meta)


def load_archive():
    with gzip.open(reference_path(),'rt') as stream:reference = json.load(stream)
    airports = {a['code']:a for a in reference['airports']}
    for f in reference['flights']:
        a,b = airports[f['origin']],airports[f['destination']]
        if (a['country'] not in COUNTRIES or b['country'] not in COUNTRIES or a['country']==b['country']
            or any(x['country'] in {'AE','QA'} and x['code'] not in HUBS for x in (a,b))):
            raise ValueError('Flight outside the international network footprint')
        if not 60<=f['arrival']-f['departure']<=86400:raise ValueError('Invalid international duration')
        if any(x['country']=='CN' and x['timezone']!='Asia/Shanghai' for x in (a,b)):
            raise ValueError('Chinese airports require China standard time')
        if any(x['country']=='TH' and x['timezone']!='Asia/Bangkok' for x in (a,b)):
            raise ValueError('Thai airports require ICT Asia/Bangkok')
        price=f.get('price')
        if price and (price.get('currency') not in {'USD','MYR'} or type(price.get('amount_minor')) is not int or price['amount_minor']<=0
            or tuple(price.get(k) for k in ('adults','cabin','trip_type'))!=(1,'economy','one_way')):
            raise ValueError('Invalid original-currency international fare')
    return reference


def overlay(base, city):
    """Shared successful queries own their routes/dates; other captures survive."""
    shared = project(load_archive(),city)
    keys = {(q['date'],q['origin'],q['destination']) for q in shared['metadata']['queries']
            if q['status'] in {'results','no_matching_direct_flights'}}
    flights = {f['id']:f for f in base['flights'] if not (f.get('flight_scope')=='international'
        and (f['source_date'],f['origin'],f['destination']) in keys)}
    flights.update({f['id']:f for f in shared['flights']})
    airports = {a['code']:a for a in base['airports']}
    for a in shared['airports']:
        old = airports.get(a['code'])
        alias=old and {old.get('icao'),a.get('icao')}<=ICAO_ALIASES.get(a['code'],set())
        if old and (any(old.get(k)!=a.get(k) for k in ('country','lat','lon')) or (old.get('icao')!=a.get('icao') and not alias)):
            raise ValueError(f"Conflicting shared airport identity: {a['code']}")
        airports[a['code']] = {**(old or {}),**a}
    meta = {**base['metadata'],'fare_context':shared['metadata']['fare_context'],
        'shared_network_coverage':shared['metadata']['coverage'],'shared_network_note':NOTE,
        'priced_flights':sum(bool(f.get('price')) for f in flights.values()),
        'airlines':sorted({f.get('airline','Unknown') for f in flights.values()})}
    meta['source_date']=max(base['metadata'].get('source_date',''),shared['metadata'].get('source_date',''))
    meta['replay_note']=meta.get('replay_note','').replace('one-way USD quotes','one-way quotes in their original currencies').replace('one-way MYR quotes','one-way quotes in their original currencies')
    meta['source_dates_by_scope']={**meta.get('source_dates_by_scope',{}),'international_network':shared['metadata']['source_date']}
    meta['priced_flights_by_scope']={scope:sum(bool(f.get('price')) for f in flights.values() if f.get('flight_scope')==scope) for scope in ('domestic','international')}
    scopes = dict(meta.get('coverage_by_scope',{}))
    # Existing worldwide route coverage remains separate from the network's
    # selected-country coverage; never label the latter all international routes.
    meta['coverage_by_country_pair'] = shared['metadata']['coverage_by_country_pair']
    if city in {'china_flights','japan_flights','south_korea_flights','thailand_flights'}:
        scopes={'domestic':base['metadata']['coverage'],'international':shared['metadata']['coverage']}
        both={k:scopes['domestic'].get(k,0)+scopes['international'].get(k,0) for k in (
            'routes_planned','routes_searched','routes_returned','routes_with_search_results','queries_planned','queries_captured',
            'queries_not_returned','queries_rejected','rejected_records','failed_or_missing_queries','failed_queries','unattempted_queries')}
        planned={code for q in [*base['metadata'].get('queries',[]),*shared['metadata']['queries']] for code in (q['origin'],q['destination'])}
        searched=set(planned)
        planned.update(code for _,a,b in [*base['metadata'].get('uncollected_queries',[]),*shared['metadata']['uncollected_queries']] for code in (a,b))
        both.update(airports_returned=len(airports),airports_planned=len(planned),candidate_airports=len(planned),airports_searched=len(searched))
        scopes['both']=both;meta['coverage']=both;meta['scope']='both'
        meta['replay_note']='Domestic flights and captured international connections to selected SunTrain flight locations. Airport boards use local dates and times. Coverage and prices are partial; paths are illustrative.'
    if scopes:meta['coverage_by_scope']=scopes
    return dict(airports=sorted(airports.values(),key=lambda a:a['code']),flights=sorted(flights.values(),key=lambda f:(f['departure'],f['id'])),metadata=meta)
