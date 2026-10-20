from datetime import date,datetime
import gzip
import hashlib
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_jakarta_timetable import parse_table,extended_times,PDF_SHA256
from scripts.prepare_jakarta_replay import active,TIMETABLE,TIMETABLE_SHA256,GEOMETRY,GEOMETRY_SHA256


def test_pdf_grid_keeps_blank_branch_cells_and_pass_throughs():
    rows=[['NO.','NOMOR KA','RELASI','STASIUN',None,None,None,None,'KETERANGAN'],
          [None,None,None,'JNG','POK','MRI','KPB','JAKK',None],
          ['1','5505B - 5506','Ckr-Mri-Kpb','','','05:13','05:51','','Full Racket'],
          ['2','5021B','Bks-Mri-Ak','04:49','Ls','04:51','','','']]
    trips=parse_table(rows)
    assert trips[0]['number']=='5505B' and trips[0]['published_numbers']=='5505B - 5506'
    assert trips[0]['calls']==[['MRI',18780],['KPB',21060]]
    assert trips[1]['calls']==[['JNG',17340],['MRI',17460]]


def test_pdf_notice_excludes_non_passenger_positioning_and_keeps_weekday_flags():
    rows=[[None,None,None,'MRI','SUD','SUDB','KPB',None],
          ['1','5701B','Sud-Kpb','04:15','04:20','04:21','04:45','Mulai melayani pengguna dari St. Sudirman'],
          ['2','1153F','Dp-Jakk','04:10','','','05:08','Sabtu/Minggu/Libur Nasional Batal']]
    trips=parse_table(rows)
    assert trips[0]['calls'][0]==['SUD',15600]
    assert trips[1]['weekdays_only']
    assert active(trips[1],date(2025,12,15))
    assert not active(trips[1],date(2025,12,20))
    assert not active({**trips[0],'valid_through':'2025-12-16'},date(2025,12,17))
    with pytest.raises(ValueError):active(trips[0],date(2026,1,1))


def test_midnight_rollover_is_preserved_without_repairing_short_backwards_times():
    assert extended_times(['23:55','00:02','00:10'])==[86100,86520,87000]
    with pytest.raises(ValueError):extended_times(['06:30','06:29'])
    with pytest.raises(ValueError):extended_times(['06:70','07:00'])


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.JAKARTA_PATH,'rt') as f:return json.load(f)


def test_historical_provenance_and_complete_krl_scope(reference):
    assert hashlib.sha256(TIMETABLE.read_bytes()).hexdigest()==TIMETABLE_SHA256
    assert hashlib.sha256(GEOMETRY.read_bytes()).hexdigest()==GEOMETRY_SHA256
    meta=reference['metadata']
    assert meta['start_date']=='2025-12-15' and meta['end_date']=='2025-12-21'
    assert meta['timezone']=='Asia/Jakarta' and meta['sources'][0]['sha256']==PDF_SHA256
    assert meta['schedule_encoding']=='shared-stops-flat-times-v1'
    assert {p['line'] for p in reference['patterns'].values() if p['mode']=='commuter_rail'}=={'Bogor','Nambo','Cikarang','Rangkasbitung','Tangerang','Tanjung Priok'}
    assert all(p['operator']=='KAI Commuter' and 'stops' not in p for p in reference['patterns'].values() if p['mode']=='commuter_rail')
    names={s['name'] for s in reference['stations']}
    assert {'Bogor','Nambo','Cikarang','Bekasi','Rangkasbitung','Tangerang','Tanjung Priuk','Jakarta Kota','Pondok Rajeg','Karet'}<=names
    assert 'Gambir' not in names


