"""Reuse and collect dated Pacific schedules and USD fares on one local departure date."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flights import main,prepare_cached,seed,collection_routes,validate_query
from scripts.prepare_pacific_routes import CACHE,DAY
if __name__=='__main__':sys.exit(main('PACIFIC',CACHE,'pacific'))
