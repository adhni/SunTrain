"""Prepare Trenitalia, Trenord and Italo passenger trains for 5–11 October 2026."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
import re
import sys
import unicodedata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import merge_references,save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
GEOMETRY=ROOT/'data/reference/italy/rail-osm-2026-10-19.json.gz'
GEOMETRY_SHA256='611779b8a2037d68942437b0023bf720d59e63e30104a0e799c8177d2aae279d'
AGENCY='IT::Operator:05403151003:TRENITALIA:TRENITALIA'
PRODUCTS={'FR','FA','FB','IC','ICN','EC','EN','REG','RV','SFM','MET','EXP'}
COLORS={'FR':'C51D30','FA':'667889','FB':'7252A1','IC':'1E6E88','ICN':'253B73','EC':'5F4A9B','EN':'34478C',
        'REG':'16834B','RV':'247C97','SFM':'91602F','MET':'267875','EXP':'8C3B57'}
NOTE='Trenitalia, Trenord and Italo passenger trains from historical October 2026 schedules. Italian portions and intervening foreign calls retain original times. Paths are inferred railway alignments, not exact running tracks or historical diversions. Unsupported sections, including sea crossings, stay gaps. Other operators, metros, trams and buses are excluded. No individual passenger loads.'
BASE={'first':'2026-10-05','last':'2026-10-11','timezone':'Europe/Rome','calendar_validity':True,'assign_by_start':['train'],
    'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
    'geometry_quality':'track','geometry_source':'© OpenStreetMap contributors via Geofabrik Italy; selected, matched and simplified by SunTrain',
    'geometry_source_url':'https://download.geofabrik.de/europe/italy.html',
    'geometry_license':'ODbL 1.0','geometry_license_url':'https://opendatacommons.org/licenses/odbl/1-0/',
    'geometry_source_date':'Extract retrieved 2026-10-19; geographic reference for October schedules',
    'geometry_sha256':GEOMETRY_SHA256,'note':NOTE}
SOURCES={
 'trenitalia':{**BASE,'captured':'2026-10-05','published':'2026-09-25',
    'url':'https://raw.githubusercontent.com/deryclem/trenitalia-gtfs/5cb930e7d9c135ea857e13608ad1ba1ec658e344/gtfs-trenitalia.zip',
    'sha256':'42b1a0bfb5b13c303382bb756d45457ad6c96418fc22324122930e86bc528b18',
    'source':'Trenitalia / CCISS historical NeTEx, converted to GTFS by Clément Desouche (@deryclem)',
    'source_url':'https://github.com/deryclem/trenitalia-gtfs/tree/5cb930e7d9c135ea857e13608ad1ba1ec658e344',
    'attribution':'Trenitalia S.p.A. / CCISS MMTIS original NeTEx, publication 25 September 2026. GTFS conversion © 2026 Clément Desouche (@deryclem), CC BY 4.0, archived commit 5 October 2026. Historical selection and railway matching by SunTrain. Geography © OpenStreetMap contributors, ODbL 1.0.'},
 'trenord':{**BASE,'captured':'2026-08-04','published':'',
    'url':'https://files.mobilitydatabase.org/mdb-855/mdb-855-202608040032/mdb-855-202608040032.zip',
    'sha256':'b4296f145b42ccb35c26085470ff4b3fd5dffe533251c0aab312312a73820ad6',
    'source':'Trenord / Regione Lombardia historical GTFS via MobilityDatabase',
    'source_url':'https://www.dati.lombardia.it/Mobilit-e-trasporti/Orario-Ferroviario-Regionale-Gtfs/3z4k-mxz9',
    'attribution':'Trenord / Regione Lombardia, CC BY 4.0, GTFS archived 4 August 2026 by MobilityDatabase. Historical selection and railway matching by SunTrain. Geography © OpenStreetMap contributors, ODbL 1.0.'}}
SOURCES['italo']={**BASE,'captured':'2026-10-05','published':'2026-10-04',
    'url':'https://raw.githubusercontent.com/deryclem/italo-gtfs/bb789e58e6b29be1896388b97b0c4dd642193706/gtfs-italo.zip',
    'sha256':'dbbb6e9fa453fa016cafaaafe4f61393c2de53f3c119110fb77539d885e2298d',
    'source':'Italo / CCISS historical NeTEx, converted to GTFS by Clément Desouche (@deryclem)',
    'source_url':'https://github.com/deryclem/italo-gtfs/tree/bb789e58e6b29be1896388b97b0c4dd642193706',
    'attribution':'Italo S.p.A. / CCISS MMTIS original NeTEx, publication 4 October 2026. GTFS conversion © 2026 Clément Desouche (@deryclem), CC BY 4.0, archived commit 5 October 2026. Historical selection and railway matching by SunTrain. Geography © OpenStreetMap contributors, ODbL 1.0.'}

# Pinned Trenord station-code group S05 covers Ticino. These additional audited
# Swiss calls use other identifiers; nearby Italian S01 stations remain included.
SWISS_TRENORD={'S01301','S13143','S19901','S19919','Z05304'}


def selected_route(feed,route,agencies):
    if feed=='trenitalia':
        return (route.get('agency_id')==AGENCY and agencies.get(AGENCY,{}).get('agency_name')=='TRENITALIA'
                and route.get('route_type')=='2' and route.get('route_short_name') in PRODUCTS
                and route.get('route_id','').startswith('IT::Line:railTRENITALIA:'))
    if feed=='italo':
        return (route.get('agency_id')=='IT::Operator:1'
            and agencies.get('IT::Operator:1',{}).get('agency_name')=='Italo - Nuovo Trasporto Viaggiatori'
            and route.get('route_type')=='2' and route.get('route_short_name')=='Italo'
            and route.get('route_id','').startswith('IT::Line:RAIL-'))
    return (route.get('agency_id')=='1' and agencies.get('1',{}).get('agency_name')=='Trenord'
            and route.get('route_type')=='2' and route.get('route_id')!='TN_Bus')


def domestic_sequence(feed,sequence,stops):
    if feed=='italo':return sequence
    def domestic(row):
        key=row['stop_id']
        return (stops[key].get('stop_code','').startswith('83') if feed=='trenitalia'
            else not (key.startswith('S05') or key in SWISS_TRENORD))
    indices=[i for i,row in enumerate(sequence) if domestic(row)]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def single_train_itinerary(trip_id):
    # The converted Italo feed also contains rail legs of connecting passenger
    # itineraries. They repeat existing trains and can carry the FIRST train's
    # number even on a different connecting train. Replay direct journeys only.
    return not bool(re.search(r'_rail\d*$',trip_id))


def train_number(value):
    # Trenord publishes e.g. "S13 - 24311"; retain its actual train number.
    tail=value.rsplit(' - ',1)[-1].strip()
    return str(int(tail)) if tail.isdigit() else tail


def geometry_resolver(geographic):
    graphs={}
    def resolve(route,trip,sequence,coordinates):
        fast=route.get('route_short_name') in {'FR','FA','Italo'}
        if fast not in graphs:graphs[fast]=FranceRailGraph(geographic['ways'],fast=fast)
        result=[]
        for a,b in zip(coordinates,coordinates[1:]):
            curve=graphs[fast].leg(a,b)
            if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([a,b])[-1]):curve=None
            result.append(curve)
        return result
    return resolve


def normalized_name(value):
    return re.sub(r'[^A-Z0-9]','',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().upper())


def remove_duplicate_occurrences(reference):
    removed=Counter()
    def endpoints(pattern):
        return [reference['stations'][i] for i in (reference['stop_patterns'][pattern['stop_pattern']]['stations'][0],
                reference['stop_patterns'][pattern['stop_pattern']]['stations'][-1])]
    def same_stations(a,b):
        return all(normalized_name(x['name'])==normalized_name(y['name']) or
            cumulative_distances([[x['lon'],x['lat']],[y['lon'],y['lat']]])[-1]<=150 for x,y in zip(a,b))
    for day,rows in reference['days'].items():
        seen=defaultdict(list);kept=[]
        # Prefer primary national records if two feeds describe the same trip.
        for key,trip,offset in sorted(rows,key=lambda row:row[1].startswith('it-trenord:')):
            p=reference['patterns'][key];number=train_number(reference['train_numbers'].get(trip,trip))
            signature=(number,offset+p['times'][1],offset+p['times'][-2]);ends=endpoints(p)
            if number.isdigit() and any(same_stations(ends,previous) for previous in seen[signature]):
                removed[p['operator']]+=1;continue
            seen[signature].append(ends);kept.append([key,trip,offset])
        reference['days'][day]=sorted(kept,key=lambda row:(row[2],row[1]))
    reference['metadata']['deduplicated_occurrences']=dict(removed)
    reference['metadata']['daily_services']={d:dict(Counter(reference['patterns'][p]['mode'] for p,t,o in rows)) for d,rows in reference['days'].items()}


def prepare(cache,output):
    if file_hash(GEOMETRY)!=GEOMETRY_SHA256:raise ValueError('Italian railway geometry differs from the validated reference')
    with gzip.open(GEOMETRY,'rt') as f:geographic=json.load(f)
    resolver=geometry_resolver(geographic);references=[]
    for feed,source in SOURCES.items():
        numbers,destinations,audit={},{},Counter()
        def select(sequence,stops):
            if feed=='italo' and sequence and not single_train_itinerary(sequence[0]['trip_id']):
                audit['connecting_itinerary_legs_excluded']+=1;return []
            clipped=domestic_sequence(feed,sequence,stops)
            if clipped:
                audit['included_candidates']+=1
                if len(clipped)<len(sequence):audit['clipped_candidates']+=1
                destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
            else:audit['outside_scope_or_single_call']+=1
            return clipped
        def describe(route,trip):
            short=route['route_short_name'];numbers[trip['trip_id']]=train_number(trip.get('trip_short_name') or trip['trip_id'])
            label=route['route_long_name'] if feed=='trenitalia' else 'AV' if feed=='italo' else short
            operator={'trenitalia':'Trenitalia','trenord':'Trenord','italo':'Italo'}[feed]
            return {'mode':'train','operator':operator,
                'route_id':route['route_id'],'route_short_name':short,'category':short,'line':label+' · '+operator,
                'color':COLORS[short] if feed=='trenitalia' else route.get('route_color') or '006633',
                'direction':'Not specified','destination':destinations[trip['trip_id']]}
        target=cache/(feed+'-week.json.gz')
        prepare_rail('it-'+feed,source,cache,target,lambda r,a:selected_route(feed,r,a),describe,geometry_resolver=resolver,select_sequence=select)
        with gzip.open(target,'rt') as f:r=json.load(f)
        r['train_numbers']=numbers;r['metadata']['scope_audit']=dict(audit);references.append(('it-'+feed,r))
    result=merge_references(references,source_name='Trenitalia, Trenord and Italo historical Italian passenger train schedules',replay_note=NOTE)
    result['metadata']['additional_geometry_sources']=[]
    result['metadata']['scope_audit']={ns:r['metadata']['scope_audit'] for ns,r in references}
    remove_duplicate_occurrences(result);save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',output.stat().st_size,'deduplicated',result['metadata']['deduplicated_occurrences'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/italy')
    p.add_argument('--output',type=Path,default=ROOT/'data/reference/italy/2026-10-05.json.gz')
    a=p.parse_args();prepare(a.cache,a.output)
