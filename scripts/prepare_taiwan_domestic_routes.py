"""Taiwan domestic airport candidates from official tourism/airport route lists."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
SOURCE='https://eng.taiwan.net.tw/m1.aspx?sno=0024034'
GROUPS={'Main island':'TSA RMQ KHH CYI TNN HUN TTT','Penghu':'MZG','Kinmen':'KNH','Matsu':'LZN MFK','Eastern islands':'GNI KYD'}
PAIRS={'TSA':'HUN TTT MZG KNH LZN MFK','RMQ':'HUN MZG KNH LZN','KHH':'HUN MZG KNH','CYI':'MZG KNH','TNN':'MZG KNH','TTT':'GNI KYD','MZG':'KNH'}


def prepare():
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 groups={c:g for g,cs in GROUPS.items() for c in cs.split()};air=[];pairs=set();evidence=[]
 for c,g in sorted(groups.items()):
  matches=[a for a in rows if a['iata_code']==c and a['iso_country']=='TW' and a['type']!='closed']
  if len(matches)!=1:raise ValueError(f'Unresolved exact Taiwanese airport {c}')
  a=matches[0];air.append(dict(code=c,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({c})",municipality=a['municipality'],country='TW',timezone='Asia/Taipei',island_group=g,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg'])))
 for a,targets in PAIRS.items():
  for b in targets.split():
   pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=SOURCE,kind='Official airport/tourism route candidate; may be historical or frequency-only, dated capture required'))
 d=dict(country='TW',scope='domestic',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Taipei',currency='USD',max_duration=28800,airports=air,routes=sorted(pairs),evidence=evidence,airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SOURCE,route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),unresolved_airports=[],source_reviewed_date='2026-10-26',coverage_scope='Selected main-island and offshore domestic airports; schedules and prices remain partial',deferred_airports=['HCN and small Penghu commuter/island services'],airport_notes=['TPE and TSA remain separate; no TPE domestic trunk service is inferred.','LZN Nangan and MFK Beigan remain separate.'])
 (ROOT/'data/sources/taiwan_flights_routes.json').write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');print(dict(airports=len(air),routes=len(pairs)))
if __name__=='__main__':prepare()
