"""Focused mainland-China domestic candidates; publications are not timetables."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL, AIRPORT_HASH, pinned_download

AIRCHINA_URL = 'https://webresource.airchina.com.cn/zh-CN/content/marketing/yxhdymjh/2025scck/'
CAAC_URL = 'https://www.caac.gov.cn/XXGK/XXGK/TZTG/201811/P020181115387162391198.pdf'
REGIONS = {
    'North':'PEK PKX TSN', 'Northeast':'SHE DLC HRB',
    'East':'SHA PVG HGH NKG XMN FOC TAO TNA', 'Central':'WUH CSX CGO',
    'South':'CAN SZX NNG HAK SYX', 'Southwest':'CTU TFU CKG KMG KWE',
    'Northwest':'XIY URC LHW',
}
CITIES = {
    'Beijing':['PEK','PKX'], 'Shanghai':['SHA','PVG'], 'Chengdu':['CTU','TFU'],
    **{c:[c] for c in 'CAN SZX KMG CKG XIY HGH XMN CSX WUH TAO SYX HAK DLC KWE FOC CGO NKG TNA'.split()},
}
# Historical CAAC city-pair table: a small candidate list, not current schedules
# or service-frequency evidence. Multi-airport cities expand into exact queries.
CITY_PAIRS = {
    'Beijing':'Shanghai CAN Chengdu SZX KMG CKG XIY HGH XMN CSX WUH TAO SYX HAK DLC KWE FOC',
    'Shanghai':'CAN Chengdu SZX KMG CKG XIY XMN CSX WUH TAO CGO SYX HAK DLC KWE FOC',
    'CAN':'Chengdu KMG CKG XIY HGH XMN TAO NKG SYX HAK DLC FOC TNA',
}
# Airport-specific Air China 2025 product route table, curated to the 30 airports.
# The product has expired; these are search candidates, never fare evidence.
EXACT_PAIRS = {
    'PEK':'SHA PVG HGH CTU TFU CKG CAN SZX XMN FOC SYX HAK NKG XIY LHW CSX SHE DLC NNG KWE KMG CGO TAO HRB WUH',
    'PKX':'PVG HGH TFU CKG HAK XIY LHW CSX SHE KWE KMG HRB',
    'TSN':'SHA PVG HGH CTU TFU CAN XMN FOC HAK CSX DLC NNG HRB WUH',
    'CTU':'CAN SZX HGH SHA PVG TAO NKG FOC URC',
    'TFU':'CAN SZX HGH PVG TNA NKG URC LHW KMG',
    'SHA':'CAN', 'PVG':'CAN SZX HRB SHE DLC HAK',
    'HGH':'CAN SZX DLC HRB KMG HAK', 'CKG':'URC',
    'WUH':'SHE CAN XMN HAK', 'HAK':'DLC',
}


def prepare():
    regions = {code:region for region,codes in REGIONS.items() for code in codes.split()}
    cache = ROOT / '.cache/australia-flights-audit'; cache.mkdir(parents=True, exist_ok=True)
    raw = pinned_download(AIRPORT_URL, cache/'ourairports-airports.csv', AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    airports = []
    for code in sorted(regions):
        matches = [a for a in rows if a['iata_code']==code and a['iso_country']=='CN' and a['type']!='closed']
        if len(matches)!=1:
            raise ValueError(f'Ambiguous or unresolved airport: {code}')
        a = matches[0]
        # Airline schedules use China standard time, including Urumqi. Do not
        # substitute Asia/Urumqi's UTC+6 civil-clock convention for flight times.
        airports.append(dict(code=code, icao=a.get('icao_code') or a['ident'],
            name=f"{a['name']} ({code})", municipality=a['municipality'], country='CN',
            timezone='Asia/Shanghai', island_group=regions[code], mode='flight',
            lat=float(a['latitude_deg']), lon=float(a['longitude_deg'])))
    pairs = set(); evidence = []
    def add(a,b,url,kind):
        if a==b or a not in regions or b not in regions:
            raise ValueError(f'Candidate outside the selected mainland airport set: {a}-{b}')
        pairs.update([(a,b),(b,a)])
        evidence.append(dict(origin=a,destination=b,source=url,kind=kind))
    for city, destinations in CITY_PAIRS.items():
        for destination in destinations.split():
            for a in CITIES[city]:
                for b in CITIES[destination]:
                    add(a,b,CAAC_URL,'Historical 2018 city-pair candidate expanded to exact airports; no claim that every airport combination operates')
    for a,destinations in EXACT_PAIRS.items():
        for b in destinations.split():
            add(a,b,AIRCHINA_URL,'Airport-specific 2025 route candidate from an expired product; not dated service or price evidence')
    add('CAN','URC','https://www.caac.gov.cn/English/BeltAndRoad/202606/t20260604_230981.html',
        'Published 2026 domestic leg of a longer international routing; domestic search verifies standalone dated segments')
    add('SHA','LHW','https://www.ceair.com/global/static/AboutChinaEasternAirlines/intoEasternAirlines/InvestorRelations/announcement/ShanghaiExchangeReleased/shExcReleased2026/202601/P020260115596082764942.pdf',
        'Published China Eastern route candidate; no dated schedule or aircraft inference')
    add('PVG','LHW','https://flights.ch.com/flight-date/SHA-LHW/',
        'Spring route page identifies Pudong explicitly despite its SHA city slug; older dates are candidates only')
    manifest = dict(country='CN',scope='domestic',start_date='2026-11-02',end_date='2026-11-02',
        timezone='Asia/Shanghai',currency='USD',max_duration=8*3600,
        coverage_scope='Selected major mainland airports and published route candidates; small airports and international/regional connections deferred',
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,
        route_source_url=AIRCHINA_URL,route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated candidate evidence and explicit city-to-airport expansion, not raw webpage bytes',
        source_documents=[dict(url=AIRCHINA_URL,sha256='0d9e3261fccd255474e935b53d118fc777e49402c6f819c4b7c794d0883b3450',purpose='Reviewed 2025 route-table HTML; expired product, candidates only')],
        source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
        airports=airports,routes=sorted(pairs),evidence=evidence,deferred_airports=[],unresolved_airports=[])
    (ROOT/'data/sources/china_flights_routes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(airports),directional_routes=len(pairs))))


if __name__=='__main__':
    prepare()
