"""Taipei Metro replay anchored to official terminal departures and run/dwell tables."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import date,timedelta
import gzip
import io
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash,path_legs
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.compact_transit import save_reference
CACHE=ROOT/'.cache/taipei'
OUTPUT=ROOT/'data/reference/taipei/2026-10-23.json.gz'
NOTE=('Taipei Metro Red, Green, Orange and Blue lines, 23–27 October 2026. Published terminal departures with official run/dwell-time estimates between stops; '
      'not a linked train-level timetable. Partial coverage: intermediate morning starts are omitted; Brown and Circular lines are unavailable. '
      'Saturday/Sunday and 26 October public-holiday calendars are retained. No live positions or passenger loads.')
SPECS={'R-1':('R','R01','R28'),'R-2':('R','R01','R22'),'R-3':('R_XBT','R22','R22A'),
       'G-1':('G','G01','G19'),'G-2':('G','G08','G19'),'G-3':('G_XBT','G03A','G03'),
       'O-1':('O_XINZHUANG','O01','O21'),'O-2':('O_LUZHOU','O01','O54'),
       'BL-1':('BL','BL01','BL23'),'BL-2':('BL','BL05','BL23')}
LABELS={'R':'Red · Tamsui–Xinyi','R_XBT':'Red · Xinbeitou shuttle','G':'Green · Songshan–Xindian',
        'G_XBT':'Green · Xiaobitan shuttle','O_XINZHUANG':'Orange · Huilong','O_LUZHOU':'Orange · Luzhou','BL':'Blue · Bannan'}


def clean(name):return name.replace('捷運','').replace('臺','台').removesuffix('站')


def timetable_kind(day,line):
    if day==date(2026,10,26) or day.weekday()==6:return 'sunday' if line=='r' else 'holiday'
    if day.weekday()==5:return 'saturday' if line=='r' else 'holiday'
    return 'weekday'


def departure(value):
    cells=value.strip('{}').split(',')
    if len(cells)!=5 or cells[1] or cells[2] or cells[4]:raise ValueError('Unexpected station timetable encoding')
    h,m=map(int,cells[3].split(':'))
    if not 0<=h<=25 or not 0<=m<60:raise ValueError('Invalid departure clock')
    return h*3600+m*60+(86400 if h<3 else 0)


def prepare(cache=CACHE,output=OUTPUT):
    manifest=ROOT/'data/reference/taipei/sources.json'
    sources=json.loads(manifest.read_text())
    for s in sources:
        if file_hash(cache/s['file'])!=s['sha256']:raise ValueError('Changed Taipei source: '+s['file'])
    lines={l['id']:l for l in json.loads((cache/'trtc.json').read_text())['lines']}
    files={p.stem:list(csv.DictReader(p.open(encoding='big5'))) for p in cache.glob('*.csv') if p.name!='travel.csv'}
    names={r['StationID']:r['StationName'] for rows in files.values() for r in rows if r['StationID']}
    # Codes are line-specific at interchanges; resolve using each line's own CSV.
    coords={};sequences={}
    for rid,(lid,first,last) in SPECS.items():
        lookup={clean(r['StationName']):r['StationID'] for rows in files.values() for r in rows if r['RouteID']==rid}
        lookup.update({clean(names[k]):k for k in [first,last]})
        seq=[]
        for s in lines[lid]['stations']:
            key=lookup.get(clean(s['name']))
            if key:seq.append(key);coords[key]=s
        if first not in seq or last not in seq:raise ValueError('Missing Metro endpoint: '+rid)
        a,b=seq.index(first),seq.index(last);sequences[rid]=seq[min(a,b):max(a,b)+1]
    travel={};dwell={}
    for r in csv.DictReader((cache/'travel.csv').open(encoding='big5')):
        a,b=clean(r['stationA']),clean(r['stationB']);bus=r['stationbus'];travel[bus,a,b]=int(r['traveltime']);travel[bus,b,a]=int(r['traveltime'])
        dwell[bus,a]=int(r['stoptime'])
    tables={'agency.txt':[{'agency_id':'TRTC','agency_name':'Taipei Metro','agency_url':'https://www.metro.taipei/','agency_timezone':'Asia/Taipei'}],
        'stops.txt':[{'stop_id':k,'stop_name':names[k],'stop_lat':v['lat'],'stop_lon':v['lon']} for k,v in sorted(coords.items())],
        'routes.txt':[],'trips.txt':[],'stop_times.txt':[],'calendar_dates.txt':[]}
    for rid,(lid,_,_) in SPECS.items():
        tables['routes.txt'].append({'route_id':rid,'agency_id':'TRTC','route_type':'1','route_short_name':LABELS[lid],'route_long_name':LABELS[lid],'route_color':lines[lid]['color'].lstrip('#')})
    audit=Counter();used=set()
    for n in range(6):
        day=date(2026,10,23)+timedelta(days=n);ds=day.strftime('%Y%m%d')
        tables['calendar_dates.txt'].append({'service_id':ds,'date':ds,'exception_type':'1'})
        for line in ['r','g','o','bl']:
            for row in files[line+'-'+timetable_kind(day,line)]:
                rid=row['RouteID']
                if rid not in SPECS or row['StationID'] not in coords:continue
                _,first,last=SPECS[rid];origin=first if row['Direction']=='0' else last
                if row['StationID']!=origin:continue
                seq=sequences[rid][:]
                a,b=seq.index(origin),seq.index(row['DestinationStaionID'])
                if a>b:seq=seq[b:a+1][::-1]
                else:seq=seq[a:b+1]
                if len(seq)<2:continue
                t=departure(row['DepartureTimes']);key=(ds,rid,origin,row['DestinationStaionID'],t)
                if key in used:raise ValueError('Duplicate Metro terminal departure')
                used.add(key);trip='metro-'+ds+'-'+str(len(used));times=[(t,t)]
                for x,y in zip(seq,seq[1:]):
                    a,b=clean(names[x]),clean(names[y])
                    buses={'R-1':['淡水-廣慈/奉天宮'],'R-2':['北投-大安','淡水-廣慈/奉天宮'],'R-3':['北投-新北投'],
                        'G-1':['松山-新店'],'G-2':['松山-台電大樓','松山-新店'],'G-3':['七張-小碧潭'],
                        'O-1':['南勢角-迴龍'],'O-2':['南勢角-蘆洲'],'BL-1':['南港展覽館-頂埔'],
                        'BL-2':['南港展覽館-亞東醫院','南港展覽館-頂埔']}[rid]
                    bus=next(bus for bus in buses if (bus,a,b) in travel)
                    arrival=times[-1][1]+travel[bus,a,b]
                    times.append((arrival,arrival+(dwell.get((bus,b),0) if y!=seq[-1] else 0)))
                tables['trips.txt'].append({'route_id':rid,'service_id':ds,'trip_id':trip,'direction_id':row['Direction']})
                for i,(s,(a,b)) in enumerate(zip(seq,times)):
                    clock=lambda v:f'{v//3600:02d}:{v//60%60:02d}:{v%60:02d}'
                    tables['stop_times.txt'].append({'trip_id':trip,'stop_id':s,'stop_sequence':i+1,'arrival_time':clock(a),'departure_time':clock(b)})
                audit[rid]+=1
    tables['calendar.txt']=[{'service_id':'unused-boundary','start_date':'20261022','end_date':'20261022',**{d:0 for d in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']}}]
    with zipfile.ZipFile(cache/'gtfs.zip','w') as archive:
        for name,rows in tables.items():
            stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            archive.writestr(zipfile.ZipInfo(name,date_time=(2026,10,23,0,0,0)),stream.getvalue(),compress_type=zipfile.ZIP_DEFLATED)
    def resolve(route,trip,sequence,coordinates):
        lid=SPECS[route['route_id']][0];points=[[lon,lat] for lat,lon in lines[lid]['shape']]
        if (trip['direction_id']=='0') != (sequences[route['route_id']][0]==SPECS[route['route_id']][1]):points.reverse()
        return path_legs([(i,None,p) for i,p in enumerate(points)],None,coordinates)
    source={'first':'2026-10-23','last':'2026-10-27','timezone':'Asia/Taipei','url':'local-conversion/gtfs.zip','sha256':file_hash(cache/'gtfs.zip'),
        'captured':'2026-10-23','published':'','calendar_validity':True,'assign_by_start':['subway'],
        'source':'Taipei Metro official terminal departures and published run/dwell times','source_url':'https://data.gov.tw/dataset/131737',
        'license':'Taiwan Open Government Data License 1.0','license_url':'https://data.gov.tw/license',
        'attribution':'Taipei Rapid Transit Corporation / Taipei City open data. TDX railway shapes preserved by Rail Island; Red extension geography © OpenStreetMap contributors, ODbL 1.0. SunTrain conversion.',
        'note':NOTE,'geometry_source':'TDX railway shapes; Red extension OSM','geometry_source_url':next(s['url'] for s in sources if s['file']=='trtc.json'),
        'geometry_license':'Government Open Data License 1.0; OSM extension ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/','geometry_source_date':'Preserved October 2026 snapshot'}
    prepare_rail('taipei',source,cache,output,lambda r,a:r['route_id'] in SPECS,
        lambda r,t:{'mode':'subway','line':r['route_short_name'],'route_id':r['route_id'],'operator':'Taipei Metro'},geometry_resolver=resolve)
    with gzip.open(output,'rt') as f:r=json.load(f)
    r['metadata']['sources']=[{'source_url':s['url'],'sha256':s['sha256'],'source_date':'2026-10-23'} for s in sources]
    r['metadata']['timing_method']='Published terminal departure plus official run/dwell-time estimates; no linked train IDs'
    save_reference(r,output);print('Days',{d:len(v) for d,v in r['days'].items()},'bytes',output.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=CACHE);p.add_argument('--output',type=Path,default=OUTPUT);a=p.parse_args();prepare(a.cache,a.output)
