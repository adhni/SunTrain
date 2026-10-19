from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo
import pytest
from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_portugal_replay import selected_route,SOURCES


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.PORTUGAL_PATH,'rt') as f:return json.load(f)


def test_lisbon_scope_excludes_other_transport_and_unknown_lines():
    agencies={'ML':{'agency_name':'Metropolitano de Lisboa, E.P.E.'}}
    route={'agency_id':'ML','route_type':'1','route_id':'A','route_long_name':'Azul'}
    assert selected_route('lisbon',route,agencies)
    for change in [{'route_type':'3'},{'route_type':'0'},{'route_id':'future'},{'agency_id':'other'},{'route_long_name':'changed'}]:
        assert not selected_route('lisbon',{**route,**change},agencies)


def test_historical_metro_source_and_native_geometry(reference):
    meta=reference['metadata'];source=SOURCES['lisbon']
    archive=next(s for s in meta['sources'] if s['sha256']==source['sha256'])
    assert archive['source_date']=='2026-05-01'
    assert archive['valid_from']=='20260101' and archive['valid_through']=='20261231'
    assert any(s['sha256']==source['sha256'] and 'NAP declaration' in s['license'] for s in meta['schedule_licenses'])
    patterns=[p for p in reference['patterns'].values() if p['operator']=='Lisbon Metro']
    assert {p['operator'] for p in patterns}=={'Lisbon Metro'}
    assert {(p['line'],p['color'].lower()) for p in patterns}=={
        ('Lisbon Azul','#6699cc'),('Lisbon Amarela','#ffcc00'),('Lisbon Verde','#00cc99'),('Lisbon Vermelha','#ff3366')}
    stations=set()
    for p in patterns:
        calls=reference['stop_patterns'][p['stop_pattern']]
        stations.update(reference['stations'][s]['name'] for s in calls['stations'])
        for leg in calls['legs']:
            path=reference['paths'][leg]
            assert path['quality']=='shape' and len(path['coordinates'])>=2
    assert {'Aeroporto','Reboleira','Odivelas','Telheiras','Cais do Sodré','Santa Apolónia','Rato'}<=stations
    assert len(stations)==50
    assert not meta['omitted_trips']
    assert not any(t.startswith('pt-lisbon:') for t in meta['unresolved_geometry_trips'])


def test_calendar_exceptions_overnight_calls_and_single_business_day(reference):
    counts=[];occurrences=[];late=False
    for day,rows in reference['days'].items():
        rows=[(k,t,o) for k,t,o in rows if reference['patterns'][k]['operator']=='Lisbon Metro']
        counts.append(len(rows))
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Lisbon')).timestamp()
        for k,t,o in rows:
            times=reference['patterns'][k]['times']
            assert 10800<=o+times[1]<97200
            occurrences.append((t,midnight+o))
            late|=o+times[-1]>86400
    assert counts==[1532,1532,1532,1206,1532,1110,1110]
    assert len(occurrences)==len(set(occurrences)) and late


def test_metro_only_load_and_combined_default_preserve_existing_trains():
    metro=replay.get_replay_day('2026-06-01','portugal',modes=['subway'])
    trains=replay.get_replay_day('2026-06-01','portugal',modes=['train'])
    combined=replay.get_replay_day('2026-06-01','portugal')
    assert len(metro['services'])==2685 and len(trains['services'])==1517
    assert len(combined['services'])==4202
    assert all(s['mode']=='subway' and s['source_trip_id'].startswith(('pt-lisbon:','pt-porto:')) for s in metro['services'])
    assert {s['source_trip_id'] for s in combined['services'] if s['mode']=='train'}=={s['source_trip_id'] for s in trains['services']}
    assert descriptor('2026-06-01','portugal',['subway'])['modes']==['subway']
