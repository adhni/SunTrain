import json
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from scripts.prepare_google_flights import parse_results, ZONES


def segment(origin='MEL', destination='SYD', departure=None, arrival=None, duration=90, carrier='QF', number='400'):
    row = [None] * 33
    row[3], row[6], row[8], row[10], row[11] = origin, destination, departure or [6, None], arrival or [7, 30], duration
    row[17], row[20], row[21], row[22] = 'Boeing 737', [2026, 11, 2], [2026, 11, 2], [carrier, number, None, 'Qantas']
    return row


def scripts(*rows):
    return ["AF_initDataCallback({key: 'ds:1', hash: '5', data:" + json.dumps([rows]) + ', sideChannel:{}});']


def test_exact_airports_keep_mel_and_avv_separate_and_do_not_mix_connecting_segments():
    rows = scripts(segment(), segment('AVV'), segment('MEL', 'BNE', duration=30))
    mel = parse_results(rows, 'MEL', 'SYD', '2026-11-02')
    avv = parse_results(rows, 'AVV', 'SYD', '2026-11-02')
    assert len(mel) == len(avv) == 1
    assert mel[0]['origin'] == 'MEL' and avv[0]['origin'] == 'AVV'
    assert mel[0]['id'] != avv[0]['id']


def test_published_identity_zero_minutes_and_duplicate_search_options():
    row = segment()
    flights = parse_results(scripts(row, row), 'MEL', 'SYD', '2026-11-02')
    assert len(flights) == 1 and flights[0]['number'] == 'QF400'
    assert datetime.fromtimestamp(flights[0]['departure'], ZoneInfo('Australia/Melbourne')).strftime('%H:%M') == '06:00'
    assert not parse_results(scripts(row), 'MEL', 'SYD', '2026-11-03')


def test_half_hour_zone_is_verified_against_published_duration():
    assert ZONES['BHQ'] == 'Australia/Broken_Hill'
    row = segment('BHQ', 'SYD', [10, None], [12, 30], 120)
    assert len(parse_results(scripts(row), 'BHQ', 'SYD', '2026-11-02')) == 1
    row[11] = 150
    with pytest.raises(ValueError, match='duration differs'):
        parse_results(scripts(row), 'BHQ', 'SYD', '2026-11-02')


def test_conflicting_times_are_not_silently_merged():
    row = segment()
    other = segment(departure=[8,None], arrival=[9,30])
    with pytest.raises(ValueError, match='Conflicting'):
        parse_results(scripts(row, other), 'MEL', 'SYD', '2026-11-02')
