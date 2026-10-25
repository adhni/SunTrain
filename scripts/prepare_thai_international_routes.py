"""Thailand candidates within existing SunTrain flight countries; not service proof."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COUNTRIES={'AU','ID','MY','SG','IN','CN','JP','KR','AE','QA','TH'}
HUBS={'DXB','AUH','DOH'}
SOURCES={
 'thai_china':'https://www.thaiairways.com/flights/en/flights-from-bangkok-to-china',
 'airasia_china':'https://newsroom.airasia.com/news/nihao-china-airasia-welcomes-the-new-year-with-special-fares',
 'airasia_winter':'https://newsroom.airasia.com/news/airasia-gears-up-for-high-season-with-major-international-expansion',
 'NRT':'https://www.narita-airport.jp/en/discover/citylist/',
 'HND':'https://tokyo-haneda.com/en/flight/city_list.html?tab=intFlight',
 'KIX':'https://assets.kansai-airports.co.jp/551f6859-e_20260324_pressrelease_s26.pdf',
 'NGO':'https://www.centrair.jp/en/',
 'ICN':'https://m.flyasiana.com/C/KR/KO/booking/route',
 'PUS':'https://en.airbusan.com/content/individual/booking/route',
 'probe':'https://www.airportthai.co.th/en/homeen/',
}

def prepare():
 airports={};pairs=set();evidence=[];inputs=[]
 for name in ['china','japan','south_korea','thailand']:
  path=ROOT/f'data/sources/{name}_flights_routes.json'
  d=json.loads(path.read_text());airports.update({a['code']:a for a in d['airports']})
  inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 paths=sorted(p for p in ROOT.glob('data/sources/*_international_routes.json') if p.name!='thailand_international_routes.json')+[ROOT/'data/sources/gulf_flights_routes.json']
 for path in paths:
  d=json.loads(path.read_text());airports.update({a['code']:a for a in d['airports']})
  inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  for a,b in d['routes']:
   aa,bb=airports[a],airports[b]
   if 'TH' not in {aa['country'],bb['country']} or aa['country']==bb['country']:continue
   if any(x['country'] not in COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in HUBS) for x in (aa,bb)):continue
   pairs.add((a,b));evidence.append(dict(origin=a,destination=b,source=str(path.relative_to(ROOT)),kind='Existing published/probe candidate; not dated service evidence'))
 base=len(pairs)
 def add(a,targets,source,kind):
  for b in targets.split():
   if airports[a]['country']==airports[b]['country'] or 'TH' not in {airports[a]['country'],airports[b]['country']}:raise ValueError((a,b))
   pairs.update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,source=SOURCES[source],kind=kind))
 add('BKK','PVG PEK CAN TFU KMG XMN SZX CKG','thai_china','Airline exact-airport offer candidates; not dated nonstop evidence')
 add('DMK','CAN SZX TFU XIY KMG HGH WUH CSX PVG CKG','airasia_china','Historical December 2025 city routes, Chengdu/Shanghai resolved to TFU/PVG probes; promotion ended before replay')
 add('DMK','NRT KIX CTS NGO DEL','airasia_winter','Winter 2026 city candidates resolved to exact airports; dated nonstop captures required')
 for a,targets in {'NRT':'BKK DMK','HND':'BKK','KIX':'BKK DMK CNX','NGO':'BKK DMK','ICN':'BKK','PUS':'BKK'}.items():
  add(a,targets,a,'Official airport/airline candidate; Bangkok city labels at HND/PUS resolved to BKK; not dated service evidence')
 for a,targets in {'HKT':'PVG CAN PEK KMG SZX TFU ICN PUS','CNX':'PEK PVG CAN KMG ICN','DMK':'ICN PUS'}.items():
  add(a,targets,'probe','Supplemental exact-airport gateway probe; airport directory is identity context, not route evidence')
 codes={c for p in pairs for c in p};catalogue=[]
 for code in sorted(codes):
  a=dict(airports[code]);a.pop('island_group',None)
  if a['country']=='CN':a['timezone']='Asia/Shanghai'
  if a['country']=='IN':a['timezone']='Asia/Kolkata'
  catalogue.append(a)
 doc=dict(country='TH',scope='international',start_date='2026-11-02',end_date='2026-11-02',timezone='Asia/Bangkok',currency='USD',max_duration=86400,
  airports=catalogue,routes=[list(p) for p in sorted(pairs)],base_directional_routes=base,evidence=evidence,input_manifests=inputs,source_urls=SOURCES,
  source_reviewed_date='2026-10-25',unresolved_airports=[],coverage_scope='Selected existing SunTrain countries and Gulf hubs; not worldwide or exhaustive')
 doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=evidence,inputs=inputs),sort_keys=True).encode()).hexdigest()
 (ROOT/'data/sources/thailand_international_routes.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(dict(airports=len(catalogue),base_routes=base,routes=len(pairs))))

if __name__=='__main__':prepare()
