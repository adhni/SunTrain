"""Compile KRL railway ways and station positions from pinned OSM API extracts."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_jakarta_timetable import NAMES,save
from scripts.prepare_switzerland_geometry import compact_ways
RELATIONS=[16877210,16877211,15094545,2922163,15094546,17193463,17193008]
SOURCE_PINS={'tanah-abang.osm': '932faadb719d7d7acb82d18c94e3b80a3ae5597528e3613418f04e1903b71ee2', 'relation-16877210.osm': '001d33c91ca1be851323429f77f34ad920260a7075b5c7bd6a1bb7e356ef6837', 'relation-16877211.osm': '7f4ac977a2ac7c9017c5d354c1bb0bfbd4d926ede48b4b9a23eea4ed82bfe980', 'relation-17193463.osm': '16fe8e2caaeea55610886c74573c5016207b8e4b4ec6ea6449c8d4dc98220c48', 'relation-15094545.osm': 'a1b67c8a3138b24db11e3d36664b5a473b7c4ae1551692e2c213324282d316ac', 'relation-15094546.osm': 'b72438797613d0e1a9a1c8317a0e65b92b29d3c49ce4977dcd8ec2e5f1b7392d', 'relation-2922163.osm': '4e6d7d59726f7d7f0bcc4ee129de757284ce275c80190e1baac85961b9126787', 'relation-17193008.osm': '3de3c628a8fa44d2797e340423c17a4fbc1aa8b7eb59e56168d17e503e2f0911', 'pondok-rajeg-station.osm': '7dd3ee0b8984b78594f337e584758321c3e81440da7434c644993211c64b778b', 'karet-station.osm': '80bb3c0a47a518db4c91208777351dc9b616ae331266ed22784e1cbde5f364b6'}
OUTPUT=ROOT/'data/reference/jakarta/rail-osm-2026-10-20.json.gz'


def normalized(name):return re.sub(r'[^a-z0-9]','',name.lower().replace('stasiun',''))


def prepare(cache,output=OUTPUT):
    nodes={};ways={};rail_ids=set();sources=[];named=defaultdict(list)
    files=[(f'relation-{i}.osm',f'https://api.openstreetmap.org/api/0.6/relation/{i}/full') for i in RELATIONS]
    files += [('pondok-rajeg-station.osm','https://api.openstreetmap.org/api/0.6/node/1228345121'),
              ('karet-station.osm','https://api.openstreetmap.org/api/0.6/way/605535396/full'),
              ('tanah-abang.osm','https://api.openstreetmap.org/api/0.6/map?bbox=106.806,-6.191,106.816,-6.179')]
    for name,url in files:
        data=(cache/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=SOURCE_PINS[name]:raise ValueError('OSM source differs from audited extract: '+name)
        root=ET.fromstring(data)
        sources.append({'url':url,'sha256':hashlib.sha256(data).hexdigest(),'accessed':'2026-10-20'})
        for e in root:
            key=e.attrib.get('id');tags={t.attrib['k']:t.attrib['v'] for t in e.findall('tag')}
            if e.tag=='node':
                nodes[key]=[float(e.attrib['lon']),float(e.attrib['lat'])]
                if tags.get('name') and (tags.get('railway') in {'stop','station','halt','disused_station'} or key=='1228345121'):
                    named[normalized(tags['name'])].append((0 if tags.get('railway')=='stop' else 1,key))
            elif e.tag=='way':
                ids=[n.attrib['ref'] for n in e.findall('nd')]
                ways[key]={'nodes':ids,'gauge':tags.get('gauge','')}
                if tags.get('railway')=='rail':rail_ids.add(key)
    tracks=compact_ways({k:v for k,v in ways.items() if k in rail_ids},nodes)
    if not tracks:raise ValueError('No native KRL railway ways')
    stations={}
    for code,name in NAMES.items():
        if code=='GMR':continue # Published pass-through only, no KRL passenger call.
        candidates=named.get(normalized(name),[])
        if code=='KAT':
            # Historic station building polygon. Its centroid locates the old
            # station; animation still requires an actual railway anchor.
            ids=ways['605535396']['nodes'];points=[nodes[n] for n in dict.fromkeys(ids)]
            coordinate=[sum(p[i] for p in points)/len(points) for i in range(2)]
            stations[code]={'name':name,'coordinates':coordinate,'osm_id':'way/605535396'};continue
        if not candidates:raise ValueError('Missing station position: '+code+' '+name)
        _,key=min(set(candidates));stations[code]={'name':name,'coordinates':nodes[key],'osm_id':'node/'+key}
    result={'metadata':{'source':'© OpenStreetMap contributors; native KRL route-member ways and station features',
        'source_url':'https://www.openstreetmap.org/copyright','license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'source_date':'2026-10-20','sources':sources,
        'note':'Current railway reference for December 2025 schedules; not observed historic running tracks. Junctions use native OSM node IDs, never nearby-coordinate joins. No community stitched polylines or station-position guesses.'},
        'ways':tracks,'stations':stations}
    save(result,output);print('ways',len(tracks),'stations',len(stations),'bytes',output.stat().st_size,'sha256',hashlib.sha256(output.read_bytes()).hexdigest(),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/jakarta');p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.cache,a.output)
