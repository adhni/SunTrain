"""Existing inter-country candidates plus focused official East Asian gateways."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.asean_flights import PROFILES, RETIRED_AIRPORTS

COUNTRIES = {'AU':'Australia','ID':'Indonesia','MY':'Malaysia','SG':'Singapore','IN':'India',
             'VN':'Vietnam','PH':'Philippines','TH':'Thailand','CN':'China','JP':'Japan','KR':'South Korea','AE':'United Arab Emirates','QA':'Qatar'}
COUNTRIES.update({c:p['name'] for c,p in PROFILES.items()})
HUBS = {'DXB','AUH','DOH'}
SOURCES = {
    'NRT':'https://www.narita-airport.jp/en/discover/citylist/',
    'HND':'https://tokyo-haneda.com/en/flight/city_list.html?tab=intFlight',
    'KIX':'https://assets.kansai-airports.co.jp/551f6859-e_20260324_pressrelease_s26.pdf',
    'NGO':'https://www.centrair.jp/en/',
    'ICN':'https://m.flyasiana.com/C/KR/KO/booking/route',
    'PUS':'https://en.airbusan.com/content/individual/booking/route',
    'historical':'https://www.airportal.go.kr/e-book/catImage/16/2018%20POCKET%20AVIATION%20STATUS.pdf',
}
SOURCE_DOCUMENTS = {
    'NRT':dict(sha256='552baf28eca934636b5e6227a7bf40954b4fbe570eb6e0dc113615b4c0f4e1d4',bytes=269377),
    'HND':dict(sha256='8ca2a84b5d17dd27742d27fa21540d51b6d320d3a778058c971f5bbea83d53d1',bytes=72772),
    'ICN':dict(sha256='306a86e99552505809ce2e82708d0b00d0a54af3a921966e466dcb6aa84a2f48',bytes=214277),
}
# Explicit airport labels from the cited official tables. Older/seasonal entries
# are candidates only; via-only columns and codeshare connections are not added.
GATEWAYS = {
    'NRT':'CAN CKG DLC FOC HAK HGH HRB PEK PVG SHE SZX TAO TFU TNA TSN XMN CJJ CJU ICN PUS TAE BLR BOM DEL CGK DPS KUL SIN',
    'HND':'GMP ICN CAN SZX SHA PVG TSN TAO DLC PEK PKX KUL SIN CGK SYD DEL BOM DOH DXB',
    'KIX':'PUS CJJ TAE GMP ICN CJU PEK PKX CSX TFU CKG DLC FOC CAN KWE HAK HGH HRB TNA KMG LHW NKG TAO PVG SHE SZX TSN URC WUH XMN XIY KUL SIN BNE SYD CNS DOH AUH DXB',
    'NGO':'FOC TAO LHW XIY PEK PKX PVG DLC TSN NKG SZX XMN SHE HGH CAN ICN GMP PUS CJJ KUL SIN',
    'ICN':'CAN NGO NKG DLC NRT HND PEK CTS PVG SZX XIY KIX OKA CSX TFU TSN HRB HGH FUK SIN CGK SYD',
    'PUS':'NRT KIX FUK CTS TAO XIY CAN BKI DPS',
}
# Historical 2018 government airport tables, explicitly resolved within major
# gateways. Beijing city entries become PEK/PKX candidates, not airport evidence
# for a then-unopened PKX. Ambiguous Shanghai entries use explicitly named PVG.
HISTORICAL = {
    'GMP':'HND KIX SHA PEK PKX',
    'PUS':'NRT KIX FUK NGO CTS OKA PEK PKX PVG TAO CAN HGH NKG SHE XIY SYX KUL BKI',
    'CJU':'NRT KIX NKG PEK PKX PVG NNG SZX WUH TSN SHE XIY KMG HGH KWE FOC KUL',
    'TAE':'KIX NRT FUK CTS OKA PEK PKX PVG SHE SYX',
    'CJJ':'KIX PEK PKX PVG HGH SHE HRB DLC',
}


def eligible(a, b):
    return (a['country'] in COUNTRIES and b['country'] in COUNTRIES and a['country'] != b['country']
            and all(x['country'] not in {'AE','QA'} or x['code'] in HUBS for x in (a,b))
            and not ({a['code'],b['code']} & {'MWX','ITM',*RETIRED_AIRPORTS}))


def prepare():
    airports, pairs, evidence, inputs = {}, set(), [], []
    paths = sorted(ROOT.glob('data/sources/*_international_routes.json')) + [ROOT/'data/sources/gulf_flights_routes.json']
    # Domestic catalogues supply exact identities for additional major gateways.
    for name in ['china','japan','south_korea']:
        d = json.loads((ROOT/f'data/sources/{name}_flights_routes.json').read_text())
        airports.update({a['code']:a for a in d['airports']})
    for path in paths:
        d = json.loads(path.read_text())
        airports.update({a['code']:a for a in d['airports']})
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        by_code = {a['code']:a for a in d['airports']}
        for a,b in d['routes']:
            if eligible(by_code[a],by_code[b]):
                pairs.add((a,b))
                evidence.append(dict(origin=a,destination=b,source=str(path.relative_to(ROOT)),kind='Existing published/probe candidate; not dated service evidence'))
    base_count = len(pairs)
    for table, historical in [(GATEWAYS,False),(HISTORICAL,True)]:
        for a, targets in table.items():
            for b in targets.split():
                if not eligible(airports[a],airports[b]):
                    raise ValueError(f'Outside network footprint: {a}-{b}')
                pairs.update([(a,b),(b,a)])
                evidence.append(dict(origin=a,destination=b,source=SOURCES['historical' if historical else a],
                    kind='Historical city/airport table, explicitly resolved search candidate' if historical else 'Official airport/airline route candidate; not dated nonstop evidence'))
    codes = {c for p in pairs for c in p}
    catalogue = []
    for code in sorted(codes):
        a = dict(airports[code]); a.pop('island_group',None)
        if a['country'] in PROFILES:a['timezone']=PROFILES[a['country']]['zone']
        if a['country']=='CN':a['timezone']='Asia/Shanghai'
        if a['country']=='IN':a['timezone']='Asia/Kolkata'
        catalogue.append(a)
    doc = dict(profile='international_network',scope='international',start_date='2026-11-02',end_date='2026-11-02',
        timezone='UTC',max_duration=86400,currency='mixed',countries=COUNTRIES,hubs=sorted(HUBS),
        base_directional_routes=base_count,airports=catalogue,routes=[list(p) for p in sorted(pairs)],
        evidence=evidence,input_manifests=inputs,source_urls=SOURCES,
        source_documents={k:dict(url=SOURCES[k],**v) for k,v in SOURCE_DOCUMENTS.items()},source_reviewed_date='2026-10-25',
        route_hash_basis='SHA256 of curated candidates and input manifest pins; not raw-page bytes',
        unresolved_airports=[],coverage_scope='Existing inter-country candidates plus major East Asian gateways; regional gaps remain')
    doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=evidence,inputs=inputs,documents=SOURCE_DOCUMENTS),sort_keys=True).encode()).hexdigest()
    output = ROOT/'data/sources/international_network_routes.json'
    output.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(dict(airports=len(catalogue),base_routes=base_count,routes=len(pairs))))


if __name__=='__main__':prepare()
