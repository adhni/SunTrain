"""Capture public, airport-specific Google Flights results for a dated replay.

Preparation only: PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py
No flight search runs in the app. Cached queries are resumed rather than repeated.
"""
import argparse
import asyncio
import csv
import fcntl
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
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


def parse_results(scripts, origin, destination, search_date, zones=None, rejected=None):
    """Read embedded JSON, with optional per-record rejection diagnostics."""
    zones = ZONES if zones is None else zones
    flights, conflicts = {}, set()

    def segment(value):
        # Google's array encoding uses null for zero-valued clock components.
        local_departure = datetime(*value[20], *[v or 0 for v in value[8]], tzinfo=ZoneInfo(zones[origin]))
        local_arrival = datetime(*value[21], *[v or 0 for v in value[10]], tzinfo=ZoneInfo(zones[destination]))
        if local_departure.date().isoformat() != search_date:
            return None
        departure, arrival = int(local_departure.timestamp()), int(local_arrival.timestamp())
        if not 60 <= arrival - departure <= 8 * 3600:
            raise ValueError(f'Invalid domestic flight duration: {origin}-{destination} {local_departure.isoformat()} to {local_arrival.isoformat()} (source {value[11]} min)')
        if abs((arrival - departure) / 60 - value[11]) > 1:
            raise ValueError('Source duration differs from airport-local timestamps')
        carrier, number = value[22][:2]
        if not isinstance(carrier, str) or not isinstance(number, str):
            raise ValueError('Missing flight identity')
        flight_number = carrier + number
        identifier = f'{search_date}:{flight_number}:{origin}:{destination}'
        return dict(id=identifier, number=flight_number, airline=(value[22][3] if len(value[22]) > 3 else None) or carrier,
            carrier=carrier, origin=origin, destination=destination, departure=departure,
            arrival=arrival, aircraft=value[17] or 'Aircraft not specified', source_date=search_date)

    def walk(value):
        if not isinstance(value, list):
            return
        if (len(value) > 22 and value[3] == origin and value[6] == destination
                and isinstance(value[20], list) and len(value[20]) == 3
                and isinstance(value[22], list) and len(value[22]) >= 2):
            try:
                record = segment(value)
                if record is not None:
                    identifier = record['id']
                    if identifier in flights and flights[identifier] != record:
                        conflicts.add(identifier)
                        flights.pop(identifier)
                        raise ValueError('Conflicting duplicate flight')
                    if identifier not in conflicts:
                        flights[identifier] = record
            except (ValueError, TypeError, IndexError) as error:
                if rejected is None:
                    raise
                diagnostic = dict(origin=origin, destination=destination, date=search_date,
                    number=''.join(str(v) for v in value[22][:2]), reason=str(error))
                if diagnostic not in rejected:
                    rejected.append(diagnostic)
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


def country_config(country='AU'):
    if country == 'AU':
        return dict(country='AU', zones=ZONES, timezone='Australia/Melbourne', end_date=None, manifest=None)
    if country != 'ID':
        raise ValueError(f'Unsupported flight country: {country}')
    manifest = json.loads((ROOT / 'data/sources/indonesia_flights_routes.json').read_text())
    return dict(country='ID', zones={a['code']: a['timezone'] for a in manifest['airports']},
        timezone=manifest['timezone'], end_date=manifest['end_date'], manifest=manifest)


def expected_queries(search_date, pairs, config=None, end_date=None):
    config = config or country_config()
    for origin, destination in pairs:
        if config['country'] == 'ID':
            start = date.fromisoformat(search_date) - timedelta(days=1)
            end = date.fromisoformat(end_date or config['end_date']) + timedelta(days=1)
            dates = [(start + timedelta(days=n)).isoformat() for n in range((end-start).days+1)]
        else:
            midnight = datetime.fromisoformat(search_date).replace(tzinfo=ZoneInfo(config['timezone']))
            dates = sorted({search_date, midnight.astimezone(ZoneInfo(config['zones'][origin])).date().isoformat()})
        for day in dates:
            yield day, origin, destination


