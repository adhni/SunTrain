"""Exact New Zealand airport candidates, focused domestic hubs and international gateways."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from dashboard.international_network import COUNTRIES,HUBS
DAY='2026-11-02'
REGIONS={'North Island':'AKL WLG HLZ TRG ROT TUO GIS NPE NPL PMR KKE WRE','South Island':'CHC ZQN NSN BHE HKK TIU DUD IVC'}
SOURCES={
 'airline':'https://www.airnewzealand.com/en-nz/travel-info/destinations-we-fly-to',
 'wlg_domestic':'https://www.wellingtonairport.co.nz/flight-information/routes/domestic-destinations/',
 'wlg_international':'https://www.wellingtonairport.co.nz/flight-information/routes/international-destinations/',
 'akl_network':'https://www.aucklandairport.co.nz/content/dam/aia/files/corporate/annual-report-2025/FY25%20Annual%20results%20presentation.pdf',
 'chc_schedule':'https://www.christchurchairport.nz/about-us/who-we-are/media/2026/christchurch-airports-biggest-ever-international-summer-takes-flight/',
}
DOMESTIC={'AKL':'WLG CHC ZQN NSN NPE PMR TRG NPL GIS KKE BHE ROT DUD TUO IVC WRE',
 'CHC':'WLG ZQN DUD IVC NSN HLZ PMR TRG NPE ROT NPL HKK',
 'WLG':'ZQN DUD NSN NPE BHE HLZ NPL TRG ROT GIS TIU IVC TUO'}


def prepare():
    regions={c:r for r,codes in REGIONS.items() for c in codes.split()};pairs={'domestic':set(),'international':set()};evidence=[];inputs=[];catalogue={}
    def add(scope,a,targets,source,kind):
        for b in targets.split():
            if a==b:raise ValueError('Self route')
            pairs[scope].update([(a,b),(b,a)])
            evidence.append(dict(origin=a,destination=b,scope=scope,source=source,kind=kind))
    for a,targets in DOMESTIC.items():
        add('domestic',a,targets,SOURCES['wlg_domestic'] if a=='WLG' else SOURCES['airline'],'Selected exact-airport hub probe; destination list is context, not proof of a dated pair')
    for path in [ROOT/f'data/sources/{n}_international_routes.json' for n in ['australia','indonesia','malaysia','singapore','india']]+[ROOT/'data/sources/gulf_flights_routes.json']:
        d=json.loads(path.read_text());air={a['code']:a for a in d['airports']};catalogue.update(air)
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for a,b in d['routes']:
            endpoints=[air[a],air[b]]
            if 'NZ' not in {v['country'] for v in endpoints} or endpoints[0]['country']==endpoints[1]['country']:continue
            if any(v['country'] not in COUNTRIES or (v['country'] in {'AE','QA'} and v['code'] not in HUBS) for v in endpoints):continue
            pairs['international'].add((a,b));evidence.append(dict(origin=a,destination=b,scope='international',source=str(path.relative_to(ROOT)),kind='Existing published/probe candidate; no cached flight identity changes'))
    base=len(pairs['international'])
    for path in sorted(ROOT.glob('data/sources/*_flights_routes.json')):
        d=json.loads(path.read_text());catalogue.update({a['code']:a for a in d['airports'] if a.get('country') and a.get('timezone')})
    add('international','AKL','NRT PVG',SOURCES['airline'],'Airline destination candidate, Tokyo explicitly probed as NRT; dated nonstop capture required')
    add('international','AKL','ICN PEK CAN SZX HGH HAK TFU',SOURCES['akl_network'],'Historical airport network context; exact gateway probes, not dated operation evidence; Chengdu explicitly probed as TFU')
    add('international','CHC','CAN',SOURCES['chc_schedule'],'Airport summer schedule candidate; only dated captures create flight records')
    add('international','WLG','BNE SYD MEL OOL',SOURCES['wlg_international'],'Official airport nonstop destination candidate, dated capture required')
    # CHC-NRT starts 28 November and CHC-PER starts 30 November: outside this replay.
    # HKG/TPE, Pacific islands and North America are outside the shared country footprint.
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    resolved={}
    for code in sorted({c for ps in pairs.values() for pair in ps for c in pair}):
        old=catalogue.get(code,{});country='NZ' if code in regions else old.get('country')
        matches=[a for a in rows if a['iata_code']==code and a['type']!='closed' and a['iso_country']==country]
        if len(matches)!=1:raise ValueError(f'Unresolved or ambiguous airport: {code}/{country}')
        a=matches[0];zone='Pacific/Auckland' if country=='NZ' else old.get('timezone')
        if country=='CN':zone='Asia/Shanghai'
        if country=='IN':zone='Asia/Kolkata'
        ZoneInfo(zone)
        resolved[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        if country=='NZ':resolved[code]['island_group']=regions[code]
    for scope,ps in pairs.items():
        codes={c for pair in ps for c in pair};ev=[e for e in evidence if e['scope']==scope]
        doc=dict(country='NZ',scope=scope,start_date=DAY,end_date=DAY,timezone='Pacific/Auckland',currency='USD',max_duration=(8 if scope=='domestic' else 24)*3600,
            airports=[resolved[c] for c in sorted(codes)],routes=[list(p) for p in sorted(ps)],evidence=ev,input_manifests=inputs if scope=='international' else [],
            airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SOURCES['airline'],source_urls=SOURCES,source_reviewed_date='2026-10-26',
            unresolved_airports=[],base_directional_routes=base if scope=='international' else 0,coverage_scope='Selected North and South Island hubs and regional airports; international limited to existing SunTrain flight countries',
            deferred_airports=['CHT and smaller commuter, island and scenic services'],deferred_routes=['CHC-NRT starts 2026-11-28','CHC-PER starts 2026-11-30'])
        doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=ev,inputs=doc['input_manifests']),sort_keys=True).encode()).hexdigest()
        kind='flights' if scope=='domestic' else 'international'
        (ROOT/f'data/sources/new_zealand_{kind}_routes.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(dict(scope=scope,airports=len(codes),routes=len(ps),base_routes=base)))


if __name__=='__main__':prepare()
