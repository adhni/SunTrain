"""Worldwide passenger route discovery for Taiwan and Hong Kong, with exact airports."""
import csv,hashlib,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard.flight_profiles import PROFILES
from dashboard.asean_flights import RETIRED_AIRPORTS
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from scripts.prepare_indonesia_international import COUNTRY_ZONES
DAY='2026-11-02'
COUNTRY_EXTRA={'BD':'Asia/Dhaka','NP':'Asia/Kathmandu','MM':'Asia/Yangon','LA':'Asia/Vientiane','MV':'Indian/Maldives','MN':'Asia/Ulaanbaatar','KZ':'Asia/Almaty','RU':'Europe/Moscow','ET':'Africa/Addis_Ababa','ZA':'Africa/Johannesburg','FJ':'Pacific/Fiji','PW':'Pacific/Palau','GU':'Pacific/Guam','MP':'Pacific/Saipan','FI':'Europe/Helsinki','BE':'Europe/Brussels','ES':'Europe/Madrid','IT':'Europe/Rome','CH':'Europe/Zurich','AT':'Europe/Vienna','CZ':'Europe/Prague','IL':'Asia/Jerusalem'}
AIRPORT_EXTRA={'SEA':'America/Los_Angeles','LAX':'America/Los_Angeles','SFO':'America/Los_Angeles','ONT':'America/Los_Angeles','PHX':'America/Phoenix','DFW':'America/Chicago','ORD':'America/Chicago','IAH':'America/Chicago','JFK':'America/New_York','BOS':'America/New_York','IAD':'America/New_York','HNL':'Pacific/Honolulu','YVR':'America/Vancouver','YYZ':'America/Toronto','DPS':'Asia/Makassar','CGK':'Asia/Jakarta','SUB':'Asia/Jakarta','UPG':'Asia/Makassar','MDC':'Asia/Makassar','BKI':'Asia/Kuching','KCH':'Asia/Kuching','TWU':'Asia/Kuching','MYY':'Asia/Kuching','SBW':'Asia/Kuching'}


def prepare():
 seed_path=ROOT/'data/sources/taiwan_hong_kong_route_seed.json';seed=json.loads(seed_path.read_text());evidence=[];pairs=set();known={};inputs=[dict(path=str(seed_path.relative_to(ROOT)),sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest())]
 for path in sorted(ROOT.glob('data/sources/*_routes.json')):
  if path.name in {'taiwan_international_routes.json','hong_kong_international_routes.json','taiwan_hong_kong_worldwide_routes.json','international_network_routes.json'}:continue
  d=json.loads(path.read_text());air={a['code']:a for a in d.get('airports',[]) if a.get('country') and a.get('timezone')};known.update(air)
  if not path.name.endswith('_international_routes.json') and path.name!='gulf_flights_routes.json':continue
  used=False
  for a,b in d.get('routes',[]):
   if a not in air or b not in air or not ({air[a]['country'],air[b]['country']}&{'TW','HK'}) or air[a]['country']==air[b]['country']:continue
   a,b=RETIRED_AIRPORTS.get(a,a),RETIRED_AIRPORTS.get(b,b);pairs.add((a,b));evidence.append(dict(origin=a,destination=b,source=str(path.relative_to(ROOT)),kind='Existing exact-airport candidate; cached flight identities never remapped'));used=True
  if used:inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 catalogue={}
 def airport(code):
  if code in catalogue:return catalogue[code]
  matches=[a for a in rows if a['iata_code']==code and a['type']!='closed']
  if len(matches)!=1:raise ValueError(f'Unresolved exact airport {code}')
  a=matches[0];country=a['iso_country'];old=known.get(code,{})
  if old.get('country',country)!=country:raise ValueError(f'Conflicting airport country {code}')
  zone=AIRPORT_EXTRA.get(code) or (PROFILES.get(country) or {}).get('zone') or old.get('timezone') or (COUNTRY_ZONES|COUNTRY_EXTRA).get(country)
  if country=='CN':zone='Asia/Shanghai'
  if country=='IN':zone='Asia/Kolkata'
  if not zone:raise ValueError(f'Missing explicit IANA zone {code}/{country}')
  ZoneInfo(zone)
  catalogue[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
  return catalogue[code]
 for r in seed['candidates']:
  a,b=r['origin'],r['destination'];aa,bb=airport(a),airport(b)
  if aa['country']==bb['country']:continue
  if not {aa['country'],bb['country']}&{'TW','HK'}:raise ValueError('World route must touch TW/HK')
  pairs.update([(a,b),(b,a)]);evidence.append(r)
 for code in {c for pair in pairs for c in pair}:airport(code)
 def doc(ps,ev,country=None):
  codes={c for pair in ps for c in pair}
  return dict(profile='taiwan_hong_kong_worldwide',country=country,scope='international',start_date=DAY,end_date=DAY,timezone=PROFILES[country]['zone'] if country else 'UTC',currency='mixed',max_duration=86400,
   airports=[catalogue[c] for c in sorted(codes)],routes=[list(p) for p in sorted(ps)],evidence=ev,input_manifests=inputs,source_documents=seed['sources'],airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,route_source_url=seed['sources']['caa_2026_08' if country=='TW' else 'hkg_2026']['url'],route_source_sha256=hashlib.sha256(json.dumps(dict(evidence=ev,inputs=inputs),sort_keys=True).encode()).hexdigest(),source_reviewed_date='2026-10-26',unresolved_airports=[],countries={catalogue[c]['country']:catalogue[c]['country'] for c in sorted(codes)},coverage_scope='Worldwide published passenger destination candidates; not restricted to existing SunTrain countries; dated captures and prices remain partial')
 for country in ['TW','HK']:
  ps={p for p in pairs if country in {catalogue[c]['country'] for c in p}};ev=[e for e in evidence if (e['origin'],e['destination']) in ps or (e['destination'],e['origin']) in ps];slug=PROFILES[country]['slug']
  (ROOT/f'data/sources/{slug}_international_routes.json').write_text(json.dumps(doc(ps,ev,country),ensure_ascii=False,indent=2)+'\n');print(country,len(ps),'directions',len({c for p in ps for c in p}),'airports')
 (ROOT/'data/sources/taiwan_hong_kong_worldwide_routes.json').write_text(json.dumps(doc(pairs,evidence),ensure_ascii=False,indent=2)+'\n');print('World union',len(pairs),'directions')


if __name__=='__main__':prepare()
