"""Add the pinned May 2026 MRT timetable as an explicitly dated weekday overlay."""
from pathlib import Path
import gzip
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_rail_replay import prepare

COMMIT = 'c39d5b10ffc6a749363477ce7702425b719c1814'
FEED = ROOT / 'data/reference/jakarta/mrt-may-2026.zip'
SHA256 = '47fb971e1ac7842a68bacde88f6105f9512b5185767b0615cc98c7f5640255a0'
URL = f'https://raw.githubusercontent.com/MuhammadNafishZaldinanda/gtfs-mrt-jakarta/{COMMIT}/gtfs-mrt-jakarta.zip'
NOTE = 'KRL: December 2025 timetable. MRT: May 2026 snapshot matched by weekday/weekend, not a December 2025 reconstruction. Positions are scheduled estimates; passenger counts are unavailable.'


def departure_events(sequence, stops):
    # The upstream conversion subtracts an assumed 30-second dwell. Only its
    # published departure events are supported by the operator's tables.
    return [{**row, 'arrival_time': row['departure_time']} for row in sequence]


def build(output):
    source = {
        'first': '2025-12-15', 'last': '2025-12-21', 'timezone': 'Asia/Jakarta',
        'url': FEED.as_uri(), 'sha256': SHA256, 'captured': '2026-05-03', 'published': '2026-05-03',
        # Upstream's 2019–2030 calendar is a weekday template, not proof of
        # historical validity. Dates here are explicit overlay display dates.
        'calendar_validity': True, 'assign_by_start': ['subway'],
        'source': 'MRT Jakarta departures, community GTFS snapshot of 3 May 2026',
        'source_url': URL, 'license': 'MIT (community conversion); operator timetable rights retained',
        'license_url': f'https://github.com/MuhammadNafishZaldinanda/gtfs-mrt-jakarta/blob/{COMMIT}/LICENSE',
        'attribution': 'MRT Jakarta departure tables; GTFS conversion © 2026 Muhammad Nafish Zaldinanda (MIT). Railway geometry © OpenStreetMap contributors (ODbL 1.0). SunTrain uses departure events without assumed dwell times.',
        'geometry_source': 'OpenStreetMap MRT route geometry distributed in the community GTFS',
        'geometry_source_url': 'https://www.openstreetmap.org/copyright',
        'geometry_license': 'ODbL 1.0', 'geometry_license_url': 'https://opendatacommons.org/licenses/odbl/1-0/',
        'geometry_method': 'ordered_projection', 'note': NOTE,
    }
    prepare('jakarta-mrt', source, ROOT / '.cache/jakarta/mrt-build', output,
            lambda route, agencies: route['route_id'] == 'MRTJ_NS' and route['route_type'] == '1',
            lambda route, trip: {'mode': 'subway', 'operator': 'MRT Jakarta', 'line': 'MRT North–South',
                'route_id': 'MRTJ_NS', 'color': '#CA1F47',
                'destination': 'Blok M' if trip['shape_id'] == 'shape_LBB_BKM' else trip['trip_headsign'],
                'direction': 'Northbound' if trip['direction_id'] == '0' else 'Southbound'},
            select_sequence=departure_events)
    with gzip.open(output, 'rt') as stream:
        result = json.load(stream)
    result['metadata']['sources'][0]['source_url'] = URL
    result['metadata']['timetable_snapshot'] = '2026-05-03'
    result['metadata']['date_mapping'] = 'weekday/weekend overlay on the KRL week; December 2025 MRT validity is not established'
    if result['metadata']['omitted_trips'] or result['metadata']['unresolved_geometry_trips']:
        raise ValueError('MRT schedule/geometry omissions require inspection')
    return result
