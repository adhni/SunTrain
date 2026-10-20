"""Convert the official 19 September 2026 LRT Jakarta PDF and native tracks."""
from datetime import date, timedelta
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_jakarta_timetable import save, extended_times

PDF_URL = 'https://drive.google.com/uc?export=download&id=1mBXkx0-9OHVZCXrU-1FCK2yzHjCZMcfh'
PDF_SHA256 = '719a9e1ef4a1813b6d7ae7d4b129cc64bcf938e2db8b07e15b31596a5a9e8892'
SOURCE = ROOT / 'data/reference/jakarta/lrt-jakarta-timetable-2026-09-19.json.gz'
GEOMETRY = ROOT / 'data/reference/jakarta/lrt-jakarta-osm-2026-10-20.json.gz'
SOURCE_SHA256 = '858c0917d413ed79b33b3f131f49512545ef028c9a0ee21b60a9ffb387e44b3a'
GEOMETRY_SHA256 = '04e260e8ea949268e341e631b67b189d0f7dc28f925a3b7da5616fc3673ec5b9'
NAMES = dict(item.split(':',1) for item in ('KPG:Kelapa Gading|BVU:Boulevard Utara Summarecon Mall|'
    'BVS:Boulevard Selatan|PUM:Pulomas|EQT:Equestrian|VLD:Velodrome|RWM:Rawamangun|'
    'PKA:Pramuka|MAT:Matraman|PKM:Proklamasi|MGI:Manggarai').split('|'))
NOTE = ('LRT Jakarta: official timetable valid from 19 September 2026, displayed on matching weekdays. '
        'Pramuka, Matraman and Proklamasi are pass-throughs in this edition; published short trips are retained.')


def parse_tables(tables):
    trips = []
    for table, direction in zip(tables[:2], ['south','north']):
        if table[0][:2] != ['Loop','KA'] or set(table[0][2:]) != set(NAMES):
            raise ValueError('Unexpected LRT Jakarta PDF headers')
        codes = table[0][2:]
        for row in table[2:]:
            if len(row) != 13 or not re.fullmatch(r'\d{4}',row[1] or ''):
                raise ValueError('Invalid LRT Jakarta PDF row')
            calls = []
            for code, value in zip(codes,row[2:]):
                value = (value or '').strip()
                if value in {'-', 'Ls.'}: continue
                if not re.fullmatch(r'\d{1,2}:\d{2}',value): raise ValueError('Unknown timetable cell: '+value)
                calls.append([code,extended_times([value])[0]])
            if len(calls)<2 or any(b[1]<=a[1] for a,b in zip(calls,calls[1:])):
                raise ValueError('Incomplete/backwards LRT Jakarta row: '+row[1])
            trips.append({'number':row[1], 'loop':row[0], 'direction':direction, 'calls':calls})
    if len({t['number'] for t in trips}) != len(trips): raise ValueError('Duplicate published train number')
    return trips


def extract_pdf(cache):
    import pdfplumber # Preparation only; runtime/replay builds do not need PDF tooling.
    pdf = cache/'timetable.pdf'
    if hashlib.sha256(pdf.read_bytes()).hexdigest()!=PDF_SHA256: raise ValueError('Official PDF changed')
    with pdfplumber.open(pdf) as document:
        text=document.pages[0].extract_text()
        if len(document.pages)!=1 or 'Berlaku Mulai 19 September 2026' not in text: raise ValueError('Unexpected PDF edition')
        trips=parse_tables(document.pages[0].extract_tables())
    save({'metadata':{'source':'PT LRT Jakarta official train timetable, valid from 19 September 2026',
        'source_url':PDF_URL, 'published':'2026-09-18','valid_from':'2026-09-19','sha256':PDF_SHA256,
        'official_distribution':'https://linktr.ee/lrtjkt','license':'Published operator timetable; source rights retained',
        'note':'Daily published table; no separate weekday/weekend restriction is printed. Ls. means no passenger call. One event per printed station time; no invented dwell.'},
        'trips':trips}, SOURCE)
    print('source',hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE.stat().st_size,'trips',len(trips),flush=True)


