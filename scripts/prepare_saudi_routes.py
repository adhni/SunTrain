"""Build Saudi domestic candidates and four-hub worldwide connections, without all-pairs expansion."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flight_routes import build as build_country,DAY
CACHE=ROOT/'.cache/google-flights-saudi-usd-v1'
NOTE="Saudi Arabia · Flights departing 2 November 2026 in each origin airport’s local time, including overnight arrivals. Timeline: Saudi time (UTC+3); airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative."

def build():
    m=build_country('saudi','SA','Asia/Riyadh',CACHE,
        'Published domestic routes from 28 Saudi civilian airport candidates; worldwide sourced routes from RUH, JED, DMM and MED, both directions; other existing Saudi captures reused without new searches. Not all routes or airlines; seasonal candidates are not dated evidence.',
        NOTE,'Outside the RUH/JED/DMM/MED worldwide international footprint',
        {'HMB':'Africa/Cairo','KSQ':'Asia/Samarkand','NMA':'Asia/Tashkent'})
    m['collection_strategy']='Published Saudi domestic routes and four-hub worldwide connections, one origin-local date; reused quotes unchanged, new captures USD'
    return m

if __name__=='__main__':
    m=build();(ROOT/'data/sources/saudi_flights_routes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(m['airports']),directions=len(m['routes']),reusable_directions=len(m['reuse_sources']),source_gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])))
