"""Validated, query-owned international additions used only by World preparation."""
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dashboard.flight_sources import read_reference
from dashboard import world_flights as world

PROFILE = 'world_international_expansion'


def is_international(a, b):
    # Match the existing US/Puerto Rico treatment, without changing identities.
    from dashboard.flight_profiles import PROFILES
    jurisdictions = PROFILES['US']['flight_jurisdictions']
    return jurisdictions.get(a['country'], a['country']) != jurisdictions.get(b['country'], b['country'])


def reference_path():
    return Path(os.getenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE', str(
        world.ROOT / f'data/reference/{PROFILE}/{world.DAY}.json.gz')))


def query_key(flight):
    return flight.get('source_date'), flight['origin'], flight['destination']


def load_reference():
    path = reference_path()
    if not path.exists():
        return None
    result = read_reference(path)
    meta = result['metadata']
    if (meta.get('profile') != PROFILE or meta.get('start_date') != world.DAY
            or meta.get('end_date') != world.DAY or meta.get('timezone') != 'UTC'):
        raise ValueError('Invalid World international supplement context')
    airports = {}
    for airport in result['airports']:
        world.merge_airport(airports, airport)
    owners = {}
    for query in meta['queries']:
        key = tuple(query[k] for k in ('date', 'origin', 'destination'))
        when = datetime.fromisoformat(query['captured_at'].replace('Z', '+00:00'))
        if key in owners or when.tzinfo is None or query['status'] not in {'results', 'no_matching_direct_flights'}:
            raise ValueError('Invalid supplemental query ownership')
        owners[key] = query
    seen = {}
    for flight in result['flights']:
        key = query_key(flight)
        a, b = airports[flight['origin']], airports[flight['destination']]
        if (key not in owners or owners[key]['status'] != 'results' or not is_international(a, b)
                or flight.get('flight_scope') != 'international'
                or not 60 <= flight['arrival'] - flight['departure'] <= 86400
                or datetime.fromtimestamp(flight['departure'], ZoneInfo(a.get('replay_timezone', a['timezone']))).date().isoformat() != key[0]
                or flight['departure'] >= world.END or flight['arrival'] < world.START):
            raise ValueError('Invalid supplemental international flight')
        if seen.setdefault(flight['id'], world.identity(flight)) != world.identity(flight):
            raise ValueError('Conflicting supplemental source identity')
    return result


def overlay(reference, supplement):
    """Remove superseded query records, retaining unchanged identity evidence.

    Official timetable rows absent from Google remain valid independent evidence.
    Matching official identities defer to Google's explicitly owned replacement,
    following the existing Europe preparation policy.
    """
    owners = {tuple(q[k] for k in ('date', 'origin', 'destination')) for q in supplement['metadata']['queries']}
    current = {world.identity(f) for f in supplement['flights']}
    current_ids = {f['id'] for f in supplement['flights']}
    def keep(flight):
        if flight['departure'] >= world.END or flight['arrival'] < world.START:
            return True
        if query_key(flight) not in owners or flight.get('flight_scope') != 'international':
            return True
        if world.identity(flight) in current:
            return True
        if flight.get('schedule_source') == 'ryanair_public_timetable' and flight['id'] not in current_ids:
            return True
        return False
    return {**reference, 'flights': [f for f in reference['flights'] if keep(f)]}


def validate_inputs(supplement, inputs):
    expected = supplement['metadata']['baseline_inputs']
    actual = {str(p.relative_to(world.ROOT)): value for p, value in baseline_inputs(inputs).items() if p != reference_path().resolve()}
    if actual != expected:
        raise ValueError('Existing flight sources changed since the international expansion audit')


def baseline_inputs(inputs):
    """A separately validated domestic addition cannot replace any frozen input."""
    from dashboard import south_america_domestic as domestic
    extra=domestic.reference_path().resolve()
    if extra not in inputs:return inputs
    domestic.load_reference()  # Reject international records or invalid context before allowing the extra input.
    return {p:v for p,v in inputs.items() if p!=extra}
