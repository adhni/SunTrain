from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_great_britain_replay import OPERATORS,SOURCE,selected_route,intercity_sequence,BritainRailGraph,geometry_resolver,follows_hints
from scripts.prepare_great_britain_geometry import speed


def test_intercity_scope_excludes_replacement_buses_and_london_duplicates():
    agencies={'='+code:{'agency_name':name} for code,name in OPERATORS.items()}
    for code in OPERATORS:
        assert selected_route({'agency_id':'='+code,'route_id':code,'route_type':'2'},agencies)
        assert not selected_route({'agency_id':'='+code,'route_id':code+'_RRB','route_type':'714'},agencies)
    for code in ['LO','XR','LT','NT','AW','CS']:
        assert not selected_route({'agency_id':'='+code,'route_id':code,'route_type':'2'},agencies)


def test_mixed_operators_keep_whole_intercity_journeys_and_exclude_local_runs():
    def selected(code,codes):
        stops={s:{'stop_code':s} for s in codes};seq=[{'stop_id':s} for s in codes]
        return intercity_sequence(code,seq,stops)
    assert len(selected('GW',['PAD','RDG','SWI','BTH','BRI']))==5
    assert len(selected('GW',['PAD','RDG','EXD','PLY','PNZ']))==5
    assert not selected('GW',['PLY','GNH','PNZ'])
    assert not selected('GW',['PAD','RDG','OXF'])
    assert len(selected('EM',['STP','LEI','DBY','SHF']))==4
    assert len(selected('EM',['DBY','SHF']))==2
    assert not selected('EM',['STP','BDM','COR'])
    assert not selected('EM',['NOT','MFT','NRW'])
    assert speed({'maxspeed':'125 mph'})==pytest.approx(201.168)
    assert speed({'maxspeed':'200'})==200


def test_connected_geometry_uses_track_curves_and_preserves_gaps():
    points=[[-1.0,52.0],[-1.0,52.001],[-0.999,52.001]]
    ways=[{'node_ids':['a','b','c'],'coordinates':points,'speed':100}]
    graph=BritainRailGraph(ways)
    assert graph.leg(points[0],points[-1])==points
    resolve=geometry_resolver({'ways':ways},{'shape':points})
    assert resolve({}, {'shape_id':'shape'},[],[points[0],points[-1]])[0]==points
    assert resolve({}, {'shape_id':'shape'},[],[points[0],[0,55]])==[None]


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.GREAT_BRITAIN_PATH,'rt') as f:return json.load(f)


def test_historical_week_operator_scope_and_shared_schedules(reference):
    meta=reference['metadata']
    assert meta['start_date']=='2026-10-05' and meta['end_date']=='2026-10-11'
    assert meta['timezone']=='Europe/London' and meta['sources'][0]['sha256']==SOURCE['sha256']
    assert meta['schedule_encoding']=='shared-stops-flat-times-v1'
    patterns=reference['patterns']
    assert {p['operator'] for p in patterns.values()}==set(OPERATORS.values())
    assert all(p['mode']=='train' and p['route_id'] in OPERATORS and p['direction']=='Not specified' and 'stops' not in p for p in patterns.values())
    names={s['name'].lower() for s in reference['stations']}
    for place in ['london','edinburgh','glasgow','cardiff','swansea','plymouth','manchester','leeds','york','newcastle']:
        assert any(place in s for s in names),place
    occurrences=[]
    for day,rows in reference['days'].items():
        assert len(rows)>500
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/London')).timestamp()
        for key,trip,offset in rows:
            assert 10800<=offset+patterns[key]['times'][1]<97200
            occurrences.append((trip,midnight+offset))
    assert len(occurrences)==len(set(occurrences))
    for path in reference['paths'].values():
        if path['quality']=='approximate':assert path['coordinates']==path['distances']==[]
        else:assert path['quality']=='track' and len(path['coordinates'])>=2


def test_day_endpoint_and_city_validation():
    day=replay.get_replay_day('2026-10-05','great_britain')
    assert day['services'] and day['timezone']=='Europe/London'
    assert descriptor('2026-10-05','great_britain')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2026-10-05','great_britain',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-01','great_britain')


