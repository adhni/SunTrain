import json

import pytest

from dashboard import replay
from dashboard.cities import CITIES
from dashboard.replay_http import descriptor
from scripts.compact_transit import save_reference
from scripts.prepare_mumbai_scope import corridor


@pytest.mark.parametrize('codes,label', [
    (['CCG','BVI','VR','DRD'],'Western'), (['CSMT','TNA','KYN'],'Central'),
    (['KJT','PDI'],'Central'), (['CSMT','VDLR','PNVL'],'Harbour'),
    (['TNA','TUH','NEU'],'Trans-Harbour'), (['DIVA','BIRD','BSR'],'Diva–Vasai / regional'),
    (['LNL','PUNE'],None), (['ADI','BHUJ'],None),
])
def test_corridors_require_mumbai_core_calls_and_do_not_use_train_number_alone(codes,label):
    assert corridor(codes,[[73,19]]*len(codes)) == label
    assert corridor(codes,[[73,19],[74,21]]) is None


@pytest.fixture
def sources(monkeypatch,tmp_path):
    settings = {'timezone':'Asia/Kolkata','bounds':[[72.7,18.9],[73.3,19.5]],'passenger_data':False,
        'start_date':'2026-08-31','end_date':'2026-08-31','modes':[('Local','commuter_rail')],
        'default_modes':['commuter_rail']}
    for city in ['india','mumbai']:
        monkeypatch.setitem(CITIES,city,{'name':city,**settings})
    monkeypatch.setenv('SUNTRAIN_INDIA_REFERENCE',str(tmp_path/'absent-base.gz'))
    reference={'metadata':{'source':'test','source_url':'https://example.com','license':'test','attribution':'test',
        'sources':[{'sha256':'test-pin'}]},'stations':[{'name':'Alpha','lon':73,'lat':19,'mode':'train'},
        {'name':'Bravo','lon':73.1,'lat':19,'mode':'train'}],
        'patterns':{'p':{'mode':'commuter_rail','operator':'Indian Railways','route_id':'Local','line':'Local',
        'origin':'Alpha','destination':'Bravo','color':'#123456','stops':[[0,0,0],[1,600,600]],'legs':['l']}},
        'paths':{'l':{'coordinates':[[73,19],[73.1,19]],'distances':[0,10000],'quality':'track'}},
        'days':{'2026-08-31':[['p','93001',21600],['p','99801',22000]]}}
    path=tmp_path/'commuter_rail/2026-08-31.json.gz';save_reference(reference,path)
    scope={'source_sha256':'test-pin','trips':{'93001':{'line':'Western','color':'8E448D'}}}
    scopepath=tmp_path/'mumbai-scope.json';scopepath.write_text(json.dumps(scope))
    replay.clear_replay_cache()
    yield path,scopepath
    replay.clear_replay_cache()


def test_mumbai_reuses_india_files_filters_services_and_does_not_mutate_india(sources):
    india=replay.get_replay_day('2026-08-31','india')
    mumbai=replay.get_replay_day('2026-08-31','mumbai')
    assert len(india['services'])==2 and len(mumbai['services'])==1
    assert mumbai['services'][0]['number']=='93001'
    p=mumbai['transit_patterns'][mumbai['services'][0]['pattern']]
    assert p['line']=='Western' and p['color']=='#8E448D'
    assert india['transit_patterns'][india['services'][0]['pattern']]['line']=='Local'
    sourcepaths={path for mode,path,_ in replay.rail_reference_files('mumbai','2026-08-31') if mode!='mumbai_scope'}
    assert sourcepaths=={str(sources[0])}
    assert descriptor('2026-08-31','mumbai')['modes']==['commuter_rail']


def test_scope_change_invalidates_payload_and_http_revision_and_rejects_wrong_source(sources):
    before=descriptor('2026-08-31','mumbai')['revision']
    replay.get_replay_day('2026-08-31','mumbai')
    scope=json.loads(sources[1].read_text());scope['source_sha256']='wrong-version'
    sources[1].write_text(json.dumps(scope)+'\n')
    assert descriptor('2026-08-31','mumbai')['revision']!=before
    with pytest.raises(ValueError,match='different India timetable'):
        replay.get_replay_day('2026-08-31','mumbai')
