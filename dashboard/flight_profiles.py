"""Shared country profiles for recent flight locations."""
from dashboard.asean_flights import PROFILES as ASEAN_PROFILES, city_settings as settings_for, load_domestic as load_for

PROFILES={**ASEAN_PROFILES,'NZ':dict(slug='new_zealand',name='New Zealand',zone='Pacific/Auckland',label='NZDT',clock='New Zealand time (NZDT, UTC+13)',bounds=[[165,-48],[179,-33]],domestic=True,default_scope='domestic')}
PROFILES.update({
 'US':dict(
     slug='united_states',name='United States',zone='America/New_York',label='EST',
     clock='Eastern time (EST, UTC−5)',bounds=[[-126,23],[-65,50]],
     domestic=True,domestic_only=True,default_scope='domestic',origin_local_day=True,
     airport_zones={
         **dict.fromkeys('ATL JFK MCO MIA CLT EWR BOS LGA FLL'.split(),'America/New_York'),
         **dict.fromkeys('DFW ORD IAH MSP'.split(),'America/Chicago'),'DEN':'America/Denver',
         'PHX':'America/Phoenix','DTW':'America/Detroit',
         **dict.fromkeys('LAX LAS SFO SEA'.split(),'America/Los_Angeles'),
     },
     description='United States · Domestic flights between the top 20 airports · 2 November 2026 departures, including overnight arrivals. Timeline: Eastern time (EST, UTC−5); airport boards use local time. All returned airlines; captured USD fares and coverage are partial. Paths are illustrative.',
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
