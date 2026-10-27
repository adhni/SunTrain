"""Pin published Pacific airport routes, excluding Cartesian airport combinations."""
import csv,hashlib,json,sys
import requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.discover_arabia_jordan_flights import main
AIRPORTS='POM LAE HGU GKA RAB GUR MAS KVG WWK HIR MUA VLI SON TAH NOU GEA LIF ILP UVE MEE NAN SUV LBS TVU SVU KDV APW PPG TBU VAV HPA RAR AIT PPT BOB RFP HUH MOZ RGI NHV GMR IUE FUN INU TRW CXI MAJ KWA PNI TKK KSA YAP ROR GUM SPN ROP TIQ HNL OGG KOA LIH ITO MKK LNY HNM JHM NLK WLS FUT CHT IPC'.split()
ARCHIVE_URL='https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat'
ARCHIVE_HASH='bd373706238134f619c624c606dccc74c05c2582a977c489c81de501735f2390'

def supplement():
    """Pinned 2014 candidates only; Google captures establish dated service."""
    cache=ROOT/'.cache/pacific-flights-audit/openflights-routes.dat'
    if not cache.exists():
        response=requests.get(ARCHIVE_URL,timeout=45);response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest()!=ARCHIVE_HASH:raise ValueError('Historical route archive changed')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(response.content)
    raw=cache.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ARCHIVE_HASH:raise ValueError('Historical route archive changed')
    groups={}
    for row in csv.reader(raw.decode().splitlines()):
        if len(row)>7 and row[7]=='0' and (row[2] in AIRPORTS or row[4] in AIRPORTS):
            for origin,dest in [(row[2],row[4]),(row[4],row[2])]:
                if origin in AIRPORTS:groups.setdefault(origin,set()).add(dest)
    path=ROOT/'data/sources/pacific_flights_discovery.json';doc=json.loads(path.read_text())
    doc['supplemental_airport_maps']=[dict(airport=origin,destinations=sorted(destinations),
        documents=[dict(url=ARCHIVE_URL,sha256=ARCHIVE_HASH,bytes=len(raw))],
        description='2014-era OpenFlights zero-stop route candidates; NOT current service evidence or flight timings.',
        kind='Historical sourced search candidates only') for origin,destinations in sorted(groups.items())]
    # Primary-source route facts checked separately; no timings inferred.
    for origin,destinations,url,description in [
        ('NOU',['LIF','ILP','UVE','MEE'],'https://www.newcaledonia.travel/frequently-asked-questions/domestic-flights/','Official October 2026 tourism status confirms domestic network moved from GEA to NOU in March 2026; cancelled routes remain search candidates only.'),
        ('NAN',['FUN'],'https://parliament.gov.fj/wp-content/uploads/2026/03/11Fiji-Airways-Annual-Report-2024-2.pdf','Official Fiji Airways annual report records Nadi–Funafuti introduced January 2024; dated capture required.'),
        ('NAN',['SFO'],'https://www.flysfo.com/vi/node/14876','SFO airport publishes nonstop Nadi service; dated capture required.'),
        ('PPT',['SFO'],'https://www.airtahiti.com/en/coming-to-polynesia','Air Tahiti identifies San Francisco nonstop access; Paris itineraries stop in the US and are excluded.'),
        ('APW',['PPG'],'https://www.talofaairways.com/routes/','Talofa publishes Faleolo–Pago Pago service; route candidate only, not a dated schedule.'),
        ('CHT',['WLG','CHC'],'https://www.airchathams.co.nz/blog/upcoming-changes-to-chatham-islands-air-services','Air Chathams published October 2026 Wellington/Christchurch network; dated times must come from capture.')]:
        destinations=sorted(destinations)
        facts=json.dumps(dict(airport=origin,destinations=destinations),sort_keys=True,separators=(',',':')).encode()
        doc['supplemental_airport_maps'].append(dict(airport=origin,destinations=destinations,
            documents=[dict(url=url,facts_sha256=hashlib.sha256(facts).hexdigest(),facts_reviewed_at='2026-10-27')],description=description,kind='Primary published route facts, not flight timings'))
    doc['historical_route_source']=dict(url=ARCHIVE_URL,sha256=ARCHIVE_HASH,cache_path=str(cache.relative_to(ROOT)),age_warning='Historical 2014-era route archive; current service must be established only by dated captured flights')
    doc['supplemental_source_warning']='OpenFlights routes stopped updating June 2014. Historical candidates only; dated Google captures determine returned flights.'
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    if '--supplement-only' not in sys.argv:main({'pacific':AIRPORTS},ROOT/'.cache/pacific-flights-audit')
    supplement()
