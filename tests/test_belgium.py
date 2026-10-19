from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_belgium_replay import (
    GEOMETRY, GEOMETRY_SHA256, RAIL_PRODUCTS, SOURCE, domestic_sequence, selected_route,
)


def test_rail_scope_uses_source_categories_and_excludes_replacement_buses():
    agencies={'NMBS/SNCB':{'agency_name':'NMBS/SNCB'}}
    route={'agency_id':'NMBS/SNCB','route_type':'103','route_short_name':'IC'}
    for mode,products in RAIL_PRODUCTS.items():
        for product in products:
            assert selected_route({**route,'route_type':mode,'route_short_name':product},agencies)
    for mode in ['700','3','0','1','4','1400']:
        assert not selected_route({**route,'route_type':mode},agencies)
    assert not selected_route({**route,'route_short_name':'BUS'},agencies)
    assert not selected_route(route,{'NMBS/SNCB':{'agency_name':'Unknown'}})
    assert not selected_route({**route,'agency_id':'Other'},agencies)


def test_domestic_clipping_preserves_foreign_intermediate_stations_and_times():
    sequence=[{'stop_id':s,'arrival_time':f'{22+i}:00:00'} for i,s in enumerate(
        ['8400001','8814001_3','8200001','8841004','8010001'])]
    assert domestic_sequence(sequence)==sequence[1:4]
    assert domestic_sequence(sequence[:2])==[]
    assert domestic_sequence([])==[]


@pytest.fixture(scope='module')
def reference():
    with gzip.open(replay.BELGIUM_PATH,'rt') as stream:return json.load(stream)


def test_pinned_sources_nationwide_scope_and_compact_schedules(reference):
    assert file_hash(GEOMETRY)==GEOMETRY_SHA256
    metadata=reference['metadata']
    assert metadata['sources'][0]['sha256']==SOURCE['sha256']
    assert metadata['sources'][0]['feed_version']=='2026-05-30'
    assert metadata['schedule_encoding']=='shared-stops-flat-times-v1'
    assert metadata['license']=='CC BY 4.0' and metadata['geometry_license']=='CC0 1.0'
    assert not metadata['omitted_trips']
    patterns=reference['patterns'].values()
    assert all('stops' not in p for p in patterns)
    assert {p['mode'] for p in patterns}=={'train'}
    assert {p['operator'] for p in patterns}=={'NMBS/SNCB'}
    assert {'IC','L','P','S1','S8','S32','S41','S51','S61'} <= {p['category'] for p in patterns}
    names={s['name'] for s in reference['stations']}
    for fragment in ['Bruxelles','Antwerpen','Gent','Brugge','Liège','Namur','Charleroi','Arlon','Oostende','Hasselt']:
        # The source uses French station names where available.
        aliases={'Antwerpen':'Anvers','Gent':'Gand','Brugge':'Bruges','Oostende':'Ostende'}
        assert any(fragment in n or aliases.get(fragment,fragment) in n for n in names)
    assert not city_settings('belgium')['passenger_data']


def test_week_has_one_start_window_per_occurrence_and_keeps_empty_geometry_gaps(reference):
    assert len(reference['days'])==7
    seen=[];overnight=[]
    for day,rows in reference['days'].items():
        assert len(rows)>1000
        midnight=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('Europe/Brussels')).timestamp()
        for key,trip,offset in rows:
            assert 10800<=offset<97200
            seen.append((trip,midnight+offset))
            if offset<86400<offset+reference['patterns'][key]['times'][-1]:overnight.append(trip)
    assert len(seen)==len(set(seen)) and overnight
    for path in reference['paths'].values():
        if path['quality']=='approximate':assert path['coordinates']==path['distances']==[]
        else:assert path['quality']=='track' and len(path['coordinates'])>=2


def test_core_intercity_and_suburban_services_have_detailed_rail_paths(reference):
    for category in ['IC','L','P','S1','S41','S51','S61']:
        paths=[reference['paths'][key] for raw in reference['patterns'].values() if raw['category']==category
               for key in reference['stop_patterns'][raw['stop_pattern']]['legs']]
        assert paths and any(len(p['coordinates'])>10 for p in paths),category


def test_existing_loader_serves_matching_week_with_commercial_numbers(monkeypatch):
    monkeypatch.setattr(replay.data,'get_metadata',lambda:pytest.fail('Belgium queried Melbourne warehouse'))
    day=replay.get_replay_day('2026-06-01','belgium')
    assert day['timezone']=='Europe/Brussels' and day['services']
    assert all(s['mode']=='train' and s['source_trip_id'] for s in day['services'])
    assert any(s['number'].isdigit() for s in day['services'])
    assert city_settings('belgium')['start_date']==city_settings('switzerland')['start_date']
    assert descriptor('2026-06-01','belgium')['modes']==['train']
    with pytest.raises(ValueError):descriptor('2026-06-01','belgium',['bus'])
    with pytest.raises(ValueError):replay.get_replay_day('2026-06-08','belgium')
