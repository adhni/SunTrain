from collections import Counter
import gzip
import hashlib
import json

import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_java_regional import SOURCE,SOURCE_SHA256,operator_trip


def read(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def test_all_four_regions_cover_every_regular_number_section_once():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    source=read(SOURCE)
    assert len(source['trips'])==166
    assert source['metadata']['groups']=={'Merak':14,'Bandung':64,'Yogyakarta / Solo':37,'East Java':51}
    sections=[n for t in source['trips'] for n in t['number'].split('-')]
    assert len(sections)==len(set(sections))==190
    assert {t['name'] for t in source['trips']} >= {'Commuter Line Merak','Commuter Line Garut','Commuter Line Bandung Raya',
        'Commuter Line Walahar','Commuter Line Jatiluhur','Commuter Line Yogyakarta','Commuter Line Prameks Kutoarjo',
        'Commuter Line Dhoho','Commuter Line Penataran','Commuter Line Supas','Commuter Line Jenggala',
        'Commuter Line Arjonegoro','Commuter Line Blorasura','Pandanwangi'}
    assert {n for n in source['metadata']['omitted_trips']}=={'511F','512F','730F','731F','732F','733F'}
    assert not any(t['untimed_calls'] for t in source['trips'])
    assert all(not n.endswith('F') and int(n)<800 for n in sections)
    assert not any('Bogor' in t['name'] or 'Feeder' in t['name'] for t in source['trips'])


def test_published_operator_events_and_government_dwell_are_not_blended():
    source=read(SOURCE);trips={t['number']:t for t in source['trips']}
    assert trips['311']['calls'][1]==['KEN',19020,19140]
    assert trips['701']['calls'][2]==['SLO',18660,18780]
    bandung=trips['380']
    assert bandung['source_kind']=='operator' and bandung['calls'][0]==['PDL',14400,14400]
    assert all(a==d for c,a,d in bandung['calls'])
    overnight=trips['367']
    assert overnight['calls'][0]==['CCL',74700,74700] and overnight['calls'][-1]==['PWK',88500,88500]
    arjonegoro=trips['444-445']
    assert next(c for c in arjonegoro['calls'] if c[0]=='SBI')==['SBI',21540,21840]
    for trip in source['trips']:
        assert trip['calls'][0][1]==trip['calls'][0][2]
        assert trip['calls'][-1][1]==trip['calls'][-1][2]
        assert all(a<=d for c,a,d in trip['calls'])
        assert all(left[2]<=right[1] for left,right in zip(trip['calls'],trip['calls'][1:]))


def test_operator_parser_preserves_loops_real_dwell_and_rejects_guessed_events():
    t=operator_trip('401 - 402','Dhoho',[('SB','Surabaya Kota','23:00'),('KTS','Kertosono','00:30'),
        ('KTS','Kertosono','00:45'),('SB','Surabaya Kota','02:00')],'East Java',1)
    assert t['number']=='401-402'
    assert t['calls']==[['SB',82800,82800],['KTS',88200,89100],['SB',93600,93600]]
    assert [c for c,clock in t['route']]==['SB','KTS','SB']
    with pytest.raises(ValueError):operator_trip('123','Test',[('A','A','06:00'),('B','B','every 10 minutes')],'Test',1)


def test_regional_reference_paths_loops_and_business_day_ownership():
    r=read(replay.JAVA_REGIONAL_PATH)
    assert r['metadata']['track_coverage']=={'matched':2106,'total':2106}
    assert not r['metadata']['unresolved_geometry_patterns']
    for day,rows in r['days'].items():
        assert len(rows)==166 and len({(t,o) for p,t,o in rows})==166
        assert all(10800<=o<97200 for p,t,o in rows)
    trip=r['patterns']['java-rv-401-402'];top=r['stop_patterns'][trip['stop_pattern']]
    assert top['stations'][0]==top['stations'][-1]
    assert len(top['stations'])==48
    paths=[r['paths'][k] for k in top['legs']]
    assert 300000<sum(p['distances'][-1] for p in paths)<400000
    assert {'Kertosono','Blitar','Malang'} <= {r['stations'][i]['name'].title() for i in top['stations']}
    assert all(a['coordinates'][-1]==b['coordinates'][0] for a,b in zip(paths,paths[1:]))
    for p in r['patterns'].values():
        t=r['stop_patterns'][p['stop_pattern']]
        assert p['mode']=='regional_rail' and len(p['times'])==2*len(t['stations'])
        assert all(r['paths'][k]['quality']=='track' and r['paths'][k]['distances'][-1]>0 for k in t['legs'])


def test_regional_only_does_not_open_intercity_or_jakarta_and_combines_without_collisions(monkeypatch):
    replay.clear_replay_cache();opened=[];original=gzip.open
    def counted(path,*args,**kwargs):opened.append(str(path));return original(path,*args,**kwargs)
    with monkeypatch.context() as context:
        context.setattr(gzip,'open',counted)
        regional=replay.get_replay_day('2025-02-03','java',modes=['regional_rail'])
    assert opened==[str(replay.JAVA_REGIONAL_PATH)]
    assert len(regional['services'])==166 and not regional['schedule'].get('display_date_mapping')
    assert all(s['number']!=s['source_trip_id'] and 'stops' not in s for s in regional['services'])
    defaults=replay.get_replay_day('2025-02-03','java')
    assert Counter(s['mode'] for s in defaults['services'])=={'train':515,'regional_rail':166}
    all_modes=['train','regional_rail','commuter_rail','subway','light_rail']
    all_rail=replay.get_replay_day('2025-02-03','java',modes=all_modes)
    assert len(all_rail['services'])==2686 and len({s['id'] for s in all_rail['services']})==2686
    assert all_rail['schedule']['display_date_mapping']=={'2025-02-03':'2025-12-15'}
    for pattern in all_rail['transit_patterns'].values():
        topology=all_rail['transit_stop_patterns'][pattern['stop_pattern']]
        assert all(0<=s<len(all_rail['stations']) for s in topology['stations'])
        assert all(leg in all_rail['paths'] for leg in topology['legs'])
    sunday=replay.get_replay_day('2025-02-09','java')
    assert len(sunday['services'])==669
    assert sunday['end']>=max(s['departure']+int(sunday['transit_patterns'][s['pattern']]['times'][-1]) for s in sunday['services'])


def test_regional_reference_updates_invalidate_only_selected_modes(tmp_path,monkeypatch):
    path=tmp_path/'regional.json.gz';path.write_bytes(b'first')
    monkeypatch.setenv('SUNTRAIN_JAVA_REGIONAL_RAIL_REFERENCE',str(path))
    train=descriptor('2025-02-03','java',['train'])
    regional=descriptor('2025-02-03','java',['regional_rail'])
    default=descriptor('2025-02-03','java')
    path.write_bytes(b'updated')
    assert descriptor('2025-02-03','java',['train'])==train
    assert descriptor('2025-02-03','java',['regional_rail'])['revision']!=regional['revision']
    assert descriptor('2025-02-03','java')['revision']!=default['revision']
