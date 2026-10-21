"""Prepare nationwide Amtrak and Brightline trains from pinned historical GTFS."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.prepare_australian_replay import records
from scripts.prepare_boston_replay import project_stops
from scripts.prepare_replay_geometry import clip_path, point_at, simplify
from scripts.compact_transit import merge_references, save_reference
from zipfile import ZipFile

FIRST, LAST = '2026-10-12', '2026-10-18'
NOTE = ('Amtrak intercity trains and Brightline for 12–18 October 2026. All replay clocks and stop times use '
        'Eastern time (America/New_York), including trains in other time zones. Journeys belong to their '
        '03:00–03:00 departure day and the timeline continues through their multi-day arrivals. '
        'Source train routes and supplied shapes are retained; unsupported paths stay gaps. '
        'Connecting buses, MARC, Shore Line East and other commuter/urban networks are excluded. '
        'Scheduled estimates, not live positions; no individual passenger loads.')
AMTRAK_ARCHIVES = [
    {'start': '2026-10-11', 'end': '2026-10-17', 'captured': '2026-10-11', 'published': '2026-10-10',
     'url': 'https://files.mobilitydatabase.org/mdb-11/mdb-11-202610110034/mdb-11-202610110034.zip',
     'sha256': 'da5edcc943482a339d7f1c1700c6c03c79f0772fd0421f1e64bcc4d195896944'},
    {'start': '2026-10-18', 'end': '2026-10-19', 'captured': '2026-10-18', 'published': '2026-10-17',
     'url': 'https://files.mobilitydatabase.org/mdb-11/mdb-11-202610180152/mdb-11-202610180152.zip',
     'sha256': '4fcb81d7ac94ec05cd0badcdd7677f2595bf12d8df230cbd3d65d877f0b83e48'},
]
SOURCES = {
    'amtrak': {
        'source': 'Amtrak official GTFS, archived 11 and 18 October 2026 by MobilityDatabase',
        'source_url': 'https://content.amtrak.com/content/gtfs/GTFS.zip',
        'license': 'Amtrak GTFS use statement; operator rights retained',
        'license_url': 'https://github.com/user-attachments/files/24483097/Response.-.26-FOI-00215.pdf',
        'attribution': 'Timetable and supplied railway shapes: National Railroad Passenger Corporation (Amtrak); Maple Leaf Canadian section: VIA Rail Canada. Historical archives: MobilityDatabase, 11 and 18 October 2026. SunTrain selects passenger trains, compacts schedules and clips source shapes.',
        'archives': AMTRAK_ARCHIVES,
    },
    'brightline': {
        'captured': '2026-10-11', 'published': '', 'calendar_validity': True,
        'url': 'https://files.mobilitydatabase.org/mdb-1126/mdb-1126-202610110040/mdb-1126-202610110040.zip',
        'sha256': 'f04b391cd9412950c7d7f1d7e22ef4eb6b04ddb1fe825770b235fa64d732d539',
        'source': 'Brightline official GTFS, archived 11 October 2026 by MobilityDatabase',
        'source_url': 'https://feed.gobrightline.com/bl_gtfs.zip',
        'license': 'Operator-published schedule data; Brightline rights retained',
        'license_url': 'https://www.gobrightline.com/website-terms-of-use',
        'attribution': 'Timetable and supplied railway shapes: Brightline Trains LLC. Historical archive: MobilityDatabase, 11 October 2026. SunTrain compacts schedules and clips source shapes. No open-data licence is asserted.',
    },
}


def selected_route(network, route, agencies):
    agency = agencies.get(route.get('agency_id', ''), {}).get('agency_name')
    if route.get('route_type') != '2':
        return False
    if network == 'brightline':
        return route.get('agency_id') == 'BL' and agency == 'Brightline'
    if network == 'amtrak':
        return agency == 'Amtrak' or (agency == 'Via Rail Canada' and route.get('route_long_name') == 'Maple Leaf')
    raise ValueError('Unsupported US intercity network')


def describe_route(network, route, trip):
    return {'mode': 'train', 'route_id': route['route_id'],
            'line': 'Brightline · Miami–Orlando' if network == 'brightline' else route['route_long_name'],
            'operator': 'Brightline' if network == 'brightline' else 'VIA Rail (Maple Leaf)' if route.get('agency_id') == '157' else 'Amtrak',
            'direction': 'To ' + trip['trip_headsign'] if trip.get('trip_headsign') else 'Not specified'}


def shape_legs(points, coordinates):
    """Keep verified legs on the original shape when isolated stops do not match."""
    if len(points) < 2:
        return [None] * (len(coordinates) - 1)
    def curve(a, b):
        path = simplify(clip_path(points, a, b, point_at(points, a), point_at(points, b)))
        return path if len(path) >= 2 else [path[0], path[0]]
    try:
        positions = project_stops(points, coordinates)
        return [curve(a, b) for a, b in zip(positions, positions[1:])]
    except ValueError:
        legs, previous = [], 0
        for first, last in zip(coordinates, coordinates[1:]):
            try:
                a, b = project_stops(points, [first, last], minimum_position=previous)
                legs.append(curve(a, b))
                previous = b
            except ValueError:
                legs.append(None)
        return legs


def amtrak_geometry(routes, trips, shapes):
    """Use this snapshot's supplied shape, or a verified same-route shape if absent."""
    candidates, points = {}, {}
    for trip in trips.values():
        if trip.get('shape_id') in shapes:
            candidates.setdefault(trip['route_id'], set()).add(trip['shape_id'])
    def get_points(identifier):
        if identifier not in points:
            points[identifier] = [p for _, _, p in sorted(shapes.get(identifier, []))]
        return points[identifier]
    def resolve(route, trip, sequence, coordinates):
        own = get_points(trip.get('shape_id', ''))
        if len(own) >= 2:
            return shape_legs(own, coordinates)
        best, coverage = [None] * (len(coordinates) - 1), 0
        for identifier in sorted(candidates.get(route['route_id'], [])):
            legs = shape_legs(get_points(identifier), coordinates)
            matched = sum(leg is not None for leg in legs)
            if matched > coverage:
                best, coverage = legs, matched
            if coverage == len(best):
                break
        return best
    return resolve


