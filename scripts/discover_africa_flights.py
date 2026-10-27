"""Pin public airport-map candidate facts for Africa; not dated flight evidence."""
import concurrent.futures,hashlib,html,json,re
from datetime import datetime,timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'.cache/africa-flights-audit'
CACHE.mkdir(parents=True,exist_ok=True)
CODES='CAI HRG SSH CMN RAK AGA ALG TUN LOS ABV ACC DSS ABJ FIH DLA ADD BJR NBO MBA DAR ZNZ EBB KGL JNB CPT DUR GRJ WDH MRU SEZ'.split()

def discover(code):
    entries=[];body=None
    for kind,url in [('page',f'https://www.gcpromap.com/airports/{code.lower()}/'),('map',f'https://www.gcpromap.com/assets/images/airports/{code.lower()}-routes.svg')]:
        path=CACHE/f'{code.lower()}-{"page.html" if kind=="page" else "routes.svg"}'
        if not path.exists():
            r=requests.get(url,timeout=35)
            if r.status_code in {403,429} or any(t in r.text.lower() for t in ['verify you are human','unusual traffic']):
                raise RuntimeError('Discovery access limited; stop without retry')
            if r.status_code!=200:
                print(code,kind,r.status_code,flush=True)
                return dict(airport=code,destinations=[],documents=entries,error=f'{url}: HTTP {r.status_code}')
            temporary=path.with_suffix('.tmp');temporary.write_bytes(r.content);temporary.replace(path)
        data=path.read_bytes();entries.append(dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
        if kind=='page':
            body=data.decode();match=re.search(r'Schedule period:.*?</p>',body,re.S)
            description=html.unescape(re.sub('<[^>]*>',' ',match[0])).strip() if match else None
        else:
            titles=re.findall(r'<title[^>]*>(.*?)</title>',data.decode(),re.S)
            destinations=sorted({m.group(1) for text in titles if (m:=re.search(r'\(([A-Z0-9]{3})\):',text))})
    if not destinations:raise ValueError(f'No exact destination labels: {code}')
    print(code,len(destinations),flush=True)
    return dict(airport=code,destinations=destinations,documents=entries,description=description,
        kind='Secondary published outbound nonstop airport map; seasonal candidates, not dated service evidence',
        reverse_policy='Reciprocal searches are candidates only; no return-day flight inferred')

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(discover,CODES))
    doc=dict(reviewed_at=datetime.now(timezone.utc).isoformat(),launch_airports=CODES,airport_maps=rows,
        source_scope='30 geographically balanced African starter airports; no Cartesian airport expansion')
    (ROOT/'data/sources/africa_flights_discovery.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
    print('DONE',sum(len(r['destinations']) for r in rows),flush=True)

if __name__=='__main__':main()
