"""Extract native Java railway tracks and station references from dated OSM data."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_switzerland_geometry import compact_ways
from scripts.prepare_java_replay import save
SOURCE_URL='https://download.geofabrik.de/asia/indonesia/java-261018.osm.pbf'
SOURCE_SHA256='31fb514159bf252515a95de0b4e47d92f00c1b34d1940477cf5c1de3dcf0d93a'
OUTPUT=ROOT/'data/reference/java/rail-osm-2026-10-18.json.gz'


def prepare(filename,output=OUTPUT):
    import osmium
    digest=hashlib.sha256(filename.read_bytes()).hexdigest()
    if digest!=SOURCE_SHA256:raise ValueError('Java OSM extract differs from the pinned source')
    class Inventory(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.ways={};self.stations=[];self.station_ways={}
        def node(self,node):
            tags=dict(node.tags)
            if tags.get('railway') in {'station','halt','stop'}:
                self.stations.append({'osm_id':'node/'+str(node.id),'tags':tags,'coordinates':[node.location.lon,node.location.lat]})
        def way(self,way):
            tags=dict(way.tags)
            if (tags.get('railway')=='rail' and tags.get('gauge','1067')=='1067'
                and tags.get('service') not in {'yard','spur'} and tags.get('usage') not in {'industrial','military','test'}):
                self.ways[str(way.id)]={'nodes':[str(n.ref) for n in way.nodes],'gauge':tags.get('gauge','1067')}
            elif tags.get('railway') in {'station','halt'}:
                self.station_ways[str(way.id)]={'nodes':[str(n.ref) for n in way.nodes],'tags':tags}
    inventory=Inventory();inventory.apply_file(str(filename),filters=[osmium.filter.KeyFilter('railway')])
    needed={n for w in [*inventory.ways.values(),*inventory.station_ways.values()] for n in w['nodes']}
    class Locations(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.nodes={}
        def node(self,node):
            if str(node.id) in needed:self.nodes[str(node.id)]=[node.location.lon,node.location.lat]
    locations=Locations();locations.apply_file(str(filename),filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    if needed-locations.nodes.keys():raise ValueError('Missing native OSM rail/station nodes')
    for identifier,station in inventory.station_ways.items():
        points=[locations.nodes[n] for n in station['nodes']]
        inventory.stations.append({'osm_id':'way/'+identifier,'tags':station['tags'],
            'coordinates':[sum(p[i] for p in points)/len(points) for i in range(2)]})
    result={'metadata':{'source':'© OpenStreetMap contributors via Geofabrik Java','source_url':SOURCE_URL,
        'source_sha256':digest,'source_date':'2026-10-18','license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'note':'Conventional 1067 mm railway alignments. Native shared node IDs define connections; no invented connectors. October 2026 geography is an alignment reference, not a record of historical platform assignments.'},
        'ways':compact_ways(inventory.ways,locations.nodes),'stations':inventory.stations}
    save(result,output)
    print('ways',len(result['ways']),'stations',len(result['stations']),'bytes',output.stat().st_size,'sha256',hashlib.sha256(output.read_bytes()).hexdigest(),'pbf',digest,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('extract',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.extract,a.output)
