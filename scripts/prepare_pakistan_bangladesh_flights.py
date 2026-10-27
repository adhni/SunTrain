"""Reuse captures and collect one-date Pakistan/Bangladesh schedules and USD offers."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.pakistan_bangladesh_flights import COUNTRIES
from scripts.prepare_arabia_jordan_flights import main
if __name__=='__main__':sys.exit(main(COUNTRIES))
