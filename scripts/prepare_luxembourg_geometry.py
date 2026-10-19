"""Compile Luxembourg's official INSPIRE railway links for offline replay."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_geometry import compile_ways
SOURCE_URL='https://download.data.public.lu/resources/inspire-annex-i-theme-transport-networks-rail-railwaylink-3/20261009-231644/tn.railtransportnetwork.railwaylink.gml'
SOURCE_SHA256='89d0142a9ec6821540dd167c0aa5410096ded1d73d8b4218fc220de5ede59eb4'
OUTPUT=ROOT/'data/reference/luxembourg/act-rail-2026-10-09.json.gz'


def prepare(filename,output=OUTPUT):
    from pyproj import Transformer
    if file_hash(filename)!=SOURCE_SHA256:raise ValueError('ACT railway source differs from the validated export')
    # EPSG:3035's declared GML axis order is northing/easting; EPSG:4326
    # is latitude/longitude. Respect both, then store GeoJSON lon/lat.
    transform=Transformer.from_crs(3035,4326)
    ns={'rail':'http://inspire.ec.europa.eu/schemas/tn-ra/5.0','gml':'http://www.opengis.net/gml/3.2'}
    features=[]
    for row in ET.parse(filename).getroot().findall('.//rail:RailwayLink',ns):
        line=row.find('.//gml:LineString',ns);values=list(map(float,line.find('gml:posList',ns).text.split()))
        if line.get('srsName')!='http://www.opengis.net/def/crs/EPSG/0/3035' or len(values)%2:raise ValueError('Unexpected railway coordinate system')
        coordinates=[]
        for a,b in zip(values[::2],values[1::2]):
            lat,lon=transform.transform(a,b)
            if not (5.5<lon<6.8 and 49.3<lat<50.3):raise ValueError('Invalid Luxembourg railway reprojection')
            coordinates.append([lon,lat])
        features.append({'properties':{'idgaia':row.get('{'+ns['gml']+'}id'),'type_voie':'VPA','code_ligne':''},
                         'geometry':{'type':'LineString','coordinates':coordinates}})
    if not features:raise ValueError('No railway links')
    ways,_=compile_ways(features,[])
    result={'metadata':{'source':'Administration du cadastre et de la topographie / Géoportail · INSPIRE RailwayLink',
        'source_url':SOURCE_URL,'source_date':'Resource 2026-10-09; geographic reference for June 2026 schedules',
        'source_sha256':file_hash(filename),'source_features':len(features),'license':'CC0 1.0',
        'license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
        'attribution':'Railway geometry: Administration du cadastre et de la topographie / Géoportail Luxembourg, CC0. Reprojected, matched and simplified by SunTrain.',
        'note':'Inferred geographic paths, not exact operating tracks or historical diversions. Original coincident endpoints/vertices define junctions; no proximity snapping or new crossing intersections.'},'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print('features',len(features),'ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.source,a.output)
