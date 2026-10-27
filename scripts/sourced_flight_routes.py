"""Build sourced exact-airport flight candidates for a country and selected worldwide hubs."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_HASH,AIRPORT_URL
from scripts.prepare_gulf_airports import TZ_HASH,TZ_URL
DAY='2026-11-02'


def build(profile,country,timezone,cache,coverage_scope,replay_note,deferred_reason,timezone_overrides=None):
    discovery=json.loads((ROOT/f'data/sources/{profile}_flights_discovery.json').read_text())
    hubs=set(discovery['launch_airports']);worldwide=set(discovery['worldwide_hubs'])
    for path,digest in [(ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH),(ROOT/'.cache/gulf-flights-audit/openflights-airports.dat',TZ_HASH)]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Pinned airport/timezone source changed')
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        active={}
        for a in csv.DictReader(stream):
            if a['iata_code'] and a['type']!='closed':active.setdefault(a['iata_code'],[]).append(a)
    with (ROOT/'.cache/gulf-flights-audit/openflights-airports.dat').open() as stream:
        zones={r[4]:r[11] for r in csv.reader(stream) if len(r)>11 and r[11]!='\\N' and any(r[5] in (a.get('icao_code'),a['ident']) for a in active.get(r[4],[]))}
    manifests=[]
    for path in sorted((ROOT/'data/sources').glob('*routes.json')):
        if path.name==f'{profile}_flights_routes.json':continue
        m=json.loads(path.read_text());manifests.append((path,m))
        for a in m.get('airports',[]):
            if any(a.get('icao') in (r.get('icao_code'),r['ident']) for r in active.get(a.get('code'),[])):
                zones[a['code']]=a['timezone']
    # Current exact airports absent from the older OpenFlights catalogue.
    # National airports use the configured IANA zone; foreign airports retain their own.
    overrides={'GNJ':'Asia/Baku','GRV':'Europe/Moscow','GSV':'Europe/Saratov',
        'KVO':'Europe/Belgrade','MRA':'Africa/Tripoli','KRT':'Africa/Khartoum','JCL':'Europe/Prague'}
    overrides.update({code:timezone for code,rows in active.items() if len(rows)==1 and rows[0]['iso_country']==country})
    overrides.update(timezone_overrides or {})
    zones.update(overrides)
    unresolved={};airports={}
    def airport(code):
        if code in airports:return airports[code]
        rows=active.get(code,[])
        if len(rows)!=1 or not zones.get(code):
            unresolved[code]='Ambiguous/missing active IATA identity or explicit timezone';return None
        a=rows[0];ZoneInfo(zones[code])
        airports[code]=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],country=a['iso_country'],timezone=zones[code],mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        return airports[code]
    evidence={};deferred=[]
    def add(a,b,source,kind,new=True):
        aa,bb=airport(a),airport(b)
        if a==b or not aa or not bb:return
        if new and aa['country']!=bb['country'] and (any(x['country']==country and x['code'] not in hubs for x in (aa,bb)) or not set((a,b)) & worldwide):
            deferred.append(dict(origin=a,destination=b,reason=deferred_reason,source=source));return
        if not any(x['country']==country for x in (aa,bb)):return
        evidence.setdefault((a,b),[]).append(dict(source=source,kind=kind,new_collection=new))
    for row in discovery['airport_maps']+discovery.get('supplemental_airport_maps',[]):
        for b in row['destinations']:
            for a,c in [(row['airport'],b),(b,row['airport'])]:
                add(a,c,row['documents'][-1]['url'],'Published outbound map; reverse query is a candidate only')
    for path,m in manifests:
        for pair in m.get('routes',[]):
            if len(pair)==2 and set(pair)&hubs:
                add(*pair,str(path.relative_to(ROOT)),'Previously sourced exact-airport candidate')
    # Reuse positive captures even beyond the launch footprint, without new queries.
    reusable={}
    for directory in sorted((ROOT/'.cache').glob('google-flights*')):
        if not directory.is_dir() or directory==cache:continue
        for path in sorted(directory.rglob(f'{DAY}-*.json')):
            match=re.fullmatch(rf'{DAY}-([A-Z0-9]{{3}})-([A-Z0-9]{{3}})\.json',path.name)
            if not match:continue
            a,b=match.groups();aa,bb=airport(a),airport(b)
            if not aa or not bb or not any(x['country']==country for x in (aa,bb)):continue
            q=json.loads(path.read_text())
            if not q.get('flights') or q.get('rejected_flights') or q.get('status')!='results':continue
            add(a,b,str(path.relative_to(ROOT)),'Previously captured dated national route; reuse only',new=False)
            reusable.setdefault((a,b),[]).append(str(path.relative_to(ROOT)))
    archive_path=ROOT/'data/reference/europe_flights/2026-11-02.json.gz'
    with gzip.open(archive_path,'rt') as stream:archive=json.load(stream)
    archive_routes=set()
    for f in archive['flights']:
        if f.get('schedule_source')!='ryanair_public_timetable' or f.get('source_date')!=DAY:continue
        a,b=f['origin'],f['destination'];aa,bb=airport(a),airport(b)
        if aa and bb and any(x['country']==country for x in (aa,bb)):
            add(a,b,str(archive_path.relative_to(ROOT)),'Existing dated official timetable capture; reuse only',new=False)
            archive_routes.add((a,b))
    used=hubs|{c for pair in evidence for c in pair}
    for c in hubs:airport(c)
    basis=[dict(origin=a,destination=b,sources=s) for (a,b),s in sorted(evidence.items())]
    digest=hashlib.sha256(json.dumps(basis,sort_keys=True).encode()).hexdigest()
    return dict(profile=profile,countries=sorted({airports[c]['country'] for c in used if c in airports}),
        start_date=DAY,end_date=DAY,timezone=timezone,currency='USD',scope='regional',max_duration=86400,
        query_date_policy='origin_local_departure_day_only',launch_airports=sorted(hubs),worldwide_hubs=sorted(worldwide),
        airports=[airports[c] for c in sorted(used) if c in airports],routes=[list(p) for p in sorted(evidence)],
        new_collection_routes=[list(p) for p,sources in sorted(evidence.items()) if any(e['new_collection'] for e in sources)],
        archive_snapshot=dict(path=str(archive_path.relative_to(ROOT)),sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest()),
        archive_reuse_routes=[list(p) for p in sorted(archive_routes)],
        reuse_sources=[dict(origin=a,destination=b,paths=paths) for (a,b),paths in sorted(reusable.items())],
        evidence=basis,route_source_sha256=digest,additional_selection_sha256=digest,
        airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,timezone_source_url=TZ_URL,timezone_source_sha256=TZ_HASH,
        timezone_overrides=overrides,
        input_manifests=[dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path,_ in manifests if any(str(path.relative_to(ROOT))==e['source'] for row in basis for e in row['sources'])],
        route_source_url=f'data/sources/{profile}_flights_discovery.json',
        source_gaps=[r for r in discovery['airport_maps'] if r.get('error')],
        deferred_routes=deferred,unresolved_airports=[dict(code=c,reason=v) for c,v in sorted(unresolved.items()) if c in used or any(c in (r['airport'],) or c in r['destinations'] for r in discovery['airport_maps']+discovery.get('supplemental_airport_maps',[]))],
        coverage_scope=coverage_scope,replay_note=replay_note)
