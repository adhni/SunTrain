"""Prepare Spanish passenger trains for 24–30 June 2024 from pinned archives."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import merge_references, save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY = ROOT / 'data/reference/spain/ign-rail-2026-10-19.json.gz'
GEOMETRY_SHA256 = 'ae1acc73a5fbe3b49a498b49bb65d62e0e08d3b675b0c9f770c7329dcead86d2'
PRODUCTS = {'AVE', 'AVE INT', 'AVLO', 'ALVIA', 'Intercity', 'EUROMED', 'MD', 'AVANT',
            'REG.EXP.', 'REGIONAL', 'PROXIMDAD', 'TRENCELTA', 'TORRE ORO', 'RODALIES'}
FGC_LINES = {'R5','R6','S1','S2','S3','S4','S8','R60','R50','S9','R63','R53','RL1','RL2'}
# Audited foreign stations in these two Renfe snapshots. Prefixes alone are
# unsafe: 94002 (Daimiel) and 94004 (Almagro) are Spanish stations.
FOREIGN_STOPS = {'94346','94021','94033','87089','87912','87814','87302','87173','87088',
                 '87374','87303','87810','79316','77310'}
CREDIT = 'Obra derivada de IGR Redes de Transporte, consulta 2026-10-19, CC BY 4.0, ign.es / Sistema Cartográfico Nacional. Matched and simplified by SunTrain.'
BASE = {'first':'2024-06-24','last':'2024-06-30','timezone':'Europe/Madrid','calendar_validity':True,
        'license':'CC BY 4.0','license_url':'https://creativecommons.org/licenses/by/4.0/',
        'assign_by_start':['train'],'geometry_source':CREDIT,
        'geometry_source_url':'https://api-features.idee.es/collections/railwaylink?f=json',
        'geometry_license':'CC BY 4.0','geometry_license_url':'https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf',
        'geometry_source_date':'Accessed 2026-10-19; geographic reference for 2024 schedules',
        'geometry_sha256':GEOMETRY_SHA256,'geometry_quality':'track',
        'note':'Spanish passenger trains from historical June 2024 schedules. International journeys retain Spanish station portions and any intervening foreign calls with original times. Paths are inferred geographical alignments, not exact running tracks or a record of every diversion. Unresolved movement stays hidden between stops. No individual passenger loads.'}
SOURCES = {
 'national':{**BASE,'captured':'2024-06-24','published':'',
    'url':'https://files.mobilitydatabase.org/mdb-790/mdb-790-202406240002/mdb-790-202406240002.zip',
    'sha256':'885f50c3c0dbff11ed54758c49d1e1c8d8ff8947b1f7eac8f68667fa5d90c6d9',
    'source':'Renfe historical high-speed, long-distance and medium-distance GTFS via MobilityDatabase',
    'source_url':'https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia',
    'attribution':'Origen de los datos: Renfe Operadora · archived 24 June 2024 by MobilityDatabase. '+CREDIT},
 'cercanias':{**BASE,'captured':'2024-06-24','published':'',
    'url':'https://files.mobilitydatabase.org/mdb-1065/mdb-1065-202406240019/mdb-1065-202406240019.zip',
    'sha256':'e630225b5acfe8c14b58c6197e00b439716ec929ea8538f1fcd22a4d64f342d4',
    'source':'Renfe historical Cercanías and Rodalies GTFS via MobilityDatabase',
    'source_url':'https://data.renfe.com/dataset/horarios-cercanias',
    'attribution':'Origen de los datos: Renfe Operadora · Cercanías/Rodalies archive 24 June 2024 via MobilityDatabase. '+CREDIT},
 'fgc':{**BASE,'captured':'2024-06-07','published':'2024-06-04','geometry_quality':'shape',
    'url':'https://files.mobilitydatabase.org/mdb-1856/mdb-1856-202406071504/mdb-1856-202406071504.zip',
    'sha256':'b27cae62bf76e28b0cecd9a8b6dc92e901b61f2361506a18ebcc07caa52b54d7',
    'source':'FGC historical regional and suburban train GTFS via MobilityDatabase',
    'source_url':'https://dadesobertes.fgc.cat/explore/dataset/gtfs_zip/information/',
    'geometry_source':'FGC official historical GTFS shapes, selected and simplified by SunTrain',
    'geometry_source_url':'https://www.fgc.cat/google/google_transit.zip',
    'geometry_source_date':'GTFS version 2024-06-04; archived 2024-06-07',
    'geometry_sha256':'b27cae62bf76e28b0cecd9a8b6dc92e901b61f2361506a18ebcc07caa52b54d7',
    'geometry_license_url':'https://creativecommons.org/licenses/by/4.0/',
    'attribution':'Timetable and supplied FGC shapes: Ferrocarrils de la Generalitat de Catalunya, version 4 June 2024, archived 7 June by MobilityDatabase. Selected and simplified by SunTrain.'}}


def selected_route(feed, route, agencies):
    agency = route.get('agency_id') or (next(iter(agencies)) if len(agencies)==1 else None)
    expected = {'national':('1071','RENFE OPERADORA'),'cercanias':('1071VC','Renfe Cercanias'),'fgc':('','FGC')}[feed]
    if (agency,agencies.get(agency,{}).get('agency_name')) != expected or route.get('route_type') != '2':return False
    return (route.get('route_short_name') in PRODUCTS if feed=='national' else
            route.get('route_short_name') in FGC_LINES if feed=='fgc' else True)


def domestic_sequence(sequence):
    indices = [i for i,row in enumerate(sequence) if row['stop_id'] not in FOREIGN_STOPS]
    return sequence[indices[0]:indices[-1]+1] if len(indices)>=2 else []


def geometry_resolver(geographic):
    graph = FranceRailGraph(geographic['ways'])
    def resolve(route, trip, sequence, coordinates):
        result=[]
        for a,b in zip(coordinates,coordinates[1:]):
            curve=graph.leg(a,b)
            if curve and cumulative_distances(curve)[-1] > max(5000,3*cumulative_distances([a,b])[-1]):curve=None
            result.append(curve)
        return result
    return resolve


def finalize_credits(result):
    # Both Renfe components share the same geography; credit it once.
    result['metadata']['attribution'] = ('Origen de los datos: Renfe Operadora · archive 24 June 2024. '
        'FGC schedules and supplied shapes · version 4 June 2024, archive 7 June 2024. '
        'Archives via MobilityDatabase; historical selection and simplification by SunTrain. '+CREDIT)
    result['metadata']['additional_geometry_sources'] = [credit for credit in result['metadata']['additional_geometry_sources']
        if credit['geometry_source'] != result['metadata']['geometry_source']]


def prepare(cache, output):
    if file_hash(GEOMETRY)!=GEOMETRY_SHA256:raise ValueError('Spanish railway geometry differs from the validated reference')
    with gzip.open(GEOMETRY,'rt') as stream:geographic=json.load(stream)
    resolver=geometry_resolver(geographic);references=[]
    for feed,source in SOURCES.items():
        numbers,destinations={},{}
        def select(sequence,stops):
            clipped=domestic_sequence(sequence) if feed!='fgc' else sequence
            if clipped:destinations[sequence[0]['trip_id']]=stops[clipped[-1]['stop_id']]['stop_name']
            return clipped
        def describe(route,trip):
            short=route['route_short_name'];operator={'national':'Renfe','cercanias':'Renfe Cercanías / Rodalies','fgc':'FGC'}[feed]
            numbers[trip['trip_id']]=trip.get('trip_short_name') or trip['trip_id']
            # The national source uses near-white for every product; use a
            # readable display palette rather than invisible white vehicles.
            color=({'AVE':'7B1B55','AVE INT':'7B1B55','AVLO':'A820A0','AVANT':'176B9A'}.get(short,'8A204F')
                   if feed=='national' else route.get('route_color') or '007D79')
            return {'mode':'train','operator':operator,'route_id':route['route_id'],'route_short_name':short,
                    'category':short,'line':short+' · '+operator,'color':color,'direction':'Not specified',
                    'destination':destinations[trip['trip_id']]}
        target=cache/(feed+'-week.json.gz')
        prepare_rail('es-'+feed,source,cache,target,lambda route,agencies:selected_route(feed,route,agencies),describe,
                     geometry_resolver=resolver if feed!='fgc' else None,select_sequence=select)
        with gzip.open(target,'rt') as stream:r=json.load(stream)
        r['train_numbers']=numbers;references.append(('es-'+feed,r))
    result=merge_references(references,source_name='Renfe national, Cercanías/Rodalies and FGC historical passenger trains',
        replay_note=BASE['note']+' Includes validated Renfe and FGC train services. Iryo, OUIGO España, Euskotren and FEVE are not included; metros, trams and buses are excluded.')
    finalize_credits(result)
    save_reference(result,output)
    print('days',{d:len(rows) for d,rows in result['days'].items()},'bytes',output.stat().st_size,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'.cache/spain')
    parser.add_argument('--output',type=Path,default=ROOT/'data/reference/spain/2024-06-24.json.gz')
    args=parser.parse_args();prepare(args.cache,args.output)
