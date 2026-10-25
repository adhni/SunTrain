"""Focused, exact-airport Singapore flight candidates; never timetable evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from scripts.prepare_gulf_airports import TZ_URL,TZ_HASH

SIA_URL='https://www.singaporeair.com/sg/en/plan-travel/destinations/'
SCOOT_URL='https://cdn.flyscoot.com/prod/images/default-source/where-we-fly/scoot-network-aug26.webp'
SELETAR_URL='https://www.seletarairport.com/commercial-flights.html'
# Curated SQ/TR entries, excluding the destination directory's partner-only list.
# Metropolitan codes NYC/BJS/TYO are deliberately resolved to separate airports.
SIA='''ADL AMD AMS AKL BWN BKK BCN PEK PKX BLR BNE BRU PUS CNS CPT CEB TFU MAA CKG CHC CMB CPH DAD DRW DEL DPS DAC DXB FRA FUK CAN KWE HGH HAN SGN HKG HYD IST CGK JNB KTM COK CCU KUL SZB LHR LGW LAX MLE MAN MEL MXP BOM MUC NGO JFK EWR KIX CDG PEN PER KTI HKT FCO SFO SEA ICN PVG SZX SAI SUB SYD TPE HND NRT XMN RGN FOC HAK NKG NNG TAO SWA SHE TSN WUH XIY CGO OKA CTS MFM CJU BPN LBJ LOP KJT UPG MDC PDG PLM PKU PNK SRG TJQ YIA VTE BTU IPH KBR BKI KUA KCH LGK MKZ MYY SBW CRK MPH DVO ILO CNX CEI HDY KBV CXR PQC ATH ATQ VTZ CJB TRZ TRV JED'''
SCOOT='''ATQ VTZ MAA CJB TRZ TRV CEI CNX USM HKT HDY KBV LGK PEN KBR IPH KUA SZB KUL MKZ KCH SBW MYY BKI KNO BPN UPG MDC CGK KJT YIA SUB DPS LOP LBJ PKU PDG PLM PNK TJQ SRG HAN DAD CXR SGN PQC VTE MNL CRK ILO CEB DVO HAK HKG MFM TPE FOC CAN NNG CSX KMG KWE WUH NKG XIY CGO TAO TSN SHE HGH SWA ICN CJU KIX NRT HND OKA CTS PER MEL SYD ATH VIE JED'''
# Other-carrier and newer gateway probes. Inclusion is not proof of direct service.
PROBES='''MNL KNO ADD AUH BAH DOH HEL YVR DIL POM NOU NAN MRU MCT RUH VVO DMK KHH LPQ MDL KHN NGB WNZ WUX JJN TNA HFE HRB CGQ LHW YIH DYG INC SYX UBN VGA IXM IXZ CCJ IXE BBI PNQ LKO JAI IXB MAD'''


def prepare():
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as f:all_airports=list(csv.DictReader(f))
    active={}
    for a in all_airports:
        if a['iata_code'] and a['type']!='closed':active.setdefault(a['iata_code'],[]).append(a)
    tzraw=pinned_download(TZ_URL,ROOT/'.cache/gulf-flights-audit/openflights-airports.dat',TZ_HASH)
    with tzraw.open() as f:rows=list(csv.reader(f))
    zones={r[4]:r[11] for r in rows if len(r)>11 and r[11]!='\\N' and any(r[5] in (a.get('icao_code'),a['ident']) for a in active.get(r[4],[]))}
    for name in ['australia','indonesia','malaysia','gulf']:
        for kind in ['flights','international']:
            p=ROOT/f'data/sources/{name}_{kind}_routes.json'
            if p.exists():zones.update({a['code']:a['timezone'] for a in json.loads(p.read_text())['airports']})
    overrides={'SIN':'Asia/Singapore','XSP':'Asia/Singapore','UBN':'Asia/Ulaanbaatar','DIL':'Asia/Dili',
        'INC':'Asia/Shanghai','VGA':'Asia/Kolkata','IXZ':'Asia/Kolkata'}
    zones.update(overrides)
    pairs=set();evidence=[]
    def add(hub,code,source,kind):
        if hub==code:return
        if code in {'SIN','XSP'}:raise ValueError('No domestic Singapore service candidates')
        pairs.update([(hub,code),(code,hub)])
        evidence.append(dict(origin=hub,destination=code,source=source,kind=kind))
    for codes,url,kind in [(SIA,SIA_URL,'SQ/TR directory entry; not dated nonstop evidence'),(SCOOT,SCOOT_URL,'August 2026 network map candidate; not dated nonstop evidence'),(PROBES,SIA_URL,'Supplemental exact-airport probe; not proof of published/current service')]:
        for code in codes.split():add('SIN',code,url,kind)
    add('XSP','SZB',SELETAR_URL,'Published Seletar commercial route candidate; not dated flight evidence')
    for name in ['australia','indonesia','malaysia','gulf']:
        p=ROOT/f'data/sources/{name}_{"flights" if name=="gulf" else "international"}_routes.json';m=json.loads(p.read_text())
        for a,b in m['routes']:
            if a in {'SIN','XSP'}:add(a,b,m['route_source_url'],f'Reciprocal candidate from {p.name}')
            elif b in {'SIN','XSP'}:add(b,a,m['route_source_url'],f'Reciprocal candidate from {p.name}')
    airports=[]
    for code in sorted({c for pair in pairs for c in pair}):
        candidates=active.get(code,[])
        if len(candidates)!=1:raise ValueError(f'Ambiguous or unresolved airport: {code}')
        a=candidates[0];zone=zones.get(code)
        if not zone:raise ValueError(f'Unresolved timezone: {code}')
        ZoneInfo(zone)
        airports.append(dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=a['iso_country'],timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg'])))
    m=dict(country='SG',scope='international',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Singapore',max_duration=86400,currency='USD',
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,timezone_source_url=TZ_URL,timezone_source_sha256=TZ_HASH,timezone_overrides=overrides,
        route_source_url=SIA_URL,route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),route_hash_basis='Curated exact-airport candidates and explicit probes; not raw website bytes',
        source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',airports=airports,routes=sorted(pairs),evidence=evidence,unresolved_airports=[])
    (ROOT/'data/sources/singapore_international_routes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(airports),routes=len(pairs))))


if __name__=='__main__':prepare()
