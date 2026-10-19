"""Compile Infrabel's official railway alignments for offline replay matching."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_geometry import compile_ways

SOURCE_URL = 'https://opendata.infrabel.be/api/explore/v2.1/catalog/datasets/geografische-positie-van-alle-spoorsegmenten/exports/geojson'
OUTPUT = ROOT/'data/reference/belgium/infrabel-tracks-2026-06-15.json.gz'


def prepare(cache,output=OUTPUT):
    filename=cache/'infrabel-segments.geojson'
    catalog=json.loads((cache/'segments-catalog.json').read_text())
    raw=json.loads(filename.read_text())
    if len(raw['features'])!=catalog['metas']['default']['records_count']:
        raise ValueError('Incomplete Infrabel railway export')
    identifiers=[str(f['properties']['id']) for f in raw['features']]
    if len(set(identifiers))!=len(identifiers):
        raise ValueError('Duplicate Infrabel segment IDs')
    # Reuse the endpoint/vertex junction compiler already used for France.
    # Source IDs are segment IDs, not native operational junction identifiers.
    features=[{'geometry':f['geometry'],'properties':{'idgaia':str(f['properties']['id']),
               'type_voie':'VPA','code_ligne':''}} for f in raw['features']]
    ways,_=compile_ways(features,[])
    positions={}
    for way in ways:
        way['source_segment_id']=way.pop('source_track_id').split(':')[0]
        way.pop('line_code')
        for node,point in zip(way['node_ids'],way['coordinates']):
            if node in positions and positions[node]!=point:
                raise ValueError('Conflicting Infrabel junction coordinates')
            positions[node]=point
    result={'metadata':{'source':'Infrabel · geographical position of all railway track segments',
        'source_url':SOURCE_URL,'source_date':'Portal processed 2026-06-15; accessed 2026-10-19 Australia/Melbourne',
        'source_sha256':file_hash(filename),'source_features':len(raw['features']),
        'license':'CC0 1.0','license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
        'license_metadata_url':'https://opendata.infrabel.be/explore/dataset/geografische-positie-van-alle-spoorsegmenten/',
        'note':'Derived geographical paths, not exact running-track records. Original coincident endpoints/vertices join at seven decimal places; interior crossings do not join. No proximity snapping. Curves simplified between preserved junctions; heights are not used for operational routing.'},'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print('ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/belgium')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();prepare(args.cache,args.output)
