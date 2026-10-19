"""Prepare Luxembourg passenger trains for 1–7 June 2026."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timedelta
import gzip
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_portugal_replay import geometry_resolver
from scripts.prepare_rail_replay import prepare as prepare_rail
GEOMETRY=ROOT/'data/reference/luxembourg/act-rail-2026-10-09.json.gz'
GEOMETRY_SHA256='a64b5b1e6ffdd411d361c31e61576cb44366d2dc5ae0522cd12549592b709224'
PRODUCTS={'RB','RE','TER','IC','TGV'}
# Boundary timing points are actual source calls. Nearby international branch
# termini retain their timetable calls; unavailable foreign geometry stays gaps.
BORDER_STOPS={'000300000033','000300000034','000300000131','000400000053','000400000064','000500000081',
              '000400000002','000400000106'}
SOURCE={'first':'2026-06-01','last':'2026-06-07','timezone':'Europe/Berlin','calendar_validity':True,
    'captured':'2026-05-28','published':'2026-05-27',
    'url':'https://download.data.public.lu/resources/horaires-et-arrets-des-transport-publics-gtfs/20260528-044959/gtfs-20260527-20260712.zip',
    'sha256':'9c37b008f7e191658546c3a9247f2889065859d8a38801c18fbccdc2fe7b8933',
    'source':'Administration des transports publics · official historical national GTFS, CFL passenger rail selection',
    'source_url':'https://data.public.lu/en/datasets/horaires-et-arrets-des-transport-publics-gtfs/',
    'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
    'attribution':'Timetables: Administration des transports publics, Luxembourg, CC BY 4.0, archived 28 May 2026. Railway geography: Administration du cadastre et de la topographie / Géoportail Luxembourg, CC0, resource 9 October 2026. Selected, matched and simplified by SunTrain.',
    'assign_by_start':['train'],'geometry_quality':'track',
    'geometry_source':'ACT / Géoportail Luxembourg · official INSPIRE RailwayLink; reprojected, matched and simplified by SunTrain',
    'geometry_source_url':'https://data.public.lu/en/datasets/inspire-annex-i-theme-transport-networks-rail-railwaylink-3/',
    'geometry_license':'CC0 1.0','geometry_license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
    'geometry_source_date':'Resource 2026-10-09; geographic reference for June 2026 schedules','geometry_sha256':GEOMETRY_SHA256,
    'note':'Luxembourg passenger trains from the official May 2026 archive. Domestic and source border calls retain original times; distant foreign portions are excluded. Inferred railway alignments, not exact operating tracks or every historical diversion. Unsupported sections remain gaps. Trams, buses and replacement buses are excluded. No individual passenger loads.'}
COLORS={'RB':'247C97','RE':'B42135','TER':'2775B6','IC':'7252A1','TGV':'A12769'}


def selected_route(route,agencies):
    return (route.get('agency_id')=='11' and agencies.get('11',{}).get('agency_name')=='Chemins de Fer Luxembourgeois'
            and route.get('route_type')=='2' and route.get('route_short_name') in PRODUCTS)


def domestic_sequence(sequence):
    indices=[i for i,r in enumerate(sequence) if r['stop_id'].startswith(('0001','0002')) or r['stop_id'] in BORDER_STOPS]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def verify_timezone():
    # The national feed declares Europe/Berlin. Use that original zone while
    # compiling, then label the replay Europe/Luxembourg only after verifying
    # every hour of the service window, including both carry days.
    first=datetime.fromisoformat(SOURCE['first'])-timedelta(days=1)
    for i in range(9*24):
        clock=first+timedelta(hours=i)
        if clock.replace(tzinfo=ZoneInfo(SOURCE['timezone'])).timestamp()!=clock.replace(tzinfo=ZoneInfo('Europe/Luxembourg')).timestamp():
            raise ValueError('Source and Luxembourg timezones disagree in the selected window')


def prepare(cache,output):
    verify_timezone()
    if file_hash(GEOMETRY)!=GEOMETRY_SHA256:raise ValueError('Luxembourg railway geometry differs from the validated reference')
    with gzip.open(GEOMETRY,'rt') as stream:geographic=json.load(stream)
    numbers,destinations,audit={},{},Counter()
    def select(sequence,stops):
        clipped=domestic_sequence(sequence)
        if clipped:
            audit['included_candidates']+=1
            if len(clipped)<len(sequence):audit['clipped_candidates']+=1
            destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
        else:audit['outside_scope_or_single_call']+=1
        return clipped
    def describe(route,trip):
        short=route['route_short_name'];numbers[trip['trip_id']]=trip.get('trip_short_name') or trip['trip_id']
        return {'mode':'train','operator':'CFL','route_id':route['route_id'],'route_short_name':short,'category':short,
                'line':short+' · CFL','color':COLORS[short],'direction':'Direction '+{'0':'A','1':'B'}.get(trip.get('direction_id'),'unknown'),
                'destination':destinations[trip['trip_id']]}
    prepare_rail('luxembourg',SOURCE,cache,output,selected_route,describe,geometry_resolver=geometry_resolver(geographic),select_sequence=select)
    with gzip.open(output,'rt') as stream:result=json.load(stream)
    used={t for rows in result['days'].values() for _,t,_ in rows}
    result['train_numbers']={t:n for t,n in numbers.items() if t in used}
    result['metadata'].update(timezone='Europe/Luxembourg',source_timezone=SOURCE['timezone'],scope_audit=dict(audit))
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',output.stat().st_size,'scope',dict(audit),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/luxembourg')
    p.add_argument('--output',type=Path,default=ROOT/'data/reference/luxembourg/2026-06-01.json.gz')
    a=p.parse_args();prepare(a.cache,a.output)
