"""Prepare the published Jetstar NW12 domestic timetable for a personal replay.

Preparation only: PYTHONPATH=.cache/flight-tools .venv/bin/python
scripts/prepare_australian_flights.py. Install pypdf in that ignored tools folder.
The app reads the prepared gzip, without pypdf or external flight API requests.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
FIRST, LAST = date(2013, 3, 4), date(2013, 3, 10)
PDF_URL = 'https://www.jetstar.com/_/media/Jetstar%20Australia/Files/PDF/Flight%20Schedules/NW12_Timetable_Domestic.pdf'
AIRPORT_URL = 'https://raw.githubusercontent.com/davidmegginson/ourairports-data/3b10d0b967cc04c62eb6411939e4e9936a88e701/airports.csv'
PDF_HASH = '03bf458def29b6298311e3d6ced21c7bf585bb6167c611b6e2c13f459b63c4b1'
AIRPORT_HASH = 'a19e9690fc3bffa8c0af18c4de9a6c8e711e64d4647837c58c12269fe348cf17'
ZONES = {
    **dict.fromkeys(['MEL', 'AVV'], 'Australia/Melbourne'),
    **dict.fromkeys(['SYD', 'BNK', 'NTL'], 'Australia/Sydney'),
    **dict.fromkeys(['BNE', 'CNS', 'HTI', 'MCY', 'MKY', 'OOL', 'PPP', 'TSV'], 'Australia/Brisbane'),
    'ADL': 'Australia/Adelaide', 'PER': 'Australia/Perth', 'DRW': 'Australia/Darwin',
    'HBA': 'Australia/Hobart', 'LST': 'Australia/Hobart',
}
ROW = re.compile(r'(?<!\S)(\d{2,4})\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})\s+'
                 r'(Daily|[Xx]?[1-7]+)\s+([A-Z]{3})\s+([A-Z]{3})\s+(\w{3})\s+(\d{1,4})\s+(\d{1,4})(?!\S)')


def operating_days(value):
    if value == 'Daily':
        return set(range(1, 8))
    if not re.fullmatch(r'[Xx]?[1-7]+', value):
        raise ValueError(f'Invalid operating days: {value}')
    days = {int(n) for n in value.lstrip('Xx')}
    return set(range(1, 8)) - days if value[0].lower() == 'x' else days


def instant(day, clock, zone):
    clock = int(clock)
    hours, minutes = divmod(clock, 100)
    if not (0 <= hours <= 24 and 0 <= minutes < 60) or hours == 24 and minutes:
        raise ValueError(f'Invalid timetable clock: {clock}')
    local = datetime.combine(day, time(hours % 24, minutes)) + timedelta(days=hours // 24)
    candidates = {int(aware.timestamp()) for fold in (0, 1)
                  if (aware := local.replace(tzinfo=ZoneInfo(zone), fold=fold)).astimezone(timezone.utc)
                  .astimezone(ZoneInfo(zone)).replace(tzinfo=None) == local}
    if len(candidates) != 1:
        raise ValueError(f'Ambiguous or nonexistent local clock: {local} {zone}')
    return candidates.pop()


def flight_times(day, departure, arrival, origin_zone, destination_zone):
    start = instant(day, departure, origin_zone)
    end = instant(day, arrival, destination_zone)
    if end <= start:
        end = instant(day + timedelta(days=1), arrival, destination_zone)
    if not 15 * 60 <= end - start <= 8 * 3600:
        raise ValueError(f'Implausible domestic duration: {end - start}')
    return start, end


def great_circle(a, b, segments=64):
    def vector(point):
        lon, lat = map(math.radians, point)
        return math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)
    u, v = vector(a), vector(b)
    angle = math.acos(max(-1, min(1, sum(x * y for x, y in zip(u, v)))))
    points = []
    for index in range(segments + 1):
        f = index / segments
        if angle < 1e-10:
            points.append(list(a))
            continue
        p = [(math.sin((1 - f) * angle) * x + math.sin(f * angle) * y) / math.sin(angle) for x, y in zip(u, v)]
        points.append([round(math.degrees(math.atan2(p[1], p[0])), 6),
                       round(math.degrees(math.atan2(p[2], math.hypot(p[0], p[1]))), 6)])
    points[0], points[-1] = list(a), list(b)
    return points


def pinned_download(url, path, expected):
    if not path.exists():
        path.write_bytes(urlopen(url, timeout=60).read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Source checksum changed: {path}')
    return path


def prepare(cache, output):
    from pypdf import PdfReader
    cache.mkdir(parents=True, exist_ok=True)
    pdf = pinned_download(PDF_URL, cache / 'jetstar-nw12-domestic.pdf', PDF_HASH)
    airports_csv = pinned_download(AIRPORT_URL, cache / 'ourairports-airports.csv', AIRPORT_HASH)
    rows, malformed = [], []
    for page_index, page in enumerate(PdfReader(pdf).pages):
        page.transfer_rotation_to_content()
        text = page.extract_text(extraction_mode='layout', layout_mode_strip_rotated=False)
        matches = list(ROW.finditer(text))
        for row in matches:
            number, first, last, days, origin, destination, equipment, departure, arrival = row.groups()
            rows.append(dict(number='JQ' + number, first=datetime.strptime(first, '%d/%m/%y').date(),
                             last=datetime.strptime(last, '%d/%m/%y').date(), weekdays=operating_days(days),
                             origin=origin, destination=destination, equipment=equipment,
                             departure=departure, arrival=arrival, page=page_index + 1))
        # Page 3 contains date-formatted flight numbers / numeric date serials.
        # Keep them out rather than guessing flight identifiers or dates.
        remaining = ROW.sub('', text)
        for line in remaining.splitlines():
            if re.search(r'\b[A-Z]{3}\s+[A-Z]{3}\s+32[01]\s+\d+\s+\d+', line):
                malformed.append({'page': page_index + 1, 'reason': 'Malformed flight number or validity date in source'})
    if len(rows) != 568 or len(malformed) != 13:
        raise ValueError(f'Unexpected PDF extraction: {len(rows)} valid / {len(malformed)} malformed rows')
    used = sorted({r[key] for r in rows for key in ['origin', 'destination']})
    with airports_csv.open(encoding='utf-8-sig') as stream:
        catalogue = [r for r in csv.DictReader(stream) if r['iso_country'] == 'AU' and r['iata_code'] in used]
    airports = []
    for code in used:
        candidates = [r for r in catalogue if r['iata_code'] == code]
        if len(candidates) != 1 or code not in ZONES:
            raise ValueError(f'Ambiguous airport or missing timezone: {code}')
        airport = candidates[0]
        airports.append(dict(code=code, icao=airport['ident'], name=f"{airport['name']} ({code})",
                             municipality=airport['municipality'], timezone=ZONES[code], mode='flight',
                             lat=float(airport['latitude_deg']), lon=float(airport['longitude_deg'])))
    flights, seen = [], set()
    for offset in range(-1, (LAST - FIRST).days + 2):
        day = FIRST + timedelta(days=offset)
        for row in rows:
            if not row['first'] <= day <= row['last'] or day.isoweekday() not in row['weekdays']:
                continue
            departure, arrival = flight_times(day, row['departure'], row['arrival'], ZONES[row['origin']], ZONES[row['destination']])
            key = (str(day), row['number'], row['origin'], row['destination'])
            if key in seen:
                raise ValueError(f'Duplicate operating flight: {key}')
            seen.add(key)
            flights.append(dict(id=':'.join(key), number=row['number'], origin=row['origin'], destination=row['destination'],
                                departure=departure, arrival=arrival, equipment=row['equipment'], source_page=row['page']))
    reference = dict(metadata=dict(start_date=str(FIRST), end_date=str(LAST), source='Jetstar domestic NW12 timetable',
        source_url=PDF_URL, source_date='2012-10-09', source_sha256=PDF_HASH, source_valid_from='2012-10-28', source_valid_to='2013-03-30',
        airport_source='OurAirports', airport_source_url='https://ourairports.com/data/', airport_source_sha256=AIRPORT_HASH,
        airport_reference_date='2026-10-24', omitted_source_rows=malformed, parsed_source_rows=len(rows),
        replay_note='Jetstar domestic flights · 4–10 March 2013. Other airlines are not included. Paths illustrate scheduled travel between airports; they are not recorded flight tracks. Some malformed source entries are excluded.'),
        airports=airports, flights=sorted(flights, key=lambda f: (f['departure'], f['id'])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(reference, separators=(',', ':'), allow_nan=False).encode())
    print(json.dumps({'airports': len(airports), 'flights_including_adjacent_dates': len(flights),
                      'parsed_source_rows': len(rows), 'omitted_source_rows': len(malformed),
                      'output_bytes': output.stat().st_size}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/australia-flights-audit')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/australia_flights/2013-03-04.json.gz')
    args = parser.parse_args()
    prepare(args.cache, args.output)
