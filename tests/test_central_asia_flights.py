"""Exact modern airports, post-2024 Kazakhstan clocks and sourced regional coverage."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib,json,re
import pytest
from dashboard.flight_profiles import PROFILES,load_domestic
from dashboard.i18n import CATALOGUES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from scripts.sourced_flights import prepare_cached,collection_routes
from tests.test_google_flights import segment,scripts
DAY='2026-11-02'

def test_five_country_footprint_sourced_pairs_and_modern_airport_identities(tmp_path):
    cfg=country_config('CENTRAL_ASIA');m=cfg['manifest'];a={a['code']:a for a in m['airports']}
    assert set(m['regional_countries'])=={'KZ','UZ','KG','TJ','TM'}
    assert len(m['launch_airports'])==44
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert all(any(a[c]['country'] in m['regional_countries'] for c in pair) for pair in m['routes'])
    assert ['LHR','JFK'] not in m['routes'] and ['BSZ','FRA'] not in m['routes']  # Connecting lists excluded.
    assert ['ASB','LGW'] in m['routes'] and ['ASB','LHR'] not in m['routes']
    assert ['BSZ','OSS'] in m['routes'] and ['OSS','BSZ'] in m['routes']
    assert ['ASB','KEA'] in m['routes'] and ['DYU','LBD'] in m['routes']
    assert a['BSZ']['icao']=='UCFM' and a['NQZ']['icao']=='UACC'
    assert a['TAS']['icao']=='UZTT' and a['SKD']['icao']=='UZSS' and a['FEG']['icao']=='UZFF'
    assert not {'FRU','TSE'}&set(a)
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert cfg['currency']=='USD' and cfg['max_duration']==86400
    assert not m['archive_reuse_routes'] and all(e['sources'] for e in m['evidence'])
    assert set(collection_routes(tmp_path,cfg))==set(map(tuple,m['new_collection_routes']))
    for sentence in re.split(r'(?<=[.!?])\s+',m['replay_note']):assert CATALOGUES['id'][sentence]!=sentence

@pytest.mark.parametrize('code',['ALA','NQZ','CIT','SCO','GUW','AKX','URA','KSN','KZO','UKK','TAS','SKD','DYU','ASB','BSZ','OSS'])
def test_current_national_offsets_year_round(code):
    cfg=country_config('CENTRAL_ASIA');air={a['code']:a for a in cfg['manifest']['airports']}
    expected=6 if air[code]['country']=='KG' else 5
    for month in [1,7,11]:assert datetime(2026,month,2,12,tzinfo=ZoneInfo(cfg['zones'][code])).utcoffset().total_seconds()==3600*expected

@pytest.mark.parametrize('origin,destination,arrival,duration',[('ALA','BSZ',[1,30],60),('BSZ','TAS',[0,0],90),('ASB','KRW',[0,30],60)])
@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_overnight_short_regional_segments_and_retained_fares(origin,destination,arrival,duration,currency,tmp_path):
    cfg=country_config('CENTRAL_ASIA');row=segment(origin,destination,[23,30],arrival,duration,carrier='KC',number='100');row[21]=[2026,11,3]
    fs=parse_results(scripts(row,row),origin,destination,DAY,cfg['zones'],[],86400)
    assert len(fs)==1 and fs[0]['arrival']-fs[0]['departure']==duration*60
    fs[0]['price']=dict(currency=currency,amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    q=dict(date=DAY,origin=origin,destination=destination,captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)
    path=tmp_path/f'{DAY}-{origin}-{destination}.json';path.write_text(json.dumps(q));original=path.read_bytes()
    pairs=[[origin,destination],[destination,origin]];cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    out=tmp_path/'day.gz';prepare_cached(tmp_path,out,cfg);first=out.read_bytes();prepare_cached(tmp_path,out,cfg)
    assert first==out.read_bytes() and path.read_bytes()==original
    r=load_domestic(out,'CENTRAL_ASIA');assert len(r['flights'])==1 and r['flights'][0]['price']['currency']==currency
    assert r['metadata']['uncollected_queries']==[[DAY,destination,origin]]
    assert r['flights'][0]['flight_scope']==('domestic' if origin=='ASB' else 'international')


def test_historical_candidates_are_domestic_only_and_fact_hashes_are_honest():
    d=json.loads(Path('data/sources/central_asia_flights_discovery.json').read_text());cfg=country_config('CENTRAL_ASIA');a={a['code']:a for a in cfg['manifest']['airports']}
    assert 'June 2014' in d['supplemental_source_warning']
    for row in d['supplemental_airport_maps']:
        doc=row['documents'][0]
        if 'facts_sha256' in doc:
            facts=json.dumps(dict(airport=row['airport'],destinations=row['destinations']),sort_keys=True,separators=(',',':')).encode()
            assert hashlib.sha256(facts).hexdigest()==doc['facts_sha256'] and 'sha256' not in doc
        else:
            assert 'Historical domestic' in row['kind']
            assert all(a[x]['country']==a[row['airport']]['country'] for x in row['destinations'])


def test_final_snapshot_honest_coverage_local_dates_and_full_replay_window():
    from dashboard import flights
    cfg=country_config('CENTRAL_ASIA');r=load_domestic(flights.reference_path(DAY,'central_asia_flights'),'CENTRAL_ASIA');m=r['metadata'];fs=r['flights'];a={a['code']:a for a in r['airports']}
    assert len(fs)==len({f['id'] for f in fs}) and fs
    assert not m['failed_queries'] and not m['uncollected_queries']
    assert m['coverage']['queries_captured']==len(cfg['manifest']['routes'])
    assert m['coverage']['rejected_records']==0
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in fs)
    assert all(not f.get('price') or f['price']['currency'] in {'USD','EUR','MYR'} for f in fs)
    assert set(cfg['manifest']['regional_countries'])<={a[f[k]]['country'] for f in fs for k in ('origin','destination')}
    assert all(f['flight_scope']==('domestic' if a[f['origin']]['country']==a[f['destination']]['country'] else 'international') for f in fs)
    day=flights.replay_day(DAY,'central_asia_flights');assert len(day['services'])==len(fs) and day['timezone']=='UTC'
    assert all(day['start']<=f['departure']<f['arrival']<day['end'] for f in fs)
    for path in day['paths'].values():assert all(abs(b[0]-a[0])<180 for a,b in zip(path['coordinates'],path['coordinates'][1:]))


def test_central_asia_http_cache_and_date_rejection(tmp_path,monkeypatch):
    from flask import Flask
    from dashboard import replay_http as http
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    app=Flask(__name__);http.register_replay_routes(app);client=app.test_client()
    info=http.descriptor(DAY,'central_asia_flights');first=client.get(info['url'])
    assert first.status_code==200
    assert client.get(info['url'],headers={'If-None-Match':first.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
