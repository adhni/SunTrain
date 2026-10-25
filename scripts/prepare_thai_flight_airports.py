"""Exact Thai domestic candidates; published routes and explicit probes, not schedules."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

AIRASIA='https://newsroom.airasia.com/news/airasia-is-back-at-suvarnabhumi-direct-flights-resume-oct-1-to-chiang-mai-krabi-and-phuket'
THAI='https://www.thaiairways.com/en-bd/content/where-we-fly/thailand/'
PG='https://www.bangkokair.com/eng/discovery-airpass/route-fare'
UTP='https://www.utapao.com/apps/domestic.php'
REGIONS={'Central':'BKK DMK HHQ','North':'CNX CEI LPT NNT PHS MAQ THS',
    'Northeast':'UTH UBP KKC KOP SNO ROI BFV LOE','East':'UTP TDX',
    'South':'HKT KBV USM URT NST HDY TST NAW CJM UNN'}


def prepare():
    regions={c:r for r,codes in REGIONS.items() for c in codes.split()}
    cache=ROOT/'.cache/australia-flights-audit';cache.mkdir(parents=True,exist_ok=True)
    raw=pinned_download(AIRPORT_URL,cache/'ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    airports=[]
    for code in sorted(regions):
        matches=[a for a in rows if a['iata_code']==code and a['iso_country']=='TH' and a['type']!='closed']
        if len(matches)!=1:raise ValueError(f'Unresolved or ambiguous airport: {code}')
        a=matches[0]
        airports.append(dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",
            municipality=a['municipality'],country='TH',timezone='Asia/Bangkok',island_group=regions[code],mode='flight',
            lat=float(a['latitude_deg']),lon=float(a['longitude_deg'])))
    pairs=set();evidence=[]
    def add(a,targets,url,kind='Published route candidate; not dated operation or fare evidence'):
        for b in targets.split():
            if a==b or a not in regions or b not in regions:raise ValueError(f'Invalid Thai route: {a}-{b}')
            pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=url,kind=kind))
    add('BKK','CNX CEI HDY KKC KBV HKT UBP UTH',THAI)
    add('BKK','CNX KBV HKT',AIRASIA)
    add('CNX','DMK BKK UTH KKC HHQ HDY HKT KBV URT',AIRASIA)
    add('HKT','DMK BKK CNX KKC',AIRASIA)
    # The older Airpass table is a candidate list only. Its product prices are
    # never copied, and Bangkok Airways' Bangkok airport is resolved as BKK.
    add('BKK','CNX HKT KBV THS TDX LPT CEI USM',PG,'Historical Airpass route candidate; no product prices or timings retained')
    add('CNX','HKT KBV USM',PG,'Historical Airpass route candidate')
    add('USM','HKT KBV UTP',PG,'Historical Airpass route candidate')
    add('HKT','HDY',PG,'Historical Airpass route candidate')
    add('UTP','CNX HDY KKC HKT UTH DMK USM',UTP,'Undated airport timetable candidate; dated captures required')
    # Focused Bangkok/regional probes supplement the published hub network.
    # These are explicitly search candidates, never an assertion of service.
    add('DMK','BFV CEI CJM CNX HDY KBV KKC KOP LOE LPT MAQ NNT NST NAW PHS HKT UNN ROI SNO URT TST UBP UTH',AIRASIA,
        'Supplemental exact-airport regional probe; not a published pair or proof of service')
    add('BKK','NST',THAI,'Supplemental exact-airport regional probe; not a published pair or proof of service')
    add('HKT','UTH',AIRASIA,'Supplemental northeast connection probe; dated availability checked separately')
    manifest=dict(country='TH',scope='domestic',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Bangkok',
        currency='USD',max_duration=8*3600,coverage_scope='Selected domestic hubs and regional airports; smaller/charter-only services deferred',
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=AIRASIA,
        route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated exact-airport evidence and explicit probes; not raw website bytes',
        source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
        source_documents=[dict(url=AIRASIA,sha256='7372e24aeff86fe08c02c65bbce3030fd498cdeac82fb2178e625f148bc5f093',bytes=161686),
            dict(url=UTP,sha256='28b1d7cc0f54d925e83d8cb280d6c895541764a3875f45e96d66f9825013dabb',bytes=33356)],
        airports=airports,routes=sorted(pairs),evidence=evidence,unresolved_airports=[],
        deferred_airports=[dict(code=c,reason='Smaller/commuter airport outside this first pass') for c in ['HGN','PRH']])
    (ROOT/'data/sources/thailand_flights_routes.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(airports=len(airports),directional_routes=len(pairs))))


if __name__=='__main__':prepare()
