"""Prepare the KRL week from the official PDF's station cells and connected tracks."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date,datetime,time,timedelta
import gzip
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference, compact_reference, merge_references
from scripts.prepare_jakarta_mrt import build as build_mrt, NOTE as COMBINED_NOTE
from scripts.prepare_jakarta_lrt import build as build_lrt, NOTE as LRT_NOTE
from scripts.prepare_jakarta_lrt_city import build as build_lrt_jakarta, NOTE as LRT_JAKARTA_NOTE
from scripts.prepare_jakarta_intercity import build as build_intercity, NOTE as INTERCITY_NOTE
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_jakarta_timetable import PDF_SHA256,SOURCE_URL
TIMETABLE=ROOT/'data/reference/jakarta/timetable-2025-12-13.json.gz'
GEOMETRY=ROOT/'data/reference/jakarta/rail-osm-2026-10-20.json.gz'
TIMETABLE_SHA256='f65c268a47dc77f6fce6665872cc4c8e7bfe94f7f8ea948aa23f74ea701e31f6'
GEOMETRY_SHA256='fee798fe12616a629ef11009d406538a95c97684f7510d1f3235ed646b1f5f9c'
FIRST='2025-12-15';LAST='2025-12-21'
COLORS={'Bogor':'#E4002B','Nambo':'#E4002B','Cikarang':'#005EB8','Rangkasbitung':'#00843D','Tangerang':'#9B5A28','Tanjung Priok':'#E56DB1'}
NOTE='KRL schedules from the official 13 December 2025 timetable. Weekday restrictions are retained. Positions are estimated along mapped railway tracks. Individual train passenger counts are unavailable.'


def active(trip,day):
    # The selected week and its carry days contain no Indonesian national holiday.
    if not date(2025,12,14)<=day<=date(2025,12,22):raise ValueError('Calendar extension requires a new holiday/revision audit')
    return (not trip['weekdays_only'] or day.weekday()<5) and (not trip.get('valid_through') or str(day)<=trip['valid_through'])


def prepare(output):
    for path,pin in [(TIMETABLE,TIMETABLE_SHA256),(GEOMETRY,GEOMETRY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pin:raise ValueError('KRL reference differs from validated source: '+str(path))
    with gzip.open(TIMETABLE,'rt') as f:timetable=json.load(f)
    with gzip.open(GEOMETRY,'rt') as f:geographic=json.load(f)
    graph=FranceRailGraph(geographic['ways']);zone=ZoneInfo('Asia/Jakarta')
    first,last=date.fromisoformat(FIRST),date.fromisoformat(LAST)
    days=[first+timedelta(days=i) for i in range((last-first).days+1)]
    keys=sorted({code for trip in timetable['trips'] for code,clock in trip['calls']});station_ids={c:i for i,c in enumerate(keys)}
    result={'stations':[{'name':geographic['stations'][c]['name'],'lon':geographic['stations'][c]['coordinates'][0],
        'lat':geographic['stations'][c]['coordinates'][1],'mode':'train'} for c in keys],
        'patterns':{},'paths':{},'days':{str(d):[] for d in days},'train_numbers':{}}
    legs={};matched=total=0
    for trip in timetable['trips']:
        calls=trip['calls'];line=trip['line'];start=calls[0][1];path_keys=[]
        for (a,_),(b,_) in zip(calls,calls[1:]):
            if (a,b) not in legs:
                origin,destination=[geographic['stations'][c]['coordinates'] for c in [a,b]]
                curve=graph.leg(origin,destination)
                if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([origin,destination])[-1]):curve=None
                key='jakarta-'+a+'-'+b;legs[a,b]=key
                result['paths'][key]={'coordinates':curve or [],'distances':cumulative_distances(curve or []),'quality':'track' if curve else 'approximate'}
            path_keys.append(legs[a,b])
        key='krl-'+trip['number'];result['train_numbers'][key]=trip['number']
        result['patterns'][key]={'mode':'commuter_rail','operator':'KAI Commuter','line':line,'route_id':line,'color':COLORS[line],
            'direction':'Not specified','origin':geographic['stations'][calls[0][0]]['name'],
            'destination':geographic['stations'][calls[-1][0]]['name'],
            'stops':[[station_ids[c],clock-start,clock-start] for c,clock in calls],'legs':path_keys}
        for offset in range(-1,len(days)+1):
            service_day=first+timedelta(days=offset)
            if not active(trip,service_day):continue
            departure=datetime.combine(service_day,time(),zone).timestamp()+start
            owner=datetime.fromtimestamp(departure,zone).date()
            if datetime.fromtimestamp(departure,zone).hour<3:owner-=timedelta(days=1)
            if str(owner) in result['days']:
                midnight=datetime.combine(owner,time(),zone).timestamp()
                result['days'][str(owner)].append([key,key,int(departure-midnight)])
                total+=len(path_keys);matched+=sum(bool(result['paths'][p]['coordinates']) for p in path_keys)
    for rows in result['days'].values():rows.sort(key=lambda row:(row[2],row[1]))
    result['metadata']={'start_date':FIRST,'end_date':LAST,'timezone':'Asia/Jakarta',
        'source':'KAI Commuter official KRL timetable, 13 December 2025 edition; table conversion by SunTrain',
        'source_url':SOURCE_URL,'license':'Published KAI Commuter timetable; source rights retained','license_url':'https://www.commuterline.id/',
        'attribution':'Timetable: PT Kereta Commuter Indonesia / KAI Commuter, official 13 December 2025 publication. Station-event table extraction and replay preparation by SunTrain. Railway ways and station geography © OpenStreetMap contributors, ODbL 1.0.',
        'sources':[{'source_url':SOURCE_URL,'source_date':'2025-12-13','published':'2025-12-13','sha256':PDF_SHA256}],
        'geometry_source':'© OpenStreetMap contributors; KRL route-member railway ways and station features',
        'geometry_source_url':'https://www.openstreetmap.org/copyright','geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
        'geometry_source_date':'2026-10-20; geographic reference for December 2025 timetable','geometry_sha256':GEOMETRY_SHA256,
        'replay_note':NOTE,'daily_services':{d:dict(Counter(result['patterns'][p]['line'] for p,t,o in rows)) for d,rows in result['days'].items()},
        'omitted_trips':timetable['metadata']['omitted_rows'],'track_coverage':{'matched':matched,'total':total},
        'unresolved_geometry_patterns':{},'unresolved_geometry_trips':{}}
    mrt=build_mrt(ROOT/'.cache/jakarta/mrt-prepared.json.gz')
    lrt=build_lrt()
    lrt_jakarta=build_lrt_jakarta()
    intercity=build_intercity()
    result=merge_references([('krl',compact_reference(result)),('mrt',mrt),('lrt',lrt),('lrtj',lrt_jakarta),('intercity',intercity)],
        source_name='Jakarta KRL, MRT, both LRT networks, airport rail and Whoosh historical timetables',
        replay_note=COMBINED_NOTE+' '+LRT_NOTE+' '+LRT_JAKARTA_NOTE+' '+INTERCITY_NOTE)
    result['metadata']['operator_periods']={'KAI Commuter':'15–21 December 2025',
        'MRT Jakarta':{'snapshot':'2026-05-03','mapping':mrt['metadata']['date_mapping']},
        'LRT Jabodebek':{'source_updated_dates':lrt['metadata']['source_updated_dates'],'captured':'2026-10-20','mapping':lrt['metadata']['date_mapping']},
        'LRT Jakarta':{'valid_from':'2026-09-19','mapping':lrt_jakarta['metadata']['date_mapping']},
        **intercity['metadata']['operator_periods']}
    save_reference(result,output)
    print('daily',{d:len(v) for d,v in result['days'].items()},'coverage',matched,total,'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'data/reference/jakarta/2025-12-15.json.gz')
    a=p.parse_args();prepare(a.output)
