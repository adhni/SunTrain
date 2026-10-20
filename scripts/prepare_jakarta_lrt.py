"""Prepare LRT Jabodebek station-time replay without inventing terminal arrivals."""
from collections import Counter, defaultdict
from datetime import date, timedelta
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import compact_reference
from scripts.prepare_france_replay import FranceRailGraph
from scripts.prepare_switzerland_geometry import compact_ways
from scripts.prepare_jakarta_timetable import save
from scripts.prepare_transit_replay import seconds

SOURCE = ROOT / 'data/reference/jakarta/lrt-jabodebek-2026-10-20.json.gz'
GEOMETRY = ROOT / 'data/reference/jakarta/lrt-osm-2026-10-20.json.gz'
SOURCE_SHA256 = 'fcd5394fd05c965f0ae22ad7c8c0afdde3989eeb17fbc66d68c73b2f6881c6b8'
GEOMETRY_SHA256 = '7a5a2485dcf8d1c6aeae32f9a535ff5d7d7779193a3644eb49871388529d69b6'
API = 'https://api.commute.shiorilabs.id'
RELATIONS = [16036440, 16036441, 16079478, 16079479]
NOTE = ('LRT Jabodebek: community-converted September 2026 station schedules, '
        'matched by weekday/weekend. Terminal arrival times are unavailable; '
        'animation ends at the last published call.')


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path)) as stream:
        return json.load(stream)


