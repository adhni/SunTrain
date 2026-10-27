"""Resume Saudi domestic and worldwide hub routes on one date; new USD fares, intact reused quotes."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flights import main,prepare_cached,collection_routes,seed,validate_query
from scripts.prepare_saudi_routes import CACHE,DAY

if __name__=='__main__':sys.exit(main('SA',CACHE,'saudi'))
