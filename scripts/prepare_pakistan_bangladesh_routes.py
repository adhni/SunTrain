"""Prepare published domestic and worldwide route candidates; no Cartesian expansion."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.pakistan_bangladesh_flights import COUNTRIES
from scripts.prepare_arabia_jordan_routes import build as build_country

def build(code):return build_country(code,COUNTRIES)

if __name__=='__main__':
    for code,p in COUNTRIES.items():
        m=build(code);(ROOT/f"data/sources/{p['slug']}_flights_routes.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(country=code,airports=len(m['airports']),directions=len(m['routes']),reuse=len(m['reuse_sources']),archive_routes=m['archive_reuse_routes'],gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])),flush=True)
