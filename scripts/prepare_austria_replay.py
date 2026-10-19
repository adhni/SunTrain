"""Prepare Austrian passenger trains for 1–7 June 2026 from ÖBB's annual timetable."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compact_transit import save_reference
from scripts.prepare_rail_replay import prepare as prepare_rail

OPERATORS = {'01': 'OEBB Personenverkehr AG Kundenservice', '10': 'Montafonerbahn AG',
             '08': 'City Air Terminal Betriebsgesellschaft m.b.H.'}
SOURCE = {
    'name': 'Austria', 'first': '2026-06-01', 'last': '2026-06-07', 'timezone': 'Europe/Vienna',
    'captured': '2025-12-12', 'published': '2025-12-12',
    'url': 'https://static.web.oebb.at/open-data/soll-fahrplan-gtfs/GTFS_Fahrplan_2026.zip',
    'sha256': 'a1ace21ca33ff5d6c740a1467252a44f7b9bece2692ca9d96e167f639d5ab633', 'calendar_validity': True,
    'source': 'ÖBB Open Data · published 2025/2026 annual passenger timetable',
    'source_url': 'https://data.oebb.at/de/datensaetze~soll-fahrplan-gtfs~',
    'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'attribution': 'Timetable and route shapes: ÖBB-Personenverkehr AG / ÖBB Open Data, 2026 annual timetable published 12 December 2025. Historical selection and simplification by SunTrain.',
    'assign_by_start': ['train'],
    'note': 'Austrian passenger trains from the published 2026 annual timetable, including regional and S-Bahn services, Montafonerbahn and CAT. This is the original annual schedule, not a record of subsequent timetable amendments or actual movements. International journeys retain first through last Austrian station calls and intervening foreign calls. WESTbahn and other operators absent from this source are not included. Metros, trams and buses are excluded. No individual passenger loads.'}


def selected_route(route, agencies):
    agency = route.get('agency_id')
    # This source's 220-A route contains only ATB Tauern car-shuttle trains.
    return (route.get('route_type') == '2' and route.get('route_id') != '11-220-A-j26-1' and agency in OPERATORS
            and agencies.get(agency, {}).get('agency_name') == OPERATORS[agency])


def domestic_sequence(sequence):
    indices = [i for i, row in enumerate(sequence) if row['stop_id'].startswith('at:')]
    return sequence[indices[0]:indices[-1]+1] if len(indices) >= 2 else []


def prepare(cache, output):
    numbers, destinations, audit = {}, {}, Counter()
    def select(sequence, stops):
        clipped = domestic_sequence(sequence)
        if clipped:
            audit['included_candidates'] += 1
            if len(clipped) < len(sequence): audit['clipped_candidates'] += 1
            destinations[sequence[0]['trip_id']] = stops[clipped[-1]['stop_id']]['stop_name']
        else: audit['outside_austrian_scope_or_single_call'] += 1
        return clipped
    def describe(route, trip):
        number = trip.get('trip_short_name', '')
        numbers[trip['trip_id']] = number
        category = number.split()[0] if number else route['route_short_name']
        color = ('00843D' if route['agency_id'] == '08' else
                 '006BB6' if route['agency_id'] == '10' else
                 '6A4C93' if category in {'NJ', 'EN'} else
                 '0074B8' if category == 'S' else 'E20015')
        return {'mode': 'train', 'route_id': route['route_id'],
                'route_short_name': route['route_short_name'], 'category': category,
                # The annual feed repeats broad long-distance corridor names
                # on unrelated local routes. Use its short line identifier.
                'line': route['route_short_name'] + ' · ' + {'01': 'ÖBB', '10': 'Montafonerbahn', '08': 'CAT'}[route['agency_id']],
                'direction': 'Direction ' + {'0': 'A', '1': 'B'}.get(trip.get('direction_id'), 'unknown'),
                'destination': destinations[trip['trip_id']], 'color': color}
    prepare_rail('austria', SOURCE, cache, output, selected_route, describe, select_sequence=select)
    with gzip.open(output, 'rt') as stream: result = json.load(stream)
    used = {t for rows in result['days'].values() for _, t, _ in rows}
    result['train_numbers'] = {t: n for t, n in numbers.items() if n and t in used}
    result['metadata']['scope_audit'] = dict(audit)
    save_reference(result, output)
    print('days', {d: len(rows) for d, rows in result['days'].items()}, 'scope', dict(audit), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/austria')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/austria/2026-06-01.json.gz')
    args = parser.parse_args(); prepare(args.cache, args.output)
