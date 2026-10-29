"""Recover international caches, then collect at most 1,000 new World queries."""
import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard import world_flights as world, international_expansion as adapter
from dashboard.flight_sources import cached_reference_reads
from scripts.discover_international_expansion import (
    Airports, CACHE, DAY, SOURCE, audit, digest, merged_attempts, read, relative, save, timestamp, validate_query)
from scripts.prepare_google_flights import capture

CAPTURES = ROOT / '.cache/google-flights-world-international-usd-v1'


def baseline_query_times(cache=CACHE):
    """Validated adapter ownership outranks older raw caches, including empties."""
    path = cache / 'validated-queries.json.gz'
    if path.exists():
        return read(path)
    from dashboard.cities import CITIES
    from dashboard.flights import load_reference
    times = {}
    official = set()
    with cached_reference_reads() as inputs:
        for city, settings in sorted(CITIES.items()):
            if city == 'world_flights' or settings.get('replay_kind') != 'flights':
                continue
            reference = load_reference(DAY, city)
            for query in reference['metadata'].get('queries', []):
                if (query.get('status') not in {'results', 'no_matching_direct_flights'}
                        or not all(query.get(k) for k in ('date', 'origin', 'destination', 'captured_at'))):
                    continue
                key = '|'.join(query[k] for k in ('date', 'origin', 'destination'))
                when = timestamp(query['captured_at'])
                times[key] = max(times.get(key, 0), when)
            official.update(f['id'] for f in reference['flights'] if f.get('schedule_source') == 'ryanair_public_timetable')
        expected = read(cache / 'baseline.json.gz')['metadata']['inputs']
        if {relative(p): v for p, v in inputs.items()} != expected:
            raise ValueError('Validated sources changed since the baseline was frozen')
    result = dict(times=times, protected_official_ids=sorted(official))
    save(path, result)
    return result


def quotes(flight):
    return [{k: v for k, v in q.items() if k != 'views'}
            for q in ([flight['price']] if flight.get('price') else []) + flight.get('fare_quotes', [])]


def record_query_key(flight, airports):
    airport = airports[flight['origin']]
    local = datetime.fromtimestamp(flight['departure'], ZoneInfo(airport.get('replay_timezone', airport['timezone'])))
    return local.date().isoformat(), flight['origin'], flight['destination']


