"""Extract Great Britain's passenger railway tracks for offline historical replay."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_switzerland_geometry import compact_ways
SOURCE_URL='https://download.geofabrik.de/europe/great-britain-261018.osm.pbf'
SOURCE_SHA256='a47a150f448aeb72738019e053c8aa1ce6a3ed65dea6f1b1acd4afed75775065'
OUTPUT=ROOT/'data/reference/great_britain/rail-osm-2026-10-19.json.gz'


def passenger_track(tags):
    return (tags.get('railway') in {'rail','narrow_gauge','preserved'}
        and tags.get('service') not in {'yard','spur'}
        and tags.get('usage') not in {'industrial','military','test'}
        and tags.get('disused')!='yes' and tags.get('abandoned')!='yes')


def speed(tags):
    values=[float(v) for v in re.findall(r'\d+(?:\.\d+)?',tags.get('maxspeed',''))]
    factor=1.609344 if 'mph' in tags.get('maxspeed','').lower() else 1
    return min(350,max(20,max(values)*factor if values else 250 if tags.get('highspeed')=='yes' else 100))


def prepare(filename,output=OUTPUT):
    import osmium
    digest=file_hash(filename)
    if digest!=SOURCE_SHA256:raise ValueError('Great Britain OSM extract differs from the validated source')
    class Inventory(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.ways={}
        def way(self,w):
            tags=dict(w.tags)
            if passenger_track(tags) and len(w.nodes)>1:
                self.ways[str(w.id)]={'nodes':[str(n.ref) for n in w.nodes],'gauge':tags.get('gauge',''),'speed':speed(tags)}
    inventory=Inventory();inventory.apply_file(str(filename),filters=[osmium.filter.KeyFilter('railway')])
    print('railway ways',len(inventory.ways),flush=True)
    needed={n for w in inventory.ways.values() for n in w['nodes']}
    class Locations(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.nodes={}
        def node(self,n):
            if str(n.id) in needed:self.nodes[str(n.id)]=[n.location.lon,n.location.lat]
    locations=Locations();locations.apply_file(str(filename),filters=[osmium.filter.IdFilter(int(n) for n in needed)])
    ways=compact_ways(inventory.ways,locations.nodes)
    for way in ways:way['speed']=inventory.ways[way['source_way_id']]['speed']
    result={'metadata':{'source':'© OpenStreetMap contributors via Geofabrik Great Britain',
        'source_url':SOURCE_URL,'source_date':'Extract retrieved 2026-10-19; geographic reference for October schedules',
        'source_sha256':digest,'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'missing_nodes':len(needed-locations.nodes.keys()),
        'note':'Rail/narrow-gauge/preserved tracks; no metros, trams, roads or ferry bridges. Native OSM nodes define connections, never coordinate snapping. Simplified between preserved junctions. Speeds retained in km/h. Replay routing uses ordered passing-point hints on connected tracks; geometry is an inference, not exact historical running tracks or diversions.'},'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print('ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('extract',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.extract,a.output)
