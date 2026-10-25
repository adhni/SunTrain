"""New Zealand exact airports, daylight saving, source quotes and shared ownership."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from flask import Flask
from dashboard import flights,international_network as network,replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.prepare_international_network import config,prepare as prepare_network
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_international_network import put,query,quote
DAY='2026-11-02';CFG=country_config('NZ');AIR={a['code']:a for a in CFG['manifest']['airports']}
START=network.window('Pacific/Auckland')[0]


def test_exact_north_south_airports_focused_candidates_and_seasonal_gaps():
    assert len(AIR)==20 and len(CFG['manifest']['routes'])==82
    assert AIR['AKL']['icao']=='NZAA' and AIR['WLG']['icao']=='NZWN' and AIR['CHC']['icao']=='NZCH'
    assert all(a['country']=='NZ' and a['timezone']=='Pacific/Auckland' for a in AIR.values())
    assert {a['island_group'] for a in AIR.values()}=={'North Island','South Island'}
    assert CFG['currency']=='USD' and CITIES['new_zealand_flights']['default_flight_scope']=='domestic'
    assert 'CHT' not in AIR and CFG['manifest']['deferred_airports']
    m=json.loads(Path('data/sources/new_zealand_international_routes.json').read_text());air={a['code']:a for a in m['airports']}
    assert len(m['routes'])==90 and m['base_directional_routes']==70
    assert not {'HKG','TPE','NAN','CHT'}&air.keys()
    assert ['CHC','NRT'] not in m['routes'] and ['CHC','PER'] not in m['routes']
    assert ['AKL','WSI'] in m['routes'] and air['WSI']['code']!=air['SYD']['code']
    for a,b in m['routes']:assert (air[a]['country']=='NZ')!=(air[b]['country']=='NZ') and [b,a] in m['routes']


def test_dst_midnight_adjacent_dates_overnight_short_segments_and_cheapest_quote():
    assert START==int(datetime(2026,11,1,11,tzinfo=ZoneInfo('UTC')).timestamp())
    assert datetime(2026,6,2,tzinfo=ZoneInfo('Pacific/Auckland')).utcoffset().total_seconds()==43200
    assert set(expected_queries(DAY,[('WLG','BHE')],CFG))=={('2026-11-01','WLG','BHE'),(DAY,'WLG','BHE')}
    row=segment('AKL','WLG',[23,30],[0,30],60,carrier='NZ',number='1');row[20]=[2026,11,1]
    fs=parse_results(scripts(row,row),'AKL','WLG','2026-11-01',CFG['zones'])
    assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
    prices=cheapest_prices(scripts([offer(row,100),offer(row,60.50)]),fs,'USD')
    assert prices[fs[0]['id']]['amount_minor']==6050
    short=segment('WLG','BHE',[9,0],[9,25],25,carrier='NZ',number='2')
    assert len(parse_results(scripts(short),'WLG','BHE',DAY,CFG['zones']))==1
    with pytest.raises(ValueError,match='duration'):parse_results(scripts(short),'WLG','BHE',DAY,{**CFG['zones'],'BHE':'Australia/Sydney'})


def test_missing_queries_reproducibility_fixture_isolation_http_and_date_rejection(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();out=tmp_path/'day.gz'
    row=segment('AKL','WLG',[9,0],[10,0],60,carrier='NZ',number='1');f=parse_results(scripts(row),'AKL','WLG',DAY,CFG['zones'])[0]
    put(cache,query(f));pairs=[('AKL','WLG'),('CHC','HKK')]
    prepare(cache,out,DAY,pairs,CFG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CFG);assert out.read_bytes()==first
    assert len(json.loads(gzip.decompress(first))['metadata']['uncollected_queries'])==3
    monkeypatch.setenv('SUNTRAIN_NEW_ZEALAND_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    assert not network.enabled(DAY,'new_zealand_flights') and flights.reference_paths(DAY,'new_zealand_flights')==[out]
    day=flights.replay_day(DAY,'new_zealand_flights');assert day['start']==START and len(day['services'])==1
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'new_zealand_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Pacific/Auckland'
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
    with pytest.raises(ValueError,match='approved manifest'):prepare(cache,out,DAY,[('KKE','HKK')],CFG)


@pytest.mark.parametrize('change',[{'country':'AU'},{'timezone':'UTC'},{'timezone':'Pacific/Chatham'}])
def test_domestic_wrong_country_and_zone_rejected(tmp_path,change):
    from dashboard.flight_profiles import load_domestic
    doc=dict(airports=[AIR['AKL'],{**AIR['WLG'],**change}],flights=[],metadata=dict(fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')))
    p=tmp_path/'bad.gz'
    with gzip.open(p,'wt') as f:json.dump(doc,f)
    with pytest.raises(ValueError,match='national identities'):load_domestic(p,'NZ')


def test_local_vs_utc_shared_ownership_original_prices_and_adjacent_searches(tmp_path,monkeypatch):
    cfg=config();m=cfg['manifest'];pairs=[['AKL','KUL'],['KUL','AKL']];codes={c for p in pairs for c in p}
    m={**m,'routes':pairs,'airports':[a for a in m['airports'] if a['code'] in codes]}
    views={c:network.consumer_queries(m,c) for c in ['international_network',*network.CITIES]}
    cfg={**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}
    assert ('2026-10-31','KUL','AKL') in views['new_zealand_flights']
    assert ('2026-11-03','AKL','KUL') in views['international_network']
    f=dict(id='NZ1',number='NZ1',carrier='NZ',airline='Air New Zealand',origin='AKL',destination='KUL',departure=START+3600,arrival=START+7200,source_date=DAY,price=quote('MYR'))
    cache=tmp_path/'cache';put(cache,query(f));out=tmp_path/'shared.gz';prepare_network(cache,out,cfg)
    monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out));raw=network.load_archive()
    nz=network.project(raw,'new_zealand_flights');utc=network.project(raw,'international_network')
    assert len(nz['flights'])==1 and not utc['flights'] and nz['flights'][0]['price']['currency']=='MYR'
    next(a for a in raw['airports'] if a['code']=='AKL')['timezone']='UTC'
    with gzip.open(out,'wt') as stream:json.dump(raw,stream)
    with pytest.raises(ValueError,match='national IANA zone'):network.load_archive()


def test_prepared_new_zealand_scopes_and_shared_consistency():
    if not flights.reference_path(city='new_zealand_flights').exists():pytest.skip('Domestic collection in progress')
    raw=network.load_archive()
    if 'new_zealand_flights' not in raw['metadata']['queries_by_view']:pytest.skip('International collection in progress')
    full=flights.load_reference(DAY,'new_zealand_flights');shared=network.project(raw,'new_zealand_flights');byid={f['id']:f for f in full['flights']}
    assert shared['flights'] and all(byid[f['id']]==f for f in shared['flights'])
    assert {f['flight_scope'] for f in full['flights']}=={'domestic','international'}
    assert full['metadata']['coverage_by_scope']['international']==shared['metadata']['coverage']
    assert not full['metadata']['coverage']['failed_or_missing_queries']
    assert {'AKL','WLG','CHC','ZQN'}<={a['code'] for a in full['airports']}
