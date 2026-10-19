"""Extract connected Swiss passenger-rail geography from a dated OSM PBF.

Pyosmium is preparation-only. The derived railway database is ODbL 1.0.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_replay_geometry import simplify

SOURCE_URL = 'https://download.geofabrik.de/europe/switzerland-261017.osm.pbf'
SOURCE_SHA256 = '7e35adb483f61ab05d9ec273b3d62aaed4cf6a55d84e17360a3f9066c8384ae9'
OUTPUT = ROOT / 'data/reference/switzerland/osm-rail-2026-10-17.json.gz'


def passenger_track(tags):
    return (tags.get('railway') in {'rail', 'narrow_gauge', 'light_rail', 'preserved'}
            and tags.get('service') not in {'yard', 'spur'}
            and tags.get('usage') not in {'industrial', 'military', 'test'}
            and tags.get('disused') != 'yes' and tags.get('abandoned') != 'yes')


def compact_ways(ways, nodes):
    counts = Counter(node for way in ways.values() for node in way['nodes'])
    result = []
    for key, way in sorted(ways.items()):
        ids = way['nodes']
        # Preserve native junction nodes, including those inside a way.
        cuts = sorted({0, len(ids)-1, *(i for i,n in enumerate(ids) if counts[n] > 1)})
        for a,b in zip(cuts,cuts[1:]):
            selected = ids[a:b+1]
            if len(selected)<2 or any(n not in nodes for n in selected):
                continue
            points = [nodes[n] for n in selected]
            curve = simplify(points)
            # Simplification retains original vertices. Keep their native IDs.
            retained, cursor = [], 0
            for point in curve:
                while nodes[selected[cursor]] != point:
                    cursor += 1
                retained.append(selected[cursor]); cursor += 1
            result.append({'node_ids': retained, 'coordinates': curve, 'speed': 100,
                           'source_way_id': key, 'gauge': way.get('gauge','')})
    return result


def prepare(filename, output):
    import osmium

    digest = file_hash(filename)
    if digest != SOURCE_SHA256:
        raise ValueError('Swiss OSM extract differs from the validated source')

    class Inventory(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}
        def way(self, way):
            if passenger_track(dict(way.tags)) and len(way.nodes)>1:
                self.ways[str(way.id)] = {'nodes':[str(n.ref) for n in way.nodes],
                                          'gauge':way.tags.get('gauge','')}

    inventory = Inventory()
    inventory.apply_file(str(filename), filters=[osmium.filter.KeyFilter('railway')])
    print('selected railway ways',len(inventory.ways),flush=True)
    needed = {n for w in inventory.ways.values() for n in w['nodes']}

    class Locations(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.nodes = {}
        def node(self, node):
            if str(node.id) in needed:
                self.nodes[str(node.id)] = [node.location.lon, node.location.lat]

    locations = Locations()
    locations.apply_file(str(filename), filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    print('selected railway nodes',len(locations.nodes),flush=True)
    ways = compact_ways(inventory.ways, locations.nodes)
    result = {'metadata': {'source':'© OpenStreetMap contributors via Geofabrik Switzerland',
        'source_url':SOURCE_URL,'source_date':'2026-10-17','source_sha256':digest,
        'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'note':'Rail/narrow-gauge/light-rail/preserved track geography; no cableways or funicular tracks. Connections use identical native OSM node IDs, never coordinate snapping. Curves simplified between preserved junctions. October geography is a reference for June schedules, not proof of historical running tracks or diversions.',
        'missing_nodes':len(needed-locations.nodes.keys())}, 'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f, gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print('ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('extract',type=Path)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();prepare(args.extract,args.output)
