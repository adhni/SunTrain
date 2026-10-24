"""Build targeted Australian cross-border candidates from pinned BITRE passenger pairs.

Preparation only: PYTHONPATH=.cache/excel-tools .venv/bin/python scripts/prepare_australia_international.py
City-pair statistics are candidates, never dated/nonstop schedule evidence.
"""
import csv
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_HASH, AIRPORT_URL, pinned_download
from scripts.prepare_indonesia_international import COUNTRY_ZONES
from scripts.prepare_google_flights import ZONES

SOURCE_URL = 'https://www.bitre.gov.au/sites/default/files/documents/International_airline_activity_0726.xlsx'
SOURCE_HASH = 'ea1c46bd8c436f713fa0d1b0354da8afc3b76e3efb2ce2b403339885ee4c2c25'
AU_PORTS = dict(zip(['Adelaide','Brisbane','Cairns','Canberra','Darwin','Gold Coast','Melbourne','Newcastle','Perth','Sunshine Coast','Sydney'], 'ADL BNE CNS CBR DRW OOL MEL NTL PER MCY SYD'.split()))
# Explicit airport mappings: no metropolitan/city-code Google searches.
FOREIGN_PORTS = {
 'Abu Dhabi':'AUH','Apia':'APW','Auckland':'AKL','Bandar Seri Begawan':'BWN',
 'Bangalore':'BLR','Bangkok':'BKK DMK','Beijing':'PEK PKX','Chengdu':'TFU CTU',
 'Christchurch':'CHC','Colombo':'CMB','Dallas':'DFW','Denpasar':'DPS','Dili':'DIL',
 'Doha':'DOH','Dubai':'DXB','Dunedin':'DUD','Espiritu Santo':'SON','Guangzhou':'CAN',
 'Haikou':'HAK','Hamilton':'HLZ','Hangzhou':'HGH','Hanoi':'HAN','Ho Chi Minh City':'SGN',
 'Hong Kong':'HKG','Honiara':'HIR','Honolulu':'HNL','Istanbul':'IST','Jakarta':'CGK',
 'Jinan':'TNA','Johannesburg':'JNB','Kuala Lumpur':'KUL','London':'LHR',
 'Los Angeles':'LAX','Manila':'MNL','Mauritius':'MRU','Munda':'MUA','Nadi':'NAN',
 'Nanjing':'NKG','Nauru':'INU','New Delhi':'DEL','New York':'JFK','Noumea':'NOU',
 'Osaka':'KIX','Palau':'ROR','Paris':'CDG','Phuket':'HKT','Port Moresby':'POM',
 'Port Vila':'VLI','Qingdao':'TAO','Queenstown':'ZQN','Rarotonga':'RAR','Rome':'FCO',
 'San Francisco':'SFO','Santiago':'SCL','Seoul':'ICN','Shanghai':'PVG SHA',
 'Shenzhen':'SZX','Singapore':'SIN','Taipei':'TPE','Tokyo':'HND NRT',
 'Tongatapu':'TBU','Toronto':'YYZ','Vancouver':'YVR','Wellington':'WLG',
 'Wuhan':'WUH',"Xi'an":'XIY','Xiamen':'XMN',
}
EXTRA_ZONES = {'FJ':'Pacific/Fiji','WS':'Pacific/Apia','VU':'Pacific/Efate',
 'SB':'Pacific/Guadalcanal','NR':'Pacific/Nauru','NC':'Pacific/Noumea',
 'PW':'Pacific/Palau','CK':'Pacific/Rarotonga','TO':'Pacific/Tongatapu',
 'ZA':'Africa/Johannesburg','MU':'Indian/Mauritius','CL':'America/Santiago',
 'IT':'Europe/Rome'}
AIRPORT_ZONES = {'LAX':'America/Los_Angeles','SFO':'America/Los_Angeles',
 'DFW':'America/Chicago','JFK':'America/New_York','HNL':'Pacific/Honolulu',
 'YVR':'America/Vancouver','YYZ':'America/Toronto','WSI':'Australia/Sydney',
 'DPS':'Asia/Makassar','CGK':'Asia/Jakarta'}
