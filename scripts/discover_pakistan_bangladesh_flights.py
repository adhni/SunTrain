"""Pin published Pakistan and Bangladesh exact-airport route candidates."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.discover_arabia_jordan_flights import main
AIRPORTS={'pakistan':'KHI ISB LHE PEW LYP MUX SKT UET GWD GIL KDU TUK SKZ BHV CJL DBA DEA RYK HDD KDD MFG WNS PZH'.split(),
          'bangladesh':'DAC CGP ZYL CXB JSR RJH SPD BZL'.split()}
if __name__=='__main__':main(AIRPORTS,ROOT/'.cache/pakistan-bangladesh-flights-audit')
