"""Pinned flight schedules adapted to the existing replay payload."""
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import gzip
import json
import os

from dashboard.cities import replay_settings
from dashboard.flight_profiles import BY_CITY as PROFILE_CITIES, load_domestic as load_profile_domestic
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
            '8B': ('TransNusa', '#5ba4c6'), 'IP': ('Pelita Air', '#9ca8e7'),
            'OD': ('Batik Air (OD)', '#c58cb6'),
            'SQ': ('Singapore Airlines', '#e5b748'), 'EK': ('Emirates', '#d94e54'),
            'NZ': ('Air New Zealand', '#65b7ad'), 'QR': ('Qatar Airways', '#b57f9c'),
            'CX': ('Cathay Pacific', '#54aa93'), 'UA': ('United', '#649ce0'),
            'AA': ('American', '#a0afc6'), 'DL': ('Delta', '#cf7b89'),
            'WN': ('Southwest Airlines', '#e8bd54'), 'B6': ('JetBlue', '#79a6dd'),
            'F9': ('Frontier Airlines', '#74b58a'), 'XE': ('JSX', '#b98ad2'),
            'AS': ('Alaska Airlines', '#74bbc0'),
            'SY': ('Sun Country Airlines', '#d99763'), 'G4': ('Allegiant Air', '#9b91cf'),
            'MX': ('Breeze Airways', '#6cc6d6'),
            'AC': ('Air Canada', '#dc747c'), 'WS': ('WestJet', '#63b5aa'),
            'TS': ('Air Transat', '#6b9ed5'), 'PD': ('Porter Airlines', '#b5a282'),
            'F8': ('Flair Airlines', '#9bbb5c'), 'AM': ('Aeromexico', '#8a9dd2'),
            'Y4': ('Volaris', '#b88ad1'), 'VB': ('Viva', '#7fbe78'),
            '4N': ('Air North', '#be9b70'),
            '8P': ('Pacific Coastal Airlines', '#7eaec9'), '5T': ('Canadian North', '#c39471'),
            'P6': ('Pascan', '#b58dca'), 'YB': ('Harbour Air', '#dcac5f'),
            '9M': ('Central Mountain Air', '#7caf92'), '3H': ('Air Inuit', '#d38eab'),
            'PB': ('PAL Airlines', '#8b9dd3'), 'DU': ('Air Liaison', '#b1b16c'),
            'YN': ('Air Creebec', '#bf9977'), 'MO': ('Calm Air', '#73b8bb'),
            '8T': ('Air Tindi', '#a794c7'),
            'XN': ('Mexicana', '#9ab5a1'),
            'CM': ('Copa Airlines', '#749fd0'), 'AV': ('Avianca', '#dc7c89'),
            'DM': ('Arajet', '#a38ad4'), 'Q6': ('Volaris Costa Rica', '#bd85c4'),
            'WU': ('Western Air', '#b197d0'), 'S6': ('Sunrise Airways', '#e5a45b'),
            'UP': ('Bahamasair', '#65b5bb'), 'N3': ('Volaris El Salvador', '#a98ccd'),
            'AR': ('Aerolineas Argentinas', '#78b4d5'),
            'LA': ('LATAM', '#ac89c8'), 'G3': ('Gol', '#df9b66'),
            'AD': ('Azul', '#6da9ce'),
            'JA': ('JetSMART', '#de7d86'), 'H2': ('Sky Airline', '#9ebd60'),
            'FO': ('Flybondi', '#dfc15c'), 'P5': ('Wingo', '#b191ce'),
            'OB': ('BoA', '#7e9bc7'), 'VE': ('Clic', '#c89863'),
            'FJ': ('Fiji Airways', '#b9956e'),
            'PX': ('Air Niugini', '#d99855'), 'CG': ('PNG Air', '#c57890'),
            'VT': ('Air Tahiti', '#e47c94'), 'TN': ('Air Tahiti Nui', '#60bbcf'),
            'SB': ('Aircalin', '#8e9bdd'), 'TY': ('Air Caledonie', '#e9af62'),
            'IE': ('Solomon Airlines', '#85b46c'), 'NF': ('Air Vanuatu', '#79b7ab'),
            'OL': ('Samoa Airways', '#b797cf'), 'GZ': ('Air Rarotonga', '#6bb5c5'),
            'NM': ('Air Moana', '#65a9dd'), 'ON': ('Nauru Airlines', '#b7a266'),
            '3C': ('Air Chathams', '#a3b773'), '9X': ('Southern Airways Express', '#8dbab0'), 'TR': ('Scoot', '#e5c547'),
            'KC': ('Air Astana', '#8c99cf'), 'FS': ('FlyArystan', '#df777f'),
            'DV': ('SCAT', '#e3b65e'), 'IQ': ('Vietjet Qazaqstan', '#d58c82'),
            'HY': ('Uzbekistan Airways', '#60b4c6'), 'HH': ('Qanot Sharq', '#d181a9'),
            'C6': ('Centrum Air', '#91b970'), 'SZ': ('Somon Air', '#c0a15c'),
            'YK': ('Avia Traffic Company', '#ab98d2'), 'UH': ('Silk Avia', '#71b6ab'),
            'MH': ('Malaysia Airlines', '#7c9ada'), 'TG': ('THAI', '#b690d9'), 'AK': ('AirAsia', '#e95055'),
            'FY': ('Firefly', '#ef9b48'), 'MY': ('AirBorneo', '#53b6aa'),
            'D7': ('AirAsia X', '#c75668'), 'BI': ('Royal Brunei', '#bca64b'),
            'EY': ('Etihad Airways', '#bd9d61'), 'FZ': ('flydubai', '#ee9353'),
            '3L': ('Air Arabia Abu Dhabi', '#df8078'),
            '6E': ('IndiGo', '#6996e5'), 'AI': ('Air India', '#e66767'),
            'IX': ('Air India Express', '#f49b50'), 'QP': ('Akasa Air', '#b18bdd'),
            'SG': ('SpiceJet', '#efbd4f'), '9I': ('Alliance Air', '#60b7ac'),
            'S5': ('Star Air', '#df90b3'), 'S9': ('FlyBig', '#89b951'),
            'IC': ('Fly91', '#b89162'),
            'KE': ('Korean Air', '#75b9df'), 'OZ': ('Asiana Airlines', '#c98b9c'),
            '7C': ('Jeju Air', '#f3a450'), 'LJ': ('Jin Air', '#a5c94e'),
            'BX': ('Air Busan', '#67a8e1'), 'RS': ('Air Seoul', '#57c3ab'),
            'ZE': ('Eastar Jet', '#e46d7b'), 'RF': ('Aero K', '#8b97df'),
            'JL': ('Japan Airlines', '#e76b75'), 'NH': ('ANA', '#679fe1'),
            'BC': ('Skymark Airlines', '#e3bd54'), 'MM': ('Peach', '#cc87c2'),
            'GK': ('Jetstar Japan', '#ed9a52'), 'HD': ('AIRDO', '#74c9dc'),
            '6J': ('Solaseed Air', '#a7c85c'), '7G': ('StarFlyer', '#a3acc4'),
            'IJ': ('Spring Japan', '#69bd8b'), 'NU': ('Japan Transocean Air', '#dc91a7'),
            'FW': ('IBEX Airlines', '#aa94d8'), 'JH': ('Fuji Dream Airlines', '#cf9a69'),
            'OC': ('Oriental Air Bridge', '#64bba9'), 'MZ': ('Amakusa Airlines', '#b8a77b'),
            'CA': ('Air China', '#dc7375'), 'MU': ('China Eastern', '#789edc'),
            'CZ': ('China Southern', '#63b6d4'), 'HU': ('Hainan Airlines', '#dfa967'),
            'ZH': ('Shenzhen Airlines', '#c58cae'), 'MF': ('XiamenAir', '#73bda7'),
            '3U': ('Sichuan Airlines', '#e18c7b'), 'FM': ('Shanghai Airlines', '#bb99d8'),
            '9C': ('Spring Airlines', '#9bc65b'), 'HO': ('Juneyao Air', '#bd93b3'),
            'KN': ('China United Airlines', '#a6b5db'), 'GS': ('Tianjin Airlines', '#c2ad71'),
            'JD': ('Beijing Capital Airlines', '#d195a1'), 'SC': ('Shandong Airlines', '#91b7d0'),
            'PN': ('West Air', '#bbaf62'), 'OQ': ('Chongqing Airlines', '#a0bf92'),
            'TV': ('Tibet Airlines', '#c19cc3'), 'EU': ('Chengdu Airlines', '#d29b71'),
            'GJ': ('Loong Air', '#83b9b8'), 'KY': ('Kunming Airlines', '#b5a9d3'),
            'QW': ('Qingdao Airlines', '#7fae9d'), 'UQ': ('Urumqi Air', '#c4a683'),
            'AQ': ('9 Air', '#b7bb71'),
            'PG': ('Bangkok Airways', '#78b4d8'),
            'FD': ('Thai AirAsia', '#e88087'), 'SL': ('Thai Lion Air', '#dc9c78'),
            'VZ': ('Thai Vietjet Air', '#d8bb65'), 'DD': ('Nok Air', '#dfc968'),
            'PR': ('Philippine Airlines', '#749edb'), '2P': ('PAL Express', '#9ab6e0'), '5J': ('Cebu Pacific', '#dfc968'),
            'DG': ('Cebgo', '#97bf79'), 'Z2': ('Philippines AirAsia', '#e88087'),
            '2R': ('Sunlight Air', '#72b9c8'),
            'VN': ('Vietnam Airlines', '#68a8c7'), 'VJ': ('Vietjet Air', '#e7837b'),
            'QH': ('Bamboo Airways', '#7db78c'), 'VU': ('Vietravel Airlines', '#d5bc66'),
            'BL': ('Pacific Airlines', '#d79c77'),
            'K6': ('Air Cambodia', '#b596d8'), 'ZA': ('Sky Angkor Airlines', '#dfaa70'),
            'KR': ('Cambodia Airways', '#79b3c8'), 'QV': ('Lao Airlines', '#73b69b'),
            'LK': ('Lao Skyway', '#d3bd71'), '8M': ('Myanmar Airways International', '#91a6d9'),
            'UB': ('Myanmar National Airlines', '#bf99c3'), 'TL': ('Airnorth', '#9aabd8'),
            'CI': ('China Airlines', '#c690bb'), 'BR': ('EVA Air', '#6db597'),
            'JX': ('STARLUX Airlines', '#b5a276'), 'IT': ('Tigerair Taiwan', '#dfbe62'),
            'B7': ('UNI Air', '#8ebe7e'), 'AE': ('Mandarin Airlines', '#b39dc9'),
            'HX': ('Hong Kong Airlines', '#cf838b'), 'UO': ('HK Express', '#b197d6'),
            'HB': ('Greater Bay Airlines', '#79b8ca'),
            'U4': ('Buddha Air', '#77b99d'), 'YT': ('Yeti Airlines', '#b3c97b'),
            'N9': ('Shree Airlines', '#d9a56e'), 'RA': ('Nepal Airlines', '#d9818a'),
            'H9': ('Himalaya Airlines', '#94a5d7'),
            'ET': ('Ethiopian', '#77b88b'), 'KQ': ('Kenya Airways', '#dc7b83'),
            'MS': ('EgyptAir', '#81a7dc'), 'AT': ('Royal Air Maroc', '#d68b9c'),
            'FA': ('FlySafair', '#d78fbc'), '4Z': ('Airlink', '#9daee0'),
            'SA': ('South African', '#d2b66d'), 'WB': ('RwandAir', '#83b9d4'),
            'P4': ('Air Peace', '#86a9df'), 'HF': ("Air Cote D'Ivoire", '#dfad70'),
            'MK': ('Air Mauritius', '#d77f91'), 'HM': ('Air Seychelles', '#74b9ae'),
            'TC': ('Air Tanzania', '#9cbf79'), 'HC': ('Air Senegal', '#c9b16d'),
            'AH': ('Air Algerie', '#cf929d'), 'TU': ('Tunisair', '#d88782'),
            'WY': ('Oman Air', '#5daea8'), 'OV': ('SalamAir', '#9dbd65'),
            'KU': ('Kuwait Airways', '#77acd6'), 'J9': ('Jazeera Airways', '#7c96bd'),
            'GF': ('Gulf Air', '#b2a175'), 'RJ': ('Royal Jordanian', '#cc858d'),
            'PK': ('Pakistan International Airlines', '#65ab91'), 'PA': ('airblue', '#77a8d7'),
            '9P': ('Fly Jinnah', '#dd8a8c'), 'PF': ('Air Sial', '#b799ce'),
            'ER': ('SereneAir', '#79b7c3'), 'BG': ('Biman', '#cf8b92'),
            'BS': ('US-Bangla Airlines', '#789ed0'), 'VQ': ('NOVOAIR', '#ac94cc'),
            '2A': ('Air Astra', '#dcac65'),
            'SV': ('Saudia', '#67b28b'), 'XY': ('flynas', '#57bfc0'),
            'F3': ('flyadeal', '#b08bce'),
            'TK': ('Turkish Airlines', '#dd7b82'), 'PC': ('Pegasus', '#d9b84f'),
            'VF': ('AJet', '#73b6cf'), 'XQ': ('SunExpress', '#d69e61')}


