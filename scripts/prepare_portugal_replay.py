"""Prepare Portuguese passenger trains and Lisbon Metro for 1–7 June 2026 from pinned GTFS."""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import merge_references,save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail
GEOMETRY=ROOT/'data/reference/portugal/ip-rail-2026-04-15.json.gz'
GEOMETRY_SHA256='b988a3d1ea461986ff95dc58deee1eaac36183652b168b3be958a21f616a6183'
CREDIT='Infraestruturas de Portugal, Rede Ferroviária Nacional, 15 April 2026, CC BY 4.0. Reprojected, matched and simplified by SunTrain.'
PRODUCTS={'AP':'Alfa Pendular','IC':'Intercidades','IR':'InterRegional','R':'Regional','U':'Urbanos'}
BASE={'first':'2026-06-01','last':'2026-06-07','timezone':'Europe/Lisbon','calendar_validity':True,
    'assign_by_start':['train','subway'],'published':'','geometry_source':CREDIT,
    'geometry_source_url':'https://dados.gov.pt/en/datasets/rede-ferroviaria-nacional',
    'geometry_license':'CC BY 4.0','geometry_license_url':'https://creativecommons.org/licenses/by/4.0/',
    'geometry_source_date':'2026-04-15','geometry_sha256':GEOMETRY_SHA256,'geometry_quality':'track',
    'note':'Historical CP, Fertagus and Lisbon Metro schedules, 1–7 June 2026. CP journeys retain Portuguese station portions and original times. Inferred rail alignments and supplied Fertagus/Lisbon Metro shapes; unresolved movement stays hidden between stops. No individual passenger loads.'}
SOURCES={
 'cp':{**BASE,'captured':'2026-05-31',
    'url':'https://files.mobilitydatabase.org/mdb-2057/mdb-2057-202605310107/mdb-2057-202605310107.zip',
    'sha256':'6e2c9832899eec69abf16545b4bd6af82879481d1c35823159ba057c74b2ceae',
    'source':'CP - Comboios de Portugal historical GTFS via MobilityDatabase',
    'source_url':'https://publico.cp.pt/gtfs/gtfs.zip',
    'license':'No licence / no contract (CP NAP declaration)',
    'license_url':'https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/176',
    'attribution':'CP - Comboios de Portugal, archived 31 May 2026 by MobilityDatabase. Historical selection by SunTrain. '+CREDIT},
 'fertagus':{**BASE,'captured':'2026-04-14','published':'2026-04-13',
    'url':'https://files.mobilitydatabase.org/tld-715/tld-715-202604140058/tld-715-202604140058.zip',
    'sha256':'a0735e39bb85438de09c98c89f7e0d45680bc372f23255f9183d1df12ff8fb3a',
    'source':'Fertagus historical passenger train GTFS via MobilityDatabase',
    'source_url':'https://www.fertagus.pt/GTFSTMLzip/Fertagus_GTFS.zip',
    'license':'CC BY 4.0','license_url':'https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/185',
    'geometry_method':'native_or_ordered_per_leg','geometry_quality':'shape','geometry_source':'Fertagus official historical GTFS shapes, selected and simplified by SunTrain',
    'geometry_source_url':'https://www.fertagus.pt/GTFSTMLzip/Fertagus_GTFS.zip',
    'geometry_source_date':'2026-04-13; archived 2026-04-14',
    'geometry_sha256':'a0735e39bb85438de09c98c89f7e0d45680bc372f23255f9183d1df12ff8fb3a',
    'geometry_license_url':'https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/185',
    'attribution':'Fertagus schedules and supplied shapes, archived 14 April 2026 by MobilityDatabase, CC BY 4.0. Selected and simplified by SunTrain.'}}


LISBON_LINES={'A':'Azul','B':'Amarela','C':'Verde','D':'Vermelha'}
SOURCES['lisbon']={**BASE,'captured':'2026-05-01','published':'',
    'url':'https://files.mobilitydatabase.org/tld-716/tld-716-202605010025/tld-716-202605010025.zip',
    'sha256':'79480fbe7cedb1c72bba2e2d62245107d7d979d6b1b50d6a7c0c5e8e94815956',
    'source':'Metropolitano de Lisboa historical GTFS via MobilityDatabase',
    'source_url':'https://www.metrolisboa.pt/google_transit/googleTransit.zip',
    'license':'No licence / no contract (Lisbon Metro NAP declaration)',
    'license_url':'https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/186',
    'geometry_quality':'shape','geometry_source':'Metropolitano de Lisboa official historical GTFS shapes, selected and simplified by SunTrain',
    'geometry_source_url':'https://www.metrolisboa.pt/google_transit/googleTransit.zip',
    'geometry_source_date':'Archived 2026-05-01',
    'geometry_sha256':'79480fbe7cedb1c72bba2e2d62245107d7d979d6b1b50d6a7c0c5e8e94815956',
    'geometry_license':'No licence / no contract (Lisbon Metro NAP declaration)',
    'geometry_license_url':'https://nap-portugal.imt-ip.pt/nap/multimodalsupplydetail/186',
    'attribution':'Metropolitano de Lisboa schedules and supplied shapes, archived 1 May 2026 by MobilityDatabase. Selected and simplified by SunTrain.'}


