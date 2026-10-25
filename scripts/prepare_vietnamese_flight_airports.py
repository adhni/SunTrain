"""Exact Vietnamese domestic candidates and selected international gateways."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

DAY='2026-11-02'
COUNTRIES={'AU','ID','MY','SG','IN','TH','PH','CN','JP','KR','AE','QA','VN'}
REGIONS={'North':'HAN HPH DIN VDO','Central and Highlands':'THD VII VDH HUI DAD VCL UIH TBB CXR DLI BMV PXU','South':'SGN VCA VKG CAH VCS PQC'}
SOURCES={
 'domestic':'https://www.vietnamairlines.com/content/dam/vna/vna-assets/MKT-PDF/BOD-WKS-DOM-EN.pdf',
 'regional':'https://giftcards.vietnamairlines.com/nhom-duong-bay/',
 'international':'https://www.vietnamairlines.com/content/dam/vna/vna-assets/MKT-PDF/BOD-WKS-INT-VI.pdf',
 'japan':'https://www.vietnamairlines.com/en-vn/flights-from-hanoi-to-japan',
 'korea':'https://www.vietjetair.com/vi/ve-may-bay/san-bay-da-nang-dad-da-nang',
 'airport_identity':'https://airportmap.vietnamairlines.com/?lang=en',
 'dli':'https://caa.gov.vn/Pages/Print.aspx?NewsId=20260805113611646',
}


def prepare():
    regions={c:r for r,codes in REGIONS.items() for c in codes.split()}
    pairs={'domestic':set(),'international':set()};evidence=[];catalogue={};inputs=[]
    def add(scope,a,targets,source,kind):
        for b in targets.split():
            if a==b:raise ValueError('Self route')
            pairs[scope].update([(a,b),(b,a)])
            evidence.append(dict(origin=a,destination=b,source=source,kind=kind,scope=scope))
    add('domestic','HAN','DAD CXR DLI HUI UIH VCL TBB VII VCA VDH DIN',SOURCES['domestic'],'Airline promotional route table, city labels resolved to exact airports; not dated service or fare evidence')
    add('domestic','SGN','HAN HPH VII BMV PXU VDH THD VDO VCL HUI CXR DLI DAD VKG CAH TBB UIH',SOURCES['domestic'],'Airline promotional route table, city labels resolved to exact airports; not dated service evidence')
    add('domestic','DAD','HPH VCA CXR VDO DLI VII THD BMV PXU',SOURCES['regional'],'Undated airline route-group candidate, city labels resolved; not current operation evidence')
    for a,targets in {'HUI':'DLI CXR','THD':'DLI','VCA':'BMV DLI VCS PQC','VII':'BMV','PQC':'DLI','HPH':'DIN'}.items():
        add('domestic',a,targets,SOURCES['regional'],'Undated airline route-group candidate, city labels resolved; dated captures required')
    add('domestic','DAD','PQC',SOURCES['airport_identity'],'Supplemental exact-airport cross-country probe; not published pair evidence')
    # Cover each selected region from the two major hubs without all-pairs searches.
    for hub in ['HAN','SGN']:
        add('domestic',hub,' '.join(c for c in sorted(regions) if c!=hub),SOURCES['airport_identity'],'Supplemental exact-airport hub probe; airport map establishes identity, not this route')
    # Only primary country manifests are inputs. Derived country manifests must
    # not acquire circular content-hash dependencies on one another.
    names=['australia','indonesia','malaysia','singapore','india']
    paths=[ROOT/f'data/sources/{name}_international_routes.json' for name in names]+[ROOT/'data/sources/gulf_flights_routes.json']
    for path in paths:
        d=json.loads(path.read_text());air={a['code']:a for a in d['airports']};catalogue.update(air)
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for a,b in d['routes']:
            if 'VN' not in {air[a]['country'],air[b]['country']} or air[a]['country']==air[b]['country']:continue
            if any(x['country'] not in COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in {'DXB','AUH','DOH'}) for x in (air[a],air[b])):continue
            pairs['international'].add((a,b));evidence.append(dict(origin=a,destination=b,scope='international',source=str(path.relative_to(ROOT)),kind='Existing route/probe candidate; dated nonstop capture required'))
    base=len(pairs['international'])
    # The recovered PH seed preserved candidates that its own release deferred.
    seed_path=ROOT/'data/sources/philippines_recovered_candidates.json';seed=json.loads(seed_path.read_text())
    hints={a['code']:a for a in seed['philippines_airports']};inputs.append(dict(path=str(seed_path.relative_to(ROOT)),sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest()))
    for r in seed['philippines_international_routes']:
        a,b=r['origin_iata'],r['destination_iata']
        if {hints[a]['country'],hints[b]['country']}=={'PH','VN'}:
            pairs['international'].add((a,b));evidence.append(dict(origin=a,destination=b,scope='international',source=r['source_url'],kind='Recovered partial-package candidate, not independently verified route or dated-flight evidence'))
    # Published city/offer lists discover candidates only; nonstop captures decide.
    add('international','HAN','NRT KIX NGO',SOURCES['japan'],'Exact-airport airline offer candidate, not dated nonstop evidence')
    for a in ['HAN','SGN']:
        add('international',a,'BKK HKT ICN PUS',SOURCES['international'],'Airline city-pair promotional table, Bangkok resolved to BKK; dates/fares are not copied')
    add('international','DAD','ICN PUS',SOURCES['korea'],'Official city/airport route candidate, Bangkok resolved to BKK; dated capture required')
    add('international','DAD','BKK',SOURCES['international'],'Airline city-pair promotional table, Bangkok resolved to BKK; dated capture required')
    for a in ['CXR','PQC']:
        add('international',a,'ICN PUS',SOURCES['korea'],'Supplemental exact-airport Korean gateway probe; contextual airline page is not pair evidence')
    for a,targets in {'HAN':'PVG PEK PKX CAN SZX TFU KMG HND FUK DMK','SGN':'PVG PEK CAN SZX TFU KMG NRT HND KIX NGO FUK DMK',
                      'DAD':'PVG CAN TFU NRT HND KIX DMK','CXR':'PVG CAN PEK','PQC':'BKK DMK'}.items():
        add('international',a,targets,SOURCES['airport_identity'],'Supplemental exact-airport major-gateway probe; identity map is not route evidence')
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    resolved={}
    for code in sorted({c for ps in pairs.values() for pair in ps for c in pair}):
        old=catalogue.get(code,{});hint=hints.get(code,{})
        country='VN' if code in regions else old.get('country') or hint.get('country')
        matches=[a for a in rows if a['iata_code']==code and a['iso_country']==country and a['type']!='closed']
        if len(matches)!=1:raise ValueError(f'Unresolved or ambiguous airport: {code}/{country}')
        a=matches[0];zone='Asia/Ho_Chi_Minh' if country=='VN' else old.get('timezone') or hint.get('timezone')
        if country=='CN':zone='Asia/Shanghai'
        if country=='IN':zone='Asia/Kolkata'
        # Additional East Asian/Thai gateways use explicit national IANA zones.
        zone=zone or {'CN':'Asia/Shanghai','JP':'Asia/Tokyo','KR':'Asia/Seoul','TH':'Asia/Bangkok'}.get(country)
        ZoneInfo(zone)
        entry=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        if country=='VN':entry['island_group']=regions[code]
        resolved[code]=entry
    for scope,ps in pairs.items():
        codes={c for p in ps for c in p};ev=[e for e in evidence if e['scope']==scope]
        doc=dict(country='VN',scope=scope,start_date=DAY,end_date=DAY,timezone='Asia/Ho_Chi_Minh',currency='USD',max_duration=(8 if scope=='domestic' else 24)*3600,
            airports=[resolved[c] for c in sorted(codes)],routes=[list(p) for p in sorted(ps)],evidence=ev,
            airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SOURCES['domestic' if scope=='domestic' else 'international'],
            route_hash_basis='Curated candidate evidence and input hashes, not raw website bytes',source_urls=SOURCES,source_reviewed_date='2026-10-25',
            input_manifests=inputs if scope=='international' else [],unresolved_airports=[],base_directional_routes=base if scope=='international' else 0,
            coverage_scope='Selected domestic hubs and regions; international restricted to existing SunTrain flight countries',
            airport_notes=['SGN remains Tan Son Nhat; Long Thanh is not substituted or assigned invented schedules.','DLI closure earlier in 2026 is not treated as a November closure; dated captures determine coverage.'])
        doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=ev,inputs=doc['input_manifests']),sort_keys=True).encode()).hexdigest()
        kind='flights' if scope=='domestic' else 'international'
        (ROOT/f'data/sources/vietnam_{kind}_routes.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(dict(scope=scope,airports=len(codes),routes=len(ps),base_routes=doc['base_directional_routes'])))


if __name__=='__main__':prepare()
