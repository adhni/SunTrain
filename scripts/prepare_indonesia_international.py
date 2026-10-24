"""Build exact-airport international candidates touching Indonesia; preparation only."""
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_HASH, AIRPORT_URL, pinned_download
from scripts.prepare_indonesia_airports import PDF_URL, PDF_HASH

# Explicit airport-local IANA zones, including separate city airports and DST.
COUNTRY_ZONES = {
    'SG': 'Asia/Singapore', 'MY': 'Asia/Kuala_Lumpur', 'TH': 'Asia/Bangkok',
    'VN': 'Asia/Ho_Chi_Minh', 'KH': 'Asia/Phnom_Penh', 'BN': 'Asia/Brunei',
    'PH': 'Asia/Manila', 'CN': 'Asia/Shanghai', 'HK': 'Asia/Hong_Kong',
    'MO': 'Asia/Macau', 'TW': 'Asia/Taipei', 'JP': 'Asia/Tokyo', 'KR': 'Asia/Seoul',
    'IN': 'Asia/Kolkata', 'LK': 'Asia/Colombo', 'AE': 'Asia/Dubai', 'QA': 'Asia/Qatar',
    'SA': 'Asia/Riyadh', 'OM': 'Asia/Muscat', 'UZ': 'Asia/Tashkent',
    'TR': 'Europe/Istanbul', 'EG': 'Africa/Cairo', 'NL': 'Europe/Amsterdam',
    'GB': 'Europe/London', 'FR': 'Europe/Paris', 'DE': 'Europe/Berlin',
    'NZ': 'Pacific/Auckland', 'TL': 'Asia/Dili', 'PG': 'Pacific/Port_Moresby',
}
AU_ZONES = {
    'MEL': 'Australia/Melbourne', 'AVV': 'Australia/Melbourne', 'SYD': 'Australia/Sydney',
    'BNE': 'Australia/Brisbane', 'OOL': 'Australia/Brisbane', 'CNS': 'Australia/Brisbane',
    'ADL': 'Australia/Adelaide', 'PER': 'Australia/Perth', 'DRW': 'Australia/Darwin',
}

AIRPORT_ZONES = {'BKI': 'Asia/Kuching', 'KCH': 'Asia/Kuching'}


def prepare():
    from pypdf import PdfReader
    domestic = json.loads((ROOT / 'data/sources/indonesia_flights_routes.json').read_text())
    known = {a['code']: {**a, 'country': 'ID'} for a in domestic['airports']}
    airport_file = pinned_download(AIRPORT_URL,
        ROOT / '.cache/australia-flights-audit/ourairports-airports.csv', AIRPORT_HASH)
    with airport_file.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    pdf = pinned_download(PDF_URL, ROOT / '.cache/indonesia-flights-audit/kemenhub-2023.pdf', PDF_HASH)
    pairs, evidence, unresolved = set(), [], []

    def airport(code):
        if code in known:
            return known[code]
        matches = [a for a in rows if a['iata_code'] == code and a['type'] != 'closed']
        if len(matches) != 1:
            raise ValueError(f'Unresolved airport {code}')
        a = matches[0]
        country = a['iso_country']
        zone = AIRPORT_ZONES.get(code) or (AU_ZONES.get(code) if country == 'AU' else COUNTRY_ZONES.get(country))
        if not zone:
            raise ValueError(f'Unresolved airport time zone {code} ({country})')
        record = dict(code=code, icao=a['ident'], name=f"{a['name']} ({code})",
            municipality=a['municipality'], country=country, timezone=zone,
            island_group='Overseas', mode='flight',
            lat=float(a['latitude_deg']), lon=float(a['longitude_deg']))
        known[code] = record
        return record

    for index, page in enumerate(PdfReader(pdf).pages):
        text = page.extract_text()
        if 'RUTE ANGKUTAN UDARA NIAGA BERJADWAL LUAR NEGERI TAHUN 2023' not in text:
            continue
        for line in text.splitlines():
            # Chengdu Tianfu is printed as bare TFU, unlike parenthesised codes.
            codes = [a or b for a, b in re.findall(r'\(([A-Z]{3})\)|\b(TFU)\b', line)]
            if len(codes) not in (2, 4):
                continue
            for a, b in zip(codes[::2], codes[1::2]):
                evidence.append(dict(origin=a, destination=b, source=PDF_URL, page=index + 1))
                try:
                    aa, bb = airport(a), airport(b)
                    if (aa['country'] == 'ID') == (bb['country'] == 'ID'):
                        unresolved.append(dict(origin=a, destination=b,
                            reason='Not a cross-border Indonesian pair'))
                        continue
                    pairs.update([(a, b), (b, a)])
                except ValueError as error:
                    unresolved.append(dict(origin=a, destination=b, reason=str(error)))

    foreign = sorted({code for pair in pairs for code in pair if known[code]['country'] != 'ID'})
    # These are search candidates, not claims of current direct service.
    for hub in ['CGK', 'DPS']:
        for code in foreign:
            pairs.update([(hub, code), (code, hub)])
    # Avalon remains independent of Melbourne even if no flights are returned.
    airport('AVV')
    pairs.update([('DPS', 'AVV'), ('AVV', 'DPS')])
    codes = sorted({code for pair in pairs for code in pair})
    output = dict(country='ID', scope='international', start_date='2026-11-02',
        end_date='2026-11-08', timezone='Asia/Jakarta', max_duration=24 * 3600,
        airport_source_url=AIRPORT_URL, airport_source_sha256=AIRPORT_HASH,
        route_source_url=PDF_URL, route_source_sha256=PDF_HASH, historical_route_year=2023,
        airports=[known[c] for c in codes], routes=sorted(pairs), evidence=evidence,
        unresolved_airports=unresolved)
    path = ROOT / 'data/sources/indonesia_international_routes.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(airports=len(codes),
        foreign_airports=sum(known[c]['country'] != 'ID' for c in codes),
        routes=len(pairs), unresolved=len(unresolved))))


if __name__ == '__main__':
    prepare()
