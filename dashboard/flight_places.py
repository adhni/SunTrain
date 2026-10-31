"""Small discovery index derived from World; no replay data is loaded by the homepage."""
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'data/reference/flight_places.json'
# Browsing groups, independent of airline inventories and collector boundaries.
REGIONS = {
    'africa': ('Africa', [[-20, -36], [56, 38]], 'DZ AO BJ BW BF BI CM CV CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW SH ST SN SC SL SO ZA SS SD TZ TG TN UG EH ZM ZW'),
    'asia': ('Asia', [[25, -12], [180, 78]], 'AF AM AZ BH BD BT BN KH CN CX CC IO HK IN ID IR IQ IL JP JO KZ KP KR KW KG LA LB MO MY MV MN MM NP OM PK PS PH QA SA SG LK SY TW TJ TH TL TM AE UZ VN YE'),
    'europe': ('Europe', [[-25, 34], [65, 72]], 'AL AD AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GE GG GI GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SK SM TR UA VA XK'),
    'north-america': ('North America', [[-170, 5], [-50, 80]], 'AG AI AW BS BB BZ BM BQ VG CA KY CR CU CW DM DO SV GL GD GP GT HT HN JM MQ MX MS NI PA PR BL KN LC MF PM VC SX TT TC US VI'),
    'south-america': ('South America', [[-83, -56], [-34, 13]], 'AR BO BR CL CO EC FK GF GY PY PE SR UY VE'),
    'oceania': ('Oceania', [[110, -52], [230, 25]], 'AS AU CK FJ PF GU KI MH FM NR NC NZ NU NF MP PW PG PN WS SB TK TO TV UM VU WF'),
}
SUBREGIONS = {
    'central-asia': ('Central Asia', 'asia', [[45, 32], [88, 56]], 'KZ KG TJ TM UZ'),
    'pacific-islands': ('Pacific Islands', 'oceania', [[128, -33], [252, 33]], 'AS CK FJ PF GU KI MH FM NR NC NU NF MP PW PG PN WS SB TK TO TV VU WF'),
}


def airport_bounds(airports, padding=.65):
    """Smallest longitude interval, including Pacific countries across the dateline."""
    lons = sorted(a['lon'] % 360 for a in airports)
    gaps = [(lons[(i + 1) % len(lons)] + (360 if i == len(lons) - 1 else 0) - lon, i)
            for i, lon in enumerate(lons)]
    gap, i = max(gaps)
    west = lons[(i + 1) % len(lons)]
    if west > 180:
        west -= 360
    return [[round(west-padding, 6), max(-80, min(a['lat'] for a in airports)-padding)],
            [round(west+360-gap+padding, 6), min(83, max(a['lat'] for a in airports)+padding)]]


def build_index(reference, source_hash):
    from dashboard.europe_flights import CARRIERS
    membership = {}
    for region, (_, _, codes) in REGIONS.items():
        for code in codes.split():
            if code in membership:
                raise ValueError('Duplicate browsing region: ' + code)
            membership[code] = region
    airports = {a['code']: a for a in reference['airports']}
    counts = {}
    for flight in reference['flights']:
        countries = {airports[flight[k]]['country'] for k in ('origin', 'destination')}
        keys = {'world_flights', *('country:' + c for c in countries),
                *('airport:' + flight[k] for k in ('origin', 'destination'))}
        for c in countries:
            if c not in membership:
                raise ValueError('Unreviewed browsing country: ' + c)
            keys.add('region:' + membership[c])
        for region, (_, _, _, codes) in SUBREGIONS.items():
            if countries & set(codes.split()):
                keys.add('region:' + region)
        if {flight['origin'], flight['destination']} & {'DXB', 'AUH', 'DOH'}:
            keys.add('experience:gulf')
        regions = {membership[c] for c in countries}
        if 'europe' in regions and regions & {'north-america', 'south-america'}:
            keys.add('experience:atlantic')
        if flight['flight_scope'] == 'international':
            keys.add('experience:international')
        if flight['carrier'] in CARRIERS:
            keys.add('experience:european-airlines')
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
    places = []
    for region, (name, bounds, codes) in REGIONS.items():
        places.append(dict(id='region:'+region, name=name, kind='region', bounds=bounds,
                           countries=sorted(codes.split()), count=counts.get('region:'+region, 0), home_marker=False))
    for region, (name, parent, bounds, codes) in SUBREGIONS.items():
        places.append(dict(id='region:'+region, name=name, kind='region', region=parent, bounds=bounds,
                           countries=sorted(codes.split()), count=counts.get('region:'+region, 0), home_marker=False))
    europe = REGIONS['europe'][2].split()
    americas = REGIONS['north-america'][2].split() + REGIONS['south-america'][2].split()
    for key, name, fields in [
        ('gulf', 'Gulf connections', {'codes':['DXB', 'AUH', 'DOH']}),
        ('atlantic', 'Across the Atlantic', {'between':[europe, americas]}),
        ('international', 'International flights', {'scope':'international'}),
        ('european-airlines', 'European airline networks', {'carriers':sorted(CARRIERS)}),
    ]:
        places.append(dict(id='experience:'+key, name=name, kind='experience', home_marker=False,
                           bounds=[[-180, -60], [180, 82]], count=counts.get('experience:'+key, 0), **fields))
    active = [a for code, a in airports.items() if 'airport:'+code in counts]
    for country in sorted({a['country'] for a in active}):
        local = [a for a in active if a['country'] == country]
        places.append(dict(id='country:'+country, name=country, country=country, kind='country',
                           region=membership[country], bounds=airport_bounds(local), airports=len(local),
                           count=counts['country:'+country], home_marker=True))
    for a in sorted(active, key=lambda a: a['code']):
        places.append(dict(id='airport:'+a['code'], name=a['name'], code=a['code'], country=a['country'],
                           municipality=a.get('municipality', ''), kind='airport', region=membership[a['country']],
                           bounds=airport_bounds([a]), count=counts['airport:'+a['code']], home_marker=False))
    return dict(date=reference['metadata']['start_date'], timezone='UTC', source_sha256=source_hash,
                flights=len(reference['flights']), places=places)


def prepare(source=None, destination=INDEX):
    from dashboard.world_flights import reference_path
    data = Path(source or reference_path()).read_bytes()
    result = build_index(json.loads(gzip.decompress(data)), hashlib.sha256(data).hexdigest())
    Path(destination).write_text(json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False)+'\n')
    return result


@lru_cache(maxsize=1)
def catalogue():
    return json.loads(INDEX.read_text())
