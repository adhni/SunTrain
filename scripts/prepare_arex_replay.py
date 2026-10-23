"""Convert AREX's linked train timetable into a labelled weekday overlay."""
from __future__ import annotations
import csv,gzip,io,json,re,sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_korea_rail import workbook,norm
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.compact_transit import save_reference
from dashboard.replay import cumulative_distances
CACHE=ROOT/'.cache/arex'
SOURCE_URL='https://www.airportrailroad.com/static/file/%EC%97%B4%EC%B0%A8%EC%8B%9C%EA%B0%81%ED%91%9C_261023.xlsx'
NOTE='AREX express and all-stop trains: October 2026 published timetable snapshot, matched by weekday to the January reference week. This layer does not reconstruct January airport services.'


def seconds(value):
    if value in {None,'','---'}:return None
    if not isinstance(value,str) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}',value):raise ValueError('Invalid AREX clock: '+str(value))
    h,m,s=map(int,value.split(':'))
    if h>=48 or m>=60 or s>=60:raise ValueError('Invalid AREX clock: '+value)
    return h*3600+m*60+s


def parse(sheets):
    trips=[]
    for title,a in sheets.items():
        days=tuple(range(5)) if title=='평일' else (5,6) if title=='휴일' else None
        if days is None:raise ValueError('Unknown AREX calendar: '+title)
        headers=[i for i,r in enumerate(a) if norm(r[0])=='열차번호']
        for i in headers:
            end=next(k for k in range(i+5,len(a)) if norm(a[k][0])=='비고')
            for k,number in enumerate(a[i][1:],1):
                if not norm(number):continue
                if not re.fullmatch(r'A\d{4}',number):raise ValueError('Unknown AREX train number')
                origin,destination=norm(a[i+1][k]),norm(a[i+3][k]);calls=[];offset=0
                for j in range(i+5,end,2):
                    name=norm(a[j][0]);arrival=seconds(a[j][k]);departure=seconds(a[j+1][k])
                    if name=='수색직결선':continue  # Working control point, not a passenger station.
                    if arrival is None:
                        if name!=origin:continue  # Passing clocks do not create stops.
                        arrival=departure
                    if arrival is None:raise ValueError('Missing AREX origin clock')
                    departure=arrival if departure is None else departure
                    if not calls and arrival<3*3600:offset=86400
                    if calls and arrival+offset<calls[-1][2]:
                        if calls[-1][2]%86400>=20*3600 and arrival<=4*3600 and offset==0:offset=86400
                        else:raise ValueError('Backwards AREX call: '+number)
                    arrival+=offset
                    if departure+offset<arrival:
                        if arrival%86400>=20*3600 and departure<=4*3600 and offset==0:offset=86400
                        else:raise ValueError('Backwards AREX dwell: '+number)
                    departure+=offset;calls.append((name,arrival,departure))
                if len(calls)<2 or calls[0][0]!=origin or calls[-1][0]!=destination:raise ValueError('Incomplete AREX journey: '+number)
                if calls[0][2]%86400!=seconds(a[i+2][k])%86400 or calls[-1][1]%86400!=seconds(a[i+4][k])%86400:raise ValueError('AREX endpoint clocks disagree: '+number)
                express=number.startswith('A1')
                if express and {c[0] for c in calls}!={'서울','인천공항1터미널','인천공항2터미널'}:raise ValueError('Changed express pattern')
                trips.append({'number':number,'route':'express' if express else 'normal','days':days,'calls':calls})
    return trips


