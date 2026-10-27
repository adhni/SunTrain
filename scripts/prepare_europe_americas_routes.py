"""Intersect pinned European route pairs with existing Americas airports; never expand airport pairs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DAY='2026-11-02'
OUTPUT=ROOT/'data/sources/europe_americas_flights_routes.json'


def build():
    paths=[ROOT/'data/sources/europe_groups_routes.json',ROOT/'data/sources/americas_flights_routes.json']
    groups,americas=[json.loads(p.read_text()) for p in paths]
    airports={a['code']:a for a in groups['airports']}
    american={a['code']:a for a in americas['airports']}
    # Match exact airport identity, not city aliases. Preserve the capture parser's
    # original IANA zones; this view does not reinterpret regional replay overrides.
    for code in airports.keys() & american.keys():
        if any(airports[code][k]!=american[code][k] for k in ('icao','country','lat','lon')):
            raise ValueError(f'Conflicting exact airport identity: {code}')
    pairs=sorted({(a,b) for a,b in groups['routes']
        if (a in american and airports[b]['europe']) or (b in american and airports[a]['europe'])})
    used={c for pair in pairs for c in pair}
    provenance=[]
    by_brand={brand:set(map(tuple,routes)) for brand,routes in groups['routes_by_brand'].items()}
    for a,b in pairs:
        brands=sorted(brand for brand,routes in by_brand.items() if (a,b) in routes)
        if not brands:
            raise ValueError('Route lacks pinned discovery evidence')
        provenance.append(dict(origin=a,destination=b,discovery_brands=brands,
            source_urls=sorted({groups['source_urls'][brand] for brand in brands}),
            kind='Pinned published route-map candidate; all returned airlines eligible, dated captures required'))
    inputs=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    basis=dict(inputs=inputs,evidence=provenance)
    digest=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(profile='europe_americas',countries=sorted({airports[c]['country'] for c in used}),
        start_date=DAY,end_date=DAY,timezone='UTC',currency='EUR',scope='regional',max_duration=86400,
        query_date_policy='origin_local_departure_day_only',
        airports=[airports[c] for c in sorted(used)],routes=[list(p) for p in pairs],
        regions=dict(europe=sorted(c for c in used if airports[c]['europe']),americas=sorted(used & american.keys())),
        evidence=provenance,input_manifests=inputs,source_documents=groups['source_documents'],
        source_reviewed_date=groups['source_reviewed_date'],route_source_sha256=digest,
        route_source_hash_basis='SHA256 of normalized pinned discovery evidence and input manifest hashes',
        route_source_url='data/sources/europe_groups_discovery.json',additional_selection_sha256=digest,
        coverage_scope='Published European flag-carrier route candidates intersected with the existing 77-airport Americas catalogue; all returned airlines on those pairs, not every European or Americas route.',
        replay_note='Europe–Americas connections between selected airports. Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. Timeline: UTC; airport boards use local time. Existing EUR quotes are retained without conversion. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.',
        unresolved_airports=[])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();manifest=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(manifest['airports']),directions=len(manifest['routes']),europe=len(manifest['regions']['europe']),americas=len(manifest['regions']['americas']))))
