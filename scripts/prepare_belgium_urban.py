"""Add Belgian metro, tram and light-rail schedules for 1–7 June 2026."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.compact_transit import save_reference
from scripts.prepare_rail_replay import prepare as prepare_rail

BASE={'first':'2026-06-01','last':'2026-06-07','timezone':'Europe/Brussels',
    'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
    'source_url':'https://data.belgianmobility.io/en/data.html','assign_by_start':['subway','tram'],
    'geometry_method':'native_or_ordered_per_leg','geometry_quality':'shape',
    'geometry_source':'Official operator GTFS route shapes, selected by SunTrain',
    'geometry_source_url':'https://data.belgianmobility.io/en/data.html',
    'geometry_license':'CC BY 4.0','geometry_license_url':'https://creativecommons.org/licenses/by/4.0/',
    'note':'Historical Belgian metro/tram schedules and operator route shapes. Only rail route types are selected; buses and replacement buses are excluded. Positions are schedule estimates, not GPS. No individual passenger loads.'}
SOURCES={
    'stib-mivb':{**BASE,'captured':'2026-05-31','published':'2026-05-25',
        'url':'https://gtfs.flatturtle.cloud/stib-mivb/stib-mivb-gtfs_2026-05-31.zip',
        'sha256':'abb7e03497c3f61a1e7f92651a59b181a3e21ae606145fdd7f056e83d0941fb4',
        'source':'STIB-MIVB historical metro and tram GTFS via FlatTurtle',
        'attribution':'Source: STIB-MIVB – Open Data – 2026-05-25 · archived 31 May 2026; selected and processed by SunTrain.'},
    'delijn':{**BASE,'captured':'2026-05-31','published':'2026-05-30',
        'url':'https://gtfs.flatturtle.cloud/delijn/delijn-gtfs_2026-05-31.zip',
        'sha256':'51f2a28e44d8f9a3d5bd9b36b7ac66992d638bec8b46d873015acae1f2cb3baa',
        'source':'De Lijn historical tram GTFS via FlatTurtle',
        'attribution':'Source: De Lijn – Open Data – 2026-05-30 · archived 31 May 2026; selected and processed by SunTrain.'},
    'tec':{**BASE,'captured':'2026-05-30','published':'','calendar_validity':True,
        'url':'https://gtfs.flatturtle.cloud/tec/tec-gtfs_2026-05-30.zip',
        'sha256':'b887f24fc1164a05be272fc7fdfb0957ebe988aab1fef6f5578e3a8eef95007f',
        'source':'LETEC historical Charleroi metro and Liège tram GTFS via FlatTurtle',
        'attribution':'Source: LETEC – Open Data – archive 2026-05-30 (publisher revision unspecified); selected and processed by SunTrain.'}}
OPERATORS={'stib-mivb':{'STIB/MIVB':'STIB'},'delijn':{'delijn':'De Lijn'},
           'tec':{'C':'TEC Charleroi','L':'TEC Liège - Verviers'}}


def selected_route(feed,route,agencies):
    agency=route.get('agency_id');operators=OPERATORS[feed]
    if agency not in operators or agencies.get(agency,{}).get('agency_name')!=operators[agency]:return False
    kind=route.get('route_type');short=route.get('route_short_name')
    if feed=='stib-mivb':return kind=='0' or kind=='1' and short in {'1','2','5','6'}
    if feed=='delijn':return kind=='0'
    return (agency=='C' and kind=='1' and short in {'M2','M3','M4'}
            or agency=='L' and kind=='0' and short=='T1')


def describe_route(feed,route,trip):
    short=route['route_short_name'];mode='subway' if route['route_type']=='1' else 'tram'
    if feed=='stib-mivb':
        label='Brussels '+('Metro ' if mode=='subway' else 'Tram ')+short;operator='STIB-MIVB';color=route['route_color']
    elif feed=='delijn':
        city={'1':'Antwerp','2':'Ghent','5':'Coastal'}[route['route_id'][0]]
        label=city+' Tram '+short;operator='De Lijn';color=route['route_color']
    else:
        label=('Charleroi ' if mode=='subway' else 'Liège Tram ')+short
        operator=OPERATORS[feed][route['agency_id']];color='007F8B' if mode=='subway' else '8A3B8F'
    return {'mode':mode,'operator':operator,'route_id':route['route_id'],'route_short_name':short,
            'line':label,'color':color,'direction':'Direction '+{'0':'A','1':'B'}.get(trip.get('direction_id'),'unknown')}


def merge_references(references):
    """Combine compact feeds with namespaced IDs and remapped station indices."""
    result={'metadata':dict(references[0][1]['metadata']),'stations':[],'patterns':{},
            'stop_patterns':{},'paths':{},'days':{d:[] for d in references[0][1]['days']},'train_numbers':{}}
    for namespace,r in references:
        if set(r['days'])!=set(result['days']):raise ValueError('Belgian feed dates differ')
        offset=len(result['stations']);result['stations'].extend(r['stations']);prefix=namespace+':'
        result['patterns'].update({prefix+k:{**p,'route_id':prefix+p['route_id'],
            'stop_pattern':prefix+p['stop_pattern']} for k,p in r['patterns'].items()})
        result['stop_patterns'].update({prefix+k:{'stations':[s+offset for s in p['stations']],
            'legs':[prefix+leg for leg in p['legs']]} for k,p in r['stop_patterns'].items()})
        result['paths'].update({prefix+k:p for k,p in r['paths'].items()})
        for day,rows in r['days'].items():
            result['days'][day].extend([[prefix+k,prefix+t,o] for k,t,o in rows])
        for rows in r['days'].values():
            for _,t,_ in rows:result['train_numbers'][prefix+t]=r.get('train_numbers',{}).get(t,t)
    schedules=[r['metadata'] for _,r in references]
    geometry_sources=[]
    for m in schedules[1:]:
        credit={k:m[k] for k in ['geometry_source','geometry_source_url','geometry_license','geometry_license_url']}
        if credit not in geometry_sources:geometry_sources.append(credit)
    result['metadata'].update(
        source='Belgian historical trains, metros and trams',
        sources=[s for m in schedules for s in m['sources']],
        attribution=' '.join(m['attribution'] for m in schedules),
        additional_geometry_sources=geometry_sources,
        omitted_trips={namespace:r['metadata']['omitted_trips'] for namespace,r in references if r['metadata']['omitted_trips']},
        unresolved_geometry_patterns=dict(sum((Counter(m['unresolved_geometry_patterns']) for m in schedules),Counter())),
        unresolved_geometry_trips={namespace+':'+t:v for namespace,r in references for t,v in r['metadata']['unresolved_geometry_trips'].items()},
        replay_note='Belgian trains, Brussels metro/trams, Antwerp/Ghent/coastal trams, Charleroi light rail and Liège tram. Select Trams under Transport to include tram networks. Buses are excluded. Historical schedules and inferred paths; unresolved movement stays hidden between stops. No individual passenger loads.')
    for day,rows in result['days'].items():
        if len({(t,o) for _,t,o in rows})!=len(rows):raise ValueError('Duplicate Belgian occurrence IDs')
        rows.sort(key=lambda row:(row[2],row[1]))
    result['metadata']['daily_services']={d:dict(Counter(result['patterns'][k]['mode'] for k,_,_ in rows)) for d,rows in result['days'].items()}
    return result


def prepare(cache,output):
    # Rebuild the national source separately before merging; never merge a
    # previously combined file back into itself.
    from scripts.prepare_belgium_replay import prepare as prepare_national, SOURCE as NATIONAL, GEOMETRY_SHA256
    national_cache=cache/'be-nmbs-week.json.gz'
    valid=False
    if national_cache.exists():
        with gzip.open(national_cache,'rt') as stream:old=json.load(stream)
        valid=(old['metadata']['sources'][0]['sha256']==NATIONAL['sha256']
               and old['metadata']['geometry_sha256']==GEOMETRY_SHA256
               and old['metadata']['start_date']==BASE['first'] and old['metadata']['end_date']==BASE['last'])
    if not valid:prepare_national(cache,national_cache)
    with gzip.open(national_cache,'rt') as stream:references=[('be-nmbs',json.load(stream))]
    for feed,source in SOURCES.items():
        target=cache/(feed+'-week.json.gz');numbers={}
        def describe(route,trip):
            numbers[trip['trip_id']]=trip.get('trip_short_name') or trip['trip_id']
            return describe_route(feed,route,trip)
        prepare_rail('be-'+feed,source,cache,target,
            lambda route,agencies:selected_route(feed,route,agencies),describe)
        with gzip.open(target,'rt') as stream:r=json.load(stream)
        r['train_numbers']=numbers;references.append(('be-'+feed,r))
        print(feed,'days',{d:len(rows) for d,rows in r['days'].items()},flush=True)
    save_reference(merge_references(references),output)
    print('Saved combined Belgium',output.stat().st_size,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/belgium')
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/belgium/2026-06-01.json.gz')
    args=parser.parse_args();prepare(args.cache,args.output)
