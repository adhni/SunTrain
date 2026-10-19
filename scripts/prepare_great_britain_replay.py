"""Prepare Great Britain's intercity and optional regional/commuter trains from dated National Rail GTFS."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
import math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_replay import file_hash,records
from scripts.prepare_rail_replay import prepare as prepare_rail,TimetableArchive
from scripts.prepare_france_replay import FranceRailGraph
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
GEOMETRY=ROOT/'data/reference/great_britain/rail-osm-2026-10-19.json.gz'
GEOMETRY_SHA256='ea5698742e8c5e164f52d5d7b7ad1f0b3ed08fc3d05d1f6abbd29550fb1c1ccc'
OPERATORS={'GR':'LNER','VT':'Avanti West Coast','GW':'GWR','XC':'CrossCountry','EM':'EMR',
    'TP':'TransPennine Express','LD':'Lumo (East Coast)','LF':'Lumo (West Coast)','HT':'Hull Trains','GC':'Grand Central'}
# Route IDs differ from agency IDs for the West Midlands brands, Stansted
# Express and Merseyrail's two networks. Match both identities explicitly.
REGIONAL_ROUTES={
    'NT':('NT','Northern Rail'), 'SR':('SR','ScotRail'), 'AW':('AW','Transport for Wales'),
    'LE':('LE','Greater Anglia'), 'SX':('LE','Greater Anglia'),
    'LN':('LM','West Midlands Trains'), 'WM':('LM','West Midlands Trains'),
    'SW':('SW','South Western Railway'), 'SE':('SE','Southeastern'), 'SN':('SN','Southern'),
    'TL':('TL','Thameslink'), 'GN':('GN','Great Northern'), 'CC':('CC','c2c'),
    'CH':('CH','Chiltern Railways'), 'ME_Northern':('ME','Merseyrail'), 'ME_Wirral':('ME','Merseyrail')}
REGIONAL_NOTE='Regional and commuter trains from 5–11 October 2026 schedules. London Overground, Elizabeth line and other TfL networks use the existing London replay and are excluded here. Remaining GWR/EMR local services and Caledonian Sleeper are not included. Paths are inferred railway alignments; unsupported legs remain gaps. No individual passenger counts.'
GWR_INTERCITY={'SWI','BTH','BRI','BPW','CDF','SWA','EXD','PLY','PNZ','HFD','WOS','CNM','GCR','CMN','PGN','NTA'}
EMR_INTERCITY={'LEI','DBY','NOT','SHF'}
NOTE='Initial Great Britain long-distance/intercity corridors for 5–11 October 2026. GWR and EMR use explicit mainline corridor selection because the converted feed does not identify train categories. Select Regional / commuter rail to include the added operators. Remaining GWR/EMR local services and Caledonian Sleeper are excluded. Existing London networks stay in the London replay. Original times retained; railway paths are inferred, with unsupported legs hidden. No live tracking or individual passenger counts.'
SOURCE={'name':'Great Britain','first':'2026-10-05','last':'2026-10-11','timezone':'Europe/London',
    'captured':'2026-10-04','published':'2026-10-04',
    'url':'https://github.com/planarnetwork/gb-transit/releases/download/feed-2026-10-04/gtfs-rail-and-tfl.zip',
    'sha256':'7bc0854bbc6d5206bfdd51a0e77a7bb1b3af8c627c360e2c5b0823fb03a7c5b7',
    'source_url':'https://github.com/planarnetwork/gb-transit/releases/tag/feed-2026-10-04',
    'license_url':'https://planarnetwork.github.io/gb-transit/feeds/using-this-data/#sources-and-licences',
    'geometry_quality':'track','geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
    'assign_by_start':['train'],
    'source':'RDG / Rail Settlement Plan National Rail timetable, converted by Planar Network, 4 October 2026 archive',
    'license':'Rail Settlement Plan timetable terms; NaPTAN OGL v3.0',
    'attribution':'National Rail timetable data © Rail Delivery Group / Rail Settlement Plan. Station names and coordinates: DfT NaPTAN, contains public sector information licensed under the Open Government Licence v3.0. GTFS conversion by Planar Network. No National Rail Enquiries station facilities/accessibility fields reproduced. Railway geography © OpenStreetMap contributors, ODbL 1.0; matched and simplified by SunTrain.',
    'geometry_source':'© OpenStreetMap contributors via Geofabrik Great Britain',
    'geometry_source_url':'https://download.geofabrik.de/europe/great-britain.html',
    'geometry_source_date':'OSM data through 18 October 2026; geographic reference, not historical running-track records',
    'note':NOTE}


def selected_route(route,agencies,regional=False):
    if regional:
        audited=REGIONAL_ROUTES.get(route.get('route_id'))
        return bool(audited and route.get('route_type')=='2' and route.get('agency_id')=='='+audited[0]
            and agencies.get('='+audited[0],{}).get('agency_name')==audited[1])
    code=route.get('route_id')
    return (code in OPERATORS and route.get('route_type')=='2' and route.get('agency_id')=='='+code
        and agencies.get('='+code,{}).get('agency_name')==OPERATORS[code])


def intercity_sequence(code,sequence,stops):
    """Conservative corridor scope, not a claim of official train classification."""
    codes={stops[r['stop_id']].get('stop_code') for r in sequence}
    if code=='GW' and not ('PAD' in codes and bool(codes&GWR_INTERCITY)):return []
    if code=='EM' and not (('STP' in codes and bool(codes&EMR_INTERCITY)) or len(codes&EMR_INTERCITY)>=2):return []
    return sequence if len(sequence)>=2 else []


def describe_route(route,trip,regional=False):
    if regional:
        code=route['route_id'];name=REGIONAL_ROUTES[code][1]
        line=route.get('route_long_name') or name+' '+route.get('route_short_name','')
        return {'mode':'regional_rail','route_id':code,'line':line.strip(),'direction':'Not specified','operator':name}
    code=route['route_id']
    return {'mode':'train','route_id':code,'line':route['route_long_name'],
        'direction':'Not specified','operator':OPERATORS[code]}


class BritainRailGraph(FranceRailGraph):
    """Use a stable track anchor so consecutive waypoint paths stay connected."""
    def __init__(self,ways):
        super().__init__(ways)
        remaining=set(self.nodes);largest=set()
        while remaining:
            first=remaining.pop();component={first};queue=[first]
            while queue:
                for neighbour,_ in self.neighbours[queue.pop()]:
                    if neighbour in remaining:
                        remaining.remove(neighbour);component.add(neighbour);queue.append(neighbour)
            if len(component)>len(largest):largest=component
        self.mainland=largest
        self.fixed_anchors={};self.flexible=False

    def anchors(self,point):
        if self.flexible:return super().anchors(point)
        key=tuple(point)
        if key not in self.fixed_anchors:
            candidates=super().anchors(point)
            self.fixed_anchors[key]=[a for a in candidates if self.edges[a[0]][0] in self.mainland][:1]
        return self.fixed_anchors[key]


def follows_hints(curve,hints):
    """Reject a flexible endpoint match that bypasses its documented corridor."""
    points=np.asarray(curve,dtype=float)
    for hint in hints:
        scale=np.array([math.cos(math.radians(hint[1])),1.0])*111195
        starts=(points[:-1]-hint)*scale;vectors=np.diff(points,axis=0)*scale
        fractions=np.clip(-np.sum(starts*vectors,axis=1)/np.maximum(np.sum(vectors*vectors,axis=1),1e-20),0,1)
        if np.min(np.linalg.norm(starts+fractions[:,None]*vectors,axis=1))>400:return False
    return True


def geometry_resolver(geographic,shapes):
    graph=BritainRailGraph(geographic['ways']);fallbacks={}
    def resolve(route,trip,sequence,coordinates):
        # Shapes are only ordered station/passing-point hints. Every displayed
        # metre comes from the connected track graph, never from the sketch.
        hints=shapes.get(trip.get('shape_id'),[])
        indices=[];cursor=0
        for point in coordinates:
            candidates=[i for i in range(cursor,len(hints)) if cumulative_distances([point,hints[i]])[-1]<=150]
            if not candidates:indices=[];break
            index=min(candidates,key=lambda i:cumulative_distances([point,hints[i]])[-1])
            indices.append(index);cursor=index+1
        curves=[]
        for i,(a,b) in enumerate(zip(coordinates,coordinates[1:])):
            waypoints=[a,*hints[indices[i]+1:indices[i+1]],b] if indices else [a,b]
            # Unlocatable passing hints may be omitted; actual scheduled calls
            # must still anchor within 150 m. Never draw a connector to a hint.
            waypoints=[p for j,p in enumerate(waypoints) if j in {0,len(waypoints)-1} or graph.anchors(p)]
            combined=[]
            for start,end in zip(waypoints,waypoints[1:]):
                curve=graph.leg(start,end)
                if not curve or cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([start,end])[-1]):
                    combined=[];break
                if combined and combined[-1]!=curve[0]:
                    raise ValueError('Waypoint track paths do not join at their shared anchor')
                combined.extend(curve if not combined else curve[1:])
            if not combined:
                # Grade-separated interchanges (e.g. Tamworth) can have more
                # than one valid station track. Try flexible endpoint anchors
                # only when the resulting single track curve follows the same
                # passing-point corridor. Never connect two projected tracks.
                key=(tuple(a),tuple(b),tuple(map(tuple,waypoints)))
                if key not in fallbacks:
                    graph.flexible=True
                    try:curve=graph._leg(a,b)
                    finally:graph.flexible=False
                    fallbacks[key]=curve if curve and follows_hints(curve,waypoints) and cumulative_distances(curve)[-1]<=max(5000,3*cumulative_distances([a,b])[-1]) else None
                combined=fallbacks[key]
            curves.append(combined or None)
        return curves
    return resolve


def prepare(cache,output,geometry=GEOMETRY,regional=False):
    if file_hash(geometry)!=GEOMETRY_SHA256:raise ValueError('GB railway geometry differs from the validated reference')
    with gzip.open(geometry,'rt') as f:geographic=json.load(f)
    filename=cache/'gtfs-rail-and-tfl.zip'
    if not filename.exists():
        from scripts.prepare_boston_replay import fetch
        fetch(SOURCE['url'],filename)
    if file_hash(filename)!=SOURCE['sha256']:raise ValueError('GB timetable differs from the validated archive')
    with TimetableArchive(filename) as archive:
        trips={t['trip_id']:t for t in records(archive,'trips.txt') if t['route_id'] in (REGIONAL_ROUTES if regional else OPERATORS)}
        needed={t['shape_id'] for t in trips.values()};raw={}
        for row in records(archive,'shapes.txt'):
            if row['shape_id'] in needed:raw.setdefault(row['shape_id'],[]).append((int(row['shape_pt_sequence']),[float(row['shape_pt_lon']),float(row['shape_pt_lat'])]))
        shapes={k:[p for _,p in sorted(rows)] for k,rows in raw.items()}
    audit=Counter();numbers={}
    def select(sequence,stops):
        trip=trips[sequence[0]['trip_id']] if sequence else None
        selected=(sequence if regional and len(sequence)>=2 else intercity_sequence(trip['route_id'],sequence,stops)) if trip else []
        audit['included_candidates' if selected else 'outside_intercity_corridors']+=1
        if selected:numbers[trip['trip_id']]=trip.get('trip_short_name') or trip['trip_id'].split('_')[0]
        return selected
    source={**SOURCE,'geometry_sha256':GEOMETRY_SHA256}
    if regional:source.update(assign_by_start=['regional_rail'],note=REGIONAL_NOTE)
    namespace='gb-regional' if regional else 'great_britain'
    prepare_rail(namespace,source,cache,output,
        lambda r,a:selected_route(r,a,regional),lambda r,t:describe_route(r,t,regional),
        geometry_resolver=geometry_resolver(geographic,shapes),select_sequence=select,daily=regional)
    outputs=sorted(output.glob('*.json.gz')) if regional else [output]
    for target in outputs:
        with gzip.open(target,'rt') as f:result=json.load(f)
        needed={t for rows in result['days'].values() for p,t,o in rows}
        result['train_numbers']={t:n for t,n in numbers.items() if t in needed}
        result['metadata']['scope_audit']=dict(audit)
        if regional:
            prefix='gb-rv-'
            result['stop_patterns']={prefix+k:v for k,v in result['stop_patterns'].items()}
            result['patterns']={prefix+k:{**v,'stop_pattern':prefix+v['stop_pattern']} for k,v in result['patterns'].items()}
            result['days']={d:[[prefix+k,t,o] for k,t,o in rows] for d,rows in result['days'].items()}
        save_reference(result,target)
        print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',target.stat().st_size,flush=True)



if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/great-britain')
    p.add_argument('--output',type=Path);p.add_argument('--regional',action='store_true')
    a=p.parse_args();output=a.output or ROOT/('data/reference/great_britain/regional_rail' if a.regional else 'data/reference/great_britain/2026-10-05.json.gz')
    prepare(a.cache,output,regional=a.regional)
