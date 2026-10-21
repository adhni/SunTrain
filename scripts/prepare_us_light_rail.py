"""Add TRAX/S-Line, DART light rail and SPRINTER from existing pinned US feeds."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_american_replay import FIRST
from scripts.prepare_us_commuter_replay import SOURCES as COMMUTER_SOURCES, prepare as prepare_networks

SOURCES = {
    'trax': {**COMMUTER_SOURCES['frontrunner'], 'name': 'TRAX / S-Line', 'route_types': ['0'],
             'license': 'UTA published-data terms; operator rights retained'},
    'dart_light_rail': {**COMMUTER_SOURCES['dart'], 'name': 'DART light rail', 'route_types': ['0'],
                       'license': 'DART published-data terms; operator rights retained'},
    'sprinter': {**COMMUTER_SOURCES['coaster'], 'name': 'SPRINTER', 'route_types': ['0'],
                 'license': 'NCTD published-data terms; operator rights retained'},
}
NOTE = ('Optional TRAX Blue/Red/Green and S-Line, DART Blue/Green/Orange/Red, and NCTD SPRINTER, '
        '12–18 October 2026. All clocks use Eastern time; native agency times are converted once. '
        'Departures belong to one 03:00–03:00 Eastern window. Source route colours and railway shapes '
        'are retained; unsupported sections remain gaps. Other urban networks, buses and streetcars '
        'outside the selected S-Line are excluded. Scheduled estimates, not live positions or passenger loads.')


def prepare(cache, output):
    prepare_networks(cache, output, sources=SOURCES, mode='light_rail', note=NOTE,
        source_name='UTA, DART and NCTD historical light rail schedules',
        attribution='Timetable and supplied railway shapes: Utah Transit Authority, Dallas Area Rapid Transit '
                    'and North County Transit District. Dated UTA/DART archives: MobilityDatabase. NCTD feed '
                    'captured 21 October 2026. SunTrain selects rail services, shares schedules and converts '
                    'clocks to Eastern time. Source-specific terms apply; no operator endorsement.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/us-commuter')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/reference/us_rail' / ('light-rail-' + FIRST + '.json.gz'))
    args = parser.parse_args()
    prepare(args.cache, args.output)
