"""Exact Korean airports and published domestic candidates, not dated schedules."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_australian_flights import AIRPORT_URL, AIRPORT_HASH, pinned_download

TOURISM_URL = 'https://english.visitkorea.or.kr/svc/contents/infoHtmlView.do?vcontsId=171992'
JINAIR_URL = 'https://files.jinair.com/documents/%EC%A7%84%EC%97%90%EC%96%B4%20%EC%83%81%EC%9A%A9%EC%9A%B0%EB%8C%80%20%EC%9D%B4%EC%9A%A9%EC%95%88%EB%82%B4%EC%84%9C%282026%29.pdf'
TRANSFER_URL = 'https://www.airport.kr/ap_en/1467/subview.do'
CODES = 'ICN GMP CJU PUS CJJ TAE KWJ RSU USN KPO HIN KUV WJU MWX YNY'.split()


def prepare():
    cache = ROOT / '.cache/australia-flights-audit'
    cache.mkdir(parents=True, exist_ok=True)
    raw = pinned_download(AIRPORT_URL, cache / 'ourairports-airports.csv', AIRPORT_HASH)
    with raw.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    airports = []
    for code in sorted(CODES):
        matches = [a for a in rows if a['iata_code'] == code and a['iso_country'] == 'KR' and a['type'] != 'closed']
        if len(matches) != 1:
            raise ValueError(f'Ambiguous or unresolved airport: {code}')
        a = matches[0]
        airports.append(dict(code=code, icao=a.get('icao_code') or a['ident'],
            name=f"{a['name']} ({code})", municipality=a['municipality'], country='KR',
            timezone='Asia/Seoul', mode='flight', lat=float(a['latitude_deg']), lon=float(a['longitude_deg'])))
    evidence = []
    pairs = set()
    for hub, destinations, source in [
        ('CJU', 'GMP PUS CJJ TAE KWJ RSU USN KPO HIN KUV WJU YNY', TOURISM_URL),
        ('GMP', 'PUS USN RSU HIN KPO KWJ', TOURISM_URL),
        ('GMP', 'TAE', JINAIR_URL),
    ]:
        for code in destinations.split():
            pairs.update([(hub, code), (code, hub)])
            evidence.append(dict(origin=hub, destination=code, source=source,
                kind='Published route candidate; not evidence of service on the replay date'))
    excluded = [
        dict(code='MWX', reason='Closed through 2026-12-24 23:59, beyond the replay date', source=TOURISM_URL),
        dict(code='ICN', reason='Transit-exclusive domestic connections are not ordinary standalone domestic services; historical ICN–CJU listing is not dated evidence', source=TRANSFER_URL),
    ]
    manifest = dict(country='KR', scope='domestic', start_date='2026-11-02', end_date='2026-11-02',
        timezone='Asia/Seoul', currency='USD', max_duration=8*3600,
        airport_source_url=AIRPORT_URL, airport_source_sha256=AIRPORT_HASH,
        route_source_url=TOURISM_URL, route_source_sha256=hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest(),
        route_hash_basis='Curated published exact-airport candidates, not raw website bytes',
        source_reviewed_date='2026-10-25', source_reviewed_timezone='Australia/Melbourne',
        airports=airports, routes=sorted(pairs), evidence=evidence,
        excluded_airports=excluded, unresolved_airports=[])
    output = ROOT / 'data/sources/south_korea_flights_routes.json'
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(airports=len(airports), routes=len(pairs))))


if __name__ == '__main__':
    prepare()
