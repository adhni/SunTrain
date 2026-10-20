"""Prepare optional US commuter trains without duplicating existing MBTA services."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compact_transit import merge_references, save_reference
from scripts.prepare_american_replay import FIRST, LAST, amtrak_geometry as supplied_route_geometry
from scripts.prepare_australian_replay import records
from scripts.prepare_rail_replay import prepare as prepare_rail

SOURCES = json.loads((ROOT / 'data/sources/us_commuter_sources.json').read_text())
NOTE = ('Optional US commuter and regional trains, 12–18 October 2026. All map clocks and stop times '
        'use Eastern time; original agency times are converted once, including western and overnight '
        'services. Departures belong to one 03:00–03:00 Eastern window. Supplied railway geometry is '
        'retained where verified; unsupported sections remain gaps. MBTA is already available in Boston '
        'and is not duplicated. No connecting buses, subway/light rail networks, live positions or passenger loads.')


def selected_route(key, route, agencies):
    source = SOURCES[key]
    agency = route.get('agency_id') or (next(iter(agencies)) if len(agencies) == 1 else None)
    return (agency in source['agency_ids']
            and agency in agencies
            and route.get('route_type') in source['route_types']
            and ('route_ids' not in source or route['route_id'] in source['route_ids']))


def describe_route(key, route, trip):
    name = SOURCES[key]['name']
    label = route.get('route_long_name') or route.get('route_short_name') or route['route_id']
    if label.lower().startswith(name.lower() + ' '):
        label = label[len(name) + 1:]
    return {'mode': 'commuter_rail', 'route_id': route['route_id'], 'operator': name,
            'line': name if label.lower() == name.lower() else name + ' · ' + label}


def geometry_factory(config):
    def factory(routes, trips, shapes):
        # Metrolink supplies named route shapes but omits shape_id in trips.
        # Only the audited same-line IDs are candidates, in this dated ZIP.
        candidates = dict(trips)
        for route_id, identifiers in config.get('route_shapes', {}).items():
            for shape_id in identifiers:
                candidates['shape:' + shape_id] = {'route_id': route_id, 'shape_id': shape_id}
        return supplied_route_geometry(routes, candidates, shapes)
    return factory


def prepare(cache, output):
    references = []
    for key, config in SOURCES.items():
        network_cache = cache / key
        packed = network_cache / 'prepared.json.gz'
        source = {'first': FIRST, 'last': LAST, 'replay_timezone': 'America/New_York',
                  'calendar_validity': True, 'allow_empty_days': True, 'geometry_method': 'ordered_projection',
                  'assign_by_start': ['commuter_rail'], 'source': config['name'] + ' official published GTFS',
                  'geometry_source': config['name'] + ' supplied GTFS railway shapes',
                  'geometry_source_url': config['source_url'], 'geometry_license': config['license'],
                  'geometry_license_url': config['license_url'], 'note': NOTE,
                  'attribution': 'Timetable and supplied railway shapes: ' + config['name']
                      + '. SunTrain selects passenger rail, compacts schedules and converts clocks to Eastern time. '
                      + ('Dated archive: MobilityDatabase. ' if 'files.mobilitydatabase.org' in config['url'] else
                         'Operator-published feed, captured 21 October 2026; source calendars cover the replay week. ')
                      + 'Operator rights and published terms apply; no endorsement.', **config}
        source['additional_shape_ids'] = [shape for identifiers in config.get('route_shapes', {}).values() for shape in identifiers]
        prepare_rail('us-' + key, source, network_cache, packed,
                     lambda route, agencies: selected_route(key, route, agencies),
                     lambda route, trip: describe_route(key, route, trip),
                     geometry_resolver_factory=geometry_factory(config))
        with gzip.open(packed, 'rt') as stream:
            reference = json.load(stream)
        numbers = {}
        for archive in config.get('archives', [config]):
            with ZipFile(network_cache / archive['url'].rsplit('/', 1)[-1]) as feed:
                for trip in records(feed, 'trips.txt'):
                    value = trip.get('trip_short_name') or trip['trip_id']
                    if trip['trip_id'] in numbers and numbers[trip['trip_id']] != value:
                        raise ValueError('Train number differs between snapshots for the same trip ID')
                    numbers[trip['trip_id']] = value
        reference['train_numbers'] = numbers
        references.append((key, reference))
    result = merge_references(references, source_name='US commuter and regional historical schedules', replay_note=NOTE)
    result['metadata']['attribution'] = ('Timetable and supplied railway shapes: '
        + ', '.join(config['name'] for config in SOURCES.values())
        + '. Historical archives: MobilityDatabase; COASTER, Tri-Rail and Rail Runner: operator-published feeds. '
        'SunTrain selects rail services, shares schedules and converts clocks to Eastern time. '
        'Source-specific terms apply; SunTrain is independent of the operators.')
    result['metadata']['operator_sources'] = {
        config['name']: {k: config[k] for k in ['timezone', 'captured', 'source_url', 'license', 'license_url']}
        for config in SOURCES.values()}
    save_reference(result, output)
    print('US commuter daily services:', {d: len(rows) for d, rows in result['days'].items()}, flush=True)
    print('Saved', output, output.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/us-commuter')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/us_rail' / ('commuter-' + FIRST + '.json.gz'))
    args = parser.parse_args()
    prepare(args.cache, args.output)
