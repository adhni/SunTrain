"""Sourced domestic/cross-border directions and frozen November Canadian offsets."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.sourced_flight_routes import build as build_country,DAY
from dashboard.canada_mexico_flights import COUNTRIES

def timezone_overrides():
    zones={'HMB':'Africa/Cairo','KSQ':'Asia/Samarkand','NMA':'Asia/Tashkent','YHS':'America/Vancouver','YTP':'America/Vancouver','ZEL':'America/Vancouver','YSK':'America/Iqaluit'}
    regions={'MX-BCN':'America/Tijuana','MX-BCS':'America/Mazatlan','MX-SON':'America/Hermosillo','MX-SIN':'America/Mazatlan','MX-NAY':'America/Mazatlan','MX-ROO':'America/Cancun','MX-CHH':'America/Chihuahua'}
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        for a in csv.DictReader(stream):
            if a['iata_code'] and a['type']!='closed' and a['iso_country']=='MX':zones[a['iata_code']]=regions.get(a['iso_region'],'America/Mexico_City')
    zones.update(CJS='America/Ciudad_Juarez',NOG='America/Hermosillo',MAM='America/Matamoros',NLD='America/Matamoros',REX='America/Matamoros',PVR='America/Mexico_City')
    return zones

def freeze_canadian_clocks(m):
    with (ROOT/'.cache/australia-flights-audit/ourairports-airports.csv').open(encoding='utf-8-sig') as stream:
        regions={a['iata_code']:a['iso_region'] for a in csv.DictReader(stream) if a['iata_code'] and a['type']!='closed'}
    for a in m['airports']:
        if a['country']!='CA':continue
        if regions.get(a['code']) in {'CA-AB','CA-NT','CA-SK'} or (regions.get(a['code'])=='CA-BC' and a['timezone']=='America/Edmonton'):a['replay_timezone']='Etc/GMT+6'
        elif regions.get(a['code'])=='CA-BC' and a['timezone']=='America/Vancouver':a['replay_timezone']='Etc/GMT+7'
    return m

def build(code):
    p=COUNTRIES[code];slug=p['slug'];name=p['name']
    note=f'{name} · Flights departing 2 November 2026 in each origin airport’s local time, including overnight arrivals. Timeline: UTC; airport boards use local time. New quotes use USD; reused quotes retain their original currencies. Coverage and prices are partial. Empty results mean not returned, not no service. Paths are illustrative.'
    m=build_country(slug,code,'UTC',ROOT/f'.cache/google-flights-{slug}-usd-v1',
        f'Published domestic and Canada/US/Mexico routes from 15 reviewed {name} gateways, both directions, plus compatible existing worldwide captures. Regional domestic destinations can extend beyond the gateways. Not an exact top-15 ranking or complete country/airline coverage.',
        note,'Outside the reviewed national gateway footprint',timezone_overrides(),national_countries=[code],include_previous_candidates=False)
    freeze_canadian_clocks(m)
    m.update(collection_strategy='Published domestic and Canada/US/Mexico directions, one origin-local date; intact reused worldwide captures, new USD quotes; no Cartesian airport expansion',
        new_collection_countries=['CA','MX','US'],canadian_clock_sources=['https://archive.news.gov.bc.ca/releases/news_releases_2024-2028/2026AG0013-000209.htm','https://www.alberta.ca/albertas-new-time-system-abt','https://www.gov.nt.ca/en/newsroom/northwest-territories-ends-seasonal-time-change','https://www.saskatchewan.ca/Government/Municipal-Administration/Tools-Guides-and-Resources/Saskatchewan-Time-System'],
        mexico_clock_source='https://www.gob.mx/sener/articulos/en-la-republica-mexicana-ya-no-hay-horario-de-verano?idiom=es')
    return m

if __name__=='__main__':
    for code,p in COUNTRIES.items():
        m=build(code);(ROOT/f"data/sources/{p['slug']}_flights_routes.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(country=code,airports=len(m['airports']),directions=len(m['routes']),reuse=len(m['reuse_sources']),gaps=len(m['source_gaps']),unresolved=m['unresolved_airports'])),flush=True)
