"""Build connected Seoul metropolitan railway graphs from South Korea OSM."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_switzerland_geometry import compact_ways


def prepare(pbf, output):
    import osmium
    class Ways(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.ways = {}
        def way(self, w):
            t=dict(w.tags)
            if (t.get('railway') in {'rail','subway'} and t.get('gauge','1435')=='1435'
                    and t.get('service') not in {'yard','spur'} and len(w.nodes)>1
                    and t.get('usage') not in {'industrial','military','test'}
                    and t.get('disused')!='yes' and t.get('abandoned')!='yes'):
                self.ways[str(w.id)]={'nodes':[str(n.ref) for n in w.nodes], 'gauge':t.get('gauge','1435')}
    ways=Ways();ways.apply_file(str(pbf),filters=[osmium.filter.KeyFilter('railway')])
    needed={n for w in ways.ways.values() for n in w['nodes']}
    class Nodes(osmium.SimpleHandler):
        def __init__(self):super().__init__();self.nodes={}
        def node(self,n):self.nodes[str(n.id)]=[n.location.lon,n.location.lat]
    nodes=Nodes();nodes.apply_file(str(pbf),filters=[osmium.filter.IdFilter(int(n) for n in needed).enable_for(osmium.osm.NODE)])
    reader=osmium.io.Reader(str(pbf));stamp=reader.header().get('osmosis_replication_timestamp');reader.close()
    result={'metadata':{'source':'© OpenStreetMap contributors via Geofabrik South Korea',
        'source_url':'https://download.geofabrik.de/asia/south-korea.html','source_sha256':file_hash(pbf),
        'source_date':stamp,'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'missing_nodes':len(needed-nodes.nodes.keys())},'ways':compact_ways(ways.ways,nodes.nodes)}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':')).encode())
    print('Track ways',len(result['ways']),'missing nodes',result['metadata']['missing_nodes'],'bytes',output.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pbf',type=Path,default=ROOT/'.cache/seoul/south-korea.osm.pbf')
    p.add_argument('--output',type=Path,default=ROOT/'.cache/seoul/tracks.json.gz')
    a=p.parse_args();prepare(a.pbf,a.output)
