"""Capture public, airport-specific Google Flights results for a dated replay.

Preparation only: PYTHONPATH=.cache/browser-tools python3 scripts/prepare_google_flights.py
No flight search runs in the app. Cached queries are resumed rather than repeated.
"""
import argparse
import asyncio
import csv
from contextlib import asynccontextmanager
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


def parse_results(scripts, origin, destination, search_date, zones=None, rejected=None, max_duration=8 * 3600):
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
        # A repeated clock hour has two UTC meanings. The source's dated arrival
        # and stated duration may identify exactly one; never guess between two.
        def instants(local):
            return {int(local.replace(fold=fold).timestamp()) for fold in (0,1)
                if datetime.fromtimestamp(local.replace(fold=fold).timestamp(),local.tzinfo).replace(tzinfo=None)==local.replace(tzinfo=None)}
        departures,arrivals=instants(local_departure),instants(local_arrival)
        if not departures or not arrivals:raise ValueError('Nonexistent airport-local clock time')
        matching={(d,a) for d in departures for a in arrivals
            if 60<=a-d<=max_duration and abs((a-d)/60-value[11])<=1}
        if len(matching)>1:raise ValueError('Ambiguous airport-local timestamps despite source duration')
        if matching:departure,arrival=matching.pop()
        if not 60 <= arrival - departure <= max_duration:
            raise ValueError(f'Invalid flight duration: {origin}-{destination} {local_departure.isoformat()} to {local_arrival.isoformat()} (source {value[11]} min)')
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


def country_config(country='AU', scope='domestic'):
    from dashboard.flight_profiles import PROFILES
    if country in PROFILES:
        p=PROFILES[country]
        if scope!='domestic' or not p['domestic']:
            if p.get('worldwide'):raise ValueError('Use prepare_taiwan_hong_kong_flights.py for worldwide international flights')
            raise ValueError('This country profile uses prepare_international_network.py for international flights')
        manifest=json.loads((ROOT/f"data/sources/{p['slug']}_flights_routes.json").read_text())
        config=dict(country=country,zones={a['code']:a['timezone'] for a in manifest['airports']},timezone=p['zone'],end_date=manifest['end_date'],manifest=manifest,scope='domestic',capture_prices=True,currency='USD',max_duration=28800,allow_empty_snapshot=True)
        if manifest.get('query_date_policy')=='origin_local_departure_day_only':
            config.update(queries=[(manifest['start_date'],a,b) for a,b in manifest['routes']],reject_invalid_segments=True)
        if p.get('origin_local_day'):
            config['capture_wait_until']='domcontentloaded'
        return config
    if country == 'AU' and scope == 'domestic':
        return dict(country='AU', zones=ZONES, timezone='Australia/Melbourne', end_date=None, manifest=None)
    if country not in {'AU', 'ID', 'MY', 'SG', 'IN', 'KR', 'JP', 'CN', 'TH', 'PH', 'VN'}:
        raise ValueError(f'Unsupported flight country: {country}')
    if country=='SG' and scope!='international':
        raise ValueError('Singapore flights use international scope')
    if country in {'TH','PH','VN'} and scope!='domestic':
        raise ValueError('Thailand/Philippines/Vietnam international flights use prepare_international_network.py')
    if country in {'KR', 'JP', 'CN'} and scope != 'domestic':
        label = {'KR':'South Korea','JP':'Japan','CN':'China','TH':'Thailand'}[country]
        raise ValueError(f'{label} international flights are planned; only domestic is available')
    name = {'AU':'australia','ID':'indonesia','MY':'malaysia','SG':'singapore','IN':'india','KR':'south_korea','JP':'japan','CN':'china','TH':'thailand','PH':'philippines','VN':'vietnam'}[country]
    kind = 'international' if scope == 'international' else 'flights'
    filename = f'{name}_{kind}_routes.json'
    manifest = json.loads((ROOT / 'data/sources' / filename).read_text())
    return dict(country=country, zones={a['code']: a['timezone'] for a in manifest['airports']},
        timezone=manifest['timezone'], end_date=manifest['end_date'], manifest=manifest,
        scope=scope, capture_prices=country in {'MY','SG','IN','KR','JP','CN','TH','PH','VN'}, currency={'MY':'MYR','SG':'USD','IN':'USD','KR':'USD','JP':'USD','CN':'USD','TH':'USD','PH':'USD','VN':'USD'}.get(country), max_duration=manifest.get('max_duration', 8 * 3600))


