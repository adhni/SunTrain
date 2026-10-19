"""Prepare nationwide Swiss passenger trains for 1–7 June 2026."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta
import gzip
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY = ROOT / 'data/reference/switzerland/osm-rail-2026-10-17.json.gz'
GEOMETRY_SHA256 = '91cff97a89179fea8831fadae15215d98dfd224ca515cc18e4aec211799012ab'
OPERATORS = json.loads((ROOT / 'data/reference/switzerland/rail-operators.json').read_text())
# Extended route types paired with the publisher's actual rail products.
# Do not accept arbitrary numeric ranges (e.g. car shuttles or replacement buses).
RAIL_TYPES = {'100': {'ZUG'}, '101': {'TGV'}, '102': {'IC','EC','ICE','RJX'},
              '103': {'IR'}, '105': {'NJ'}, '106': {'R','RB','RE','TER'},
              '107': {'PE'}, '109': {'S','SN'}, '116': {'CC'}, '117': {'EXT'}}
COLORS = {'11':'EB0000','33':'006F53','82':'C8102E','72':'D50032','48':'C8102E','93':'C8102E',
          '65':'007E8A','86':'E50019','64':'B79B60'}
SOURCE = {
    # The official archive declares Europe/Berlin for all agencies. Its clock
    # matches Europe/Zurich throughout this week; the application uses Zurich.
    'name':'Switzerland','first':'2026-06-01','last':'2026-06-07','timezone':'Europe/Berlin',
    'captured':'2026-05-30','published':'2026-06-01',
    'url':'https://data.opentransportdata.swiss/dataset/3d2c18f9-9ef1-463f-a249-5c67604efd74/resource/caf12531-948a-4683-91d8-fc63167e4da2/download/gtfs_fp2026_20260530.zip',
    'sha256':'c50a50f8673303bc05ed1dbb602736484d5f107452221a2ad397f1a4a088f146',
    'source':'Historical Swiss nationwide passenger timetable · opentransportdata.swiss / SKI',
    'source_url':'https://data.opentransportdata.swiss/en/dataset/timetable-2026-gtfs2020',
    'license':'opentransportdata.swiss Open Data terms (attribution required)',
    'license_url':'https://opentransportdata.swiss/en/terms-of-use/',
    'attribution':'Timetables: opentransportdata.swiss / SKI · GTFS version 20260530, published 1 June 2026. Historical selection, matching and simplification by SunTrain. Railway geography © OpenStreetMap contributors via Geofabrik.',
    'assign_by_start':['train'],'geometry_quality':'track',
    'geometry_source':'© OpenStreetMap contributors · Geofabrik Switzerland, matched and simplified by SunTrain',
    'geometry_source_url':'https://www.openstreetmap.org/copyright',
    'geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
    'geometry_source_date':'2026-10-17; geographic reference for June timetables',
    'note':'Passenger trains across Switzerland, including regional, S-Bahn, narrow-gauge and rack railways represented in the archived timetable. International journeys retain Swiss/border-coded station portions and original times. Metros, trams, buses, funiculars and cableways are excluded. Railway paths are inferred geographical alignments; unresolved sections remain gaps. Historical schedules, not live positions or exact running-track records. No individual passenger loads.'}


def selected_route(route, agencies):
    agency = route.get('agency_id')
    return (route.get('route_desc') in RAIL_TYPES.get(route.get('route_type'), set())
            and agency in OPERATORS and agencies.get(agency,{}).get('agency_name') == OPERATORS[agency])


def domestic_sequence(sequence):
    # This May snapshot uses seven-digit UIC/DiDok IDs plus optional platform suffixes.
    indices = [i for i,row in enumerate(sequence) if re.match(r'^85\d{5}(?::|$)',row['stop_id'])]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def geometry_resolver(geographic):
    # Reuse France's indexed, station-local 150 m anchoring and native-ID routing.
    graph = FranceRailGraph(geographic['ways'])
    def resolve(route, trip, sequence, coordinates):
        curves = []
        for a,b in zip(coordinates,coordinates[1:]):
            curve = graph.leg(a,b)
            if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([a,b])[-1]):
                curve = None
            curves.append(curve)
        return curves
    return resolve


def prepare(cache, output, geometry=GEOMETRY):
    if file_hash(geometry)!=GEOMETRY_SHA256:
        raise ValueError('Swiss railway geometry differs from the validated reference')
    with gzip.open(geometry,'rt') as stream:
        geographic=json.load(stream)
    first,last=date.fromisoformat(SOURCE['first']),date.fromisoformat(SOURCE['last'])
    for i in range(-1,(last-first).days+2):
        day=first+timedelta(days=i)
        if datetime.combine(day,time(12),ZoneInfo(SOURCE['timezone'])).utcoffset()!=datetime.combine(day,time(12),ZoneInfo('Europe/Zurich')).utcoffset():
            raise ValueError('Source timezone differs from the Swiss replay clock')
    numbers, destinations, audit = {}, {}, Counter()
    def select(sequence,stops):
        clipped=domestic_sequence(sequence)
        if clipped:
            audit['included_candidates']+=1
            if len(clipped)<len(sequence):audit['clipped_candidates']+=1
            destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
        else:audit['outside_swiss_scope_or_single_call']+=1
        return clipped
    def describe(route,trip):
        numbers[trip['trip_id']]=trip.get('trip_short_name','')
        agency=route['agency_id']; name=route.get('route_short_name') or route['route_desc']
        return {'mode':'train','route_id':route['route_id'],'route_short_name':name,
                'category':route['route_desc'],'line':name+' · '+OPERATORS[agency],
                'direction':'Direction '+{'0':'A','1':'B'}.get(trip.get('direction_id'),'unknown'),
                'destination':destinations[trip['trip_id']],
                'color':route.get('route_color') or COLORS.get(agency,'465D79')}
    prepare_rail('switzerland',{**SOURCE,'geometry_sha256':GEOMETRY_SHA256,
                 'geometry_references':[geographic['metadata']]},cache,output,selected_route,describe,
                 geometry_resolver=geometry_resolver(geographic),select_sequence=select)
    with gzip.open(output,'rt') as stream:result=json.load(stream)
    used={t for rows in result['days'].values() for _,t,_ in rows}
    result['train_numbers']={t:n for t,n in numbers.items() if n and t in used}
    result['metadata']['scope_audit']=dict(audit)
    result['metadata'].update(timezone='Europe/Zurich',feed_timezone=SOURCE['timezone'])
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'scope',dict(audit),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/switzerland')
    parser.add_argument('--geometry',type=Path,default=GEOMETRY)
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/switzerland/2026-06-01.json.gz')
    args=parser.parse_args();prepare(args.cache,args.output,args.geometry)
