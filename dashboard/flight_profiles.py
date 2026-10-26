"""Shared country profiles for recent flight locations."""
from dashboard.asean_flights import PROFILES as ASEAN_PROFILES, city_settings as settings_for, load_domestic as load_for

PROFILES={**ASEAN_PROFILES,'NZ':dict(slug='new_zealand',name='New Zealand',zone='Pacific/Auckland',label='NZDT',clock='New Zealand time (NZDT, UTC+13)',bounds=[[165,-48],[179,-33]],domestic=True,default_scope='domestic')}
PROFILES.update({
 'US':dict(
     slug='united_states',name='North America',zone='America/New_York',label='EST',
     clock='Eastern time (EST, UTC−5)',bounds=[[-161,17],[-65,55]],max_duration=57600,
     domestic=True,standalone=True,default_scope='both',origin_local_day=True,flight_country_filters=True,
     airport_countries={**dict.fromkeys('YYZ YVR YUL YYC YEG'.split(),'CA'),**dict.fromkeys('MEX CUN GDL MTY TIJ'.split(),'MX')},
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
     },
     description='North America · Flights between the US top 30, Canada top 5 and Mexico top 5 airports · 2 November 2026 departures, including overnight arrivals. Timeline: Eastern time (EST, UTC−5); airport boards use local time. All captured fares use USD, including domestic flights. Coverage and prices are partial; paths are illustrative.',
 ),
 'NP':dict(slug='nepal',name='Nepal',zone='Asia/Kathmandu',label='NPT',clock='Nepal time (NPT, UTC+5:45)',bounds=[[80,26.2],[88.3,30.5]],domestic=True,default_scope='domestic'),
 'TW':dict(slug='taiwan',name='Taiwan',zone='Asia/Taipei',label='CST',clock='Taiwan time (UTC+8)',bounds=[[117.7,21.7],[122.3,26.6]],domestic=True,default_scope='domestic',worldwide=True),
 'HK':dict(slug='hong_kong',name='Hong Kong',zone='Asia/Hong_Kong',label='HKT',clock='Hong Kong time (HKT, UTC+8)',bounds=[[113.8,22.1],[114.5,22.6]],domestic=False,default_scope='international',airport='HKG',worldwide=True),
})
BY_CITY={p['slug']+'_flights':(c,p) for c,p in PROFILES.items()}


def city_settings():
    return settings_for(PROFILES)


def load_domestic(path,code):
    return load_for(path,code,PROFILES)
