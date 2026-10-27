"""Published country routes for Oman, Kuwait, Bahrain and Jordan; no Cartesian searches."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dashboard.arabia_jordan_flights import COUNTRIES
from scripts.sourced_flight_routes import build as build_country,DAY


def build(code):
    p=COUNTRIES[code];slug=p['slug'];name=p['name']
    cache=ROOT/f'.cache/google-flights-{slug}-usd-v1'
    note=f"{name} · Flights departing 2 November 2026 in each origin airport’s local time, including overnight arrivals. Timeline: {p['clock']}; airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative."
    m=build_country(slug,code,p['zone'],cache,
        f'Published domestic and worldwide international routes from the selected {name} civilian airports, both directions; other existing national captures reused without new searches. Seasonal candidates are not dated service evidence; coverage is partial.',
        note,'Outside the sourced national airport footprint',
        {'HMB':'Africa/Cairo','KSQ':'Asia/Samarkand','NMA':'Asia/Tashkent'})
    m['collection_strategy']=f'Published {name} airport routes, one origin-local date; reused quotes unchanged, new captures USD'
    return m

if __name__=='__main__':
    for code,p in COUNTRIES.items():
        m=build(code);(ROOT/f"data/sources/{p['slug']}_flights_routes.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(country=code,airports=len(m['airports']),directions=len(m['routes']),reuse=len(m['reuse_sources']),archive_routes=m['archive_reuse_routes'],gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])),flush=True)