def prepare(cache=CACHE,coordinate_cache=ROOT/'.cache/seoul'):
    pin=json.loads((ROOT/'data/reference/seoul/arex-source.json').read_text())
    if file_hash(cache/pin['file'])!=pin['sha256']:raise ValueError('Changed AREX publication')
    trips=parse(workbook(cache/pin['file']));print('AREX templates',len(trips),Counter((t['route'],str(t['days'])) for t in trips),flush=True)
    stations={norm(s['station_name']):s for s in csv.DictReader((coordinate_cache/'stations.csv').open(encoding='utf-8-sig')) if s['line_key']=='인천국제공항선'}
    tables={'agency.txt':[{'agency_id':'arex','agency_name':'AREX','agency_url':'https://www.airportrailroad.com/','agency_timezone':'Asia/Seoul'}],
            'stops.txt':[],'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar.txt':[]}
    for rid,label,color in [('express','AREX express','F5A200'),('normal','AREX all-stop','0090D2')]:tables['routes.txt'].append({'route_id':rid,'agency_id':'arex','route_type':'2','route_short_name':label,'route_long_name':label,'route_color':color})
    used=set();numbers={}
    for idx,t in enumerate(trips):
        trip='arex-'+str(idx);numbers[trip]=t['number'];tables['trips.txt'].append({'trip_id':trip,'route_id':t['route'],'service_id':trip})
        tables['calendar.txt'].append({'service_id':trip,'start_date':'20260104','end_date':'20260112',**{d:int(i in t['days']) for i,d in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])}})
        for i,(n,a,b) in enumerate(t['calls']):
            s=stations[n]  # Missing calls fail preparation; never skip stations.
            if n not in used:used.add(n);tables['stops.txt'].append({'stop_id':n,'stop_name':n,'stop_lon':s['lon'],'stop_lat':s['lat']})
            fmt=lambda v:f'{v//3600:02d}:{v//60%60:02d}:{v%60:02d}'
            tables['stop_times.txt'].append({'trip_id':trip,'stop_id':n,'stop_sequence':i+1,'arrival_time':fmt(a),'departure_time':fmt(b)})
    with ZipFile(cache/'gtfs.zip','w') as z:
        for filename,rows in tables.items():
            f=io.StringIO();w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);z.writestr(ZipInfo(filename,date_time=(2026,10,23,0,0,0)),f.getvalue(),compress_type=ZIP_DEFLATED)
    geo=json.load(gzip.open(coordinate_cache/'tracks.json.gz','rt'));graph=FranceRailGraph(geo['ways'])
    @lru_cache(maxsize=None)
    def leg(a,b):
        curve=graph.leg(list(a),list(b))
        return curve if curve and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
    def resolve(route,trip,sequence,coords):return [leg(tuple(a),tuple(b)) for a,b in zip(coords,coords[1:])]
    source={'first':'2026-01-05','last':'2026-01-11','timezone':'Asia/Seoul','url':'local-conversion/gtfs.zip','sha256':file_hash(cache/'gtfs.zip'),
        'captured':'2026-10-23','published':'2026-10-23','calendar_validity':True,'assign_by_start':['commuter_rail'],'geometry_quality':'track',
        'source':'AREX October 2026 timetable snapshot; weekday overlay','source_url':'https://www.airportrailroad.com/train/normal/info/010',
        'license':'Published AREX timetable facts; source attribution retained','license_url':'https://www.airportrailroad.com/train/normal/info/010',
        'attribution':'Airport Railroad Co., Ltd. (AREX), published timetable facts. Station inventory: official Korean open data preserved by minseok852/subway-etl, KOGL Type 1. Railway geography © OpenStreetMap contributors, ODbL 1.0.',
        'note':NOTE,'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],'geometry_license':'ODbL 1.0','geometry_license_url':geo['metadata']['license_url'],'geometry_source_date':geo['metadata']['source_date'],'geometry_sha256':file_hash(coordinate_cache/'tracks.json.gz')}
    output=cache/'arex.json.gz'
    prepare_rail('seoul',source,cache,output,lambda r,a:True,lambda r,t:{'mode':'commuter_rail','operator':'AREX','line':r['route_short_name'],'route_id':r['route_id'],'direction':'Not specified'},geometry_resolver=resolve)
    reference=json.load(gzip.open(output,'rt'));reference['train_numbers']=numbers
    reference['metadata']['sources']=[{'source_url':SOURCE_URL,'sha256':pin['sha256'],'source_date':'2026-10-23','note':NOTE}]
    # Use the captured Friday–Thursday source week, matching each displayed weekday.
    reference['metadata']['display_date_mapping']={'2026-01-05':'2026-10-26','2026-01-06':'2026-10-27','2026-01-07':'2026-10-28','2026-01-08':'2026-10-29','2026-01-09':'2026-10-23','2026-01-10':'2026-10-24','2026-01-11':'2026-10-25'}
    save_reference(reference,output);return reference

if __name__=='__main__':prepare()
