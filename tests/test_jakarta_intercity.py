from collections import Counter
from datetime import date
import gzip
import hashlib
import json

import pytest
from dashboard import replay
from dashboard.cities import city_settings
from scripts.prepare_jakarta_intercity import (SOURCE,SOURCE_SHA256,GEOMETRY,GEOMETRY_SHA256,
    AIRPORT_CODES,airport_source_day,parse_airport_table,parse_whoosh_table)


def test_airport_calendar_uses_the_original_dates_and_does_not_duplicate_number_pairs():
    row=['','2','805A','806A','MRI-DU-BST','05:30','05:37','05:48','05:58','06:05','06:16',
         'Tidak Berjalan tanggal\n6,7,13,14,20,21,27,28\nSeptember 2025','']
    trips=parse_airport_table([row],AIRPORT_CODES)
    assert len(trips)==1 and trips[0]['number']=='805A' and trips[0]['published_numbers']==['805A','806A']
    assert trips[0]['calls'][0]==['MRI',19800,19800]
    assert str(airport_source_day(date(2025,12,20))) in trips[0]['excluded_dates']
    assert airport_source_day(date(2025,12,15))==date(2025,9,15)
    with pytest.raises(ValueError):airport_source_day(date(2026,1,1))
    row[11]='Does not run sometimes'
    with pytest.raises(ValueError):parse_airport_table([row],AIRPORT_CODES)


def test_whoosh_pass_throughs_and_real_arrival_departure_times():
    table=[['No','Stasiun','Jadwal',None,'Keterangan'],[None,None,'Datang','Berangkat',None],
        ['1','Tegalluar','-','06.05.00',''],['2','Padalarang','06.20.00','06.23.00',''],
        ['3','Karawang','Ls','06.39.00',''],['4','Halim','06.52.00','-','']]
    trip=parse_whoosh_table(table,'G1004','regular')
    assert [c for c,a,d in trip['calls']]==['TGR','PDL','HLM']
    assert trip['pass_throughs']==[['KRW',23940]]
    assert trip['calls'][1]==['PDL',22800,22980]
    assert trip['calls'][-1]==['HLM',24720,24720]


def test_source_pins_and_whoosh_scenarios_are_not_mixed():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()==GEOMETRY_SHA256
    with gzip.open(SOURCE,'rt') as stream:r=json.load(stream)
    assert Counter(t['calendar'] for t in r['trips'])=={'airport':70,'regular':62,'sunday':56}
    regular={t['number']:t for t in r['trips'] if t['calendar']=='regular'}
    sunday={t['number']:t for t in r['trips'] if t['calendar']=='sunday'}
    assert set(regular)=={'G'+str(n) for n in range(1003,1065)}
    assert set(sunday)=={'G'+str(n) for n in range(1009,1065)}
    assert all(sunday[n]['calls']==regular[n]['calls'] for n in sunday)
    assert r['metadata']['sunday_rule_published']=='2025-10-10'
    for rows,first_east,first_west in [(regular.values(),23100,21900),(sunday.values(),28800,27300)]:
        assert min(t['calls'][0][2] for t in rows if t['direction']=='whoosh-east')==first_east
        assert min(t['calls'][0][2] for t in rows if t['direction']=='whoosh-west')==first_west
    assert regular['G1003']['calls'][1]==['KRW',24000,24120]


def test_selected_replay_days_preserve_services_tracks_and_expanded_bounds():
    with gzip.open(replay.JAKARTA_PATH,'rt') as stream:r=json.load(stream)
    for day,expected in [('2025-12-15',(70,62)),('2025-12-20',(64,62)),('2025-12-21',(64,56))]:
        selected=replay.get_replay_day(day,'jakarta',modes=('train',))
        counts=Counter(selected['transit_patterns'][s['pattern']]['route_id'].split(':')[-1] for s in selected['services'])
        assert counts=={'airport':expected[0],'whoosh':expected[1]}
        assert all(s['mode']=='train' for s in selected['services'])
        assert len({s['id'] for s in selected['services']})==sum(expected)
    for p in r['patterns'].values():
        if p['mode']!='train':continue
        top=r['stop_patterns'][p['stop_pattern']]
        assert all(r['paths'][leg]['quality']=='track' and len(r['paths'][leg]['coordinates'])>=2 for leg in top['legs'])
        if p['operator']=='KCIC / Whoosh':
            assert len(top['stations']) in {3,4}
            length=sum(r['paths'][leg]['distances'][-1] for leg in top['legs'])
            assert 135000<length<150000
        else:
            assert p['operator']=='KAI Commuter' and len(top['stations'])==6
            assert 'Sudirman' not in {r['stations'][i]['name'] for i in top['stations']}
    (west,south),(east,north)=city_settings('jakarta')['bounds']
    for s in r['stations']:assert west<=s['lon']<=east and south<=s['lat']<=north
