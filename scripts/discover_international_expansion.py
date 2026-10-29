"""Evidence-led international candidates and cache inventory for the World replay.

Discovery downloads route maps, never flight searches. Cache inspection does not
merge raw schedules into World: the supplemental adapter validates them separately.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard import world_flights as world
from dashboard.international_network import RETIRED_AIRPORTS
from dashboard.international_expansion import is_international
from scripts.prepare_australian_flights import AIRPORT_HASH
from scripts.prepare_gulf_airports import TZ_HASH, NEW_ZONES

DAY = world.DAY
CACHE = ROOT / '.cache/international-expansion'
SOURCE = ROOT / 'data/sources/world_international_expansion.json.gz'
ASIAN_HUBS = 'HND NRT KIX ICN PEK PKX PVG CAN DEL BOM CGK KUL BKK MNL SIN DXB AUH DOH'.split()
BRIDGE_HUBS = 'LHR CDG AMS FRA MAD IST JFK EWR MIA YYZ GRU EZE LIM JNB ADD CMN CAI'.split()
AIRLINES = 'VY EW HV TO UX V7 RO JU FB'.split()
ABSENT_COUNTRIES = {'IR', 'CU', 'AO', 'BZ', 'HN', 'NI'}
ABSENT_GATEWAYS = 'IKA MHD HAV VRA NBJ BZE SAP XPL RTB MGA'.split()
STREAMS = [('asia_gulf', 350), ('europe_airlines', 300), ('intercontinental', 250), ('absent_countries', 100)]
DATES = {'2026-10-31', '2026-11-01', DAY, '2026-11-03'}
PATTERN = re.compile(r'(2026-(?:10-31|11-0[123]))-([A-Z0-9]{3})-([A-Z0-9]{3})\.json')
# These pre-context collectors explicitly configured 24-hour parsing. Their
# empty captures are reusable; do not assume every legacy query used eight hours.
LEGACY_PARSERS = {
    'google-flights-international-network': 'scripts/prepare_international_network.py',
    'google-flights-gulf': 'scripts/prepare_gulf_flights.py',
    'google-flights-australia-international': 'scripts/prepare_australia_international.py',
    'google-flights-indonesia-international': 'scripts/prepare_indonesia_international.py',
    'google-flights-taiwan-hong-kong-worldwide': 'scripts/prepare_taiwan_hong_kong_flights.py',
    'google-flights-malaysia-international': 'scripts/prepare_malaysia_international.py',
    'google-flights-india-international': 'scripts/prepare_indian_flights.py',
    'google-flights-singapore': 'scripts/prepare_singapore_flights.py',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = world.canonical_json(value).encode()
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0) if path.suffix == '.gz' else raw)
    temporary.replace(path)


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def relative(path):
    path = Path(path)
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Capture timestamp has no timezone')
    return parsed.timestamp()


def merged_attempts(manifest, path):
    """Neither a rebuilt manifest nor a missing/stale cache resets paid attempts."""
    local = read(path)['attempts'] if Path(path).exists() else []
    published = manifest.get('collection', {}).get('attempts', [])
    merged = {}
    for journal in (published, local):
        keys = [tuple(row['query']) for row in journal]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate attempts in campaign journal')
        for row in journal:
            key = tuple(row['query'])
            if key in merged and merged[key] != row:
                raise ValueError('Conflicting campaign attempt journals')
            merged[key] = row
    if len(merged) > 1000:
        raise ValueError('Campaign attempt journal exceeds 1,000 searches')
    return list(merged.values())


class Airports:
    """Existing validated identities win; new IATA codes require pinned resolution."""
    def __init__(self, baseline):
        self.known = {a['code']: world.canonical_airport(a) for a in baseline['airports']}
        self.rows = defaultdict(list)
        self.zones = {**NEW_ZONES, 'XPL': 'America/Tegucigalpa'}
        self.unresolved = {}
        airport_file = ROOT / '.cache/australia-flights-audit/ourairports-airports.csv'
        zone_file = ROOT / '.cache/gulf-flights-audit/openflights-airports.dat'
        if digest(airport_file.read_bytes()) != AIRPORT_HASH or digest(zone_file.read_bytes()) != TZ_HASH:
            raise ValueError('Pinned airport/timezone catalogue changed')
        for row in csv.DictReader(airport_file.open(encoding='utf-8-sig')):
            if row['iata_code'] and row['type'] != 'closed':
                self.rows[row['iata_code']].append(row)
        for row in csv.reader(zone_file.open()):
            if (len(row) > 11 and row[11] != '\\N' and any(
                    row[5] in (a.get('icao_code'), a['ident']) for a in self.rows.get(row[4], []))):
                self.zones.setdefault(row[4], row[11])
        for path in sorted((ROOT / 'data/sources').glob('*routes.json')):
            for a in read(path).get('airports', []):
                if any(a.get('icao') in (r.get('icao_code'), r['ident']) for r in self.rows.get(a.get('code'), [])):
                    self.zones[a['code']] = a['timezone']

    def country(self, code):
        if code in self.known:
            return self.known[code]['country']
        values = {r['iso_country'] for r in self.rows.get(code, [])}
        return next(iter(values)) if len(values) == 1 else None

    def possibly_international(self, a, b):
        ca, cb = self.country(a), self.country(b)
        return not ca or not cb or is_international({'country': ca}, {'country': cb})

    def get(self, code):
        if code in RETIRED_AIRPORTS:
            self.unresolved[code] = 'Retired commercial endpoint; do not infer its replacement'
            return None
        if code in self.known:
            return self.known[code]
        rows = self.rows.get(code, [])
        if len(rows) != 1 or code not in self.zones:
            self.unresolved[code] = 'Missing/ambiguous active IATA identity or explicit IANA timezone'
            return None
        row = rows[0]
        ZoneInfo(self.zones[code])
        result = dict(code=code, icao=row.get('icao_code') or row['ident'],
                      name=f"{row['name']} ({code})", municipality=row['municipality'],
                      country=row['iso_country'], timezone=self.zones[code], mode='flight',
                      lat=float(row['latitude_deg']), lon=float(row['longitude_deg']))
        result = world.canonical_airport(result)
        self.known[code] = result
        return result


def validate_query(query, key, airports, legacy_duration=None):
    if tuple(query.get(k) for k in ('date', 'origin', 'destination')) != tuple(key):
        raise ValueError('Wrong exact query identity')
    timestamp(query['captured_at'])
    if query.get('status') not in {'results', 'no_matching_direct_flights'} or query.get('rejected_flights'):
        raise ValueError('Rejected or partially rejected capture')
    if bool(query.get('flights')) != (query['status'] == 'results'):
        raise ValueError('Capture status disagrees with records')
    url = urlparse(query.get('url', ''))
    params = parse_qs(url.query)
    expected = f'Flights from {key[1]} to {key[2]} on {key[0]} one way nonstop'
    if url.hostname != 'www.google.com' or params.get('q', [''])[0] not in {expected, expected+' one adult economy'}:
        raise ValueError('Not an exact-airport all-airline nonstop query')
    context = query.get('capture_context') or {}
    if context.get('airline_filter', 'none') != 'none':
        raise ValueError('Airline-limited search')
    if not query['flights'] and context.get('max_duration', legacy_duration or 28800) < 86400:
        raise ValueError('Empty short-parser result is not a compatible international search')
    identities = {}
    a, b = airports.get(key[1]), airports.get(key[2])
    if not a or not b:
        raise ValueError('Unresolved airport')
    if not is_international(a, b):
        raise ValueError('Domestic query')
    zone = ZoneInfo(a.get('replay_timezone', a['timezone']))
    for flight in query['flights']:
        if tuple(flight.get(k) for k in ('source_date', 'origin', 'destination')) != tuple(key):
            raise ValueError('Wrong dated flight segment')
        if any(type(flight.get(k)) is not int for k in ('departure', 'arrival')):
            raise ValueError('Undated segment')
        if not 60 <= flight['arrival'] - flight['departure'] <= 86400:
            raise ValueError('Invalid duration')
        if datetime.fromtimestamp(flight['departure'], zone).date().isoformat() != key[0]:
            raise ValueError('Wrong airport-local departure date')
        if not all(isinstance(flight.get(k), str) and flight[k] for k in ('id', 'carrier', 'number')):
            raise ValueError('Missing flight identity')
        identity = world.identity(flight)
        if identities.setdefault(flight['id'], identity) != identity:
            raise ValueError('Conflicting source identity')
        price = flight.get('price')
        if price and (query.get('price_error') or price.get('currency') not in world.CURRENCIES
                      or params.get('curr') != [price['currency']]
                      or type(price.get('amount_minor')) is not int or price['amount_minor'] <= 0
                      or tuple(price.get(k) for k in ('adults', 'cabin', 'trip_type')) != (1, 'economy', 'one_way')):
            raise ValueError('Unverified fare context')
    return query


def audit(cache=CACHE, directories=None):
    """Index latest intact schedules, without duplicating all raw cache files."""
    original = cache / 'baseline.json.gz'
    if original.exists():
        baseline = read(original)
    else:
        baseline = world.load_reference(DAY)
        if 'world_international_expansion' in baseline['metadata'].get('member_views', {}):
            # A fresh checkout may already contain the expanded World snapshot.
            # Recreate the 40-view baseline instead of feeding this campaign
            # back into itself or declaring its existing additions new again.
            previous = os.environ.get('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE')
            os.environ['SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE'] = str(cache/'no-supplement.gz')
            try:
                baseline = world.prepare(original)
            finally:
                if previous is None:
                    os.environ.pop('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE', None)
                else:
                    os.environ['SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE'] = previous
        else:
            save(original, baseline)
    airports = Airports(baseline)
    candidates, invalid, failures = {}, Counter(), []
    totals = Counter()
    directories = directories or sorted((ROOT / '.cache').glob('google-flights*'))
    for directory in directories:
        for path in sorted(directory.rglob('*.json')):
            match = PATTERN.fullmatch(path.name)
            if not match:
                continue
            key = match.groups()
            if not airports.possibly_international(key[1], key[2]):
                continue
            a, b = airports.get(key[1]), airports.get(key[2])
            if not a or not b or not is_international(a, b):
                continue
            totals['files_inspected'] += 1
            raw = path.read_bytes()
            try:
                query = validate_query(json.loads(raw), key, airports, 86400 if directory.name in LEGACY_PARSERS else None)
            except (ValueError, KeyError, TypeError) as error:
                invalid[str(error)] += 1
                failures.append(dict(query=list(key), path=relative(path), reason=str(error)))
                continue
            info = dict(path=relative(path), sha256=digest(raw), captured_at=query['captured_at'],
                        flights=len(query['flights']), status=query['status'])
            if directory.name in LEGACY_PARSERS and not query.get('capture_context'):
                source = LEGACY_PARSERS[directory.name]
                info['parser_evidence'] = dict(path=source, sha256=digest((ROOT/source).read_bytes()), max_duration=86400)
            candidates.setdefault(key, []).append(info)
    rows = []
    for key, values in sorted(candidates.items()):
        values.sort(key=lambda x: (timestamp(x['captured_at']), x['path']))
        rows.append(dict(query=list(key), latest=values[-1], sources=values))
    # Freeze the original World counts and hashes so resumed runs never treat
    # additions from this campaign as the pre-expansion baseline.
    result = dict(day=DAY, queries=rows, rejected_caches=failures,
                  invalid_reasons=dict(sorted(invalid.items())), totals=dict(totals),
                  unresolved_airports=dict(sorted(airports.unresolved.items())))
    save(cache / 'cache-index.json.gz', result)
    print(json.dumps(dict(cached_international_queries=len(rows), **totals,
                          invalid_reasons=result['invalid_reasons'], unresolved_airports=len(airports.unresolved))), flush=True)
    return result


def fetch_map(kind, code, cache):
    """Reuse pinned local maps; each missing source gets one request, no challenge retries."""
    import requests
    import html
    suffix = f'{code.lower()}-routes.svg'
    url = (f'https://www.gcpromap.com/assets/images/airports/{suffix}' if kind == 'airport'
           else f'https://www.gcpromap.com/assets/images/airlines/carriers/{suffix}')
    target = cache / 'discovery' / f'{kind}-{suffix}'
    if not target.exists():
        compatible = sorted((ROOT / '.cache').glob(f'*-audit/{suffix}'))
        if compatible:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(compatible[0].read_bytes())
        else:
            response = requests.get(url, timeout=35)
            if response.status_code in {403, 429} or 'unusual traffic' in response.text.lower():
                raise RuntimeError('Discovery access challenge; stop without retries')
            if response.status_code != 200:
                return dict(kind=kind, code=code, url=url, error=f'HTTP {response.status_code}', routes=[])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
    raw = target.read_bytes()
    tree = ElementTree.fromstring(raw)
    pairs = set()
    if kind == 'airport':
        for destination in re.findall(r'\(([A-Z0-9]{3})\):', html.unescape(raw.decode())):
            if destination != code:
                pairs.update([(code, destination), (destination, code)])
    else:
        for node in tree.iter():
            match = re.fullmatch(r'([A-Z0-9]{3}) to ([A-Z0-9]{3})', node.text or '') if node.tag.endswith('title') else None
            if match and match[1] != match[2]:
                pairs.update([(match[1], match[2]), (match[2], match[1])])
    print(f'{kind} {code}: {len(pairs)} directional candidates', flush=True)
    return dict(kind=kind, code=code, url=url, sha256=digest(raw), routes=sorted(pairs),
                evidence='Secondary published route map; reverse direction is a candidate, not dated service')


def discover(cache=CACHE):
    baseline = read(cache / 'baseline.json.gz')
    airports = Airports(baseline)
    # Reviewed international gateways, not alphabetical or all-airport pairs.
    absent = [code for code in ABSENT_GATEWAYS if airports.get(code)]
    jobs = [('airport', c) for c in dict.fromkeys(ASIAN_HUBS + BRIDGE_HUBS + absent)]
    jobs += [('airline', c) for c in AIRLINES]
    rows, gaps = [], []
    # Submit only two at a time, so a challenge cannot leave a full queued crawl running.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for start in range(0, len(jobs), 2):
            futures = [(job, pool.submit(fetch_map, *job, cache)) for job in jobs[start:start+2]]
            for job, future in futures:
                try:
                    rows.append(future.result())
                except (requests_error_types()) as error:
                    gaps.append(dict(kind=job[0], code=job[1], error=str(error)))
    result = dict(reviewed_at=datetime.now(timezone.utc).isoformat(), maps=rows, gaps=gaps,
                  absent_country_gateways=absent)
    save(cache / 'discovery.json', result)
    return result


def requests_error_types():
    import requests
    return (requests.RequestException, ElementTree.ParseError)


def build_manifest(cache=CACHE, output=SOURCE):
    baseline = read(cache / 'baseline.json.gz')
    index = read(cache / 'cache-index.json.gz')
    discovery = read(cache / 'discovery.json')
    airports = Airports(baseline)
    world_keys = {world.identity(f) for f in baseline['flights']}
    world_routes = {(f['origin'], f['destination']) for f in baseline['flights']}
    returned_airports = {c for f in baseline['flights'] for c in (f['origin'], f['destination'])}
    world_countries = {a['country'] for a in baseline['airports'] if a['code'] in returned_airports}
    evidence = defaultdict(list)
    for row in discovery['maps']:
        for a, b in row['routes']:
            if not airports.possibly_international(a, b):
                continue
            evidence[(a, b)].append({k: row[k] for k in ('kind', 'code', 'url', 'sha256', 'evidence')})
    # Previously published candidates can fill discovery source failures. The
    # existing manifests remain untouched; their hub whitelist is not inherited.
    for path in sorted((ROOT / 'data/sources').glob('*routes.json')):
        manifest = read(path)
        manifest_hash = digest(path.read_bytes())
        for a, b in manifest.get('routes', []):
            if not (set((a,b)) & set(ASIAN_HUBS+BRIDGE_HUBS)
                    or {airports.country(a),airports.country(b)} & ABSENT_COUNTRIES):
                continue
            if not airports.possibly_international(a,b):
                continue
            aa, bb = airports.get(a), airports.get(b)
            if not aa or not bb or not is_international(aa, bb):
                continue
            if set((a, b)) & set(ASIAN_HUBS + BRIDGE_HUBS) or {aa['country'], bb['country']} & ABSENT_COUNTRIES:
                evidence[(a, b)].append(dict(kind='manifest', code=path.stem, url=relative(path),
                                            sha256=manifest_hash, evidence='Previously sourced directional candidate'))
    indexed = {tuple(row['query']): row for row in index['queries']}
    ledger = {}
    boundary = defaultdict(set)
    for key, row in indexed.items():
        latest = row['latest']
        q = read(ROOT / latest['path'])
        overlapping = [f for f in q['flights'] if f['departure'] < world.END and f['arrival'] >= world.START]
        missing = [f for f in overlapping if world.identity(f) not in world_keys]
        ledger[key] = dict(query=list(key), state='cached_but_excluded' if missing else
                          'empty_result' if not q['flights'] else 'captured',
                          additional_identities=len(missing), **latest)
        for f in q['flights']:
            # Only observed schedules justify a new adjacent-date query. Shift
            # in airport-local calendar time, respecting DST at each airport.
            a, b = airports.get(key[1]), airports.get(key[2])
            for offset in (-1, 1):
                from datetime import timedelta
                origin_zone = ZoneInfo(a.get('replay_timezone', a['timezone']))
                destination_zone = ZoneInfo(b.get('replay_timezone', b['timezone']))
                departure = datetime.fromtimestamp(f['departure'], origin_zone) + timedelta(days=offset)
                arrival = datetime.fromtimestamp(f['arrival'], destination_zone) + timedelta(days=offset)
                candidate = (departure.date().isoformat(), key[1], key[2])
                if (candidate[0] != DAY and candidate[0] in DATES and
                        departure.timestamp() < world.END and arrival.timestamp() >= world.START):
                    boundary[candidate[1:]].add(candidate[0])
    queued = []
    unresolved_pairs = []
    for (a, b), sources in sorted(evidence.items()):
        aa, bb = airports.get(a), airports.get(b)
        if not aa or not bb:
            unresolved_pairs.append(dict(origin=a, destination=b, reason='Unresolved exact airport'))
            continue
        if not is_international(aa, bb):
            continue
        stream = ('asia_gulf' if set((a, b)) & set(ASIAN_HUBS) else
                  'europe_airlines' if any(s['kind'] == 'airline' for s in sources) else
                  'intercontinental' if set((a, b)) & set(BRIDGE_HUBS) else 'absent_countries')
        dates = [DAY] + sorted(boundary[(a, b)])
        for day in dict.fromkeys(dates):
            key = (day, a, b)
            if key in indexed:
                continue
            row = dict(query=list(key), state='never_searched', stream=stream,
                       missing_direction=(a, b) not in world_routes,
                       missing_country=bool({aa['country'], bb['country']} - world_countries),
                       boundary=day != DAY, evidence=sources,
                       source_strength=1 if any(s['kind'] in {'airport','airline'} for s in sources) else 2)
            ledger[key] = row
            queued.append(row)
    def priority(row):
        return (not row['missing_direction'], not row['missing_country'], row['source_strength'], row['boundary'], tuple(row['query'][1:]), row['query'][0])
    queues = {name: sorted((r for r in queued if r['stream'] == name), key=priority) for name, _ in STREAMS}
    previous = read(output) if Path(output).exists() else {}
    attempt_path = ROOT / '.cache/google-flights-world-international-usd-v1/attempts.json'
    attempted = [tuple(r['query']) for r in merged_attempts(previous, attempt_path)]
    selected = []
    for key in attempted:
        row = ledger.get(key, dict(query=list(key), state='interrupted_query'))
        sources = evidence.get(key[1:], [])
        row['stream'] = ('asia_gulf' if set(key[1:]) & set(ASIAN_HUBS) else
                         'europe_airlines' if any(s['kind']=='airline' for s in sources) else
                         'intercontinental' if set(key[1:]) & set(BRIDGE_HUBS) else 'absent_countries')
        selected.append(row)
        ledger[key] = row
    for name, _ in STREAMS:
        queues[name] = [r for r in queues[name] if tuple(r['query']) not in set(attempted)]
    for name, limit in STREAMS:
        available = max(0, limit - sum(r['stream']==name for r in selected))
        selected.extend(queues[name][:available])
        queues[name] = queues[name][available:]
    for name, _ in STREAMS:
        extra = queues[name][:max(0, 1000-len(selected))]
        selected.extend(extra)
        queues[name] = queues[name][len(extra):]
    # Keep each stream's priority order while spreading it across checkpoints.
    stream_rows = {name: [r for r in selected if r['stream'] == name] for name, _ in STREAMS}
    selected = [row for _, _, row in sorted(
        ((i + 0.5) / len(rows), order, row)
        for order, (name, _) in enumerate(STREAMS) for i, row in enumerate(stream_rows[name])
        for rows in [stream_rows[name]])]
    pending = [r for name, _ in STREAMS for r in queues[name]]
    used = {c for r in ledger.values() for c in r['query'][1:] if airports.get(c)}
    result = dict(profile='world_international_expansion', day=DAY, timezone='UTC', currency='USD',
                  search_limit=1000, concurrency=2, baseline_inputs=baseline['metadata']['inputs'],
                  baseline_counts=dict(flights=len(baseline['flights']),
                      international_overlapping=sum(f['flight_scope']=='international' for f in baseline['flights']),
                      international_departures=sum(f['flight_scope']=='international' and world.START<=f['departure']<world.END for f in baseline['flights'])),
                  airports=[airports.known[c] for c in sorted(used)],
                  new_searches=[r['query'] for r in selected], remaining_queue=[r['query'] for r in pending],
                  workstreams={name:dict(budget=limit, selected=sum(r['stream']==name for r in selected),
                                        remaining=len(queues[name])) for name, limit in STREAMS},
                  ledger=[ledger[k] for k in sorted(ledger)],
                  source_documents=discovery, unresolved_airports=dict(sorted(airports.unresolved.items())),
                  unresolved_routes=unresolved_pairs,
                  invalid_cache_counts=index['invalid_reasons'],
                  limitations=['Published routes are candidates, not proof of service on this date.',
                    'Empty results mean not returned, never no service.',
                    'Adjacent dates are searched only when existing timings demonstrate potential UTC overlap; unobserved boundary schedules remain a gap.',
                    'Google Flights can omit airlines, sold-out flights and individual frequencies.'])
    if previous.get('collection'):
        result['collection'] = previous['collection']
    save(output, result)
    print(json.dumps(dict(new_searches=len(selected), remaining=len(pending),
                          cache_states=dict(Counter(r['state'] for r in ledger.values())), workstreams=result['workstreams'])), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['audit', 'discover', 'manifest'])
    parser.add_argument('--cache', type=Path, default=CACHE)
    args = parser.parse_args()
    {'audit': audit, 'discover': discover, 'manifest': build_manifest}[args.action](args.cache)


if __name__ == '__main__':
    main()
