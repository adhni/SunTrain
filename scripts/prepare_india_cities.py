"""Prepare Kochi, Delhi and Chennai rail using pinned source GTFS and shared paths."""
from __future__ import annotations

import argparse
from datetime import date
from functools import lru_cache
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import merge_references, save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail

CACHE = ROOT / '.cache/india-cities'
WEEK = ('2025-12-15', '2025-12-21')
CHENNAI_WEEK = ('2026-10-12', '2026-10-18')
METRO_WEEK = ('2021-12-13', '2021-12-19')
SOURCES = {
    'kochi': ('https://kochimetro.org/opendata/KMRLOpenData.zip',
              '26347766f41574bbde22e57c1ac12d8c169baed10ea7ea232008ffb428fcb158'),
    'delhi': ('https://ethanc8.github.io/delhi-gtfs/metro.zip',
              'fe9d74757a192bac058560d252c0edee6ad6a0eb2693005f71f0106a7ef711c3'),
    'cmrl': ('https://test.cumta.org/CMRL%20gtfs.zip',
             '094f6cfb2e393e5f0ccf516dc7ad41aa25e766d836c98a0b8b682dac090fc3e9'),
    'srr': ('https://test.cumta.org/Southern%20Railways.zip',
            'da3f41ab4f83ad6a4f629f4b24f706ad939114e6348a4738e875fb6080ff5533'),
}
OUTPUTS = {'kochi': ROOT / 'data/reference/kochi/2025-12-15.json.gz',
           'delhi': CACHE / 'delhi/2025-12-15.json.gz',
           'chennai': CACHE / 'chennai/2026-10-12.json.gz'}
TERMS = {'kochi': 'https://kochimetro.org/open-data/', 'delhi': 'https://otd.delhi.gov.in/terms',
         'cmrl': 'https://test.cumta.org/', 'srr': 'https://test.cumta.org/'}
OPERATORS = {'kochi': 'Kochi Metro Rail Limited', 'delhi': 'Delhi Metro Rail Corporation',
             'cmrl': 'Chennai Metro Rail Limited', 'srr': 'Southern Railway'}
NOTES = {
    'kochi': 'Kochi Metro schedules for 15–21 December 2025 from the official calendar. Supplied track shapes; no passenger counts or live tracking.',
    'delhi': 'Delhi, Noida Aqua and Gurgaon Rapid Metro: approximate OTD timetable preserved by ethanc8. Weekday pilot for 15–19 December 2025; the mirror lacks Sunday trips and contains only 59 Saturday trips, so a complete weekend is not shown. Calendar application, not a reconstruction of historical disruptions. Local pilot; source reuse conditions require clarification.',
    'cmrl': 'Historical Chennai Metro timetable for 13–19 December 2021. The source has Monday–Saturday service only; missing Sunday service is not invented. Local pilot; source redistribution terms are unspecified.',
    'srr': 'Chennai suburban rail from the October 2026 CUMTA snapshot, applied to 12–18 October source calendars. The implausible 2170 calendar end is not evidence of future validity. Local pilot; source redistribution terms are unspecified.',
}


def select_route(feed, route, agencies):
    expected = OPERATORS[feed]
    agency = route.get('agency_id') or (next(iter(agencies)) if len(agencies) == 1 else '')
    # SR encodes suburban railway as type 1; explicit operator scope prevents
    # interpreting it as metro or accidentally accepting buses.
    return route.get('route_type') == '1' and agencies.get(agency, {}).get('agency_name') == expected


def describe(feed, route, trip):
    if feed == 'srr':
        return {'mode': 'train', 'operator': OPERATORS[feed], 'route_id': route['route_long_name'],
                'route_short_name': route['route_short_name'], 'line': route['route_long_name'],
                'color': '800000', 'direction': 'Not specified'}
    return {'mode': 'subway', 'operator': OPERATORS[feed], 'route_id': route['route_id'],
            'route_short_name': route.get('route_short_name') or route['route_id'],
            'line': route.get('route_long_name', '').strip() or 'Kochi Metro',
            'color': route.get('route_color') or ('009CA6' if feed == 'kochi' else '687B8C')}


def suburban_resolver(geometry):
    graph = FranceRailGraph(geometry['ways'])
    @lru_cache(maxsize=None)
    def leg(a, b):
        path = graph.leg(list(a), list(b))
        return path if path and cumulative_distances(path)[-1] <= max(5000, 3*cumulative_distances([a,b])[-1]) else None
    return lambda route, trip, sequence, coordinates: [leg(tuple(a),tuple(b)) for a,b in zip(coordinates,coordinates[1:])]