def prepare(cache=CACHE, output=None, include_fresh=True):
    # The committed prepared supplement remains usable without raw caches, but
    # rebuilding it must not silently discard evidence when a cache was cleared.
    published = read(SOURCE) if SOURCE.exists() else {}
    if published.get('collection') and adapter.reference_path().exists():
        existing = read(adapter.reference_path())
        checked = set()
        for query in existing['metadata']['queries']:
            for source in query['source_documents']:
                if not include_fresh and source['path'].startswith(relative(CAPTURES) + '/'):
                    continue
                path = ROOT/source['path']
                if path in checked:
                    continue
                if not path.exists() or digest(path.read_bytes()) != source['sha256']:
                    raise ValueError('Published raw capture missing or changed; retain the prepared supplement and regenerate World offline')
                checked.add(path)
    baseline = read(cache / 'baseline.json.gz')
    indexed = read(cache / 'cache-index.json.gz')
    authority = baseline_query_times(cache)
    airports = Airports(baseline)
    baseline_airports = {a['code']: a for a in baseline['airports']}
    by_query = defaultdict(list)
    for flight in baseline['flights']:
        if flight['flight_scope'] == 'international':
            by_query[record_query_key(flight, baseline_airports)].append(flight)
    protected = set(authority['protected_official_ids'])
    records, queries, decisions = [], [], []
    stats = Counter()
    for item in indexed['queries']:
        key = tuple(item['query'])
        if not adapter.is_international(airports.get(key[1]), airports.get(key[2])):
            continue
        sources = [s for s in item['sources'] if include_fresh or not s['path'].startswith(relative(CAPTURES) + '/')]
        if not sources:
            continue
        sources.sort(key=lambda s: (timestamp(s['captured_at']), s['path']))
        latest = sources[-1]
        if timestamp(latest['captured_at']) < authority['times'].get('|'.join(key), 0):
            stats['superseded_by_validated_adapter'] += 1
            decisions.append(dict(query=list(key), decision='superseded_by_validated_adapter'))
            continue
        schedules = []
        for info in sources:
            path = ROOT / info['path']
            raw = path.read_bytes()
            if digest(raw) != info['sha256']:
                raise ValueError(f'Capture changed after indexing: {path}')
            schedules.append(validate_query(json.loads(raw), key, airports, info.get('parser_evidence', {}).get('max_duration')))
        newest = schedules[-1]
        all_quotes, all_aircraft = defaultdict(dict), defaultdict(set)
        for query in schedules:
            for flight in query['flights']:
                identity = world.identity(flight)
                for quote in quotes(flight):
                    all_quotes[identity][world.canonical_json(quote)] = quote
                name = world.aircraft_name(flight)
                if name != 'Aircraft not specified':
                    all_aircraft[identity].add(name)
        current = [f for f in newest['flights'] if f['departure'] < world.END and f['arrival'] >= world.START]
        old = by_query[key]
        old_ids = {world.identity(f) for f in old}
        new_ids = {world.identity(f) for f in current}
        changed = new_ids != old_ids
        enriched = False
        prepared = []
        old_by_identity = {world.identity(f): f for f in old}
        for flight in current:
            identity = world.identity(flight)
            row = {**flight, 'flight_scope': 'international', 'source_page': newest['url']}
            offers = sorted(all_quotes[identity].values(), key=lambda q: (
                world.CURRENCIES.index(q['currency']), q['amount_minor'], world.canonical_json(q)))
            if offers:
                row['price'] = offers[0]
                row['fare_quotes'] = offers
            names = sorted(all_aircraft[identity])
            if len(names) > 1:
                row['aircraft'] = 'Aircraft differs between captures'
                row['aircraft_variants'] = [dict(aircraft=name) for name in names]
            elif names:
                row['aircraft'] = names[0]
            prior = old_by_identity.get(identity)
            if prior:
                old_quotes = {world.canonical_json(q) for q in quotes(prior)}
                enriched |= bool(set(all_quotes[identity]) - old_quotes)
                enriched |= bool(names and world.aircraft_name(prior) not in names)
            prepared.append(row)
        if not changed and not enriched:
            stats['unchanged_queries'] += 1
            continue
        # Queries outside the replay window do not own any World records.
        if not current and not old:
            continue
        added = len(new_ids - old_ids)
        removed = sum(world.identity(f) not in new_ids and not (set(f.get('provenance', {}).get('source_ids', [])) & protected) for f in old)
        stats['added_identities'] += added
        stats['replaced_or_removed_identities'] += removed
        stats['queries_owned'] += 1
        stats['new_capture_queries_owned' if latest['path'].startswith(relative(CAPTURES) + '/') else 'cached_queries_owned'] += 1
        queries.append(dict(date=key[0], origin=key[1], destination=key[2], status=newest['status'],
                            captured_at=newest['captured_at'], url=newest['url'], source_path=latest['path'],
                            sha256=latest['sha256'], source_documents=sources))
        records.extend(prepared)
        decisions.append(dict(query=list(key), decision='owned', added=added, replaced_or_removed=removed,
                              flights=len(prepared), source_path=latest['path']))
    records.sort(key=lambda f: (f['departure'], f['id']))
    codes = {c for f in records for c in (f['origin'], f['destination'])}
    # Empty owning queries need endpoint identities too, even without a flight.
    codes.update(c for q in queries for c in (q['origin'], q['destination']))
    metadata = dict(profile=adapter.PROFILE, name='International expansion', start_date=DAY, end_date=DAY, timezone='UTC', scope='international',
                    source='Recovered and newly captured international Google Flights schedules',
                    source_url='https://www.google.com/travel/flights',
                    source_date=max((q['captured_at'][:10] for q in queries), default=''),
                    baseline_inputs=baseline['metadata']['inputs'], queries=queries,
                    coverage=dict(flights=len(records), routes_returned=len({(f['origin'], f['destination']) for f in records}),
                        airports_returned=len({c for f in records for c in (f['origin'], f['destination'])}),
                        queries_captured=len(queries), queries_not_returned=sum(q['status']=='no_matching_direct_flights' for q in queries)),
                    recovery=dict(stats),
                    replay_note='International passenger additions for 2 November 2026 UTC; partial coverage. Existing country views are unchanged.',
                    fare_context=dict(currency='mixed', currencies=list(world.CURRENCIES), new_capture_currency='USD',
                                      adults=1, cabin='economy', trip_type='one_way'))
    manifest = read(SOURCE) if SOURCE.exists() else None
    if manifest:
        metadata['source_manifest'] = dict(path=relative(SOURCE), sha256=digest(SOURCE.read_bytes()))
        metadata['unresolved_airports'] = manifest['unresolved_airports']
    stop = CAPTURES / 'collection-stop.json'
    if stop.exists() and include_fresh:
        metadata['collection_stop'] = read(stop)
    result = dict(airports=[airports.known[c] for c in sorted(codes)], flights=records, metadata=metadata)
    output = Path(output or adapter.reference_path())
    save(output, result)
    save(cache / ('preparation-decisions.json.gz' if include_fresh else 'cache-only-decisions.json.gz'), decisions)
    print(json.dumps(dict(output=relative(output), flights=len(records), **stats)), flush=True)
    return result


