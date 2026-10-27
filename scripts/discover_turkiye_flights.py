"""Pin published exact-airport Türkiye route candidates, not dated flight evidence."""
import concurrent.futures,hashlib,html,json,re
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'.cache/turkiye-flights-audit'
CACHE.mkdir(parents=True,exist_ok=True)
CODES=['IST','SAW','ESB','ADB','AYT']
def discover(code):
 entries=[];description=None;destinations=[]
 for kind,url in [('page',f'https://www.gcpromap.com/airports/{code.lower()}/'),('map',f'https://www.gcpromap.com/assets/images/airports/{code.lower()}-routes.svg')]:
  path=CACHE/f'{code.lower()}-{"page.html" if kind=="page" else "routes.svg"}'
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
 return dict(airport=code,destinations=destinations,documents=entries,description=description,kind='Published outbound nonstop airport map; seasonal candidates, not dated service evidence')
def main():
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(discover,CODES))
 (ROOT/'data/sources/turkiye_flights_discovery.json').write_text(json.dumps(dict(reviewed_at=datetime.now(timezone.utc).isoformat(),launch_airports=CODES,worldwide_hubs=['IST','SAW'],airport_maps=rows),ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
