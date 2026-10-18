"""Compile German U-Bahn/Stadtbahn route ways from cached OSM Overpass responses.

The derived railway database is ODbL 1.0. Only native OSM node identities join
tracks. Timetables remain a separate CC BY 4.0 source.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash

OUTPUT = ROOT / 'data/reference/germany/ubahn-osm.json.gz'
# Agency identifiers belong to the pinned 31 May urban archive, not other feeds.
NETWORKS = {
    '44': ('Berlin', 'berlin'), '273': ('Hamburg', 'hamburg'),
    '276': ('München', 'munich'), '271': ('Nürnberg', 'nuremberg'),
    '348': ('Frankfurt', 'frankfurt'), '49': ('Stuttgart', 'stuttgart'),
    '339': ('Hannover', 'hannover'), '294': ('Köln / Bonn', 'cologne-bonn'),
    '83': ('Essen', 'ruhr'), '76': ('Mülheim', 'ruhr'),
    '316': ('Bochum', 'ruhr'), '139': ('Dortmund', 'ruhr'),
    '275': ('Düsseldorf', 'dusseldorf-duisburg'), '123': ('Duisburg', 'dusseldorf-duisburg'),
}
EXTRACTS = {'frankfurt': 'Frankfurt', 'stuttgart': 'Stuttgart', 'hannover': 'Hannover',
            'cologne-bonn': 'Koeln', 'ruhr': 'Dortmund', 'bochum': 'Bochum'}
REFERENCE_REGIONS = {'83': 'dusseldorf-duisburg', '76': 'dusseldorf-duisburg', '316': 'bochum'}
QUERY_BOUNDS = {'berlin': '52.3,13.0,52.7,13.8', 'hamburg': '53.3,9.7,53.9,10.5',
                'munich': '48.12,11.55,48.16,11.6', 'nuremberg': '49.3,10.8,49.65,11.3',
                'dusseldorf-duisburg': '51.0,6.4,51.6,7.0'}


def extract_pbf(filename, codes):
    import osmium  # Offline tool only; never imported by the app/replay builder.

    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways, self.relations = {}, []

        def way(self, way):
            if way.tags.get('railway') in {'subway', 'light_rail', 'tram', 'rail'}:
                self.ways[way.id] = {'type': 'way', 'id': way.id, 'tags': dict(way.tags),
                                     'nodes': [n.ref for n in way.nodes]}

        def relation(self, relation):
            if (relation.tags.get('type') == 'route' and relation.tags.get('route') in {'subway', 'light_rail', 'tram'}
                    and relation.tags.get('ref', '').replace(' ', '') in codes):
                self.relations.append({'type': 'relation', 'id': relation.id, 'tags': dict(relation.tags),
                    'members': [{'type': 'way', 'ref': m.ref, 'role': m.role} for m in relation.members if m.type == 'w']})

    inventory = Inventory()
    inventory.apply_file(str(filename))
    wanted = {m['ref'] for r in inventory.relations for m in r['members'] if m.get('role', '') in {'', 'forward', 'backward'}}
    ways = {key: w for key, w in inventory.ways.items() if key in wanted}
    needed = {node for way in ways.values() for node in way['nodes']}

    class Locations(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {}

        def node(self, node):
            if node.id in needed:
                self.nodes[node.id] = {'lon': node.location.lon, 'lat': node.location.lat}

    locations = Locations()
    locations.apply_file(str(filename))
    complete = []
    for way in ways.values():
        if all(n in locations.nodes for n in way['nodes']):
            complete.append({**way, 'geometry': [locations.nodes[n] for n in way['nodes']]})
    with osmium.io.Reader(str(filename)) as reader:
        timestamp = reader.header().get('osmosis_replication_timestamp')
    return {'elements': [*inventory.relations, *complete], 'osm3s': {'timestamp_osm_base': timestamp}}


def route_ways(response, code):
    ways = {str(e['id']): e for e in response['elements'] if e['type'] == 'way'
            and e.get('tags', {}).get('railway') in {'subway', 'light_rail', 'tram', 'rail'}
            and e.get('tags', {}).get('service') not in {'yard', 'siding', 'spur'}}
    relations = [e for e in response['elements'] if e['type'] == 'relation'
                 and e.get('tags', {}).get('type') == 'route'
                 and e.get('tags', {}).get('route') in {'subway', 'light_rail', 'tram'}
                 and e.get('tags', {}).get('ref', '').replace(' ', '') == code.replace(' ', '')]
    wanted = {str(m['ref']) for r in relations for m in r.get('members', [])
              if m['type'] == 'way' and m.get('role', '') in {'', 'forward', 'backward'}}
    result = []
    for key in sorted(wanted & ways.keys()):
        way = ways[key]
        points = way.get('geometry', [])
        if len(points) != len(way['nodes']) or not all('lon' in p and 'lat' in p for p in points):
            continue
        result.append({'way_id': key, 'node_ids': [str(n) for n in way['nodes']],
                       'coordinates': [[p['lon'], p['lat']] for p in points]})
    colors = {r['tags'].get('colour', '').lstrip('#').upper() for r in relations}
    colors = {c for c in colors if re.fullmatch('[0-9A-F]{6}', c)}
    return result, next(iter(colors)) if len(colors) == 1 else None, [str(r['id']) for r in relations]


def prepare(cache, scope, output=OUTPUT):
    scopes = json.loads(scope.read_text())['routes']
    responses, provenance = {}, []
    for region in sorted({REFERENCE_REGIONS.get(r['agency_id'], NETWORKS[r['agency_id']][1]) for r in scopes.values()}):
        if region in EXTRACTS:
            city = EXTRACTS[region]
            filename = cache / (city + '.osm.pbf')
            codes = {r['route_short_name'].replace(' ', '') for r in scopes.values() if NETWORKS[r['agency_id']][1] == region}
            codes.update(r['route_short_name'].replace(' ', '') for r in scopes.values() if REFERENCE_REGIONS.get(r['agency_id']) == region)
            digest = file_hash(filename)
            cached = cache / (city + '-ubahn-extracted.json')
            response = json.loads(cached.read_text()) if cached.exists() else {}
            if response.get('source_sha256') != digest or response.get('selected_codes') != sorted(codes):
                print('Extracting', city, flush=True)
                response = {**extract_pbf(filename, codes), 'source_sha256': digest, 'selected_codes': sorted(codes)}
                cached.write_text(json.dumps(response, separators=(',', ':')))
            responses[region] = response
            provenance.append({'file': filename.name, 'sha256': digest,
                'source_url': f'https://download.bbbike.org/osm/bbbike/{city}/{city}.osm.pbf',
                'osm_timestamp': response['osm3s']['timestamp_osm_base'], 'region': region})
            continue
        paths = sorted(cache.glob('ubahn-' + region + '*.json'))
        if not paths:
            raise ValueError('Missing OSM reference: ' + region)
        combined = {}
        for path in paths:
            raw = json.loads(path.read_text())
            if raw.get('remark'):
                raise ValueError(raw['remark'])
            for element in raw['elements']:
                key = element['type'], element['id']
                if key in combined and combined[key] != element:
                    raise ValueError('Conflicting OSM snapshots: ' + str(key))
                combined[key] = element
            provenance.append({'file': path.name, 'sha256': file_hash(path),
                'source_url': 'https://overpass.private.coffee/api/interpreter',
                'osm_timestamp': raw.get('osm3s', {}).get('timestamp_osm_base'),
                'query': '[out:json][timeout:40];rel[ref=U35](51.4,7.1,51.6,7.4);out body;way(r);out geom;' if region == 'bochum' else f'[out:json][timeout:{40 if region == "munich" else 25}];rel[route=subway]({QUERY_BOUNDS[region]});out body;way(r);out geom;',
                'region': region})
        responses[region] = {'elements': list(combined.values())}
    lines = {}
    for route in scopes.values():
        agency, code = route['agency_id'], route['route_short_name']
        key = agency + ':' + code
        if key in lines:
            continue
        region = REFERENCE_REGIONS.get(agency, NETWORKS[agency][1])
        ways, color, relations = route_ways(responses[region], code)
        lines[key] = {'ways': ways, 'color': color, 'relations': relations}
        print(NETWORKS[agency][0], code, len(ways), color, flush=True)
    result = {'metadata': {'source': 'OpenStreetMap contributors via Overpass and BBBike extracts',
        'source_url': 'https://www.openstreetmap.org/copyright',
        'license': 'ODbL 1.0', 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
        'references': provenance,
        'note': 'Geographic railway reference; route membership and native node IDs retained. No invented links or proof of individual historical running tracks.'}, 'lines': lines}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as f, gzip.GzipFile(filename='', fileobj=f, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(result, separators=(',', ':'), allow_nan=False).encode())
    print('geometry', file_hash(output), output.stat().st_size, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/germany')
    parser.add_argument('--scope', type=Path, default=ROOT / 'data/reference/germany/ubahn-scope.json')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    prepare(args.cache, args.scope, args.output)
