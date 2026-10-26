"""Exact Nepal airports, quarter-hour clocks and limited international scope."""
from datetime import datetime
import gzip,json
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from flask import Flask
from dashboard import flights,international_network as n,replay_http
from dashboard.cities import CITIES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.prepare_international_network import config,prepare as prepare_network
from scripts.prepare_international_network_routes import eligible
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_international_network import put,query,quote
DAY='2026-11-02';CFG=country_config('NP');AIR={a['code']:a for a in CFG['manifest']['airports']};START=n.window('Asia/Kathmandu')[0]


def test_exact_airports_and_international_only_to_existing_flight_locations():
 assert len(AIR)==21 and len(CFG['manifest']['routes'])==52
 assert AIR['KTM']['icao']=='VNKT' and AIR['PHH']['icao']=='VNPR' and AIR['PKR']['icao']=='VNPK'
 assert AIR['PKR']['lat']!=AIR['PHH']['lat']
 assert AIR['LUA']['icao']!=AIR['RHP']['icao']
 assert all(a['country']=='NP' and a['timezone']=='Asia/Kathmandu' for a in AIR.values())
 assert CFG['currency']=='USD' and CITIES['nepal_flights']['default_flight_scope']=='domestic'
 m=json.loads(Path('data/sources/nepal_international_routes.json').read_text());air={a['code']:a for a in m['airports']}
 assert len(m['routes'])==48 and ['PHH','DXB'] in m['routes'] and 'PKR' not in air
 assert {'KTM','PHH','BWA'}=={a['code'] for a in air.values() if a['country']=='NP'}
 assert not {'IST','SHJ','DAC','DMM','RUH','CMB','KWI'}&air.keys()
 for a,b in m['routes']:
  assert (air[a]['country']=='NP')!=(air[b]['country']=='NP') and [b,a] in m['routes']
  assert air[a]['country'] in n.CORE_COUNTRIES and air[b]['country'] in n.CORE_COUNTRIES
 shared=config()['manifest'];assert ['PHH','DXB'] in shared['routes'] and ['PKR','DXB'] not in shared['routes']
 assert not eligible(AIR['PKR'],air['DXB'])
 assert not n.within_footprint(air['KTM'],dict(country='FR'))


def test_quarter_hour_midnight_overnight_short_segments_and_cheapest_quote():
 assert START==int(datetime(2026,11,1,18,15,tzinfo=ZoneInfo('UTC')).timestamp())
 assert set(expected_queries(DAY,[('KTM','SIF')],CFG))=={('2026-11-01','KTM','SIF'),(DAY,'KTM','SIF')}
 short=segment('KTM','SIF',[9,0],[9,15],15,carrier='U4',number='1')
 assert len(parse_results(scripts(short),'KTM','SIF',DAY,CFG['zones']))==1
 row=segment('KTM','BIR',[23,45],[0,15],30,carrier='U4',number='2');row[20]=[2026,11,1]
 fs=parse_results(scripts(row,row),'KTM','BIR','2026-11-01',CFG['zones']);assert len(fs)==1 and fs[0]['departure']<START<fs[0]['arrival']
 assert cheapest_prices(scripts([offer(row,100),offer(row,65)]),fs,'USD')[fs[0]['id']]['amount_minor']==6500
 with pytest.raises(ValueError,match='duration'):parse_results(scripts(short),'KTM','SIF',DAY,{**CFG['zones'],'SIF':'Asia/Kolkata'})


def test_missing_queries_reproducibility_custom_isolation_http_cache_and_date(tmp_path,monkeypatch):
 cache=tmp_path/'cache';out=tmp_path/'day.gz';f=parse_results(scripts(segment('KTM','BIR',[9,0],[9,35],35,carrier='U4',number='1')),'KTM','BIR',DAY,CFG['zones'])[0]
 put(cache,query(f));pairs=[('KTM','BIR'),('RHP','LUA')];prepare(cache,out,DAY,pairs,CFG);first=out.read_bytes();prepare(cache,out,DAY,pairs,CFG);assert out.read_bytes()==first
 assert len(json.loads(gzip.decompress(first))['metadata']['uncollected_queries'])==3
 monkeypatch.setenv('SUNTRAIN_NEPAL_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
 assert not n.enabled(DAY,'nepal_flights') and flights.reference_paths(DAY,'nepal_flights')==[out]
 assert flights.replay_day(DAY,'nepal_flights')['start']==START
 app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();info=replay_http.descriptor(DAY,'nepal_flights');response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
 assert response.status_code==200 and json.loads(gzip.decompress(response.data))['timezone']=='Asia/Kathmandu'
 assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
 assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404


@pytest.mark.parametrize('change',[{'country':'IN'},{'timezone':'UTC'},{'timezone':'Asia/Kolkata'}])
def test_domestic_wrong_country_or_zone_rejected(tmp_path,change):
 from dashboard.flight_profiles import load_domestic
 doc=dict(airports=[AIR['KTM'],{**AIR['BIR'],**change}],flights=[],metadata=dict(fare_context=dict(currency='USD',adults=1,cabin='economy',trip_type='one_way')))
 p=tmp_path/'bad.gz'
 with gzip.open(p,'wt') as f:json.dump(doc,f)
 with pytest.raises(ValueError,match='national identities'):load_domestic(p,'NP')


def test_shared_local_day_ownership_original_currency_and_adjacent_searches(tmp_path,monkeypatch):
 cfg=config();m=cfg['manifest'];pairs=[['KTM','KUL'],['KUL','KTM']];m={**m,'routes':pairs,'airports':[a for a in m['airports'] if a['code'] in {'KTM','KUL'}]};views={c:n.consumer_queries(m,c) for c in ['international_network',*n.CITIES]};cfg={**cfg,'manifest':m,'queries_by_view':views,'queries':sorted({q for qs in views.values() for q in qs})}
 assert ('2026-11-01','KUL','KTM') in views['nepal_flights'] and ('2026-11-03','KTM','KUL') in views['international_network']
 f=dict(id='RA1',number='RA1',carrier='RA',airline='Nepal Airlines',origin='KTM',destination='KUL',departure=START+3600,arrival=START+7200,source_date='2026-11-01',price=quote('MYR'));cache=tmp_path/'cache';put(cache,query(f));out=tmp_path/'shared.gz';prepare_network(cache,out,cfg)
 monkeypatch.setenv('SUNTRAIN_INTERNATIONAL_NETWORK_REFERENCE',str(out));raw=n.load_archive();np=n.project(raw,'nepal_flights');utc=n.project(raw,'international_network')
 assert len(np['flights'])==1 and not utc['flights'] and np['flights'][0]['price']['currency']=='MYR'


def test_prepared_nepal_scopes_and_shared_consistency():
 full=flights.load_reference(DAY,'nepal_flights');shared=n.project(n.load_archive(),'nepal_flights');byid={f['id']:f for f in full['flights']}
 assert shared['flights'] and all(byid[f['id']]==f for f in shared['flights'])
 assert {f['flight_scope'] for f in full['flights']}=={'domestic','international'}
 assert not full['metadata']['coverage']['failed_or_missing_queries']
 assert len(byid)==len(full['flights'])
