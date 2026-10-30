"""Domestic additions preserve the original corpus and have a durable 200-search cap."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from dashboard import flights, international_expansion, south_america_domestic as domestic, world_flights as world
from scripts import prepare_south_america_domestic as campaign
from scripts.discover_international_expansion import digest, read, save, validate_query
from tests.test_international_expansion import query as international_query, Airports


def fixture():
    airports=[dict(code=c,country=country,timezone='America/Argentina/Buenos_Aires',
        lat=-34,lon=-58,icao='S'+c,name=c,mode='flight') for c,country in [('AAA','AR'),('BBB','AR'),('CCC','BR')]]
    f=dict(id='domestic-one',carrier='AR',number='AR1',airline='Example',origin='AAA',destination='BBB',
        departure=world.START+12*3600,arrival=world.START+13*3600,source_date=world.DAY,flight_scope='domestic',
        price=dict(currency='USD',amount_minor=10000,adults=1,cabin='economy',trip_type='one_way'))
    metadata=dict(profile='south_america_domestic',start_date=world.DAY,end_date=world.DAY,scope='domestic',
        fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way'),
        queries=[dict(date=world.DAY,origin='AAA',destination='BBB',status='results')],uncollected_queries=[])
    extra=dict(airports=airports[:2],flights=[f],metadata=metadata)
    base=dict(airports=[airports[0],airports[2]],flights=[{**f,'id':'original','destination':'CCC','flight_scope':'international'}],
        metadata=dict(queries=[dict(date=world.DAY,origin='AAA',destination='CCC',status='results')],
            country_gateways={'AR':'AAA','BR':'CCC'},uncollected_queries=[]))
    return base,extra


def test_additive_overlay_preserves_records_airports_queries_and_input_objects():
    base,extra=fixture();before=deepcopy((base,extra))
    result=domestic.overlay(base,extra)
    assert (base,extra)==before
    assert {f['id']:f for f in result['flights']}=={f['id']:f for f in base['flights']+extra['flights']}
    assert result['airports'][:2]==base['airports']
    assert result['metadata']['country_gateways']==base['metadata']['country_gateways']
    assert result['metadata']['coverage_by_scope']['domestic']['queries_captured']==1
    assert result['metadata']['coverage_by_scope']['international']['queries_captured']==1
    assert result['metadata']['coverage']['island_groups']['BR']==dict(candidate_airports=1,airports_returned=1)
    extra['flights'][0]['id']='original'
    with pytest.raises(ValueError,match='conflicts'):domestic.overlay(base,extra)
    base,extra=fixture();extra['metadata']['queries']=base['metadata']['queries']
    with pytest.raises(ValueError,match='replace original queries'):domestic.overlay(base,extra)


@pytest.mark.parametrize('bad',['scope','country','currency','fare_context','duration','float_time','local_date','id_conflict'])
def test_archive_rejects_invalid_scope_fares_dates_and_identities(tmp_path,monkeypatch,bad):
    _,extra=fixture();path=tmp_path/'extra.gz'
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(path))
    save(path,extra);assert domestic.load_reference()==extra
    f=extra['flights'][0]
    if bad=='scope':f['flight_scope']='international'
    elif bad=='country':extra['airports'][1]['country']='CL'
    elif bad=='currency':f['price']['currency']='ARS'
    elif bad=='fare_context':extra['metadata']['fare_context']['adults']=2
    elif bad=='duration':f['arrival']=f['departure']+28801
    elif bad=='float_time':f['arrival']=float(f['arrival'])
    elif bad=='local_date':f['departure']+=86400;f['arrival']+=86400
    else:extra['flights'].append({**f,'number':'AR2'})
    save(path,extra)
    with pytest.raises(ValueError):domestic.load_reference()


def test_custom_base_fixtures_isolate_domestic_layer_and_only_valid_extra_is_unfrozen(tmp_path,monkeypatch):
    _,extra=fixture();path=tmp_path/'extra.gz';save(path,extra)
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_FLIGHTS_REFERENCE',str(tmp_path/'custom-base.gz'))
    assert not domestic.enabled()
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(path))
    assert domestic.enabled()
    inputs={path.resolve():{'sha256':'extra'},tmp_path/'base.gz':{'sha256':'original'}}
    assert international_expansion.baseline_inputs(inputs)=={tmp_path/'base.gz':{'sha256':'original'}}
    extra['flights'][0]['flight_scope']='international';save(path,extra)
    with pytest.raises(ValueError):international_expansion.baseline_inputs(inputs)


def test_short_parser_empty_domestic_capture_is_compatible_but_not_international():
    airports=Airports();airports.known['BBB']['country']='AU'
    q=international_query([],capture_context=dict(max_duration=28800,airline_filter='none'))
    key=(world.DAY,'AAA','BBB')
    assert validate_query(q,key,airports,scope='domestic')['status']=='no_matching_direct_flights'
    with pytest.raises(ValueError,match='short-parser'):validate_query(q,key,airports)
    airports.known['BBB']['country']='ID'
    with pytest.raises(ValueError,match='International query'):validate_query(q,key,airports,scope='domestic')


def test_published_manifest_has_exact_200_evidenced_queries_and_reviewed_chilean_zones():
    m=read(campaign.SOURCE);campaign.check(m)
    assert m['search_limit']==200 and m['checkpoint_size']==50
    assert m['country_allocations']=={'AR':126,'PE':44,'CL':30}
    assert len(m['reused'])==2 and not m['deferred']
    assert {tuple(q) for q in m['new_searches']}.isdisjoint(tuple(q['query']) for q in m['reused'])
    a={a['code']:a for a in m['airports']}
    for code,zone in campaign.CHILE_ZONES.items():
        assert a[code]['timezone']==zone
    assert a['IPC']['timezone']=='Pacific/Easter'
    assert datetime(2026,7,2,tzinfo=ZoneInfo(a['BBA']['timezone'])).utcoffset().total_seconds()==-3*3600
    assert datetime(2026,7,2,tzinfo=ZoneInfo(a['CPO']['timezone'])).utcoffset().total_seconds()==-4*3600
    original=read(campaign.BASE)
    assert {tuple(q) for q in m['new_searches']}.isdisjoint((q['date'],q['origin'],q['destination']) for q in original['metadata']['queries'])


@pytest.mark.parametrize('stale_journal',[False,True])
def test_collection_reviews_every_50_and_never_repeats_published_attempts(tmp_path,monkeypatch,stale_journal):
    m=deepcopy(read(campaign.SOURCE));m['collection']=dict(attempts=[])
    source=tmp_path/'source.gz';captures=tmp_path/'captures';save(source,m)
    monkeypatch.setattr(campaign,'SOURCE',source);monkeypatch.setattr(campaign,'CAPTURES',captures)
    monkeypatch.setattr(campaign,'check',lambda m:None)
    counts=[]
    async def collect(cache,day,pairs,workers,cfg):
        assert workers==2 and cfg['currency']=='USD' and cfg['scope']=='domestic'
        assert len(cfg['queries'])==50
        for key in cfg['queries']:cfg['on_query_start'](key)
    def publish():
        m=read(source);m['collection']=dict(attempts=read(captures/'attempts.json')['attempts'])
        counts.append(len(m['collection']['attempts']));save(source,m)
    monkeypatch.setattr(campaign,'capture',collect);monkeypatch.setattr(campaign,'publish',publish)
    for _ in range(4):assert campaign.collect()==0
    assert counts==[50,100,150,200]
    if stale_journal:save(captures/'attempts.json',dict(attempts=[]))
    else:(captures/'attempts.json').unlink()
    assert campaign.collect()==0 and counts==[50,100,150,200]
    assert len(read(captures/'attempts.json')['attempts'])==200
    save(captures/'collection-stop.json',dict(reason='challenge'))
    with pytest.raises(RuntimeError,match='do not retry'):campaign.collect()


def test_original_world_reproduces_exactly_and_added_overlap_is_independently_counted(tmp_path,monkeypatch):
    m=read(campaign.SOURCE);extra=domestic.load_reference()
    combined=world.load_reference(world.DAY)
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(tmp_path/'absent.gz'))
    out=tmp_path/'old-world.gz';baseline=world.prepare(out)
    assert digest(out.read_bytes())==m['baseline_world_sha256']
    assert len(baseline['flights'])==m['baseline_world_flights']==56231
    old={world.identity(f) for f in baseline['flights']}
    added={world.identity(f) for f in extra['flights'] if f['departure']<world.END and f['arrival']>=world.START}-old
    assert {world.identity(f) for f in combined['flights']}==old|added
    assert len(added)==m['collection']['world_added']==extra['metadata']['coverage']['new_world_identities']
    assert combined['metadata']['scopes']['international']==baseline['metadata']['scopes']['international']==28333
    assert combined['metadata']['scopes']['domestic']==27898+len(added)
    for path,info in m['baseline_inputs'].items():assert digest((world.ROOT/path).read_bytes())==info['sha256']


def test_missing_published_capture_cannot_erase_the_portable_snapshot(tmp_path,monkeypatch):
    _,extra=fixture();reference=tmp_path/'domestic.gz';cache=tmp_path/'audit'
    extra['metadata']['queries'][0].update(source_path=str(tmp_path/'removed.json'),sha256='published')
    save(reference,extra);before=reference.read_bytes()
    save(cache/'baseline-world.json.gz',dict(flights=[]))
    source=tmp_path/'source.gz'
    save(source,dict(collection=dict(attempts=[]),reused=[],
        baseline_world_sha256=digest((cache/'baseline-world.json.gz').read_bytes())))
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(reference))
    monkeypatch.setattr(campaign,'SOURCE',source);monkeypatch.setattr(campaign,'CACHE',cache)
    monkeypatch.setattr(campaign,'CAPTURES',tmp_path/'captures');monkeypatch.setattr(campaign,'check',lambda m:None)
    with pytest.raises(ValueError,match='Published domestic capture missing'):campaign.publish()
    assert reference.read_bytes()==before
