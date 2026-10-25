"""Curated exact-airport candidates for the remaining ASEAN members."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.asean_flights import PROFILES,RETIRED_AIRPORTS
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

SOURCES={
 'BN':'https://www.flyroyalbrunei.com/brunei/en/destination/route-map/route-map/',
 'KH':'https://www.aircambodia.com/en/offer/-ready-for-your-ultimate-vacation-ready-for-takeoff-',
 'LA':'https://laoairlines.com/en/route-map/',
 'MM':'https://secure.flymna.com/plan-a-trip',
 'TL':'https://timorleste.tl/plan-your-trip',
 'relocation':'https://www.techoairport.com.kh/news/techo-intl-airport-welcome-first-flight-09-sep-2025',
 'sai_relocation':'https://www.icao.int/sites/default/files/APAC/Meetings/2023/2023%20MET%20SG%2027/3-Working%20Papers/WP24_A.I.5_KHM_SIEM-REAP-ANGKOR-INTERNATIONAL-AIRPORT-VDSA.pdf',
 'TL_domestic':'https://www.aerodili.com/about/',
}
DOMESTIC={
 'BN':[],
 'KH':[('KTI','SAI KOS'),('SAI','KOS')],
 'LA':[('VTE','LPQ PKZ LXG ODY XKH ZVK HOE'),('LPQ','PKZ'),('PKZ','ZVK')],
 'MM':[('RGN','MDL HEH NYU THL MYT PBU KAW MGZ TVY NYT KMV AKY SNW'),('MDL','HEH NYU THL MYT PBU')],
 'TL':[('DIL','OEC')],
}
EXTRA={
 'BN':[('BWN','SIN KUL BKI KCH MNL CGK SUB BKK SGN HAN MEL ICN NRT PVG PKX CAN DXB')],
 'KH':[('KTI','BKK DMK HAN SGN DAD KUL SIN ICN PUS CAN SZX PVG KMG TFU DEL MNL'),('SAI','BKK DMK HAN SGN DAD SIN KUL ICN'),('KOS','KTI KUL CAN')],
 'LA':[('VTE','BKK DMK CNX HAN SGN KTI SIN KUL ICN PUS KMG CAN PVG'),('LPQ','BKK DMK CNX HAN SAI ICN'),('PKZ','SGN SAI')],
 'MM':[('RGN','BKK DMK CNX SIN KUL HAN SGN ICN KMG CAN DEL CCU GAY'),('MDL','BKK DMK KMG')],
 'TL':[('DIL','DRW DPS SIN KUL KOE XMN')],
}


def prepare():
    domestic={c:set() for c in PROFILES};international={c:set() for c in PROFILES};ev={c:[] for c in PROFILES};catalogue={};inputs=[]
    def add(c,a,b,source,kind,scope):
        if a==b:raise ValueError('Self route')
        target=domestic[c] if scope=='domestic' else international[c]
        target.add((a,b));ev[c].append(dict(origin=a,destination=b,source=source,kind=kind,scope=scope))
    names=['australia','indonesia','malaysia','singapore','india']
    for path in [ROOT/f'data/sources/{n}_international_routes.json' for n in names]+[ROOT/'data/sources/gulf_flights_routes.json']:
        d=json.loads(path.read_text());air={a['code']:a for a in d['airports']};catalogue.update(air)
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for a,b in d['routes']:
            for c in PROFILES:
                if c not in {air[a]['country'],air[b]['country']} or air[a]['country']==air[b]['country']:continue
                aa,bb=RETIRED_AIRPORTS.get(a,a),RETIRED_AIRPORTS.get(b,b)
                add(c,aa,bb,str(path.relative_to(ROOT)),'Existing candidate; retired airport labels explicitly migrated for discovery only, never cached flights', 'international')
    # Domestic catalogues supply identities for focused added foreign gateways.
    for path in ROOT.glob('data/sources/*_flights_routes.json'):
        d=json.loads(path.read_text());catalogue.update({a['code']:a for a in d['airports'] if a.get('country') and a.get('timezone')})
    base={c:len(ps) for c,ps in international.items()}
    for c in PROFILES:
        for a,targets in DOMESTIC[c]:
            for b in targets.split():
                for x,y in [(a,b),(b,a)]:add(c,x,y,SOURCES.get(c+'_domestic',SOURCES[c]),'Selected domestic route/probe candidate; undated airline network is context, dated capture required','domestic')
        for a,targets in EXTRA[c]:
            for b in targets.split():
                for x,y in [(a,b),(b,a)]:add(c,x,y,SOURCES[c],'Supplemental exact-airport gateway probe; contextual network page is not dated service evidence','international')
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    codes={x for groups in [domestic,international] for ps in groups.values() for pair in ps for x in pair}
    # Resolve every candidate against country-matching, unique active IATA rows.
    resolved={}
    for code in sorted(codes):
        matches=[a for a in rows if a['iata_code']==code and a['type']!='closed']
        hint=catalogue.get(code)
        if hint and hint.get('country'):matches=[a for a in matches if a['iso_country']==hint['country']]
        if len(matches)!=1:raise ValueError(f'Unresolved or ambiguous airport: {code}')
        a=matches[0];country=a['iso_country'];old=catalogue.get(code,{})
        zone=PROFILES[country]['zone'] if country in PROFILES else old.get('timezone')
        zone={'Asia/Rangoon':'Asia/Yangon'}.get(zone,zone)
        if country=='CN':zone='Asia/Shanghai'
        if country=='IN':zone='Asia/Kolkata'
        if code=='KOE':zone='Asia/Makassar'
        if not zone:raise ValueError(f'Missing explicit timezone: {code}/{country}')
        ZoneInfo(zone)
        resolved[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
    footprint={'AU','ID','MY','SG','IN','TH','PH','VN','CN','JP','KR','AE','QA',*PROFILES}
    for c,p in PROFILES.items():
        for scope,ps in [('domestic',domestic[c]),('international',international[c])]:
            if scope=='domestic' and not p['domestic']:continue
            ps={pair for pair in ps if resolved[pair[0]]['country']!=resolved[pair[1]]['country']} if scope=='international' else ps
            ps={pair for pair in ps if all(resolved[x]['country'] in footprint and (resolved[x]['country'] not in {'AE','QA'} or x in {'DXB','AUH','DOH'}) for x in pair)}
            if scope=='international':
                # Include both endpoints' candidate in their own country manifests.
                for other,ops in international.items():
                    for a,b in ops:
                        if c in {resolved[a]['country'],resolved[b]['country']} and resolved[a]['country']!=resolved[b]['country']:ps.add((a,b))
            needed={x for pair in ps for x in pair}
            evidence=[e for es in ev.values() for e in es if e['scope']==scope and (e['origin'],e['destination']) in ps]
            doc=dict(country=c,scope=scope,start_date='2026-11-02',end_date='2026-11-02',timezone=p['zone'],currency='USD',max_duration=(8 if scope=='domestic' else 24)*3600,
                airports=[resolved[x] for x in sorted(needed)],routes=[list(pair) for pair in sorted(ps)],evidence=evidence,unresolved_airports=[],
                airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SOURCES[c],source_urls=SOURCES,
                source_reviewed_date='2026-10-26',base_directional_routes=base[c] if scope=='international' else 0,
                input_manifests=inputs if scope=='international' else [],coverage_scope='Selected captured schedules and exact-airport probes; not complete national coverage',
                retired_airport_candidate_migrations=RETIRED_AIRPORTS,flight_records_remapped=False)
            doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=evidence,inputs=doc['input_manifests']),sort_keys=True).encode()).hexdigest()
            kind='flights' if scope=='domestic' else 'international'
            (ROOT/f"data/sources/{p['slug']}_{kind}_routes.json").write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
            print(json.dumps(dict(country=c,scope=scope,airports=len(needed),routes=len(ps))))


if __name__=='__main__':prepare()
