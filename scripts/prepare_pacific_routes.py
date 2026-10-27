"""Build sourced Pacific island routes with exact airport membership and local time zones."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flight_routes import build as build_region,DAY
CACHE=ROOT/'.cache/google-flights-pacific-usd-v1'
MEMBERS='FJ PG SB VU NC WS AS TO CK PF NU TV NR KI MH FM PW GU MP NF WF'.split()
EXTRA='HNL OGG KOA LIH ITO MKK LNY HNM JHM CHT IPC'.split()
NOTE="Pacific Islands · Flights departing 2 November 2026 in each origin airport’s local time, including overnight and date-line arrivals. Timeline: UTC; airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative."

def timezone_overrides():
    overrides={'HMB':'Africa/Cairo','KSQ':'Asia/Samarkand','NMA':'Asia/Tashkent'}
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            code=row['iata_code'];country=row['iso_country']
            if not code or row['type']=='closed':continue
            if country=='PG':overrides[code]='Pacific/Bougainville' if row['iso_region']=='PG-NSB' else 'Pacific/Port_Moresby'
            elif country=='SB':overrides[code]='Pacific/Guadalcanal'
            elif country=='PF':overrides[code]='Pacific/Marquesas' if code in {'AUQ','NHV','UAH','UAP'} else 'Pacific/Gambier' if code=='GMR' else 'Pacific/Tahiti'
            elif country=='KI':overrides[code]='Pacific/Kiritimati' if code in {'CXI','TNV','TNQ'} else 'Pacific/Kanton' if code=='CIS' else 'Pacific/Tarawa'
            elif country=='US' and row['iso_region']=='US-HI':overrides[code]='Pacific/Honolulu'
    return overrides

def build():
    m=build_region('pacific','PACIFIC','UTC',CACHE,
        'Published routes from selected Pacific island gateways and regional airports, including Hawaii, Chatham Islands and Easter Island; international connections and compatible existing regional captures. Mainland US/Chile, Australia and New Zealand airports are connecting destinations, not additional regional collection hubs. Not complete island or airline coverage.',
        NOTE,'Outside the selected Pacific gateway footprint',
        timezone_overrides(),national_countries=MEMBERS,national_airports=EXTRA,include_previous_candidates=False)
    m.update(regional_countries=MEMBERS,regional_extra_airports=EXTRA,timezone_rule_source_url='https://data.iana.org/time-zones/tzdb/australasia',
        collection_strategy='Sourced Pacific island routes and worldwide connections, one origin-local date; reused quotes unchanged, new USD captures; no Cartesian airport expansion')
    return m

if __name__=='__main__':
    m=build();(ROOT/'data/sources/pacific_flights_routes.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(airports=len(m['airports']),directions=len(m['routes']),reuse=len(m['reuse_sources']),archive_routes=m['archive_reuse_routes'],source_gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])))
