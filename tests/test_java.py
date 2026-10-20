from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from zoneinfo import ZoneInfo

import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_java_connections import SOURCE as CONNECTIONS
from scripts.prepare_java_replay import (SOURCE, SOURCE_SHA256, GEOMETRY, GEOMETRY_SHA256,
    parse_pages, normalize_trip)


def test_pdf_visual_order_continuations_midnight_and_pass_throughs():
    pages=[(1,'KA 3 (Argo Bromo Anggrek) Relasi SBI-GMR\nNo. Stasiun dan Perhentian Datang Berangkat Keterangan\n'
        '1 Surabaya Pasarturi (SBI) 21:15:00\n2 Lamongan (LMG) Ls 21:40:00\n'
        '3 Semarang Tawang (SMT) 00:07:00 00:10:00\n6'),
        (2,'No. Stasiun dan Perhentian Datang Berangkat Keterangan\n4 Gambir (GMR) 05:00:00\n7')]
    parsed=parse_pages(pages)
    assert len(parsed)==1
    t=normalize_trip(parsed[0])
    assert t['calls']==[['SBI',76500,76500],['SMT',86820,87000],['GMR',104400,104400]]
    assert [c for c,clock in t['route']]==['SBI','LMG','SMT','GMR']
    assert t['untimed_calls']==[]
    parsed[0]['rows'][2]['events']='00:07:00 23:10:00'
    with pytest.raises(ValueError):normalize_trip(parsed[0])


def test_pinned_complete_intercity_source_and_explicit_exclusions():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()==GEOMETRY_SHA256
    with gzip.open(SOURCE,'rt') as stream:source=json.load(stream)
    assert source['metadata']['effective_from']=='2025-02-01'
    assert source['metadata']['extracted_tables']==297
    assert len(source['trips'])==253
    omitted=source['metadata']['omitted_trips']
    assert len([n for n in omitted if n.endswith('F')])==36
    assert {n for n in omitted if not n.endswith('F')}=={str(n) for n in range(223,231)}
    assert all(not t['untimed_calls'] and not t['number'].endswith('F') for t in source['trips'])
    assert len({t['name'] for t in source['trips']})==78
    assert {t['destination'] for t in source['trips']} >= {'GMR','BD','SMT','YK','SLO','SGU','ML','JR','KTG'}


def test_all_timed_legs_have_tracks_and_one_business_day_owner():
    with gzip.open(replay.JAVA_PATH,'rt') as stream:r=json.load(stream)
    assert r['metadata']['track_coverage']=={'matched':3350,'total':3350}
    with gzip.open(SOURCE,'rt') as stream:source=json.load(stream)
    with gzip.open(CONNECTIONS,'rt') as stream:connections=json.load(stream)
    source_trips={t['number']:t for t in source['trips']+connections['trips']}
    for day,rows in r['days'].items():
        assert len(rows)==383
        assert len({(t,o) for p,t,o in rows})==383
        assert all(10800<=offset<97200 for p,t,offset in rows)
        for p,t,offset in rows:
            source_trip=source_trips[r['train_numbers'][t]]
            pattern=r['patterns'][p];topology=r['stop_patterns'][pattern['stop_pattern']]
            assert len(topology['stations'])*2==len(pattern['times'])
            assert pattern['times'][0]==pattern['times'][1]==0
            assert pattern['times'][-2]==pattern['times'][-1]
            assert all(a<=b for a,b in zip(pattern['times'],pattern['times'][1:]))
            assert [r['stations'][s]['name'] for s in topology['stations']]==[source_trip['stations'][c] for c,a,d in source_trip['calls']]
            for leg in topology['legs']:
                path=r['paths'][leg]
                assert path['quality']=='track' and len(path['coordinates'])>=2
                assert len(path['coordinates'])==len(path['distances']) and path['distances'][-1]>0
    overnight=r['patterns']['java-3']
    assert overnight['times'][-1]==27900
    assert 'Ls' not in {s['name'] for s in r['stations']}


def test_java_reuses_jakarta_once_by_weekday_without_reading_unselected_java(monkeypatch):
    replay.clear_replay_cache();opened=[];original=gzip.open
    def counted(path,*a,**k):
        opened.append(str(path));return original(path,*a,**k)
    with monkeypatch.context() as context:
        context.setattr(gzip,'open',counted)
        combined=replay.get_replay_day('2025-02-03','java',modes=['commuter_rail','subway','light_rail'])
    assert opened==[str(replay.JAKARTA_PATH)]
    assert Counter(s['mode'] for s in combined['services'])=={'commuter_rail':1144,'subway':285,'light_rail':576}
    assert combined['schedule']['display_date_mapping']=={'2025-02-03':'2025-12-15'}
    zone=ZoneInfo('Asia/Jakarta')
    assert all(datetime.fromtimestamp(s['departure'],zone).strftime('%Y-%m-%d') in {'2025-02-03','2025-02-04'} for s in combined['services'])
    assert all('stops' not in s and s['number']!=s['source_trip_id'] for s in combined['services'])
    assert not list((replay.ROOT/'data/reference/java').glob('*jakarta*'))
    replay.clear_replay_cache();opened.clear()
    with monkeypatch.context() as context:
        context.setattr(gzip,'open',counted)
        full=replay.get_replay_day('2025-02-03','java',modes=['train','commuter_rail','subway','light_rail'])
    assert opened.count(str(replay.JAVA_PATH))==1 and opened.count(str(replay.JAKARTA_PATH))==1
    assert len(full['services'])==2520 and len({s['id'] for s in full['services']})==2520
    assert all(0<=s<len(full['stations']) for t in full['transit_stop_patterns'].values() for s in t['stations'])
    assert 'DJKA' in full['schedule']['attribution'] and 'MRT' in full['schedule']['attribution']
    assert all(k in full['paths'] for t in full['transit_stop_patterns'].values() for k in t['legs'])


def test_weekend_overlays_and_existing_jakarta_are_preserved():
    saturday=replay.get_replay_day('2025-02-08','java',modes=['train'])
    sunday=replay.get_replay_day('2025-02-09','java',modes=['train'])
    assert len(saturday['services'])==509 and len(sunday['services'])==503
    assert sunday['schedule']['display_date_mapping']=={'2025-02-09':'2025-12-21'}
    assert all(s['number'] not in {'805A','G1003'} for s in sunday['services'])
    assert sunday['end']==max(s['departure']+int(sunday['transit_patterns'][s['pattern']]['times'][-1]) for s in sunday['services'])
    assert sunday['end']>sunday['start']+86400
    original=replay.get_replay_day('2025-12-15','jakarta')
    assert len(original['services'])==2137 and original['business_date']=='2025-12-15'
    with pytest.raises(ValueError):replay.get_replay_day('2025-12-15','java')
    with pytest.raises(ValueError):descriptor('2025-02-03','java',['bus'])


def test_java_http_revisions_include_reused_reference_and_remain_compact(tmp_path,monkeypatch):
    path=tmp_path/'jakarta.json.gz';path.write_bytes(b'original')
    monkeypatch.setenv('SUNTRAIN_JAKARTA_REFERENCE',str(path))
    first=descriptor('2025-02-03','java')
    assert first['modes']==['regional_rail','train'] and len(json.dumps(first))<600
    path.write_bytes(b'updated reference')
    assert descriptor('2025-02-03','java')['revision']!=first['revision']
