"""Taiwan source calendar, overnight and bundled replay integration checks."""
from collections import Counter
from datetime import date
import gzip
import json
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_taiwan_replay import category,operation_dates,seconds,unroll,via_point,OUTPUT


def test_holiday_date_lists_and_ranges_do_not_create_daily_specials():
    assert operation_dates('10/23, 10/25~10/27')=={date(2026,10,d) for d in [23,25,26,27]}
    assert len(operation_dates(''))==5
    for value in ['weekdays','10/22','10/27~10/23','10/28']:
        with pytest.raises(ValueError):operation_dates(value)


def test_source_clocks_preserve_dwell_and_midnight_without_hiding_bad_rows():
    assert seconds('19:48:30')==71310
    assert unroll([(85800,85830),(300,330)])==[[85800,85830],[86700,86730]]
    for pairs in [[(36000,35900)],[(300,200)],[(86300,86300),(100,100),(50,50)]]:
        with pytest.raises(ValueError):unroll(pairs)
    with pytest.raises(ValueError):seconds('24:00:00')


def test_passenger_categories_exclude_freight_empty_stock_and_parcels():
    assert category('1131')[0]=='Local'
    assert category('1132')[0]=='Fast local'
    assert category('110G')[0]=='Tze-Chiang / express'
    for code in ['1270','1280','12A0','1152','4200']:assert category(code) is None


def test_bundled_taiwan_calendar_numbers_and_mode_isolation():
    with gzip.open(OUTPUT,'rt') as f:reference=json.load(f)
    assert len(reference['days'])==5
    assert reference['metadata']['conversion_omissions'].get('Missing source station',0)==0
    assert reference['metadata']['omitted_trips']=={}
    for day,expected in [('2026-10-23',187),('2026-10-24',170),('2026-10-25',192),('2026-10-26',197),('2026-10-27',155)]:
        payload=replay.get_replay_day(day,'taiwan')
        counts=Counter(s['mode'] for s in payload['services'])
        assert counts['high_speed_rail']==expected
        assert counts['train']>900
        assert len({s['id'] for s in payload['services']})==len(payload['services'])
        for service in payload['services']:
            p=payload['transit_patterns'][service['pattern']]
            departure=service['departure']+int(p['times'][1])
            assert payload['start']<=departure<payload['start']+86400
            assert payload['end']>=service['departure']+int(p['times'][-1])
            assert not service['number'].startswith(('tra-','thsr-'))
            assert p['operator'] in {'Taiwan Railways','Taiwan High Speed Rail'}
        assert descriptor(day,'taiwan')['modes']==['high_speed_rail','train']
    only=replay.get_replay_day('2026-10-23','taiwan',modes=('high_speed_rail',))
    assert len(only['services'])==187 and {s['mode'] for s in only['services']}=={'high_speed_rail'}
    assert only['timezone']=='Asia/Taipei' and only['passenger_data'] is False
    assert all('stop_pattern' in p and 'stops' not in p for p in reference['patterns'].values())
    assert all(not p['coordinates'] for p in reference['paths'].values() if p['quality']=='approximate')


def test_mountain_and_coast_hints_do_not_change_other_corridors():
    south,north=(120.53,24.08),(120.88,24.68)
    assert via_point('1',south,north)==[120.68691,24.13728]
    assert via_point('2',north,south)==[120.55752,24.23702]
    assert via_point('0',south,north) is None
    assert via_point('1',(121.5,24),(121.6,24.5)) is None
    assert via_point('1',(120.6,23),(120.7,23.5)) is None
