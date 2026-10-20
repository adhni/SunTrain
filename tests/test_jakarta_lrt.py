from collections import Counter
import gzip
import hashlib
import json

from dashboard import replay
from scripts.prepare_jakarta_lrt import SOURCE, SOURCE_SHA256, GEOMETRY, GEOMETRY_SHA256


def test_lrt_source_preserves_calendars_grouped_station_clocks_and_provenance():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest() == GEOMETRY_SHA256
    with gzip.open(SOURCE, 'rt') as stream: source = json.load(stream)
    assert Counter(t['calendar'] for t in source['trips']) == {'WD':430, 'SAT':270, 'SUN':270}
    assert source['metadata']['source_updated_dates'] == ['2026-09-06','2026-09-27']
    assert len(source['metadata']['sources']) == 57
    assert source['metadata']['license'] == 'ODbL 1.0'
    assert source['metadata']['validation']['SAT'] == {'matched_official_departures':3242,'compared':3242}
    assert source['metadata']['validation']['WD'] == {'matched_official_departures':5033,'compared':5158}
    sample = next(t for t in source['trips'] if t['calendar']=='WD' and t['number']=='LRTJBDB-1001')
    assert sample['calls'][0] == ['DKA',21900] # 06:05, also in official station table.
    assert sample['calls'][-1] == ['BEK',24600] # 06:50; no invented terminal arrival.
    assert sample['destination']=='JTM' and len(sample['calls'])==13
    for t in source['trips']:
        assert t['destination'] not in {code for code,clock in t['calls']}
        assert all(a[1] < b[1] for a,b in zip(t['calls'],t['calls'][1:]))


def test_lrt_paths_and_independent_filters_preserve_last_published_calls():
    with gzip.open(replay.JAKARTA_PATH, 'rt') as stream: reference = json.load(stream)
    patterns = {key:p for key,p in reference['patterns'].items() if p['operator']=='LRT Jabodebek'}
    assert {p['line'] for p in patterns.values()} == {'LRT Cibubur','LRT Bekasi'}
    assert {p['color'] for p in patterns.values()} == {'#21409A','#006838'}
    assert all(p['terminal_arrival_missing'] for p in patterns.values())
    names = set()
    for pattern in patterns.values():
        stops = reference['stop_patterns'][pattern['stop_pattern']]
        names.update(reference['stations'][i]['name'] for i in stops['stations'])
        assert len(stops['stations']) in {11,13}
        assert len(stops['legs']) == len(stops['stations'])-1
        assert all(reference['paths'][leg]['quality']=='track' and len(reference['paths'][leg]['coordinates'])>=2 for leg in stops['legs'])
    assert len(names)==18
    occurrences=set()
    for day, rows in reference['days'].items():
        lrt = [r for r in rows if r[0] in patterns]
        assert len(lrt)==(270 if day in {'2025-12-20','2025-12-21'} else 430)
        for key,trip,offset in lrt:
            assert 10800 <= offset < 97200
            assert (day,trip,offset) not in occurrences
            occurrences.add((day,trip,offset))
    day = replay.get_replay_day('2025-12-15','jakarta',modes=('light_rail',))
    assert len(day['services'])==576 and all(s['mode']=='light_rail' for s in day['services'])
    assert sum(day['transit_patterns'][s['pattern']]['operator']=='LRT Jabodebek' for s in day['services'])==430
    assert {p['operator'] for p in day['transit_patterns'].values()}=={'LRT Jabodebek','LRT Jakarta'}
    assert 'last published call' in day['schedule']['replay_note']
    assert reference['metadata']['operator_periods']['LRT Jabodebek']['captured']=='2026-10-20'
