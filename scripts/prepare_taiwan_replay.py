"""Prepare Taiwan rail from official daily JSON and a dated THSR PDF."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import date
from functools import lru_cache
import gzip
import io
import json
from pathlib import Path
import re
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail

CACHE=ROOT/'.cache/taiwan'
OUTPUT=ROOT/'data/reference/taiwan/2026-10-23.json.gz'
FIRST,LAST='2026-10-23','2026-10-27'
LICENSE='https://data.gov.tw/license'
HSR_URL='https://www.thsrc.com.tw/Attachment/Download?pageID=a3b630bb-1066-4352-a1ef-58c7b4e8ef7c&id=4d5ce117-801a-4848-aa53-adc35c3c6455'
MIRROR='https://raw.githubusercontent.com/siriushsu/taiwan-rail-live/d41aafac1482d50eb0ea72d37ebdf2f87d9d9677/data/thsr_schedule_dense.json'
NOTE=('Taiwan Railways and Taiwan High Speed Rail, 23–27 October 2026. Official daily TRA schedules and the dated THSR holiday timetable. '
      'THSR publishes one time per stop, so station dwell is unavailable. Passenger services only; private charters are excluded. '
      'Connected OSM railway paths, separated by track gauge; missing sections remain gaps. Scheduled estimates, no live tracking or passenger loads.')


def seconds(value):
    h,m,s=map(int,value.split(':'))
    if not 0<=h<24 or not 0<=m<60 or not 0<=s<60:raise ValueError('Invalid source clock')
    return 3600*h+60*m+s


def unroll(pairs):
    """Accept one genuine midnight crossing, reject unexplained backwards clocks."""
    result=[];offset=0;previous=None
    for arrival,departure in pairs:
        values=[]
        for value in [arrival,departure]:
            candidate=value+offset
            if previous is not None and candidate<previous:
                if offset or previous%86400<20*3600 or value>4*3600:
                    raise ValueError('Backwards source clock')
                offset=86400;candidate=value+offset
            values.append(candidate);previous=candidate
        result.append(values)
    return result


def operation_dates(text):
    if not text:return {date(2026,10,d) for d in range(23,28)}
    dates=set()
    for part in text.replace(' ','').split(','):
        match=re.fullmatch(r'10/(\d{2})(?:~10/(\d{2}))?',part)
        if not match:raise ValueError('Unknown THSR operation date: '+text)
        a=int(match[1]);b=int(match[2] or match[1])
        if not 23<=a<=b<=27:raise ValueError('THSR dates outside PDF validity')
        dates.update(date(2026,10,d) for d in range(a,b+1))
    return dates


def thsr_rows(filename):
    import pdfplumber
    rows=[]
    with pdfplumber.open(filename) as pdf:
        if len(pdf.pages)!=4:raise ValueError('Unexpected holiday PDF layout')
        for page_index,page in enumerate(pdf.pages):
            words=page.extract_words();text=page.extract_text()
            if page_index in {0,2} and '2026/10/23~2026/10/27' not in text:raise ValueError('Unexpected THSR validity')
            south='Southbound' in text
            names=['南港','台北','板橋','桃園','新竹','苗栗','台中','彰化','雲林','嘉義','台南','左營']
            if not south:names.reverse()
            centers=[]
            for name in names:
                header=next(w for w in words if w['text']==name and w['top']<150)
                centers.append((header['x0']+header['x1'])/2)
            observed=0
            for number in [w for w in words if w['x0']<90 and 80<w['top']<1170 and re.fullmatch(r'\d{3,4}',w['text'])]:
                line=[w for w in words if abs(w['top']-number['top'])<2]
                qualifiers=''.join(w['text'] for w in line if 90<w['x0']<200)
                calls={}
                for w in line:
                    if re.fullmatch(r'\d{2}:\d{2}',w['text']) and w['x0']>200:
                        idx=min(range(12),key=lambda i:abs((w['x0']+w['x1'])/2-centers[i]))
                        if idx in calls:raise ValueError('Duplicate THSR station cell')
                        calls[idx]=seconds(w['text']+':00');observed+=1
                if len(calls)<2:raise ValueError('Incomplete THSR train row')
                rows.append({'number':number['text'].zfill(4),'dates':operation_dates(qualifiers),
                    'direction':'Southbound' if south else 'Northbound',
                    'calls':[(names[i],t) for i,t in sorted(calls.items())]})
            expected=sum(bool(re.fullmatch(r'\d{2}:\d{2}',w['text'])) for w in words)
            if observed!=expected:raise ValueError('Unparsed THSR time cells')
    if len({r['number'] for r in rows})!=len(rows):raise ValueError('Duplicate THSR train numbers')
    return rows


def category(code):
    if code in {'1131','1135'}:return 'Local','2574A8'
    if code=='1132':return 'Fast local','27816B'
    if code.startswith('110'):return 'Tze-Chiang / express','B84A42'
    if code.startswith('111'):return 'Chu-Kuang','C77F26'
    if code in {'1120','1140','1141','1151'}:return 'Other passenger','816AA4'
    return None


def convert(cache):
    """Build an intermediate GTFS using only dated, published train calls."""
    sources=json.loads((ROOT/'data/reference/taiwan/sources.json').read_text())
    for entry in sources:
        if file_hash(cache/entry['file'])!=entry['sha256']:raise ValueError('Changed TRA source: '+entry['file'])
    raw_stations=json.loads((cache/'tra-stations.json').read_text())
    stations={r['stationCode']:{'stop_id':r['stationCode'],'stop_name':r['stationEName']+' · '+r['stationName'],
        'stop_lat':r['gps'].split()[0],'stop_lon':r['gps'].split()[1]} for r in raw_stations}
    # Only official TDX station names/coordinates are reused from this preserved
    # data file; its timetable and interpolated passing points are not used.
    mirror=json.loads((cache/'mirror-thsr_schedule_dense.json').read_text())
    hs={s['name']:s for t in mirror['trains'] for s in t['stops'] if s.get('stop')}
    english=['Nangang','Taipei','Banqiao','Taoyuan','Hsinchu','Miaoli','Taichung','Changhua','Yunlin','Chiayi','Tainan','Zuoying']
    for name,en in zip(['南港','台北','板橋','桃園','新竹','苗栗','台中','彰化','雲林','嘉義','台南','左營'],english):
        s=hs[name];stations['hsr-'+name]={'stop_id':'hsr-'+name,'stop_name':en+' HSR · '+name,'stop_lat':s['lat'],'stop_lon':s['lon']}
    tables={'agency.txt':[{'agency_id':a,'agency_name':n,'agency_url':u,'agency_timezone':'Asia/Taipei'} for a,n,u in
        [('tra','Taiwan Railways','https://www.railway.gov.tw/'),('thsr','Taiwan High Speed Rail','https://www.thsrc.com.tw/')]],
        'stops.txt':list(stations.values()),'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar_dates.txt':[]}
    numbers={};routes=set();audit=Counter()
    def add(day,number,agency,label,color,direction,calls,times,via='0'):
        if len(calls)<2 or any(s not in stations for s in calls):raise ValueError('Missing source station')
        times=unroll(times);trip=agency+'-'+day.strftime('%Y%m%d')+'-'+number;rid=agency+'-'+label+'-via-'+via
        if rid not in routes:
            routes.add(rid);tables['routes.txt'].append({'route_id':rid,'agency_id':agency,'route_short_name':label,'route_long_name':label,'route_type':'2','route_color':color,'taiwan_via':via})
        numbers[trip]=number;tables['trips.txt'].append({'route_id':rid,'service_id':day.strftime('%Y%m%d'),'trip_id':trip,'direction_id':'0' if direction in {'1','Southbound'} else '1'})
        for i,(station,(a,b)) in enumerate(zip(calls,times)):
            clock=lambda s:f'{s//3600:02d}:{s//60%60:02d}:{s%60:02d}'
            tables['stop_times.txt'].append({'trip_id':trip,'stop_id':station,'stop_sequence':i+1,'arrival_time':clock(a),'departure_time':clock(b)})
    for filename in sorted(cache.glob('tra-202610*.json')):
        day=date.fromisoformat(filename.stem[4:8]+'-'+filename.stem[8:10]+'-'+filename.stem[10:12])
        if not date.fromisoformat(FIRST)<=day<=date(2026,10,28):continue
        for t in json.loads(filename.read_text())['TrainInfos']:
            c=category(t['CarClass'])
            if t['Type'] not in {'1','2','3'} or c is None:audit['non_public_passenger']+=1;continue
            calls=sorted(t['TimeInfos'],key=lambda r:int(r['Order']))
            try:add(day,t['Train'],'tra',*c,t['LineDir'],[s['Station'] for s in calls],[(seconds(s['ARRTime']),seconds(s['DEPTime'])) for s in calls],via=t['Line'])
            except ValueError as error:audit[str(error)]+=1
    for row in thsr_rows(cache/'thsr-holiday.pdf'):
        for day in sorted(row['dates']):
            add(day,row['number'],'thsr','High-speed rail','E85D0D',row['direction'],['hsr-'+n for n,_ in row['calls']],[(t,t) for _,t in row['calls']])
    days={t['service_id'] for t in tables['trips.txt']}
    # The generic importer also checks the preceding date. It cannot supply
    # an occurrence here: ownership is by origin departure, never overlap.
    tables['calendar.txt']=[{'service_id':'unused-boundary','start_date':'20261022','end_date':'20261022',
        **{d:0 for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']}}]
    tables['calendar_dates.txt']=[{'service_id':d,'date':d,'exception_type':'1'} for d in sorted(days)]
    with zipfile.ZipFile(cache/'gtfs.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name,rows in tables.items():
            s=io.StringIO();writer=csv.DictWriter(s,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);z.writestr(zipfile.ZipInfo(name,date_time=(2026,10,23,0,0,0)),s.getvalue(),compress_type=zipfile.ZIP_DEFLATED)
    return numbers,sources,dict(audit)


def via_point(via,a,b):
    """Honour the official Mountain/Coast field when an express skips the split."""
    point={'1':[120.68691,24.13728],'2':[120.55752,24.23702]}.get(via)
    if point and max(a[0],b[0])<121 and min(a[1],b[1])<point[1]<max(a[1],b[1]):
        return point
    return None


def prepare(cache=CACHE,output=OUTPUT):
    numbers,sources,audit=convert(cache)
    with gzip.open(cache/'tracks.json.gz','rt') as stream:geo=json.load(stream)
    graphs={a:FranceRailGraph([w for w in geo['ways'] if w['gauge']==g]) for a,g in [('tra','1067'),('thsr','1435')]}
    @lru_cache(maxsize=None)
    def leg(agency,via,a,b):
        graph=graphs[agency]
        waypoint=via_point(via,a,b) if agency=='tra' else None
        if waypoint:
            # Fix one physical anchor for both halves; never join different tracks
            # with a synthetic connector at the intermediate corridor hint.
            anchors=graph.anchors(waypoint)
            if not anchors:return None
            graph.anchor_cache[tuple(waypoint)]=anchors[:1]
            first,second=graph.leg(list(a),waypoint),graph.leg(waypoint,list(b))
            curve=first+second[1:] if first and second and first[-1]==second[0] else None
        else:
            curve=graph.leg(list(a),list(b))
        return curve if curve and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
    def resolve(route,trip,sequence,coordinates):return [leg(route['agency_id'],route['taiwan_via'],tuple(a),tuple(b)) for a,b in zip(coordinates,coordinates[1:])]
    source={'first':FIRST,'last':LAST,'timezone':'Asia/Taipei','url':'local-conversion/gtfs.zip',
        'sha256':file_hash(cache/'gtfs.zip'),'captured':'2026-10-23','published':'2026-10-23','calendar_validity':True,
        'source':'Taiwan Railways daily JSON and official Taiwan High Speed Rail holiday timetable',
        'source_url':'https://data.gov.tw/en/datasets/6138','license':'Taiwan Open Government Data License 1.0 (TRA / TDX data)',
        'license_url':LICENSE,'attribution':'Taiwan Railway Corporation · Taiwan High Speed Rail Corporation / MOTC TDX. '
        'Railway geography © OpenStreetMap contributors, ODbL 1.0. SunTrain timetable conversion and inferred track matching.',
        'note':NOTE,'assign_by_start':['train','high_speed_rail'],'geometry_quality':'track',
        'geometry_source':geo['metadata']['source'],'geometry_source_url':geo['metadata']['source_url'],
        'geometry_license':'ODbL 1.0','geometry_license_url':geo['metadata']['license_url'],
        'geometry_source_date':geo['metadata']['source_date'],'geometry_sha256':file_hash(cache/'tracks.json.gz')}
    def describe(route,trip):
        hsr=route['agency_id']=='thsr'
        return {'mode':'high_speed_rail' if hsr else 'train','operator':'Taiwan High Speed Rail' if hsr else 'Taiwan Railways',
            'line':route['route_short_name'],'route_id':route['route_id'].rsplit('-via-',1)[0],
            'direction':('Southbound' if trip['direction_id']=='0' else 'Northbound') if hsr else ('Direction A' if trip['direction_id']=='0' else 'Direction B')}
    prepare_rail('taiwan',source,cache,output,lambda r,a:r['agency_id'] in {'tra','thsr'},describe,geometry_resolver=resolve)
    with gzip.open(output,'rt') as stream:result=json.load(stream)
    result['train_numbers']=numbers
    result['metadata']['conversion_sha256']=source['sha256']
    result['metadata']['sources']=[{'source_url':r['url'],'sha256':r['sha256'],'source_date':'2026-10-23'} for r in sources]
    result['metadata']['raw_sources']=sources
    result['metadata']['station_coordinate_source_note']='Only twelve station coordinates are reused from the preserved TDX data; no community interpolation or schedule is used.'
    result['metadata']['conversion_omissions']=audit
    save_reference(result,output)
    print('Days',{d:len(v) for d,v in result['days'].items()},'bytes',output.stat().st_size,'conversion omissions',audit,flush=True)

def download_sources(cache):
    from scripts.prepare_boston_replay import fetch
    cache.mkdir(parents=True,exist_ok=True)
    for source in json.loads((ROOT/'data/reference/taiwan/sources.json').read_text()):
        if source['file']=='tracks.json.gz':continue  # Build from the PBF separately.
        path=fetch(source['url'],cache/source['file'])
        if file_hash(path)!=source['sha256']:raise ValueError('Changed source; re-audit before updating pins: '+source['file'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=OUTPUT)
    p.add_argument('--download-sources',action='store_true');a=p.parse_args()
    if a.download_sources:download_sources(a.cache)
    else:prepare(a.cache,a.output)
