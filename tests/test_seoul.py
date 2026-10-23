import gzip
import json
import pytest
from scripts.prepare_seoul_replay import call_times,clock,OUTPUT
from dashboard import replay


def test_source_clocks_and_missing_endpoint_companions():
    assert call_times('12:53:00','12:53:30')==(46380,46410,False)
    assert call_times('','05:30:00')==(19800,19800,True)
    assert call_times('14:01:00','')==(50460,50460,True)
    assert call_times('00:00:00','12:01:00')==(43260,43260,True)
    assert call_times('24:10:00','24:10:30')==(87000,87030,False)
    assert call_times('00:10:00','00:10:30')==(87000,87030,False)
    for pair in [('',''),('12:00:00','11:59:00')]:
        with pytest.raises(ValueError):call_times(*pair)
    with pytest.raises(ValueError):clock('25:65:00')


def test_bundled_seoul_ownership_scope_geometry_and_train_identity():
    with gzip.open(OUTPUT,'rt') as f:r=json.load(f)
    assert len(r['days'])==7
    assert {p['line'].split()[1] for p in r['patterns'].values() if p['mode']=='subway'}==set('123456789')
    assert any('express' in p['line'] for p in r['patterns'].values())
    assert {p['mode'] for p in r['patterns'].values()}=={'subway','commuter_rail'}
    assert all('stop_pattern' in p for p in r['patterns'].values())
    assert all(not p['coordinates'] for p in r['paths'].values() if p['quality']=='approximate')
    for day in ['2026-01-05','2026-01-10','2026-01-11']:
        p=replay.get_replay_day(day,'seoul')
        assert len(p['services'])>3000
        assert len({s['id'] for s in p['services']})==len(p['services'])
        for s in p['services']:
            pattern=p['transit_patterns'][s['pattern']]
            assert p['start']<=s['departure']+int(pattern['times'][1])<p['end']
            assert not s['number'].startswith('seoul-')
        assert p['timezone']=='Asia/Seoul' and p['passenger_data'] is False


def test_suburban_matrix_separate_horizontal_blocks_and_calendars():
    from scripts.prepare_seoul_suburban import matrix_trips
    a = [
        ['시발역', '문산', None, '시발역', '서울', None],
        ['종착역', '서울', None, '종착역', '문산', None],
        ['열차번호', 'K2201', None, '열차번호', 'K2202', None],
        ['문산', '', None, '서울', '', None],
        [None, {'time': 18000}, None, None, {'time': 20000}, None],
        ['서울', {'time': 20000}, None, '문산', {'time': 22000}, None],
        [None, '', None, None, '', None],
    ]
    t = matrix_trips({'경춘선 광운대시종착(평)': a}, 'gyeongchun')
    assert len(t) == 2
    assert [r['number'] for r in t] == ['K2201', 'K2202']
    assert [r['calls'][0][0] for r in t] == ['문산', '서울']
    assert all(r['days'] == (0,1,2,3,4) for r in t)
    assert matrix_trips({'휴일상행': a}, 'gyeongchun')[0]['days'] == (5,6)


def test_incomplete_suburban_journeys_are_audited_without_invented_calls():
    from scripts.prepare_seoul_suburban import matrix_trips
    from collections import Counter
    a = [['시발역','서울'], ['종착역','고색'], ['열차번호','K6043'],
         ['서울',''], [None,{'time':18000}], ['수원',{'time':20000}], [None,{'time':20030}]]
    with pytest.raises(ValueError): matrix_trips({'평일하행':a}, 'suin-bundang')
    audit=Counter()
    assert matrix_trips({'평일하행':a}, 'suin-bundang',audit)==[]
    assert audit=={'suin-bundang:Incomplete suburban journey':1}


def test_bundled_suburban_scope_and_mode_isolation():
    from collections import Counter
    day=replay.get_replay_day('2026-01-05','seoul')
    counts=Counter(day['transit_patterns'][s['pattern']]['line'] for s in day['services'] if s['mode']=='commuter_rail')
    assert set(counts)=={'Gyeongui–Jungang','Suin–Bundang','Gyeongchun','AREX express','AREX all-stop'}
    assert counts['AREX express']==56 and counts['AREX all-stop']==369
    assert all(v>100 for k,v in counts.items() if not k.startswith('AREX'))
    assert len(replay.get_replay_day('2026-01-05','seoul',modes=('subway',))['services'])==4715
    suburban=replay.get_replay_day('2026-01-05','seoul',modes=('commuter_rail',))
    assert len(suburban['services'])==sum(counts.values())
    assert all(s['number'].startswith(('K','A')) for s in suburban['services'])
    assert all(p['operator'] in {'KORAIL','AREX'} for p in suburban['transit_patterns'].values())
    assert not any(p['line']=='ITX-Cheongchun' for p in day['transit_patterns'].values())
    with gzip.open(OUTPUT,'rt') as f:r=json.load(f)
    assert r['metadata']['suburban_unlocated_station_trip_exclusions']=={}
    assert r['metadata']['suburban_source_audit']=={'suin-bundang:Incomplete suburban journey':1}


def test_arex_clocks_stopping_patterns_midnight_and_weekday_overlay():
    from datetime import date
    from scripts.prepare_arex_replay import seconds
    assert seconds('00:00:00')==0 and seconds('24:30:30')==88230
    assert seconds('---') is None
    with pytest.raises(ValueError): seconds('12:65:00')
    for d,expected in [('2026-01-05',425),('2026-01-10',377)]:
        day=replay.get_replay_day(d,'seoul')
        services=[s for s in day['services'] if day['transit_patterns'][s['pattern']]['operator']=='AREX']
        assert len(services)==expected
        express=[s for s in services if day['transit_patterns'][s['pattern']]['line']=='AREX express']
        assert len(express)==56
        assert all(len(day['transit_stop_patterns'][day['transit_patterns'][s['pattern']]['stop_pattern']]['stations'])==3 for s in express)
        midnight=next(s for s in services if s['number']=='A3293')
        pattern=day['transit_patterns'][midnight['pattern']]
        assert (pattern['origin'],pattern['destination'])==('서울','검암')
        assert midnight['departure']+int(pattern['times'][1])==day['start']+21*3600
        mapped=day['schedule']['arex_display_date_mapping'][d]
        assert date.fromisoformat(mapped).weekday()==date.fromisoformat(d).weekday()
        assert mapped.startswith('2026-10-')
        assert 'October 2026' in day['schedule']['replay_note']
