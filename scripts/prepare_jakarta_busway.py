"""Prepare optional TransJakarta BRT or Mikrotrans from a dated archive.

Non-exact frequencies produce illustrative departures at published headways.
Mikrotrans also retains exact departures where explicitly marked in the source.
Rail preparation remains strict about frequencies; its shared encoding is reused.
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
MIKROTRANS_NOTE = ('Mikrotrans: May 2026 snapshot matched by weekday/weekend, not December 2025 history. '
                  'Most departures are illustrative frequency-based estimates; one JAK.20 pattern is exact in the feed. '
                  'Most departure windows are 05:00–22:00 WIB; JAK.52 also has late services until midnight and one JAK.43B pattern runs 06:00–10:00. '
                  'No live positions or individual passenger loads.')


def selected_route(route, agencies):
    return route['route_type'] == '3' and route.get('route_desc') == 'BRT'


def selected_mikrotrans(route, agencies):
    return (route['route_type'] == '3' and route.get('route_desc') == 'Mikrotrans'
            and route.get('route_short_name', '').upper().startswith('JAK'))


def frequency_departures(rows, *, allow_exact=False):
    """Half-open headway windows; reject overlapping/double-counted templates."""
    departures = set()
    previous_end = -1
    for row in sorted(rows, key=lambda r: seconds(r['start_time'])):
        start, end, headway = seconds(row['start_time']), seconds(row['end_time']), int(row['headway_secs'])
        if row.get('exact_times', '0') not in ({'0', '1'} if allow_exact else {'0'}) or headway <= 0 or end <= start or start < previous_end:
            raise ValueError('Invalid, overlapping or unexpectedly exact frequency window')
        departures.update(range(start, end, headway))
        previous_end = end
    return sorted(departures)


def prepare(cache, output, *, mikrotrans=False):
    select = selected_mikrotrans if mikrotrans else selected_route
    category = 'Mikrotrans' if mikrotrans else 'BRT'
    slug = 'mikrotrans' if mikrotrans else 'busway'
    note = MIKROTRANS_NOTE if mikrotrans else NOTE
    cache.mkdir(parents=True, exist_ok=True)
    original = fetch(URL, cache / 'may-2026.zip')
    if hashlib.sha256(original.read_bytes()).hexdigest() != SHA256:
        raise ValueError('TransJakarta archive changed; inspect before updating the pin')
    frequencies = defaultdict(list)
    with ZipFile(original) as archive:
        routes = {r['route_id'] for r in records(archive, 'routes.txt') if select(r, {})}
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
            raise ValueError('Every selected template must have an explicit frequency window')
        # Exactness belongs to the source trip, and must participate in the
        # pattern signature so shared schedules cannot mix estimates and exact trips.
        exact = {}
        for trip, rows in frequencies.items():
            values = {row.get('exact_times', '0') for row in rows}
            if len(values) != 1:
                raise ValueError('A template mixes exact and estimated frequency windows')
            frequency_departures(rows, allow_exact=mikrotrans)
            exact[trip] = values == {'1'}
        # Extract geometry and timing templates only. We expand frequencies below,
        # keeping shared preparation's rejection of frequencies unchanged.
        templates = cache / ('mikrotrans-templates.zip' if mikrotrans else 'templates.zip')
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
        'source': f'TransJakarta {category} GTFS, archived 7 May 2026; frequency-based illustration',
        'source_url': URL, 'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'attribution': f'GTFS Static Transjakarta © 2026 PT Transportasi Jakarta, CC BY 4.0. Changes by SunTrain: {category} selection, shared timing/path conversion and illustrative headway-based departures. Archive: MobilityDatabase, 7 May 2026.',
        'geometry_source': 'TransJakarta GTFS road shapes',
        'geometry_source_url': 'https://gtfs.transjakarta.co.id/files/file_gtfs.zip',
        'geometry_license': 'CC BY 4.0', 'geometry_license_url': 'https://creativecommons.org/licenses/by/4.0/',
        # The archive's native distance anchors are inconsistent for several
        # routes. Project each ordered stop sequence onto its own supplied shape.
        'geometry_method': 'ordered_projection', 'note': note,
    }
    packed = cache / ('mikrotrans-templates.json.gz' if mikrotrans else 'templates.json.gz')
    prepare_templates('jakarta-' + slug, source, cache / ('build-mikrotrans' if mikrotrans else 'build'), packed, select,
        lambda route, trip: {'mode': 'bus', 'operator': 'TransJakarta', 'route_id': route['route_id'],
            'line': route['route_short_name'] + ' · ' + route['route_long_name'],
            **({'frequency_based': not exact[trip['trip_id']]} if mikrotrans else {})})
    with gzip.open(packed, 'rt') as stream:
        result = json.load(stream)
    pattern_for_trip = {trip: key for rows in result['days'].values() for key, trip, offset in rows}
    if set(pattern_for_trip) != set(trips):
        raise ValueError('Some templates were omitted; inspect the preparation report')
    result['days'] = {str(FIRST + timedelta(days=i)): [] for i in range((LAST-FIRST).days + 1)}
    for pattern in result['patterns'].values():
        if mikrotrans:
            pattern['mode'] = 'mikrotrans'
        else:
            pattern['frequency_based'] = True
    for offset in range(-1, (LAST-FIRST).days + 2):
        service_day = FIRST + timedelta(days=offset)
        active = active_services(calendars, exceptions, service_day)
        for trip, data in trips.items():
            if data['service_id'] not in active:
                continue
            for departure in frequency_departures(frequencies[trip], allow_exact=mikrotrans):
                owner = service_day + timedelta(days=(departure - 10800) // 86400)
                if str(owner) not in result['days']:
                    continue
                arrival = (service_day - owner).days * 86400 + departure - first_departure[trip][1]
                kind = ':scheduled-' if exact[trip] else ':estimate-'
                result['days'][str(owner)].append([pattern_for_trip[trip], trip + kind + str(departure), arrival])
    for rows in result['days'].values():
        rows.sort(key=lambda r: (r[2], r[1]))
    result['metadata'].update(sources=[{'source_url': URL, 'source_date': '2026-05-07', 'sha256': SHA256}],
        frequency_based=True, snapshot_date='2026-05-07', note=note,
        **({'exact_templates': sum(exact.values()), 'estimated_templates': len(exact) - sum(exact.values())} if mikrotrans else {}),
        license_statement_url='https://ppid.transjakarta.co.id/informasi/berkala',
        date_mapping='May 2026 weekday templates displayed on the KRL week; not December 2025 bus history',
        daily_services={d: dict(Counter(result['patterns'][p]['route_id'] for p,t,o in rows)) for d,rows in result['days'].items()})
    for day in result['days']:
        save_reference(daily_reference(result, day), output / (day + '.json.gz'))
    print(category, 'routes', len(routes), 'templates', len(trips), 'daily occurrences', {d: len(v) for d,v in result['days'].items()}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/jakarta/busway')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--mikrotrans', action='store_true', help='Prepare the separate optional Mikrotrans layer instead of BRT')
    args = parser.parse_args()
    prepare(args.cache, args.output or ROOT / 'data/reference/jakarta' / ('mikrotrans' if args.mikrotrans else 'bus'), mikrotrans=args.mikrotrans)
