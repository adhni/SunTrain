"""Build the reviewed South America top-twenty and all-country catalogue with 702 directions."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

SELECTION=ROOT/'data/sources/south_america_airport_selection.json'


def prepare():
    selection=json.loads(SELECTION.read_text())
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    airports=[]
    for item in selection['airports']:
        code=item['code']
        matches=[a for a in rows if a['iata_code']==code and a['iso_country']==item['country'] and a['type']!='closed']
        if len(matches)!=1:raise ValueError(f'Unresolved exact airport: {code}')
        a=matches[0]
        airports.append(dict(**item,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",
            municipality=a['municipality'],lat=float(a['latitude_deg']),lon=float(a['longitude_deg']),mode='flight'))
    codes=[a['code'] for a in airports]
    if len(set(codes))!=27 or [a['rank'] for a in airports if a['rank'] is not None]!=list(range(1,21)):
        raise ValueError('Expected twenty ranked airports and seven national gateways')
    if set(selection['country_gateways'])!={'AR','BO','BR','CL','CO','EC','GY','PY','PE','SR','UY','VE'} or any(not any(a['code']==c and a['country']==country for a in airports) for country,c in selection['country_gateways'].items()):
        raise ValueError('Every South American country requires its exact national gateway')
    manifest=dict(profile='south_america',countries=list(dict.fromkeys(a['country'] for a in airports)),scope='regional',
        start_date='2026-11-02',end_date='2026-11-02',timezone='UTC',currency='USD',max_duration=28800,
        query_date_policy='origin_local_departure_day_only',
        coverage_scope='Nonstop flights between 27 selected South American airports: the reviewed top twenty plus national gateways for all twelve sovereign countries; domestic and cross-border, all returned airlines. Other airports excluded.',
        replay_note='South American domestic and cross-border flights between 27 selected airports covering all twelve South American countries. Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. Timeline: UTC; airport boards use local time. All captured fares use USD, including domestic flights. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.',
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,
        route_source_url=selection['source_url'],route_source_sha256=hashlib.sha256(SELECTION.read_bytes()).hexdigest(),
        route_source_hash_basis='SHA256 of committed normalized airport selection facts, not source webpage bytes',
        route_basis='All 702 ordered pairs among the reviewed top twenty plus seven national gateways; published traffic metrics differ; search candidates, not evidence of service.',
        additional_selection_source='data/sources/south_america_airport_selection.json',additional_selection_sha256=hashlib.sha256(SELECTION.read_bytes()).hexdigest(),
        country_gateways=selection['country_gateways'],airports=airports,routes=sorted((a,b) for a in codes for b in codes if a!=b),unresolved_airports=[])
    (ROOT/'data/sources/south_america_flights_routes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(airports),directions=len(manifest['routes']))))


if __name__=='__main__':prepare()
