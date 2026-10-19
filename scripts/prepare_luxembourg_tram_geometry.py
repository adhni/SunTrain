"""Extract connected Luxtram tracks from a pinned OSM Luxembourg extract."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_switzerland_geometry import compact_ways
SOURCE_URL='https://download.geofabrik.de/europe/luxembourg-latest.osm.pbf'
SOURCE_SHA256='cb86963cf266edae26ee81ebafc9360f2d21570096bcdc67b7fb1623b6e3f05a'
OUTPUT=ROOT/'data/reference/luxembourg/luxtram-osm-2026-10-19.json.gz'


def prepare(filename,output=OUTPUT):
    import osmium
    digest=file_hash(filename)
    if digest!=SOURCE_SHA256:raise ValueError('Luxembourg OSM extract differs from the validated source')
    class Inventory(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.ways={}
        def way(self,w):
            if w.tags.get('railway')=='tram' and w.tags.get('service') not in {'yard','siding','spur'}:
                self.ways[str(w.id)]={'nodes':[str(n.ref) for n in w.nodes]}
    inventory=Inventory();inventory.apply_file(str(filename),filters=[osmium.filter.KeyFilter('railway')])
    needed={n for w in inventory.ways.values() for n in w['nodes']}
    class Locations(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.nodes={}
        def node(self,n):
            if str(n.id) in needed:self.nodes[str(n.id)]=[n.location.lon,n.location.lat]
    locations=Locations();locations.apply_file(str(filename),filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    if needed-locations.nodes.keys():raise ValueError('Incomplete tram track extract')
    ways=compact_ways(inventory.ways,locations.nodes)
    result={'metadata':{'source':'© OpenStreetMap contributors via Geofabrik Luxembourg',
        'source_url':SOURCE_URL,'source_date':'Extract retrieved 2026-10-19; geographic reference for June schedules',
        'source_sha256':digest,'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'note':'Tram tracks only, with native OSM node connections. Depots/sidings excluded. Simplified between preserved junctions; no coordinate snapping, road routing or invented links.'},'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print('ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('extract',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.extract,a.output)
