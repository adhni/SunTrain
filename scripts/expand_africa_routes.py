"""Bound Africa's next release to the frozen starter's deferred pairs and cached positives."""
import csv,gzip,hashlib,json,re
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.prepare_africa_routes import ROOT,AFRICAN,DAY,CACHE,AIRPORT_HASH,TZ_HASH
STARTER=ROOT/'data/sources/africa_flights_starter_routes.json.gz'
STARTER_HASH='2eff9a592c1bef2d854fd738be9b39041c995546f00c7b2295e3130bf92f984b'

def build():
 from scripts.prepare_africa_flights import validate_query
 if hashlib.sha256(STARTER.read_bytes()).hexdigest()!=STARTER_HASH:raise ValueError('Frozen Africa starter manifest changed')
 base=json.loads(gzip.decompress(STARTER.read_bytes()));air={a['code']:a for a in base['airports']}
 raw=ROOT/'.cache/australia-flights-audit/ourairports-airports.csv';tz=ROOT/'.cache/gulf-flights-audit/openflights-airports.dat'
 if hashlib.sha256(raw.read_bytes()).hexdigest()!=AIRPORT_HASH or hashlib.sha256(tz.read_bytes()).hexdigest()!=TZ_HASH:raise ValueError('Pinned airport catalogue changed')
 active={}
 for a in csv.DictReader(raw.open(encoding='utf-8-sig')):
  if a['iata_code'] and a['type']!='closed':active.setdefault(a['iata_code'],[]).append(a)
 zones={r[4]:r[11] for r in csv.reader(tz.open()) if len(r)>11 and r[11]!='\\N' and any(r[5] in (a.get('icao_code'),a['ident']) for a in active.get(r[4],[]))}
 for path in sorted((ROOT/'data/sources').glob('*routes.json')):
  if path.name=='africa_flights_routes.json':continue
  for a in json.loads(path.read_text()).get('airports',[]):
   if a.get('timezone') and any(a.get('icao') in (r.get('icao_code'),r['ident']) for r in active.get(a.get('code'),[])):zones[a['code']]=a['timezone']
 zones.update({c:a['timezone'] for c,a in air.items()})
 unresolved={}
 def airport(code):
  if code in air:return air[code]
  hits=active.get(code,[])
  if len(hits)!=1 or not zones.get(code):
   unresolved[code]='Missing/ambiguous active identity or explicit timezone';return None
  a=hits[0];ZoneInfo(zones[code]);air[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=a['iso_country'],timezone=zones[code],mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
  return air[code]
 evidence={(r['origin'],r['destination']):list(r['sources']) for r in base['evidence']};expanded=set();excluded=[]
 for row in base['deferred_routes']:
  a,b=row['origin'],row['destination'];aa,bb=airport(a),airport(b)
  if not aa or not bb or a==b or any(x['country'] not in AFRICAN for x in (aa,bb)):
   excluded.append(dict(**row,review='Unresolved exact African passenger-airport pair'));continue
  expanded.add((a,b));evidence.setdefault((a,b),[]).append(dict(source=row['source'],kind='Frozen starter published pair deferred solely by the 30-airport boundary; dated service remains unverified',new_collection=True))
 reusable={}
 for directory in sorted((ROOT/'.cache').glob('google-flights*')):
  if not directory.is_dir() or directory==CACHE:continue
  for path in sorted(directory.rglob(f'{DAY}-*.json')):
   match=re.fullmatch(rf'{DAY}-([A-Z0-9]{{3}})-([A-Z0-9]{{3}})\.json',path.name)
   if not match:continue
   a,b=match.groups()
   if not any(len(active.get(c,[]))==1 and active[c][0]['iso_country'] in AFRICAN for c in (a,b)):continue
   aa,bb=airport(a),airport(b)
   if not aa or not bb:continue
   try:q=validate_query(json.loads(path.read_text()),(DAY,a,b),{'zones':zones})
   except (ValueError,KeyError,TypeError):continue
   if not q['flights']:continue
   source=str(path.relative_to(ROOT));reusable.setdefault((a,b),[]).append(source)
   item=dict(source=source,kind='Compatible dated African capture; reuse only',new_collection=False)
   if item not in evidence.setdefault((a,b),[]):evidence[(a,b)].append(item)
 used={c for pair in evidence for c in pair}|set(base['launch_airports']);basis=[dict(origin=a,destination=b,sources=ss) for (a,b),ss in sorted(evidence.items())]
 archive=ROOT/base['archive_snapshot']['path'];digest=hashlib.sha256(json.dumps(basis,sort_keys=True).encode()).hexdigest()
 return {**base,'airports':[air[c] for c in sorted(used)],'countries':sorted({air[c]['country'] for c in used}),
  'routes':[list(p) for p in sorted(evidence)],'new_collection_routes':[list(p) for p in sorted(set(map(tuple,base['new_collection_routes']))|expanded)],
  'reuse_sources':[dict(origin=a,destination=b,paths=ps) for (a,b),ps in sorted(reusable.items())],
  'evidence':basis,'route_source_sha256':digest,'additional_selection_sha256':digest,
  'archive_snapshot':dict(path=base['archive_snapshot']['path'],sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),
  'starter_manifest':dict(path=str(STARTER.relative_to(ROOT)),sha256=STARTER_HASH),
  'expanded_routes':[list(p) for p in sorted(expanded)],'expansion_exclusions':excluded,
  'refresh_empty_queries':[['ACC','FCO']],
  'resolved_starter_airports':[r['code'] for r in base['unresolved_airports'] if r['code'] in used],
  'deferred_routes':excluded,'unresolved_airports':[r for r in base['unresolved_airports'] if r['code'] not in used]+[dict(code=c,reason=v) for c,v in sorted(unresolved.items()) if c in used],
  'coverage_scope':'Original 30 African gateways, their 658 previously deferred published African directions, and compatible cached positives. No all-pairs, extra dates or new worldwide gateway sweep.'}
