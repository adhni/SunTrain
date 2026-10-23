"""Prepare dated KORAIL suburban railway matrices for the Seoul reference week."""
from __future__ import annotations
import csv
from collections import Counter,defaultdict
from functools import lru_cache
import gzip
import io
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_korea_rail import workbook,norm,itx_clock,station_name
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.compact_transit import save_reference
from dashboard.replay import cumulative_distances
CACHE=ROOT/'.cache/seoul-suburban'
LINES={'gyeongui':('Gyeongui–Jungang','경의·중앙선','77C4A3'),
       'suin-bundang':('Suin–Bundang','수인분당선','F5A200'),
       'gyeongchun':('Gyeongchun','경춘선','0C8E72')}
ALIASES={'능길':'신길온천','신인천':'인천','신수원':'수원','평내호':'평내호평','항공대':'한국항공대','디엠시':'디지털미디어시티',
         '효창공':'효창공원앞','홍대입':'홍대입구','1양정':'양정','1양원':'양원',
         '수원시':'수원시청','매탄권':'매탄권선','신길온':'신길온천','남동인':'남동인더스파크','인천논':'인천논현','소래포':'소래포구',
         '강남구':'강남구청','로데오':'압구정로데오','대모산':'대모산입구','서울역':'서울'}
NOTE=('KORAIL Gyeongui–Jungang (including the Seoul branch), Suin–Bundang and Gyeongchun suburban trains from official timetables effective 30 December 2025, '
      'shown on the 5–11 January 2026 reference week. Published station calls, dwell, short workings and passing/express patterns retained. '
      'KORAIL working station names are matched to the station inventory. Disconnected railway sections remain gaps. '
      'ITX-Cheongchun stays in the South Korea national view. No live tracking or individual passenger counts.')


def name(value):
    key=station_name(value)
    return ALIASES.get(key,key)


def matrix_trips(sheets,line,audit=None):
    result=[]
    for title,a in sheets.items():
        if '(평)' in title or '평일' in title:days=tuple(range(5))
        elif '(휴)' in title or '휴일' in title:days=(5,6)
        else:raise ValueError('Unknown suburban service calendar: '+title)
        headers=[(i,j) for i,row in enumerate(a) for j,v in enumerate(row) if norm(v)=='열차번호']
        if not headers:raise ValueError('Missing suburban train header: '+title)
        for i,j in headers:
            end=min([k for r,k in headers if r==i and k>j]+[len(a[i])])
            for k in range(j+1,end):
                number=norm(a[i][k])
                if not number:continue
                if not re.fullmatch(r'K\d{4,5}',number):raise ValueError('Unknown suburban train number: '+number)
                try:
                    origin,destination=name(a[i-2][k]),name(a[i-1][k]);calls=[];offset=0
                    for r in range(i+1,len(a),2):
                        label=a[r][j]
                        if not norm(label):continue
                        station=name(label);arrival=itx_clock(a[r][k]);departure=itx_clock(a[r+1][k]) if r+1<len(a) else None
                        if arrival is None:
                            if station!=origin:continue  # Passing time in the paired row.
                            arrival=departure
                        if arrival is None:raise ValueError('Missing suburban origin clock: '+number)
                        departure=arrival if departure is None else departure
                        previous=calls[-1][3] if calls else None
                        if previous is not None and arrival+offset<previous:
                            if previous%86400>=20*3600 and arrival<=4*3600 and offset==0:offset=86400
                            else:raise ValueError('Backwards suburban calls: '+number)
                        arrival+=offset
                        if departure+offset<arrival:
                            if arrival%86400>=20*3600 and departure<=4*3600 and offset==0:offset=86400
                            else:raise ValueError('Backwards suburban dwell: '+number)
                        departure+=offset;calls.append((station,str(label).strip(),arrival,departure))
                    if len(calls)<2 or calls[0][0]!=origin or calls[-1][0]!=destination:raise ValueError('Incomplete suburban journey: '+number)
                    result.append({'line':line,'number':number,'days':days,'calls':calls,'sheet':title})
                except ValueError as error:
                    if audit is None:raise
                    audit[line+':'+str(error).split(':')[0]]+=1
    return result