def test_passing_point_hints_select_the_connected_corridor_not_a_shortcut():
    a=[-1,52];b=[-0.995,52.01];c=[-0.99,52]
    ways=[{'node_ids':['a','b','c'],'coordinates':[a,b,c],'speed':100},
          {'node_ids':['a','c'],'coordinates':[a,c],'speed':100}]
    resolve=geometry_resolver({'ways':ways},{'via':[a,b,c]})
    path=resolve({}, {'shape_id':'via'},[],[a,c])[0]
    assert any(point==pytest.approx(b) for point in path)


def test_flexible_station_tracks_cannot_bypass_the_documented_corridor():
    assert follows_hints([[-1,52],[-0.99,52]],[[-1,52],[-0.995,52.0001]])
    assert not follows_hints([[-1,52],[-0.99,52]],[[-0.995,52.01]])


def test_regional_brands_use_their_actual_operator_and_exclude_tfl():
    from scripts.prepare_great_britain_replay import REGIONAL_ROUTES
    agencies={'='+agency:{'agency_name':name} for agency,name in REGIONAL_ROUTES.values()}
    for code,(agency,name) in REGIONAL_ROUTES.items():
        assert selected_route({'agency_id':'='+agency,'route_id':code,'route_type':'2'},agencies,regional=True)
        assert not selected_route({'agency_id':'='+agency,'route_id':code,'route_type':'714'},agencies,regional=True)
    for code,agency in [('LIB','LO'),('XR','XR'),('tfl_DLR','DLR'),('GW','GW'),('CS','CS')]:
        assert not selected_route({'agency_id':'='+agency,'route_id':code,'route_type':'2'},agencies,regional=True)


def test_regional_daily_bundles_are_separate_from_existing_london_and_intercity(reference):
    from scripts.prepare_great_britain_replay import REGIONAL_ROUTES
    from pathlib import Path
    paths=sorted((replay.ROOT/'data/reference/great_britain/regional_rail').glob('*.json.gz'))
    assert len(paths)==7
    occurrences=[];regional_trips=set();operators=set()
    with gzip.open(replay.LONDON_PATH,'rt') as f:london=json.load(f)
    london_trips={t for rows in london['days'].values() for p,t,o in rows}
    for path in paths:
        with gzip.open(path,'rt') as f:r=json.load(f)
        assert list(r['days'])==[path.name[:10]]
        assert r['metadata']['schedule_encoding']=='shared-stops-flat-times-v1'
        assert set(r['patterns']).isdisjoint(reference['patterns'])
        assert set(r['stop_patterns']).isdisjoint(reference['stop_patterns'])
        assert {p['route_id'] for p in r['patterns'].values()}<=set(REGIONAL_ROUTES)
        assert all(p['mode']=='regional_rail' for p in r['patterns'].values())
        for day,rows in r['days'].items():
            midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/London')).timestamp()
            for p,t,o in rows:
                pattern=r['patterns'][p];operators.add(pattern['operator'])
                assert 10800<=o+pattern['times'][1]<97200
                occurrences.append((t,midnight+o));regional_trips.add(t)
    assert operators=={name for agency,name in REGIONAL_ROUTES.values()}
    assert not regional_trips&london_trips
    assert not regional_trips&{t for rows in reference['days'].values() for p,t,o in rows}
    assert len(occurrences)==len(set(occurrences))


