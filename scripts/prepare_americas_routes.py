"""Build a sourced, single-date cross-Americas search shortlist without flight searches.

Run with --dry-run to report the search budget. Published routes are candidates,
not evidence that a flight operates on the replay date.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-11-02'
EVIDENCE = ROOT / 'data/sources/americas_route_evidence.json'
OUTPUT = ROOT / 'data/sources/americas_connections_routes.json'
INPUTS = ['united_states_flights_routes.json', 'south_america_flights_routes.json']


def build(root=ROOT):
    evidence_path = root / EVIDENCE.relative_to(ROOT)
    reviewed = json.loads(evidence_path.read_text())
    if reviewed['departure_date'] != DAY:
        raise ValueError('Shortlist must use the existing replay date')
    manifests, inputs = [], []
    for name in INPUTS:
        path = root / 'data/sources' / name
        manifests.append(json.loads(path.read_text()))
        inputs.append(dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    north, south = [{a['code']: a for a in m['airports']} for m in manifests]
    if north.keys() & south.keys():
        raise ValueError('Regional airport catalogues must be distinct')
    airports = {**north, **south}
    reviews = reviewed['airport_reviews']
    if len(reviews) != len(south) or {r['airport'] for r in reviews} != south.keys():
        raise ValueError('Every southern airport needs exactly one discovery review')
    pairs, provenance = set(), []

    def add(a, b, source_ids, kind):
        if not ((a in south and b in north) or (a in north and b in south)):
            raise ValueError(f'Candidate outside selected cross-region airports: {a}-{b}')
        if not source_ids or any(s not in reviewed['sources'] for s in source_ids):
            raise ValueError('Candidate needs a reviewed source')
        pairs.update([(a, b), (b, a)])
        provenance.append(dict(origin=a, destination=b, source_ids=source_ids, kind=kind,
            direction_policy='Search both directions independently; no reverse-day service inferred'))

    for review in reviews:
        if len(set(review['destinations'])) != len(review['destinations']):
            raise ValueError('Repeated airport in reviewed destination list')
        for b in review['destinations']:
            add(review['airport'], b, review['source_ids'], 'Published nonstop candidate; dated capture required')
    for review in reviewed['corroboration']:
        for b in review['destinations']:
            add(review['airport'], b, [review['source_id']], 'Official direct-route candidate; dated capture required')
    for item in reviewed['excluded_candidates']:
        if (item['origin'], item['destination']) in pairs or (item['destination'], item['origin']) in pairs:
            raise ValueError('Excluded seasonal candidate reintroduced')
    return dict(profile='americas_connections', scope='regional', start_date=DAY, end_date=DAY,
        timezone='UTC', currency='USD', max_duration=16*3600,
        query_date_policy='origin_local_departure_day_only', concurrency=2,
        airports=[airports[c] for c in sorted(airports)],
        regions=dict(north=sorted(north), south=sorted(south)),
        routes=[list(p) for p in sorted(pairs)],
        queries=[[DAY, a, b] for a, b in sorted(pairs)],
        possible_cross_region_directions=2*len(north)*len(south),
        evidence=sorted(provenance, key=lambda e:(e['origin'], e['destination'], e['source_ids'])),
        sources=reviewed['sources'], airport_reviews=reviews,
        excluded_candidates=reviewed['excluded_candidates'],
        evidence_path=str(evidence_path.relative_to(root)),
        route_source_sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        route_source_hash_basis='SHA256 of committed normalized discovery facts; not raw source-page bytes',
        input_manifests=inputs, reviewed_on=reviewed['reviewed_on'], limitations=reviewed['limitations'])


def combined_manifest(shortlist, root=ROOT):
    manifests = [json.loads((root/'data/sources'/name).read_text()) for name in INPUTS]
    routes = sorted({tuple(p) for m in [*manifests, shortlist] for p in m['routes']})
    snapshots = []
    for slug in ['united_states', 'south_america']:
        path = root/f'data/reference/{slug}_flights/{DAY}.json.gz'
        snapshots.append(dict(path=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return dict(profile='americas', countries=sorted({a['country'] for a in shortlist['airports']}),
        scope='regional', start_date=DAY, end_date=DAY, timezone='UTC', currency='USD', max_duration=16*3600,
        query_date_policy='origin_local_departure_day_only', airports=shortlist['airports'], routes=[list(p) for p in routes],
        cross_region_routes=shortlist['routes'], regions=shortlist['regions'], input_snapshots=snapshots,
        route_source_url=str(EVIDENCE.relative_to(ROOT)), route_source_sha256=shortlist['route_source_sha256'],
        route_source_hash_basis=shortlist['route_source_hash_basis'],
        additional_selection_sha256=shortlist['route_source_sha256'], unresolved_airports=[],
        coverage_scope='Existing 50-airport North America and 27-airport South America snapshots plus sourced cross-region candidates. Other airports and unlisted cross-region pairs are not searched.',
        replay_note='Americas domestic and cross-border flights between 77 selected airports. Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. Timeline: UTC; airport boards use local time. All captured fares use USD. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.')


def budget(manifest, cache):
    """Count only captures matching the exact route/date and requested USD context."""
    reusable, incompatible = [], []
    for d, a, b in manifest['queries']:
        path = cache / f'{d}-{a}-{b}.json'
        if not path.exists():
            continue
        try:
            q = json.loads(path.read_text())
            if (q['date'], q['origin'], q['destination']) != (d, a, b):
                raise ValueError('Wrong query identity')
            if q['status'] not in {'results', 'no_matching_direct_flights'} or bool(q['flights']) != (q['status']=='results'):
                raise ValueError('Unsuccessful or inconsistent query')
            # Currency is encoded in the capture URL even for empty/no-price pages.
            from urllib.parse import parse_qs, urlparse
            if parse_qs(urlparse(q['url']).query).get('curr') != ['USD']:
                raise ValueError('Wrong capture currency')
            if any(f['origin']!=a or f['destination']!=b or f['source_date']!=d
                   or (f.get('price') and f['price']['currency']!='USD') for f in q['flights']):
                raise ValueError('Wrong segment or price context')
            reusable.append([d, a, b])
        except (ValueError, KeyError, TypeError):
            incompatible.append(str(path))
    total = len(manifest['queries'])
    return dict(airports=len(manifest['airports']), southern_airports_reviewed=len(manifest['airport_reviews']),
        airport_pairs=len(manifest['routes'])//2, directional_queries=total,
        dates=[DAY], currency='USD', concurrency=2,
        possible_cross_region_directions=manifest['possible_cross_region_directions'],
        directions_avoided=manifest['possible_cross_region_directions']-total,
        reusable_queries=len(reusable), new_queries=total-len(reusable), incompatible_captures=incompatible,
        starts_collection=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--cache', type=Path, default=ROOT/'.cache/google-flights-americas-usd-v1')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    manifest = build()
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
        (args.output.parent/'americas_flights_routes.json').write_text(json.dumps(combined_manifest(manifest), indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(budget(manifest, args.cache)))


if __name__ == '__main__':
    main()
