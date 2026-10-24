"""Pinned domestic flight schedules adapted to the existing replay payload."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip
import json
import os

from dashboard.cities import replay_settings
from scripts.prepare_australian_flights import great_circle

DIRECTORY = Path(__file__).resolve().parents[1] / 'data/reference/australia_flights'
DEFAULT = DIRECTORY / '2026-11-02.json.gz'
AIRLINES = {'QF': ('Qantas', '#e53935'), 'VA': ('Virgin Australia', '#aa76db'),
            'JQ': ('Jetstar', '#f57c28'), 'ZL': ('Rex', '#439edd'),
            'FC': ('Link Airways', '#50b6a1'), 'QQ': ('Alliance Airlines', '#eab54d'),
            'FP': ('FlyPelican', '#a1c75b')}


def reference_path(business_date=None):
    default = DIRECTORY / '2013-03-04.json.gz' if business_date and business_date.startswith('2013-03-') else DEFAULT
    return Path(os.getenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE', str(default)))


def replay_day(business_date):
    from dashboard.replay import cumulative_distances
    with gzip.open(reference_path(business_date), 'rt') as stream:
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
        carrier = flight.get('carrier', 'JQ')
        operator, color = AIRLINES.get(carrier, (flight.get('airline', carrier), '#62b4b4'))
        services.append(dict(id=flight['id'], number=flight['number'], mode='flight', operator=operator,
            line=route, route_id=key, direction='Scheduled service', origin=a['name'], destination=b['name'],
            color=color, carrier=carrier, aircraft=flight.get('aircraft', 'Airbus A' + flight.get('equipment', '320')),
            operating_airline=flight.get('airline', operator), source_page=flight.get('source_page'),
            stops=[[origin, flight['departure'], flight['departure']], [destination, flight['arrival'], flight['arrival']]],
            legs=[key], timing_uncertain=False))
    return dict(**replay_settings('australia_flights'), business_date=business_date,
        start=start, end=end, initial=start + 10 * 3600, day_start_hour=0,
        services=services, stations=airports, paths=paths, geometry={},
        approximate_legs=0, total_legs=len(services), excluded_services=0,
        schedule={**reference['metadata'], 'available': True})