async def capture(cache, search_date, pairs, concurrency, config=None, end_date=None):
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / '.collection.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another collector is using this cache; collection not started') from error
        try:
            return await _capture(cache, search_date, pairs, concurrency, config, end_date)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def _capture(cache, search_date, pairs, concurrency, config=None, end_date=None):
    from playwright.async_api import async_playwright
    cache.mkdir(parents=True, exist_ok=True)
    pending = asyncio.Queue()
    config = config or country_config()
    for day, origin, destination in expected_queries(search_date, pairs, config, end_date):
        path = cache / f'{day}-{origin}-{destination}.json'
        if not path.exists():
            pending.put_nowait((origin, destination, day, path))
    total = pending.qsize()
    print(f'Collecting {total} uncached airport/date queries', flush=True)
    async with async_playwright() as p:
        completed = 0
        # Bound browser memory/cache growth during thousands of dated searches.
        while not pending.empty():
            batch = asyncio.Queue()
            while not pending.empty() and batch.qsize() < 50:
                batch.put_nowait(pending.get_nowait())
            browser = await p.chromium.launch(channel='chrome', headless=True, args=['--blink-settings=imagesEnabled=false', '--disk-cache-size=16777216', '--media-cache-size=1048576', '--js-flags=--max-old-space-size=512'])
            context = await browser.new_context(ignore_https_errors=True)
            async def worker():
                nonlocal completed
                page = await context.new_page()
                while not batch.empty():
                    if shutil.disk_usage(cache).free < 128 * 1024 * 1024:
                        raise RuntimeError('Low disk space; collection stopped before exhausting the disk')
                    origin, destination, day, path = batch.get_nowait()
                    url = 'https://www.google.com/travel/flights?' + urlencode(dict(hl='en', q=f'Flights from {origin} to {destination} on {day} one way nonstop'))
                    try:
                        await page.goto(url, wait_until='commit', timeout=45000)
                        if '/sorry/' in page.url:
                            raise RuntimeError('Search access limited; collection stopped')
                        # Functions avoid the page's Trusted Types restriction on eval strings.
                        await page.wait_for_function('''() => [...document.scripts].some(s => s.textContent.includes("key: 'ds:1'"))''', timeout=15000)
                        scripts = await page.locator('script').all_text_contents()
                        rejected = [] if config['country'] == 'ID' else None
                        records = parse_results(scripts, origin, destination, day, config['zones'], rejected)
                        body = await page.locator('body').inner_text()
                        if '/sorry/' in page.url or 'unusual traffic' in body.lower():
                            raise RuntimeError('Search access limited; stop rather than retrying a challenge')
                        result = dict(origin=origin, destination=destination, date=day, url=url,
                            captured_at=datetime.now(timezone.utc).isoformat(), flights=records,
                            page_sha256=hashlib.sha256('\n'.join(scripts).encode()).hexdigest(),
                            status='results' if records else ('rejected_source_records' if rejected else 'no_matching_direct_flights'))
                        if rejected:
                            result['rejected_flights'] = rejected
                        temporary = path.with_suffix('.tmp')
                        temporary.write_text(json.dumps(result, separators=(',', ':')) + '\n')
                        temporary.replace(path)
                    except RuntimeError:
                        raise
                    except Exception as error:
                        # A challenge can replace a page before schedule scripts appear.
                        # Check this again after readiness timeouts instead of continuing.
                        body = ''
                        try:
                            body = await page.locator('body').inner_text(timeout=2000)
                        except Exception:
                            pass  # Diagnostic only: preserve the original collection error.
                        if '/sorry/' in page.url or 'unusual traffic' in body.lower():
                            raise RuntimeError('Search access limited; collection stopped') from error
                        (cache / f'{day}-{origin}-{destination}.error.json').write_text(json.dumps(dict(
                            origin=origin, destination=destination, date=day, error=str(error)[:300])))
                        print(f'Uncollected {origin}-{destination} {day}: {str(error)[:110]}', flush=True)
                        if 'ERR_INTERNET_DISCONNECTED' in str(error):
                            raise RuntimeError('Network connection lost; collection stopped') from error
                    completed += 1
                    if completed % 10 == 0 or completed == total:
                        print(f'{completed}/{total} queries checked', flush=True)
                    await asyncio.sleep(1)
                await page.close()
            tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
            try:
                await asyncio.gather(*tasks)
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            finally:
                await browser.close()



