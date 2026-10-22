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
    assert {p['line'].split()[1] for p in r['patterns'].values()}==set('123456789')
    assert any('express' in p['line'] for p in r['patterns'].values())
    assert all(p['mode']=='subway' and 'stop_pattern' in p for p in r['patterns'].values())
    assert all(not p['coordinates'] for p in r['paths'].values() if p['quality']=='approximate')
    for day in ['2025-10-20','2025-10-25','2025-10-26']:
        p=replay.get_replay_day(day,'seoul')
        assert len(p['services'])>3000
        assert len({s['id'] for s in p['services']})==len(p['services'])
        for s in p['services']:
            pattern=p['transit_patterns'][s['pattern']]
            assert p['start']<=s['departure']+int(pattern['times'][1])<p['end']
            assert not s['number'].startswith('seoul-')
        assert p['timezone']=='Asia/Seoul' and p['passenger_data'] is False
