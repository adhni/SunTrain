"""Deterministic union of validated flight views; never a raw-archive concatenation."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile

DAY = '2026-11-02'
ROOT = Path(__file__).resolve().parents[1]
START = int(datetime(2026, 11, 2, tzinfo=timezone.utc).timestamp())
END = START + 86400
NOTE = ('Combined domestic and international captures from SunTrain flight views · 2 November 2026. '
        'Timeline: UTC; airport boards use local dates and times. '
        'Coverage is partial, including gaps near UTC midnight because local capture dates differ. '
        'Fares retain their original currencies without conversion; paths are illustrative.')
CURRENCIES = ('USD', 'EUR', 'MYR')
# Reviewed against the existing national/regional catalogues. Only these aliases
# are accepted; equal present-day offsets are not evidence of airport identity.
TIMEZONES = {
    **{code: ('Asia/Kolkata', {'Asia/Kolkata', 'Asia/Calcutta'})
       for code in ('CCJ', 'CJB', 'IXC', 'IXE', 'IXM', 'JAI', 'LKO', 'PNQ', 'STV')},
    'AKX': ('Asia/Aqtobe', {'Asia/Aqtobe', 'Asia/Oral'}),
    'CIT': ('Asia/Almaty', {'Asia/Almaty', 'Asia/Qyzylorda'}),
    'GUW': ('Asia/Atyrau', {'Asia/Atyrau', 'Asia/Oral'}),
    'SCO': ('Asia/Aqtau', {'Asia/Aqtau', 'Asia/Oral'}),
    'FEG': ('Asia/Tashkent', {'Asia/Tashkent', 'Asia/Samarkand'}),
    'TAS': ('Asia/Tashkent', {'Asia/Tashkent', 'Asia/Samarkand'}),
    'DTW': ('America/Detroit', {'America/Detroit', 'America/New_York'}),
    'EZE': ('America/Argentina/Buenos_Aires', {'America/Argentina/Buenos_Aires', 'America/Buenos_Aires'}),
    'GVA': ('Europe/Zurich', {'Europe/Zurich', 'Europe/Paris'}),
    'MTY': ('America/Monterrey', {'America/Monterrey', 'America/Mexico_City'}),
}
ICAOS = {
    'PDG': ('WIPT', {'WIPT', 'WIEE'}), 'SRG': ('WARS', {'WARS', 'WAHS'}),
    'TJQ': ('WIOD', {'WIOD', 'WIKT'}), 'KTI': ('VDTI', {'VDTI', 'KH-0002'}),
    'TAS': ('UZTT', {'UZTT', 'UTTT'}),
}


def reference_path():
    return Path(os.getenv('SUNTRAIN_WORLD_FLIGHTS_REFERENCE', str(ROOT / f'data/reference/world_flights/{DAY}.json.gz')))


def canonical_airport(airport):
    from dashboard.flight_profiles import PROFILES
    result = dict(airport)
    code = result['code']
    for field, table in [('timezone', TIMEZONES), ('icao', ICAOS)]:
        if code in table:
            value, aliases = table[code]
            if result.get(field) not in aliases:
                raise ValueError(f'Unreviewed {field} for {code}: {result.get(field)}')
            result[field] = value
    frozen = PROFILES['CA'].get('airport_replay_zones', {}).get(code)
    if result.get('replay_timezone') and result['replay_timezone'] != frozen:
        raise ValueError(f'Unreviewed dated replay zone for {code}')
    if frozen:
        result['replay_timezone'] = frozen
    return result


def merge_airport(airports, airport):
    airport = canonical_airport(airport)
    old = airports.get(airport['code'])
    if old and any(old.get(k) != airport.get(k) for k in ('country', 'lat', 'lon', 'icao', 'timezone', 'replay_timezone')):
        raise ValueError(f'Conflicting World airport identity: {airport["code"]}')
    if not old:
        airports[airport['code']] = airport


def identity(flight):
    return tuple(flight[k] for k in ('carrier', 'number', 'origin', 'destination', 'departure', 'arrival'))


def aircraft_name(flight):
    name = str(flight.get('aircraft') or '').strip()
    if name.casefold() in {'', 'unknown', 'not specified', 'aircraft not specified', 'n/a'}:
        return 'Airbus A' + flight['equipment'] if flight.get('equipment') else 'Aircraft not specified'
    return name


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def merge_views(views, start=START, end=END):
    """Each tuple is (view id, validated reference, its existing replay window)."""
    airports, groups, source_ids, before_window = {}, {}, {}, set()
    member_counts = {}
    for city, reference, (local_start, local_end) in views:
        local_count = selected = 0
        for airport in reference['airports']:
            merge_airport(airports, airport)
        for flight in reference['flights']:
            if flight['departure'] >= local_end or flight['arrival'] < local_start:
                continue
            local_count += 1
            key = identity(flight)
            old = source_ids.setdefault(flight['id'], key)
            if old != key:
                raise ValueError(f'Conflicting source flight ID: {flight["id"]}')
            before_window.add(key)
            if flight['departure'] >= end or flight['arrival'] < start:
                continue
            selected += 1
            if key not in groups:
                groups[key] = {'base': dict(flight), 'ids': set(), 'views': set(), 'quotes': {},
                               'aircraft': {}, 'pages': set(), 'dates': set()}
            row = groups[key]
            if row['base']['flight_scope'] != flight['flight_scope']:
                raise ValueError(f'Conflicting flight scope: {flight["id"]}')
            row['ids'].add(flight['id']); row['views'].add(city)
            if flight.get('source_page'): row['pages'].add(flight['source_page'])
            if flight.get('source_date'): row['dates'].add(flight['source_date'])
            name = aircraft_name(flight)
            if name != 'Aircraft not specified' and not flight.get('aircraft_variants'):
                row['aircraft'].setdefault(name, set()).add(city)
            quotes = ([flight['price']] if flight.get('price') else []) + flight.get('fare_quotes', [])
            for quote in quotes:
                quote = {k: v for k, v in quote.items() if k != 'views'}
                if (quote.get('currency') not in CURRENCIES or type(quote.get('amount_minor')) is not int
                    or quote['amount_minor'] <= 0 or tuple(quote.get(k) for k in ('adults', 'cabin', 'trip_type')) != (1, 'economy', 'one_way')):
                    raise ValueError(f'Incompatible captured fare: {flight["id"]}')
                row['quotes'].setdefault(canonical_json(quote), {'quote': dict(quote), 'views': set()})['views'].add(city)
            for variant in flight.get('aircraft_variants', []):
                row['aircraft'].setdefault(variant['aircraft'], set()).add(city)
        metadata = reference['metadata']
        member_counts[city] = {'name': metadata.get('name', metadata.get('profile', city)), 'flights_in_view': local_count,
            'flights_overlapping_utc': selected, 'source': metadata.get('source', city),
            'source_url': metadata.get('source_url'), 'source_date': metadata.get('source_date'),
            'coverage': metadata.get('coverage', {}),
            **({'shared_network_coverage': metadata['shared_network_coverage']} if metadata.get('shared_network_coverage') else {})}
    flights = []
    for key, row in groups.items():
        base = row['base']
        fields = ('number', 'carrier', 'origin', 'destination', 'departure', 'arrival', 'flight_scope')
        record = {k: base[k] for k in fields}
        record['id'] = min(row['ids']) if len(row['ids']) == 1 else 'world:' + hashlib.sha256(canonical_json(key).encode()).hexdigest()[:24]
        record['airline'] = base.get('airline', base['carrier'])
        record['aircraft'] = (next(iter(row['aircraft'])) if len(row['aircraft']) == 1 else
                              'Aircraft differs between captures' if row['aircraft'] else 'Aircraft not specified')
        if len(row['aircraft']) > 1:
            record['aircraft_variants'] = [{'aircraft': name, 'views': sorted(members)} for name, members in sorted(row['aircraft'].items())]
        quotes = sorted(row['quotes'].values(), key=lambda q: (CURRENCIES.index(q['quote']['currency']),
                        q['quote']['amount_minor'], q['quote'].get('captured_at', ''), canonical_json(q['quote'])))
        if quotes:
            record['price'] = quotes[0]['quote']
            if len(quotes) > 1:
                record['fare_quotes'] = [{**q['quote'], 'views': sorted(q['views'])} for q in quotes]
        record['provenance'] = {'views': sorted(row['views']), 'source_ids': sorted(row['ids']),
                                'source_pages': sorted(row['pages']), 'source_dates': sorted(row['dates'])}
        if row['pages']: record['source_page'] = min(row['pages'])
        flights.append(record)
    flights.sort(key=lambda f: (f['departure'], f['id']))
    if len({f['id'] for f in flights}) != len(flights): raise ValueError('Colliding canonical flight IDs')
    returned = {f[k] for f in flights for k in ('origin', 'destination')}
    coverage = {'flights': len(flights), 'airports_returned': len(returned), 'airports_catalogue': len(airports),
                'routes_returned': len({(f['origin'], f['destination']) for f in flights}), 'source_views': len(member_counts)}
    return {'airports': [airports[k] for k in sorted(airports)], 'flights': flights,
        'metadata': {'profile': 'world_flights', 'start_date': DAY, 'end_date': DAY, 'timezone': 'UTC',
            'scope': 'both', 'combined_capture': True, 'source': 'Combined SunTrain flight captures',
            'airport_source_url': 'https://ourairports.com/data/', 'replay_note': NOTE,
            'fare_context': {'currency': 'mixed', 'currencies': list(CURRENCIES), 'adults': 1, 'cabin': 'economy', 'trip_type': 'one_way'},
            'coverage': coverage, 'member_views': member_counts,
            'union_before_utc_window': len(before_window),
            'scopes': dict(sorted(Counter(f['flight_scope'] for f in flights).items()))}}


def prepare(output=None):
    from dashboard.cities import CITIES
    from dashboard.flights import load_reference, replay_window
    from dashboard.flight_sources import cached_reference_reads
    from dashboard import international_expansion
    members = sorted(city for city, settings in CITIES.items() if settings.get('replay_kind') == 'flights' and city != 'world_flights')
    def views(supplement):
        for city in members:
            settings = CITIES[city]
            if not settings['start_date'] <= DAY <= settings['end_date']: raise ValueError(f'World date unavailable: {city}')
            reference = load_reference(DAY, city)
            if supplement is not None:
                reference = international_expansion.overlay(reference, supplement)
            yield city, reference, replay_window(reference, DAY, city)
        if supplement is not None:
            yield international_expansion.PROFILE, supplement, (START, END)
    with cached_reference_reads() as inputs:
        supplement = international_expansion.load_reference()
        result = merge_views(views(supplement))
        if supplement is not None:
            international_expansion.validate_inputs(supplement, inputs)
        result['metadata']['inputs'] = {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): values
                                       for path, values in sorted(inputs.items())}
    destination = Path(output or reference_path()); destination.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json(result).encode()
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(gzip.compress(raw, compresslevel=9, mtime=0)); stream.flush()
            temporary.chmod(0o644)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return result


def load_reference(business_date):
    from dashboard.flight_sources import read_reference
    if business_date != DAY: raise ValueError('Unsupported World flight date')
    result = read_reference(reference_path())
    if result['metadata'].get('profile') != 'world_flights' or result['metadata'].get('start_date') != DAY:
        raise ValueError('Invalid World snapshot context')
    return result