def prepare(cache, output):
    references = []
    for network, config in SOURCES.items():
        source = {'first': FIRST, 'last': LAST, 'timezone': 'America/New_York',
                  'geometry_method': 'ordered_projection', 'assign_by_start': ['train'],
                  'geometry_source': network.title() + ' GTFS railway shapes',
                  'geometry_source_url': config['source_url'], 'geometry_license': config['license'],
                  'geometry_license_url': config['license_url'], 'note': NOTE, **config}
        packed = cache / (network + '-prepared.json.gz')
        prepare_rail('us-' + network, source, cache, packed,
                     lambda route, agencies: selected_route(network, route, agencies),
                     lambda route, trip: describe_route(network, route, trip),
                     geometry_resolver_factory=amtrak_geometry if network == 'amtrak' else None)
        with gzip.open(packed, 'rt') as stream:
            result = json.load(stream)
        numbers = {}
        archives = config.get('archives', [config])
        for archive in archives:
            with ZipFile(cache / archive['url'].rsplit('/', 1)[-1]) as feed:
                for trip in records(feed, 'trips.txt'):
                    numbers[trip['trip_id']] = trip.get('trip_short_name') or trip['trip_id']
        result['train_numbers'] = numbers
        references.append((network, result))
    result = merge_references(references, source_name='Amtrak and Brightline historical intercity schedules', replay_note=NOTE)
    save_reference(result, output)
    print('US intercity daily services:', {d: len(rows) for d, rows in result['days'].items()}, flush=True)
    print('Saved', output, output.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/us-intercity')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/us_rail' / (FIRST + '.json.gz'))
    args = parser.parse_args()
    prepare(args.cache, args.output)
