"""Convert the official Seoul bulk train-call CSV into shared historical replay."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import csv
from functools import lru_cache
import gzip
import io
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.compact_transit import save_reference,merge_references
CACHE=ROOT/'.cache/seoul'
OUTPUT=ROOT/'data/reference/seoul/2026-01-05.json.gz'
COLORS={'1':'0052A4','2':'00A84D','3':'EF7C1C','4':'00A5DE','5':'996CAC','6':'CD7C2F','7':'747F00','8':'E6186C','9':'BDB092'}
NOTE=('Seoul metropolitan subway Lines 1–9 from the official 30 September 2025 bulk timetable, applied to a 5–11 January 2026 reference week; exact source effective dates are unspecified. '
      'Source snapshot replay, not a reconstruction of actual disruptions or a guarantee of every operator/extension. Original train calls and express/local patterns retained. '
      'Rows without service-day tags are excluded. Missing endpoint arrival/departure cells use the published companion clock; invalid trips are excluded. Connected OSM railway paths; unsupported sections remain gaps. '
      'No live positions or individual passenger counts. KORAIL suburban lines are included from separate dated workbooks; AREX and other metropolitan operators are not included. KTX/intercity has its own South Korea view.')


COMBINED_NOTE=('5–11 January 2026 reference week. Subway Lines 1–9 use the September 2025 snapshot; KORAIL Gyeongui–Jungang, Suin–Bundang and Gyeongchun use timetables effective 30 December 2025. '
               'Published calls, dwell and stopping patterns are retained. Railway gaps hide vehicle positions between stops. KTX, SRT and ITX-Cheongchun are in the separate South Korea view.')


def clock(value):
    h,m,s=map(int,value.split(':'))
    if not 0<=h<48 or not 0<=m<60 or not 0<=s<60:raise ValueError('Invalid clock')
    return h*3600+m*60+s


def call_times(arrival,departure):
    a=clock(arrival) if arrival else None;b=clock(departure) if departure else None
    if a is None and b is None:raise ValueError('Both source clocks missing')
    if a==0 and b is not None and b>3*3600:a=None
    if b==0 and a is not None and a>3*3600:b=None
    repaired=a is None or b is None
    a=b if a is None else a;b=a if b is None else b
    if a<3*3600:a+=86400
    if b<3*3600:b+=86400
    if b<a:raise ValueError('Backwards dwell')
    return a,b,repaired


def prepare(cache=CACHE,output=OUTPUT):
    pins=json.loads((ROOT/'data/reference/seoul/sources.json').read_text())
    for pin in pins:
        if file_hash(cache/pin['file'])!=pin['sha256']:raise ValueError('Changed Seoul source: '+pin['file'])
    stations={r['id']:r for r in csv.DictReader((cache/'stations.csv').open(encoding='utf-8-sig'))}
    groups=defaultdict(list);audit=Counter()
    for r in csv.DictReader((cache/'timetable.csv').open(encoding='utf-8-sig')):
        if not r['SI_ID'] and not r['STATION_NM']:audit['blank_station_rows']+=1;continue
        if not r['WEEKTAG']:audit['missing_service_day_rows']+=1;continue
        key=tuple(r[k] for k in ['WEEKTAG','LINE','TRAIN_NO','INOUTTAG','GUBHANG','ST_STT_NM','ED_STT_NM'])
        groups[key].append(r)
    tables={'agency.txt':[{'agency_id':'seoul','agency_name':'Seoul metropolitan subway','agency_url':'https://www.seoulmetro.co.kr/','agency_timezone':'Asia/Seoul'}],
        'stops.txt':[],'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar.txt':[]}
    ids=set();routes=set();numbers={}
    for idx,(key,rows) in enumerate(sorted(groups.items())):
        week,line,number,direction,express,origin,destination=key
        if line not in COLORS or week not in {'DAY','SAT','END'}:raise ValueError('Unexpected timetable category')
        calls=[];seen=set()
        try:
            for r in rows:
                if r['SI_ID'] not in stations:raise ValueError('Missing station coordinates')
                a,b,repaired=call_times(r['STT'],r['EDT']);audit['companion_clock_cells']+=int(repaired)
                sig=(r['SI_ID'],a,b)
                if sig in seen:audit['duplicate_call_rows']+=1;continue
                seen.add(sig);calls.append((a,b,r['SI_ID'],r['STATION_NM']))
            calls.sort()
            if len(calls)<2:raise ValueError('Single-call trip')
            if any(b[0]<a[1] for a,b in zip(calls,calls[1:])):raise ValueError('Overlapping source calls')
        except ValueError as error:audit[str(error)]+=1;continue
        rid=line+'-'+express;trip='seoul-'+str(idx);numbers[trip]=number
        if rid not in routes:
            routes.add(rid);tables['routes.txt'].append({'route_id':rid,'agency_id':'seoul','route_type':'1','route_short_name':'Line '+line+(' · express' if express=='1' else ''),'route_long_name':'Line '+line,'route_color':COLORS[line]})
        tables['trips.txt'].append({'route_id':rid,'service_id':week,'trip_id':trip,'direction_id': '0' if direction in {'UP','IN'} else '1','trip_headsign':destination})
        for i,(a,b,s,name) in enumerate(calls):
            if s not in ids:
                ids.add(s);station=stations[s];tables['stops.txt'].append({'stop_id':s,'stop_name':name,'stop_lat':station['lat'],'stop_lon':station['lon']})
            fmt=lambda v:f'{v//3600:02d}:{v//60%60:02d}:{v%60:02d}'
            tables['stop_times.txt'].append({'trip_id':trip,'stop_id':s,'stop_sequence':i+1,'arrival_time':fmt(a),'departure_time':fmt(b)})
    for week in ['DAY','SAT','END']:
        tables['calendar.txt'].append({'service_id':week,'start_date':'20260104','end_date':'20260112',**{d:int((i<5 and week=='DAY') or (i==5 and week=='SAT') or (i==6 and week=='END')) for i,d in enumerate(['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])}})
    with zipfile.ZipFile(cache/'gtfs.zip','w') as archive:
        for name,rows in tables.items():
            s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            archive.writestr(zipfile.ZipInfo(name,date_time=(2025,9,30,0,0,0)),s.getvalue(),compress_type=zipfile.ZIP_DEFLATED)
    with gzip.open(cache/'tracks.json.gz','rt') as f:geo=json.load(f)
    graph=FranceRailGraph(geo['ways'])
    @lru_cache(maxsize=None)
    def leg(a,b):
        curve=graph.leg(list(a),list(b))
        return curve if curve and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
    def resolve(route,trip,sequence,coordinates):return [leg(tuple(a),tuple(b)) for a,b in zip(coordinates,coordinates[1:])]
    source={'first':'2026-01-05','last':'2026-01-11','timezone':'Asia/Seoul','url':'local-conversion/gtfs.zip','sha256':file_hash(cache/'gtfs.zip'),
        'captured':'2026-10-23','published':'2025-09-30','calendar_validity':True,'assign_by_start':['subway'],'geometry_quality':'track',
        'source':'Seoul Metro official September 2025 bulk train timetable','source_url':'https://data.seoul.go.kr/dataList/OA-22522/L/1/datasetView.do',
        'license':'KOGL Type 1 attribution','license_url':'https://www.kogl.or.kr/info/licenseType1.do',
        'attribution':'Seoul Metro / Seoul Open Data Plaza · KOGL Type 1. Station inventory: official Korean open data preserved by minseok852/subway-etl. Railway geography © OpenStreetMap contributors, ODbL 1.0. SunTrain conversion and inferred track matching.',
        'note':NOTE,'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],
        'geometry_license':'ODbL 1.0','geometry_license_url':geo['metadata']['license_url'],'geometry_source_date':geo['metadata']['source_date'],'geometry_sha256':file_hash(cache/'tracks.json.gz')}
    prepare_rail('seoul',source,cache,output,lambda r,a:r['route_id'] in routes,
        lambda r,t:{'mode':'subway','operator':'Seoul metropolitan subway','line':r['route_short_name'],'route_id':r['route_id']},geometry_resolver=resolve)
    with gzip.open(output,'rt') as f:result=json.load(f)
    result['train_numbers']=numbers;result['metadata']['source_audit']=dict(audit)
    result['metadata']['sources']=[{'source_url':s['url'],'sha256':s['sha256'],'source_date':s.get('date','2026-10-23')} for s in pins]
    from scripts.prepare_seoul_suburban import prepare as prepare_suburban
    suburban=prepare_suburban(coordinate_cache=cache)
    result=merge_references([('metro',result),('korail',suburban)],source_name='Seoul metropolitan and KORAIL suburban railway schedules',replay_note=COMBINED_NOTE)
    result['metadata']['license']='Seoul Metro and station inventory: KOGL Type 1; KORAIL published timetable facts; OSM geography: ODbL 1.0'
    result['metadata']['suburban_source_audit']=suburban['metadata']['source_audit']
    result['metadata']['suburban_unlocated_station_trip_exclusions']=suburban['metadata']['unlocated_station_trip_exclusions']
    save_reference(result,output);print('Days',{d:len(v) for d,v in result['days'].items()},'bytes',output.stat().st_size,'audit',dict(audit),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=OUTPUT);a=p.parse_args();prepare(a.cache,a.output)
