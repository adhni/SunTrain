"""Europe is a region with explicit launch brands, not a synthetic country."""
import gzip,json,os
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
DAY='2026-11-02'
EUROPE_COUNTRIES=set('AL AD AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GE GG GI GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS SE SI SK SM TR UA VA XK'.split())
BRANDS={'ryanair':'Ryanair','easyjet':'easyJet','wizzair':'Wizz Air'}
# Reviewed carrier codes, never airline-name substring matching.
CARRIERS={'FR':'ryanair','RK':'ryanair','RR':'ryanair','AL':'ryanair',
 'U2':'easyjet','EC':'easyjet','DS':'easyjet','EZY':'easyjet','EJU':'easyjet','EZS':'easyjet',
 'W6':'wizzair','W4':'wizzair','W9':'wizzair','WZZ':'wizzair','WMT':'wizzair','WUK':'wizzair'}
COLORS={'ryanair':'#82ace0','easyjet':'#f59c57','wizzair':'#e660b6'}
NOTE='Ryanair, easyJet and Wizz Air · 2 November 2026 schedule snapshot. Timeline: UTC; airport boards use local dates and times. Captured fares retain their original currencies. Coverage and prices are partial; paths are illustrative.'
SETTINGS=dict(replay_kind='flights',name='Europe · Flights',timezone='UTC',bounds=[[-26,13],[57,70]],passenger_data=False,
 start_date=DAY,end_date=DAY,flight_scopes=True,default_flight_scope='both',flight_country_filters=True,flight_brands=BRANDS,
 description=NOTE,default_modes=['flight'],modes=[('Flights','flight')],operators=[],directions=[('Scheduled service','Scheduled service')])


def reference_path():return Path(os.getenv('SUNTRAIN_EUROPE_FLIGHTS_REFERENCE',str(ROOT/f'data/reference/europe_flights/{DAY}.json.gz')))


def valid_price(p):
 return (p.get('currency') in {'EUR','USD','MYR'} and type(p.get('amount_minor')) is int and p['amount_minor']>0
  and tuple(p.get(k) for k in ('adults','cabin','trip_type'))==(1,'economy','one_way'))


def load_reference(day):
 if day!=DAY:raise ValueError('Unsupported Europe flight date')
 with gzip.open(reference_path(),'rt') as f:r=json.load(f)
 meta=r['metadata']
 if (meta.get('profile'),meta.get('start_date'),meta.get('end_date'),meta.get('timezone'))!=('europe_flights',DAY,DAY,'UTC'):raise ValueError('Invalid Europe snapshot context')
 if tuple(meta.get('fare_context',{}).get(k) for k in ('currency','adults','cabin','trip_type'))!=('EUR',1,'economy','one_way'):raise ValueError('Invalid Europe query fare context')
 air={a['code']:a for a in r['airports']}
 if len(air)!=len(r['airports']):raise ValueError('Duplicate European airport code')
 for a in air.values():
  if type(a.get('europe')) is not bool or a['europe']!=(a.get('country') in EUROPE_COUNTRIES):raise ValueError('Explicit reviewed Europe airport membership required')
  ZoneInfo(a['timezone'])
 ids={}
 for f in r['flights']:
  a,b=air[f['origin']],air[f['destination']];brand=CARRIERS.get(f['carrier'])
  if not brand or f.get('brand')!=brand:raise ValueError('Flight outside verified Europe launch brands')
  if not (a['europe'] or b['europe']):raise ValueError('Flight wholly outside reviewed Europe footprint')
  scope='domestic' if a['country']==b['country'] else 'international'
  if f.get('flight_scope')!=scope or not 60<=f['arrival']-f['departure']<=28800:raise ValueError('Invalid European flight scope or duration')
  if f.get('price') and not valid_price(f['price']):raise ValueError('Invalid European fare context')
  if f['id'] in ids:raise ValueError('Duplicate European flight identity')
  ids[f['id']]=f
 return r
