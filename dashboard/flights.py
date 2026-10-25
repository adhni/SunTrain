"""Pinned flight schedules adapted to the existing replay payload."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import gzip
import json
import os

from dashboard.cities import replay_settings
from scripts.prepare_australian_flights import great_circle

DIRECTORY = Path(__file__).resolve().parents[1] / 'data/reference/australia_flights'
DEFAULT = DIRECTORY / '2026-11-02.json.gz'
AIRLINES = {'QF': ('Qantas', '#e53935'), 'VA': ('Virgin Australia', '#aa76db'),
            'JQ': ('Jetstar', '#f57c28'), 'ZL': ('Rex', '#439edd'),
            'FC': ('Link Airways', '#50b6a1'), 'QQ': ('Alliance Airlines', '#eab54d'),
            'FP': ('FlyPelican', '#a1c75b'),
            'GA': ('Garuda Indonesia', '#439edd'), 'QG': ('Citilink', '#63b547'),
            'JT': ('Lion Air', '#e53935'), 'ID': ('Batik Air', '#aa76db'),
            'IW': ('Wings Air', '#f57c28'), 'IU': ('Super Air Jet', '#bb965f'),
            'QZ': ('Indonesia AirAsia', '#ef647b'), 'SJ': ('Sriwijaya Air', '#eab54d'),
            'IN': ('NAM Air', '#50b6a1'), 'IL': ('Trigana Air', '#d88bd6'),
            '8B': ('TransNusa', '#5ba4c6'), 'IP': ('Pelita Air', '#9ca8e7'),
            'OD': ('Batik Air (OD)', '#c58cb6'),
            'SQ': ('Singapore Airlines', '#e5b748'), 'EK': ('Emirates', '#d94e54'),
            'NZ': ('Air New Zealand', '#65b7ad'), 'QR': ('Qatar Airways', '#b57f9c'),
            'CX': ('Cathay Pacific', '#54aa93'), 'UA': ('United', '#649ce0'),
            'AA': ('American', '#a0afc6'), 'DL': ('Delta', '#cf7b89'),
            'FJ': ('Fiji Airways', '#b9956e'), 'TR': ('Scoot', '#e5c547'),
            'MH': ('Malaysia Airlines', '#7c9ada'), 'TG': ('THAI', '#b690d9'), 'AK': ('AirAsia', '#e95055'),
            'FY': ('Firefly', '#ef9b48'), 'MY': ('AirBorneo', '#53b6aa'),
            'D7': ('AirAsia X', '#c75668'), 'BI': ('Royal Brunei', '#bca64b'),
            'EY': ('Etihad Airways', '#bd9d61'), 'FZ': ('flydubai', '#ee9353'),
            '3L': ('Air Arabia Abu Dhabi', '#df8078'),
            '6E': ('IndiGo', '#6996e5'), 'AI': ('Air India', '#e66767'),
            'IX': ('Air India Express', '#f49b50'), 'QP': ('Akasa Air', '#b18bdd'),
            'SG': ('SpiceJet', '#efbd4f'), '9I': ('Alliance Air', '#60b7ac'),
            'S5': ('Star Air', '#df90b3'), 'S9': ('FlyBig', '#89b951'),
            'IC': ('Fly91', '#b89162')}


def airline_style(carrier, name):
    palette = ('#62b4b4', '#d58b68', '#9ba9da', '#d3b85f', '#ba8fc4')
    index = int(hashlib.sha256(carrier.encode()).hexdigest()[:8], 16) % len(palette)
    if carrier == 'MY':
        return (name or AIRLINES[carrier][0], AIRLINES[carrier][1])
    return AIRLINES.get(carrier, (name or carrier, palette[index]))


def reference_path(business_date=None, city='australia_flights'):
    if city=='india_flights':
        return Path(os.getenv('SUNTRAIN_INDIA_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'india_flights/2026-11-02.json.gz')))
    if city=='singapore_flights':
        return Path(os.getenv('SUNTRAIN_SINGAPORE_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'singapore_flights/2026-11-02.json.gz')))
    if city=='gulf_flights':
        from dashboard.gulf_flights import reference_paths as hub_paths
        return hub_paths(business_date)[0]
    if city == 'malaysia_flights':
        return Path(os.getenv('SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE', str(DIRECTORY.parent / 'malaysia_flights/2026-11-02.json.gz')))
    if city == 'indonesia_flights':
        return Path(os.getenv('SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE', str(DIRECTORY.parent / 'indonesia_flights/2026-11-02.json.gz')))
    if city != 'australia_flights':
        raise ValueError(f'Unknown flight country: {city}')
    default = DIRECTORY / '2013-03-04.json.gz' if business_date and business_date.startswith('2013-03-') else DEFAULT
    return Path(os.getenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE', str(default)))


def reference_paths(business_date=None, city='australia_flights'):
    if city=='gulf_flights':
        from dashboard.gulf_flights import reference_paths as hub_paths
        return hub_paths(business_date)
    paths = [reference_path(business_date, city)]
    if city=='singapore_flights':return paths
    prefix = {'indonesia_flights':'INDONESIA','australia_flights':'AUSTRALIA','malaysia_flights':'MALAYSIA','india_flights':'INDIA'}[city]
    # The legacy March 2013 Australian snapshot remains isolated.
    if not (city == 'australia_flights' and business_date and business_date.startswith('2013-03-')):
        override = os.getenv(f'SUNTRAIN_{prefix}_INTERNATIONAL_REFERENCE')
        # A custom domestic fixture is isolated unless international data is explicit.
        if override or not os.getenv(f'SUNTRAIN_{prefix}_FLIGHTS_REFERENCE'):
            international = Path(override or reference_path(business_date, city).with_name('2026-11-02-international.json.gz'))
            if override or international.exists():
                paths.append(international)
    return paths


def snapshot_coverage(reference):
    queries = reference['metadata'].get('queries', [])
    missing = reference['metadata'].get('uncollected_queries', [])
    pairs = {(q['origin'], q['destination']) for q in queries}
    planned = pairs | {(a, b) for _, a, b in missing}
    represented = {f[k] for f in reference['flights'] for k in ('origin', 'destination')}
    return dict(candidate_airports=len({c for pair in planned for c in pair} | represented), airports_returned=len(represented),
        airports_planned=len({c for pair in planned for c in pair}),
        airports_searched=len({c for pair in pairs for c in pair}),
        routes_planned=len(planned), routes_searched=len(pairs),
        routes_with_search_results=len({(q['origin'],q['destination']) for q in queries if q.get('status')=='results'}),
        routes_returned=len({(f['origin'],f['destination']) for f in reference['flights']}),
        queries_planned=len(queries)+len(missing), queries_captured=len(queries),
        queries_not_returned=sum(q.get('status')=='no_matching_direct_flights' for q in queries),
        failed_or_missing_queries=len(missing), unattempted_queries=len(missing), failed_queries=0)


def continuous_arc(a, b):
    """Keep Pacific flights continuous instead of interpolating across the world.

    Use Australia's world copy for both directions so reverse frequency arcs align.
    Longitudes beyond 180 are intentional and supported by MapLibre world copies.
    """
    points = great_circle(a, b)
    previous = 135
    for point in points:
        point[0] += 360 * round((previous - point[0]) / 360)
        previous = point[0]
    return points


def load_reference(business_date, city):
    if city=='gulf_flights':
        from dashboard.gulf_flights import load_reference as hub_reference
        return hub_reference(business_date)
    references = []
    for path in reference_paths(business_date, city):
        with gzip.open(path, 'rt') as stream:
            references.append(json.load(stream))
    country = {'indonesia_flights':'ID','australia_flights':'AU','malaysia_flights':'MY','singapore_flights':'SG','india_flights':'IN'}[city]
    airports, flights = {}, {}
    for reference in references:
        if country in {'SG','IN'}:
            context=reference['metadata'].get('fare_context',{})
            if tuple(context.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way'):
                label='Singapore' if country=='SG' else 'Indian'
                raise ValueError(f'{label} fares require USD, one adult, economy, one-way')
        catalogue = {a['code']: {**a, 'country': a.get('country', country)} for a in reference['airports']}
        for code, airport in catalogue.items():
            if code in airports and airports[code] != airport:
                raise ValueError(f'Conflicting airport identity: {code}')
            airports[code] = airport
        for flight in reference['flights']:
            a, b = catalogue[flight['origin']], catalogue[flight['destination']]
            if country=='SG':
                if not ({flight['origin'],flight['destination']} & {'SIN','XSP'}):
                    raise ValueError('Singapore flight must touch SIN or XSP')
                price=flight.get('price')
                if price and (price.get('currency')!='USD' or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
                    raise ValueError('Singapore prices require positive USD minor units; no implicit conversion')
            if country=='IN':
                price=flight.get('price')
                if price and (tuple(price.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way') or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
                    raise ValueError('Indian prices require positive USD minor units, one adult, economy, one-way; no implicit conversion')
            scope = 'domestic' if a['country'] == b['country'] == country else 'international'
            if scope == 'international' and (a['country'] == country) == (b['country'] == country):
                raise ValueError('Flight has no national endpoint')
            if reference['metadata'].get('scope') == 'international' and scope != 'international':
                raise ValueError('International reference contains a domestic flight')
            if reference['metadata'].get('scope')=='domestic' and scope!='domestic':
                raise ValueError('Domestic reference contains an international flight')
            record = {**flight, 'flight_scope': scope}
            if flight['id'] in flights and flights[flight['id']] != record:
                raise ValueError('Conflicting flight identity')
            flights[flight['id']] = record
    metadata = dict(references[0]['metadata'])
    if city in {'indonesia_flights', 'australia_flights', 'malaysia_flights','india_flights'}:
        coverages = {r['metadata'].get('scope', 'domestic'): r['metadata'].get('coverage') or snapshot_coverage(r) for r in references}
        if len(references) > 1:
            combined = {key: sum(c.get(key, 0) for c in coverages.values()) for key in (
                'routes_planned', 'routes_searched', 'routes_with_search_results', 'routes_returned',
                'queries_planned', 'queries_captured', 'queries_not_returned', 'queries_rejected',
                'rejected_records', 'failed_or_missing_queries', 'failed_queries', 'unattempted_queries')}
            queries = [q for r in references for q in r['metadata'].get('queries', [])]
            missing = [q for r in references for q in r['metadata'].get('uncollected_queries', [])]
            failed = [q for r in references for q in r['metadata'].get('failed_queries', [])]
            searched = {q[k] for q in queries + failed for k in ('origin', 'destination')}
            planned = searched | {code for _, a, b in missing for code in (a, b)}
            combined.update(airports_returned=len(airports), airports_searched=len(searched),
                airports_planned=len(planned), candidate_airports=(len(planned | set(airports)) if country in {'AU','MY','IN'} else
                coverages.get('domestic', {}).get('candidate_airports', 0)
                + coverages.get('international', {}).get('candidate_foreign_airports', 0)))
            coverages['both'] = combined
            metadata['replay_note'] = ('Indonesian domestic and international flight schedules for 2–8 November 2026. Timeline: WIB; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                if country == 'ID' else 'Australian domestic and international flight schedules for 2 November 2026. Timeline: Melbourne time; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.')
            if country in {'MY','IN'}:
                metadata['replay_note']='Malaysian domestic and international flight schedules for 2 November 2026. Timeline: MYT; airport boards use local time. Prices are captured one-adult economy one-way quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                if country=='IN':
                    metadata['scope']='both'
                    metadata['replay_note']='Indian domestic and international flight schedules for 2 November 2026. Timeline: IST; airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                metadata['priced_flights']=sum('price' in f for f in flights.values())
                metadata['priced_flights_by_scope']={r['metadata'].get('scope','domestic'):r['metadata'].get('priced_flights',0) for r in references}
                metadata['fare_context_unverified_queries']=sum(r['metadata'].get('fare_context_unverified_queries',0) for r in references)
            metadata['queries'] = queries
            metadata['uncollected_queries'] = missing
            metadata['failed_queries'] = failed
            metadata['unresolved_airports'] = [a for r in references for a in r['metadata'].get('unresolved_airports', [])]
            metadata['airlines'] = sorted({f.get('airline', f.get('carrier', 'Unknown')) for f in flights.values()})
            metadata['source_dates_by_scope'] = {r['metadata'].get('scope', 'domestic'): r['metadata'].get('source_date') for r in references}
            metadata['source_date'] = max((value for value in metadata['source_dates_by_scope'].values() if value), default=None)
            metadata['coverage'] = combined
        coverages.setdefault('both', coverages.get('domestic', {}))
        metadata['coverage_by_scope'] = coverages
    return dict(airports=list(airports.values()), flights=list(flights.values()), metadata=metadata)


def replay_day(business_date, city='australia_flights'):
    from dashboard.replay import cumulative_distances
    reference = load_reference(business_date, city)
    day = date.fromisoformat(business_date)
    zone = ZoneInfo(replay_settings(city)['timezone'])
    start = int(datetime.combine(day, time(), zone).timestamp())
    end = int(datetime.combine(day + timedelta(days=1), time(), zone).timestamp())
    airports = reference['airports']
    indices = {a['code']: i for i, a in enumerate(airports)}
    services, paths = [], {}
    for flight in reference['flights']:
        # Retain arrivals exactly at midnight so the new day's arrival board owns them.
        if flight['departure'] >= end or flight['arrival'] < start:
            continue
        origin, destination = indices[flight['origin']], indices[flight['destination']]
        a, b = airports[origin], airports[destination]
        route = f"{flight['origin']} → {flight['destination']}"
        key = flight['origin'] + '-' + flight['destination']
        if key not in paths:
            coordinates = continuous_arc([a['lon'], a['lat']], [b['lon'], b['lat']])
            paths[key] = dict(quality='illustrative', coordinates=coordinates, distances=cumulative_distances(coordinates))
        carrier = flight.get('carrier') or ('JQ' if city == 'australia_flights' else 'Unknown')
        operator, color = airline_style(carrier, flight.get('airline'))
        services.append(dict(id=flight['id'], number=flight['number'], mode='flight', operator=operator,
            line=route, route_id=key, direction='Scheduled service', origin=a['name'], destination=b['name'],
            color=color, carrier=carrier, flight_scope=flight['flight_scope'], aircraft=flight.get('aircraft') or ('Airbus A' + flight['equipment'] if flight.get('equipment') else 'Aircraft not specified'),
            operating_airline=flight.get('airline', operator), source_page=flight.get('source_page'),
            **({'price':flight['price']} if flight.get('price') else {}),
            stops=[[origin, flight['departure'], flight['departure']], [destination, flight['arrival'], flight['arrival']]],
            legs=[key], timing_uncertain=False))
    return dict(**replay_settings(city), business_date=business_date,
        start=start, end=end, initial=start + 10 * 3600, day_start_hour=0,
        services=services, stations=airports, paths=paths, geometry={},
        approximate_legs=0, total_legs=len(services), excluded_services=0,
        schedule={**reference['metadata'], 'available': True})
