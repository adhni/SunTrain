"""Add dated Vienna U-Bahn schedules to Austria's 1–7 June 2026 replay."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.compact_transit import merge_references, save_reference
from scripts.prepare_austria_replay import SOURCE as NATIONAL, prepare as prepare_national
from scripts.prepare_rail_replay import prepare as prepare_rail

LINES = {'U1', 'U2', 'U3', 'U4', 'U6'}
ARCHIVES = [
    {'start': '2026-05-31', 'end': '2026-06-01', 'captured': '2026-05-26', 'published': '',
     'url': 'https://files.mobilitydatabase.org/mdb-648/mdb-648-202605260032/mdb-648-202605260032.zip',
     'sha256': '915f8c10e08f827c49d724b832d2f644f8bc3325c743d061776f907e56b8e62a'},
    {'start': '2026-06-02', 'end': '2026-06-08', 'captured': '2026-06-02', 'published': '',
     'url': 'https://files.mobilitydatabase.org/mdb-648/mdb-648-202606020029/mdb-648-202606020029.zip',
     'sha256': '9e38d4ea387445af3b91a2bdd25fd31e7e1eacf3c6990135e181348e3c115d70'},
]
SOURCE = {
    'first': NATIONAL['first'], 'last': NATIONAL['last'], 'timezone': 'Europe/Vienna',
    'archives': ARCHIVES, 'calendar_validity': True, 'assign_by_start': ['subway'],
    'source': 'Wiener Linien historical U-Bahn schedules via MobilityDatabase',
    'source_url': 'https://www.data.gv.at/datasets/ab4a73b6-1c2d-42e1-b4d9-049e04889cf0?locale=de',
    'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'attribution': 'Vienna U-Bahn timetable and route shapes: Stadt Wien – Wiener Linien, archived 26 May and 2 June 2026 by MobilityDatabase; selected and simplified by SunTrain.',
    'geometry_source': 'Wiener Linien official historical GTFS route shapes',
    'geometry_source_url': 'https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip',
    'geometry_license': 'CC BY 4.0', 'geometry_license_url': 'https://creativecommons.org/licenses/by/4.0/',
    'note': 'Vienna U1, U2, U3, U4 and U6 from dated Wiener Linien schedules and supplied shapes. Only services active in the selected calendars appear. Buses, replacement buses, trams and WLB are excluded. No individual passenger loads.'}
NOTE = ('Austrian passenger trains from the published 2026 annual timetable, plus Vienna U-Bahn from May/June archives. '
        'Annual train schedules do not reconstruct later amendments. International trains retain Austrian portions and intervening foreign calls. '
        'WESTbahn and other missing train operators remain pending data access. Trams and buses are excluded. Scheduled estimates; no individual passenger loads.')


def selected_route(route, agencies):
    return (route.get('agency_id') == '04' and route.get('route_type') == '1'
            and route.get('route_short_name') in LINES
            and agencies.get('04', {}).get('agency_name') == 'Wiener Linien GmbH & Co KG')


def describe_route(route, trip):
    return {'mode': 'subway', 'operator': 'Wiener Linien', 'route_id': route['route_id'],
            'route_short_name': route['route_short_name'], 'category': route['route_short_name'],
            'line': 'Vienna ' + route['route_short_name'], 'color': route['route_color'],
            'direction': 'Direction ' + {'0': 'A', '1': 'B'}.get(trip.get('direction_id'), 'unknown')}


def prepare(cache, output):
    national = cache / 'at-oebb-week.json.gz'
    valid = False
    if national.exists():
        with gzip.open(national, 'rt') as stream: old = json.load(stream)
        valid = (old['metadata']['sources'][0]['sha256'] == NATIONAL['sha256']
                 and old['metadata']['start_date'] == SOURCE['first'] and old['metadata']['end_date'] == SOURCE['last']
                 and {p['mode'] for p in old['patterns'].values()} == {'train'})
    if not valid: prepare_national(cache, national)
    with gzip.open(national, 'rt') as stream: train = json.load(stream)
    metro = cache / 'vienna-ubahn-week.json.gz'
    prepare_rail('at-vienna', SOURCE, cache, metro, selected_route, describe_route)
    with gzip.open(metro, 'rt') as stream: subway = json.load(stream)
    result = merge_references([('at-oebb', train), ('at-vienna', subway)],
                             source_name='Austrian passenger trains and Vienna U-Bahn', replay_note=NOTE)
    save_reference(result, output)
    print('days', {d: len(rows) for d, rows in result['days'].items()}, 'bytes', output.stat().st_size, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/austria')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/austria/2026-06-01.json.gz')
    args = parser.parse_args(); prepare(args.cache, args.output)
