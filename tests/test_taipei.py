from datetime import date
from collections import Counter
import gzip
import json
import pytest
from scripts.prepare_taipei_replay import departure,timetable_kind,OUTPUT
from dashboard import replay


def test_holiday_calendar_and_after_midnight_departures():
    assert timetable_kind(date(2026,10,26),'r')=='sunday'
    assert timetable_kind(date(2026,10,26),'bl')=='holiday'
    assert timetable_kind(date(2026,10,24),'r')=='saturday'
    assert timetable_kind(date(2026,10,27),'r')=='weekday'
    assert departure('{12,,,00:15,}')==87300
    assert departure('{12,,,24:15,}')==87300
    assert departure('{12,,,06:15,}')==22500
    with pytest.raises(ValueError):departure('{12,train,,06:15,}')


def test_bundled_metro_dates_routes_shared_geometry_and_scope():
    with gzip.open(OUTPUT,'rt') as f:r=json.load(f)
    assert r['metadata']['omitted_trips']=={}
    assert r['metadata']['unresolved_geometry_patterns']=={}
    assert all('stop_pattern' in p and p['mode']=='subway' for p in r['patterns'].values())
    assert {p['route_id'] for p in r['patterns'].values()}=={'R-1','R-2','R-3','G-1','G-2','G-3','O-1','O-2','BL-1','BL-2'}
    assert r['days']['2026-10-25']!=r['days']['2026-10-23']
    for day,count in [('2026-10-23',2333),('2026-10-24',2054),('2026-10-25',2035),('2026-10-26',2035),('2026-10-27',2333)]:
        p=replay.get_replay_day(day,'taipei')
        assert len(p['services'])==count
        assert len({s['id'] for s in p['services']})==count
        for s in p['services']:
            pattern=p['transit_patterns'][s['pattern']]
            assert p['start']<=s['departure']+int(pattern['times'][1])<p['end']
        assert p['timezone']=='Asia/Taipei' and p['passenger_data'] is False
        assert p['approximate_legs']==0
