"""Shared country profiles for recent flight locations."""
from dashboard.asean_flights import PROFILES as ASEAN_PROFILES, city_settings as settings_for, load_domestic as load_for

PROFILES={**ASEAN_PROFILES,'NZ':dict(slug='new_zealand',name='New Zealand',zone='Pacific/Auckland',label='NZDT',clock='New Zealand time (NZDT, UTC+13)',bounds=[[165,-48],[179,-33]],domestic=True,default_scope='domestic')}
PROFILES.update({
 'TW':dict(slug='taiwan',name='Taiwan',zone='Asia/Taipei',label='CST',clock='Taiwan time (UTC+8)',bounds=[[117.7,21.7],[122.3,26.6]],domestic=True,default_scope='domestic',worldwide=True),
 'HK':dict(slug='hong_kong',name='Hong Kong',zone='Asia/Hong_Kong',label='HKT',clock='Hong Kong time (HKT, UTC+8)',bounds=[[113.8,22.1],[114.5,22.6]],domestic=False,default_scope='international',airport='HKG',worldwide=True),
})
BY_CITY={p['slug']+'_flights':(c,p) for c,p in PROFILES.items()}


def city_settings():
    return settings_for(PROFILES)


def load_domestic(path,code):
    return load_for(path,code,PROFILES)
