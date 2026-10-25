"""Small shared profiles for the five remaining ASEAN flight locations."""
import gzip
import json
from pathlib import Path

DAY='2026-11-02'
PROFILES={
 'BN':dict(slug='brunei',name='Brunei',zone='Asia/Brunei',label='BNT',clock='Brunei time (BNT, UTC+8)',bounds=[[113.8,4.0],[115.5,5.2]],domestic=False,default_scope='international',airport='BWN'),
 'KH':dict(slug='cambodia',name='Cambodia',zone='Asia/Phnom_Penh',label='ICT',clock='Cambodia time (ICT, UTC+7)',bounds=[[102,10],[108,14.8]],domestic=True,default_scope='international'),
 'LA':dict(slug='laos',name='Laos',zone='Asia/Vientiane',label='ICT',clock='Laos time (ICT, UTC+7)',bounds=[[100,13.5],[108,22.7]],domestic=True,default_scope='domestic'),
 'MM':dict(slug='myanmar',name='Myanmar',zone='Asia/Yangon',label='MMT',clock='Myanmar time (MMT, UTC+6:30)',bounds=[[92,9.5],[102,28.7]],domestic=True,default_scope='domestic'),
 'TL':dict(slug='timor_leste',name='Timor-Leste',zone='Asia/Dili',label='TLT',clock='Timor-Leste time (TLT, UTC+9)',bounds=[[124,-9.6],[127.5,-8.0]],domestic=True,default_scope='international',airport='DIL'),
}
BY_CITY={p['slug']+'_flights':(code,p) for code,p in PROFILES.items()}
RETIRED_AIRPORTS={'PNH':'KTI','REP':'SAI'}


def description(profile):
    prefix='International flights' if not profile['domestic'] else 'Domestic flights and international connections'
    if profile.get('worldwide'):
        return f"{profile['name']} · {'Domestic flights and worldwide international connections' if profile['domestic'] else 'Worldwide international flights'} · 2 November 2026. Timeline: {profile['clock']}; airport boards use local time. Captured fares retain their original currencies. Coverage and prices are partial; paths are illustrative."
    return f"{profile['name']} · {prefix} to selected SunTrain flight locations · 2 November 2026. Timeline: {profile['clock']}; airport boards use local time. Captured fares retain their original currencies. Coverage and prices are partial; paths are illustrative."


def city_settings(profiles=None):
    selected={p["slug"]+"_flights":(c,p) for c,p in (profiles or PROFILES).items()}
    return {city:dict(replay_kind='flights',name=p['name']+' · Flights',timezone=p['zone'],bounds=p['bounds'],passenger_data=False,
        start_date=DAY,end_date=DAY,flight_scopes=p['domestic'],default_flight_scope=p['default_scope'],default_airport=p.get('airport'),description=description(p),
        default_modes=['flight'],modes=[('Flights','flight')],operators=[],directions=[('Scheduled service','Scheduled service')]) for city,(_,p) in selected.items()}


def load_domestic(path,code,profiles=None):
    p=(profiles or PROFILES)[code]
    with gzip.open(Path(path),'rt') as stream:reference=json.load(stream)
    context=reference['metadata'].get('fare_context',{})
    if tuple(context.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way'):
        raise ValueError('Country domestic fares require USD, one adult, economy, one-way')
    air={a['code']:a for a in reference['airports']};records={}
    if any(a['country']!=code or a['timezone']!=p['zone'] or a['code'] in RETIRED_AIRPORTS for a in air.values()):
        raise ValueError('Country domestic airports require exact national identities and zones')
    for f in reference['flights']:
        if f['origin'] not in air or f['destination'] not in air or not 60<=f['arrival']-f['departure']<=28800:
            raise ValueError('Invalid domestic segment')
        price=f.get('price')
        if price and (tuple(price.get(k) for k in ('currency','adults','cabin','trip_type'))!=('USD',1,'economy','one_way') or type(price.get('amount_minor')) is not int or price['amount_minor']<=0):
            raise ValueError('Country domestic prices require positive USD minor units; no implicit conversion')
        record={**f,'flight_scope':'domestic'}
        if f['id'] in records and records[f['id']]!=record:raise ValueError('Conflicting country flight identity')
        records[f['id']]=record
    return {**reference,'flights':list(records.values())}
