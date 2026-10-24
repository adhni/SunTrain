"""Targeted exact-airport Malaysian cross-border candidates, not schedule evidence."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from scripts.prepare_indonesia_international import COUNTRY_ZONES,AU_ZONES

SQ_URL='https://www.singaporeair.com/en_UK/my/plan-travel/local-promotions/malaysia/'
SCOOT_URL='https://www.flyscoot.com/flights/en-my/'
MH_URL='https://www.malaysiaairlines.com/hq/en/plan-trip/destinations.html'
AIRASIA_URL='https://www.airasia.com/flights/'
# Explicit gateway probes rather than every Malaysian airport against the world.
# A candidate is only accepted as a service after a dated exact-airport capture.
PROBES={
 'KUL':'''SIN BKK DMK HKT KBV CNX HDY URT USM HAN SGN DAD CXR DLI PQC VTE KTI SAI RGN BWN MNL CEB DVO CRK
 HKG MFM TPE KHH ICN PUS CJU NRT HND KIX CTS FUK OKA
 PEK PKX PVG CAN SZX XMN CTU TFU KMG HGH WUH CSX NNG HAK SYX FOC XIY CGO CKG KWL SWA WNZ NKG TNA TAO NGB TSN URC BAR
 DEL BOM BLR MAA HYD COK TRV TRZ CCU AMD ATQ DAC CMB MLE KTM KHI LHE ISB
 DXB AUH DOH MCT SHJ JED MED RUH DMM IST SAW TAS ALA ASB LHR LGW CDG AMS FRA AKL MRU''',
 'PEN':'SIN BKK DMK HKT HKG TPE ICN CAN SZX XMN PVG PKX TFU KMG DOH DXB MAA',
 'BKI':'SIN BWN HKG TPE ICN PUS NRT CAN SZX PVG PKX HGH WUH NNG KMG MNL DMK',
 'JHB':'SIN DMK BKK CAN HAK ICN',
 'KCH':'SIN BWN HKG CAN SZX DMK',
 'LGK':'SIN DXB SHJ DOH',
 'SZB':'SIN XSP DMK HKG',
 'TWU':'CAN NKG BWN',
 'KBR':'SIN',
}
EXTRA_ZONES={'MM':'Asia/Yangon','LA':'Asia/Vientiane','BD':'Asia/Dhaka','MV':'Indian/Maldives',
 'NP':'Asia/Kathmandu','PK':'Asia/Karachi','KZ':'Asia/Almaty','TM':'Asia/Ashgabat','MU':'Indian/Mauritius'}
ID_ZONES={'DPS':'Asia/Makassar','UPG':'Asia/Makassar','BPN':'Asia/Makassar','MDC':'Asia/Makassar',
 'PNK':'Asia/Pontianak','KTG':'Asia/Pontianak','DJJ':'Asia/Jayapura','AMQ':'Asia/Jayapura'}


def prepare():
    domestic=json.loads((ROOT/'data/sources/malaysia_flights_routes.json').read_text())
    known={a['code']:a for a in domestic['airports']}
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    pairs=set();evidence=[]
    def airport(code):
        if code in known:return known[code]
        matches=[a for a in rows if a['iata_code']==code and a['type']!='closed']
        if len(matches)!=1:raise ValueError(f'Unresolved exact airport {code}')
        a=matches[0];country=a['iso_country']
        zone=(AU_ZONES.get(code) if country=='AU' else ID_ZONES.get(code,'Asia/Jakarta') if country=='ID'
            else (COUNTRY_ZONES|EXTRA_ZONES).get(country))
        if not zone:raise ValueError(f'Unresolved airport time zone {code} ({country})')
        group='Peninsular Malaysia' if country=='MY' else 'Overseas'
        if country=='MY' and a['iso_region'] in {'MY-12','MY-13','MY-15'}:
            zone='Asia/Kuching';group='Sarawak' if a['iso_region']=='MY-13' else 'Sabah & Labuan'
        known[code]=dict(code=code,icao=a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,
            timezone=zone,island_group=group,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        return known[code]
    def add(a,b,source,kind):
        aa,bb=airport(a),airport(b)
        if (aa['country']=='MY')==(bb['country']=='MY'):raise ValueError('Not a Malaysian cross-border pair')
        pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=source,kind=kind))
    # Reuse already reviewed route candidates and their original source provenance.
    for name in ['australia','indonesia']:
        path=ROOT/f'data/sources/{name}_international_routes.json';source=json.loads(path.read_text())
        catalogue={a['code']:a for a in source['airports']}
        for a,b in source['routes']:
            if catalogue[a]['country']=='MY':
                if b not in known:known[b]=catalogue[b]
                add(a,b,source['route_source_url'],f'Reciprocal candidate from {path.name}; not current service evidence')
    for a,targets in PROBES.items():
        for b in targets.split():add(a,b,AIRASIA_URL if a!='KUL' else MH_URL,'Targeted gateway probe; not evidence of current nonstop service')
    for a in 'KUL PEN SZB IPH KCH BKI KUA LGK MKZ MYY SBW'.split():
        add(a,'SIN',SQ_URL,'Published Singapore Airlines/Scoot gateway; verify replay date')
    add('KBR','SIN',SCOOT_URL,'Published Scoot airport candidate; verify replay date')
    codes=sorted({c for pair in pairs for c in pair})
    result=dict(country='MY',scope='international',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Kuala_Lumpur',max_duration=86400,
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SQ_URL,
        route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated candidate evidence, not raw website bytes',source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
        airports=[known[c] for c in codes],routes=sorted(pairs),evidence=evidence,unresolved_airports=[],
        search_strategy='Both directions of published Singapore gateways, existing AU/ID reciprocal candidates and targeted gateway probes. Exact IATA only; no national airport/world Cartesian product. Probes are not proof of current service.')
    (ROOT/'data/sources/malaysia_international_routes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(codes),malaysian_airports=sorted(c for c in codes if known[c]['country']=='MY'),routes=len(pairs))))

if __name__=='__main__':prepare()
