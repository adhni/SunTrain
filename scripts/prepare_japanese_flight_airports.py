"""Published Japan domestic candidates, limited to the major-airport first pass."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL, AIRPORT_HASH, pinned_download

ANA_URL = 'https://www.ana.co.jp/guide/plan/airinfo/dom-timetable/pdf/timetable_all_20261025_20270131.pdf'
HND_URL = 'https://tokyo-haneda.com/en/flight/monthlyFlightSchedule.html'
NRT_URL = 'https://www.narita-airport.jp/en/discover/citylist/'
JAIR_URL = 'https://www.jair.co.jp/area/'
PEACH_URL = 'https://www.flypeach.com/en/lm/st/routemap'
SKYMARK_URL = 'https://www.skymark.co.jp/en/dom_network/'
NAHA_URL = 'https://www.naha-airport.co.jp/flight/city_list/'
REGIONS = {
    'Hokkaido':'CTS AKJ HKD MMB KUH OBO OKD',
    'Honshu':'HND NRT ITM KIX UKB NGO NKM AOJ AXT SDJ FKS HNA KIJ KMQ TOY FSZ HIJ OKJ UBJ IWK TTJ YGJ SYO IBR',
    'Shikoku':'TKS TAK MYJ KCZ',
    'Kyushu':'FUK KKJ HSG NGS KMJ OIT KMI KOJ',
    'Okinawa':'OKA ISG MMY SHI',
}
DEFERRED = {'NKM', 'OKD'}
# Route headings from ANA's 2026 winter PDF; filtered below to this release's
# airport set. Published seasonal/partner entries remain candidates, not flights.
ANA_GROUPS = '''AKJ:HND
AOJ:CTS ITM
ASJ:KKX KOJ OKA RNJ TKN
AXJ:FUK KMJ
AXT:CTS HND ITM NGO
CTS:FKS FUK HIJ HKD HND ITM KIJ KMQ KUH MMB NGO NRT OKJ SDJ SHB TOY UKB WKJ
FKS:ITM
FUJ:FUK NGS
FUK:HND ITM KIJ KMI KMQ KUM NGO OKA SDJ TSJ
HAC:HND
HIJ:HND OKA SDJ
HKD:HND ITM NGO
HND:HSG ISG ITM IWJ IWK KCZ KIX KKJ KMI KMJ KMQ KOJ KUH MBE MMB MMY MYJ NGO NGS NTQ OBO OIT OKA OKJ ONJ SHB SYO TAK TKS TOY TTJ UBJ UKB WKJ YGJ
IKI:NGS
ISG:ITM KIX MMY NGO OKA
ITM:KCZ KIJ KMI KMJ KOJ MMY MYJ NGS NRT OIT OKA SDJ
IWK:OKA
KIX:MMY OKA
KKX:KOJ
KMI:NGO OKA
KMJ:OKA
KOJ:KUM NGO OKA OKE RNJ TKN TNE
MMY:NGO OKA
MYJ:NGO OKA
NGO:NGS NRT OIT OKA SDJ
NGS:TSJ
OKA:OKE SDJ TAK UKB
OKE:TKN'''


def prepare():
    regions = {code:region for region, codes in REGIONS.items() for code in codes.split()}
    active = set(regions) - DEFERRED
    cache = ROOT / '.cache/australia-flights-audit'
    cache.mkdir(parents=True, exist_ok=True)
    raw = pinned_download(AIRPORT_URL, cache / 'ourairports-airports.csv', AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    airports = []
    for code in sorted(regions):
        matches = [a for a in rows if a['iata_code']==code and a['iso_country']=='JP' and a['type']!='closed']
        if len(matches)!=1:
            raise ValueError(f'Ambiguous or unresolved airport: {code}')
        a = matches[0]
        airports.append(dict(code=code, icao=a.get('icao_code') or a['ident'],
            name=f"{a['name']} ({code})", municipality=a['municipality'], country='JP',
            timezone='Asia/Tokyo', island_group=regions[code], mode='flight',
            lat=float(a['latitude_deg']), lon=float(a['longitude_deg'])))
    pairs = set(); evidence = []
    def add(hub, destinations, source, kind='Published route candidate; not dated flight evidence'):
        for code in destinations.split():
            if hub not in active or code not in active:
                continue
            pairs.update([(hub, code), (code, hub)])
            evidence.append(dict(origin=hub, destination=code, source=source, kind=kind))
    for line in ANA_GROUPS.splitlines():
        hub, destinations = line.split(':'); add(hub, destinations, ANA_URL)
    add('HND', 'AOJ AXT SYO HKD MMB AKJ KUH OBO KOJ KMI OKA MMY ISG SHI', HND_URL)
    add('NRT', 'AKJ CTS ITM KIX NGO HIJ KCZ MYJ TAK FUK ISG KKJ KMI KMJ KOJ NGS OIT OKA', NRT_URL)
    add('NRT', 'HKD', 'https://www.narita-airport.jp/files/3a7f642590e6b43238a824febdcc3d359b4d6efa4dea8211b674fc4b1e9b4303')
    add('ITM', 'HKD AOJ AXT HNA SDJ KIJ MYJ OIT FUK NGS KMJ KMI KOJ CTS', JAIR_URL,
        'Regional-city and seasonal network candidate; dated availability is checked separately')
    add('ITM', 'AKJ', 'https://press.jal.co.jp/ja/release/202608/009668.html')
    add('FUK', 'TKS KCZ MYJ KMI', JAIR_URL)
    add('CTS', 'MMB AOJ HNA SDJ', JAIR_URL)
    for hub, codes in [('NRT','KIX CTS FUK OKA ISG'), ('KIX','NRT CTS SDJ FUK NGS KMI KOJ OKA ISG'),
                       ('NGO','CTS OKA ISG'), ('FUK','CTS OKA ISG')]:
        add(hub, codes, PEACH_URL)
    for hub, codes in [('HND','CTS UKB FUK KOJ OKA SHI'), ('CTS','IBR NGO UKB FUK'),
                       ('SDJ','UKB'), ('IBR','UKB FUK OKA'), ('NGO','KOJ OKA'),
                       ('UKB','NGS KOJ OKA SHI'), ('FUK','OKA SHI'), ('OKA','SHI')]:
        add(hub, codes, SKYMARK_URL)
    add('OKA', 'CTS SDJ HND NRT IBR KIJ KMQ FSZ NGO KIX ITM UKB IWK HIJ OKJ MYJ TAK FUK NGS KMJ KMI KOJ ISG MMY SHI', NAHA_URL)
    deferred = [dict(code=code, reason='Commuter-focused airport deferred from the major-airport first pass') for code in sorted(DEFERRED)]
    manifest = dict(country='JP', scope='domestic', start_date='2026-11-02', end_date='2026-11-02',
        timezone='Asia/Tokyo', currency='USD', max_duration=8*3600,
        coverage_scope='Major airports and city routes first; small island and commuter services deferred',
        airport_source_url=AIRPORT_URL, airport_source_sha256=AIRPORT_HASH,
        route_source_url=ANA_URL, route_source_sha256=hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated exact-airport candidate evidence, not raw website bytes',
        source_documents=[dict(url=ANA_URL, sha256='db3f438961d14e13a6275b21b8ce5cbcb5f09cf828c46b166e623c06f449d223', purpose='Route headings only; no timetable adapter')],
        source_reviewed_date='2026-10-25', source_reviewed_timezone='Australia/Melbourne',
        airports=airports, routes=sorted(pairs), evidence=evidence,
        deferred_airports=deferred, unresolved_airports=[])
    (ROOT / 'data/sources/japan_flights_routes.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(airports=len(airports), searched_airports=len(active), directional_routes=len(pairs))))


if __name__=='__main__':
    prepare()
