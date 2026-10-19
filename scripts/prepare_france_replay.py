"""Prepare French national trains and optional RER/Transilien for 1–7 June 2026."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_germany_replay import GermanRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY = ROOT / 'data/reference/france/sncf-tracks-2026-08-12.json.gz'
GEOMETRY_SHA256 = '3feb9511f650fd89407c3475ed487eb26c1099b6f7e10bd9c70fcc43dd2f419d'
NATIONAL_AGENCIES = {'1187': 'SNCF VOYAGEURS', '5111': 'SNCF Voyageurs SA', '5235': 'SNCF Voyageurs EA',
                     '5270': 'SNCF Voyageurs LO', '5429': 'TMR SA', 'OCEdefault': 'OCEdefault'}
SUBURBAN_AGENCIES = {'IDFM:71': 'RER', 'IDFM:1046': 'Transilien'}
PRODUCTS = {'Train TER': 'TER', 'TGV INOUI': 'TGV INOUI', 'OUIGO': 'OUIGO', 'INTERCITES': 'Intercités',
            'INTERCITES de nuit': 'Intercités de nuit', 'ICE': 'ICE', 'Lyria': 'TGV Lyria', 'Train': 'Train', 'Navette': 'Navette'}
BASE = {'name': 'France', 'first': '2026-06-01', 'last': '2026-06-07', 'timezone': 'Europe/Paris',
    'captured': '2026-05-31', 'published': '2026-05-30', 'calendar_validity': True,
    'license': 'ODbL 1.0', 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
    'geometry_quality': 'track', 'geometry_source': 'SNCF Réseau · RFN track alignments, matched/simplified by SunTrain',
    'geometry_source_url': 'https://www.data.gouv.fr/datasets/fichier-de-formes-des-voies-du-reseau-ferre-national',
    'geometry_license': 'ODbL 1.0', 'geometry_license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
    'geometry_source_date': 'Track extraction 12 August 2026; accessed 19 October 2026 Australia/Melbourne',
    'attribution': 'Timetables: SNCF Voyageurs, SNCF Transilien / Île-de-France Mobilités · historical archives 31 May 2026. Track alignments: SNCF Réseau. Matched and simplified by SunTrain.',
    'assign_by_start': ['train', 'commuter_rail'],
    'note': 'French national passenger trains and optional RER/Transilien from historical May archives. National international trips retain their French/border-coded station portions and original times. Road services and trams are excluded, including coaches incorrectly supplied as rail. Railway paths are inferred from RFN track geometry; unresolved sections stay gaps, including many RER A/B central and outer sections and part of RER E. No actual train loads or live tracking.'}
NATIONAL = {**BASE,
    'url': 'https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services.clever-cloud.com/83582/83582.20260531.001627.736700.zip',
    'sha256': '678ff24f33098a357abdbd539974a693d3d920e9184db4f5c9f101a81b36b786',
    'source': 'SNCF Voyageurs historical GTFS via the French national transport data portal',
    'source_url': 'https://transport.data.gouv.fr/datasets/horaires-sncf'}
SUBURBAN = {**BASE,
    'url': 'https://transport-data-gouv-fr-resource-history-prod.cellar-c2.services.clever-cloud.com/67595/67595.20260531.181639.479952.zip',
    'sha256': 'c356e92b5e4d3a8f18c7be107779ee9eb7d9d35498b1d264e9e863b02c125cf2',
    'published': '2026-05-31', 'source': 'SNCF Transilien / Île-de-France Mobilités historical GTFS via the national portal',
    'source_url': 'https://transport.data.gouv.fr/datasets/horaires-des-lignes-transilien-1'}


class FranceRailGraph(GermanRailGraph):
    """Reuse connected rail routing, with indexed station-local distance checks."""
    def __init__(self, ways, fast=False):
        super().__init__(ways, fast=fast)
        self.geographic_starts = self.starts / self.scale
        self.geographic_vectors = self.vectors / self.scale
        self.grid = defaultdict(list)
        lower = np.floor((np.minimum(self.starts, self.starts+self.vectors)-200)/2000).astype(int)
        upper = np.floor((np.maximum(self.starts, self.starts+self.vectors)+200)/2000).astype(int)
        for i,(lo,hi) in enumerate(zip(lower,upper)):
            for x in range(lo[0],hi[0]+1):
                for y in range(lo[1],hi[1]+1):self.grid[x,y].append(i)

    def anchors(self, point):
        key = tuple(point)
        if key not in self.anchor_cache:
            projected = np.array(point)*self.scale
            cell = tuple(np.floor(projected/2000).astype(int))
            indices = np.asarray(self.grid.get(cell, []),dtype=int)
            scale = np.array([math.cos(math.radians(point[1])),1.0])*111195
            vectors = self.geographic_vectors[indices]*scale
            offset = (np.array(point)-self.geographic_starts[indices])*scale
            fractions = np.clip(np.sum(offset*vectors,axis=1)/np.maximum(np.sum(vectors**2,axis=1),1e-20),0,1)
            errors = np.linalg.norm(offset-fractions[:,None]*vectors,axis=1)
            candidates = sorted(np.where(errors<=150)[0],key=lambda j:(errors[j],indices[j]))[:16]
            self.anchor_cache[key] = [(int(indices[j]),float(fractions[j]),float(errors[j]),
                (self.geographic_starts[indices[j]]+fractions[j]*self.geographic_vectors[indices[j]]).tolist()) for j in candidates]
        return self.anchor_cache[key]


def selected_route(route, agencies, suburban=False):
    operators = SUBURBAN_AGENCIES if suburban else NATIONAL_AGENCIES
    return (route.get('route_type')=='2' and route.get('agency_id') in operators
            and agencies.get(route['agency_id'],{}).get('agency_name')==operators[route['agency_id']])


def product(stop_id):
    return stop_id[13:].rsplit('-',1)[0] if stop_id.startswith('StopPoint:OCE') else None


def french_stop(stop_id):
    match = re.search(r'(\d{8})$',stop_id)
    return bool(match and match[1].startswith('87'))


def national_sequence(sequence, route, audit):
    kinds = {product(row['stop_id']) for row in sequence}
    if len(kinds) != 1 or next(iter(kinds)) not in PRODUCTS:
        audit['non_rail_product'] += 1
        return []
    category = next(iter(kinds))
    if category == 'Navette' and not (route['route_short_name'] == 'A01' and route['route_long_name'] == 'Tours - Saint-Pierre NavettesTGV'):
        audit['unconfirmed_shuttle'] += 1
        return []
    indices = [i for i, row in enumerate(sequence) if french_stop(row['stop_id'])]
    if len(indices) < 2:
        audit['outside_french_scope_or_single_call'] += 1
        return []
    # Keep foreign intermediate calls and original times; never join over them.
    return sequence[indices[0]:indices[-1] + 1]


def geometry_resolver(geometry, descriptions):
    graphs = {}
    def resolve(route, trip, sequence, coordinates):
        category = descriptions[trip['trip_id']].get('product')
        fast = category in {'TGV INOUI','OUIGO','ICE','Lyria'}
        if fast not in graphs:graphs[fast]=FranceRailGraph(geometry['ways'],fast=fast)
        curves=[]
        for a,b in zip(coordinates,coordinates[1:]):
            curve=graphs[fast].leg(a,b)
            if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([a,b])[-1]):curve=None
            curves.append(curve)
        return curves
    return resolve


def merged_reference(references):
    first=references[0][1]
    result={'metadata':{**first['metadata'], 'source':'French national and suburban passenger railway schedules',
        'sources':[s for _,r in references for s in r['metadata']['sources']],
        'omitted_trips':{namespace:r['metadata']['omitted_trips'] for namespace,r in references if r['metadata']['omitted_trips']},
        'unresolved_geometry_by_source':{namespace:r['metadata']['unresolved_geometry_patterns'] for namespace,r in references},
        'unresolved_geometry_patterns':dict(sum((Counter(r['metadata']['unresolved_geometry_patterns']) for _,r in references), Counter())),
        'unresolved_geometry_trips':{t:v for _,r in references for t,v in r['metadata']['unresolved_geometry_trips'].items()},
        'native_anchor_patterns':sum(r['metadata']['native_anchor_patterns'] for _,r in references),
        'scope_audits':{namespace:r['metadata'].get('scope_audit',{}) for namespace,r in references}},
        'stations':[],'patterns':{},'stop_patterns':{},'paths':{},'days':{day:[] for day in first['days']}}
    for namespace,r in references:
        offset=len(result['stations']);result['stations'].extend(r['stations']);prefix=namespace+'-'
        result['patterns'].update({prefix+k:{**p,'stop_pattern':prefix+p['stop_pattern']} for k,p in r['patterns'].items()})
        result['stop_patterns'].update({prefix+k:{**p,'stations':[s+offset for s in p['stations']]} for k,p in r['stop_patterns'].items()})
        for k,p in r['paths'].items():
            if k in result['paths'] and p!=result['paths'][k]:raise ValueError('Path ID collision')
            result['paths'][k]=p
        for day,rows in r['days'].items():result['days'][day].extend([[prefix+k,t,o] for k,t,o in rows])
    for day,rows in result['days'].items():
        if len({(t,o) for _,t,o in rows})!=len(rows):raise ValueError('Duplicate cross-feed occurrence IDs')
        rows.sort(key=lambda row:(row[2],row[1]))
    result['metadata']['daily_services'] = {day:dict(Counter(result['patterns'][k]['route_id'] for k,_,_ in rows))
                                          for day,rows in result['days'].items()}
    return result


def prepare(cache,output,geometry=GEOMETRY):
    cache.mkdir(parents=True,exist_ok=True)
    if file_hash(geometry)!=GEOMETRY_SHA256:raise ValueError('French track geometry differs from the validated reference')
    with gzip.open(geometry,'rt') as f:geographic=json.load(f)
    references=[]
    for namespace,source,suburban in [('fr-sncf',NATIONAL,False),('fr-idfm',SUBURBAN,True)]:
        filename=fetch(source['url'],cache/source['url'].rsplit('/',1)[1])
        if file_hash(filename)!=source['sha256']:raise ValueError('France archive differs from its validated pin')
        descriptions={};numbers={};audit=Counter()
        with ZipFile(filename) as z:
            routes={r['route_id']:r for r in records(z,'routes.txt')}
            trips={r['trip_id']:r for r in records(z,'trips.txt')}
        def select(sequence,stops):
            if not sequence:return []
            trip_id=sequence[0]['trip_id'];route=routes[trips[trip_id]['route_id']]
            if suburban:
                clipped=sequence;label=('RER ' if route['agency_id']=='IDFM:71' else 'Transilien ')+route['route_short_name'];category=None
            else:
                clipped=national_sequence(sequence,route,audit)
                if not clipped:return []
                category=product(clipped[0]['stop_id'])
                name=route.get('route_long_name','').strip(' -')
                if not name:name=stops[clipped[0]['stop_id']]['stop_name']+' ↔ '+stops[clipped[-1]['stop_id']]['stop_name']
                short=route['route_short_name']
                label=PRODUCTS[category]+(' '+short if short and short!='INCONNU' else '')+' · '+name
                numbers[trip_id]=trips[trip_id].get('trip_headsign','')
            descriptions[trip_id]={'mode':'commuter_rail' if suburban else 'train','product':category,
                'route_id':route['route_id'],'route_short_name':route['route_short_name'],'line':label,
                'direction':'Direction '+{'0':'A','1':'B'}.get(trips[trip_id].get('direction_id'),'unknown'),
                'destination':stops[clipped[-1]['stop_id']]['stop_name'],
                'color':route.get('route_color') or ('0055A4' if suburban else '6F2C91')}
            audit['included_candidates']+=1
            return clipped
        def describe(route,trip):return descriptions[trip['trip_id']]
        weekly=cache/(namespace+'-week.json.gz')
        prepare_rail(namespace,{**source,'geometry_sha256':GEOMETRY_SHA256,'geometry_references':geographic['metadata']['references']},
            cache,weekly,lambda r,a:selected_route(r,a,suburban),describe,
            geometry_resolver=geometry_resolver(geographic,descriptions),select_sequence=select)
        with gzip.open(weekly,'rt') as f:r=json.load(f)
        r['metadata']['scope_audit']=dict(audit)
        r['train_numbers']=numbers
        references.append((namespace,r))
        print(namespace,'days',{d:len(rows) for d,rows in r['days'].items()},'scope',dict(audit),flush=True)
    merged=merged_reference(references)
    merged['train_numbers']={t:n for _,r in references for t,n in r.get('train_numbers',{}).items() if n}
    save_reference(merged,output)
    print('Saved',output,output.stat().st_size,'daily counts',{d:len(rows) for d,rows in merged['days'].items()},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/france')
    parser.add_argument('--geometry',type=Path,default=GEOMETRY)
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/france/2026-06-01.json.gz')
    args=parser.parse_args();prepare(args.cache,args.output,args.geometry)