def test_optional_regional_loading_and_combined_shared_indices(monkeypatch):
    replay.clear_replay_cache()
    original_open=gzip.open
    def selected_only(path,*args,**kwargs):
        assert str(path) not in {str(replay.GREAT_BRITAIN_PATH),str(replay.LONDON_PATH)}
        return original_open(path,*args,**kwargs)
    with monkeypatch.context() as context:
        context.setattr(gzip,'open',selected_only)
        regional=replay.get_replay_day('2026-10-05','great_britain',modes=['regional_rail'])
    base=replay.get_replay_day('2026-10-05','great_britain')
    merged=replay.get_replay_day('2026-10-05','great_britain',modes=['train','regional_rail'])
    assert len(base['services'])==1689
    assert len(merged['services'])==len(base['services'])+len(regional['services'])
    assert len({s['id'] for s in merged['services']})==len(merged['services'])
    assert all(s['mode']=='regional_rail' and s['source_trip_id'] for s in regional['services'])
    for s in merged['services']:
        p=merged['transit_patterns'][s['pattern']];topology=merged['transit_stop_patterns'][p['stop_pattern']]
        assert all(0<=station<len(merged['stations']) for station in topology['stations'])
        assert all(leg in merged['paths'] for leg in topology['legs'])


def test_intercity_descriptor_does_not_depend_on_unselected_regional_files(tmp_path,monkeypatch):
    directory=tmp_path/'regional';directory.mkdir();p=directory/'2026-10-05.json.gz';p.write_bytes(b'first')
    monkeypatch.setenv('SUNTRAIN_GREAT_BRITAIN_REGIONAL_RAIL_REFERENCE',str(directory))
    before=descriptor('2026-10-05','great_britain')
    selected=descriptor('2026-10-05','great_britain',['regional_rail'])
    p.write_bytes(b'updated-source')
    assert descriptor('2026-10-05','great_britain')==before
    assert descriptor('2026-10-05','great_britain',['regional_rail'])['revision']!=selected['revision']


def test_gb_london_rail_reuses_one_existing_file_and_preserves_attribution(monkeypatch):
    replay.clear_replay_cache()
    london_modes=['subway','light_rail','commuter_rail']
    files=replay.rail_reference_files('great_britain','2026-10-05',london_modes)
    assert len(files)==3 and {path for mode,path,stamp in files}=={str(replay.LONDON_PATH)}
    original_open=gzip.open;opened=[]
    def counted_open(path,*args,**kwargs):
        opened.append(str(path));return original_open(path,*args,**kwargs)
    with monkeypatch.context() as context:
        context.setattr(gzip,'open',counted_open)
        london_in_gb=replay.get_replay_day('2026-10-05','great_britain',modes=london_modes)
    assert opened==[str(replay.LONDON_PATH)]
    london=replay.get_replay_day('2026-10-05','london')
    assert len(london_in_gb['services'])==len(london['services'])
    assert london_in_gb['city']=='great_britain'
    assert {s['mode'] for s in london_in_gb['services']}==set(london_modes)
    assert 'Powered by TfL Open Data' in london_in_gb['schedule']['attribution']
    merged=replay.get_replay_day('2026-10-05','great_britain',modes=['train','regional_rail',*london_modes])
    assert len(merged['services'])==17879+len(london['services'])
    assert len({(s['source_trip_id'],s['departure']) for s in merged['services']})==len(merged['services'])
    assert 'Powered by TfL Open Data' in merged['schedule']['attribution']
    assert 'Rail Delivery Group' in merged['schedule']['attribution']
    assert 'Geomni' in merged['schedule']['attribution']
    for s in merged['services']:
        p=merged['transit_patterns'][s['pattern']];sp=merged['transit_stop_patterns'][p['stop_pattern']]
        assert len(sp['stations'])*2==len(p['times'])
        assert all(0<=i<len(merged['stations']) for i in sp['stations'])
        assert all(leg in merged['paths'] for leg in sp['legs'])


def test_gb_london_reference_change_only_invalidates_selected_london_modes(tmp_path,monkeypatch):
    path=tmp_path/'london.json.gz';path.write_bytes(b'first')
    monkeypatch.setenv('SUNTRAIN_LONDON_REFERENCE',str(path))
    default=descriptor('2026-10-05','great_britain')
    selected=descriptor('2026-10-05','great_britain',['commuter_rail'])
    path.write_bytes(b'updated')
    assert descriptor('2026-10-05','great_britain')==default
    assert descriptor('2026-10-05','great_britain',['commuter_rail'])['revision']!=selected['revision']
