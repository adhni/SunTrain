"""Resume Türkiye flights with the existing CLI defaults and shared country collector."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flights import main as run,prepare_cached,collection_routes,seed,budget,validate_query
from scripts.prepare_turkiye_routes import CACHE,DAY

def main():return run('TR',CACHE,'turkiye')

if __name__=='__main__':sys.exit(main())