SUPPLEMENTS = [
 ('AVV','DPS','https://avalonairport.com.au/flights/airlines-schedules/'),
 ('HBA','AKL','https://hobartairport.com.au/travellers/destinations/'),
 ('WSI','AKL','https://www.wsiairport.com.au/faqs?page=1'),
 ('ADL','CHC','https://southaustralia.com/plan-a-trip/fly-to-adelaide-south-australia'),
 ('PER','CDG','https://www.qantas.com/en-au/where-we-fly/international-flight-routes'),
]
EXCLUSIONS = [
 dict(airport='WSI', destination='SIN', reason='Published start 23 November 2026 is after replay date', source='https://www.destinationnsw.com.au/newsroom/western-sydney-to-open-to-passengers-on-25-october-2026'),
 dict(airport='ADL', destination='SFO', reason='Published seasonal service December to February, outside replay date', source='https://southaustralia.com/plan-a-trip/fly-to-adelaide-south-australia'),
 dict(airport='NTL', destination='SIN', reason='Published service via DPS; search nonstop NTL-DPS only', source='https://www.newcastleairport.com.au/flights/our-destinations/'),
 dict(airport='MCY', destination='SIN', reason='Published service via DPS; search nonstop MCY-DPS only', source='https://www.sunshinecoastairport.com.au/flights/our-destinations/bali-singapore/'),
 dict(airport='ADL', destination='HKG', reason='Published seasonal return 10 November 2026 is after replay date', source='https://tourism.sa.gov.au/news-articles/tourism-and-trade-boom-with-more-hong-kong-to-adelaide-flights-this-summer'),
 dict(airport='MEL', destination='ICN', reason='Published seasonal return 18 December 2026 is after replay date', source='https://www.melbourneairport.com.au/corporate/Korean-Air-set-to-land-at-Melbourne-Airport'),
]


def prepare():
    import openpyxl
    (ROOT/'.cache/australia-international-audit').mkdir(parents=True,exist_ok=True)
    (ROOT/'.cache/australia-flights-audit').mkdir(parents=True,exist_ok=True)
    path = pinned_download(SOURCE_URL, ROOT/'.cache/australia-international-audit/bitre-2026-07.xlsx', SOURCE_HASH)
    airport_file = pinned_download(AIRPORT_URL, ROOT/'.cache/australia-flights-audit/ourairports-airports.csv', AIRPORT_HASH)
    with airport_file.open(encoding='utf-8-sig') as f:
        catalogue = list(csv.DictReader(f))
    with gzip.open(ROOT/'data/reference/australia_flights/2026-11-02.json.gz','rt') as f:
        known={a['code']:{**a,'country':'AU'} for a in json.load(f)['airports']}
    pairs,evidence,unresolved=set(),[],[]
    def airport(code):
        if code in known:return known[code]
        rows=[a for a in catalogue if a['iata_code']==code and a['type']!='closed']
        if len(rows)!=1:raise ValueError(f'Unresolved exact airport {code}')
        a=rows[0];country=a['iso_country']
        zone=AIRPORT_ZONES.get(code) or (ZONES.get(code) if country=='AU' else (EXTRA_ZONES|COUNTRY_ZONES).get(country))
        if not zone:raise ValueError(f'Unresolved time zone {code} ({country})')
        known[code]=dict(code=code,icao=a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,
            timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        return known[code]
    def add(a,b,source,**details):
        try:
            aa,bb=airport(a),airport(b)
            if (aa['country']=='AU')==(bb['country']=='AU'):raise ValueError('Not an Australian cross-border pair')
            pairs.update([(a,b),(b,a)])
            evidence.append(dict(origin=a,destination=b,source=source,**details))
        except ValueError as error:unresolved.append(dict(origin=a,destination=b,reason=str(error)))
    port=None
    book=openpyxl.load_workbook(path,data_only=True,read_only=True)
    for index,row in enumerate(book['Table_5'].values,1):
        foreign,local=row[:2]
        if local:port=local
        if port not in AU_PORTS or foreign in (None,'Total'):continue
        if not any(isinstance(v,(int,float)) and v>0 for v in row[6:9]):continue
        if foreign not in FOREIGN_PORTS:
            unresolved.append(dict(australian_city=port,foreign_city=foreign,row=index,reason='Unmapped BITRE city'))
            continue
        for code in FOREIGN_PORTS[foreign].split():
            add(AU_PORTS[port],code,SOURCE_URL,sheet='Table_5',row=index,foreign_city=foreign,australian_city=port,passengers_2026=row[8])
    book.close()
    for a,b,url in SUPPLEMENTS:add(a,b,url,kind='published airport destination')
    # WSI must never silently disappear because a pinned catalogue predates opening.
    if any(r['origin']=='WSI' for r in unresolved):raise ValueError('Pinned airport catalogue cannot resolve WSI')
    codes=sorted({c for pair in pairs for c in pair})
    result=dict(country='AU',scope='international',start_date='2026-11-02',end_date='2026-11-02',
        timezone='Australia/Melbourne',max_duration=86400,airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,
        route_source_url=SOURCE_URL,route_source_sha256=SOURCE_HASH,route_source_period='2026-07',
        source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
        airports=[known[c] for c in codes],routes=sorted(pairs),evidence=evidence,unresolved_airports=unresolved,excluded_candidates=EXCLUSIONS,
        search_strategy='Only reported passenger city pairs and explicit dated airport supplements; both directions, exact IATA airports. No domestic-airport Cartesian product. City-pair traffic may include stops; only dated exact-airport segments are retained.')
    target=ROOT/'data/sources/australia_international_routes.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(codes),australian_airports=sorted(c for c in codes if known[c]['country']=='AU'),routes=len(pairs),unresolved=unresolved)))

if __name__=='__main__':prepare()
