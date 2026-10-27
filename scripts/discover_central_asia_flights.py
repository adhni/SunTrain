"""Pin sourced Central Asian airport directions, never all airport combinations."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.discover_arabia_jordan_flights import main
AIRPORTS='ALA NQZ CIT SCO GUW AKX URA KSN KGF KZO UKK PWQ PLX PPK KOV DMB DZN HSA TAS SKD BHK UGC NCU FEG NMA AZN TMJ NVI KSQ BSZ OSS IKU IKG DYU LBD TJU KQT ASB KRW TAZ CRZ MYP BKN KEA'.split()

# Only reviewed nonstop facts; connecting-destination sections are excluded.
# Top-20 lists are partial candidate discovery, never complete-airport claims.
FACTS=[
 ('BSZ','OSS SAW SVO TAS IST DME ALA KJA DXB LED OVB SHJ URC ESB NQZ SVX AYT GYD PKX XIY IKG ISB CXR',
  'https://www.flightconnections.com/flights-from-bishkek-bsz','Reviewed October 2026 nonstop top-20 list and explicit airport-code facts; not the complete airport network.'),
 ('DYU','ZIA DME LED TAS IST DXB SVX ALA VKO OVB KZN KUF URC LBD UFA GYD KJA XIY CEK JED BSZ DEL NQZ MUC',
  'https://www.flightconnections.com/flights-from-dushanbe-dyu','Reviewed October 2026 nonstop top-20 list and explicit airport-code facts; not the complete airport network.'),
 ('SKD','VKO IST DME TAS LED SVO ZIA SVX TLV XIY ADB KZN ALA GYD OVB UFA MRV NQZ SYX AER',
  'https://www.flightconnections.com/flights-from-samarkand-skd','Reviewed October 2026 nonstop top-20 list; future-only and connecting sections excluded.'),
 ('OSS','BSZ DME SVX LED KJA VKO IKT OVB ZIA SVO TAS SAW KHG IKG SGC URC TJM NJC',
  'https://www.flightconnections.com/flights-from-osh-oss','Reviewed October 2026 nonstop list; zero-flight KWI candidate omitted.'),
 ('LBD','ZIA OVB SVX LED DYU SGC DME KHG TJM KZN KJA UFA KUF MRV',
  'https://www.flightconnections.com/flights-from-khujand-lbd','Reviewed October 2026 nonstop list, not frequency-derived flight timings.'),
 ('UGC','TAS IST VKO LED DME ZIA BHK MCX KUF ALA',
  'https://www.flightconnections.com/flights-from-urgench-ugc','Reviewed October 2026 nonstop list; zero-flight CDG/FCO/MXP candidates omitted.'),
 ('FEG','TAS VKO DME ZIA LED OVB KZN IKT IST JED',
  'https://www.flightconnections.com/flights-from-fergana-feg','Reviewed October 2026 nonstop list, not frequency-derived flight timings.'),
 ('NMA','VKO TAS DME SVX KUF ZIA UFA JED NJC MCX AER IKT LED DEL PEE KJA OMS KZN',
  'https://www.flightconnections.com/flights-from-namangan-nma','Reviewed October 2026 nonstop list; zero-flight KWI candidate omitted.'),
 ('ASB','TAZ CRZ MYP BKN KRW KEA',
  'https://turkmenistanairlines.tm/en/services/show/napravlenie-i-raspisanie-reysov','Published official domestic routes only; weekly timings are not imported.'),
 ('TAZ','BKN CRZ MYP',
  'https://turkmenistanairlines.tm/en/services/show/napravlenie-i-raspisanie-reysov','Published official cross-regional domestic route candidates.'),
 ('BKN','KEA MYP CRZ',
  'https://turkmenistanairlines.tm/en/services/show/napravlenie-i-raspisanie-reysov','Published official cross-regional domestic route candidates.'),
 ('ASB','FRA LGW MXP AUH IST JED BKK PEK SGN KUL DEL ICN',
  'https://turkmenistanairlines.com/flight-map','Published international exact-IATA route map; dated service and fares require Google capture.')]

def supplement():
    from scripts.discover_pacific_flights import ARCHIVE_HASH,ARCHIVE_URL
    path=ROOT/'data/sources/central_asia_flights_discovery.json';doc=json.loads(path.read_text());rows=[]
    for origin,codes,url,description in FACTS:
        destinations=sorted(codes.split());facts=json.dumps(dict(airport=origin,destinations=destinations),sort_keys=True,separators=(',',':')).encode()
        rows.append(dict(airport=origin,destinations=destinations,description=description,
            kind='Reviewed published nonstop route facts, not dated service',
            documents=[dict(url=url,facts_sha256=hashlib.sha256(facts).hexdigest(),facts_reviewed_at='2026-10-27')]))
    # Domestic-only historical candidates fill regional source-map gaps without
    # expanding stale international networks. Current IATA queries stay exact.
    archive=ROOT/'.cache/pacific-flights-audit/openflights-routes.dat'
    if not archive.exists():
        import requests
        response=requests.get(ARCHIVE_URL,timeout=45);response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest()!=ARCHIVE_HASH:raise ValueError('Historical routes changed')
        archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes(response.content)
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ARCHIVE_HASH:raise ValueError('Historical routes changed')
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        countries={a['iata_code']:a['iso_country'] for a in csv.DictReader(stream) if a['iata_code'] and a['type']!='closed'}
    groups={};aliases={'FRU':'BSZ','TSE':'NQZ'}
    for row in csv.reader(raw.decode().splitlines()):
        if len(row)<=7 or row[7]!='0':continue
        a,b=(aliases.get(row[i],row[i]) for i in (2,4))
        if a in AIRPORTS and b in AIRPORTS and countries.get(a)==countries.get(b) and countries.get(a) in {'KZ','UZ','KG','TJ','TM'}:
            groups.setdefault(a,set()).add(b)
    for origin,destinations in sorted(groups.items()):
        rows.append(dict(airport=origin,destinations=sorted(destinations),kind='Historical domestic candidates only',
            description='2014-era domestic-only OpenFlights routes; FRU/TSE normalized for candidate queries only, never flight-record identities. NOT current service or dated timings.',
            documents=[dict(url=ARCHIVE_URL,sha256=ARCHIVE_HASH,bytes=len(raw))]))
    doc['supplemental_airport_maps']=rows
    doc['supplemental_airport_code_changes']=[dict(old='FRU',current='BSZ',icao='UCFM',source='https://www.trinityairways.com/app/customerCenter/notice/retrieve/12418'),dict(old='TSE',current='NQZ',icao='UACC',source='https://www.gov.kz/uploads/2022/2/14/f4bd7a89429f465aae98022132afc98f_original.3460307.pdf')]
    doc['supplemental_source_warning']='Historical archive stopped updating June 2014; domestic candidates only. Reviewed current lists are partial. No frequencies or connecting itineraries become flights.'
    doc['supplemental_discovery_gaps']=['Public FlightConnections raw download returned HTTP 403; no further raw downloads attempted. Only reviewed public indexed nonstop route facts are pinned, without a fabricated raw-page checksum.']
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    if '--supplement-only' not in sys.argv:main({'central_asia':AIRPORTS},ROOT/'.cache/central-asia-flights-audit')
    supplement()
