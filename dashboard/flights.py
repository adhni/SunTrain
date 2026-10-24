"""Pinned domestic flight schedules adapted to the existing replay payload."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import json
import os

from dashboard.cities import replay_settings
from scripts.prepare_australian_flights import great_circle

DEFAULT = Path(__file__).resolve().parents[1] / 'data/reference/australia_flights/2013-03-04.json.gz'


def reference_path():
    return Path(os.getenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE', str(DEFAULT)))


def replay_day(business_date):
    from dashboard.replay import cumulative_distances
    with gzip.open(reference_path(), 'rt') as stream:
        reference = json.load(stream)
    day = date.fromisoformat(business_date)
    zone = ZoneInfo('Australia/Melbourne')
    start = int(datetime.combine(day, time(), zone).timestamp())
    end = int(datetime.combine(day + timedelta(days=1), time(), zone).timestamp())
    airports = reference['airports']
    indices = {a['code']: i for i, a in enumerate(airports)}
    services, paths = [], {}
    for flight in reference['flights']:
        if flight['departure'] >= end or flight['arrival'] < start:
            continue
        origin, destination = indices[flight['origin']], indices[flight['destination']]
        a, b = airports[origin], airports[destination]
        route = f"{flight['origin']} → {flight['destination']}"
        key = flight['origin'] + '-' + flight['destination']
        if key not in paths:
            coordinates = great_circle([a['lon'], a['lat']], [b['lon'], b['lat']])
            paths[key] = dict(quality='illustrative', coordinates=coordinates, distances=cumulative_distances(coordinates))
        services.append(dict(id=flight['id'], number=flight['number'], mode='flight', operator='Jetstar',
            line=route, route_id=key, direction='Scheduled service', origin=a['name'], destination=b['name'],
            color='#F57C28', equipment=flight['equipment'], source_page=flight['source_page'],
            stops=[[origin, flight['departure'], flight['departure']], [destination, flight['arrival'], flight['arrival']]],
            legs=[key], timing_uncertain=False))
    return dict(**replay_settings('australia_flights'), business_date=business_date,
        start=start, end=end, initial=start + 10 * 3600, day_start_hour=0,
        services=services, stations=airports, paths=paths, geometry={},
        approximate_legs=0, total_legs=len(services), excluded_services=0,
        schedule={**reference['metadata'], 'available': True})