class AttemptBudget:
    """Reserve each request durably before navigation; crashes never reset the cap."""
    def __init__(self, path, allowed, limit=1000):
        if not 0 <= limit <= 1000:
            raise ValueError('International campaign limit must be between zero and 1,000')
        self.path = Path(path)
        self.allowed = {tuple(q) for q in allowed}
        self.fingerprint = digest(world.canonical_json(sorted(self.allowed)).encode())
        self.state = read(path) if self.path.exists() else dict(queries_sha256=self.fingerprint, attempts=[])
        self.limit = limit
        self.used = {tuple(row['query']) for row in self.state['attempts']}
        if not self.used <= self.allowed:
            raise ValueError('Search manifest changed and removed attempted queries; do not reset the campaign budget')
        # Checkpoint review may replace unattempted candidates with better ones.
        # All past attempts stay charged, and must remain in the manifest.
        self.state['queries_sha256'] = self.fingerprint

    def start(self, key):
        key = tuple(key)
        if key not in self.allowed or key in self.used:
            raise RuntimeError('Query is outside the campaign or was already attempted')
        if len(self.state['attempts']) >= self.limit:
            raise RuntimeError('International campaign search limit reached')
        self.state['attempts'].append(dict(query=list(key), attempted_at=datetime.now(timezone.utc).isoformat()))
        save(self.path, self.state)
        self.used.add(key)


