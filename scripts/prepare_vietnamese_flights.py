"""Vietnamese domestic USD captures; international uses the shared network."""
import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_google_flights import capture, country_config, prepare

DAY = '2026-11-02'
PROBES = [('HAN','SGN'),('SGN','DAD'),('HAN','DIN'),('SGN','VCS'),('DAD','DLI')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/google-flights-vietnam')
    parser.add_argument('--output', type=Path, default=ROOT / f'data/reference/vietnam_flights/{DAY}.json.gz')
    parser.add_argument('--concurrency', type=int, choices=[1, 2], default=2)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    config = country_config('VN')
    manifest_pairs = config['manifest']['routes']
    pairs = PROBES if args.validate_only else PROBES + [tuple(p) for p in manifest_pairs if tuple(p) not in PROBES]
    stopped = None
    if not args.prepare_only:
        try:
            asyncio.run(capture(args.cache, DAY, pairs, args.concurrency, config))
        except RuntimeError as error:
            stopped = error
    # A probe must never publish a snapshot that implies the full manifest ran.
    if not args.validate_only:
        prepare(args.cache, args.output, DAY, manifest_pairs, config)
    if stopped:
        print(f'{stopped}; successful captures retained; collection not retried', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
