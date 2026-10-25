"""Resolve recovered Philippine candidates against pinned airport identities."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL,AIRPORT_HASH,pinned_download

DAY='2026-11-02'
COUNTRIES={'AU','ID','MY','SG','IN','TH','CN','JP','KR','AE','QA','PH'}
HUBS={'DXB','AUH','DOH'}


def prepare():
    seed_path=ROOT/'data/sources/philippines_recovered_candidates.json'
    seed=json.loads(seed_path.read_text())
    # This correction applies only to the package row claiming PH/Naga. NAG
    # remains Nagpur in existing Indian catalogues and international candidates.
    aliases={'NAG':'WNP'}
    identities={aliases.get(a['code'],a['code']):a for a in seed['philippines_airports']}
    catalogue={};international=set();evidence=[];inputs=[]
    # Existing sources can be richer than this reconstructed package. Preserve
    # their Philippine candidates and exact identities without overwriting them.
    paths=sorted(p for p in ROOT.glob('data/sources/*_international_routes.json') if p.name not in {'philippines_international_routes.json','thailand_international_routes.json'})+[ROOT/'data/sources/gulf_flights_routes.json']
    for path in paths:
        d=json.loads(path.read_text());air={a['code']:a for a in d['airports']};catalogue.update(air)
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for a,b in d['routes']:
            aa,bb=air[a],air[b]
            if 'PH' not in {aa['country'],bb['country']} or aa['country']==bb['country']:continue
            if any(x['country'] not in COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in HUBS) for x in (aa,bb)):continue
            international.add((a,b));evidence.append(dict(origin=a,destination=b,source=str(path.relative_to(ROOT)),kind='Existing route/probe candidate; dated nonstop capture required'))
    existing_count=len(international);domestic=set();deferred=[]
    for scope in ['domestic','international']:
        for r in seed[f'philippines_{scope}_routes']:
            a,b=aliases.get(r['origin_iata'],r['origin_iata']),aliases.get(r['destination_iata'],r['destination_iata']);aa,bb=identities[a],identities[b]
            if scope=='international' and any(x['country'] not in COUNTRIES or (x['country'] in {'AE','QA'} and x['code'] not in HUBS) for x in (aa,bb)):
                deferred.append(dict(origin=a,destination=b,reason='Outside existing SunTrain flight countries'));continue
            if scope=='domestic' and (aa['country']!='PH' or bb['country']!='PH'):raise ValueError('Foreign domestic candidate')
            (domestic if scope=='domestic' else international).add((a,b))
            evidence.append(dict(origin=a,destination=b,source=r['source_url'],source_locator=r['source_locator'],
                original_origin=r['origin_iata'],original_destination=r['destination_iata'],
                kind='Recovered partial-package candidate, not independently verified route or dated-flight evidence',
                original_candidate_type=r['candidate_type'],target_date_status=r['target_date_status'],
                effective_from=r['effective_from'],effective_to=r['effective_to'],notes=r['notes']))
    needed={c for pair in domestic|international for c in pair}
    raw=pinned_download(AIRPORT_URL,ROOT/'.cache/australia-flights-audit/ourairports-airports.csv',AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    resolved={}
    for code in sorted(needed):
        old=catalogue.get(code,{});hint=identities.get(code,old);country=hint['country']
        matches=[a for a in rows if a['iata_code']==code and a['iso_country']==country and a['type']!='closed']
        if len(matches)!=1:raise ValueError(f'Unresolved or ambiguous airport: {code}')
        a=matches[0];zone='Asia/Manila' if country=='PH' else old.get('timezone') or hint.get('timezone')
        if country=='CN':zone='Asia/Shanghai'
        if country=='IN':zone='Asia/Kolkata'
        ZoneInfo(zone)
        entry=dict(code=code,icao=a.get('icao_code') or a['ident'],name=f"{a['name']} ({code})",municipality=a['municipality'],
            country=country,timezone=zone,mode='flight',lat=float(a['latitude_deg']),lon=float(a['longitude_deg']))
        if country=='PH':entry['island_group']=hint.get('island_group') or identities[code]['island_group']
        resolved[code]=entry
    for scope,pairs in [('domestic',domestic),('international',international)]:
        codes={c for pair in pairs for c in pair};ev=[e for e in evidence if (e['origin'],e['destination']) in pairs]
        manifest=dict(country='PH',scope=scope,start_date=DAY,end_date=DAY,timezone='Asia/Manila',currency='USD',max_duration=(8 if scope=='domestic' else 24)*3600,
            airports=[resolved[c] for c in sorted(codes)],routes=[list(p) for p in sorted(pairs)],evidence=ev,
            coverage_scope='Recovered selected candidates; international restricted to existing SunTrain flight countries',
            airport_source_url=AIRPORT_URL,airport_source_sha256=AIRPORT_HASH,
            identity_corrections=[dict(original='NAG',resolved='WNP',country='PH',reason='Recovered Naga row used Nagpur IATA; pinned PH/Naga identity is WNP/RPUN')],
            recovered_package=dict(filename=seed['source_filename'],sha256=seed['source_sha256'],metadata=seed['source_metadata']),
            input_seed_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),input_manifests=inputs if scope=='international' else [],
            route_source_url='https://clarkinternationalairport.com/flights/',
            route_hash_basis='Curated recovered candidates and input pins, not raw website bytes',unresolved_airports=[],
            deferred_international_routes=deferred if scope=='international' else [],source_reviewed_date='2026-10-25',
            base_directional_routes=existing_count if scope=='international' else 0)
        manifest['route_source_sha256']=hashlib.sha256(json.dumps(dict(evidence=ev,inputs=manifest['input_manifests'],seed=manifest['input_seed_sha256']),sort_keys=True).encode()).hexdigest()
        name='flights' if scope=='domestic' else 'international'
        (ROOT/f'data/sources/philippines_{name}_routes.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(dict(scope=scope,airports=len(codes),routes=len(pairs),existing_candidates=manifest['base_directional_routes'],deferred=len(manifest['deferred_international_routes']))))


if __name__=='__main__':prepare()
