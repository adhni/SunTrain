from datetime import date, datetime
import gzip
import json
from zoneinfo import ZoneInfo

from flask import Flask
import pytest

from dashboard import flights, replay_http
from dashboard.replay import get_replay_day
from scripts.prepare_australian_flights import flight_times, great_circle, instant, operating_days


def test_calendar_restrictions_and_local_clocks():
    assert operating_days('Daily') == set(range(1, 8))
    assert operating_days('X67') == {1, 2, 3, 4, 5}
    assert operating_days('135') == {1, 3, 5}
    with pytest.raises(ValueError):
        operating_days('8')
    day = date(2013, 3, 4)
    start, end = flight_times(day, '700', '720', 'Australia/Sydney', 'Australia/Brisbane')
    assert end - start == 80 * 60  # Queensland is an hour behind NSW in March.
    start, end = flight_times(day, '2340', '615', 'Australia/Perth', 'Australia/Melbourne')
    assert end - start == 215 * 60
    assert datetime.fromtimestamp(end, ZoneInfo('Australia/Melbourne')).date() == date(2013, 3, 5)
    start, end = flight_times(day, '2215', '55', 'Australia/Adelaide', 'Australia/Darwin')
    assert end - start == 220 * 60
    for clock in ['2401', '1260', '-1']:
        with pytest.raises(ValueError):
            instant(day, clock, 'Australia/Melbourne')
    with pytest.raises(ValueError):
        instant(date(2026, 10, 4), '230', 'Australia/Melbourne')
    with pytest.raises(ValueError):
        instant(date(2026, 4, 5), '230', 'Australia/Melbourne')


def test_actual_published_flight_preserves_times_and_flight_number():
    payload = get_replay_day('2013-03-04', 'australia_flights')
    flight = next(s for s in payload['services'] if s['number'] == 'JQ402' and s['id'].startswith('2013-03-04'))
    dep, arr = flight['stops'][0][2], flight['stops'][1][1]
    assert datetime.fromtimestamp(dep, ZoneInfo('Australia/Sydney')).strftime('%H:%M') == '07:00'
    assert datetime.fromtimestamp(arr, ZoneInfo('Australia/Brisbane')).strftime('%H:%M') == '07:20'
    assert arr - dep == 4800
    assert flight['source_page'] == 1
    assert payload['schedule']['parsed_source_rows'] == 568
    assert len(payload['schedule']['omitted_source_rows']) == 13
    assert all(row['page'] == 3 for row in payload['schedule']['omitted_source_rows'])


@pytest.mark.parametrize('day', [f'2013-03-{n:02}' for n in range(4, 11)])
def test_every_day_has_unique_real_flights_and_overnight_carry_ins(day):
    payload = get_replay_day(day, 'australia_flights')
    assert payload['end'] - payload['start'] == 86400
    assert datetime.fromtimestamp(payload['start'], ZoneInfo(payload['timezone'])).hour == 0
    assert len(payload['services']) > 150
    assert len(payload['stations']) == 18
    assert len({s['id'] for s in payload['services']}) == len(payload['services'])
    assert any(s['stops'][0][2] < payload['start'] for s in payload['services'])
    for flight in payload['services']:
        assert flight['mode'] == 'flight' and flight['number'].startswith('JQ')
        assert flight['stops'][0][2] < payload['end'] and flight['stops'][1][1] >= payload['start']
        assert 15 * 60 <= flight['stops'][1][1] - flight['stops'][0][2] <= 8 * 3600
        path = payload['paths'][flight['legs'][0]]
        assert path['quality'] == 'illustrative'
        origin, destination = [payload['stations'][stop[0]] for stop in flight['stops']]
        assert path['coordinates'][0] == [origin['lon'], origin['lat']]
        assert path['coordinates'][-1] == [destination['lon'], destination['lat']]
        assert len(path['distances']) == len(path['coordinates']) == 65
        assert path['distances'] == sorted(path['distances'])
        assert origin['timezone'] and destination['timezone']


def test_great_circle_is_curved_and_keeps_endpoints():
    origin, destination = [115.97, -31.94], [151.17, -33.95]
    points = great_circle(origin, destination)
    assert points[0] == origin and points[-1] == destination
    assert points[32][1] < (origin[1] + destination[1]) / 2


def test_flight_download_uses_existing_cache_and_rejects_wrong_dates(tmp_path, monkeypatch):
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE', str(tmp_path))
    app = Flask(__name__)
    replay_http.register_replay_routes(app)
    client = app.test_client()
    info = replay_http.descriptor('2013-03-04', 'australia_flights')
    result = client.get(info['url'], headers={'Accept-Encoding': 'gzip'})
    assert result.status_code == 200
    payload = json.loads(gzip.decompress(result.data))
    assert payload['loaded_modes'] == ['flight']
    assert payload['day_start_hour'] == 0
    assert payload['schedule']['note_messages']
    assert 'transit_patterns' not in payload
    assert client.get(info['url'], headers={'Accept-Encoding': 'gzip', 'If-None-Match': result.headers['ETag']}).status_code == 304
    assert client.get(info['url'].replace('2013-03-04', '2026-10-24')).status_code == 404
    assert client.get(info['url'].replace('modes=flight', 'modes=train')).status_code == 404
