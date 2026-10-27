"""Pin explicit published airline pairs; never expand destination lists into all pairs."""
import concurrent.futures,csv,hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as E
from zoneinfo import ZoneInfo
import requests
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.europe_flights import OTHER_NETWORKS,EUROPE_COUNTRIES
from scripts.prepare_australian_flights import AIRPORT_HASH
from scripts.prepare_gulf_airports import TZ_HASH
CACHE=ROOT/'.cache/europe-networks-audit'

def fetch(code):
 url=f'https://www.gcpromap.com/assets/images/airlines/carriers/{code.lower()}-routes.svg';path=CACHE/f'{code.lower()}-routes.svg'
 if not path.exists():
  response=requests.get(url,timeout=40)
  if response.status_code in {403,429}:raise RuntimeError('Discovery access challenge; stop')
  if response.status_code!=200:return code,dict(url=url,error=f'HTTP {response.status_code}'),[]
  path.write_bytes(response.content)
 data=path.read_bytes();root=E.fromstring(data);pairs=set()
 for node in root.iter():
  match=re.fullmatch(r'([A-Z0-9]{3}) to ([A-Z0-9]{3})',node.text or '') if node.tag.endswith('title') else None
  if match:
   a,b=match.groups();pairs.update([(a,b),(b,a)])
 description=next((n.text for n in root.iter() if n.tag.endswith('desc')),None)
 if not pairs:raise ValueError(f'No explicit airport pairs for {code}')
 expected=re.search(r'(\d+) distinct airport pairs',description or '')
 if expected and len(pairs)!=int(expected[1])*2:raise ValueError(f'Route map pair count differs for {code}')
 return code,dict(url=url,sha256=hashlib.sha256(data).hexdigest(),description=description,kind='Secondary published nonstop route candidates; not dated flight evidence',carrier_code_source=f'https://www.iata.org/en/publications/directories/code-search/?airline.search={code}'),sorted(pairs)

def build():
 CACHE.mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(fetch,[c for _,codes,_ in OTHER_NETWORKS.values() for c in codes]))
 sources={c:s for c,s,_ in rows};bycode={c:p for c,_,p in rows}
 airport_path=ROOT/'.cache/australia-flights-audit/ourairports-airports.csv';tzpath=ROOT/'.cache/gulf-flights-audit/openflights-airports.dat'
 if hashlib.sha256(airport_path.read_bytes()).hexdigest()!=AIRPORT_HASH or hashlib.sha256(tzpath.read_bytes()).hexdigest()!=TZ_HASH:raise ValueError('Pinned airport catalogues changed')
 active={}
 for a in csv.DictReader(airport_path.open(encoding='utf-8-sig')):
  if a['iata_code'] and a['type']!='closed':active.setdefault(a['iata_code'],[]).append(a)
 zones={r[4]:r[11] for r in csv.reader(tzpath.open()) if len(r)>11 and r[11]!='\\N' and any(r[5] in (a.get('icao_code'),a['ident']) for a in active.get(r[4],[]))}
 for name in ['europe_flights_routes.json','europe_groups_routes.json']:
  for a in json.loads((ROOT/'data/sources'/name).read_text())['airports']:zones[a['code']]=a['timezone']
 zones.update(KVO='Europe/Belgrade',PKX='Asia/Shanghai',TFU='Asia/Shanghai',GZP='Europe/Istanbul',JJU='America/Nuuk',KUS='America/Nuuk')
 pairs={brand:sorted({tuple(p) for code in codes for p in bycode[code]}) for brand,(_,codes,_) in OTHER_NETWORKS.items()}
 codes=sorted({c for ps in pairs.values() for p in ps for c in p});unresolved=[]
 for c in codes:
  if len(active.get(c,[]))!=1 or not zones.get(c):unresolved.append(c)
  else:ZoneInfo(zones[c])
 pairs={brand:[p for p in ps if not set(p)&set(unresolved) and any(active[c][0]['iso_country'] in EUROPE_COUNTRIES for c in p)] for brand,ps in pairs.items()}
 used={c for ps in pairs.values() for p in ps for c in p}
 brand_sources={brand:dict(url=sources[codes[0]]['url'],documents=[sources[c] for c in codes],kind='Secondary published nonstop route candidates; not dated flight evidence') for brand,(_,codes,_) in OTHER_NETWORKS.items()}
 doc=dict(reviewed_at=datetime.now(timezone.utc).isoformat(),reviewed_date=datetime.now(timezone.utc).date().isoformat(),sources=brand_sources,carrier_sources=sources,routes_by_brand=pairs,airport_timezones={c:zones[c] for c in sorted(used)},unresolved_airports=unresolved,selection='Nine additional European networks; explicit published pairs touching Europe, one local date, no all-airport combinations',limitations='Both directions of explicit published pairs are candidates only. Seasonal routes do not prove service on 2 November. Source codes are not inferred operators or codeshares.')
 (ROOT/'data/sources/europe_networks_discovery.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(by_brand={b:len(ps) for b,ps in pairs.items()},unique_directions=len({p for ps in pairs.values() for p in ps}),gaps={c:s['error'] for c,s in sources.items() if s.get('error')})))
 return doc

if __name__=='__main__':build()
