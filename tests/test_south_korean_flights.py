"""Exact domestic candidates, KST day ownership, USD fares and cached replay."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment, scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference

DAY = '2026-11-02'
CONFIG = country_config('KR')
AIRPORTS = {a['code']: a for a in CONFIG['manifest']['airports']}
START = int(datetime(2026, 11, 2, tzinfo=ZoneInfo('Asia/Seoul')).timestamp())
CONTEXT = dict(currency='USD', adults=1, cabin='economy', trip_type='one_way')


def test_exact_catalogue_and_published_manifest_exclude_closed_and_transfer_only():
    manifest = CONFIG['manifest']
    assert len(AIRPORTS) == 15 and len(manifest['routes']) == 38
    assert CONFIG['currency'] == 'USD' and CONFIG['max_duration'] == 8*3600
    assert AIRPORTS['ICN']['icao'] != AIRPORTS['GMP']['icao']
    assert AIRPORTS['ICN']['lon'] != AIRPORTS['GMP']['lon']
    assert all(a['country'] == 'KR' and a['timezone'] == 'Asia/Seoul' for a in AIRPORTS.values())
    assert {a['code'] for a in manifest['excluded_airports']} == {'MWX', 'ICN'}
    assert '2026-12-24' in manifest['excluded_airports'][0]['reason']
    for a, b in manifest['routes']:
        assert [b, a] in manifest['routes']
        assert not {a, b} & {'ICN', 'MWX', 'SEL'}
    assert ['CJU', 'WJU'] in manifest['routes'] and ['GMP', 'HIN'] in manifest['routes']
    assert CITIES['south_korea_flights']['replay_kind'] == 'flights'
    assert CITIES['south_korea_flights'].get('flight_scopes')
    for city in ['south_korea', 'seoul']:
        assert CITIES[city].get('replay_kind', 'transit') == 'transit'
    with pytest.raises(ValueError, match='planned; only domestic'):
        country_config('KR', 'international')
    assert country_config()['manifest'] is None and country_config('MY')['currency'] == 'MYR'


def test_kst_adjacent_day_short_duration_and_distinct_flight_prices():
    assert START == int(datetime(2026, 11, 1, 15, tzinfo=ZoneInfo('UTC')).timestamp())
    assert set(expected_queries(DAY, [('GMP', 'CJU')], CONFIG)) == {
        ('2026-11-01', 'GMP', 'CJU'), (DAY, 'GMP', 'CJU')}
    row = segment('GMP', 'CJU', [23, 50], [0, 50], 60, carrier='KE', number='123')
    row[20] = [2026, 11, 1]
    f = parse_results(scripts(row, row), 'GMP', 'CJU', '2026-11-01', CONFIG['zones'])
    assert len(f) == 1 and f[0]['departure'] < START < f[0]['arrival']
    row = segment('CJU', 'WJU', [8, 0], [8, 1], 1, carrier='LJ', number='123')
    row[17] = None
    other = segment('CJU', 'WJU', [8, 0], [8, 1], 1, carrier='LJ', number='999')
    records = parse_results(scripts(row, row, other), 'CJU', 'WJU', DAY, CONFIG['zones'])
    assert len(records) == 2 and records[0]['aircraft'] == 'Aircraft not specified'
    prices = cheapest_prices(scripts([offer(row, 65), offer(row, 49.25), offer(other, 80)]), records, 'USD')
    assert prices[records[0]['id']]['amount_minor'] == 4925
    assert prices[records[1]['id']]['amount_minor'] == 8000
    row[11] = 10
    with pytest.raises(ValueError, match='duration differs'):
        parse_results(scripts(row), 'CJU', 'WJU', DAY, CONFIG['zones'])


def test_missing_query_rebuild_and_compressed_http_day_validation(tmp_path, monkeypatch):
    cache = tmp_path/'cache'; cache.mkdir()
    row = segment('GMP', 'CJU', [23, 50], [0, 50], 60, carrier='KE', number='123')
    row[20] = [2026, 11, 1]
    f = parse_results(scripts(row), 'GMP', 'CJU', '2026-11-01', CONFIG['zones'])[0]
    f['price'] = {**CONTEXT, 'amount_minor':4925, 'captured_at':'2026-10-25T00:00:00+00:00'}
    q = dict(origin='GMP', destination='CJU', date='2026-11-01', status='results',
        captured_at='2026-10-25T00:00:00+00:00', flights=[f])
    path = cache/'2026-11-01-GMP-CJU.json'; path.write_text(json.dumps(q))
    pairs = [('GMP','CJU'), ('CJU','WJU')]
    out = tmp_path/'day.gz'; prepare(cache, out, DAY, pairs, CONFIG)
    first = out.read_bytes(); prepare(cache, out, DAY, pairs, CONFIG)
    assert first == out.read_bytes()
    reference = json.loads(gzip.decompress(first))
    assert len(reference['metadata']['uncollected_queries']) == 3
    assert reference['metadata']['coverage']['queries_captured'] == 1
    monkeypatch.setenv('SUNTRAIN_SOUTH_KOREA_FLIGHTS_REFERENCE', str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE', str(tmp_path/'http'))
    day = flights.replay_day(DAY, 'south_korea_flights')
    assert day['start'] == START and len(day['services']) == 1
    assert day['services'][0]['price'] == f['price']
    assert day['services'][0]['flight_scope'] == 'domestic'
    app = Flask(__name__); replay_http.register_replay_routes(app)
    client = app.test_client(); info = replay_http.descriptor(DAY, 'south_korea_flights')
    response = client.get(info['url'], headers={'Accept-Encoding':'gzip'})
    assert response.status_code == 200
    assert json.loads(gzip.decompress(response.data))['timezone'] == 'Asia/Seoul'
    assert client.get(info['url'], headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code == 304
    assert client.get(info['url'].replace(DAY, '2026-11-03')).status_code == 404
    q['origin'] = 'ICN'; path.write_text(json.dumps(q))
    with pytest.raises(ValueError, match='identity'):
        prepare(cache, out, DAY, pairs, CONFIG)


@pytest.mark.parametrize('origin,destination', [('ICN','PUS'), ('MWX','CJU')])
def test_preparation_rejects_excluded_airports(tmp_path, origin, destination):
    with pytest.raises(ValueError, match='approved manifest'):
        prepare(tmp_path, tmp_path/'out.gz', DAY, [(origin, destination)], CONFIG)


def test_runtime_rejects_bad_currency_foreign_closed_and_transfer_only(tmp_path, monkeypatch):
    path = tmp_path/'reference.gz'
    monkeypatch.setenv('SUNTRAIN_SOUTH_KOREA_FLIGHTS_REFERENCE', str(path))
    # An international override cannot accidentally enable the planned rollout.
    monkeypatch.setenv('SUNTRAIN_SOUTH_KOREA_INTERNATIONAL_REFERENCE', str(tmp_path/'missing.gz'))
    assert flights.reference_paths(DAY, 'south_korea_flights') == [path]
    f = dict(id='flight', number='KE123', carrier='KE', origin='GMP', destination='CJU',
        departure=START, arrival=START+3600, price={**CONTEXT, 'amount_minor':4925})
    airports = list(AIRPORTS.values())
    for code in ['ICN', 'MWX']:
        write_reference(path, airports, [{**f, 'origin':code}], dict(scope='domestic', fare_context=CONTEXT))
        with pytest.raises(ValueError, match='excludes'):
            flights.load_reference(DAY, 'south_korea_flights')
    foreign = [{**a, 'country':'JP'} if a['code']=='CJU' else a for a in airports]
    write_reference(path, foreign, [f], dict(scope='domestic', fare_context=CONTEXT))
    with pytest.raises(ValueError, match='excludes'):
        flights.load_reference(DAY, 'south_korea_flights')
    f['price'] = {**f['price'], 'currency':'KRW'}
    write_reference(path, airports, [f], dict(scope='domestic', fare_context=CONTEXT))
    with pytest.raises(ValueError, match='no implicit conversion'):
        flights.load_reference(DAY, 'south_korea_flights')


def test_prepared_domestic_capture_coverage_is_honest(monkeypatch):
    monkeypatch.setenv("SUNTRAIN_SOUTH_KOREA_FLIGHTS_REFERENCE",str(flights.reference_path(city="south_korea_flights")))
    day = flights.replay_day(DAY, 'south_korea_flights')
    codes = {a['code'] for a in day['stations']}
    assert {'GMP','CJU','PUS','CJJ','WJU','HIN'} <= codes
    assert not codes & {'ICN','MWX'}
    assert day['services'] and all(s['flight_scope']=='domestic' for s in day['services'])
    assert len({f['id'] for f in day['services']}) == len(day['services'])
    c = day['schedule']['coverage']
    assert c['queries_planned'] == 76
    assert c['queries_captured'] + c['failed_or_missing_queries'] == 76
    assert c['airports_planned'] == 13 and c['candidate_airports'] == 15
    assert day['schedule']['fare_context']['currency'] == 'USD'
    assert day['schedule']['priced_flights'] == sum(bool(s.get('price')) for s in day['services'])
    for s in day['services']:
        assert s['stops'][0][2] < day['end'] and s['stops'][1][1] >= START
        if s.get('price'):
            assert s['price']['currency']=='USD' and s['price']['amount_minor']>0
