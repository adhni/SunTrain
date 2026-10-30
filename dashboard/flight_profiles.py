"""Shared country profiles for recent flight locations."""
from dashboard.asean_flights import PROFILES as ASEAN_PROFILES, city_settings as settings_for, load_domestic as load_for

PROFILES={**ASEAN_PROFILES,'NZ':dict(slug='new_zealand',name='New Zealand',zone='Pacific/Auckland',label='NZDT',clock='New Zealand time (NZDT, UTC+13)',bounds=[[165,-48],[179,-33]],domestic=True,default_scope='domestic')}
PROFILES.update({
 'US':dict(
     slug='united_states',name='North America',zone='America/New_York',label='EST',
     clock='Eastern time (EST, UTC−5)',bounds=[[-161,7],[-64,55]],arc_anchor=-98,max_duration=57600,
     domestic=True,standalone=True,default_scope='both',origin_local_day=True,flight_country_filters=True,
     airport_countries={**dict.fromkeys('YYZ YVR YUL YYC YEG'.split(),'CA'),**dict.fromkeys('MEX CUN GDL MTY TIJ'.split(),'MX'), 'PTY':'PA','SJU':'PR','PUJ':'DO','SDQ':'DO','SJO':'CR','SAL':'SV','GUA':'GT','MBJ':'JM','NAS':'BS','AUA':'AW'},
     flight_jurisdictions={'PR':'US'},
     airport_replay_zones={'YVR':'Etc/GMT+7','YYC':'Etc/GMT+6','YEG':'Etc/GMT+6'},
     airport_zones={
         **dict.fromkeys('ATL JFK MCO MIA CLT EWR BOS LGA FLL PHL IAD BWI TPA DCA'.split(),'America/New_York'),
         **dict.fromkeys('DFW ORD IAH MSP BNA AUS'.split(),'America/Chicago'),
         **dict.fromkeys('DEN SLC'.split(),'America/Denver'),
         'PHX':'America/Phoenix','DTW':'America/Detroit','HNL':'Pacific/Honolulu',
         **dict.fromkeys('LAX LAS SFO SEA SAN'.split(),'America/Los_Angeles'),
         'YYZ':'America/Toronto','YUL':'America/Toronto','YVR':'America/Vancouver',
         'YYC':'America/Edmonton','YEG':'America/Edmonton',
         'MEX':'America/Mexico_City','GDL':'America/Mexico_City','MTY':'America/Monterrey',
         'CUN':'America/Cancun','TIJ':'America/Tijuana',
         'PTY':'America/Panama','SJU':'America/Puerto_Rico','PUJ':'America/Santo_Domingo','SDQ':'America/Santo_Domingo',
         'SJO':'America/Costa_Rica','SAL':'America/El_Salvador','GUA':'America/Guatemala',
         'MBJ':'America/Jamaica','NAS':'America/Nassau','AUA':'America/Aruba',
     },
     description='North America · Flights between 50 selected airports across the US, Canada, Mexico, Central America and the Caribbean · 2 November 2026 departures, including overnight arrivals. Timeline: Eastern time (EST, UTC−5); airport boards use local time. All captured fares use USD, including domestic flights. Coverage and prices are partial; paths are illustrative.',
 ),
 'SOUTH_AMERICA':dict(
     slug='south_america',name='South America',zone='UTC',label='UTC',clock='UTC',
     bounds=[[-82,-57],[-33,13]],arc_anchor=-60,max_duration=28800,
     domestic=True,standalone=True,default_scope='both',origin_local_day=True,flight_country_filters=True,
     airport_countries={'GRU':'BR','BOG':'CO','SCL':'CL','LIM':'PE','CGH':'BR','GIG':'BR','AEP':'AR','BSB':'BR','MDE':'CO','CNF':'BR',**dict.fromkeys('VCP REC SSA POA SDU FOR CWB'.split(),'BR'),'EZE':'AR','CTG':'CO','CLO':'CO',
         'UIO':'EC','MVD':'UY','ASU':'PY','VVI':'BO','CCS':'VE','GEO':'GY','PBM':'SR'},
     airport_zones={**dict.fromkeys('GRU CGH GIG BSB CNF'.split(),'America/Sao_Paulo'),
         **dict.fromkeys('BOG MDE'.split(),'America/Bogota'),'SCL':'America/Santiago',
         'LIM':'America/Lima','AEP':'America/Argentina/Buenos_Aires',
         **dict.fromkeys('VCP POA SDU CWB'.split(),'America/Sao_Paulo'),'EZE':'America/Argentina/Buenos_Aires',
         'REC':'America/Recife','SSA':'America/Bahia','FOR':'America/Fortaleza',
         'CTG':'America/Bogota','CLO':'America/Bogota','UIO':'America/Guayaquil','MVD':'America/Montevideo',
         'ASU':'America/Asuncion','VVI':'America/La_Paz','CCS':'America/Caracas','GEO':'America/Guyana','PBM':'America/Paramaribo'},
     description='Selected South American airports, plus captured domestic routes in Argentina, Peru and Chile. Departures on 2 November 2026 in each origin airport’s local time; overnight arrivals included. Timeline: UTC; airport boards use local time. Captured fares use USD. Coverage and prices are partial; paths are illustrative.',
 ),
 'NP':dict(slug='nepal',name='Nepal',zone='Asia/Kathmandu',label='NPT',clock='Nepal time (NPT, UTC+5:45)',bounds=[[80,26.2],[88.3,30.5]],domestic=True,default_scope='domestic'),
 'TW':dict(slug='taiwan',name='Taiwan',zone='Asia/Taipei',label='CST',clock='Taiwan time (UTC+8)',bounds=[[117.7,21.7],[122.3,26.6]],domestic=True,default_scope='domestic',worldwide=True),
 'HK':dict(slug='hong_kong',name='Hong Kong',zone='Asia/Hong_Kong',label='HKT',clock='Hong Kong time (HKT, UTC+8)',bounds=[[113.8,22.1],[114.5,22.6]],domestic=False,default_scope='international',airport='HKG',worldwide=True),
})
PROFILES['AMERICAS']=dict(
    slug='americas',name='Americas',zone='UTC',label='UTC',clock='UTC',
    bounds=[[-161,-57],[-33,55]],arc_anchor=-98,max_duration=57600,
    domestic=True,standalone=True,default_scope='both',origin_local_day=True,flight_country_filters=True,
    airport_countries={**dict.fromkeys(PROFILES['US']['airport_zones'],'US'),
        **PROFILES['US']['airport_countries'],**PROFILES['SOUTH_AMERICA']['airport_countries']},
    airport_zones={**PROFILES['US']['airport_zones'],**PROFILES['SOUTH_AMERICA']['airport_zones']},
    airport_replay_zones=PROFILES['US']['airport_replay_zones'],flight_jurisdictions=PROFILES['US']['flight_jurisdictions'],
    description='Americas · Flights between 77 selected airports across North America, Central America, the Caribbean and South America · 2 November 2026 departures, including overnight arrivals. Timeline: UTC; airport boards use local time. All captured fares use USD. Coverage and prices are partial; paths are illustrative.',
)
def _europe_americas_profile():
    import json
    from pathlib import Path
    manifest=json.loads((Path(__file__).resolve().parents[1]/'data/sources/europe_americas_flights_routes.json').read_text())
    return dict(slug='europe_americas',name='Europe–Americas',zone='UTC',label='UTC',clock='UTC',
        bounds=[[-130,-57],[20,65]],arc_anchor=-55,max_duration=86400,currency='EUR',
        domestic=True,standalone=True,origin_local_day=True,default_scope='international',flight_scopes=False,flight_country_filters=True,
        airport_countries={a['code']:a['country'] for a in manifest['airports']},
        airport_zones={a['code']:a['timezone'] for a in manifest['airports']},
        description='Europe–Americas · Connections between selected airports · 2 November 2026 departures, including overnight arrivals. All airlines returned on the sourced routes are included. Timeline: UTC; airport boards use local time. Reused EUR prices retain their original currency. Coverage and prices are partial; paths are illustrative.')