def prepare_feed(feed, cache, output, geometry=None):
    url, digest = SOURCES[feed]
    first, last = METRO_WEEK if feed == 'cmrl' else CHENNAI_WEEK if feed == 'srr' else WEEK
    if feed == 'delhi':
        last = '2025-12-19'
    source = {'first': first, 'last': last, 'timezone': 'Asia/Kolkata', 'url': url, 'sha256': digest,
              'captured': '2026-10-23', 'published': '', 'calendar_validity': True,
              'assign_by_start': ['train', 'subway'], 'allow_empty_days': feed == 'cmrl',
              'source': OPERATORS[feed] + (' via ethanc8 preserved OTD feed' if feed == 'delhi' else ' via CUMTA' if feed in {'srr','cmrl'} else ' official GTFS'),
              'source_url': 'https://otd.delhi.gov.in/data/staticDMRC/' if feed == 'delhi' else TERMS[feed],
              'license': 'KMRL Open Data Terms' if feed == 'kochi' else 'Reuse conditions unresolved — local pilot',
              'license_url': TERMS[feed], 'note': NOTES[feed],
              'attribution': 'Contains data provided by Kochi Metro Rail Limited' if feed == 'kochi' else
                  'Delhi OTD / DMRC · preserved and route labels/colours consolidated by ethanc8' if feed == 'delhi' else
                  OPERATORS[feed] + ' · downloaded from CUMTA Transit Data portal; source clocks retained by SunTrain.'}
    resolver = None
    if feed == 'delhi':
        source['geometry_method'] = 'native_or_ordered_per_leg'
    source.update({'geometry_source': OPERATORS[feed] + ' supplied GTFS railway shapes',
                   'geometry_source_url': url, 'geometry_license': source['license'],
                   'geometry_license_url': TERMS[feed], 'geometry_source_date': 'Source calendar snapshot; retrieved 23 October 2026',
                   'geometry_sha256': digest})
    if feed == 'srr':
        with gzip.open(geometry, 'rt') as stream:
            geo = json.load(stream)
        source.update({'geometry_source': geo['metadata']['source'], 'geometry_source_url': geo['metadata']['source_url'],
                       'geometry_license': 'ODbL 1.0', 'geometry_license_url': geo['metadata']['license_url'],
                       'geometry_source_date': geo['metadata']['source_date'], 'geometry_sha256': file_hash(geometry),
                       'geometry_quality': 'track'})
        resolver = suburban_resolver(geo)
    prepare_rail(feed, source, cache, output, lambda r,a: select_route(feed,r,a),
                 lambda r,t: describe(feed,r,t), geometry_resolver=resolver)


def merge_chennai(suburban, metro):
    mapping = {day: next(s for s in metro['days'] if date.fromisoformat(s).weekday() == date.fromisoformat(day).weekday())
               for day in suburban['days']}
    metro['days'] = {day: metro['days'][original] for day, original in mapping.items()}
    result = merge_references([('srr', suburban), ('cmrl-2021', metro)],
        source_name='Chennai suburban rail with a historical metro weekday comparison',
        replay_note=NOTES['srr'] + ' Metro uses the separate 13–19 December 2021 timetable matched by weekday; '
                    'it is not an October 2026 metro schedule. Sunday metro service is unavailable in that source. '
                    'Only connected railway paths are animated; unresolved legs stay hidden.')
    result['metadata']['source_date_mappings'] = [{'network': 'Chennai Metro', 'display_date': day, 'source_date': original}
                                                for day, original in mapping.items()]
    result['metadata']['distribution_status'] = 'local-only; CUMTA source reuse terms unspecified'
    return result


def prepare(city, cache=CACHE, geometry=ROOT/'.cache/india/tracks.json.gz'):
    if city != 'chennai':
        prepare_feed(city, cache/city, OUTPUTS[city])
        return OUTPUTS[city]
    for feed in ['srr', 'cmrl']:
        prepare_feed(feed, cache/feed, cache/feed/'week.json.gz', geometry)
    with gzip.open(cache/'srr/week.json.gz','rt') as stream:
        suburban = json.load(stream)
    with gzip.open(cache/'cmrl/week.json.gz','rt') as stream:
        metro = json.load(stream)
    save_reference(merge_chennai(suburban, metro), OUTPUTS[city])
    return OUTPUTS[city]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('city', choices=['kochi','delhi','chennai','all'])
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--geometry', type=Path, default=ROOT/'.cache/india/tracks.json.gz')
    args = parser.parse_args()
    for city in ['kochi','delhi','chennai'] if args.city == 'all' else [args.city]:
        print(prepare(city, args.cache, args.geometry), flush=True)