def prepare_geometry(cache):
    from scripts.prepare_switzerland_geometry import compact_ways
    directions={}
    for direction,identifier in [('south',10693160),('north',10693119)]:
        path=cache/f'relation-{identifier}.osm';root=ET.fromstring(path.read_bytes())
        nodes={e.get('id'):[float(e.get('lon')),float(e.get('lat'))] for e in root.findall('node')}
        ways={e.get('id'):{'nodes':[n.get('ref') for n in e.findall('nd')],'gauge':'1435'} for e in root.findall('way')
              if any(t.get('k')=='railway' and t.get('v')=='light_rail' for t in e.findall('tag'))}
        relation=next(e for e in root.findall('relation') if e.get('id')==str(identifier))
        stop_ids=[m.get('ref') for m in relation.findall('member') if m.get('type')=='node' and m.get('role','').startswith('stop')]
        codes=list(NAMES) if direction=='south' else list(reversed(NAMES))
        if len(stop_ids)!=len(codes): raise ValueError('Unexpected OSM station sequence')
        node_elements={e.get('id'):e for e in root.findall('node')}
        for code,node_id in zip(codes,stop_ids):
            if not any(t.get('k')=='name' and t.get('v')==NAMES[code] for t in node_elements[node_id].findall('tag')):
                raise ValueError('OSM station order/name changed: '+code)
        directions[direction]={'stations':{c:{'name':NAMES[c], 'coordinates':nodes[n], 'osm_id':n} for c,n in zip(codes,stop_ids)},
            'ways':compact_ways(ways,nodes),'source_url':f'https://api.openstreetmap.org/api/0.6/relation/{identifier}/full',
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    save({'metadata':{'source':'© OpenStreetMap contributors','source_date':'2026-10-20',
        'license':'ODbL 1.0','license_url':'https://opendatacommons.org/licenses/odbl/1-0/'},'directions':directions},GEOMETRY)
    print('geometry',hashlib.sha256(GEOMETRY.read_bytes()).hexdigest(),GEOMETRY.stat().st_size,flush=True)


def build():
    from dashboard.replay import cumulative_distances
    from scripts.compact_transit import compact_reference
    from scripts.prepare_france_replay import FranceRailGraph
    for path,pin in [(SOURCE,SOURCE_SHA256),(GEOMETRY,GEOMETRY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:raise ValueError('LRT Jakarta reference changed: '+str(path))
    with gzip.open(SOURCE,'rt') as stream:source=json.load(stream)
    with gzip.open(GEOMETRY,'rt') as stream:geography=json.load(stream)
    graphs={d:FranceRailGraph(g['ways']) for d,g in geography['directions'].items()}
    result={'stations':[],'patterns':{},'paths':{},'days':{str(date(2025,12,15)+timedelta(days=i)):[] for i in range(7)},'train_numbers':{}}
    ids={}
    for trip in source['trips']:
        direction=trip['direction'];geo=geography['directions'][direction];calls=trip['calls'];start=calls[0][1];legs=[]
        for code,t in calls:
            if (direction,code) not in ids:
                ids[direction,code]=len(result['stations']);p=geo['stations'][code]
                result['stations'].append({'name':p['name'],'lon':p['coordinates'][0],'lat':p['coordinates'][1],'mode':'train'})
        for (a,_),(b,_) in zip(calls,calls[1:]):
            key='lrtj-'+direction+'-'+a+'-'+b
            if key not in result['paths']:
                points=[geo['stations'][c]['coordinates'] for c in [a,b]];curve=graphs[direction].leg(*points)
                if not curve or cumulative_distances(curve)[-1]>3*cumulative_distances(points)[-1]:raise ValueError('Missing/implausible native LRT Jakarta path: '+key)
                result['paths'][key]={'coordinates':curve,'distances':cumulative_distances(curve),'quality':'track'}
            legs.append(key)
        pattern={'mode':'light_rail','operator':'LRT Jakarta','line':'LRT Jakarta South Line','route_id':'S',
            'color':'#F26324','direction':'Southbound' if direction=='south' else 'Northbound',
            'origin':NAMES[calls[0][0]],'destination':NAMES[calls[-1][0]],
            'stops':[[ids[direction,c],t-start,t-start] for c,t in calls],'legs':legs}
        key=hashlib.sha256(json.dumps(pattern,sort_keys=True).encode()).hexdigest()[:20];result['patterns'][key]=pattern
        for day,rows in result['days'].items(): rows.append([key,trip['number'],start])
        result['train_numbers'][trip['number']]=trip['number']
    for rows in result['days'].values():rows.sort(key=lambda r:(r[2],r[1]))
    result['metadata']={**source['metadata'],'start_date':'2025-12-15','end_date':'2025-12-21','timezone':'Asia/Jakarta',
        'source_date':'2026-09-19','sources':[{'source_url':PDF_URL,'source_date':'2026-09-19','published':'2026-09-18','sha256':PDF_SHA256}],
        'license_url':'https://www.lrtjakarta.co.id/',
        'attribution':'Timetable: PT LRT Jakarta, official publication valid from 19 September 2026; operator rights retained. PDF table conversion and replay preparation by SunTrain. Railway geometry © OpenStreetMap contributors, ODbL 1.0.',
        'replay_note':NOTE,'omitted_trips':{},'unresolved_geometry_patterns':{},'unresolved_geometry_trips':{},
        'geometry_source':'© OpenStreetMap contributors; native directional LRT Jakarta railway ways',
        'geometry_source_url':'https://www.openstreetmap.org/copyright','geometry_license':'ODbL 1.0',
        'geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/','geometry_sha256':GEOMETRY_SHA256,
        'date_mapping':'Official 19 September 2026 timetable overlaid on matching KRL weekdays; not December 2025 LRT Jakarta history'}
    return compact_reference(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--extract-pdf',action='store_true')
    parser.add_argument('--prepare-geometry',action='store_true')
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/jakarta/lrt-jakarta');args=parser.parse_args()
    if args.extract_pdf:extract_pdf(args.cache)
    elif args.prepare_geometry:prepare_geometry(args.cache)
    else:print({d:len(v) for d,v in build()['days'].items()})