def expected_queries(search_date, pairs, config=None, end_date=None):
    config = config or country_config()
    if 'queries' in config:
        allowed = {tuple(p) for p in pairs}
        yield from (tuple(q) for q in config['queries'] if tuple(q[1:]) in allowed)
        return
    for origin, destination in pairs:
        if config.get('scope') in {'international','hubs'}:
            zone = ZoneInfo(config['zones'][origin])
            midnight = datetime.fromisoformat(search_date).replace(tzinfo=ZoneInfo(config['timezone']))
            finish = datetime.fromisoformat(end_date or config['end_date']).replace(tzinfo=ZoneInfo(config['timezone'])) + timedelta(days=1)
            start = (midnight - timedelta(seconds=config['max_duration'])).astimezone(zone).date()
            end = (finish - timedelta(seconds=1)).astimezone(zone).date()
            dates = [(start + timedelta(days=n)).isoformat() for n in range((end-start).days+1)]
        elif config.get('allow_empty_snapshot') or config['country'] in {'ID','MY','IN','KR','JP','CN','TH','PH','VN'}:
            start = date.fromisoformat(search_date) - timedelta(days=1)
            end = date.fromisoformat(end_date or config['end_date']) + timedelta(days=1 if config['country']=='ID' else 0)
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


def query_path(cache, day, origin, destination, config):
    if config.get('hub_codes'):
        owner=next((h for h in config['hub_codes'] if h in (origin,destination)),None)
        if owner is None:raise ValueError('Flight route must touch a selected hub')
        cache=cache/owner
    return cache/f'{day}-{origin}-{destination}.json'


@asynccontextmanager
async def browser_cleanup_tasks():
    cleanups=[]
    try:
        yield cleanups
    finally:
        await asyncio.gather(*cleanups)


async def close_browser(browser, cleanups, timeout=10):
    """Let disconnected Chrome profile cleanup finish without holding the next batch.

    A connected browser must finish closing before we open another. All pending
    cleanup tasks are awaited before the Playwright driver exits.
    """
    task=asyncio.create_task(browser.close())
    done,_=await asyncio.wait([task],timeout=timeout)
    if task in done or browser.is_connected():
        await task
    else:
        cleanups.append(task)
        print('Browser disconnected; finishing profile cleanup in background',flush=True)


