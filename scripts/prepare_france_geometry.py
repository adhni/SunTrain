"""Compile SNCF RFN main-track alignments for offline passenger-rail matching.

Derived database: ODbL 1.0. Junctions are inferred only at original coincident
segment endpoints/vertices; no proximity snapping or new crossing is introduced.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_replay_geometry import simplify

TRACK_URL = 'https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/fichier-de-formes-des-voies-du-reseau-ferre-national/exports/geojson'
SPEED_URL = 'https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/vitesse-maximale-nominale-sur-ligne/exports/json?select=code_ligne,pkd,pkf,v_max'
OUTPUT = ROOT / 'data/reference/france/sncf-tracks-2026-08-12.json.gz'


def coordinate(point):
    return tuple(round(float(v), 7) for v in point[:2])


def pk(value):
    match = re.fullmatch(r'(-?\d+)([+-])(\d+)', str(value))
    if not match:
        return None
    return int(match[1]) * 1000 + (-1 if match[2] == '-' else 1) * int(match[3])


def compile_ways(features, speeds):
    sections, ends, omitted = [], set(), Counter()
    for index, f in enumerate(features):
        p, g = f['properties'], f['geometry']
        if p.get('type_voie') not in {'VPL', 'VPA'}:
            omitted['service_tracks'] += 1
            continue
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates'] if g['type'] == 'MultiLineString' else []
        for part, line in enumerate(lines):
            points = [coordinate(p) for p in line]
            if len(points) < 2:
                continue
            ends.update((points[0], points[-1]))
            sections.append((str(p['idgaia']) + ':' + str(p.get('rg_troncon', '')) + ':' + str(index) + ':' + str(part), p, points))
    by_line = defaultdict(list)
    for r in speeds:
        a, b = pk(r.get('pkd')), pk(r.get('pkf'))
        if a is not None and b is not None and str(r.get('v_max', '')).isdigit():
            by_line[str(r['code_ligne']).zfill(6)].append((min(a, b), max(a, b), int(r['v_max'])))
    ways = []
    for identifier, p, points in sections:
        code = str(p['code_ligne']).zfill(6)
        a, b = pk(p.get('pk_debut_r')), pk(p.get('pk_fin_r'))
        values = [v for lo, hi, v in by_line[code] if a is not None and b is not None and max(min(a,b),lo) < min(max(a,b),hi)]
        speed = min(350, max(20, max(values, default=100)))
        # Preserve every potential junction before simplifying intervening curves.
        cuts = sorted({0, len(points)-1, *(i for i, point in enumerate(points) if point in ends)})
        for start, finish in zip(cuts, cuts[1:]):
            if start == finish:
                continue
            curve = simplify(points[start:finish+1])
            ids = []
            for j, point in enumerate(curve):
                pair = coordinate(point)
                # Only original endpoint positions join different track features.
                ids.append('rgi-end:' + str(pair) if pair in ends else identifier + ':' + str(start) + ':' + str(j))
            if len(set(ids)) < 2:
                continue
            ways.append({'node_ids': ids, 'coordinates': curve, 'speed': speed,
                         'source_track_id': identifier, 'line_code': code})
    return ways, dict(omitted)


def prepare(cache, output=OUTPUT):
    tracks, speed = cache / 'sncf-tracks.geojson', cache / 'sncf-speeds.json'
    raw, speeds = json.loads(tracks.read_text()), json.loads(speed.read_text())
    ways, omitted = compile_ways(raw['features'], speeds)
    positions = {}
    for way in ways:
        for node, point in zip(way['node_ids'], way['coordinates']):
            if node in positions and positions[node] != point:
                raise ValueError('Conflicting derived RFN node: ' + node)
            positions[node] = point
    result = {'metadata': {'source': 'SNCF Réseau · RFN track alignments and nominal line speeds',
        'source_url': 'https://www.data.gouv.fr/datasets/fichier-de-formes-des-voies-du-reseau-ferre-national',
        'source_date': 'Track extraction 2026-08-12; accessed 2026-10-19 Australia/Melbourne',
        'license': 'ODbL 1.0', 'license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
        'references': [{'file': tracks.name, 'source_url': TRACK_URL, 'sha256': file_hash(tracks)},
                       {'file': speed.name, 'source_url': SPEED_URL, 'sha256': file_hash(speed)}],
        'omitted': omitted, 'junction_method': 'Coincident original RFN segment endpoint and vertex coordinates, rounded to 7 decimals; no distance snapping or invented intersection.',
        'note': 'Inferred geographical alignments, not operational topology, exact running tracks or proof of historical diversions. Interior crossings remain separate. VPL/VPA retained; service tracks excluded. Curves simplified between preserved junctions.'}, 'ways': ways}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb') as f, gzip.GzipFile(filename='', fileobj=f, mode='wb', mtime=0) as stream:
        stream.write(json.dumps(result, separators=(',', ':'), allow_nan=False).encode())
    print('ways',len(ways),'bytes',output.stat().st_size,'sha256',file_hash(output),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/france')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    prepare(args.cache, args.output)
