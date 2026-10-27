"""Collect Canada/Mexico sequentially, sharing cached exact queries and new USD fares."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flights import main
from dashboard.canada_mexico_flights import COUNTRIES

def run():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--country',choices=['CA','MX','both'],default='both')
    args,remaining=parser.parse_known_args();sys.argv=[sys.argv[0],*remaining]
    for code in (COUNTRIES if args.country=='both' else [args.country]):
        p=COUNTRIES[code];result=main(code,ROOT/f".cache/google-flights-{p['slug']}-usd-v1",p['slug'])
        if result:return result
    return 0
if __name__=='__main__':sys.exit(run())