PROFILES['EUROPE_AMERICAS']=_europe_americas_profile()
def _africa_profile():
    import json
    from pathlib import Path
    manifest=json.loads((Path(__file__).resolve().parents[1]/'data/sources/africa_flights_routes.json').read_text())
    return dict(slug='africa',name='Africa',zone='UTC',label='UTC',clock='UTC',
        bounds=[[-25,-36],[65,38]],arc_anchor=20,max_duration=86400,
        currency='mixed',capture_currency='USD',price_currencies=['USD','EUR','MYR'],
        domestic=True,standalone=True,origin_local_day=True,default_scope='both',flight_country_filters=True,regional_start_view=True,
        airport_countries={a['code']:a['country'] for a in manifest['airports']},
        airport_zones={a['code']:a['timezone'] for a in manifest['airports']},
        description=manifest['replay_note'])


PROFILES['AFRICA']=_africa_profile()
def _turkiye_profile():
    import json
    from pathlib import Path
    manifest=json.loads((Path(__file__).resolve().parents[1]/'data/sources/turkiye_flights_routes.json').read_text())
    return dict(slug='turkiye',name='Türkiye',zone='Europe/Istanbul',label='TRT',clock='Türkiye time (UTC+3)',
        bounds=[[25.5,35.5],[45,42.5]],arc_anchor=35,max_duration=86400,
        currency='mixed',capture_currency='USD',price_currencies=['USD','EUR','MYR'],
        domestic=True,standalone=True,origin_local_day=True,default_scope='both',flight_country_filters=True,regional_start_view=True,
        airport_countries={a['code']:a['country'] for a in manifest['airports']},
        airport_zones={a['code']:a['timezone'] for a in manifest['airports']},description=manifest['replay_note'])


