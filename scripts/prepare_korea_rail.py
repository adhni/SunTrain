"""Prepare dated KORAIL and SR national railway publications."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
from decimal import Decimal
from functools import lru_cache
import gzip
import io
import json
from pathlib import Path
import posixpath
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
CACHE=ROOT/'.cache/korea-rail'
OUTPUT=ROOT/'data/reference/south_korea/2025-10-20.json.gz'
URLS={'ktx.xlsx':'https://www.korail.com/file/cubedata/COMMON/jfile/202504/30/2025043019686017900290.xlsx',
      'intercity.xlsx':'https://www.korail.com/file/cubedata/COMMON/jfile/202503/28/20250328195da7b30dc650.xlsx'}
NOTE=('KORAIL and SR passenger railway timetable snapshots shown on a 20–26 October 2025 reference week; exact historical operation is not confirmed. KTX/SRT publications effective 1 June; conventional publication effective 14 April; ITX-Cheongchun listed effective 1 May. '
      'Published station times and weekday restrictions retained. Published ITX-Cheongchun dwell is retained; other tables supply one timestamp per station. '
      'Cross-corridor timetable sections are combined by train identity. Unsupported railway sections remain gaps. '
      'Seoul urban rail has its own view. Tourist specials and individual passenger loads are not included; no live tracking.')
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
LABELS={'KTX':('KTX','1474AE'),'KTX-산천':('KTX-Sancheon','2267A4'),'KTX-이음':('KTX-Eum','6955A5'),
        'KTX-청룡':('KTX-Cheongryong','217E9B'),'무궁화':('Mugunghwa','C66B32'),'ITX-마음':('ITX-Maum','B64B52'),
        'ITX-새마을':('ITX-Saemaeul','318C81'),'새마을':('Saemaeul','498C70'),'누리로':('Nuriro','5277A8'),'ITX-청춘':('ITX-Cheongchun','3F9C45'),'SRT':('SRT','5B2455')}


def norm(value):return re.sub(r'\s+','',str(value or '')).replace('臺','台')


def workbook(filename):
    """Read cell values and time formats directly; preserve 24:00 as 86400."""
    with ZipFile(filename) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(t.text or '' for t in si.findall('.//m:t',NS)) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        styles=ET.fromstring(z.read('xl/styles.xml'))
        formats={int(n.attrib['numFmtId']):n.attrib['formatCode'] for n in styles.findall('m:numFmts/m:numFmt',NS)}
        timed=[int(n.attrib.get('numFmtId',0)) in {14,15,16,17,18,19,20,21,22,45,46,47} or 'h' in formats.get(int(n.attrib.get('numFmtId',0)),'').lower()
               for n in styles.findall('m:cellXfs/m:xf',NS)]
        rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result={}
        for s in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',NS):
            target=rels[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            target=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
            cells={};maxrow=maxcol=0
            for c in ET.fromstring(z.read(target)).findall('.//m:sheetData/m:row/m:c',NS):
                v=c.find('m:v',NS);typ=c.attrib.get('t')
                if v is None:
                    t=c.find('m:is',NS)
                    if t is None:continue
                    value=''.join(t.itertext())
                elif typ=='s':value=shared[int(v.text)]
                elif typ in {'str','e'}:value=v.text
                elif v.text is not None:
                    value=float(v.text)
                    if timed[int(c.attrib.get('s',0))]:value={'time':int((Decimal(v.text)*86400).to_integral_value())}
                    elif value.is_integer():value=int(value)
                else:continue
                m=re.fullmatch(r'([A-Z]+)(\d+)',c.attrib['r']);column=0
                for letter in m[1]:column=column*26+ord(letter)-64
                row=int(m[2]);cells[row-1,column-1]=value;maxrow=max(maxrow,row);maxcol=max(maxcol,column)
            result[s.attrib['name']]=[[cells.get((r,c)) for c in range(maxcol)] for r in range(maxrow)]
        return result


def running_days(value,*,blank_daily=False):
    text=norm(value).replace(',','')
    if isinstance(value,dict) and value.get('time')==0:text=''
    if text=='매일' or (not text and blank_daily):return tuple(range(7))
    if text and re.fullmatch('[월화수목금토일]+',text):return tuple(i for i,d in enumerate('월화수목금토일') if d in text)
    raise ValueError('Unrecognised running days: '+text)


def time_value(value):
    if isinstance(value,dict) and 0<value.get('time',0)<172800:return value['time']
    return None


def station_name(name):
    text=norm(name).removesuffix('출발').removesuffix('도착').removesuffix('역')
    if text=='판교(경기)':return '판교경기'
    text=re.sub('[^가-힣A-Za-z0-9]','',text).removesuffix('출발').removesuffix('도착')
    return {'진부오대산':'진부','평내호':'평내호평','평택지제':'지제'}.get(text,text)


def parse_sources(cache):
    records=[];audit=Counter()
    for filename in ['ktx.xlsx','intercity.xlsx']:
        for title,a in workbook(cache/filename).items():
            if '총괄' in title or title=='보는방법':continue
            for i,row in enumerate(a):
                for j,label in enumerate(row):
                    if norm(label)!='열차번호':continue
                    if filename=='ktx.xlsx':
                        end=next((k for k in range(j+2,len(row)) if norm(row[k]).startswith('비고')),None)
                        if end is None:raise ValueError('Missing KTX running-day column: '+title)
                        for r in a[i+3:]:
                            number=r[j]
                            if not isinstance(number,int) or not 0<number<100000:continue
                            kind=norm(r[j+1]).replace('_','-');flag=r[end]
                            calls=[(str(row[k]),time_value(r[k])) for k in range(j+2,end) if time_value(r[k]) is not None]
                            records.append({'number':str(number),'kind':kind,'flag':flag,'blank_daily':False,'calls':calls,'sheet':title})
                    else:
                        end=next((k for k in range(i+1,len(a)) if norm(a[k][j])=='비고'),None)
                        if end is None:raise ValueError('Missing conventional notes row: '+title)
                        for k in range(j+1,len(row)):
                            if not isinstance(row[k],int):break
                            kind=norm(a[i-1][k]);calls=[]
                            if i>=5 and time_value(a[i-2][k]) is not None:calls.append((str(a[i-5][k]),time_value(a[i-2][k])))
                            calls += [(str(a[r][j]),time_value(a[r][k])) for r in range(i+1,end) if a[r][j] and time_value(a[r][k]) is not None]
                            if end+4<len(a) and time_value(a[end+4][k]) is not None:calls.append((str(a[end+1][k]),time_value(a[end+4][k])))
                            records.append({'number':str(row[k]),'kind':kind,'flag':a[end][k],'blank_daily':True,'calls':calls,'sheet':title})
    groups=defaultdict(list)
    for r in records:
        if r['kind'] not in LABELS:audit['unsupported_category:'+r['kind']]+=1;continue
        try:days=running_days(r['flag'],blank_daily=r['blank_daily'])
        except ValueError as e:audit[str(e)]+=1;continue
        offset=0;previous=None;calls=[]
        for name,t in r['calls']:
            if previous is not None and t+offset<previous:
                if previous%86400>=20*3600 and t<=4*3600 and offset==0:offset=86400
                else:audit['backwards_piece']+=1;calls=[];break
            previous=t+offset;calls.append((station_name(name),name,previous))
        if len(calls)<2:audit['fewer_than_two_calls']+=1;continue
        groups[r['kind'],r['number'],days].append((r['sheet'],calls))
    result=[]
    for (kind,number,days),pieces in sorted(groups.items()):
        calls=sorted({(t,name,display) for _,rows in pieces for name,display,t in rows})
        # Identical duplicate tables are harmless; conflicting timestamps at a
        # single station are retained as separate published calls, never averaged.
        unique={}
        for t,name,display in calls:unique.setdefault((t,name),display)
        calls=[(name,display,t) for (t,name),display in sorted(unique.items())]
        result.append({'kind':kind,'number':number,'days':days,'calls':calls,'corridors':sorted({s for s,_ in pieces})})
    return result,dict(audit)


def itx_clock(value):
    # Unlike conventional zero placeholders, ITX uses blank strings for passing
    # arrivals. A numeric 00:00 is therefore a genuine clock here.
    if isinstance(value,dict) and 0<=value.get('time',-1)<172800:return value['time']
    return None


def parse_cheongchun(sheets):
    """Only marked arrivals are stops; the paired row also contains passing times."""
    trips=[]
    for title,a in sheets.items():
        if title.endswith('(평)'):days=tuple(range(5))
        elif title.endswith('(휴)'):days=(5,6)
        else:raise ValueError('Unknown ITX-Cheongchun calendar: '+title)
        if norm(a[2][0])!='열차번호':raise ValueError('Changed ITX-Cheongchun layout')
        for k,number in enumerate(a[2]):
            if not re.fullmatch(r'S\d{4}',str(number or '')):continue
            origin,destination=station_name(a[0][k]),station_name(a[1][k])
            calls=[];departures=[];offset=0
            for i in range(3,len(a)-1,2):
                if not norm(a[i][0]):continue
                name=station_name(a[i][0]);arrival=itx_clock(a[i][k]);departure=itx_clock(a[i+1][k])
                if arrival is None:
                    if name!=origin:continue  # A departure-row-only timestamp is a passing time.
                    arrival=departure
                if arrival is None:raise ValueError('Missing ITX origin departure: '+number)
                departure=arrival if departure is None else departure
                if departures and arrival+offset<departures[-1]:
                    if departures[-1]%86400>=20*3600 and arrival<=4*3600 and offset==0:offset=86400
                    else:raise ValueError('Backwards ITX calls: '+number)
                arrival+=offset
                if departure+offset<arrival:
                    if arrival%86400>=20*3600 and departure<=4*3600 and offset==0:offset=86400
                    else:raise ValueError('Backwards ITX dwell: '+number)
                departure+=offset
                calls.append((name,str(a[i][0]).strip(),arrival));departures.append(departure)
            if len(calls)<2 or calls[0][0]!=origin or calls[-1][0]!=destination:raise ValueError('Incomplete ITX journey: '+number)
            trips.append({'kind':'ITX-청춘','number':number,'days':days,'calls':calls,'departures':departures,'corridors':[title]})
    return trips


def pdf_clock(text):
    if not re.fullmatch(r'\d{2}:\d{2}',text):raise ValueError('Invalid SRT clock: '+text)
    h,m=map(int,text.split(':'))
    if h>=24 or m>=60:raise ValueError('Invalid SRT clock: '+text)
    return h*3600+m*60


def parse_srt(filename):
    """Read vector PDF clock positions against the published station columns."""
    import pdfplumber  # Preparation-only, using the existing PDF tools.
    trips=[]
    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            clocks=page.search(r'\d{2}:\d{2}',x_tolerance=.5)
            for table in page.find_tables():
                headers=[norm(v) for v in table.extract()[0]]
                cells=table.rows[0].cells
                if headers[0]!='열차번호' or not all(cells):raise ValueError('Changed SRT table header')
                centers=[(c[0]+c[2])/2 for c in cells]
                for row in table.rows[1:]:
                    bounds=[c for c in row.cells if c];y0=min(c[1] for c in bounds);y1=max(c[3] for c in bounds)
                    number=norm(page.crop((cells[0][0],y0,cells[0][2],y1)).extract_text())
                    if not re.fullmatch(r'\d{3}',number):raise ValueError('Invalid SRT train number: '+number)
                    times={}
                    for m in clocks:
                        x=(m['x0']+m['x1'])/2;y=(m['top']+m['bottom'])/2
                        if not table.bbox[0]<x<table.bbox[2] or not y0<y<y1:continue
                        k=min(range(len(centers)),key=lambda k:abs(centers[k]-x))
                        if k in times or k==0 or headers[k]=='운행일':raise ValueError('Ambiguous SRT station clock: '+number)
                        times[k]=pdf_clock(m['text'])
                    days=tuple(range(7))
                    if headers[-1]=='운행일':
                        flag=page.crop((cells[-1][0],y0,cells[-1][2],y1)).extract_text()
                        days=running_days(flag)
                    calls=[];offset=0;previous=None
                    for k,t in sorted(times.items()):
                        if previous is not None and t+offset<previous:
                            if previous>=20*3600 and t<=4*3600 and offset==0:offset=86400
                            else:raise ValueError('Backwards SRT calls: '+number)
                        previous=t+offset;name=station_name(headers[k]);calls.append((name,headers[k],previous))
                    if len(calls)<2:raise ValueError('Incomplete SRT journey: '+number)
                    trips.append({'kind':'SRT','number':number,'days':days,'calls':calls,'corridors':[headers[1]+'–'+headers[-2 if headers[-1]=='운행일' else -1]]})
    if len(trips)!=132:raise ValueError('Changed SRT publication scope: '+str(len(trips)))
    return trips


def station_candidates(geo):
    index=defaultdict(list)
    for s in geo['stations']:
        tags=s['tags'];names=[]
        for key in ['name','name:ko','alt_name','official_name']:
            for name in tags.get(key,'').split(';'):
                if name:names.extend([name,re.sub(r'\([^)]*\)','',name)])
        for name in set(map(station_name,names)):
            if name:index[name].append(s)
    def resolve(name):
        key='판교' if name=='판교경기' else name
        values=index.get(key,[])
        if key=='양원':values=[v for v in values if v['coordinate'][0]>128]  # Yeongdong Line, not Seoul's namesake
        if key=='판교':values=[v for v in values if (v['coordinate'][1]>37)==(name=='판교경기')]
        # Prefer named stations over stop-position nodes and subway/rail
        # interchanges; no invented station coordinate is introduced.
        values=sorted(values,key=lambda v:(station_name(v['tags'].get('name',''))!=key,v['tags'].get('railway') not in {'station','halt'},v['tags'].get('train')!='yes',v['id']))
        return values[0] if values else None
    return resolve


def prepare(cache=CACHE,output=OUTPUT):
    pins=json.loads((ROOT/'data/reference/south_korea/sources.json').read_text())
    for pin in pins:
        if file_hash(cache/pin['file'])!=pin['sha256']:raise ValueError('Changed national rail source: '+pin['file'])
    trips,audit=parse_sources(cache)
    trips+=parse_cheongchun(workbook(cache/'cheongchun.xlsx'))
    trips+=parse_srt(cache/'srt-timetable')
    with gzip.open(cache/'tracks.json.gz','rt') as f:geo=json.load(f)
    find_station=station_candidates(geo);missing=Counter();selected=[]
    for t in trips:
        absent=[name for name,_,_ in t['calls'] if find_station(name) is None]
        if absent:missing.update(absent);continue
        selected.append(t)
    print('Parsed',len(trips),'selected',len(selected),'missing station names',dict(missing),'audit',audit,flush=True)
    tables={'agency.txt':[{'agency_id':'korail','agency_name':'KORAIL','agency_url':'https://www.korail.com/','agency_timezone':'Asia/Seoul'},{'agency_id':'sr','agency_name':'SR','agency_url':'https://etk.srail.kr/','agency_timezone':'Asia/Seoul'}],
        'stops.txt':[],'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar.txt':[]}
    stops=set();routes=set();numbers={}
    for idx,t in enumerate(selected):
        label,color=LABELS[t['kind']];rid=t['kind'];trip='kr-'+str(idx);numbers[trip]=t['number']
        if rid not in routes:
            routes.add(rid);tables['routes.txt'].append({'route_id':rid,'agency_id':'sr' if rid=='SRT' else 'korail','route_type':'2','route_short_name':label,'route_long_name':label,'route_color':color})
        tables['trips.txt'].append({'trip_id':trip,'service_id':trip,'route_id':rid})
        tables['calendar.txt'].append({'service_id':trip,'start_date':'20251019','end_date':'20251027',**{d:int(i in t['days']) for i,d in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])}})
        for i,(name,display,clock) in enumerate(t['calls']):
            if name not in stops:
                stops.add(name);s=find_station(name);x,y=s['coordinate'];tables['stops.txt'].append({'stop_id':name,'stop_name':display,'stop_lon':x,'stop_lat':y})
            value=f'{clock//3600:02d}:{clock//60%60:02d}:{clock%60:02d}'
            dep=t.get('departures',[c[2] for c in t['calls']])[i]
            departure=f'{dep//3600:02d}:{dep//60%60:02d}:{dep%60:02d}'
            tables['stop_times.txt'].append({'trip_id':trip,'stop_id':name,'stop_sequence':i+1,'arrival_time':value,'departure_time':departure})
    with ZipFile(cache/'gtfs.zip','w') as z:
        for name,rows in tables.items():
            s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);z.writestr(ZipInfo(name,date_time=(2025,6,1,0,0,0)),s.getvalue(),compress_type=ZIP_DEFLATED)
    graphs={fast:FranceRailGraph(geo['ways'],fast=fast) for fast in [False,True]}
    @lru_cache(maxsize=None)
    def leg(fast,a,b):
        curve=graphs[fast].leg(list(a),list(b))
        return curve if curve and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
    def resolve(route,trip,sequence,coordinates):return [leg(route['route_id'].startswith('KTX') or route['route_id']=='SRT',tuple(a),tuple(b)) for a,b in zip(coordinates,coordinates[1:])]
    source={'first':'2025-10-20','last':'2025-10-26','timezone':'Asia/Seoul','url':'local-conversion/gtfs.zip','sha256':file_hash(cache/'gtfs.zip'),
        'captured':'2026-10-23','published':'2025-06-01','calendar_validity':True,'assign_by_start':['train','high_speed_rail'],'geometry_quality':'track',
        'source':'KORAIL and SR dated passenger railway timetables','source_url':'https://www.korail.com/ticket/reserve/train-timeTable',
        'license':'Published KORAIL and SR timetable facts; source attribution retained','license_url':'https://info.korail.com/info/contents.do?key=924',
        'attribution':'Korea Railroad Corporation (KORAIL) and SR, published timetable data. Railway geography © OpenStreetMap contributors, ODbL 1.0. SunTrain conversion and inferred track matching.',
        'note':NOTE,'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],
        'geometry_license':'ODbL 1.0','geometry_license_url':geo['metadata']['license_url'],'geometry_source_date':geo['metadata']['source_date'],'geometry_sha256':file_hash(cache/'tracks.json.gz')}
    prepare_rail('south_korea',source,cache,output,lambda r,a:r['route_id'] in routes,
        lambda r,t:{'mode':'high_speed_rail' if r['route_id'].startswith('KTX') or r['route_id']=='SRT' else 'train','operator':'SR' if r['route_id']=='SRT' else 'KORAIL','line':r['route_short_name'],'route_id':r['route_id'],'direction':'Not specified'},geometry_resolver=resolve)
    with gzip.open(output,'rt') as f:r=json.load(f)
    r['train_numbers']=numbers;r['metadata']['sources']=[{'source_url':s['url'],'sha256':s['sha256'],'source_date':s['date']} for s in pins]
    r['metadata']['source_audit']=audit;r['metadata']['unlocated_station_trip_exclusions']=dict(missing)
    save_reference(r,output);print('Days',{d:len(v) for d,v in r['days'].items()},'bytes',output.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=OUTPUT);a=p.parse_args();prepare(a.cache,a.output)