def test_actual_pdf_calls_loop_branches_and_weekend_calendar(reference):
    with gzip.open(TIMETABLE,'rt') as f:raw=json.load(f)
    trips={t['number']:t for t in raw['trips']}
    assert trips['1151']['calls'][0]==['DP',14700]
    assert trips['1151']['calls'][-1]==['JAKK',18180]
    assert trips['5701B']['calls'][0][0]=='SUD'
    assert '5020A' not in trips
    assert raw['metadata']['omitted_rows'][0]['number']=='5020A'
    via_mri=trips['5505B']['calls'];assert 'MRI' in {c for c,t in via_mri} and 'PSE' not in {c for c,t in via_mri}
    assert any(t['line']=='Cikarang' and 'PSE' in {c for c,v in t['calls']} and 'MRI' not in {c for c,v in t['calls']} for t in trips.values())
    weekdays={t for p,t,o in reference['days']['2025-12-15']};weekend={t for p,t,o in reference['days']['2025-12-20']}
    assert 'krl:krl-1153F' in weekdays and 'krl:krl-1153F' not in weekend
    assert len(weekdays)>len(weekend)>1000


def test_occurrence_ownership_and_shared_paths(reference):
    occurrences=[];overnight=False
    for day,rows in reference['days'].items():
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Asia/Jakarta')).timestamp()
        for key,trip,offset in rows:
            p=reference['patterns'][key];times=p['times']
            assert 10800<=offset+times[1]<97200
            if p['operator']!='KCIC / Whoosh':
                assert times[::2]==times[1::2] # Other sources publish single events, not dwell durations.
            occurrences.append((trip,midnight+offset));overnight|=offset+times[-1]>86400
            topology=reference['stop_patterns'][p['stop_pattern']]
            assert len(topology['stations'])*2==len(times)
            assert len(topology['legs'])==len(topology['stations'])-1
    assert len(occurrences)==len(set(occurrences)) and overnight
    for path in reference['paths'].values():
        if path['quality']=='approximate':assert path['coordinates']==path['distances']==[]
        else:assert path['quality'] in {'track','shape'} and len(path['coordinates'])>=2


def test_selected_day_loader_and_supported_modes():
    day=replay.get_replay_day('2025-12-15','jakarta')
    assert day['services'] and day['timezone']=='Asia/Jakarta'
    assert {s['mode'] for s in day['services']}=={'commuter_rail','subway','light_rail','train'}
    assert all(s['source_trip_id'] for s in day['services'])
    assert descriptor('2025-12-15','jakarta')['modes']==['commuter_rail','light_rail','subway','train']
    with pytest.raises(ValueError):descriptor('2025-12-15','jakarta',['ferry'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-10-05','jakarta')


def test_mrt_snapshot_short_turns_and_mode_selection(reference):
    from scripts.prepare_jakarta_mrt import FEED,SHA256
    assert hashlib.sha256(FEED.read_bytes()).hexdigest()==SHA256
    assert reference['metadata']['operator_periods']['MRT Jakarta']['snapshot']=='2026-05-03'
    assert 'not a December 2025 reconstruction' in reference['metadata']['replay_note']
    for day,total in [('2025-12-15',285),('2025-12-21',219)]:
        rows=[r for r in reference['days'][day] if reference['patterns'][r[0]]['mode']=='subway']
        assert len(rows)==total
        assert len({(t,o) for p,t,o in rows})==total
        for key,trip,offset in rows:
            p=reference['patterns'][key]
            assert p['times'][::2]==p['times'][1::2]
            topology=reference['stop_patterns'][p['stop_pattern']]
            assert all(reference['paths'][leg]['coordinates'] for leg in topology['legs'])
        late=next(reference['patterns'][p] for p,t,o in rows if 'LBB-BKM-ST' in t)
        assert late['destination']=='Blok M'
        assert len(reference['stop_patterns'][late['stop_pattern']]['stations'])==6
        early=next(reference['patterns'][p] for p,t,o in rows if 'BKM-BHI-ST' in t)
        assert len(reference['stop_patterns'][early['stop_pattern']]['stations'])==8
    day=replay.get_replay_day('2025-12-15','jakarta',modes=('subway',))
    assert len(day['services'])==285
    assert all(s['mode']=='subway' and day['transit_patterns'][s['pattern']]['operator']=='MRT Jakarta' for s in day['services'])
    assert {p['direction'] for p in day['transit_patterns'].values()}=={'Northbound','Southbound'}
    krl=replay.get_replay_day('2025-12-15','jakarta',modes=('commuter_rail',))
    assert len(krl['services'])==1144
