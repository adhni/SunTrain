"""Prepare optional nationwide U-Bahn/Stadtbahn replay for 1–7 June 2026."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.london_rail_graph import RailGraph
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_germany_regional import mode_day
from scripts.prepare_germany_replay import SOURCE as LONG_DISTANCE
from scripts.prepare_rail_replay import prepare as prepare_rail

SCOPE = ROOT / 'data/reference/germany/ubahn-scope.json'
GEOMETRY = ROOT / 'data/reference/germany/ubahn-osm.json.gz'
GEOMETRY_SHA256 = 'ef1505da21f80b4d56ab4e1638342be859b0e3f2ad71f32392bb468f71704c0e'
SOURCE = {**LONG_DISTANCE,
    'url': 'https://files.mobilitydatabase.org/mdb-1090/mdb-1090-202605310128/mdb-1090-202605310128.zip',
    'sha256': 'bf1e06acc89fbe14cb584925e9a2338f21759e5d647752bfa310268570ddff3c',
    'source': 'DELFI e.V. / GTFS.de historical U-Bahn/Stadtbahn schedules via Mobility Database',
    'source_url': 'https://gtfs.de/en/feeds/de_nv/', 'assign_by_start': ['subway'],
    'attribution': 'Timetables: DELFI e.V. / GTFS.de · archive captured 31 May 2026. U-Bahn/Stadtbahn paths © OpenStreetMap contributors, matched and simplified by SunTrain.',
    'geometry_source': 'U-Bahn/Stadtbahn railway geometry © OpenStreetMap contributors',
    'geometry_source_url': 'https://www.openstreetmap.org/copyright',
    'geometry_license': 'ODbL 1.0', 'geometry_license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
    'geometry_source_date': 'See pinned geometry references for each OSM snapshot timestamp',
    'note': 'Optional German U-Bahn and associated Stadtbahn networks for the same June week. Explicit route scope excludes buses and ordinary tram networks. OSM paths are geographical railway estimates; unavailable sections remain gaps. No individual passenger counts.',
}


class LocalRailGraph(RailGraph):
    """Measure the 150 m station cutoff at each station's actual latitude."""
    def __init__(self, ways):
        super().__init__(ways)
        self.geographic_starts = self.starts / self.scale
        self.geographic_vectors = self.vectors / self.scale

    def anchors(self, point):
        key = tuple(point)
        if key not in self.anchor_cache:
            scale = np.array([math.cos(math.radians(point[1])), 1.0]) * 111195
            vectors = self.geographic_vectors * scale
            offset = (np.array(point) - self.geographic_starts) * scale
            fractions = np.clip(np.sum(offset * vectors, axis=1) / np.maximum(np.sum(vectors ** 2, axis=1), 1e-20), 0, 1)
            errors = np.linalg.norm(offset - fractions[:, None] * vectors, axis=1)
            candidates = sorted(np.where(errors <= 150)[0], key=lambda i: (errors[i], i))[:8]
            self.anchor_cache[key] = [(int(i), float(fractions[i]), float(errors[i]),
                (self.geographic_starts[i] + fractions[i] * self.geographic_vectors[i]).tolist()) for i in candidates]
        return self.anchor_cache[key]


def selected_route(route, agencies, scope):
    audited = scope.get(route.get('route_id'))
    return bool(audited and all(route.get(k) == audited[k] for k in ('agency_id', 'route_short_name', 'route_type'))
                and agencies.get(audited['agency_id'], {}).get('agency_name') == audited['agency_name'])


def describe_route(route, trip, scope, geographic):
    audited = scope[route['route_id']]
    line = geographic['lines'][route['agency_id'] + ':' + route['route_short_name']]
    return {'mode': 'subway', 'route_id': route['route_id'], 'route_short_name': route['route_short_name'],
        'line': audited['city'] + ' ' + route['route_short_name'], 'direction': 'Not specified',
        'color': route.get('route_color') or line.get('color') or '1565A8'}


def geometry_resolver(geographic):
    graphs = {}

    def resolve(route, trip, sequence, coordinates):
        key = route['agency_id'] + ':' + route['route_short_name']
        ways = geographic['lines'][key]['ways']
        if not ways:
            return [None] * (len(coordinates) - 1)
        if key not in graphs:
            graphs[key] = LocalRailGraph(ways)
        curves = []
        for a, b in zip(coordinates, coordinates[1:]):
            curve = graphs[key].leg(a, b)
            if curve and cumulative_distances(curve)[-1] > max(3000, 3 * cumulative_distances([a, b])[-1]):
                curve = None
            curves.append(curve)
        return curves
    return resolve


def prepare(cache, output, geometry=GEOMETRY):
    if file_hash(geometry) != GEOMETRY_SHA256:
        raise ValueError('U-Bahn geometry differs from the validated reference')
    with gzip.open(geometry, 'rt') as stream:
        geographic = json.load(stream)
    scope = json.loads(SCOPE.read_text())
    if scope['source_gtfs_sha256'] != SOURCE['sha256']:
        raise ValueError('U-Bahn scope belongs to another archive')
    weekly = cache / 'ubahn-week.json.gz'
    prepare_rail('germany-ubahn', {**SOURCE, 'geometry_sha256': GEOMETRY_SHA256,
                 'geometry_references': geographic['metadata']['references']}, cache, weekly,
                 lambda route, agencies: selected_route(route, agencies, scope['routes']),
                 lambda route, trip: describe_route(route, trip, scope['routes'], geographic),
                 geometry_resolver=geometry_resolver(geographic))
    with gzip.open(weekly, 'rt') as stream:
        reference = json.load(stream)
    reference['metadata']['route_scope_sha256'] = file_hash(SCOPE)
    operators = sorted({p['operator'] for p in reference['patterns'].values()})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'ubahn-operators.json').write_text(json.dumps(operators, ensure_ascii=False, indent=2) + '\n')
    for day in reference['days']:
        result = mode_day(reference, day, 'subway', prefix='de-nv-subway-')
        filename = output / 'subway' / (day + '.json.gz')
        save_reference(result, filename)
        print(day, len(result['days'][day]), filename.stat().st_size, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/germany')
    parser.add_argument('--geometry', type=Path, default=GEOMETRY)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/germany')
    args = parser.parse_args()
    prepare(args.cache, args.output, args.geometry)