def collect(cache=CACHE):
    manifest = read(SOURCE)
    CAPTURES.mkdir(parents=True, exist_ok=True)
    stop = CAPTURES / 'collection-stop.json'
    with (CAPTURES / '.campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if stop.exists():
            raise RuntimeError('Collection previously stopped; successful captures are retained. Do not retry an access challenge.')
        if manifest.get('collection', {}).get('collection_stop'):
            raise RuntimeError('The saved campaign stopped on an access challenge; do not automatically retry it')
        attempts_path = CAPTURES / 'attempts.json'
        journal = merged_attempts(manifest, attempts_path)
        if journal and (not attempts_path.exists() or read(attempts_path)['attempts'] != journal):
            save(attempts_path, dict(queries_sha256='', attempts=journal))
        budget = AttemptBudget(attempts_path, manifest['new_searches'], manifest['search_limit'])
        zones = {a['code']: a.get('replay_timezone', a['timezone']) for a in manifest['airports']}
        known = {tuple(row['query']) for row in read(cache / 'cache-index.json.gz')['queries']}
        pending = [tuple(q) for q in manifest['new_searches'] if tuple(q) not in budget.used and tuple(q) not in known]
        cfg = dict(country='WORLD', scope='international', timezone='UTC', end_date=DAY, max_duration=86400,
                   capture_prices=True, currency='USD', zones=zones, reject_invalid_segments=True,
                   capture_context=dict(parser='world-international-v1', max_duration=86400, currency='USD',
                                        adults=1, cabin='economy', trip_type='one_way', airline_filter='none'),
                   on_query_start=budget.start)
        for start in range(0, len(pending), 250):
            batch = pending[start:start+min(250, budget.limit-len(budget.state['attempts']))]
            if not batch:
                break
            print(json.dumps(dict(batch_queries=len(batch), attempted=len(budget.state['attempts']), cap=budget.limit)), flush=True)
            stopped = None
            try:
                asyncio.run(capture(CAPTURES, DAY, sorted({q[1:] for q in batch}), 2, {**cfg, 'queries': batch}))
            except RuntimeError as error:
                stopped = error
                save(stop, dict(reason=str(error), at=datetime.now(timezone.utc).isoformat()))
            # Preserve every successful result, even when a challenge interrupted
            # the batch. Subsequent offline preparation does not visit Google.
            audit(cache)
            prepare(cache)
            report(cache, rebuild=True, stage=f"after-{len(budget.state['attempts'])}-attempts")
            if stopped:
                print(str(stopped), file=sys.stderr)
                return 2
    return 0


def metrics(reference):
    flights = reference['flights']
    international = [f for f in flights if f['flight_scope'] == 'international']
    return dict(flights=len(flights), international_overlapping=len(international),
                international_departures=sum(world.START <= f['departure'] < world.END for f in international),
                international_routes=len({(f['origin'], f['destination']) for f in international}),
                international_airports=len({c for f in international for c in (f['origin'], f['destination'])}),
                international_priced=sum(bool(f.get('price')) for f in international))


def report(cache=CACHE, rebuild=False, stage='final'):
    baseline = read(cache / 'baseline.json.gz')
    candidate = cache / f'world-{stage}.json.gz'
    if rebuild:
        world.prepare(candidate)
    current = read(candidate) if candidate.exists() else world.load_reference(DAY)
    attempts_path = CAPTURES / 'attempts.json'
    attempts = read(attempts_path)['attempts'] if attempts_path.exists() else []
    captures = []
    failed = []
    missing = []
    for row in attempts:
        key = row['query']
        path = CAPTURES / ('-'.join(key) + '.json')
        if path.exists():
            captures.append(read(path))
        elif path.with_suffix('.error.json').exists():
            failed.append(dict(query=key, error=read(path.with_suffix('.error.json'))))
        else:
            missing.append(key)
    before, after = metrics(baseline), metrics(current)
    manifest = read(SOURCE) if SOURCE.exists() else {}
    result = dict(stage=stage, before=before, after=after,
                  delta={k: after[k]-before[k] for k in before}, searches_attempted=len(attempts),
                  successful_captures=len(captures), empty_results=sum(not q['flights'] for q in captures),
                  failed_queries=failed, interrupted_queries=missing,
                  priced_new_records=sum(bool(f.get('price')) for q in captures for f in q['flights']),
                  remaining_queue=len(manifest.get('remaining_queue', [])),
                  workstreams=manifest.get('workstreams', {}))
    def countries(reference):
        airports = {a['code']: a for a in reference['airports']}
        return {airports[c]['country'] for f in reference['flights'] for c in (f['origin'], f['destination'])}
    result['new_country_endpoints'] = sorted(countries(current)-countries(baseline))
    result['rejected_queries'] = [dict(query=[q['date'], q['origin'], q['destination']],
                                     rejected=q.get('rejected_flights', [])) for q in captures
                                  if q['status']=='rejected_source_records' or q.get('rejected_flights')]
    save(cache / f'scorecard-{stage}.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'failed_queries','interrupted_queries','workstreams'}}), flush=True)
    return result


def finalize(cache=CACHE):
    """Publish the reviewed ledger and derived World without another collection."""
    manifest = read(SOURCE)
    prepare(cache)
    # Obtain the complete validated union once. Only the supplemental input hash
    # changes when the final audit summary is attached below; no records change.
    result = world.prepare(cache/'world-final.json.gz')
    final = report(cache, stage='final')
    final['after'] = metrics(result)
    final['delta'] = {k: final['after'][k]-final['before'][k] for k in final['before']}
    attempts_path = CAPTURES/'attempts.json'
    attempts = read(attempts_path)['attempts'] if attempts_path.exists() else []
    if len(attempts) > 1000:
        raise ValueError('Campaign exceeded its hard search limit')
    before = read(cache/'baseline.json.gz')
    before_ids = {world.identity(f) for f in before['flights']}
    after_ids = {world.identity(f) for f in result['flights']}
    final.update(identities_added=len(after_ids-before_ids), identities_removed=len(before_ids-after_ids))
    def endpoint_countries(reference):
        airports = {a['code']:a for a in reference['airports']}
        return {airports[c]['country'] for f in reference['flights'] for c in (f['origin'],f['destination'])}
    final['new_country_endpoints'] = sorted(endpoint_countries(result)-endpoint_countries(before))
    free_path = cache/'cache-only-supplement.json.gz'
    prepare(cache, free_path, include_fresh=False)
    previous = os.environ.get('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE')
    os.environ['SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE'] = str(free_path)
    try:
        free = world.prepare(cache/'world-cache-only-final.json.gz')
    finally:
        if previous is None:
            os.environ.pop('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE', None)
        else:
            os.environ['SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE'] = previous
    final['cache_only'] = metrics(free)
    final['new_collection_net'] = {k: final['after'][k]-final['cache_only'][k] for k in final['after']}
    ledger = {tuple(row['query']):row for row in manifest['ledger']}
    supplement = adapter.load_reference()
    recovered = {tuple(q[k] for k in ('date','origin','destination')) for q in supplement['metadata']['queries']}
    for key,row in ledger.items():
        if row['state']=='cached_but_excluded' and key in recovered:
            row['state']='recovered_from_cache'
    for attempt in attempts:
        key = tuple(attempt['query'])
        row = ledger.setdefault(key,dict(query=list(key)))
        row['attempted_at'] = attempt['attempted_at']
        path = CAPTURES/('-'.join(key)+'.json')
        if path.exists():
            q = read(path)
            row.update(state='rejected_query' if q.get('rejected_flights') or q['status']=='rejected_source_records'
                       else 'captured' if q['flights'] else 'empty_result',
                       captured_at=q['captured_at'], source_path=relative(path), sha256=digest(path.read_bytes()),
                       returned_records=len(q['flights']), url=q['url'])
        elif path.with_suffix('.error.json').exists():
            row.update(state='failed_query', error=read(path.with_suffix('.error.json')))
        else:
            row['state']='interrupted_query'
    manifest['ledger']=[ledger[k] for k in sorted(ledger)]
    manifest['collection']={**final,'attempts':attempts}
    if (CAPTURES/'collection-stop.json').exists():
        manifest['collection']['collection_stop']=read(CAPTURES/'collection-stop.json')
    save(SOURCE,manifest)
    supplement['metadata']['source_manifest']=dict(path=relative(SOURCE),sha256=digest(SOURCE.read_bytes()))
    save(adapter.reference_path(),supplement)
    result['metadata']['inputs'][relative(adapter.reference_path())]=dict(
        sha256=digest(adapter.reference_path().read_bytes()),bytes=adapter.reference_path().stat().st_size)
    save(world.reference_path(),result)
    save(cache/'scorecard-final.json',final)
    print(json.dumps(final),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['recover', 'collect', 'prepare', 'report', 'finalize'])
    parser.add_argument('--cache', type=Path, default=CACHE)
    args = parser.parse_args()
    if args.action == 'recover':
        prepare(args.cache, include_fresh=False)
        report(args.cache, rebuild=True, stage='cache-only')
    elif args.action == 'prepare':
        prepare(args.cache)
    elif args.action == 'report':
        report(args.cache, rebuild=True)
    elif args.action == 'finalize':
        finalize(args.cache)
    else:
        return collect(args.cache)
    return 0


if __name__ == '__main__':
    sys.exit(main())
