"""Pinned full Ryanair and easyJet Europe-connected route discovery."""
import csv,hashlib,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download
from dashboard.europe_flights import EUROPE_COUNTRIES as EUROPE
ZONES=dict(zip('AL AT BA BE BG CH CY CZ DE DK EE FI FR GB GE GI GR HR HU IE IM IS IT JE LT LU LV ME MK MT NL NO PL PT RO RS SE SI SK TR XK MA EH EG CV TN JO'.split(),
 'Europe/Tirane Europe/Vienna Europe/Sarajevo Europe/Brussels Europe/Sofia Europe/Zurich Asia/Nicosia Europe/Prague Europe/Berlin Europe/Copenhagen Europe/Tallinn Europe/Helsinki Europe/Paris Europe/London Asia/Tbilisi Europe/Gibraltar Europe/Athens Europe/Zagreb Europe/Budapest Europe/Dublin Europe/Isle_of_Man Atlantic/Reykjavik Europe/Rome Europe/Jersey Europe/Vilnius Europe/Luxembourg Europe/Riga Europe/Podgorica Europe/Skopje Europe/Malta Europe/Amsterdam Europe/Oslo Europe/Warsaw Europe/Lisbon Europe/Bucharest Europe/Belgrade Europe/Stockholm Europe/Ljubljana Europe/Bratislava Europe/Istanbul Europe/Belgrade Africa/Casablanca Africa/El_Aaiun Africa/Cairo Atlantic/Cape_Verde Africa/Tunis Asia/Amman'.split()))
CORE='STN LTN LGW SEN DUB EDI BRS MAN BFS BCN MAD AGP LIS OPO CDG ORY BVA FCO CIA MXP BGY LIN VCE NAP CTA BER HHN CGN AMS EIN GVA BSL VIE PRG BUD WAW WMI KRK ATH SKG SOF OTP CPH ARN OSL HEL KEF RIX VNO TIA RAK PMO'.split()
SOURCES={'ryanair':'https://www.ryanair.com/api/views/locate/3/aggregate/all/en','easyjet':'https://www.easyjet.com/en/flights-timetables'}
PILOT={'ryanair':'STN-DUB BGY-CTA STN-RAK BFS-STN','easyjet':'LGW-BCN GVA-LGW BSL-NCE LTN-EDI'}


def build(ryanair_full=True,easyjet_full=True):
 seed=json.loads((ROOT/'data/sources/europe_flights_discovery.json').read_text())
 raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
 with raw.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 def airport(code):
  hits=[a for a in rows if a['iata_code']==code and a['type']!='closed']
  if len(hits)!=1:raise ValueError(f'Unresolved exact airport {code}')
  a=hits[0];country=a['iso_country'];zone=seed['ryanair_zones'].get(code) or ZONES.get(country)
  if country=='ES':zone='Atlantic/Canary' if code in {'ACE','FUE','LPA','SPC','TFS','TFN','VDE','GMZ'} else 'Europe/Madrid'
  if country=='PT':zone='Atlantic/Azores' if code in {'PDL','TER','HOR','PIX','SMA','SJZ','FLW','GRW','CVU'} else ('Atlantic/Madeira' if code in {'FNC','PXO'} else 'Europe/Lisbon')
  if not zone:raise ValueError(f'Unresolved zone {code}/{country}')
  ZoneInfo(zone)
  return dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=country,timezone=zone,europe=country in EUROPE,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
 all_codes={c for ps in seed['routes'].values() for p in ps for c in p};air={c:airport(c) for c in sorted(all_codes)};selected={};discovered={}
 priority={c:i for i,c in enumerate(CORE)}
 for brand,ps in seed['routes'].items():
  candidates={tuple(p) for p in ps if air[p[0]]['europe'] or air[p[1]]['europe']};discovered[brand]=len(candidates)
  edges={tuple(sorted(p)) for p in candidates};chosen=set()
  def rank(p):return (sum(c not in priority for c in p),sum(priority.get(c,999) for c in p),p)
  ordered=sorted(edges,key=rank)
  for p in PILOT[brand].split():
   edge=tuple(sorted(p.split('-')))
   if edge not in edges:raise ValueError(f'Pilot route absent from source: {edge}')
   chosen.add(edge)
  # Represent each published country, then selected major/secondary airports.
  for country in sorted({air[c]['country'] for p in edges for c in p}):chosen.add(next(p for p in ordered if any(air[c]['country']==country for c in p)))
  for code in CORE:
   options=[p for p in ordered if code in p]
   if options:chosen.add(options[0])
  # Round-robin airports, avoiding a single hub-star sample.
  for offset in range(1,40):
   for code in CORE:
    options=[p for p in ordered if code in p]
    if len(chosen)>=80:break
    if len(options)>offset:chosen.add(options[offset])
   if len(chosen)>=80:break
  selected[brand]=sorted(candidates if {'ryanair':ryanair_full,'easyjet':easyjet_full}[brand] else (p for p in candidates if tuple(sorted(p)) in chosen))
 pairs=sorted({p for ps in selected.values() for p in ps});codes={c for p in pairs for c in p}
 doc=dict(profile='europe_flights',scope='both',start_date='2026-11-02',end_date='2026-11-02',timezone='UTC',currency='EUR',max_duration=28800,
  airports=[air[c] for c in sorted(codes)],routes=pairs,routes_by_brand=selected,europe_countries=sorted(EUROPE),source_urls=SOURCES,source_documents=seed['sources'],source_reviewed_date='2026-10-26',
  discovered_routes_by_brand=discovered,discovered_unique_routes=len({p for ps in seed['routes'].values() for p in map(tuple,ps) if air[p[0]]['europe'] or air[p[1]]['europe']}),
  selection=('Full published Europe-connected Ryanair and easyJet airport-pair catalogues' if ryanair_full and easyjet_full else ('Full published Ryanair airport-pair catalogue; easyJet retains the 80-pair broad starter' if ryanair_full else 'Broad starter requested by user: published-country coverage, reviewed major/secondary airports, then deterministic round-robin; up to 80 undirected pairs per brand')),unresolved_airports=[],airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH)
 doc['route_source_sha256']=hashlib.sha256(json.dumps(dict(seed=seed,selection=doc['selection'],core=CORE,routes=pairs),sort_keys=True).encode()).hexdigest()
 (ROOT/'data/sources/europe_flights_routes.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n');print(dict(airports=len(codes),directions=len(pairs),brands={k:len(v) for k,v in selected.items()},discovered=discovered))


if __name__=='__main__':build()
