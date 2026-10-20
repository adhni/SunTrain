"""Prepare optional TransJakarta BRT frequency estimates from a dated archive.

These are illustrative departures at the published headways, never claims of
exact timetabled/observed buses. Rail preparation remains strict about frequency
services; its geometry and shared-template encoding are reused here separately.
"""
from collections import defaultdict, Counter
from datetime import date, timedelta
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_boston_replay import fetch
from scripts.prepare_australian_replay import records
from scripts.prepare_rail_replay import prepare as prepare_templates
from scripts.prepare_transit_replay import active_services, seconds
from scripts.compact_transit import daily_reference, save_reference

URL = 'https://files.mobilitydatabase.org/mdb-1909/mdb-1909-202605070137/mdb-1909-202605070137.zip'
SHA256 = 'd6b6db4823b8bfdc11e98f44229bf7afdb797ea85fc96a0a269cb856bc439023'
FIRST, LAST = date(2025, 12, 15), date(2025, 12, 21)
NOTE = ('Busway: May 2026 TransJakarta BRT snapshot matched by weekday/weekend. '
        'Buses are illustrative frequency-based estimates, not exact departures or live positions. '
        'Non-BRT buses and individual passenger loads are excluded.')


def selected_route(route, agencies):
    return route['route_type'] == '3' and route.get('route_desc') == 'BRT'


def frequency_departures(rows):
    """Half-open headway windows; reject overlapping/double-counted templates."""
    departures = set()
    previous_end = -1
    for row in sorted(rows, key=lambda r: seconds(r['start_time'])):
        start, end, headway = seconds(row['start_time']), seconds(row['end_time']), int(row['headway_secs'])
        if row.get('exact_times', '0') != '0' or headway <= 0 or end <= start or start < previous_end:
            raise ValueError('Invalid, overlapping or unexpectedly exact BRT frequency window')
        departures.update(range(start, end, headway))
        previous_end = end
    return sorted(departures)


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    original = fetch(URL, cache / 'may-2026.zip')
    if hashlib.sha256(original.read_bytes()).hexdigest() != SHA256:
        raise ValueError('TransJakarta archive changed; inspect before updating the pin')
    frequencies = defaultdict(list)
    with ZipFile(original) as archive:
        routes = {r['route_id'] for r in records(archive, 'routes.txt') if selected_route(r, {})}
        trips = {r['trip_id']: r for r in records(archive, 'trips.txt') if r['route_id'] in routes}
        calendars = list(records(archive, 'calendar.txt'))
        exceptions = list(records(archive, 'calendar_dates.txt'))
        first_departure = {}
        for row in records(archive, 'stop_times.txt'):
            if row['trip_id'] in trips and (row['trip_id'] not in first_departure or int(row['stop_sequence']) < first_departure[row['trip_id']][0]):
                first_departure[row['trip_id']] = (int(row['stop_sequence']), seconds(row['departure_time']) - seconds(row['arrival_time']))
        for row in records(archive, 'frequencies.txt'):
            if row['trip_id'] in trips:
                frequencies[row['trip_id']].append(row)
        if set(frequencies) != set(trips):
            raise ValueError('Every selected BRT template must have an explicit frequency window')
        # Extract geometry and timing templates only. We expand frequencies below,
        # keeping shared preparation's rejection of frequencies unchanged.
        templates = cache / 'templates.zip'
        with ZipFile(templates, 'w', ZIP_DEFLATED) as target:
            for name in sorted(archive.namelist()):
                if name == 'frequencies.txt':
                    continue
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
                target.writestr(info, archive.read(name))
    source = {
        'first': str(FIRST), 'last': str(LAST), 'timezone': 'Asia/Jakarta',
        'url': templates.resolve().as_uri(), 'sha256': hashlib.sha256(templates.read_bytes()).hexdigest(),
        'captured': '2026-05-07', 'published': '', 'calendar_validity': True, 'assign_by_start': ['bus'],
        'source': 'TransJakarta BRT GTFS, archived 7 May 2026; frequency-based illustration',
        'source_url': URL, 'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'attribution': 'GTFS Static Transjakarta © 2026 PT Transportasi Jakarta, CC BY 4.0. Changes by SunTrain: BRT-only selection, shared timing/path conversion and illustrative headway-based departures. Archive: MobilityDatabase, 7 May 2026.',
        'geometry_source': 'TransJakarta GTFS road shapes',
        'geometry_source_url': 'https://gtfs.transjakarta.co.id/files/file_gtfs.zip',
        'geometry_license': 'CC BY 4.0', 'geometry_license_url': 'https://creativecommons.org/licenses/by/4.0/',
        # The archive's native distance anchors are inconsistent for several
        # routes. Project each ordered stop sequence onto its own supplied shape.
        'geometry_method': 'ordered_projection', 'note': NOTE,
    }
    packed = cache / 'templates.json.gz'
    prepare_templates('jakarta-busway', source, cache / 'build', packed, selected_route,
        lambda route, trip: {'mode': 'bus', 'operator': 'TransJakarta', 'route_id': route['route_id'],
            'line': route['route_short_name'] + ' · ' + route['route_long_name']})
    with gzip.open(packed, 'rt') as stream:
        result = json.load(stream)
    pattern_for_trip = {trip: key for rows in result['days'].values() for key, trip, offset in rows}
    if set(pattern_for_trip) != set(trips):
        raise ValueError('Some BRT templates were omitted; inspect the preparation report')
    result['days'] = {str(FIRST + timedelta(days=i)): [] for i in range((LAST-FIRST).days + 1)}
    for pattern in result['patterns'].values():
        pattern['frequency_based'] = True
    for offset in range(-1, (LAST-FIRST).days + 2):
        service_day = FIRST + timedelta(days=offset)
        active = active_services(calendars, exceptions, service_day)
        for trip, data in trips.items():
            if data['service_id'] not in active:
                continue
            for departure in frequency_departures(frequencies[trip]):
                owner = service_day + timedelta(days=(departure - 10800) // 86400)
                if str(owner) not in result['days']:
                    continue
                arrival = (service_day - owner).days * 86400 + departure - first_departure[trip][1]
                result['days'][str(owner)].append([pattern_for_trip[trip], trip + ':estimate-' + str(departure), arrival])
    for rows in result['days'].values():
        rows.sort(key=lambda r: (r[2], r[1]))
    result['metadata'].update(sources=[{'source_url': URL, 'source_date': '2026-05-07', 'sha256': SHA256}],
        frequency_based=True, snapshot_date='2026-05-07', note=NOTE,
        license_statement_url='https://ppid.transjakarta.co.id/informasi/berkala',
        date_mapping='May 2026 weekday templates displayed on the KRL week; not December 2025 bus history',
        daily_services={d: dict(Counter(result['patterns'][p]['route_id'] for p,t,o in rows)) for d,rows in result['days'].items()})
    for day in result['days']:
        save_reference(daily_reference(result, day), output / (day + '.json.gz'))
    print('BRT routes', len(routes), 'templates', len(trips), 'daily estimates', {d: len(v) for d,v in result['days'].items()}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/jakarta/busway')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/jakarta/bus')
    args = parser.parse_args()
    prepare(args.cache, args.output)
