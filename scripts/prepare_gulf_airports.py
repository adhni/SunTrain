"""Curated official network candidates for DXB, AUH and DOH; no invented schedules."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

HUBS=['DXB','AUH','DOH']
SOURCE_URLS={
 'DXB':'https://c.ekstatic.net/ecl/documents/partners/ek-fz-network.pdf',
 'AUH':'https://www.zayedinternationalairport.ae/en/flights-and-check-in/destination-and-airlines/destinations',
 'DOH':'https://www.qatarairways.com/content/dam/corporate/images/551_networkroutemap_global.pdf',
}
# Exact airport resolutions of published map labels; ambiguous cities have
# separately listed airport candidates. Maps may contain seasonal/upcoming/via
# routes, so only dated exact-airport captures establish retained services.
DESTINATIONS={
 'DXB':'''BEY IKA MCT RUH MED JED DMM KWI BSR BGW AMM BAH TLV YYZ CDG ATH FCO ICN KIX TPE NRT HND GLA MAN LHR LGW MXP LCA ZRH AMS SIN KUL MNL CGK DAR HKG HGH DAC MEL SYD BNE PER AKL CHC LHE ISB SKT KHI CMB JFK BOS YUL IAD MAD GRU DUB BRU SGN CRK ORD BCN LAX HAN CAI TUN MLE ADD OSL CAN SZX SAI DAD NBO SEZ ARN LIS PEW IAH BHX CEB DSS CKY BKK DAM LUN ACC ABJ LOS ABV SVO DME VKO CMN HRE MRU TNR JNB CPT DUR EBB GVA HAM BLQ DUS FRA PRG VIE BUD MUC WAW CPH IST SAW SFO SEA DFW LYS EWR LAD MCO MEX VCE HKT MIA NCE MLA NCL EDI LED GIG EZE DPS PVG PEK ADL KTI ALG BOG CCU DEL TRV BLR MAA OVB VOG NQZ TAS CIT DYU FRU HYD ALA ASB SKD SVX MCX TBS AER EVN GYD TBZ MHD KBL NJF SYZ BUZ KER BND GSM KIH HGA JIB ASM ZNZ LRR EBL AJF ISU MRV MSQ TIA CFU DBB HBE SPX ULH YNB JMK CTA NAP SZG TZX BUS JTR BJV AYT ESB SOF KRK BEG TIV KUF KZN BSL UFA CGP BOM AMD COK CCJ OTP UET MUX RSI LYP LKO KTM ZAG SJJ IFN SLL LJU ELQ TUU TIF DOH AHB GIZ EAM MBA HAS AQI NUM KBV HOF LGK OLB POZ DBV PSA PEN''',
 'AUH':'''LHR BOM COK DEL BKK DME SVO VKO DOH CAI BLR JED IST SAW MAA HKT BAH RUH HYD CCJ CMB AMD CDG KWI MAN TRV TLV ISB MNL MAD CGK MLE FRA MUC DMM BCN JFK MXP KUL MCT FCO DUB YYZ ZRH AMM KHI SYD ICN SIN LHE IXE NRT ORD AMS DPS VIE BRU ATL BEY LIS IAD MEL BOS CNN PEW PKX CCU CMN DAC ADD TPE HAN JAI ATH GVA PVG JNB WAW HKG DUS CPH PRG BUD KRK KTW KTM KBV NBO EVN SEZ HBE TBS LED GYD KIX SKT LKO MED CJB DAM MUX VTZ CNX TAS SLL BBI SCT LCA TUN AER ALA KTI TRZ IXC LYP BER IXM KNO ATZ CGP SOF HAK ASB ELQ ESB''',
 'DOH':'''ATL BOS ORD DFW IAH LAX MIA YUL JFK SFO GRU SEA IAD KAN JRO LOS LAD LUN MPM RAK MGQ NBO PHC SEZ TUN ZNZ ABJ ABV ACC ADD HBE ALG CAI CPT CMN DAR JIB DUR EBB HRE JNB ADL AMD ATQ AKL BLR BKK PEK PKX BNE CEB TFU CTU MAA CKG CRK CMB DVO DEL DPS DAC GOX GOI CAN HGH HAN SGN HKG HYD ISB CGK KHI KTM COK CCU CCJ KUL LHE MLE MNL KNO MEL MUX BOM NAG KIX PEN PER PEW KTI PNH HKT ICN PVG SKT SIN SYD TRV NRT ADA COV AMS ESB AYT ATH BCN BEG BER BHX BJV BRU OTP BUD CPH DUB DUS EDI FRA GVA HAM IST SAW LCA LIS LGW LHR LYS MAD AGP MAN MXP SVO DME MUC JMK NCE OSL CDG PRG FCO SJJ SOF ARN TLS TZX VCE VIE WAW ZAG ZRH AUH ULH ALA AMM BGW GYD BSR BEY DMM DXB EBL ELQ IFN JED KWI MED BAH MHD MCT NJF NUM RUH SLL SHJ SYZ ISU TUU TIF TAS IKA TBS YNB EVN''',
}
# Explicit additional gateway probes supplement other airlines and newer routes.
PROBES={'DXB':'CNN TRZ IXE GOI GOX IXC JAI ATQ VNS IXB IXR BBI PNQ PAT RPR STV DMK',
 'DOH':'YYZ PZU HND'}
SUPPLEMENTS=[
 ('DXB','HEL','https://cd1.mediaoffice.ae/en/news/2026/january/13-01/emirates-to-launch-flight'),
 ('DXB','RIX VNO BGY IAS KRR ROV PKR BEN ALP','https://www.flydubai.com/en-gb/destinations/airports/'),
 ('DOH','FIH NBJ AHB HAS RSI','https://dmassets.qatarairways.com/adobe/assets/urn%3Aaaid%3Aaem%3A46c43466-defb-44be-92cc-15668586a966/original/as/Q60-Network-map-07APR26.pdf'),
 ('DOH','BOG CCS','https://www.qatarairways.com/press-releases/en-WW/265500-qatar-airways-set-to-operate-to-caracas-venezuela-and-bogota-colombia-from-july-2026/'),
]
TZ_URL='https://raw.githubusercontent.com/jpatokal/openflights/e539814f664cf31e662710555b27e9688610a911/data/airports.dat'
TZ_HASH='9387cdb38df5bd664da823f8ccb69fdd9b33a1888f5b7cca09c34a3cd9ff59f9'
NEW_ZONES={'COV':'Europe/Istanbul','KTI':'Asia/Phnom_Penh','SAI':'Asia/Phnom_Penh','NQZ':'Asia/Almaty',
 'RSI':'Asia/Riyadh','NUM':'Asia/Riyadh','HOF':'Asia/Riyadh','SPX':'Africa/Cairo','DBB':'Africa/Cairo','AQI':'Asia/Riyadh',
 'DOH':'Asia/Qatar','DXB':'Asia/Dubai','AUH':'Asia/Dubai','DSS':'Africa/Dakar','BER':'Europe/Berlin',
 'CNN':'Asia/Kolkata','GOX':'Asia/Kolkata','GSM':'Asia/Tehran','BSZ':'Asia/Bishkek',
 'KWI':'Asia/Kuwait','GOI':'Asia/Kolkata','VNS':'Asia/Kolkata','VTZ':'Asia/Kolkata',
 'NBJ':'Africa/Luanda','PKR':'Asia/Kathmandu'}


def pair_owner(a,b):
    return next((hub for hub in HUBS if hub in (a,b)),None)


def prepare():
    cache=ROOT/'.cache/gulf-flights-audit';cache.mkdir(parents=True,exist_ok=True)
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as f:airports=list(csv.DictReader(f))
    by_code={}
    for a in airports:
        if a['iata_code']:by_code.setdefault(a['iata_code'],[]).append(a)
    tzfile=pinned_download(TZ_URL,cache/'openflights-airports.dat',TZ_HASH)
    with tzfile.open() as f:tzrows=list(csv.reader(f))
    current_icao={a['iata_code']:a.get('icao_code') or a['ident'] for a in airports if a['iata_code'] and a['type']!='closed'}
    stable_ident={a['iata_code']:a['ident'] for a in airports if a['iata_code'] and a['type']!='closed'}
    zones={row[4]:row[11] for row in tzrows if len(row)>11 and row[4]!='\\N' and row[11]!='\\N' and row[5] in (current_icao.get(row[4]),stable_ident.get(row[4]))}
    # Reuse already resolved modern airports and their explicit local zones.
    for country in ['australia','indonesia','malaysia']:
        for scope in ['international','flights']:
            path=ROOT/f'data/sources/{country}_{scope}_routes.json'
            if path.exists():zones.update({a['code']:a['timezone'] for a in json.loads(path.read_text())['airports']})
    zones.update(NEW_ZONES)
    known={};pairs=set();evidence=[];excluded=[]
    def airport(code):
        if code in known:return known[code]
        candidates=[a for a in by_code.get(code,[]) if a['type']!='closed']
        if len(candidates)!=1:raise ValueError(f'Unresolved or closed airport: {code}')
        a=candidates[0];zone=zones.get(code)
        if not zone:raise ValueError(f'Unresolved airport timezone: {code}')
        ZoneInfo(zone)
        known[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=a['iso_country'],
            timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        return known[code]
    def add(hub,code,source,kind):
        source_code=code
        if code=='FRU':code='BSZ'  # Same UCFM airport; official change effective 9 August 2025.
        if hub==code:return
        if by_code.get(code) and all(a['type']=='closed' for a in by_code[code]):
            excluded.append(dict(hub=hub,airport=code,reason='Closed in pinned airport catalogue',source=source));return
        airport(hub);airport(code);pairs.update([(hub,code),(code,hub)])
        evidence.append(dict(origin=hub,destination=code,source_airport_code=source_code,source=source,kind=kind))
    for hub,targets in DESTINATIONS.items():
        for code in targets.split():add(hub,code,SOURCE_URLS[hub],'Published network/table candidate; not dated nonstop evidence')
    for hub,targets in PROBES.items():
        for code in targets.split():add(hub,code,SOURCE_URLS[hub],'Supplemental exact-airport probe; not proof of published/current service')
    for hub,targets,source in SUPPLEMENTS:
        for code in targets.split():add(hub,code,source,'Newer official network/table/announcement candidate; not dated nonstop evidence')
    for country in ['australia','indonesia','malaysia']:
        path=ROOT/f'data/sources/{country}_international_routes.json';m=json.loads(path.read_text())
        for a,b in m['routes']:
            if a in HUBS:add(a,b,m['route_source_url'],f'Reciprocal candidate from {path.name}')
    codes=sorted({c for p in pairs for c in p})
    result=dict(profile='gulf',scope='hubs',hubs=HUBS,start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Dubai',max_duration=86400,
        currency='USD',airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,timezone_source_url=TZ_URL,timezone_source_sha256=TZ_HASH,
        timezone_overrides=NEW_ZONES,
        route_source_url=SOURCE_URLS['AUH'],route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated, exact-airport resolutions of official table/map labels and explicit supplementary probes; not raw website bytes',
        source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
        airports=[known[c] for c in codes],routes=sorted(pairs),evidence=evidence,excluded_candidates=excluded,unresolved_airports=[],
        query_ownership='First endpoint in DXB, AUH, DOH order owns both directions; inter-hub routes searched once')
    result['code_resolutions']=[dict(source_code='FRU',code='BSZ',icao='UCFM',effective_date='2025-08-09',source='https://airport.kg/ru/news/15')]
    (ROOT/'data/sources/gulf_flights_routes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(codes),routes=len(pairs),owned_routes={h:sum(pair_owner(*p)==h for p in pairs) for h in HUBS},excluded=excluded)))

if __name__=='__main__':prepare()
