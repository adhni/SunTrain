"""Capture public, airport-specific Google Flights results for a dated replay.

Preparation only: PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py
No flight search runs in the app. Cached queries are resumed rather than repeated.
"""
import argparse
import asyncio
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DAY = '2026-11-02'
ZONES = {
    **dict.fromkeys('MEL AVV MQL'.split(), 'Australia/Melbourne'),
    **dict.fromkeys('SYD BNK NTL ABX DBO OAG WGA MYA CFS TMW PQQ'.split(), 'Australia/Sydney'),
    **dict.fromkeys('BNE CNS HTI MCY MKY OOL PPP TSV ROK BDB GLT'.split(), 'Australia/Brisbane'),
    **dict.fromkeys('ADL MGB'.split(), 'Australia/Adelaide'),
    **dict.fromkeys('PER BME KGI'.split(), 'Australia/Perth'),
    **dict.fromkeys('HBA LST BWT DPO'.split(), 'Australia/Hobart'),
    'DRW': 'Australia/Darwin', 'CBR': 'Australia/Sydney', 'BHQ': 'Australia/Broken_Hill',
}


def parse_results(scripts, origin, destination, search_date):
    """Read JSON data embedded in the rendered page, never execute source code."""
    flights = {}
    def walk(value):
        if not isinstance(value, list):
            return
        if (len(value) > 22 and value[3] == origin and value[6] == destination
                and isinstance(value[20], list) and len(value[20]) == 3
                and isinstance(value[22], list) and len(value[22]) >= 2):
            # Google's array encoding uses null for zero-valued clock components.
            local_departure = datetime(*value[20], *[v or 0 for v in value[8]], tzinfo=ZoneInfo(ZONES[origin]))
            local_arrival = datetime(*value[21], *[v or 0 for v in value[10]], tzinfo=ZoneInfo(ZONES[destination]))
            if local_departure.date().isoformat() != search_date:
                return
            departure, arrival = int(local_departure.timestamp()), int(local_arrival.timestamp())
            if not 15 * 60 <= arrival - departure <= 8 * 3600:
                raise ValueError('Invalid domestic flight duration')
            if abs((arrival - departure) / 60 - value[11]) > 1:
                raise ValueError('Source duration differs from airport-local timestamps')
            carrier, number = value[22][:2]
            if not isinstance(carrier, str) or not isinstance(number, str):
                raise ValueError('Missing flight identity')
            flight_number = carrier + number
            identifier = f'{search_date}:{flight_number}:{origin}:{destination}'
            record = dict(id=identifier, number=flight_number, airline=value[22][3] or carrier,
                carrier=carrier, origin=origin, destination=destination, departure=departure,
                arrival=arrival, aircraft=value[17] or 'Aircraft not specified', source_date=search_date)
            if identifier in flights and flights[identifier] != record:
                raise ValueError('Conflicting duplicate flight')
            flights[identifier] = record
        for child in value:
            walk(child)
    for script in scripts:
        match = re.search(r"AF_initDataCallback\(\{key:.*?data:", script)
        if match:
            try:
                data, _ = json.JSONDecoder().raw_decode(script[match.end():])
            except json.JSONDecodeError:
                continue
            walk(data)
    return sorted(flights.values(), key=lambda f: (f['departure'], f['id']))


def routes():
    with gzip.open(ROOT / 'data/reference/australia_flights/2013-03-04.json.gz', 'rt') as stream:
        old = json.load(stream)
    pairs = {(f['origin'], f['destination']) for f in old['flights']}
    hubs = 'MEL AVV SYD BNE PER ADL CBR HBA DRW CNS OOL'.split()
    pairs.update((a, b) for a in hubs for b in hubs if a != b)
    regional = {'MEL': 'ABX MQL MGB BWT DPO', 'SYD': 'BHQ DBO OAG WGA MYA CFS TMW PQQ',
                'BNE': 'ROK BDB GLT', 'PER': 'BME KGI'}
    for hub, destinations in regional.items():
        for destination in destinations.split():
            pairs.update([(hub, destination), (destination, hub)])
    return sorted(pairs)


