"""Build exact-airport main-flag-carrier candidates from pinned public route maps."""
import csv,hashlib,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from dashboard.europe_flights import DAY,EUROPE_COUNTRIES,FLAG_CARRIERS


def build(discovery_path=None,output_path=None,carriers=None,profile='europe_groups'):
 path=discovery_path or ROOT/'data/sources/europe_groups_discovery.json';seed=json.loads(path.read_text());carriers=FLAG_CARRIERS if carriers is None else carriers
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 catalogue={};excluded=[];by_brand={}
 for brand in carriers:
  pairs=set()
  for a,b in seed['routes_by_brand'][brand]:
   for c in (a,b):
    if c in catalogue:continue
    matches=[r for r in rows if r['iata_code']==c and r['type']!='closed']
    if len(matches)!=1:raise ValueError(f'Unresolved exact airport {c}')
    row=matches[0];zone=seed['airport_timezones'][c];ZoneInfo(zone)
    catalogue[c]=dict(code=c,icao=row.get('icao_code') or row['ident'],name=f"{row['name']} ({c})",municipality=row['municipality'],country=row['iso_country'],timezone=zone,europe=row['iso_country'] in EUROPE_COUNTRIES,mode='flight',lat=float(row['latitude_deg']),lon=float(row['longitude_deg']))
   if a==b:raise ValueError('Self route')
   if not(catalogue[a]['europe'] or catalogue[b]['europe']):
    excluded.append(dict(brand=brand,origin=a,destination=b,reason='Neither airport is in Europe'));continue
   pairs.add((a,b))
  by_brand[brand]=sorted(pairs)
 routes=sorted({p for ps in by_brand.values() for p in ps});used={c for p in routes for c in p}
 doc=dict(profile=profile,start_date=DAY,end_date=DAY,timezone='UTC',currency='EUR',max_duration=86400,query_date_policy='local_departure_day_only',airports=[catalogue[c] for c in sorted(used)],routes=routes,routes_by_brand=by_brand,source_urls={brand:seed['sources'][brand]['url'] for brand in by_brand},source_documents=seed['sources'],route_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_reviewed_date=seed['reviewed_date'],airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,excluded_routes=excluded,unresolved_airports=[],selection=seed.get('selection','Nine main flag carriers; published nonstop airport-pair candidates touching Europe; dated results determine returned service'))
 if 'carrier_sources' in seed:
  doc['source_gaps']=[dict(carrier=code,**source) for code,source in seed['carrier_sources'].items() if source.get('error')]
  doc['excluded_airports']=seed['unresolved_airports']
 out=output_path or ROOT/'data/sources/europe_groups_routes.json';out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(directions=len(routes),airports=len(used),routes_by_brand={k:len(v) for k,v in by_brand.items()},excluded=len(excluded))))
 return doc


if __name__=='__main__':build()