def prepare_sources(cache):
    """Normalize audited local downloads; raw URLs/hashes remain in provenance."""
    stations = read(cache / 'stations.json')['data']
    station_by_code = {s['code']: s for s in stations}
    lines = {read(cache / name)['data']['line']['lineCode']: read(cache / name)['data']
             for name in ['cibubur.json', 'bekasi.json']}
    sequences = {key: [s['code'] for segment in line['segments'] for s in segment['stations']]
                 for key, line in lines.items()}
    sources = [{'source_url': API + url, 'sha256': hashlib.sha256((cache / name).read_bytes()).hexdigest()}
               for name, url in [('stations.json', '/stations/LRTJBDB'), ('cibubur.json', '/lines/LRTJBDB/CB'),
                                 ('bekasi.json', '/lines/LRTJBDB/BK')]]
    trips, updates = [], set()
    official = (cache / 'official.html').read_text()
    bodies = re.split(r'<div class="tab-pane[^>]*?id="pills-([^" ]+)"[^>]*>', official)[2::2]
    official_order = ['DKA','SET','RAS','KUA','PAN','CKK','CIL','CWG','HAL','JBU','CK1','CK2','BEK','JTM','HAR','KAM','CRC','TMI']
    clocks = {code: [Counter(re.findall(r'\d\d:\d\d', table)) for table in re.findall(r'<table.*?</table>', body, re.S)]
              for code, body in zip(official_order, bodies)}
    if len(clocks) != 18 or any(len(v) != 2 for v in clocks.values()):
        raise ValueError('Official station table layout changed')
    validation = {}
    for kind in ['WD', 'SAT', 'SUN']:
        groups = defaultdict(list); matched = total = 0
        for code in station_by_code:
            path = cache / f'{code}-{kind}.json'; payload = read(path)
            if payload['status'] != 200:
                raise ValueError('Invalid timetable response')
            sources.append({'source_url': f'{API}/stations/LRTJBDB/{code}/timetable?day={kind}',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            observed = Counter(r['estimatedDeparture'][:5] for r in payload['data'])
            matched += sum((observed & clocks[code][0 if kind == 'WD' else 1]).values())
            total += sum(observed.values())
            for row in payload['data']:
                if row['stationId'] != 'LRTJBDB-' + code:
                    raise ValueError('Station response mismatch')
                updates.add(row['updatedAt'][:10])
                groups[row['tripNumber']].append((code, row))
        validation[kind] = {'matched_official_departures': matched, 'compared': total}
        for identifier, calls in sorted(groups.items()):
            line = calls[0][1]['lineCode']; sequence = sequences[line]
            # The data omits each destination terminal arrival. Require the
            # entire contiguous origin-to-penultimate sequence; never interpolate
            # missing calls, infer a short turn or add an arrival duration.
            forward = calls[0][1]['boundFor'] != station_by_code[sequence[0]]['name']
            ordered = sequence if forward else list(reversed(sequence))
            by_code = {code: row for code, row in calls}
            if len(by_code) != len(calls) or set(by_code) != set(ordered[:-1]):
                raise ValueError('Incomplete/unexpected LRT station sequence: ' + identifier)
            times = [[code, seconds(by_code[code]['estimatedDeparture'])] for code in ordered[:-1]]
            if any(b[1] <= a[1] for a, b in zip(times, times[1:])):
                raise ValueError('Non-monotonic LRT journey: ' + identifier)
            trips.append({'number': identifier, 'calendar': kind, 'line': line,
                'destination': ordered[-1], 'calls': times})
    meta = {'source': 'Commute Data Platform / Shiori Labs, LRT Jabodebek station schedules',
        'source_url': 'https://data.commute.shiorilabs.id/docs', 'accessed': '2026-10-20',
        'license': 'ODbL 1.0', 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
        'source_updated_dates': sorted(updates), 'sources': sources, 'validation': validation,
        'official_reference': {'source_url': 'https://lrtjabodebek.kai.id/jadwal-keberangkatan',
            'sha256': hashlib.sha256((cache / 'official.html').read_bytes()).hexdigest()},
        'note': NOTE + ' Source trip identifiers are community groupings, not verified operator train numbers.'}
    save({'metadata': meta, 'stations': {s['code']: {'name': s['name'], 'lon': s['longitude'], 'lat': s['latitude']} for s in stations},
        'lines': {k: {'name': v['line']['name'], 'color': v['line']['colorCode'], 'stations': sequences[k]} for k,v in lines.items()},
        'trips': trips}, SOURCE)
    nodes, ways, sources = {}, {}, []
    for identifier in RELATIONS:
        path = cache / f'relation-{identifier}.osm'
        sources.append({'source_url': f'https://api.openstreetmap.org/api/0.6/relation/{identifier}/full',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for element in ET.fromstring(path.read_bytes()):
            key = element.get('id'); tags = {t.get('k'): t.get('v') for t in element.findall('tag')}
            if element.tag == 'node': nodes[key] = [float(element.get('lon')), float(element.get('lat'))]
            elif element.tag == 'way' and tags.get('railway') == 'light_rail':
                ways[key] = {'nodes': [n.get('ref') for n in element.findall('nd')], 'gauge': tags.get('gauge', '')}
    save({'metadata': {'source': '© OpenStreetMap contributors', 'source_date': '2026-10-20',
        'license': 'ODbL 1.0', 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/', 'sources': sources},
        'ways': compact_ways(ways, nodes)}, GEOMETRY)
    print('source', hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE.stat().st_size,
          'geometry', hashlib.sha256(GEOMETRY.read_bytes()).hexdigest(), GEOMETRY.stat().st_size,
          'validation', validation, flush=True)


def build():
    for path, pin in [(SOURCE, SOURCE_SHA256), (GEOMETRY, GEOMETRY_SHA256)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise ValueError('LRT reference changed; inspect before updating pin: ' + str(path))
    source, geometry = read(SOURCE), read(GEOMETRY)
    graph = FranceRailGraph(geometry['ways'])
    codes = list(source['stations']); ids = {code: i for i, code in enumerate(codes)}
    stations = source['stations']; first = date(2025,12,15)
    result = {'stations': [{**stations[c], 'mode': 'train'} for c in codes],
        'patterns': {}, 'paths': {}, 'days': {str(first + timedelta(days=i)): [] for i in range(7)}, 'train_numbers': {}}
    for trip in source['trips']:
        calls = trip['calls']; start = calls[0][1]; legs = []
        for (a,_), (b,_) in zip(calls, calls[1:]):
            key = 'lrt-' + a + '-' + b
            if key not in result['paths']:
                points = [[stations[c]['lon'], stations[c]['lat']] for c in [a,b]]
                curve = graph.leg(*points)
                if not curve or cumulative_distances(curve)[-1] > 3 * cumulative_distances(points)[-1]:
                    raise ValueError('Missing/implausible LRT track path: ' + key)
                result['paths'][key] = {'coordinates': curve, 'distances': cumulative_distances(curve), 'quality': 'track'}
            legs.append(key)
        line = source['lines'][trip['line']]
        pattern = {'mode': 'light_rail', 'operator': 'LRT Jabodebek',
            'line': 'LRT ' + ('Cibubur' if trip['line'] == 'CB' else 'Bekasi'), 'route_id': trip['line'],
            'color': line['color'], 'direction': 'To ' + {'DKA':'Dukuh Atas', 'JTM':'Jatimulya', 'HAR':'Harjamukti'}[trip['destination']],
            'origin': stations[calls[0][0]]['name'], 'destination': stations[trip['destination']]['name'],
            'terminal_arrival_missing': True,
            'stops': [[ids[c], t-start, t-start] for c,t in calls], 'legs': legs}
        key = hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
        result['patterns'][key] = pattern
        for day, rows in result['days'].items():
            weekday = date.fromisoformat(day).weekday()
            kind = 'WD' if weekday < 5 else 'SAT' if weekday == 5 else 'SUN'
            if trip['calendar'] == kind:
                identifier = kind + '-' + trip['number']; rows.append([key, identifier, start])
                result['train_numbers'][identifier] = trip['number']
    for rows in result['days'].values(): rows.sort(key=lambda r: (r[2], r[1]))
    result['metadata'] = {**source['metadata'], 'start_date': '2025-12-15', 'end_date': '2025-12-21',
        'timezone': 'Asia/Jakarta', 'sources': [{'source_url': source['metadata']['source_url'],
            'source_date': '2026-10-20', 'published': 'September 2026 conversion; captured October 2026', 'sha256': SOURCE_SHA256}],
        'attribution': 'LRT Jabodebek station schedules converted by Commute Data Platform / Shiori Labs (ODbL 1.0); source operator PT Kereta Api Indonesia, LRT Jabodebek. SunTrain replay conversion retains published station events and omits unavailable terminal arrivals. Railway geometry © OpenStreetMap contributors, ODbL 1.0.',
        'replay_note': NOTE, 'omitted_trips': {}, 'unresolved_geometry_patterns': {}, 'unresolved_geometry_trips': {},
        'geometry_source': '© OpenStreetMap contributors; native LRT Jabodebek railway ways',
        'geometry_source_url': 'https://www.openstreetmap.org/copyright',
        'geometry_license': 'ODbL 1.0', 'geometry_license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
        'geometry_source_date': '2026-10-20', 'geometry_sha256': GEOMETRY_SHA256,
        'date_mapping': 'September 2026 community station-time snapshot matched by weekday/weekend onto KRL dates; not December 2025 LRT history'}
    return compact_reference(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-sources', action='store_true')
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/jakarta/lrt')
    args = parser.parse_args()
    if args.prepare_sources: prepare_sources(args.cache)
    else:
        r = build(); print({d: len(v) for d,v in r['days'].items()})
