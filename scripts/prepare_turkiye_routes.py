"""Build exact-airport Türkiye candidates from frozen published route maps."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flight_routes import build as build_country,DAY
CACHE=ROOT/'.cache/google-flights-turkiye-usd-v1'

def build():
    return build_country('turkiye','TR','Europe/Istanbul',CACHE,
        'IST and SAW worldwide sourced connections; published domestic candidates from IST, SAW, ESB, ADB and AYT to Turkish regional airports; additional existing Turkish captures reused without new searches. Not all Turkish airports or routes; seasonal candidates are not dated evidence.',
        'Türkiye · Flights departing 2 November 2026 in each origin airport’s local time, including overnight arrivals. Timeline: Türkiye time (UTC+3); airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.',
        'Outside the two-hub worldwide international footprint')

if __name__=='__main__':
    m=build();(ROOT/'data/sources/turkiye_flights_routes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(m['airports']),directions=len(m['routes']),reusable_directions=len(m['reuse_sources']),source_gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])))
