"""Prepare World from validated views and its optional international supplement."""
import argparse
import json
from dashboard.world_flights import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Derived .json.gz snapshot path')
    args = parser.parse_args()
    result = prepare(args.output)
    print(json.dumps({**result['metadata']['coverage'], 'scopes': result['metadata']['scopes'],
                      'source_archives_read': len(result['metadata']['inputs'])}, indent=2))


if __name__ == '__main__':
    main()
