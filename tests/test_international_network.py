"""Shared schedules, original currencies and independent UTC/local day windows."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask
import pytest

from dashboard import flights, international_network as network, replay_http
from scripts.prepare_international_network import config, prepare, seed, validate_query
from scripts.prepare_international_network_routes import eligible


def small_config():
    cfg=config();m=cfg['manifest']
    pairs=[['HND','GMP'],['PVG','ICN'],['KUL','NRT'],['MEL','NRT'],['DOH','ICN']]
    pairs += [[b,a] for a,b in list(pairs)]
    codes={c for p in pairs for c in p}
    m={**m,'routes':pairs,'airports':[a for a in m['airports'] if a['code'] in codes]}
    views={city:network.consumer_queries(m,city) for city in ['international_network',*network.CITIES]}
    return {**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}


def flight(a='PVG',b='ICN',day=network.DAY,hour=8,number='MU123',duration=5400):
    cfg=small_config();airports={a['code']:a for a in cfg['manifest']['airports']}
    at=int(datetime.fromisoformat(day).replace(hour=hour,tzinfo=ZoneInfo(airports[a]['timezone'])).timestamp())
    return dict(id=f'{day}:{number}:{a}:{b}',number=number,carrier=number[:2],airline='Test airline',
        origin=a,destination=b,source_date=day,departure=at,arrival=at+duration,aircraft='Aircraft not specified')


def quote(currency='USD',amount=10000):
    return dict(currency=currency,amount_minor=amount,adults=1,cabin='economy',trip_type='one_way',
        captured_at='2026-10-25T00:00:00+00:00',basis='lowest_returned_quote')


def query(f,at='2026-10-25T00:00:00+00:00'):
    return dict(date=f['source_date'],origin=f['origin'],destination=f['destination'],captured_at=at,
        url='https://www.google.com/travel/flights',page_sha256='evidence',status='results',flights=[f])


def put(cache,q):
    cache.mkdir(parents=True,exist_ok=True)
    path=cache/f"{q['date']}-{q['origin']}-{q['destination']}.json"
    path.write_text(json.dumps(q));return path


def bundle(tmp_path,monkeypatch,records=None):
    cfg=small_config();cache=tmp_path/'cache'
    for f in records or [flight()]:put(cache,query(f))
    output=tmp_path/'network.gz';prepare(cache,output,cfg)
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(output))
    return cfg,cache,output


def test_manifest_has_exact_countries_and_focused_east_asian_candidates():
    cfg=config();m=cfg['manifest'];air={a['code']:a for a in m['airports']}
    assert m['base_directional_routes']==1814 and len(m['routes'])==2102 and len(air)==185
    assert len(set(cfg['queries']))==len(cfg['queries'])==7180
    assert all(eligible(air[a],air[b]) and [b,a] in m['routes'] for a,b in m['routes'])
    assert all(a['country'] not in {'AE','QA'} or a['code'] in network.HUBS for a in air.values())
    assert not {'ITM','MWX','HKG','MFM','TPE','BJS','TYO','SEL'} & air.keys()
    for pair in [('PVG','ICN'),('HND','GMP'),('PEK','NRT'),('PKX','HND'),('SHA','GMP'),('CJU','PVG')]:
        assert list(pair) in m['routes']
    assert all(a['timezone']=='Asia/Shanghai' for a in air.values() if a['country']=='CN')
    assert any('Historical' in e['kind'] for e in m['evidence'])


def test_query_union_covers_utc_and_country_days_without_duplicate_searches():
    cfg=small_config();views=cfg['queries_by_view']
    assert ('2026-11-03','MEL','NRT') in views['international_network']
    assert ('2026-10-31','NRT','MEL') in views['australia_flights']
    assert not any(q[0]=='2026-11-04' for q in cfg['queries'])
    assert set(cfg['queries'])=={q for qs in views.values() for q in qs}
    assert len(cfg['queries'])<sum(map(len,views.values()))
    assert network.window('UTC')[0]-network.window('Australia/Melbourne')[0]==11*3600
    assert network.window('UTC')[0]-network.window('Asia/Kolkata')[0]==19800
    assert network.window('UTC')[0]-network.window('Asia/Qatar')[0]==3*3600


def test_reuse_latest_schedules_cheapest_same_currency_and_no_fx(tmp_path):
    cfg=small_config();sources=[tmp_path/'a',tmp_path/'b',tmp_path/'c'];cache=tmp_path/'out';cache.mkdir()
    f=flight('KUL','NRT');f['price']=quote('MYR',500)
    put(sources[0],query(f,'2026-10-23T00:00:00+00:00'))
    f={**f,'price':quote('USD',9000)};put(sources[1],query(f,'2026-10-24T00:00:00+00:00'))
    f={**f,'price':quote('USD',8000)};put(sources[2],query(f))
    report=seed(cache,cfg,sources);assert report['reused']==1
    q=json.loads((cache/'2026-11-02-KUL-NRT.json').read_text())
    assert q['flights'][0]['price']['currency']=='USD' and q['flights'][0]['price']['amount_minor']==8000
    assert q['flights'][0]['price']['captured_at']=='2026-10-25T00:00:00+00:00'
    assert len(q['reused_sources'])==3
    assert seed(cache,cfg,sources)['reused']==0


def test_reuse_never_attaches_old_quote_to_changed_schedule_or_resurrects_removed_flight(tmp_path):
    cfg=small_config();a=tmp_path/'a';b=tmp_path/'b';cache=tmp_path/'out';cache.mkdir()
    f=flight();f['price']=quote();put(a,query(f,'2026-10-24T00:00:00+00:00'))
    changed=flight(hour=9);put(b,query(changed));seed(cache,cfg,[a,b])
    q=json.loads((cache/'2026-11-02-PVG-ICN.json').read_text())
    assert 'price' not in q['flights'][0] and q['superseded_schedule_records']==[f['id']]
    # A newest completed empty query owns its schedule, even if older captures had flights.
    newest={**query(f,'2026-10-26T00:00:00+00:00'),'flights':[],'status':'no_matching_direct_flights'}
    c=tmp_path/'c';put(c,newest);out=tmp_path/'empty';out.mkdir();seed(out,cfg,[a,c])
    assert not json.loads((out/'2026-11-02-PVG-ICN.json').read_text())['flights']


def test_original_myr_and_unpriced_captures_are_reused_and_invalid_prices_rejected(tmp_path):
    cfg=small_config();a=tmp_path/'a';cache=tmp_path/'out';cache.mkdir()
    f=flight('KUL','NRT');f['price']=quote('MYR');put(a,query(f))
    put(a,query(flight()))
    invalid=flight('HND','GMP');invalid['price']=quote('JPY');put(a,query(invalid))
    r=seed(cache,cfg,[a]);assert r['reused']==2 and len(r['rejected_caches'])==1
    assert json.loads((cache/'2026-11-02-KUL-NRT.json').read_text())['flights'][0]['price']['currency']=='MYR'


def test_projection_retains_overnight_overlap_but_utc_and_local_event_days_differ(tmp_path,monkeypatch):
    # 01:00 in Korea is still the previous UTC day. Its arrival is on Nov 2 UTC.
    f=flight('ICN','PVG',hour=1,duration=10*3600)
    _,_,_=bundle(tmp_path,monkeypatch,[f]);raw=network.load_archive()
    utc=network.project(raw,'international_network');kr=network.project(raw,'south_korea_flights')
    assert len(utc['flights'])==len(kr['flights'])==1
    start,end=network.window('UTC');assert f['departure']<start<=f['arrival']<end
    local_start,_=network.window('Asia/Seoul');assert f['departure']>=local_start
    assert utc['metadata']['coverage_by_country_pair']['CN-KR']['flights']==1
    assert utc['metadata']['coverage']['failed_or_missing_queries']>0


def test_missing_queries_errors_and_byte_identical_cached_preparation(tmp_path,monkeypatch):
    cfg,cache,out=bundle(tmp_path,monkeypatch)
    key=next(q for q in cfg['queries_by_view']['international_network'] if q!=(network.DAY,'PVG','ICN'))
    error=dict(date=key[0],origin=key[1],destination=key[2],error='Search access limited')
    (cache/('-'.join(key)+'.error.json')).write_text(json.dumps(error))
    prepare(cache,out,cfg);first=out.read_bytes();prepare(cache,out,cfg);assert out.read_bytes()==first
    view=network.project(network.load_archive(),'international_network')
    assert len(view['metadata']['queries'])==1 and view['metadata']['coverage']['failed_queries']==1
    assert view['metadata']['coverage']['queries_captured']+view['metadata']['coverage']['failed_or_missing_queries']==len(cfg['queries_by_view']['international_network'])


def test_shared_overlay_removes_authoritative_old_records_but_preserves_other_routes(tmp_path,monkeypatch):
    f=flight();f['price']=quote('MYR');cfg,_,_=bundle(tmp_path,monkeypatch,[f])
    raw=network.load_archive();old={**f,'arrival':f['arrival']+60,'flight_scope':'international'}
    other=flight('HND','GMP',number='NH1');other['flight_scope']='international'
    base=dict(airports=cfg['manifest']['airports'],flights=[old,other],metadata=dict(coverage={},queries=[],fare_context={}))
    result=network.overlay(base,'south_korea_flights');byid={f['id']:f for f in result['flights']}
    assert byid[f['id']]['arrival']==f['arrival'] and other['id'] in byid
    assert byid[f['id']]['price']['currency']=='MYR'
    assert old['arrival']==f['arrival']+60 and base['metadata']['fare_context']=={}
    assert result['metadata']['fare_context']['currency']=='mixed'


@pytest.mark.parametrize('code,country,old_icao,new_icao',[('PDG','ID','WIPT','WIEE'),('KTI','KH','KH-0002','VDTI')])
def test_pinned_stable_airport_ident_alias_does_not_allow_other_identity_conflicts(tmp_path,monkeypatch,code,country,old_icao,new_icao):
    from copy import deepcopy
    cfg,_,_=bundle(tmp_path,monkeypatch)
    raw=network.load_archive();real_project=network.project
    shared=real_project(raw,'south_korea_flights');airport=shared['airports'][0]
    # Exercise the explicit pinned alias without relaxing country/coordinate matching.
    old_code=airport['code'];airport.update(code=code,icao=new_icao,country=country)
    for f in shared['flights']:
        for k in ('origin','destination'):
            if f[k]==old_code:f[k]=code
    monkeypatch.setattr(network,'project',lambda *args:shared)
    old={**airport,'icao':old_icao}
    base=dict(airports=[old],flights=[],metadata=dict(coverage={},queries=[]))
    result=network.overlay(base,'indonesia_flights')
    assert any(a['code']==code and a['icao']==new_icao for a in result['airports'])
    wrong=deepcopy(base);wrong['airports'][0]['lon']+=1
    with pytest.raises(ValueError,match='airport identity'):network.overlay(wrong,'indonesia_flights')


def test_access_challenge_stops_once_and_preserves_successful_partial_capture(tmp_path,monkeypatch):
    from scripts import prepare_international_network as collector
    cfg=small_config();cache=tmp_path/'cache';put(cache,query(flight()));out=tmp_path/'partial.gz';calls=[]
    async def stop(*args,**kwargs):
        calls.append(1);raise RuntimeError('Search access limited; collection stopped')
    monkeypatch.setattr(collector,'config',lambda:cfg);monkeypatch.setattr(collector,'seed',lambda *args:None)
    monkeypatch.setattr(collector,'capture',stop)
    monkeypatch.setattr('sys.argv',['collector','--cache',str(cache),'--output',str(out)])
    assert collector.main()==2 and calls==[1]
    raw=json.loads(gzip.decompress(out.read_bytes()))
    assert len(raw['flights'])==1 and raw['metadata']['uncollected_queries']
    assert 'Search access limited' in raw['metadata']['collection_stop']['reason']


def test_http_utc_clock_compression_etag_date_rejection_and_custom_fixture_isolation(tmp_path,monkeypatch):
    _,_,out=bundle(tmp_path,monkeypatch)
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    day=flights.replay_day(network.DAY,'international_network')
    assert day['timezone']=='UTC' and day['start']==network.window('UTC')[0]
    assert day['services'] and all(f['flight_scope']=='international' for f in day['services'])
    assert flights.reference_paths(network.DAY,'china_flights')[-1]==out
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    desc=replay_http.descriptor(network.DAY,'international_network');response=client.get(desc['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and response.headers['Content-Encoding']=='gzip'
    assert json.loads(gzip.decompress(response.data))['timezone']=='UTC'
    assert client.get(desc['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    with pytest.raises(ValueError,match='Date outside'):replay_http.descriptor('2026-11-03','international_network')
    monkeypatch.delenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE')
    monkeypatch.setenv('SUNTRAIN_CHINA_FLIGHTS_REFERENCE',str(tmp_path/'domestic.gz'))
    assert not network.enabled(network.DAY,'china_flights')


@pytest.mark.parametrize('field,value',[('currency','CNY'),('amount_minor',0),('adults',2)])
def test_no_invalid_or_relabelled_currency_quotes(tmp_path,monkeypatch,field,value):
    f=flight();f['price']={**quote(),field:value}
    with pytest.raises(ValueError,match='fare context'):validate_query(query(f),(network.DAY,'PVG','ICN'))


def test_prepared_network_and_country_overlays_are_consistent():
    if not network.reference_path().exists():pytest.skip('Full collection still running')
    raw=network.load_archive();view=network.project(raw,'international_network')
    assert raw['metadata']['queries_by_view'] and view['flights']
    assert len({f['id'] for f in view['flights']})==len(view['flights'])
    assert {'CN-JP','CN-KR','JP-KR'}<=view['metadata']['coverage_by_country_pair'].keys()
    for city in ['china_flights','japan_flights','south_korea_flights','australia_flights','gulf_flights','thailand_flights','philippines_flights','vietnam_flights','brunei_flights','cambodia_flights','laos_flights','myanmar_flights','timor_leste_flights','new_zealand_flights']:
        projected=network.project(raw,city);loaded=flights.load_reference(network.DAY,city)
        byid={f['id']:f for f in loaded['flights']}
        assert all(byid[f['id']]['departure']==f['departure'] and byid[f['id']].get('price')==f.get('price') for f in projected['flights'])
