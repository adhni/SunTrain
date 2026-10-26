"""Nepal exact-airport domestic and existing-location international candidates."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from dashboard.international_network import CORE_COUNTRIES,HUBS
DAY='2026-11-02'
SOURCES={
 'buddha':'https://www.buddhaair.com/detail/flight-information',
 'yeti':'https://yetiairlines.com/',
 'tara':'https://www.taraair.com/destination.jsp',
 'sita':'https://www.sitaair.com.np/destination.jsp',
 'winter':'https://www.caanepal.gov.np/storage/app/uploads/public/6ad/204/625/6ad20462584b8147669061.pdf',
 'pokhara':'https://www.caanepal.gov.np/storage/app/uploads/public/6ad/202/46c/6ad20246c8fd7187955340.pdf',
}
GROUPS={'Central and eastern trunk':'KTM BDP BHR BIR JKR RJB SIF TMI','Pokhara':'PHH PKR','Western trunk':'BWA DHI KEP SKH','Mountain and remote':'LUA RHP JMO PPL IMK DOP JUM'}


def prepare():
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 groups={c:g for g,cs in GROUPS.items() for c in cs.split()}
 catalogue={};inputs=[];pairs={'domestic':set(),'international':set()};evidence=[]
 def airport(code):
  if code in catalogue:return catalogue[code]
  matches=[a for a in rows if a['iata_code']==code and a['type']!='closed']
  if len(matches)!=1:raise ValueError(f'Unresolved exact airport: {code}')
  a=matches[0];country=a['iso_country'];zone={'NP':'Asia/Kathmandu','CN':'Asia/Shanghai','IN':'Asia/Kolkata'}.get(country) or known[code]['timezone']
  catalogue[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
  if country=='NP':catalogue[code]['island_group']=groups.get(code,'International gateways')
  return catalogue[code]
 def add(scope,a,targets,source,kind):
  for b in targets.split():
   aa,bb=airport(a),airport(b)
   if scope=='international' and (aa['country']==bb['country'] or any(x['country'] not in CORE_COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in HUBS) for x in (aa,bb))):raise ValueError('Outside existing flight locations')
   pairs[scope].update([(a,b),(b,a)]);evidence.append(dict(origin=a,destination=b,scope=scope,source=source,kind=kind))
 known={}
 paths=sorted(ROOT.glob('data/sources/*_international_routes.json'))+[ROOT/'data/sources/gulf_flights_routes.json']
 for path in paths:
  if path.name=='nepal_international_routes.json':continue
  d=json.loads(path.read_text());known.update({a['code']:a for a in d['airports']})
 for code in groups:airport(code)
 add('domestic','KTM','BDP BWA BHR BIR DHI JKR KEP PHH PKR SIF SKH RJB TMI',SOURCES['buddha'],'Official trunk route; generic Pokhara label explicitly probed at PHH and PKR without remapping captured identities')
 for hub in ['PHH','PKR']:add('domestic',hub,'BWA BHR KEP',SOURCES['buddha'],'Published Pokhara cross-country route; exact-airport probes at the two separate airports')
 add('domestic','KTM','LUA PPL',SOURCES['tara'],'Published remote destination candidate; dated capture required')
 add('domestic','RHP','LUA',SOURCES['tara'],'Explicit Ramechhap–Lukla route, not Kathmandu substitution')
 add('domestic','PKR','JMO',SOURCES['tara'],'Pokhara domestic STOL candidate; no international airport substitution')
 add('domestic','KEP','DOP',SOURCES['sita'],'Published Nepalgunj–Dolpa candidate; dated capture required')
 add('domestic','KEP','IMK JUM',SOURCES['tara'],'Remote destination/hub probes; scheduled/charter/frequency descriptions do not create dated records')
 # Winter ICAO sectors explicitly resolve to these exact IATA airports.
 add('international','KTM','AUH DEL TFU BLR KUL VNS CCU HKG CAN KMG DXB DOH LXA SZX HGH PVG BKK BOM ICN NRT SIN DMK',SOURCES['winter'],'CAAN winter 2026/27 sector candidate; both directions searched, dated nonstop capture required')
 add('international','BWA','KUL',SOURCES['winter'],'Published WMKK–VNBW sector, reverse is a search candidate only')
 add('international','PHH','DXB',SOURCES['pokhara'],'Official OMDB–VNPR winter sector; PKR/VNPK is a different airport')
 for path in paths:
  if path.name=='nepal_international_routes.json':continue
  d=json.loads(path.read_text());air={a['code']:a for a in d['airports']};used=False
  for a,b in d['routes']:
   ends=[air[a],air[b]]
   if not any(x['country']=='NP' for x in ends) or any(x['country'] not in CORE_COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in HUBS) for x in ends) or 'PKR' in (a,b):continue
   add('international',a,b,str(path.relative_to(ROOT)),'Existing exact-airport candidate; cached identities never remapped');used=True
  if used:inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 pins=json.loads((ROOT/'data/sources/nepal_flights_source_pins.json').read_text())
 for scope,ps in pairs.items():
  codes={c for pair in ps for c in pair};ev=[e for e in evidence if e['scope']==scope]
  d=dict(country='NP',scope=scope,start_date=DAY,end_date=DAY,timezone='Asia/Kathmandu',currency='USD',max_duration=(8 if scope=='domestic' else 24)*3600,airports=[catalogue[c] for c in sorted(codes)],routes=[list(p) for p in sorted(ps)],evidence=ev,input_manifests=inputs if scope=='international' else [],airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=SOURCES['buddha' if scope=='domestic' else 'winter'],source_urls=SOURCES,source_documents=pins,source_reviewed_date='2026-10-26',unresolved_airports=[],deferred_airports=['Rara/Talcha has no unique active IATA in the pinned catalogue; no invented code','Other small commuter/charter/scenic services'],coverage_scope='Selected trunk and remote domestic routes; international limited to existing SunTrain flight locations')
  d['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=ev,inputs=d['input_manifests'],pins=pins),sort_keys=True).encode()).hexdigest()
  name='flights' if scope=='domestic' else 'international';(ROOT/f'data/sources/nepal_{name}_routes.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(scope,len(ps),'directions',len(codes),'airports')


if __name__=='__main__':prepare()