def airline_style(carrier, name):
    palette = ('#62b4b4', '#d58b68', '#9ba9da', '#d3b85f', '#ba8fc4')
    index = int(hashlib.sha256(carrier.encode()).hexdigest()[:8], 16) % len(palette)
    if carrier == 'MY':
        return (name or AIRLINES[carrier][0], AIRLINES[carrier][1])
    return AIRLINES.get(carrier, (name or carrier, palette[index]))


def reference_path(business_date=None, city='australia_flights'):
    if city=='europe_flights':
        from dashboard.europe_flights import reference_path as europe_path
        return europe_path()
    if city in PROFILE_CITIES:
        _,p=PROFILE_CITIES[city]
        if not p['domestic']:
            from dashboard.international_network import reference_path as network_path
            return network_path()
        return Path(os.getenv(f"SUNTRAIN_{p['slug'].upper()}_FLIGHTS_REFERENCE",str(DIRECTORY.parent/f"{p['slug']}_flights/2026-11-02.json.gz")))
    if city=='vietnam_flights':
        return Path(os.getenv('SUNTRAIN_VIETNAM_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'vietnam_flights/2026-11-02.json.gz')))
    if city=='philippines_flights':
        return Path(os.getenv('SUNTRAIN_PHILIPPINES_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'philippines_flights/2026-11-02.json.gz')))
    if city=='thailand_flights':
        return Path(os.getenv('SUNTRAIN_THAILAND_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'thailand_flights/2026-11-02.json.gz')))
    if city=='international_network':
        from dashboard.international_network import reference_path as network_path
        return network_path()
    if city=='china_flights':
        return Path(os.getenv('SUNTRAIN_CHINA_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'china_flights/2026-11-02.json.gz')))
    if city=='japan_flights':
        return Path(os.getenv('SUNTRAIN_JAPAN_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'japan_flights/2026-11-02.json.gz')))
    if city=='south_korea_flights':
        return Path(os.getenv('SUNTRAIN_SOUTH_KOREA_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'south_korea_flights/2026-11-02.json.gz')))
    if city=='india_flights':
        return Path(os.getenv('SUNTRAIN_INDIA_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'india_flights/2026-11-02.json.gz')))
    if city=='singapore_flights':
        return Path(os.getenv('SUNTRAIN_SINGAPORE_FLIGHTS_REFERENCE',str(DIRECTORY.parent/'singapore_flights/2026-11-02.json.gz')))
    if city=='gulf_flights':
        from dashboard.gulf_flights import reference_paths as hub_paths
        return hub_paths(business_date)[0]
    if city == 'malaysia_flights':
        return Path(os.getenv('SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE', str(DIRECTORY.parent / 'malaysia_flights/2026-11-02.json.gz')))
    if city == 'indonesia_flights':
        return Path(os.getenv('SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE', str(DIRECTORY.parent / 'indonesia_flights/2026-11-02.json.gz')))
    if city != 'australia_flights':
        raise ValueError(f'Unknown flight country: {city}')
    default = DIRECTORY / '2013-03-04.json.gz' if business_date and business_date.startswith('2013-03-') else DEFAULT
    return Path(os.getenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE', str(default)))


def reference_paths(business_date=None, city='australia_flights', include_network=True):
    if city in PROFILE_CITIES and not PROFILE_CITIES[city][1]['domestic']:return [reference_path(business_date,city)]
    paths = _reference_paths(business_date,city)
    from dashboard.international_network import enabled, reference_path as network_path
    if include_network and enabled(business_date,city):paths.append(network_path())
    return paths


def _reference_paths(business_date=None, city='australia_flights'):
    if city=='europe_flights':return [reference_path(business_date,city)]
    if city=='international_network':return [reference_path(business_date,city)]
    if city=='gulf_flights':
        from dashboard.gulf_flights import reference_paths as hub_paths
        return hub_paths(business_date)
    if city in PROFILE_CITIES:return [reference_path(business_date,city)]
    paths = [reference_path(business_date, city)]
    if city in {'singapore_flights','south_korea_flights','japan_flights','china_flights','thailand_flights','philippines_flights','vietnam_flights'}:return paths
    prefix = {'indonesia_flights':'INDONESIA','australia_flights':'AUSTRALIA','malaysia_flights':'MALAYSIA','india_flights':'INDIA'}[city]
    # The legacy March 2013 Australian snapshot remains isolated.
    if not (city == 'australia_flights' and business_date and business_date.startswith('2013-03-')):
        override = os.getenv(f'SUNTRAIN_{prefix}_INTERNATIONAL_REFERENCE')
        # A custom domestic fixture is isolated unless international data is explicit.
        if override or not os.getenv(f'SUNTRAIN_{prefix}_FLIGHTS_REFERENCE'):
            international = Path(override or reference_path(business_date, city).with_name('2026-11-02-international.json.gz'))
            if override or international.exists():
                paths.append(international)
    return paths


def snapshot_coverage(reference):
    queries = reference['metadata'].get('queries', [])
    missing = reference['metadata'].get('uncollected_queries', [])
    pairs = {(q['origin'], q['destination']) for q in queries}
    planned = pairs | {(a, b) for _, a, b in missing}
    represented = {f[k] for f in reference['flights'] for k in ('origin', 'destination')}
    return dict(candidate_airports=len({c for pair in planned for c in pair} | represented), airports_returned=len(represented),
        airports_planned=len({c for pair in planned for c in pair}),
        airports_searched=len({c for pair in pairs for c in pair}),
        routes_planned=len(planned), routes_searched=len(pairs),
        routes_with_search_results=len({(q['origin'],q['destination']) for q in queries if q.get('status')=='results'}),
        routes_returned=len({(f['origin'],f['destination']) for f in reference['flights']}),
        queries_planned=len(queries)+len(missing), queries_captured=len(queries),
        queries_not_returned=sum(q.get('status')=='no_matching_direct_flights' for q in queries),
        failed_or_missing_queries=len(missing), unattempted_queries=len(missing), failed_queries=0)


def continuous_arc(a, b, anchor=135):
    """Keep Pacific flights continuous instead of interpolating across the world.

    Use Australia's world copy for both directions so reverse frequency arcs align.
    Longitudes beyond 180 are intentional and supported by MapLibre world copies.
    """
    points = great_circle(a, b)
    previous = anchor
    for point in points:
        point[0] += 360 * round((previous - point[0]) / 360)
        previous = point[0]
    return points


def load_reference(business_date, city):
    if city=='europe_flights':
        from dashboard.europe_flights import load_reference as europe_reference
        return europe_reference(business_date)
    from dashboard.international_network import enabled,load_archive,project,overlay
    if city=='international_network' or (city in PROFILE_CITIES and not PROFILE_CITIES[city][1]['domestic']):return project(load_archive(),city)
    reference=_load_reference(business_date,city)
    return overlay(reference,city) if enabled(business_date,city) else reference


def _load_reference(business_date, city):
    if city in PROFILE_CITIES:return load_profile_domestic(reference_path(business_date,city),PROFILE_CITIES[city][0])
    if city=='gulf_flights':
        from dashboard.gulf_flights import load_reference as hub_reference
        return hub_reference(business_date)
    references = []
    for path in reference_paths(business_date, city, include_network=False):
        with gzip.open(path, 'rt') as stream:
            references.append(json.load(stream))
    country = {'indonesia_flights':'ID','australia_flights':'AU','malaysia_flights':'MY','singapore_flights':'SG','india_flights':'IN','south_korea_flights':'KR','japan_flights':'JP','china_flights':'CN','thailand_flights':'TH','philippines_flights':'PH','vietnam_flights':'VN'}[city]
    airports, flights = {}, {}
    for reference in references:
        if country in {'SG','IN','KR','JP','CN','TH','PH','VN'}:
            context=reference['metadata'].get('fare_context',{})
            if tuple(context.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way'):
                label={'SG':'Singapore','IN':'Indian','KR':'South Korean','JP':'Japanese','CN':'Chinese','TH':'Thai','PH':'Philippine','VN':'Vietnamese'}[country]
                raise ValueError(f'{label} fares require USD, one adult, economy, one-way')
        catalogue = {a['code']: {**a, 'country': a.get('country', country)} for a in reference['airports']}
        for code, airport in catalogue.items():
            if code in airports and airports[code] != airport:
                raise ValueError(f'Conflicting airport identity: {code}')
            airports[code] = airport
        for flight in reference['flights']:
            a, b = catalogue[flight['origin']], catalogue[flight['destination']]
            if country=='SG':
                if not ({flight['origin'],flight['destination']} & {'SIN','XSP'}):
                    raise ValueError('Singapore flight must touch SIN or XSP')
                price=flight.get('price')
                if price and (price.get('currency')!='USD' or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
                    raise ValueError('Singapore prices require positive USD minor units; no implicit conversion')
            if country in {'IN','KR','JP','CN','TH','PH','VN'}:
                price=flight.get('price')
                if price and (tuple(price.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way') or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
                    label={'IN':'Indian','KR':'South Korean','JP':'Japanese','CN':'Chinese','TH':'Thai','PH':'Philippine','VN':'Vietnamese'}[country]
                    raise ValueError(f'{label} prices require positive USD minor units, one adult, economy, one-way; no implicit conversion')
            scope = 'domestic' if a['country'] == b['country'] == country else 'international'
            if country=='KR' and (scope!='domestic' or {flight['origin'],flight['destination']} & {'ICN','MWX'}):
                raise ValueError('South Korean domestic snapshot excludes foreign, transit-only and closed airports')
            if country=='VN' and (scope!='domestic' or a['timezone']!='Asia/Ho_Chi_Minh' or b['timezone']!='Asia/Ho_Chi_Minh'):
                raise ValueError('Vietnamese domestic snapshot requires two Vietnamese airports using Asia/Ho_Chi_Minh')
            if country=='PH' and (scope!='domestic' or a['timezone']!='Asia/Manila' or b['timezone']!='Asia/Manila'):
                raise ValueError('Philippine domestic snapshot requires two Philippine airports using Asia/Manila')
            if country=='TH' and (scope!='domestic' or a['timezone']!='Asia/Bangkok' or b['timezone']!='Asia/Bangkok'):
                raise ValueError('Thai domestic snapshot requires two Thai airports using ICT')
            if country=='JP' and scope!='domestic':
                raise ValueError('Japanese domestic snapshot excludes foreign airports')
            if country=='CN' and (scope!='domestic' or a['timezone']!='Asia/Shanghai' or b['timezone']!='Asia/Shanghai'):
                raise ValueError('Mainland Chinese domestic snapshot requires two mainland airports using China standard time')
            if scope == 'international' and (a['country'] == country) == (b['country'] == country):
                raise ValueError('Flight has no national endpoint')
            if reference['metadata'].get('scope') == 'international' and scope != 'international':
                raise ValueError('International reference contains a domestic flight')
            if reference['metadata'].get('scope')=='domestic' and scope!='domestic':
                raise ValueError('Domestic reference contains an international flight')
            record = {**flight, 'flight_scope': scope}
            if flight['id'] in flights and flights[flight['id']] != record:
                raise ValueError('Conflicting flight identity')
            flights[flight['id']] = record
    metadata = dict(references[0]['metadata'])
    if city in {'indonesia_flights', 'australia_flights', 'malaysia_flights','india_flights'}:
        coverages = {r['metadata'].get('scope', 'domestic'): r['metadata'].get('coverage') or snapshot_coverage(r) for r in references}
        if len(references) > 1:
            combined = {key: sum(c.get(key, 0) for c in coverages.values()) for key in (
                'routes_planned', 'routes_searched', 'routes_with_search_results', 'routes_returned',
                'queries_planned', 'queries_captured', 'queries_not_returned', 'queries_rejected',
                'rejected_records', 'failed_or_missing_queries', 'failed_queries', 'unattempted_queries')}
            queries = [q for r in references for q in r['metadata'].get('queries', [])]
            missing = [q for r in references for q in r['metadata'].get('uncollected_queries', [])]
            failed = [q for r in references for q in r['metadata'].get('failed_queries', [])]
            searched = {q[k] for q in queries + failed for k in ('origin', 'destination')}
            planned = searched | {code for _, a, b in missing for code in (a, b)}
            combined.update(airports_returned=len(airports), airports_searched=len(searched),
                airports_planned=len(planned), candidate_airports=(len(planned | set(airports)) if country in {'AU','MY','IN'} else
                coverages.get('domestic', {}).get('candidate_airports', 0)
                + coverages.get('international', {}).get('candidate_foreign_airports', 0)))
            coverages['both'] = combined
            metadata['replay_note'] = ('Indonesian domestic and international flight schedules for 2–8 November 2026. Timeline: WIB; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                if country == 'ID' else 'Australian domestic and international flight schedules for 2 November 2026. Timeline: Melbourne time; airport boards use local time. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.')
            if country in {'MY','IN'}:
                metadata['replay_note']='Malaysian domestic and international flight schedules for 2 November 2026. Timeline: MYT; airport boards use local time. Prices are captured one-adult economy one-way quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                if country=='IN':
                    metadata['scope']='both'
                    metadata['replay_note']='Indian domestic and international flight schedules for 2 November 2026. Timeline: IST; airport boards use local time. Prices are captured one-adult economy one-way USD quotes, not live fares. Search coverage is partial; some flights may be absent. Paths are illustrative, not recorded flight tracks.'
                metadata['priced_flights']=sum('price' in f for f in flights.values())
                metadata['priced_flights_by_scope']={r['metadata'].get('scope','domestic'):r['metadata'].get('priced_flights',0) for r in references}
                metadata['fare_context_unverified_queries']=sum(r['metadata'].get('fare_context_unverified_queries',0) for r in references)
            metadata['queries'] = queries
            metadata['uncollected_queries'] = missing
            metadata['failed_queries'] = failed
            metadata['unresolved_airports'] = [a for r in references for a in r['metadata'].get('unresolved_airports', [])]
            metadata['airlines'] = sorted({f.get('airline', f.get('carrier', 'Unknown')) for f in flights.values()})
            metadata['source_dates_by_scope'] = {r['metadata'].get('scope', 'domestic'): r['metadata'].get('source_date') for r in references}
            metadata['source_date'] = max((value for value in metadata['source_dates_by_scope'].values() if value), default=None)
            metadata['coverage'] = combined
        coverages.setdefault('both', coverages.get('domestic', {}))
        metadata['coverage_by_scope'] = coverages
    return dict(airports=list(airports.values()), flights=list(flights.values()), metadata=metadata)


def replay_day(business_date, city='australia_flights'):
    from dashboard.replay import cumulative_distances
    reference = load_reference(business_date, city)
    day = date.fromisoformat(business_date)
    zone = ZoneInfo(replay_settings(city)['timezone'])
    start = int(datetime.combine(day, time(), zone).timestamp())
    end = int(datetime.combine(day + timedelta(days=1), time(), zone).timestamp())
    if city in PROFILE_CITIES and PROFILE_CITIES[city][1].get('origin_local_day'):
        # Bound all origin-local days, including Atlantic midnight departures
        # before Eastern midnight and western overnight arrivals.
        starts=[int(datetime.combine(day,time(),ZoneInfo(a.get('replay_timezone',a['timezone']))).timestamp()) for a in reference['airports']]
        start=min(starts,default=start)
        ends=[int(datetime.combine(day+timedelta(days=1),time(),ZoneInfo(a.get('replay_timezone',a['timezone']))).timestamp()) for a in reference['airports']]
        end=max([end,*ends,*[f['arrival']+1 for f in reference['flights']]])
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
            coordinates = continuous_arc([a['lon'], a['lat']], [b['lon'], b['lat']],anchor=PROFILE_CITIES.get(city,(None,{}))[1].get('arc_anchor',135))
            paths[key] = dict(quality='illustrative', coordinates=coordinates, distances=cumulative_distances(coordinates))
        carrier = flight.get('carrier') or ('JQ' if city == 'australia_flights' else 'Unknown')
        operator, color = airline_style(carrier, flight.get('airline'))
        if city=='europe_flights':
            from dashboard.europe_flights import COLORS,BRAND_GROUPS
            color=COLORS[flight['brand']]
        services.append(dict(id=flight['id'], number=flight['number'], mode='flight', operator=operator,
            line=route, route_id=key, direction='Scheduled service', origin=a['name'], destination=b['name'],
            color=color, carrier=carrier, flight_scope=flight['flight_scope'], aircraft=flight.get('aircraft') or ('Airbus A' + flight['equipment'] if flight.get('equipment') else 'Aircraft not specified'),
            operating_airline=flight.get('airline', operator), source_page=flight.get('source_page'),
            **({'flight_brand':flight['brand']} if flight.get('brand') else {}),
            **({'flight_group':BRAND_GROUPS[flight['brand']]} if city=='europe_flights' and flight.get('brand') in BRAND_GROUPS else {}),
            **({'price':flight['price']} if flight.get('price') else {}),
            stops=[[origin, flight['departure'], flight['departure']], [destination, flight['arrival'], flight['arrival']]],
            legs=[key], timing_uncertain=False))
    return dict(**replay_settings(city), business_date=business_date,
        start=start, end=end,
        initial=min(end, max(start, int(datetime.combine(day, time(10), zone).timestamp()))),
        day_start_hour=0,
        services=services, stations=airports, paths=paths, geometry={},
        approximate_legs=0, total_legs=len(services), excluded_services=0,
        schedule={**reference['metadata'], 'available': True})
