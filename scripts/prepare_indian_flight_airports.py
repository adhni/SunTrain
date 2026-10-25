"""Pinned DGCA-derived city pairs are search candidates, never dated schedules."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL, AIRPORT_HASH, pinned_download
from scripts.prepare_gulf_airports import TZ_URL, TZ_HASH, NEW_ZONES

COMMIT = 'e197170f131e43169620e4f8aa520350d4cbcba9'
BASE = f'https://raw.githubusercontent.com/Vonter/india-aviation-traffic/{COMMIT}/aggregated'
HASHES = {'domestic': '6be5b6dfc4e163e5deac88ebca7421aacc527863dc90eecd4a5a61d525855246',
          'international': 'df95c0b5bc6615634ef05c31dc05d4d8281063b1d7a6ea1aa15333cc798a6cdb'}
# Explicit resolutions, rather than nearest-airport or fuzzy city matching.
# Ambiguous international city labels expand to separate exact-airport probes.
CITY_CODES = {
 'AIP':'ADAMPUR', 'IXA':'AGARTALA', 'AGX':'AGATTI ISLAND', 'AGR':'AGRA', 'AMD':'AHMEDABAD',
 'AJL':'AIZAWL', 'IXD':'ALLAHABAD (PRAYAGRAJ)|PRAYAGRAJ', 'AHA':'AMBIKAPUR|AMBIKAPUR AIRPORT',
 'AVR':'AMRAVATI|AMRAVATI AIRPORT', 'ATQ':'AMRITSAR', 'IXU':'AURANGABAD', 'AYJ':'AYODHYA|AYODHYA INTERNATIONAL AIRPORT',
 'IXB':'BAGDOGRA', 'BEK':'BAREILLY', 'BUP':'BATHINDA|BHATINDA', 'IXG':'BELGAUM', 'BLR':'BENGALURU|BANGALORE',
 'BHU':'BHAVNAGAR', 'BHO':'BHOPAL', 'BBI':'BHUBANESWAR', 'BHJ':'BHUJ', 'IXX':'BIDAR', 'BKB':'BIKANER',
 'PAB':'BILASPUR', 'IXC':'CHANDIGARH', 'MAA':'CHENNAI', 'CJB':'COIMBATORE', 'COH':'COOCH BEHAR',
 'CDP':'CUDDAPAH|CUDDAPAH (KADAPA)', 'NMB':'DAMAN', 'DBR':'DARBHANGA', 'DED':'DEHRADUN', 'DEL':'DELHI',
 'DGH':'DEOGHAR', 'DHM':'DHARAMSALA|DHARAMSHALA', 'DIB':'DIBRUGARH', 'DMU':'DIMAPUR', 'DIU':'DIU',
 'RDP':'DURGAPUR', 'DXN':'GAUTAM BUDDHA NAGAR', 'GAY':'GAYA', 'HDO':'GHAZIABAD|HINDON AIRPORT',
 'GOI':'DABOLIM|GOA (DABOLIM, SOUTH GOA)', 'GOX':'GOA (MOPA, NORTH GOA)', 'GDB':'GONDIA', 'GOP':'GORAKHPUR',
 'GBI':'GULBARGA|KALABURAGI', 'GAU':'GUWAHATI|GAWAHATI', 'GWL':'GWALIOR', 'HSR':'HIRASAR (RAJKOT)|RAJKOT INTERNATIONAL AIRPORT',
 'HSS':'HISAR|HISSAR', 'HBX':'HUBLI', 'HYD':'HYDERABAD', 'IMF':'IMPHAL', 'IDR':'INDORE', 'HGI':'ITANAGAR',
 'JLR':'JABALPUR', 'JGB':'JAGDALPUR', 'JAI':'JAIPUR', 'JSA':'JAISALMER', 'JLG':'JALGAON|JALGOAN',
 'IXJ':'JAMMU', 'JGA':'JAMNAGAR', 'IXW':'JAMSHEDPUR', 'PYB':'JEYPORE', 'JRG':'JHARSUGUDA', 'JDH':'JODHPUR',
 'JRH':'JORHAT', 'IXY':'KANDLA', 'CNN':'KANNUR', 'KNU':'KANPUR', 'IXK':'KESHOD', 'HJR':'KHAJURAHO',
 'KQH':'KISHANGARH', 'COK':'KOCHI', 'KLH':'KOLHAPUR', 'CCU':'KOLKATA', 'CCJ':'KOZHIKODE', 'KUU':'KULLU',
 'KJB':'KURNOOL', 'IXL':'LEH', 'IXI':'LILABARI', 'LKO':'LUCKNOW', 'LUH':'LUDHIANA', 'IXM':'MADURAI',
 'SDW':'MALVAN', 'IXE':'MANGALORE (MANGALURU)|MANGALORE', 'BOM':'MUMBAI (MUMBAI)|MUMBAI',
 'NMI':'MUMBAI (NAVI MUMBAI)', 'MYQ':'MYSORE', 'NAG':'NAGPUR', 'NDC':'NANDED', 'ISK':'NASHIK|NASIK',
 'PGH':'PANTNAGAR', 'IXT':'PASIGHAT|PASSIGHAT', 'PAT':'PATNA', 'PNY':'PONDICHERRY|PONDICHERRY (PUDUCHERRY)',
 'PBD':'PORBANDAR', 'IXZ':'PORT BLAIR', 'PNQ':'PUNE', 'RPR':'RAIPUR', 'RJA':'RAJAHMUNDRY', 'IXR':'RANCHI',
 'REW':'REWA', 'RRK':'ROURKELA', 'RUP':'RUPSI', 'SXV':'SALEM', 'SHL':'SHILLONG', 'SLV':'SHIMLA|SIMLA',
 'SAG':'SHIRDI', 'RQY':'SHIVAMOGGA|SHIVAMOGGA AIRPORT', 'IXS':'SILCHAR', 'SSE':'SOLAPUR|SHOLAPUR',
 'SXR':'SRINAGAR', 'STV':'SURAT', 'TEI':'TEZU', 'TRV':'THIRUVANANTHAPURAM|TRIVANDRUM',
 'TRZ':'TIRUCHIRAPPALLI|TIRUCHIRAPALLY', 'TIR':'TIRUPATI', 'TCR':'TUTICORIN', 'UDR':'UDAIPUR', 'UKE':'UTKELA',
 'BDQ':'VADODARA', 'VNS':'VARANASI', 'VDY':'VIDYANAGAR', 'VGA':'VIJAYWADA|VIJAYAWADA',
 'VTZ':'VISHAKHAPATNAM (VISAKHAPATNAM)|VISAKHAPATNAM', 'ZER':'ZIRO',
 'AUH':'ABUDHABI', 'ADD':'ADDIS ABABA', 'ADE':'ADEN', 'AAN':'AL AIN', 'ALA':'ALMATY', 'AMM':'AMMAN',
 'AMS':'AMSTERDAM', 'ASB':'ASHGABAT', 'ATH':'ATHENS', 'BGW':'BAGHDAD', 'BAH':'BAHRAIN', 'GYD':'BAKU',
 'BWN':'BANDAR SERI BEGAWAN', 'BKK':'BANGKOK', 'BHX':'BIRMINGHAM', 'BSZ':'BISHKEK', 'CAI':'CAIRO',
 'CBR':'CANBERRA', 'ORD':'CHICAGO', 'CMB':'COLOMBO', 'CPH':'COPENHAGEN', 'DMM':'DAMMAM',
 'DAR':'DAR ES SALAM', 'DPS':'DENPASAR', 'DAC':'DHAKA', 'DOH':'DOHA', 'DMK':'DON MUEANG, BANGKOK',
 'DXB':'DUBAI', 'DYU':'DUSHANBE', 'EBB':'ENTEBBE', 'FRA':'FRANKFURT', 'FJR':'FUJAIRAH',
 'GLU':'GELEPHU', 'CAN':'GUANGZHOU', 'HAQ':'HAA DHAALU ATOLL', 'HAN':'HANOI', 'HEL':'HELNSKI',
 'SGN':'HO CHI MINH CITY', 'HKG':'HONG KONG', 'IST':'ISTANBUL', 'JAF':'JAFFNA', 'JED':'JEDDAH',
 'KBL':'KABUL', 'KTM':'KATHMANDU', 'KBV':'KRABI', 'KUL':'KUALALUMPUR', 'KMG':'KUNMING', 'KWI':'KUWAIT',
 'LGK':'LANGKAWI', 'MAN':'MANCHESTER', 'MLE':'MALE', 'MNL':'MANILA', 'MED':'MEDINA', 'MEL':'MELBOURNE',
 'MXP':'MILAN', 'MSQ':'MINSK', 'YUL':'MONTREAL', 'MUC':'MUNICH', 'MCT':'MUSCAT', 'NBO':'NAIROBI',
 'NJF':'NAJF', 'NRT':'NARITA', 'JFK':'NEW YORK', 'EWR':'NEWARK, NEW YORK', 'OVB':'NOVOSIBIRSK',
 'OSS':'OSH', 'CDG':'PARIS', 'PBH':'PARO', 'PEN':'PENANG', 'KTI':'PHNOM PENH', 'HKT':'PHUKET',
 'MRU':'PORT LOUIS,MAURITIUS', 'RGN':'RANGOON', 'RKT':'RAS AL-KHAIMAH', 'RUH':'RIYADH', 'FCO':'ROME',
 'SFO':'SAN FRANCISCO', 'ICN':'SEOUL', 'SEZ':'SEYCHELLES', 'PVG':'SHANGHAI', 'SNN':'SHANNON',
 'SHJ':'SHARJAH', 'SAI':'SIEM REAP', 'SIN':'SINGAPORE', 'RUN':'ST-DENIS, REUNION', 'SYD':'SYDNEY',
 'CGK':'TANGERANG', 'TAS':'TASHKENT', 'TBS':'TBILISI', 'IKA':'TEHRAN', 'TLV':'TELAVIV',
 'HND':'TOKYO', 'YYZ':'TORONTO', 'YVR':'VANCOUVER', 'VIE':'VIENNA', 'WAW':'WARSAW',
 'SVX':'YEKATERINBURG', 'ZRH':'ZURICH',
}
ALIASES = {name: [code] for code, names in CITY_CODES.items() for name in names.split('|')}
ALIASES.update({'GOA':['GOI','GOX'], 'LONDON':['LHR','LGW'], 'MOSCOW':['SVO','DME','VKO'], 'TOKYO':['HND','NRT']})


def prepare():
    cache = ROOT / '.cache/india-flights-audit'
    for directory in (cache, ROOT/'.cache/australia-flights-audit', ROOT/'.cache/gulf-flights-audit'):
        directory.mkdir(parents=True, exist_ok=True)
    raw = pinned_download(AIRPORT_URL, ROOT / '.cache/australia-flights-audit/ourairports-airports.csv', AIRPORT_HASH)
    active = {}
    for a in csv.DictReader(raw.open(encoding='utf-8-sig')):
        if a['iata_code'] and a['type'] != 'closed': active.setdefault(a['iata_code'], []).append(a)
    tzraw = pinned_download(TZ_URL, ROOT / '.cache/gulf-flights-audit/openflights-airports.dat', TZ_HASH)
    zones = {r[4]: r[11] for r in csv.reader(tzraw.open()) if len(r)>11 and r[11]!='\\N' and any(r[5] in (a.get('icao_code'),a['ident']) for a in active.get(r[4],[]))}
    for p in sorted((ROOT/'data/sources').glob('*routes.json')):
        if p.name.startswith('india_'): continue
        zones.update({a['code']:a['timezone'] for a in json.loads(p.read_text()).get('airports',[])})
    zones.update(NEW_ZONES)
    zones.update({'GLU':'Asia/Thimphu','HAQ':'Indian/Maldives','FJR':'Asia/Dubai','SAI':'Asia/Phnom_Penh','KTI':'Asia/Phnom_Penh','BSZ':'Asia/Bishkek'})
    zones.update({code:'Asia/Kolkata' for code, rows in active.items() if all(a['iso_country']=='IN' for a in rows)})
    def airport(code):
        rows=active.get(code,[])
        if len(rows)!=1 or code not in zones: raise ValueError(f'Unresolved airport or zone: {code}')
        a=rows[0];ZoneInfo(zones[code])
        return dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=a['iso_country'],timezone=zones[code],mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
    for scope in ('domestic','international'):
        url=f'{BASE}/{scope}/city.csv'
        path=pinned_download(url,cache/f'{scope}-city.csv',HASHES[scope])
        evidence=[];pairs=set();unresolved=set();weights={};excluded=set()
        def add(a,b,source,kind,weight=0):
            if a==b:return
            aa,bb=airport(a),airport(b)
            if scope=='domestic' and not aa['country']==bb['country']=='IN':raise ValueError('Domestic country mismatch')
            if scope=='international' and (aa['country']=='IN')==(bb['country']=='IN'):raise ValueError(f'International country mismatch: {a} {b}')
            pairs.update([(a,b),(b,a)])
            for key in [(a,b),(b,a)]:weights[key]=weights.get(key,0)+weight
            evidence.append(dict(origin=a,destination=b,source=source,kind=kind))
        seen=set()
        for row in csv.DictReader(path.open()):
            weight=sum(float(row[k] or 0) for k in ('PaxToCity2','PaxFromCity2'))
            if int(row['Year'])%100!=26 or weight<=0:continue
            names=[row[k].strip().upper() for k in ('City1','City2')]
            for name in names:
                if name not in ALIASES:unresolved.add(name)
            if any(name not in ALIASES for name in names):continue
            for a,b in itertools.product(*(ALIASES[name] for name in names)):
                if scope=='international' and (airport(a)['country']=='IN')==(airport(b)['country']=='IN'):
                    excluded.add((a,b));continue
                key=tuple(sorted((a,b)))
                if key not in seen:
                    add(a,b,url,'2026 positive passenger city pair from DGCA-derived mirror; exact-airport candidates, not current/nonstop evidence',weight);seen.add(key)
                else:
                    for direction in [(a,b),(b,a)]:weights[direction]=weights.get(direction,0)+weight
        if scope=='domestic':
            # Cross-region and new-airport validation probes; explicitly not route evidence.
            for a,b in [('DEL','BOM'),('BLR','MAA'),('COK','AGX'),('GAU','TEI')]:
                add(a,b,'https://plone.allianceair.in/allianceair/en/pages/schedule','Representative or exact-airport probe; only dated capture establishes service')
            for code in 'ATQ BLR BEK BHO DHM HYD JAI IXJ JDH KQH LKO BOM PGH SXR'.split():
                add('DXN',code,'https://www.niairport.in/en/passengers/fly/flightinformation/destinations','Official airport destination candidate; not dated flight evidence')
        else:
            source='https://www.adairports.ae/en/pressrelease/2026/08/air-india-express-expands-network-at-zayed-international-airport'
            for code in ['NMI','IDR','LKO','GAU']:
                add(code,'AUH',source,'August 2026 airport announcement of direct routes; not dated flight evidence')
            for code in ['DXB','BKK']:
                add('NMI',code,'https://flights.airindiaexpress.com/en-in/flights-from-navi-mumbai','Airline destination-page candidate; may include connections, not nonstop evidence')
            for name in ('gulf_flights','singapore_international','australia_international','indonesia_international','malaysia_international'):
                p=ROOT/f'data/sources/{name}_routes.json';m=json.loads(p.read_text());cat={a['code']:a for a in m['airports']}
                for a,b in m['routes']:
                    if (cat[a]['country']=='IN')!=(cat[b]['country']=='IN'):
                        if a>b:continue
                        add(a,b,m['route_source_url'],f'Reciprocal candidate from {p.name}')
            # Air India's official exact-airport route map supplements the statistics.
            source='https://www.airindia.com/content/dam/air-india/newsroom/press-kits/pdfs/Air-India-International-Route-Map-March-2026.pdf'
            for code in 'AMS CPH FRA MXP CDG FCO VIE ZRH BHX LHR ORD EWR JFK SFO YYZ YVR DOH DXB JED RUH TLV HKG ICN PVG HND DPS BKK SGN KUL MNL HKT SIN MEL SYD CMB DAC KTM MLE RGN'.split():
                add('DEL',code,source,'Published exact-airport map candidate; not dated flight evidence')
            add('BOM','DMM',source,'Published exact-airport map candidate; not dated flight evidence')
        ordered=sorted(pairs,key=lambda p:(-weights.get(p,0),p))
        airports=[airport(c) for c in sorted({c for p in pairs for c in p})]
        result=dict(country='IN',scope=scope,start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Kolkata',max_duration=86400 if scope=='international' else 28800,currency='USD',
            airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,timezone_source_url=TZ_URL,timezone_source_sha256=TZ_HASH,
            route_source_url=url,route_source_sha256=HASHES[scope],route_source_origin='DGCA / Ministry of Civil Aviation statistics, community mirror pinned by commit and SHA256',
            route_hash_basis='Raw pinned CSV bytes; city-pair statistics supply candidates, never dated schedules',source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
            candidate_year=2026,excluded_non_india_pairs=sorted(excluded),airports=airports,routes=ordered,evidence=sorted(evidence,key=lambda e:(e['origin'],e['destination'],e['source'])),unresolved_airports=sorted(unresolved))
        output=ROOT/f'data/sources/india_{"flights" if scope=="domestic" else "international"}_routes.json'
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(scope=scope,airports=len(airports),routes=len(pairs),unresolved=sorted(unresolved))))


if __name__=='__main__':prepare()
