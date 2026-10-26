"""Pin the FAA's thirty busiest airports and probe every exact directional pair."""
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL, AIRPORT_HASH, pinned_download

FAA_URL = 'https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/arp-cy2025-commercial-service-enplanements.xlsx'
FAA_HASH = '91c8d4457e9558b8bcb65c2a27cd9b95062e3c7b443e58e9714ba77942777b40'
ZONES = {
    **dict.fromkeys('ATL JFK MCO MIA CLT EWR BOS LGA FLL PHL IAD BWI TPA DCA'.split(), 'America/New_York'),
    **dict.fromkeys('DFW ORD IAH MSP BNA AUS'.split(), 'America/Chicago'),
    **dict.fromkeys('DEN SLC'.split(), 'America/Denver'),
    'PHX': 'America/Phoenix', 'DTW': 'America/Detroit', 'HNL': 'Pacific/Honolulu',
    **dict.fromkeys('LAX LAS SFO SEA SAN'.split(), 'America/Los_Angeles'),
}


def ranking(path):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        strings = [''.join(t.itertext()) for t in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', ns)]
        ranked = []
        for row in ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//m:row', ns):
            values = {}
            for cell in row.findall('m:c', ns):
                value = cell.find('m:v', ns)
                if value is not None:
                    values[''.join(c for c in cell.attrib['r'] if c.isalpha())] = strings[int(value.text)] if cell.attrib.get('t') == 's' else value.text
            if values.get('A', '').isdigit() and 1 <= int(values['A']) <= 30:
                ranked.append(dict(rank=int(values['A']), code=values['D'], enplanements_2025=int(values['I'])))
    ranked.sort(key=lambda a: a['rank'])
    if [a['rank'] for a in ranked] != list(range(1, 31)) or {a['code'] for a in ranked} != set(ZONES):
        raise ValueError('Pinned FAA top-thirty ranking differs from the reviewed airports')
    return ranked


def prepare():
    cache = ROOT / '.cache/us-flights-audit'
    cache.mkdir(parents=True, exist_ok=True)
    source = pinned_download(FAA_URL, cache / 'faa-cy2025.xlsx', FAA_HASH)
    ranked = ranking(source)
    raw = pinned_download(AIRPORT_URL, ROOT / '.cache/australia-flights-audit/ourairports-airports.csv', AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    airports = []
    for item in ranked:
        code = item['code']
        matches = [a for a in rows if a['iata_code'] == code and a['iso_country'] == 'US' and a['type'] != 'closed']
        if len(matches) != 1:
            raise ValueError(f'Unresolved exact airport: {code}')
        a = matches[0]
        airports.append(dict(code=code, icao=a.get('icao_code') or a['ident'], name=f"{a['name']} ({code})",
            municipality=a['municipality'], country='US', timezone=ZONES[code], mode='flight',
            lat=float(a['latitude_deg']), lon=float(a['longitude_deg']), **{k:v for k,v in item.items() if k != 'code'}))
    manifest = dict(country='US', scope='domestic', start_date='2026-11-02', end_date='2026-11-02',
        timezone='America/New_York', currency='USD', max_duration=57600,
        coverage_scope='Nonstop flights between the FAA CY2025 top thirty airports by total passenger boardings; all returned airlines. Other US airports excluded.',
        query_date_policy='origin_local_departure_day_only',
        replay_note='US domestic flights between thirty selected airports. Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. Timeline: Eastern time (EST, UTC−5); airport boards use local time. Captured USD fares and coverage are partial. Empty results mean not returned, not no service. Paths are illustrative.',
        airport_source_url=AIRPORT_URL, airport_source_sha256=AIRPORT_HASH,
        route_source_url=FAA_URL, route_source_sha256=FAA_HASH,
        route_basis='All 870 directional pairs among the top thirty; candidates, not evidence of service. Ranking includes domestic and international passenger boardings.',
        airports=airports, routes=sorted((a,b) for a in ZONES for b in ZONES if a != b), unresolved_airports=[])
    output = ROOT / 'data/sources/united_states_flights_routes.json'
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(airports=len(airports), directional_routes=len(manifest['routes']))))


if __name__ == '__main__':
    prepare()