def selected_route(feed,route,agencies):
    agency=route.get('agency_id') or (next(iter(agencies)) if len(agencies)==1 else None)
    expected={'cp':('1094_CP','CP - Comboios de Portugal'),'fertagus':('15','Fertagus'),'lisbon':('ML','Metropolitano de Lisboa, E.P.E.')}[feed]
    if (agency,agencies.get(agency,{}).get('agency_name'))!=expected:return False
    if feed=='lisbon':return route.get('route_type')=='1' and LISBON_LINES.get(route.get('route_id'))==route.get('route_long_name')
    if feed=='fertagus':return route.get('route_type')=='2'
    return (route.get('route_type')=='2' and route.get('route_short_name') in {'AP','IC','IR','R'} or
            route.get('route_type')=='109' and (route.get('route_short_name','').startswith('Linha ') or route.get('route_short_name')=='U'))


def domestic_sequence(sequence):
    # This CP feed uses country-prefixed UIC identifiers; Spain's entries begin 71_.
    indices=[i for i,r in enumerate(sequence) if r['stop_id'].startswith('94_')]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def geometry_resolver(geographic):
    graph=FranceRailGraph(geographic['ways'])
    def resolve(route,trip,sequence,coordinates):
        result=[]
        for a,b in zip(coordinates,coordinates[1:]):
            curve=graph.leg(a,b)
            if curve and cumulative_distances(curve)[-1]>max(5000,3*cumulative_distances([a,b])[-1]):curve=None
            result.append(curve)
        return result
    return resolve


def prepare(cache,output):
    if file_hash(GEOMETRY)!=GEOMETRY_SHA256:raise ValueError('Portuguese railway geometry differs from the validated reference')
    with gzip.open(GEOMETRY,'rt') as stream:resolver=geometry_resolver(json.load(stream))
    references=[]
    for feed,source in SOURCES.items():
        numbers,destinations={},{}
        def select(sequence,stops):
            clipped=domestic_sequence(sequence) if feed=='cp' else sequence
            if clipped:destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
            return clipped
        def describe(route,trip):
            short=route['route_short_name'];category=PRODUCTS.get(short,short)
            numbers[trip['trip_id']]=trip.get('trip_short_name') or trip['trip_id']
            if feed=='lisbon':
                return {'mode':'subway','operator':'Lisbon Metro','route_id':route['route_id'],
                    'route_short_name':short,'category':route['route_long_name'],'line':'Lisbon '+route['route_long_name'],
                    'color':route['route_color'],'direction':'Direction '+{'0':'A','1':'B'}.get(trip.get('direction_id'),'unknown'),
                    'destination':destinations[trip['trip_id']]}
            color=({'AP':'C02638','IC':'28734F','IR':'70509B','R':'2683A6'}.get(short,'229A74')
                if feed=='cp' else route.get('route_color') or 'C74F4F')
            return {'mode':'train','operator':'CP' if feed=='cp' else 'Fertagus','route_id':route['route_id'],
                'route_short_name':short,'category':category,'line':category+' · CP' if feed=='cp' else 'Fertagus',
                'color':color,'direction':'Not specified','destination':destinations[trip['trip_id']]}
        target=cache/(feed+'-week.json.gz')
        prepare_rail('pt-'+feed,source,cache,target,lambda r,a:selected_route(feed,r,a),describe,
            geometry_resolver=resolver if feed=='cp' else None,select_sequence=select)
        with gzip.open(target,'rt') as stream:reference=json.load(stream)
        reference['train_numbers']=numbers;references.append(('pt-'+feed,reference))
    result=merge_references(references,source_name='CP, Fertagus and Lisbon Metro historical Portuguese rail schedules',replay_note=BASE['note'])
    result['metadata']['schedule_licenses']=[{k:source[k] for k in ('source','license','license_url','sha256')} for source in SOURCES.values()]
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,default=ROOT/'.cache/portugal')
    p.add_argument('--output',type=Path,default=ROOT/'data/reference/portugal/2026-06-01.json.gz')
    a=p.parse_args();prepare(a.cache,a.output)
