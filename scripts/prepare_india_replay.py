"""Prepare a local-only Indian intercity rail pilot; source reuse is unresolved."""
from __future__ import annotations

import argparse
import gzip
import json
from functools import lru_cache
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash, records
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail, TimetableArchive
from scripts.prepare_switzerland_geometry import compact_ways

CACHE = ROOT / '.cache/india'
GEOMETRY = CACHE / 'tracks.json.gz'
OUTPUT = CACHE / '2026-08-31.json.gz'
URL = 'https://raw.githubusercontent.com/Neo2308/indianrailways-gtfs/b340b7048e99c18330ad333e8210d61161ac7a43/gtfs/gtfs.zip'
SHA256 = 'a0347d046ccc66b182f08df88dd5eb6153fd19610a58c87d14e1e6910c937be8'
TERMS = 'https://github.com/Neo2308/indianrailways-gtfs/issues/23'
NOTE = ('Local India intercity pilot: community timetable version 30 August 2026, applied to its calendars for '
        '31 August–6 September. Reuse permission remains unresolved; not a published open-data release. '
        'Conventional passenger services numbered 1xxxx/2xxxx, excluding explicitly labelled local, parcel and freight services; '
        'not complete Indian Railways coverage. Missing running-day calendars are excluded, never invented. '
        'Inferred railway geography; unresolved sections stay gaps. Overnight journeys retain original clocks. '
        'No live tracking or individual passenger loads.')


def selected_route(route, agencies):
    number = route.get('route_short_name', '')
    name = route.get('route_long_name', '').upper()
    return (route.get('route_type') == '2' and route.get('agency_id') == '1'
            and agencies.get('1', {}).get('agency_name') == 'Indian Railways'
            and bool(re.fullmatch(r'[12]\d{4}', number))
            and not re.search(r'\b(MEMU|DEMU|EMU|LOCAL|SUBURBAN|PARCEL|GOODS|PASS|PASSENGER)\b', name))


def describe_route(route, trip):
    name = route['route_long_name']
    category, color = 'Intercity / express', 'A34836'
    for word, label, shade in [('VANDE', 'Vande Bharat', '2389B5'), ('RAJDHANI', 'Rajdhani', 'B53649'),
                               ('SHATABDI', 'Shatabdi', '27897A'), ('DURONTO', 'Duronto', '899D22'),
                               ('TEJAS', 'Tejas', 'D08028'), ('HUMSAFAR', 'Humsafar', '5E65A7')]:
        if word in name.upper():
            category, color = label, shade
            break
    return {'mode': 'train', 'operator': 'Indian Railways', 'route_id': category,
            'route_short_name': route['route_short_name'], 'line': category, 'service_name': name, 'category': category,
            'color': color, 'direction': 'Not specified'}


def prepare_geometry(pbf, output):
    import osmium
    class Ways(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}
        def way(self, way):
            t = dict(way.tags)
            if (t.get('railway') == 'rail' and len(way.nodes) > 1
                    and t.get('service') not in {'yard', 'spur'}
                    and t.get('usage') not in {'industrial', 'military', 'test'}
                    and t.get('disused') != 'yes' and t.get('abandoned') != 'yes'):
                self.ways[str(way.id)] = {'nodes': [str(n.ref) for n in way.nodes], 'gauge': t.get('gauge', '')}
    inventory = Ways()
    inventory.apply_file(str(pbf), filters=[osmium.filter.KeyFilter('railway')])
    needed = {n for w in inventory.ways.values() for n in w['nodes']}
    print('India railway ways', len(inventory.ways), 'nodes', len(needed), flush=True)
    class Nodes(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.nodes = {}
        def node(self, node):
            self.nodes[str(node.id)] = [node.location.lon, node.location.lat]
    nodes = Nodes()
    nodes.apply_file(str(pbf), filters=[osmium.filter.IdFilter(int(n) for n in needed).enable_for(osmium.osm.NODE)])
    reader = osmium.io.Reader(str(pbf)); stamp = reader.header().get('osmosis_replication_timestamp'); reader.close()
    result = {'metadata': {'source': '© OpenStreetMap contributors via Geofabrik India',
              'source_url': 'https://download.geofabrik.de/asia/india.html', 'source_sha256': file_hash(pbf),
              'source_date': stamp, 'license': 'ODbL 1.0',
              'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
              'missing_nodes': len(needed - nodes.nodes.keys()),
              'note': 'Current geography, not historical track assignments. Native OSM connections only.'},
              'ways': compact_ways(inventory.ways, nodes.nodes)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(result, separators=(',', ':'), allow_nan=False).encode())
    print('Saved graph', output, output.stat().st_size, flush=True)


def prepare(cache, geometry, output):
    with gzip.open(geometry, 'rt') as stream:
        geographic = json.load(stream)
    graph = FranceRailGraph(geographic['ways'])
    @lru_cache(maxsize=None)
    def leg(a, b):
        curve = graph.leg(list(a), list(b))
        if curve and cumulative_distances(curve)[-1] <= max(5000, 3 * cumulative_distances([a, b])[-1]):
            return curve
        return None
    def resolve(route, trip, sequence, coordinates):
        return [leg(tuple(a), tuple(b)) for a, b in zip(coordinates, coordinates[1:])]
    source = {'first': '2026-08-31', 'last': '2026-09-06', 'timezone': 'Asia/Kolkata',
              'url': URL, 'sha256': SHA256, 'captured': '2026-10-23', 'published': '',
              'source': 'P. Radha Krishna · unofficial Indian Railways timetable, local pilot',
              'source_url': 'https://github.com/Neo2308/indianrailways-gtfs',
              'license': 'Unresolved — local pilot only', 'license_url': TERMS,
              'attribution': 'Community timetable conversion: P. Radha Krishna / Neo2308. '
                  'Railway geography © OpenStreetMap contributors, ODbL 1.0. SunTrain selection and geometry matching.',
              'assign_by_start': ['train'], 'geometry_quality': 'track', 'note': NOTE,
              'geometry_source': geographic['metadata']['source'],
              'geometry_source_url': geographic['metadata']['source_url'],
              'geometry_license': 'ODbL 1.0', 'geometry_license_url': geographic['metadata']['license_url'],
              'geometry_sha256': file_hash(geometry), 'geometry_source_date': geographic['metadata']['source_date']}
    prepare_rail('india', source, cache, output, selected_route, describe_route, geometry_resolver=resolve)
    with gzip.open(output, 'rt') as stream:
        result = json.load(stream)
    with TimetableArchive(cache / 'gtfs.zip') as archive:
        calendars = {r['service_id'] for r in records(archive, 'calendar.txt')}
        result['metadata']['missing_calendar_entries'] = sum(r['service_id'] not in calendars for r in records(archive, 'trips.txt'))
    result['metadata']['distribution_status'] = 'local-only; source permission unresolved'
    save_reference(result, output)
    print('Days', {d: len(v) for d, v in result['days'].items()}, 'bytes', output.stat().st_size, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--geometry', type=Path, default=GEOMETRY)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--prepare-geometry', type=Path)
    args = parser.parse_args()
    if args.prepare_geometry:
        prepare_geometry(args.prepare_geometry, args.geometry)
    else:
        prepare(args.cache, args.geometry, args.output)
