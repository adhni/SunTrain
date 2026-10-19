from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_luxembourg_replay import SOURCE,GEOMETRY,GEOMETRY_SHA256,selected_route,domestic_sequence,verify_timezone


def test_rail_scope_rejects_replacement_buses_trams_and_other_agencies():
    agencies={'11':{'agency_name':'Chemins de Fer Luxembourgeois'},'171':{'agency_name':'Société Nationale des Chemins de Fer Luxembourgeois'}}
    route={'agency_id':'11','route_type':'2','route_short_name':'RB'}
    for category in ['RB','RE','IC','TER','TGV']:
        assert selected_route({**route,'route_short_name':category},agencies)
    for change in [{'route_type':'3'},{'route_type':'0'},{'agency_id':'171'},{'route_short_name':'BUS'}]:
        assert not selected_route({**route,**change},agencies)


def test_domestic_and_source_border_calls_keep_original_order_and_times():
    ids=['000400000071','000400000098','000400000064','000220102018','000200405060']
    calls=[{'stop_id':s,'arrival_time':str(i)} for i,s in enumerate(ids)]
    assert domestic_sequence(calls)==calls[2:]
    assert domestic_sequence(calls[::-1])==calls[2:][::-1]
    assert domestic_sequence([calls[-1]])==[]
    assert domestic_sequence([])==[]


def test_source_timezone_alias_is_verified_for_the_entire_window(monkeypatch):
    verify_timezone()
    monkeypatch.setitem(SOURCE,'timezone','UTC')
    with pytest.raises(ValueError,match='timezones disagree'):verify_timezone()


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.LUXEMBOURG_PATH,'rt') as f:return json.load(f)


def test_dated_sources_compact_schedules_and_nationwide_coverage(reference):
    meta=reference['metadata']
    assert file_hash(GEOMETRY)==GEOMETRY_SHA256
    assert meta['sources'][0]['sha256']==SOURCE['sha256']
    assert meta['sources'][0]['source_date']=='2026-05-28'
    assert meta['start_date']=='2026-06-01' and meta['end_date']=='2026-06-07'
    assert meta['timezone']=='Europe/Luxembourg' and meta['source_timezone']=='Europe/Berlin'
    assert meta['license']=='CC BY 4.0' and meta['geometry_license']=='CC0 1.0'
    assert meta['schedule_encoding']=='shared-stops-flat-times-v1' and not meta['omitted_trips']
    assert {p['category'] for p in reference['patterns'].values()}=={'RB','RE','TER','IC','TGV'}
    assert all(p['mode']=='train' and p['operator']=='CFL' and 'stops' not in p for p in reference['patterns'].values())
    names={s['name'] for s in reference['stations']}
    for place in ['Luxembourg','Troisvierges','Clervaux','Wiltz','Diekirch','Wasserbillig','Rodange','Rumelange','Dudelange','Esch-sur-Alzette']:
        assert any(n.startswith(place) for n in names),place
    assert not {'Metz-Ville, Gare','Thionville, Gare','Trier, Hauptbahnhof','Arlon, Gare'} & names


def test_overnight_occurrences_are_unique_and_geometry_never_uses_gtfs_sketches(reference):
    counts=[];instances=[];overnight=False;good=total=0;gaps=set()
    for day,rows in reference['days'].items():
        counts.append(len(rows));midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Luxembourg')).timestamp()
        for k,t,o in rows:
            p=reference['patterns'][k];times=p['times']
            assert 10800<=o+times[1]<97200
            instances.append((t,midnight+o));overnight|=o+times[-1]>86400
            stops=reference['stop_patterns'][p['stop_pattern']]
            for i,leg in enumerate(stops['legs']):
                path=reference['paths'][leg];total+=1
                if path['quality']=='approximate':
                    assert path['coordinates']==path['distances']==[]
                    gaps.add(tuple(reference['stations'][j]['name'] for j in stops['stations'][i:i+2]))
                else:
                    good+=1;assert path['quality']=='track' and len(path['coordinates'])>=2
    assert counts==[990,990,990,990,996,718,542]
    assert len(instances)==len(set(instances)) and overnight
    assert good==43024 and total==43827 and good/total>.98
    assert all(any('Audun-le-Tiche' in s or 'Volmerange-les-Mines' in s for s in pair) for pair in gaps)
    for category in ['RE','IC','TGV']:
        paths=[reference['paths'][l] for p in reference['patterns'].values() if p['category']==category
            for l in reference['stop_patterns'][p['stop_pattern']]['legs']]
        assert any(len(p['coordinates'])>20 for p in paths)


def test_loader_filters_and_independence_from_melbourne(monkeypatch):
    monkeypatch.setattr(replay.data,'get_metadata',lambda:pytest.fail('Luxembourg queried Melbourne'))
    day=replay.get_replay_day('2026-06-01','luxembourg')
    assert len(day['services'])==990 and day['timezone']=='Europe/Luxembourg'
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert not city_settings('luxembourg')['passenger_data']
    assert descriptor('2026-06-01','luxembourg')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2026-06-01','luxembourg',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-08','luxembourg')
