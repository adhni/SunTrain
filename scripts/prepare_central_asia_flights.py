"""Resume one-date Central Asian schedules; new USD fares, unchanged reused quotes."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flights import main,prepare_cached,seed,collection_routes,validate_query
from scripts.prepare_central_asia_routes import CACHE,DAY
if __name__=='__main__':sys.exit(main('CENTRAL_ASIA',CACHE,'central_asia'))
