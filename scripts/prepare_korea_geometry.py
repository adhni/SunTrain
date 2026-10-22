"""Prepare nationwide railway paths and station candidates from the existing OSM PBF."""
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


def prepare(pbf,output):
    import osmium
    class Inventory(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.ways={};self.stations=[];self.polygons=[]
        def station(self,t):
            return (t.get('railway') in {'station','halt','stop_position'} and t.get('name')
                and t.get('disused')!='yes' and t.get('abandoned')!='yes')
        def node(self,n):
            t=dict(n.tags)
            if self.station(t):self.stations.append({'id':'n'+str(n.id),'tags':t,'coordinate':[n.location.lon,n.location.lat]})
        def way(self,w):
            t=dict(w.tags)
            if self.station(t):self.polygons.append({'id':'w'+str(w.id),'tags':t,'nodes':[str(n.ref) for n in w.nodes]})
            if (t.get('railway')=='rail' and t.get('gauge','1435')=='1435' and len(w.nodes)>1
                and t.get('service') not in {'yard','spur'} and t.get('usage') not in {'industrial','military','test'}
                and t.get('disused')!='yes' and t.get('abandoned')!='yes'):
                speeds=[float(v) for v in re.findall(r'\d+(?:\.\d+)?',t.get('maxspeed',''))]
                speed=min(350,max(speeds,default=250 if t.get('highspeed')=='yes' else 100))
                self.ways[str(w.id)]={'nodes':[str(n.ref) for n in w.nodes],'gauge':'1435','speed':max(20,speed)}
    data=Inventory();data.apply_file(str(pbf),filters=[osmium.filter.KeyFilter('railway')])
    needed={n for w in [*data.ways.values(),*data.polygons] for n in w['nodes']}
    class Nodes(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.nodes={}
        def node(self,n):self.nodes[str(n.id)]=[n.location.lon,n.location.lat]
    nodes=Nodes();nodes.apply_file(str(pbf),filters=[osmium.filter.IdFilter(int(n) for n in needed).enable_for(osmium.osm.NODE)])
    for p in data.polygons:
        points=[nodes.nodes[n] for n in p['nodes'] if n in nodes.nodes]
        if points:data.stations.append({'id':p['id'],'tags':p['tags'],'coordinate':[sum(v[i] for v in points)/len(points) for i in [0,1]]})
    ways=compact_ways(data.ways,nodes.nodes)
    for w in ways:w['speed']=data.ways[w['source_way_id']]['speed']
    reader=osmium.io.Reader(str(pbf));stamp=reader.header().get('osmosis_replication_timestamp');reader.close()
    result={'metadata':{'source':'© OpenStreetMap contributors via Geofabrik South Korea','source_url':'https://download.geofabrik.de/asia/south-korea.html',
        'source_sha256':file_hash(pbf),'source_date':stamp,'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'note':'Native rail graph. Speed tags guide high-speed routing costs only, never scheduled arrival times.'},'ways':ways,'stations':data.stations}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:stream.write(json.dumps(result,separators=(',',':')).encode())
    print('ways',len(ways),'station candidates',len(data.stations),'bytes',output.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pbf',type=Path,default=ROOT/'.cache/seoul/south-korea.osm.pbf');p.add_argument('--output',type=Path,default=ROOT/'.cache/korea-rail/tracks.json.gz');a=p.parse_args();prepare(a.pbf,a.output)