async def _capture(cache, search_date, pairs, concurrency, config=None, end_date=None):
    from playwright.async_api import async_playwright
    cache.mkdir(parents=True, exist_ok=True)
    pending = asyncio.Queue()
    config = config or country_config()
    for day, origin, destination in expected_queries(search_date, pairs, config, end_date):
        path = query_path(cache,day,origin,destination,config)
        if path.exists() and config.get('capture_context'):
            if json.loads(path.read_text()).get('capture_context')!=config['capture_context']:
                raise ValueError('Incompatible capture context; use a separate cache')
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            pending.put_nowait((origin, destination, day, path))
    total = pending.qsize()
    print(f'Collecting {total} uncached airport/date queries', flush=True)
    async with async_playwright() as p, browser_cleanup_tasks() as cleanups:
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
                    params=dict(hl='en', q=f'Flights from {origin} to {destination} on {day} one way nonstop')
                    if config.get('capture_prices'):
                        params.update(curr=config['currency']);params['q']+=' one adult economy'
                    url = 'https://www.google.com/travel/flights?' + urlencode(params)
                    try:
                        await page.goto(url, wait_until=config.get('capture_wait_until','commit'), timeout=45000)
                        if '/sorry/' in page.url:
                            raise RuntimeError('Search access limited; collection stopped')
                        # Functions avoid the page's Trusted Types restriction on eval strings.
                        await page.wait_for_function('''() => [...document.scripts].some(s => s.textContent.includes("key: 'ds:1'"))''', timeout=15000)
                        scripts = await page.locator('script').all_text_contents()
                        rejected = [] if config.get('reject_invalid_segments') or config['country'] in {'ID','MY','IN','KR','JP','CN','TH','PH','VN'} or config.get('scope') in {'international','hubs'} else None
                        records = parse_results(scripts, origin, destination, day, config['zones'], rejected, config.get('max_duration', 8 * 3600))
                        body = await page.locator('body').inner_text()
                        if '/sorry/' in page.url or 'unusual traffic' in body.lower():
                            raise RuntimeError('Search access limited; stop rather than retrying a challenge')
                        captured_at=datetime.now(timezone.utc).isoformat()
                        price_error=None
                        if config.get('capture_prices'):
                            from scripts.flight_prices import cheapest_prices, verify_fare_context
                            try:
                                verify_fare_context(body,config['currency'])
                            except ValueError as error:
                                # Exact dated schedules remain useful when fare context
                                # cannot be confirmed. Never relabel an uncertain quote.
                                price_error=str(error)
                            else:
                                prices=cheapest_prices(scripts,records,config['currency'])
                                for record in records:
                                    if record['id'] in prices:record['price']={**prices[record['id']],'captured_at':captured_at}
                        result = dict(origin=origin, destination=destination, date=day, url=url,
                            captured_at=captured_at, flights=records,
                            page_sha256=hashlib.sha256('\n'.join(scripts).encode()).hexdigest(),
                            status='results' if records else ('rejected_source_records' if rejected else 'no_matching_direct_flights'))
                        if config.get('capture_context'):result['capture_context']=config['capture_context']
                        if price_error:result['price_error']=price_error
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
                        path.with_suffix('.error.json').write_text(json.dumps(dict(
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
                await close_browser(browser,cleanups,timeout=config.get('browser_cleanup_timeout',10))




def prepare(cache, output, day, pairs, config=None, end_date=None):
    records, queries = {}, []
    config = config or country_config()
    end_date = end_date or config['end_date'] or day
    if config.get('allow_empty_snapshot'):
        allowed={tuple(p) for p in config['manifest']['routes']}
        if any(tuple(p) not in allowed for p in pairs):raise ValueError('Country route outside approved manifest')
    if config.get('hub_codes') and any(not set((a,b)) & set(config['hub_codes']) or a==b for a,b in pairs):
        raise ValueError('Flight route must touch a selected hub')
    if config['country'] in {'MY','IN','KR','JP','CN','TH','PH','VN'} and config.get('scope') != 'international':
        countries = {a['code']: a['country'] for a in config['manifest']['airports']}
        if any(countries.get(a) != config['country'] or countries.get(b) != config['country'] for a, b in pairs):
            label = {'MY':'Malaysian', 'IN':'Indian', 'KR':'Korean','JP':'Japanese','CN':'Chinese','TH':'Thai','PH':'Philippine','VN':'Vietnamese'}[config['country']]
            raise ValueError(f'{label} domestic routes require two {label} airports')
    if config.get('scope') == 'international':
        countries = {a['code']: a['country'] for a in config['manifest']['airports']}
        if any((countries[a] == config['country']) == (countries[b] == config['country']) for a, b in pairs):
            raise ValueError('International routes must have exactly one national endpoint')
    if config['country'] in {'KR', 'JP', 'CN', 'TH', 'PH', 'VN'}:
        allowed = {tuple(p) for p in config['manifest']['routes']}
        if any(tuple(p) not in allowed for p in pairs):
            raise ValueError(f"{config['country']} domestic route is outside the approved manifest")
    expected = list(expected_queries(day, pairs, config, end_date))
    missing = []
    for d, a, b in expected:
        path = query_path(cache,d,a,b,config)
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
    if not records and not config.get('allow_empty_snapshot'):
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
        source_url='https://www.google.com/travel/flights', source_date=max((q['captured_at'] for q in queries),default='')[:10],
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
        metadata['profile' if config.get('hub_codes') else 'country']='gulf' if config.get('hub_codes') else config['country']
        if config.get('capture_prices'):
            metadata['fare_context']=dict(currency=config['currency'],adults=1,cabin='economy',trip_type='one_way',taxes='Required taxes and fees included; optional charges and baggage may cost extra',basis='Lowest returned quote for the exact flight; captured prices, not live fares')
            metadata['priced_flights']=sum('price' in f for f in reference['flights'])
            metadata['fare_context_unverified_queries']=sum(bool(q.get('price_error')) for q in queries)
        metadata['airlines'] = sorted({f['airline'] for f in reference['flights']})
        metadata['replay_note'] = ('Indonesian domestic flight schedules for 2–8 November 2026. Timeline: WIB; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
            if config['country'] == 'ID' else f'Australian domestic flight schedules for {day}. Timeline: Melbourne time; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.')
        if config['country']=='MY':
            metadata['replay_note']='Malaysian domestic flight schedules for 2 November 2026. Timeline and airport boards use Malaysia time. Prices are captured one-adult economy one-way quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='IN':
            metadata['scope']=config['scope']
            metadata['replay_note']=f"Indian {config['scope']} flight schedules for 2 November 2026. Timeline: IST; airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks."
        if config['country']=='KR':
            metadata['scope']='domestic'
            metadata['excluded_airports']=config['manifest']['excluded_airports']
            metadata['replay_note']='South Korean domestic flight schedules for 2 November 2026. Timeline and airport boards use KST. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='JP':
            metadata['scope']='domestic'
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['deferred_airports']=config['manifest']['deferred_airports']
            metadata['replay_note']='Japanese domestic flight schedules for 2 November 2026. Timeline and airport boards use JST. Major airports and city routes first; small island and commuter services are not included. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config.get('allow_empty_snapshot'):
            metadata['scope']='domestic'
            stop=cache/'collection-stop.json'
            if stop.exists():metadata['collection_stop']=json.loads(stop.read_text())
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['replay_note']='Captured domestic schedules only. Empty results mean not returned, not no service. Coverage and prices are partial; paths are illustrative.'
            for key in ('deferred_airports','deferred_routes'):
                if key in config['manifest']:metadata[key]=config['manifest'][key]
        if config['manifest'].get('query_date_policy')=='origin_local_departure_day_only':
            from dashboard.flight_profiles import PROFILES
            if PROFILES.get(config['country'],{}).get('origin_local_day'):
                # One origin-local date across multiple zones spans more than 24h.
                # Include the complete dated captures and their overnight arrivals.
                reference['flights']=sorted(records.values(),key=lambda f:(f['departure'],f['id']))
                reference['airports']=airports
                represented={f[k] for f in reference['flights'] for k in ('origin','destination')}
                for f in reference['flights']:
                    if datetime.fromtimestamp(f['departure'],ZoneInfo(config['zones'][f['origin']])).date().isoformat()!=day:
                        raise ValueError('Flight outside origin-local departure day')
                metadata['replay_note']=config['manifest']['replay_note']
                metadata['query_date_policy']='origin_local_departure_day_only'
                metadata['priced_flights']=sum('price' in f for f in reference['flights'])
                metadata['airlines']=sorted({f['airline'] for f in reference['flights']})
        if config['country']=='VN':
            metadata['scope']='domestic'
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['replay_note']='Vietnamese domestic flight schedules for 2 November 2026. Timeline: Vietnam time (ICT, UTC+7); airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='PH':
            metadata['scope']='domestic'
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['replay_note']='Philippine domestic flight schedules for 2 November 2026. Timeline: Philippine time (UTC+8); airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='TH':
            metadata['scope']='domestic'
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['deferred_airports']=config['manifest']['deferred_airports']
            metadata['replay_note']='Thai domestic flight schedules for 2 November 2026. Timeline and airport boards use ICT (UTC+7). BKK and DMK are separate airports. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='CN':
            metadata['scope']='domestic'
            metadata['coverage_scope']=config['manifest']['coverage_scope']
            metadata['replay_note']='Mainland Chinese domestic flight schedules for 2 November 2026. Timeline and airport boards use China time (UTC+8), including Urumqi. Selected major airports and published route candidates; small airports and international/regional connections are not included. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config['country']=='SG':
            metadata['replay_note']='Singapore flight schedules for 2 November 2026. SIN and XSP are separate airports. Timeline: SGT; airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config.get('hub_codes'):
            metadata['hubs']=config['hub_codes']
            metadata['scope']='hubs'
            metadata['query_owner']=config.get('query_owner')
            metadata['replay_note']='Gulf hub flight schedules for 2 November 2026. Timeline: Dubai time (UTC+4); airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
        if config.get('scope') == 'international':
            metadata['scope'] = 'international'
            metadata['replay_note'] = metadata['replay_note'].replace('domestic', 'international')
            if config['country']=='MY':
                metadata['replay_note']=metadata['replay_note'].replace('Timeline and airport boards use Malaysia time.','Timeline: MYT; airport boards use local time.')
        successful = {(q['origin'], q['destination']) for q in queries if q['status'] == 'results'}
        attempted = {(q['origin'], q['destination']) for q in queries}
        attempted.update((a, b) for d, a, b in missing if query_path(cache,d,a,b,config).with_suffix('.error.json').exists())
        metadata['coverage'] = dict(candidate_airports=len(config['manifest']['airports']),
            airports_planned=len({c for pair in pairs for c in pair}),
            airports_searched=len({c for pair in attempted for c in pair}), airports_returned=len(represented),
            routes_planned=len(pairs), routes_searched=len(attempted),
            routes_with_search_results=len(successful), routes_returned=len({(f['origin'],f['destination']) for f in reference['flights']}), queries_planned=len(expected), queries_captured=len(queries),
            queries_not_returned=sum(q['status'] == 'no_matching_direct_flights' for q in queries),
            queries_rejected=sum(q['status'] == 'rejected_source_records' for q in queries),
            rejected_records=sum(len(q.get('rejected_flights', [])) for q in queries), failed_or_missing_queries=len(missing),
            island_groups={g: dict(candidate_airports=sum(a.get('island_group', a.get('country', config['country']))==g for a in config['manifest']['airports']),
                airports_returned=sum(a.get('island_group', a.get('country', config['country']))==g for a in reference['airports']))
                for g in sorted({a.get('island_group', a.get('country', config['country'])) for a in config['manifest']['airports']})})
        if config.get('scope') == 'international':
            metadata['coverage']['candidate_foreign_airports'] = sum(a['country'] != config['country'] for a in config['manifest']['airports'])
        metadata['failed_queries'] = [json.loads(query_path(cache,d,a,b,config).with_suffix('.error.json').read_text())
            for d, a, b in missing if query_path(cache,d,a,b,config).with_suffix('.error.json').exists()]
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
    parser.add_argument('--country', choices=['AU', 'ID', 'MY', 'SG', 'IN', 'KR', 'JP', 'CN', 'TH', 'PH', 'VN'], default='AU')
    parser.add_argument('--scope', choices=['domestic', 'international'], default='domestic')
    parser.add_argument('--end-date')
    parser.add_argument('--date', default=DAY)
    parser.add_argument('--cache', type=Path, default=None)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--concurrency', type=int, choices=[1, 2, 3], default=2)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    config = country_config(args.country, args.scope)
    pairs = config['manifest']['routes'] if config['manifest'] else routes()
    if args.country == 'ID' and args.scope == 'domestic':
        priority = [('CGK','DPS'), ('HLP','SUB'), ('YIA','UPG'), ('PNK','KTG'), ('UPG','AMQ'), ('DJJ','WMX')]
        pairs = priority + [tuple(pair) for pair in pairs if tuple(pair) not in priority]
    name={'AU':'australia','ID':'indonesia','MY':'malaysia','SG':'singapore','IN':'india','KR':'south_korea','JP':'japan','CN':'china','TH':'thailand','PH':'philippines','VN':'vietnam'}[args.country]
    cache_name = name.replace('_', '-')
    cache = args.cache or ROOT / (f'.cache/google-flights-{cache_name}' if args.country != 'AU' else '.cache/google-flights')
    output = args.output or ROOT / f"data/reference/{name}_flights/{args.date}.json.gz"
    if args.scope == 'international' and args.country!='SG':
        cache = args.cache or ROOT / f'.cache/google-flights-{name}-international'
        output = args.output or ROOT / f'data/reference/{name}_flights/{args.date}-international.json.gz'
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