def prepare(cache, output, day, pairs, config=None, end_date=None):
    records, queries = {}, []
    config = config or country_config()
    end_date = end_date or config['end_date'] or day
    expected = list(expected_queries(day, pairs, config, end_date))
    missing = []
    for d, a, b in expected:
        path = cache / f'{d}-{a}-{b}.json'
        if not path.exists():
            missing.append([d, a, b]); continue
        query = json.loads(path.read_text())
        if (query['date'], query['origin'], query['destination']) != (d, a, b):
            raise ValueError('Cached query identity does not match requested airports/date')
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
    airports = []
    if config['manifest']:
        catalogue = {a['code']: a for a in config['manifest']['airports']}
        airports = [catalogue[code] for code in codes]
    else:
        airport_cache = ROOT / '.cache/australia-flights-audit'
        airport_cache.mkdir(parents=True, exist_ok=True)
        airport_file = pinned_download(AIRPORT_URL, airport_cache / 'ourairports-airports.csv', AIRPORT_HASH)
        with airport_file.open(encoding='utf-8-sig') as stream:
            catalogue = list(csv.DictReader(stream))
        for code in codes:
            matches = [a for a in catalogue if a['iso_country'] == config['country'] and a['iata_code'] == code]
            if len(matches) != 1:
                raise ValueError(f'Ambiguous airport: {code}')
            a = matches[0]
            airports.append(dict(code=code, icao=a['ident'], name=f"{a['name']} ({code})", municipality=a['municipality'],
                timezone=config['zones'][code], mode='flight', lat=float(a['latitude_deg']), lon=float(a['longitude_deg'])))
    reference = dict(metadata=dict(start_date=day, end_date=end_date, source='Google Flights airport-specific search snapshot',
        source_url='https://www.google.com/travel/flights', source_date=max(q['captured_at'] for q in queries)[:10],
        airport_source_sha256=AIRPORT_HASH,
        airport_source='OurAirports', airport_source_url='https://ourairports.com/data/', queries=queries,
        uncollected_queries=missing, airlines=sorted({f['airline'] for f in records.values()}),
        replay_note=f"Domestic flight schedules for {date.fromisoformat(day).strftime('%d %B %Y').lstrip('0')}. Airline colours identify the carrier. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks."),
        airports=airports, flights=sorted(records.values(), key=lambda f: (f['departure'], f['id'])))
    if config['manifest']:
        window_start = int(datetime.fromisoformat(day).replace(tzinfo=ZoneInfo(config['timezone'])).timestamp())
        window_end = int(datetime.fromisoformat(end_date).replace(tzinfo=ZoneInfo(config['timezone'])).timestamp()) + 86400
        reference['flights'] = [f for f in reference['flights'] if f['departure'] < window_end and f['arrival'] >= window_start]
        represented = {f[k] for f in reference['flights'] for k in ['origin', 'destination']}
        reference['airports'] = [a for a in airports if a['code'] in represented]
        metadata = reference['metadata']
        metadata['country'] = config['country']
        metadata['airlines'] = sorted({f['airline'] for f in reference['flights']})
        metadata['replay_note'] = 'Indonesian domestic flight schedules for 2–8 November 2026. Timeline: WIB; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        successful = {(q['origin'], q['destination']) for q in queries if q['status'] == 'results'}
        attempted = {(q['origin'], q['destination']) for q in queries}
        attempted.update((a, b) for d, a, b in missing if (cache / f'{d}-{a}-{b}.error.json').exists())
        metadata['coverage'] = dict(candidate_airports=len(config['manifest']['airports']),
            airports_planned=len({c for pair in pairs for c in pair}),
            airports_searched=len({c for pair in attempted for c in pair}), airports_returned=len(represented),
            routes_planned=len(pairs), routes_searched=len(attempted),
            routes_with_search_results=len(successful), routes_returned=len({(f['origin'],f['destination']) for f in reference['flights']}), queries_planned=len(expected), queries_captured=len(queries),
            queries_not_returned=sum(q['status'] == 'no_matching_direct_flights' for q in queries),
            queries_rejected=sum(q['status'] == 'rejected_source_records' for q in queries),
            rejected_records=sum(len(q.get('rejected_flights', [])) for q in queries), failed_or_missing_queries=len(missing),
            island_groups={g: dict(candidate_airports=sum(a['island_group']==g for a in config['manifest']['airports']),
                airports_returned=sum(a['island_group']==g for a in reference['airports']))
                for g in sorted({a['island_group'] for a in config['manifest']['airports']})})
        metadata['failed_queries'] = [json.loads((cache / f'{d}-{a}-{b}.error.json').read_text())
            for d, a, b in missing if (cache / f'{d}-{a}-{b}.error.json').exists()]
        metadata['coverage']['failed_queries'] = len(metadata['failed_queries'])
        metadata['coverage']['unattempted_queries'] = len(missing) - len(metadata['failed_queries'])
        metadata['unresolved_airports'] = config['manifest']['unresolved_airports']
        metadata['route_source_url'] = config['manifest']['route_source_url']
        metadata['route_source_sha256'] = config['manifest']['route_source_sha256']
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    with temporary.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(reference, separators=(',', ':')).encode())
    temporary.replace(output)
    print(json.dumps(dict(airports=len(reference['airports']), flights=len(reference['flights']), queries=len(queries), uncollected=len(missing),
        airlines=reference['metadata']['airlines'], bytes=output.stat().st_size)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--country', choices=['AU', 'ID'], default='AU')
    parser.add_argument('--end-date')
    parser.add_argument('--date', default=DAY)
    parser.add_argument('--cache', type=Path, default=None)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--concurrency', type=int, choices=[1, 2, 3], default=2)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    config = country_config(args.country)
    pairs = config['manifest']['routes'] if config['manifest'] else routes()
    if args.country == 'ID':
        priority = [('CGK','DPS'), ('HLP','SUB'), ('YIA','UPG'), ('PNK','KTG'), ('UPG','AMQ'), ('DJJ','WMX')]
        pairs = priority + [tuple(pair) for pair in pairs if tuple(pair) not in priority]
    cache = args.cache or ROOT / ('.cache/google-flights-indonesia' if args.country == 'ID' else '.cache/google-flights')
    output = args.output or ROOT / f"data/reference/{'indonesia' if args.country == 'ID' else 'australia'}_flights/{args.date}.json.gz"
    stopped = None
    if not args.prepare_only:
        try:
            asyncio.run(capture(cache, args.date, pairs, args.concurrency, config, args.end_date))
        except RuntimeError as error:
            stopped = error
    prepare(cache, output, args.date, pairs, config, args.end_date)
    if stopped:
        print(str(stopped) + '; saved partial snapshot; collection was not retried', file=sys.stderr)
        sys.exit(2)
