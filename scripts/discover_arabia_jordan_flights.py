"""Pin published exact-airport Oman, Kuwait, Bahrain and Jordan route candidates, not dated flight evidence."""
import concurrent.futures,hashlib,html,json,re
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'.cache/arabia-jordan-flights-audit'
CACHE.mkdir(parents=True,exist_ok=True)
COUNTRIES={'oman':['MCT','SLL','KHS','DQM','OHS','MSH'],'kuwait':['KWI'],'bahrain':['BAH'],'jordan':['AMM','AQJ','ADJ']}
CODES=[code for codes in COUNTRIES.values() for code in codes]
def discover(code,cache=CACHE):
 entries=[];description=None;destinations=[]
 for kind,url in [('page',f'https://www.gcpromap.com/airports/{code.lower()}/'),('map',f'https://www.gcpromap.com/assets/images/airports/{code.lower()}-routes.svg')]:
  cache.mkdir(parents=True,exist_ok=True)
  path=cache/f'{code.lower()}-{"page.html" if kind=="page" else "routes.svg"}'
  if not path.exists():
   r=requests.get(url,timeout=35)
   if r.status_code in {403,429} or 'unusual traffic' in r.text.lower():raise RuntimeError('Discovery access limited; stop')
   if r.status_code!=200:return dict(airport=code,destinations=[],documents=entries,error=f'{url}: HTTP {r.status_code}')
   temp=path.with_suffix('.tmp');temp.write_bytes(r.content);temp.replace(path)
  data=path.read_bytes();entries.append(dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
  if kind=='page':
   match=re.search(r'Schedule period:.*?</p>',data.decode(),re.S)
   description=html.unescape(re.sub('<[^>]*>',' ',match[0])).strip() if match else None
  else:destinations=sorted(set(re.findall(r'\(([A-Z0-9]{3})\):',data.decode())))
 print(code,len(destinations),flush=True)
 return dict(airport=code,destinations=destinations,documents=entries,description=description,kind='Secondary published outbound nonstop airport map; seasonal candidates, not dated service evidence')
def main(countries=None,cache=CACHE):
 countries=countries or COUNTRIES
 codes=[code for values in countries.values() for code in values]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda code:discover(code,cache),codes))
 for slug,codes in countries.items():
  path=ROOT/f'data/sources/{slug}_flights_discovery.json'
  previous=json.loads(path.read_text()) if path.exists() else {}
  doc=dict(reviewed_at=datetime.now(timezone.utc).isoformat(),launch_airports=codes,worldwide_hubs=codes,airport_maps=[r for r in rows if r['airport'] in codes])
  doc.update({k:v for k,v in previous.items() if k.startswith('supplemental_')})
  path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