async def capture(cache, search_date, pairs, concurrency):
    from playwright.async_api import async_playwright
    cache.mkdir(parents=True, exist_ok=True)
    pending = asyncio.Queue()
    for origin, destination in pairs:
        # Also capture western/central/Queensland departures from the previous
        # local day that can overlap Melbourne midnight.
        dates = [search_date]
        midnight = datetime.fromisoformat(search_date).replace(tzinfo=ZoneInfo('Australia/Melbourne'))
        previous = midnight.astimezone(ZoneInfo(ZONES[origin])).date().isoformat()
        if previous != search_date:
            dates.insert(0, previous)
        for day in dates:
            path = cache / f'{day}-{origin}-{destination}.json'
            if not path.exists():
                pending.put_nowait((origin, destination, day, path))
    total = pending.qsize()
    print(f'Collecting {total} uncached airport/date queries', flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        completed = 0
        async def worker():
            nonlocal completed
            page = await context.new_page()
            while not pending.empty():
                origin, destination, day, path = pending.get_nowait()
                url = 'https://www.google.com/travel/flights?' + urlencode(dict(hl='en', q=f'Flights from {origin} to {destination} on {day} one way nonstop'))
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=45000)
                    if '/sorry/' in page.url:
                        raise RuntimeError('Search access limited; collection stopped')
                    # Functions avoid the page's Trusted Types restriction on eval strings.
                    await page.wait_for_function('''() => [...document.scripts].some(s => s.textContent.includes("key: 'ds:1'"))''', timeout=15000)
                    scripts = await page.locator('script').all_text_contents()
                    records = parse_results(scripts, origin, destination, day)
                    body = await page.locator('body').inner_text()
                    if '/sorry/' in page.url or 'unusual traffic' in body.lower():
                        raise RuntimeError('Search access limited; stop rather than retrying a challenge')
                    result = dict(origin=origin, destination=destination, date=day, url=url,
                        captured_at=datetime.now(timezone.utc).isoformat(), flights=records,
                        page_sha256=hashlib.sha256('\n'.join(scripts).encode()).hexdigest(),
                        status='results' if records else 'no_matching_direct_flights')
                    path.write_text(json.dumps(result, separators=(',', ':')) + '\n')
                except RuntimeError:
                    raise
                except Exception as error:
                    print(f'Uncollected {origin}-{destination} {day}: {str(error)[:110]}', flush=True)
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(f'{completed}/{total} queries checked', flush=True)
                await asyncio.sleep(1)
            await page.close()
        await asyncio.gather(*(worker() for _ in range(concurrency)))
        await browser.close()


def prepare(cache, output, day, pairs):
    records, queries = {}, []
    expected = []
    midnight = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Australia/Melbourne'))
    for a, b in pairs:
        dates = {day, midnight.astimezone(ZoneInfo(ZONES[a])).date().isoformat()}
        expected.extend((d, a, b) for d in sorted(dates))
    missing = []
    for d, a, b in expected:
        path = cache / f'{d}-{a}-{b}.json'
        if not path.exists():
            missing.append([d, a, b]); continue
        query = json.loads(path.read_text())
        queries.append({key: value for key, value in query.items() if key != 'flights'})
        for f in query['flights']:
            if (f['origin'], f['destination']) != (a, b):
                raise ValueError('Search included a different airport')
            if f['id'] in records and records[f['id']] != f:
                raise ValueError('Conflicting flight snapshots')
            records[f['id']] = f
    if not records:
        raise ValueError('No flights collected')
    # Match individual IATA codes; never merge MEL and AVV by municipality.
    codes = sorted({f[key] for f in records.values() for key in ['origin', 'destination']})
    from scripts.prepare_australian_flights import AIRPORT_HASH, AIRPORT_URL, pinned_download
    airport_cache = ROOT / '.cache/australia-flights-audit'
    airport_cache.mkdir(parents=True, exist_ok=True)
    airport_file = pinned_download(AIRPORT_URL, airport_cache / 'ourairports-airports.csv', AIRPORT_HASH)
    with airport_file.open(encoding='utf-8-sig') as stream:
        catalogue = list(csv.DictReader(stream))
    airports = []
    for code in codes:
        matches = [a for a in catalogue if a['iso_country'] == 'AU' and a['iata_code'] == code]
        if len(matches) != 1:
            raise ValueError(f'Ambiguous airport: {code}')
        a = matches[0]
        airports.append(dict(code=code, icao=a['ident'], name=f"{a['name']} ({code})", municipality=a['municipality'],
            timezone=ZONES[code], mode='flight', lat=float(a['latitude_deg']), lon=float(a['longitude_deg'])))
    reference = dict(metadata=dict(start_date=day, end_date=day, source='Google Flights airport-specific search snapshot',
        source_url='https://www.google.com/travel/flights', source_date=max(q['captured_at'] for q in queries)[:10],
        airport_source_sha256=AIRPORT_HASH,
        airport_source='OurAirports', airport_source_url='https://ourairports.com/data/', queries=queries,
        uncollected_queries=missing, airlines=sorted({f['airline'] for f in records.values()}),
        replay_note=f"Domestic flight schedules for {date.fromisoformat(day).strftime('%d %B %Y').lstrip('0')}. Airline colours identify the carrier. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks."),
        airports=airports, flights=sorted(records.values(), key=lambda f: (f['departure'], f['id'])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(reference, separators=(',', ':')).encode())
    print(json.dumps(dict(airports=len(airports), flights=len(records), queries=len(queries), uncollected=len(missing),
        airlines=reference['metadata']['airlines'], bytes=output.stat().st_size)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=DAY)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/google-flights')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/australia_flights/2026-11-02.json.gz')
    parser.add_argument('--concurrency', type=int, choices=[1, 2, 3], default=2)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    pairs = routes()
    if not args.prepare_only:
        asyncio.run(capture(args.cache, args.date, pairs, args.concurrency))
    prepare(args.cache, args.output, args.date, pairs)
