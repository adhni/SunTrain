"""Sourced expansion, airport separation and dated Canadian/Mexican time zones."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json,re
import pytest
from dashboard.canada_mexico_flights import COUNTRIES
from dashboard.flight_profiles import load_domestic,PROFILES
from dashboard.i18n import CATALOGUES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from scripts.sourced_flights import prepare_cached,collection_routes
from tests.test_google_flights import segment,scripts
DAY='2026-11-02'

@pytest.mark.parametrize('code',['CA','MX'])
def test_sourced_scope_exact_airports_and_single_date(code,tmp_path):
    cfg=country_config(code);m=cfg['manifest'];air={a['code']:a for a in m['airports']}
    assert len(m['launch_airports'])==15 and len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert cfg['currency']=='USD' and cfg['max_duration']==86400 and not m['archive_reuse_routes']
    assert all(any(air[c]['country']==code for c in pair) for pair in m['routes'])
    assert all(air[a]['country'] in {'CA','MX','US'} and air[b]['country'] in {'CA','MX','US'} for a,b in m['new_collection_routes'])
    assert all(e['sources'] for e in m['evidence'])
    assert set(collection_routes(tmp_path,cfg))==set(map(tuple,m['new_collection_routes']))
    if code=='CA':
        assert air['YYZ']['icao']=='CYYZ' and air['YTZ']['icao']=='CYTZ'
        assert ['YYZ','YTZ'] not in m['routes']  # No all-pairs expansion between city airports.
        assert ['YYZ','YOW'] in m['routes'] and ['YOW','YYZ'] in m['routes']
        assert air['YVR']['timezone']=='America/Vancouver' and air['YVR']['replay_timezone']=='Etc/GMT+7'
    else:
        assert air['MEX']['icao']=='MMMX' and air['NLU']['icao']=='MMSM' and air['TLC']['icao']=='MMTO'
        assert len({air[c]['icao'] for c in ['MEX','NLU','TLC']})==3
        assert ['MEX','NLU'] not in m['routes']
        assert cfg['zones']['CJS']=='America/Ciudad_Juarez'
    for sentence in re.split(r'(?<=[.!?])\s+',m['replay_note']):assert CATALOGUES['id'][sentence]!=sentence

@pytest.mark.parametrize('country,airport,offset',[('CA','YVR',-7),('CA','YYJ',-7),('CA','YLW',-7),('CA','YYC',-6),('CA','YEG',-6),('CA','YZF',-6),('CA','YXE',-6),('CA','YQR',-6),('CA','YYZ',-5),('CA','YUL',-5),('CA','YHZ',-4),('CA','YYT',-3.5),('CA','YSK',-5),('MX','MEX',-6),('MX','NLU',-6),('MX','TLC',-6),('MX','CUN',-5),('MX','TQO',-5),('MX','TIJ',-8),('MX','CJS',-7),('MX','CUU',-6),('MX','SJD',-7),('MX','HMO',-7),('MX','PVR',-6)])
def test_november_offsets_include_dated_changes(country,airport,offset):
    cfg=country_config(country);zone=cfg['zones'][airport]
    assert datetime(2026,11,2,12,tzinfo=ZoneInfo(zone)).utcoffset().total_seconds()==offset*3600

@pytest.mark.parametrize('country,origin,destination,arrival,duration',[('CA','YVR','YYZ',[7,0],330),('CA','YYT','YVR',[0,0],240),('MX','TIJ','MEX',[5,0],210),('MX','MEX','CUN',[3,0],150)])
@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_overnight_clocks_prices_duplicates_and_missing_queries(country,origin,destination,arrival,duration,currency,tmp_path):
    cfg=country_config(country);row=segment(origin,destination,[23,30],arrival,duration,carrier='AC' if country=='CA' else 'AM',number='100');row[21]=[2026,11,3]
    fs=parse_results(scripts(row,row),origin,destination,DAY,cfg['zones'],[],86400)
    assert len(fs)==1 and fs[0]['arrival']-fs[0]['departure']==duration*60
    fs[0]['price']=dict(currency=currency,amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    q=dict(date=DAY,origin=origin,destination=destination,captured_at='2026-10-28T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)
    path=tmp_path/f'{DAY}-{origin}-{destination}.json';path.write_text(json.dumps(q));original=path.read_bytes()
    pairs=[[origin,destination],[destination,origin]];cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    out=tmp_path/'day.gz';prepare_cached(tmp_path,out,cfg);first=out.read_bytes();prepare_cached(tmp_path,out,cfg)
    assert first==out.read_bytes() and path.read_bytes()==original
    r=load_domestic(out,country);assert len(r['flights'])==1 and r['flights'][0]['price']['currency']==currency
    assert r['metadata']['uncollected_queries']==[[DAY,destination,origin]]


def test_source_maps_preserve_worldwide_inventory_but_bound_new_queries():
    for p in COUNTRIES.values():
        doc=json.loads(Path(f"data/sources/{p['slug']}_flights_discovery.json").read_text())
        for row in doc['airport_maps']:
            assert set(row['destinations'])<=set(row['published_destinations'])
            if row['destinations']:assert all(d.get('sha256') for d in row['documents'])
    assert PROFILES['US']['airport_replay_zones']['YVR']=='Etc/GMT+7'

@pytest.mark.parametrize('country,origin,destination,departure,arrival,minutes',[
    ('CA','YRT','YWG',[19,15],[22,45],150),
    ('CA','YWG','YRL',[6,0],[7,0],120),
    ('MX','CJS','MEX',[8,51],[12,20],209),
    ('MX','CUN','CJS',[12,24],[14,1],157),
])
def test_reviewed_source_clock_conflicts_stay_excluded(country,origin,destination,departure,arrival,minutes):
    # Minimal source rows confirmed by a separate exact-query recheck.
    rejected=[]
    row=segment(origin,destination,departure,arrival,minutes)
    assert not parse_results(scripts(row),origin,destination,DAY,country_config(country)['zones'],rejected,86400)
    assert rejected[0]['reason']=='Source duration differs from airport-local timestamps'

@pytest.mark.parametrize('code',['CA','MX'])
def test_completed_reference_unique_dates_and_deterministic_replay(code):
    from dashboard import flights
    p=COUNTRIES[code];cfg=country_config(code);r=load_domestic(flights.reference_path(DAY,p['slug']+'_flights'),code);m=r['metadata'];fs=r['flights'];a={a['code']:a for a in r['airports']}
    assert len(fs)==len({f['id'] for f in fs}) and fs
    assert not m['failed_queries'] and not m['uncollected_queries']
    rejected=[row for q in m['queries'] for row in q.get('rejected_flights',[])]
    assert m['coverage']['rejected_records']==len(rejected)
    for row in rejected:
        assert row['reason']=='Source duration differs from airport-local timestamps'
        if code=='CA':assert (row['origin'],row['destination']) in {('YRT','YWG'),('YWG','YRT'),('YWG','YRL')}
        else:assert 'CJS' in (row['origin'],row['destination'])
        assert f"{DAY}:{row['number']}:{row['origin']}:{row['destination']}" not in {f['id'] for f in fs}
    assert m['coverage']['queries_captured']==len(cfg['manifest']['routes'])
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in fs)
    assert all(f['flight_scope']==('domestic' if a[f['origin']]['country']==a[f['destination']]['country'] else 'international') for f in fs)
    day=flights.replay_day(DAY,p['slug']+'_flights')
    assert len(day['services'])==len(fs) and all(day['start']<=f['departure']<f['arrival']<day['end'] for f in fs)
    assert len({f[k] for f in fs for k in ('origin','destination') if a[f[k]]['country']==code})>5

@pytest.mark.parametrize('code',['CA','MX'])
def test_country_http_cache_and_date_rejection(code,tmp_path,monkeypatch):
    from flask import Flask
    from dashboard import replay_http as http
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    app=Flask(__name__);http.register_replay_routes(app);client=app.test_client()
    info=http.descriptor(DAY,COUNTRIES[code]['slug']+'_flights');first=client.get(info['url'])
    assert first.status_code==200 and client.get(info['url'],headers={'If-None-Match':first.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
