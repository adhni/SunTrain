"""Capture only sourced cross-Americas directions; reuse both existing regional archives."""
import argparse
import asyncio
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_google_flights import capture, country_config, prepare
from scripts.prepare_americas_routes import DAY, budget
from dashboard.flight_profiles import load_domestic


def prepare_combined(cache, output, cfg):
    """Reconstruct original queries offline; temporary files never alter regional caches."""
    manifest = cfg['manifest']
    with tempfile.TemporaryDirectory(prefix='suntrain-americas-prepare-') as temporary:
        staging = Path(temporary)
        for item, code in zip(manifest['input_snapshots'], ['US', 'SOUTH_AMERICA']):
            source = ROOT/item['path']
            if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Regional reference changed; rebuild the reviewed manifest')
            reference = load_domestic(source, code)
            by_query = defaultdict(list)
            for f in reference['flights']:
                record = dict(f)
                record.pop('flight_scope', None)
                by_query[(f['source_date'], f['origin'], f['destination'])].append(record)
            for q in reference['metadata']['queries']:
                key = (q['date'], q['origin'], q['destination'])
                target = staging/f'{key[0]}-{key[1]}-{key[2]}.json'
                if target.exists():
                    raise ValueError('Overlapping regional query identities')
                target.write_text(json.dumps({**q, 'flights':by_query[key]}, separators=(',', ':'))+'\n')
        for a, b in manifest['cross_region_routes']:
            for suffix in ['.json', '.error.json']:
                source = cache/f'{DAY}-{a}-{b}{suffix}'
                if source.exists():
                    (staging/source.name).symlink_to(source.resolve())
        stop = cache/'collection-stop.json'
        if stop.exists():
            (staging/stop.name).symlink_to(stop.resolve())
        prepared = staging/'combined.json.gz'
        prepare(staging, prepared, DAY, manifest['routes'], cfg)
        with gzip.open(prepared, 'rt') as stream:
            reference = json.load(stream)
    pairs = set(map(tuple, manifest['cross_region_routes']))
    queries = [q for q in reference['metadata']['queries'] if (q['origin'], q['destination']) in pairs]
    records = [f for f in reference['flights'] if (f['origin'], f['destination']) in pairs]
    failed = [q for q in reference['metadata']['failed_queries'] if (q['origin'], q['destination']) in pairs]
    reference['metadata'].update(input_snapshots=manifest['input_snapshots'],
        collection_strategy='Reuse regional archives; capture sourced cross-region pairs once per origin-local date',
        cross_region_coverage=dict(routes_planned=len(pairs), queries_captured=len(queries),
            routes_returned=len({(f['origin'], f['destination']) for f in records}),
            queries_not_returned=sum(q['status']=='no_matching_direct_flights' for q in queries),
            failed_queries=len(failed), unattempted_queries=len(pairs)-len(queries)-len(failed),
            rejected_records=sum(len(q.get('rejected_flights', [])) for q in queries),
            flights=len(records), priced_flights=sum(bool(f.get('price')) for f in records)))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    with temporary.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(reference, separators=(',', ':')).encode())
    temporary.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'.cache/google-flights-americas-usd-v1')
    parser.add_argument('--output', type=Path, default=ROOT/f'data/reference/americas_flights/{DAY}.json.gz')
    parser.add_argument('--concurrency', type=int, choices=[1,2], default=2)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    cfg = country_config('AMERICAS')
    shortlist = json.loads((ROOT/'data/sources/americas_connections_routes.json').read_text())
    if args.dry_run:
        print(json.dumps({**budget(shortlist, args.cache), 'reused_regional_directions':len(cfg['manifest']['routes'])-len(shortlist['routes'])}))
        return 0
    args.cache.mkdir(parents=True, exist_ok=True)
    if budget(shortlist, args.cache)['incompatible_captures']:
        raise ValueError('Incompatible captures; inspect the dry-run report before resuming')
    stopped = None
    if not args.prepare_only:
        try:
            asyncio.run(capture(args.cache, DAY, shortlist['routes'], args.concurrency, cfg))
        except RuntimeError as error:
            stopped = error
            (args.cache/'collection-stop.json').write_text(json.dumps(dict(reason=str(error))))
    prepare_combined(args.cache, args.output, cfg)
    if stopped:
        print(f'{stopped}; successful captures retained, no challenge retries', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
