"""Add Luxtram T1 to Luxembourg's 1–7 June 2026 historical replay."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compact_transit import merge_references,save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_luxembourg_replay import SOURCE as TRAINS,prepare as prepare_trains
from scripts.prepare_portugal_replay import geometry_resolver
from scripts.prepare_rail_replay import prepare as prepare_rail
GEOMETRY=ROOT/'data/reference/luxembourg/luxtram-osm-2026-10-19.json.gz'
GEOMETRY_SHA256='15ef3ea6a83e7410166725346dc72826961e6ed0fc3d4d65a00cfbc7add6e577'
NOTE='Luxembourg passenger trains and Luxtram T1 from the official May 2026 archive. Original schedules and overnight calls are retained. Trains use national/border portions; unsupported paths remain gaps. Buses are excluded. No individual passenger loads.'
SOURCE={**TRAINS,'assign_by_start':['tram'],'source':'Administration des transports publics · historical Luxtram T1 schedules',
    'geometry_source':'© OpenStreetMap contributors via Geofabrik Luxembourg; tram tracks selected, matched and simplified by SunTrain',
    'geometry_source_url':'https://download.geofabrik.de/europe/luxembourg.html','geometry_sha256':GEOMETRY_SHA256,
    'geometry_source_date':'Extract retrieved 2026-10-19; geographic reference for June 2026 schedules',
    'geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
    'attribution':'Luxtram schedules: Administration des transports publics, Luxembourg, CC BY 4.0, archived 28 May 2026. Tram geometry: © OpenStreetMap contributors via Geofabrik, retrieved 19 October 2026, ODbL 1.0; selected, matched and simplified by SunTrain.',
    'note':NOTE}


def selected_route(route,agencies):
    return (route.get('agency_id')=='111' and agencies.get('111',{}).get('agency_name')=='Luxtram'
        and route.get('route_type')=='0' and route.get('route_short_name')=='T1')


def describe_route(route,trip):
    return {'mode':'tram','operator':'Luxtram','route_id':route['route_id'],'route_short_name':'T1','category':'T1',
        'line':'T1 · Luxtram','color':'A6B727','direction':'Direction '+{'0':'A','1':'B'}.get(trip.get('direction_id'),'unknown')}


def prepare(cache,output):
    if file_hash(GEOMETRY)!=GEOMETRY_SHA256:raise ValueError('Luxtram railway geometry differs from the validated reference')
    with gzip.open(GEOMETRY,'rt') as f:geographic=json.load(f)
    trains=cache/'trains-week.json.gz';prepare_trains(cache,trains)
    tram=cache/'tram-week.json.gz'
    prepare_rail('lu-tram',SOURCE,cache,tram,selected_route,describe_route,geometry_resolver=geometry_resolver(geographic))
    with gzip.open(trains,'rt') as f:train_reference=json.load(f)
    with gzip.open(tram,'rt') as f:tram_reference=json.load(f)
    result=merge_references([('lu-rail',train_reference),('lu-tram',tram_reference)],
        source_name='Luxembourg passenger trains and Luxtram historical schedules',replay_note=NOTE)
    # Both selections use the exact same original national timetable archive.
    result['metadata']['sources']=train_reference['metadata']['sources']
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/luxembourg')
    p.add_argument('--output',type=Path,default=ROOT/'data/reference/luxembourg/2026-06-01.json.gz')
    a=p.parse_args();prepare(a.cache,a.output)
