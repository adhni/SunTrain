"""Sourced regional routes with current exact airport identities and national clocks."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flight_routes import build as build_region,DAY
CACHE=ROOT/'.cache/google-flights-central-asia-usd-v1'
MEMBERS='KZ UZ KG TJ TM'.split()
NOTE='Central Asia · Flights departing 2 November 2026 in each origin airport’s local time, including overnight arrivals. Timeline: UTC; airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.'

def timezone_overrides():
    zones={'HMB':'Africa/Cairo'}
    west={'SCO':'Asia/Aqtau','GUW':'Asia/Atyrau','AKX':'Asia/Aqtobe','URA':'Asia/Oral','KZO':'Asia/Qyzylorda','KSN':'Asia/Qostanay'}
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        for a in csv.DictReader(stream):
            code=a['iata_code'];country=a['iso_country']
            if not code or a['type']=='closed':continue
            if country=='KZ':zones[code]=west.get(code,'Asia/Almaty')
            elif country=='UZ':zones[code]='Asia/Samarkand' if a['iso_region'] in {'UZ-XO','UZ-QR','UZ-NW','UZ-BU','UZ-SA','UZ-QA','UZ-SU'} else 'Asia/Tashkent'
            elif country in {'KG','TJ','TM'}:zones[code]={'KG':'Asia/Bishkek','TJ':'Asia/Dushanbe','TM':'Asia/Ashgabat'}[country]
    return zones

def build():
    m=build_region('central_asia','CENTRAL_ASIA','UTC',CACHE,
        'Published domestic, intra-regional and worldwide international routes from selected civilian airports in Kazakhstan, Uzbekistan, Kyrgyzstan, Tajikistan and Turkmenistan. Historical candidates are not current service evidence. Not complete country or airline coverage.',
        NOTE,'Outside the reviewed Central Asian airport footprint',timezone_overrides(),national_countries=MEMBERS,include_previous_candidates=False)
    m.update(regional_countries=MEMBERS,regional_extra_airports=[],
        timezone_rule_source_url='https://data.iana.org/time-zones/tzdb/asia',
        collection_strategy='Sourced Central Asian airport directions, one origin-local date; reuse original captures and currencies, new USD quotes; no Cartesian airport expansion')
    return m

if __name__=='__main__':
    m=build();(ROOT/'data/sources/central_asia_flights_routes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(m['airports']),directions=len(m['routes']),reuse=len(m['reuse_sources']),gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])))
