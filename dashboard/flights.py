"""Pinned domestic flight schedules adapted to the existing replay payload."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
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
            'FP': ('FlyPelican', '#a1c75b'),
            'GA': ('Garuda Indonesia', '#439edd'), 'QG': ('Citilink', '#63b547'),
            'JT': ('Lion Air', '#e53935'), 'ID': ('Batik Air', '#aa76db'),
            'IW': ('Wings Air', '#f57c28'), 'IU': ('Super Air Jet', '#bb965f'),
            'QZ': ('Indonesia AirAsia', '#ef647b'), 'SJ': ('Sriwijaya Air', '#eab54d'),
            'IN': ('NAM Air', '#50b6a1'), 'IL': ('Trigana Air', '#d88bd6'),
            '8B': ('TransNusa', '#5ba4c6'), 'IP': ('Pelita Air', '#9ca8e7')}


def airline_style(carrier, name):
    palette = ('#62b4b4', '#d58b68', '#9ba9da', '#d3b85f', '#ba8fc4')
    index = int(hashlib.sha256(carrier.encode()).hexdigest()[:8], 16) % len(palette)
    return AIRLINES.get(carrier, (name or carrier, palette[index]))


def reference_path(business_date=None, city='australia_flights'):
    if city == 'indonesia_flights':
        return Path(os.getenv('SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE', str(DIRECTORY.parent / 'indonesia_flights/2026-11-02.json.gz')))
    if city != 'australia_flights':
        raise ValueError(f'Unknown flight country: {city}')
    default = DIRECTORY / '2013-03-04.json.gz' if business_date and business_date.startswith('2013-03-') else DEFAULT
    return Path(os.getenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE', str(default)))


def replay_day(business_date, city='australia_flights'):
    from dashboard.replay import cumulative_distances
    with gzip.open(reference_path(business_date, city), 'rt') as stream:
        reference = json.load(stream)
    day = date.fromisoformat(business_date)
    zone = ZoneInfo(replay_settings(city)['timezone'])
    start = int(datetime.combine(day, time(), zone).timestamp())
    end = int(datetime.combine(day + timedelta(days=1), time(), zone).timestamp())
    airports = reference['airports']
    indices = {a['code']: i for i, a in enumerate(airports)}
    services, paths = [], {}
    for flight in reference['flights']:
        # Retain arrivals exactly at midnight so the new day's arrival board owns them.
        if flight['departure'] >= end or flight['arrival'] < start:
            continue
        origin, destination = indices[flight['origin']], indices[flight['destination']]
        a, b = airports[origin], airports[destination]
        route = f"{flight['origin']} → {flight['destination']}"
        key = flight['origin'] + '-' + flight['destination']
        if key not in paths:
            coordinates = great_circle([a['lon'], a['lat']], [b['lon'], b['lat']])
            paths[key] = dict(quality='illustrative', coordinates=coordinates, distances=cumulative_distances(coordinates))
        carrier = flight.get('carrier') or ('JQ' if city == 'australia_flights' else 'Unknown')
        operator, color = airline_style(carrier, flight.get('airline'))
        services.append(dict(id=flight['id'], number=flight['number'], mode='flight', operator=operator,
            line=route, route_id=key, direction='Scheduled service', origin=a['name'], destination=b['name'],
            color=color, carrier=carrier, aircraft=flight.get('aircraft') or ('Airbus A' + flight['equipment'] if flight.get('equipment') else 'Aircraft not specified'),
            operating_airline=flight.get('airline', operator), source_page=flight.get('source_page'),
            stops=[[origin, flight['departure'], flight['departure']], [destination, flight['arrival'], flight['arrival']]],
            legs=[key], timing_uncertain=False))
    return dict(**replay_settings(city), business_date=business_date,
        start=start, end=end, initial=start + 10 * 3600, day_start_hour=0,
        services=services, stations=airports, paths=paths, geometry={},
        approximate_legs=0, total_legs=len(services), excluded_services=0,
        schedule={**reference['metadata'], 'available': True})