def prepare(cache=CACHE,coordinate_cache=ROOT/'.cache/seoul',output=None):
    output=output or cache/'suburban.json.gz'
    pins=json.loads((ROOT/'data/reference/seoul/suburban-sources.json').read_text())
    for pin in pins:
        if file_hash(cache/pin['file'])!=pin['sha256']:raise ValueError('Changed suburban source: '+pin['file'])
    inventory=defaultdict(list)
    for s in csv.DictReader((coordinate_cache/'stations.csv').open(encoding='utf-8-sig')):inventory[name(s['station_name'])].append(s)
    def locate(station,line):
        candidates=inventory.get(station,[])
        preferred=[s for s in candidates if s['line_key']==LINES[line][1]]
        candidates=preferred or candidates
        return sorted(candidates,key=lambda s:s['id'])[0] if candidates else None
    audit=Counter()
    trips=[t for line in LINES for t in matrix_trips(workbook(cache/(line+'.xlsx')),line,audit)]
    missing=Counter();selected=[]
    for t in trips:
        absent=[n for n,_,_,_ in t['calls'] if not locate(n,t['line'])]
        if absent:missing.update(absent);continue
        selected.append(t)
    print('Suburban',len(trips),'selected',len(selected),'missing stations',dict(missing),'audit',dict(audit),flush=True)
    tables={'agency.txt':[{'agency_id':'korail','agency_name':'KORAIL','agency_url':'https://www.korail.com/','agency_timezone':'Asia/Seoul'}],
            'stops.txt':[],'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar.txt':[]}
    for line,(label,_,color) in LINES.items():tables['routes.txt'].append({'route_id':line,'agency_id':'korail','route_type':'2','route_short_name':label,'route_long_name':label,'route_color':color})
    stops=set();numbers={}
    for idx,t in enumerate(selected):
        trip='suburban-'+str(idx);numbers[trip]=t['number']
        tables['trips.txt'].append({'trip_id':trip,'route_id':t['line'],'service_id':trip})
        tables['calendar.txt'].append({'service_id':trip,'start_date':'20260104','end_date':'20260112',**{d:int(i in t['days']) for i,d in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])}})
        for i,(station,display,a,b) in enumerate(t['calls']):
            sid=t['line']+':'+station
            if sid not in stops:
                stops.add(sid);s=locate(station,t['line']);tables['stops.txt'].append({'stop_id':sid,'stop_name':station,'stop_lon':s['lon'],'stop_lat':s['lat']})
            fmt=lambda v:f'{v//3600:02d}:{v//60%60:02d}:{v%60:02d}'
            tables['stop_times.txt'].append({'trip_id':trip,'stop_id':sid,'stop_sequence':i+1,'arrival_time':fmt(a),'departure_time':fmt(b)})
    cache.mkdir(parents=True,exist_ok=True)
    with ZipFile(cache/'gtfs.zip','w') as z:
        for filename,rows in tables.items():
            s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);z.writestr(ZipInfo(filename,date_time=(2025,12,30,0,0,0)),s.getvalue(),compress_type=ZIP_DEFLATED)
    with gzip.open(coordinate_cache/'tracks.json.gz','rt') as f:geo=json.load(f)
    graph=FranceRailGraph(geo['ways'])
    @lru_cache(maxsize=None)
    def leg(a,b):
        curve=graph.leg(list(a),list(b))
        return curve if curve and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
    def resolve(route,trip,sequence,coordinates):return [leg(tuple(a),tuple(b)) for a,b in zip(coordinates,coordinates[1:])]
    source={'first':'2026-01-05','last':'2026-01-11','timezone':'Asia/Seoul','url':'local-conversion/gtfs.zip','sha256':file_hash(cache/'gtfs.zip'),
        'captured':'2026-10-23','published':'2025-12-30','calendar_validity':True,'assign_by_start':['commuter_rail'],'geometry_quality':'track',
        'source':'KORAIL December 2025 suburban railway timetables','source_url':'https://www.korail.com/ticket/reserve/train-timeTable',
        'license':'Published KORAIL timetable facts; public-work reuse policy','license_url':'https://info.korail.com/info/contents.do?key=924',
        'attribution':'Korea Railroad Corporation (KORAIL), published timetable facts. Station inventory: official Korean open data preserved by minseok852/subway-etl, KOGL Type 1. Railway geography © OpenStreetMap contributors, ODbL 1.0.',
        'note':NOTE,'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],
        'geometry_license':'ODbL 1.0','geometry_license_url':geo['metadata']['license_url'],'geometry_source_date':geo['metadata']['source_date'],'geometry_sha256':file_hash(coordinate_cache/'tracks.json.gz')}
    prepare_rail('seoul',source,cache,output,lambda r,a:r['route_id'] in LINES,
                 lambda r,t:{'mode':'commuter_rail','operator':'KORAIL','line':r['route_short_name'],'route_id':r['route_id'],'direction':'Not specified'},geometry_resolver=resolve)
    with gzip.open(output,'rt') as f:reference=json.load(f)
    reference['metadata']['source_audit']=dict(audit)
    reference['train_numbers']=numbers;reference['metadata']['sources']=[{'source_url':s['url'],'sha256':s['sha256'],'source_date':s['date']} for s in pins]
    reference['metadata']['unlocated_station_trip_exclusions']=dict(missing)
    save_reference(reference,output)
    return reference

if __name__=='__main__':prepare()