PROFILES['TR']=_turkiye_profile()
def _saudi_profile():
    import json
    from pathlib import Path
    manifest=json.loads((Path(__file__).resolve().parents[1]/'data/sources/saudi_flights_routes.json').read_text())
    return dict(slug='saudi',name='Saudi Arabia',zone='Asia/Riyadh',label='AST',clock='Saudi time (UTC+3)',
        bounds=[[34,16],[56,33]],arc_anchor=45,max_duration=86400,
        currency='mixed',capture_currency='USD',price_currencies=['USD','EUR','MYR'],
        domestic=True,standalone=True,origin_local_day=True,default_scope='both',flight_country_filters=True,regional_start_view=True,
        airport_countries={a['code']:a['country'] for a in manifest['airports']},
        airport_zones={a['code']:a['timezone'] for a in manifest['airports']},description=manifest['replay_note'])


PROFILES['SA']=_saudi_profile()
from dashboard.arabia_jordan_flights import profiles as arabia_jordan_profiles
PROFILES.update(arabia_jordan_profiles())
from dashboard.pakistan_bangladesh_flights import profiles as pakistan_bangladesh_profiles
PROFILES.update(pakistan_bangladesh_profiles())
from dashboard.pacific_flights import profile as pacific_profile
PROFILES['PACIFIC']=pacific_profile()
from dashboard.central_asia_flights import profile as central_asia_profile
PROFILES['CENTRAL_ASIA']=central_asia_profile()
from dashboard.canada_mexico_flights import profiles as canada_mexico_profiles
PROFILES.update(canada_mexico_profiles())
BY_CITY={p['slug']+'_flights':(c,p) for c,p in PROFILES.items()}


def city_settings():
    return settings_for(PROFILES)


def load_domestic(path,code):
    return load_for(path,code,PROFILES)
