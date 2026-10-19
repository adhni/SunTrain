from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from scripts.prepare_portugal_replay import SOURCES,selected_route


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.PORTUGAL_PATH,'rt') as f:return json.load(f)


def test_porto_single_agency_and_rail_scope():
    agencies={'':{'agency_name':'Metro do Porto'}}
    route={'route_id':'Bexp','route_type':'1','route_short_name':'Bx'}
    assert selected_route('porto',route,agencies)
    for change in [{'route_type':'3'},{'route_type':'0'},{'route_id':'Metrobus'},{'agency_id':'other'}]:
        assert not selected_route('porto',{**route,**change},agencies)
    assert not selected_route('porto',route,{'':{'agency_name':'Changed operator'}})


def test_dated_porto_feed_all_lines_colours_and_express_calls(reference):
    source=SOURCES['porto'];meta=reference['metadata']
    assert any(s['sha256']==source['sha256'] and s['published']=='2026-04-07' for s in meta['sources'])
    assert source['license']==source['geometry_license']=='CC0 1.0'
    assert 'Metro do Porto, SA' in meta['attribution']
    patterns=[p for p in reference['patterns'].values() if p['operator']=='Porto Metro']
    assert all(p['mode']=='subway' for p in patterns)
    assert {(p['line'],p['color']) for p in patterns}=={
        ('Porto A','#199FDA'),('Porto B','#C63920'),('Porto B express','#C63920'),
        ('Porto C','#A3BE31'),('Porto D','#EBBC14'),('Porto E','#736EB0'),('Porto F','#EE731C')}
    counts=lambda category:[len(reference['stop_patterns'][p['stop_pattern']]['stations']) for p in patterns if p['category']==category]
    assert max(counts('B express'))<max(counts('B'))
    names={reference['stations'][i]['name'] for p in patterns for i in reference['stop_patterns'][p['stop_pattern']]['stations']}
    assert {'ISMAI','Aeroporto','Campanhã','Trindade','Póvoa de Varzim'}<=names
    assert len(names)==85 and not meta['omitted_trips']


def test_porto_holiday_calendar_overnight_and_unique_occurrences(reference):
    counts=[];occurrences=[];overnight=False
    for day,rows in reference['days'].items():
        rows=[(k,t,o) for k,t,o in rows if reference['patterns'][k]['operator']=='Porto Metro']
        counts.append(len(rows));midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Lisbon')).timestamp()
        for k,t,o in rows:
            times=reference['patterns'][k]['times']
            assert 10800<=o+times[1]<97200
            occurrences.append((t,midnight+o));overnight|=o+times[-1]>86400
    assert counts==[1153,1153,1153,924,1153,918,870]
    assert len(occurrences)==len(set(occurrences)) and overnight


def test_truncated_c_shape_keeps_missing_north_empty_and_retains_supported_suffix(reference):
    patterns=[p for p in reference['patterns'].values() if p['operator']=='Porto Metro' and p['origin']=='ISMAI']
    assert patterns
    for p in patterns:
        calls=reference['stop_patterns'][p['stop_pattern']]
        paths=[reference['paths'][l] for l in calls['legs']]
        assert len(paths)==23
        assert all(p['quality']=='approximate' and p['coordinates']==[] for p in paths[:4])
        assert all(p['quality']=='shape' and len(p['coordinates'])>=2 for p in paths[4:])
    # The opposite direction retains the complete source shape.
    reverse=[p for p in reference['patterns'].values() if p['operator']=='Porto Metro' and p['destination']=='ISMAI']
    assert reverse
    assert all(reference['paths'][l]['quality']=='shape' for p in reverse for l in reference['stop_patterns'][p['stop_pattern']]['legs'])


def test_combined_metro_mode_preserves_lisbon_and_train_counts():
    day=replay.get_replay_day('2026-06-01','portugal')
    counts={name:sum(day['transit_patterns'][s['pattern']]['operator']==name for s in day['services'])
        for name in ['CP','Fertagus','Lisbon Metro','Porto Metro']}
    assert counts=={'CP':1361,'Fertagus':156,'Lisbon Metro':1532,'Porto Metro':1153}
    assert len(day['services'])==4202
