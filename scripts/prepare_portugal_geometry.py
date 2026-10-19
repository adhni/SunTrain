"""Convert IP's official Portuguese operating railway network to replay paths.

Preparation only: pyshp and pyproj are required; the dashboard uses neither.
"""
from __future__ import annotations
import argparse
import gzip
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_geometry import compile_ways
SOURCE_URL='https://dados.gov.pt/s/resources/rede-ferroviaria-nacional/20260415-171819/rede-ferroviaria.zip'
SOURCE_SHA256='6065ac244973d192ae705008fe0a6c4fc595b49d74c9f30369fadd22ebef7e19'
OUTPUT=ROOT/'data/reference/portugal/ip-rail-2026-04-15.json.gz'


def prepare(filename, output=OUTPUT):
    import shapefile
    from pyproj import CRS,Transformer
    if file_hash(filename)!=SOURCE_SHA256:raise ValueError('IP geometry differs from the validated source')
    with ZipFile(filename) as z:
        project=Transformer.from_crs(CRS.from_wkt(z.read('Rede_Ferroviaria.prj').decode()),4326,always_xy=True)
        reader=shapefile.Reader(shp=io.BytesIO(z.read('Rede_Ferroviaria.shp')),shx=io.BytesIO(z.read('Rede_Ferroviaria.shx')),dbf=io.BytesIO(z.read('Rede_Ferroviaria.dbf')))
        features=[]
        for i,row in enumerate(reader.iterShapeRecords()):
            if row.record.as_dict()['exploracao']!='Com Exploração' or row.shape.shapeType==0:continue
            g=row.shape.__geo_interface__
            lines=[g['coordinates']] if g['type']=='LineString' else g['coordinates']
            features.append({'properties':{'idgaia':str(i),'type_voie':'VPA','code_ligne':''},
                'geometry':{'type':'MultiLineString','coordinates':[[project.transform(*p[:2]) for p in line] for line in lines]}})
    ways,_=compile_ways(features,[])
    result={'metadata':{'source':'Infraestruturas de Portugal · Rede Ferroviária Nacional',
        'source_url':SOURCE_URL,'source_date':'2026-04-15','source_sha256':SOURCE_SHA256,
        'source_features':len(features),'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
        'attribution':'Infraestruturas de Portugal, Rede Ferroviária Nacional, 15 April 2026, CC BY 4.0. Reprojected, matched and simplified by SunTrain.',
        'note':'Operating railway alignments reprojected from PT-TM06/ETRS89. Coincident original endpoints/vertices form junctions; no proximity snapping or invented crossings. Inferred geographic paths, not exact operating tracks.'},'ways':ways}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f,gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as stream:
        stream.write(json.dumps(result,separators=(',',':'),allow_nan=False).encode())
    print(len(features),'features',len(ways),'ways',output.stat().st_size,'bytes',file_hash(output))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();prepare(a.source,a.output)
