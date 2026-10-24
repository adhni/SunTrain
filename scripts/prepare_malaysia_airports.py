"""Exact-airport Malaysian domestic search candidates; no inferred schedules."""
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

RAS_URL='https://www.caam.gov.my/industry/public-service-obligations/current-ras-programme/'
MH_URL='https://www.malaysiaairlines.com/hq/en/plan-trip/destinations/flights-to-malaysia.html'
# Transcribed published RAS candidates; two expressly suspended Kudat pairs omitted.
RAS='MYY-MZV MYY-LMN MYY-BTU MYY-SBW BTU-SBW KCH-MZV KCH-LMN MYY-LWY LMN-LWY MYY-BKM LWY-BKM MYY-BBN MUR-BBN MYY-MUR MYY-LGL MUR-LGL MYY-LKH MUR-LKH BBN-BKM SBW-MKM MKM-MYY MKM-BTU MKM-KCH MYY-ODN MUR-ODN MYY-LBP MUR-LBP KCH-TGC BBN-ODN BBN-LGL BKI-LDU SDK-TWU BKI-LBU LDU-SDK MYY-LBU BKI-MZV BKI-LMN BKI-LWY'.split()
HUB_CANDIDATES={
 'KUL':'AOR LGK PEN KBR TGG KUA JHB BKI SDK TWU LBU KCH MYY SBW BTU',
 'SZB':'AOR LGK PEN KBR TGG JHB BKI KCH MYY SBW BTU TWU',
 'PEN':'LGK JHB KBR TGG KUA BKI KCH MYY IPH',
 'JHB':'LGK IPH BKI KCH MYY SBW TWU',
 'BKI':'KCH MYY SBW BTU SDK TWU',
 'KCH':'MYY SBW BTU LGK',
}


def prepare():
 (ROOT/'.cache/australia-flights-audit').mkdir(parents=True,exist_ok=True)
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 pairs=set();evidence=[]
 for pair in RAS:
  a,b=pair.split('-');pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=RAS_URL,kind='Historical published RAS candidate; verify dated results'))
 for a,targets in HUB_CANDIDATES.items():
  for b in targets.split():
   pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=MH_URL,kind='Targeted hub/airport probe; not evidence of current service'))
 airports=[]
 for code in sorted({c for pair in pairs for c in pair}):
  matches=[a for a in rows if a['iso_country']=='MY' and a['iata_code']==code and a['type']!='closed']
  if len(matches)!=1:raise ValueError(f'Unresolved Malaysian airport {code}')
  a=matches[0];east=a['iso_region'] in {'MY-12','MY-13','MY-15'}
  group='Sabah & Labuan' if a['iso_region'] in {'MY-12','MY-15'} else 'Sarawak' if a['iso_region']=='MY-13' else 'Peninsular Malaysia'
  airports.append(dict(code=code,icao=a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country='MY',
   timezone='Asia/Kuching' if east else 'Asia/Kuala_Lumpur',island_group=group,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg'])))
 result=dict(country='MY',scope='domestic',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Kuala_Lumpur',max_duration=28800,
  airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=RAS_URL,
  route_source_sha256=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest(),route_hash_basis='Curated candidate evidence, not raw website bytes',
  source_reviewed_date='2026-10-25',source_reviewed_timezone='Australia/Melbourne',
  airports=airports,routes=sorted(pairs),evidence=evidence,unresolved_airports=[],
  excluded_candidates=[dict(origin='BKI',destination='KUD',reason='Explicitly suspended in CAAM table'),dict(origin='KUD',destination='SDK',reason='Explicitly suspended in CAAM table')])
 path=ROOT/'data/sources/malaysia_flights_routes.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Airports',len(airports),'directional pairs',len(pairs))
if __name__=='__main__':prepare()
