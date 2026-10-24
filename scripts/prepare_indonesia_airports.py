"""Prepare the Indonesian airport/route search manifest from official references.

Preparation only; requires pypdf. Downloads are cached for inspection and reuse.
"""
import csv
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_HASH, AIRPORT_URL, pinned_download

PDF_URL = 'https://hubud.kemenhub.go.id/hubud/website/assets/file/bukustatistik/9a4eaeb68ab0e5bb3be1a8b5202ccb90.pdf'
PDF_HASH = '34f2109ee7926c3923fe9abf405bd46941a0d9be528508a5306bf1b29f31a017'
HUBS = 'CGK HLP SUB DPS KNO UPG BPN YIA BTH KOE MDC AMQ SOQ DJJ'.split()
CACHE = ROOT / '.cache/indonesia-flights-audit'
OUTPUT = ROOT / 'data/sources/indonesia_flights_routes.json'


def plain(value):
    return re.sub(r'\s+', ' ', unescape(re.sub('<[^>]+>', ' ', value))).strip()


def airport_zone(region):
    suffix = region.removeprefix('ID-')
    if suffix in {'MA', 'MU', 'PA', 'PB', 'PD', 'PE', 'PP', 'PS', 'PT'}:
        return 'Asia/Jayapura', 'Papua' if suffix not in {'MA', 'MU'} else 'Maluku'
    if suffix in {'BA', 'NB', 'NT'}:
        return 'Asia/Makassar', 'Bali & Nusa Tenggara'
    if suffix in {'SA', 'ST', 'SG', 'SR', 'SN', 'GO'}:
        return 'Asia/Makassar', 'Sulawesi'
    if suffix in {'KS', 'KI', 'KU'}:
        return 'Asia/Makassar', 'Kalimantan'
    if suffix in {'KB', 'KT'}:
        return 'Asia/Pontianak', 'Kalimantan'
    if suffix in {'JK', 'BT', 'JB', 'JT', 'JI', 'YO'}:
        return 'Asia/Jakarta', 'Java'
    if suffix in {'AC', 'SU', 'SB', 'RI', 'KR', 'JA', 'BE', 'SS', 'BB', 'LA'}:
        return 'Asia/Jakarta', 'Sumatra'
    raise ValueError(f'Unknown Indonesian region: {region}')


def cached(url, filename):
    path = CACHE / filename
    if not path.exists():
        with urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    return path


def prepare():
    from pypdf import PdfReader
    CACHE.mkdir(parents=True, exist_ok=True)
    airport_file = pinned_download(AIRPORT_URL, ROOT / '.cache/australia-flights-audit/ourairports-airports.csv', AIRPORT_HASH)
    with airport_file.open(encoding='utf-8-sig') as stream:
        rows = [a for a in csv.DictReader(stream) if a['iso_country'] == 'ID' and a['iata_code'] and a['type'] != 'closed']
    by_code = {}
    for a in rows:
        zone, group = airport_zone(a['iso_region'])
        record = dict(code=a['iata_code'], icao=a['ident'], name=f"{a['name']} ({a['iata_code']})",
            municipality=a['municipality'], timezone=zone, island_group=group, mode='flight',
            lat=float(a['latitude_deg']), lon=float(a['longitude_deg']), scheduled=a['scheduled_service'] == 'yes')
        if record['code'] in by_code:
            raise ValueError(f"Ambiguous airport {record['code']}")
        by_code[record['code']] = record
    pdf = pinned_download(PDF_URL, CACHE / 'kemenhub-2023.pdf', PDF_HASH)
    pairs, evidence, unresolved = set(), [], []
    for index, page in enumerate(PdfReader(pdf).pages):
        text = page.extract_text()
        if 'RUTE ANGKUTAN UDARA NIAGA BERJADWAL DALAM NEGERI' not in text:
            continue
        for line in text.splitlines():
            codes = re.findall(r'\(([A-Z]{3})\)', line)
            if len(codes) not in (2, 4):
                continue
            for a, b in zip(codes[::2], codes[1::2]):
                evidence.append(dict(origin=a, destination=b, source=PDF_URL, page=index+1))
                if a not in by_code or b not in by_code:
                    unresolved.append(dict(origin=a, destination=b, reason='Airport code not in pinned catalogue', source=PDF_URL))
                elif a != b:
                    pairs.update([(a, b), (b, a)])
    directory_file = cached('https://hubud.kemenhub.go.id/api/bandara-map', 'directory.json')
    directory = json.loads(directory_file.read_text())['data']
    # Match official names exactly after removing generic airport words; no city-wide aliases.
    def normal(name):
        return re.sub(r'[^a-z0-9]', '', re.sub(r'\b(international|airport|bandar|udara|internasional)\b', '', name.lower()))
    names = {}
    for a in rows:
        names.setdefault(normal(a['name']), set()).add(a['iata_code'])
    for item in directory:
        code = item.get('IATA')
        name = item.get('NamaBandara')
        if code in by_code and name:
            names.setdefault(normal(name), set()).add(code)
    for item in directory:
        code = item.get('IATA')
        if code not in HUBS:
            continue
        url = item.get('url') or f"https://hubud.kemenhub.go.id/bandara/{item['BandaraID']}"
        path = cached(url, f'bandara-{code}.html')
        html = path.read_text()
        section = html.split('Daftar Rute Domestik', 1)
        if len(section) != 2:
            continue
        section = section[1].split('</ul>', 1)[0]
        for entry in re.findall(r'<li\b[^>]*>(.*?)</li>', section, re.S):
            text = plain(entry)
            # Destination is the span directly after the Tujuan label, excluding carrier.
            destination = re.search(r'>\s*Tujuan\s*</span>\s*<span[^>]*>(.*?)</span>', entry, re.S)
            if not destination:
                continue
            name = plain(destination[1])
            matches = names.get(normal(name), set())
            evidence.append(dict(origin=code, destination_name=name, source=url, frequency_only=True, detail=text))
            if len(matches) == 1:
                target = next(iter(matches))
                if target != code:
                    pairs.update([(code, target), (target, code)])
            else:
                unresolved.append(dict(origin=code, destination_name=name, reason='Unresolved exact airport identity', source=url))
    pairs.update((a, b) for a in HUBS for b in HUBS if a != b)
    used = {c for pair in pairs for c in pair}
    airports = [a for c, a in sorted(by_code.items()) if a['scheduled'] or c in used]
    result = dict(country='ID', start_date='2026-11-02', end_date='2026-11-08', timezone='Asia/Jakarta',
        airport_source_url=AIRPORT_URL, airport_source_sha256=AIRPORT_HASH,
        route_source_url=PDF_URL, route_source_sha256=PDF_HASH, historical_route_year=2023,
        directory_url='https://hubud.kemenhub.go.id/daftar-bandara',
        directory_sha256=hashlib.sha256(directory_file.read_bytes()).hexdigest(),
        airports=airports, routes=sorted(pairs), evidence=evidence, unresolved_airports=unresolved)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(airports=len(airports), routes=len(pairs), unresolved=len(unresolved))))


if __name__ == '__main__':
    prepare()
