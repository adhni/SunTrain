"""Prepare SNCB/NMBS passenger trains for 1–7 June 2026."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_switzerland_replay import geometry_resolver
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY=ROOT/'data/reference/belgium/infrabel-tracks-2026-06-15.json.gz'
GEOMETRY_SHA256='a47ee4aa503511e10a60f502ab510739859ec67ff8165cf39da2660a502d44d7'
RAIL_PRODUCTS={'100':{'L','S1','S2','S3','S4','S5','S7','S8','S9','S10','S19','S20',
    'S32','S33','S34','S35','S41','S42','S43','S44','S51','S52','S53','S61','S62','S63','S64'},
    '103':{'IC','P','T','TRN','EXT','EC','OTC'},'101':{'NJ'}}
# SunTrain category colours, not purported official line colours.
COLORS={'IC':'005CA9','L':'007F8B','P':'8A3B8F','EC':'534F96','NJ':'253B73','T':'39844A'}
SOURCE={
    'name':'Belgium','first':'2026-06-01','last':'2026-06-07','timezone':'Europe/Brussels',
    'captured':'2026-05-31','published':'2026-05-30',
    'url':'https://gtfs.flatturtle.cloud/sncb-nmbs/sncb-nmbs-gtfs_2026-05-31.zip',
    'sha256':'237bd2286cac3b4d79d5caecbfb3716ea2c65fdf368904c2f0c08a71a0248b05',
    'source':'SNCB/NMBS historical GTFS via FlatTurtle archive',
    'source_url':'https://data.belgianmobility.io/en/data.html',
    'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
    'attribution':'Source: NMBS/SNCB – Open Data – 2026-05-30 · archived by FlatTurtle 31 May 2026. Historical selection and railway matching by SunTrain. Track alignments: Infrabel · CC0 1.0.',
    'assign_by_start':['train'],'geometry_quality':'track',
    'geometry_source':'Infrabel · official railway track segments, matched and simplified by SunTrain',
    'geometry_source_url':'https://opendata.infrabel.be/explore/dataset/geografische-positie-van-alle-spoorsegmenten/',
    'geometry_license':'CC0 1.0','geometry_license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
    'geometry_source_date':'Portal processed 15 June 2026; accessed 19 October 2026 Australia/Melbourne',
    'note':'SNCB/NMBS passenger trains throughout Belgium from an archived timetable, including IC, L, S and P services. International journeys retain Belgian/border-coded station portions and original times. Buses and urban transport are excluded. Tracks are inferred geographical alignments; unresolved sections remain gaps. Station-level stops are used rather than platform overrides. No live tracking or individual passenger counts.'}


def selected_route(route,agencies):
    return (route.get('agency_id')=='NMBS/SNCB'
            and agencies.get('NMBS/SNCB',{}).get('agency_name')=='NMBS/SNCB'
            and route.get('route_short_name') in RAIL_PRODUCTS.get(route.get('route_type'),set()))


def domestic_sequence(sequence):
    indices=[i for i,row in enumerate(sequence) if re.match(r'^88\d{5}(?:_|$)',row['stop_id'])]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def prepare(cache,output,geometry=GEOMETRY):
    if file_hash(geometry)!=GEOMETRY_SHA256:
        raise ValueError('Infrabel railway geometry differs from the validated reference')
    with gzip.open(geometry,'rt') as stream:geographic=json.load(stream)
    numbers,destinations,audit={},{},Counter()
    def select(sequence,stops):
        clipped=domestic_sequence(sequence)
        if clipped:
            audit['included_candidates']+=1
            if len(clipped)<len(sequence):audit['clipped_candidates']+=1
            destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
        else:audit['outside_belgian_scope_or_single_call']+=1
        return clipped
    def describe(route,trip):
        short=route['route_short_name'];numbers[trip['trip_id']]=trip.get('trip_short_name','')
        return {'mode':'train','route_id':route['route_id'],'route_short_name':short,'category':short,
                'line':short+' · '+route['route_long_name'].replace(' -- ',' ↔ '),
                'direction':'Not specified','destination':destinations[trip['trip_id']],
                'color':route.get('route_color') or ('3C9FC7' if short.startswith('S') else COLORS.get(short,'465D79'))}
    prepare_rail('belgium',{**SOURCE,'geometry_sha256':GEOMETRY_SHA256,
                 'geometry_references':[geographic['metadata']]},cache,output,selected_route,describe,
                 geometry_resolver=geometry_resolver(geographic),select_sequence=select)
    with gzip.open(output,'rt') as stream:result=json.load(stream)
    used={t for rows in result['days'].values() for _,t,_ in rows}
    result['train_numbers']={t:n for t,n in numbers.items() if n and t in used}
    result['metadata']['scope_audit']=dict(audit)
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'scope',dict(audit),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/belgium')
    parser.add_argument('--geometry',type=Path,default=GEOMETRY)
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/belgium/2026-06-01.json.gz')
    args=parser.parse_args();prepare(args.cache,args.output,args.geometry)
