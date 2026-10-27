"""Regional membership and date-line clocks must survive collection and replay."""
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip,json,re
from pathlib import Path
import pytest
from dashboard.flight_profiles import PROFILES,load_domestic
from dashboard.i18n import CATALOGUES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from scripts.sourced_flights import prepare_cached
from tests.test_google_flights import segment,scripts
DAY='2026-11-02'

def test_sourced_membership_exact_airports_and_one_date():
    cfg=country_config('PACIFIC');m=cfg['manifest'];air={a['code']:a for a in m['airports']}
    members=set(m['regional_countries']);extras=set(m['regional_extra_airports'])
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert all(any(air[c]['country'] in members or c in extras for c in pair) for pair in m['routes'])
    assert ['LAX','JFK'] not in m['routes'] and ['SYD','MEL'] not in m['routes']
    assert ['HNL','AUA'] not in m['routes']  # Previous all-pairs manifests are not route evidence.
    assert ['APW','PPG'] in m['routes'] and ['PPG','APW'] in m['routes']
    assert ['CHT','WLG'] in m['routes'] and ['WLG','CHT'] in m['routes']
    assert ['NOU','LIF'] in m['routes'] and ['NAN','FUN'] in m['routes']
    assert air['NOU']['icao']!=air['GEA']['icao'] and air['APW']['country']!=air['PPG']['country']
    assert not m['archive_reuse_routes'] and cfg['currency']=='USD'
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert all(e['sources'] for e in m['evidence'])
    assert PROFILES['PACIFIC']['arc_anchor']==180
    for sentence in re.split(r'(?<=[.!?])\s+',m['replay_note']):assert CATALOGUES['id'][sentence]!=sentence

@pytest.mark.parametrize('code,offset',[('POM',10),('BUA',11),('KIE',11),('APW',13),('PPG',-11),('CXI',14),('TRW',12),('NHV',-9.5),('GMR',-9),('PPT',-10),('CHT',13.75),('IPC',-5),('HNL',-10),('GUM',10),('PNI',11),('TKK',10)])
def test_explicit_november_offsets(code,offset):
    from scripts.prepare_pacific_routes import timezone_overrides
    zone=country_config('PACIFIC')['zones'].get(code) or timezone_overrides()[code]
    assert datetime(2026,11,2,12,tzinfo=ZoneInfo(zone)).utcoffset().total_seconds()==offset*3600

@pytest.mark.parametrize('origin,destination,arrival_day',[('APW','PPG',1),('PPG','APW',3)])
def test_dateline_arrival_dates_and_deterministic_partial_preparation(origin,destination,arrival_day,tmp_path):
    cfg=country_config('PACIFIC');row=segment(origin,destination,[10,0],[10,40],40,carrier='OL',number='100');row[21]=[2026,11,arrival_day]
    fs=parse_results(scripts(row,row),origin,destination,DAY,cfg['zones'],[],86400)
    assert len(fs)==1 and fs[0]['arrival']-fs[0]['departure']==2400
    fs[0]['price']=dict(currency='USD',amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    q=dict(date=DAY,origin=origin,destination=destination,captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr=USD',status='results',flights=fs,page_sha256='0'*64)
    (tmp_path/f'{DAY}-{origin}-{destination}.json').write_text(json.dumps(q))
    pairs=[[origin,destination],[destination,origin]];cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    out=tmp_path/'week.gz';prepare_cached(tmp_path,out,cfg);first=out.read_bytes();prepare_cached(tmp_path,out,cfg)
    assert first==out.read_bytes()
    result=load_domestic(out,'PACIFIC');assert len(result['flights'])==1
    assert result['metadata']['uncollected_queries']==[[DAY,destination,origin]]
    assert result['flights'][0]['price']['currency']=='USD'

def test_historical_routes_are_explicit_candidates_and_pinned():
    import hashlib
    from scripts.discover_pacific_flights import ARCHIVE_HASH
    d=json.loads(Path('data/sources/pacific_flights_discovery.json').read_text())
    assert '2014' in d['supplemental_source_warning']
    for row in d['supplemental_airport_maps']:
        doc=row['documents'][0]
        if 'sha256' in doc:assert doc['sha256']==ARCHIVE_HASH
        else:
            facts=json.dumps(dict(airport=row['airport'],destinations=row['destinations']),sort_keys=True,separators=(',',':')).encode()
            assert doc['facts_sha256']==hashlib.sha256(facts).hexdigest()
    path=Path('.cache/pacific-flights-audit/openflights-routes.dat')
    if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==ARCHIVE_HASH

def test_complete_capture_metadata_local_dates_and_replay_window():
    from dashboard import flights
    cfg=country_config('PACIFIC');r=load_domestic(flights.reference_path(DAY,'pacific_flights'),'PACIFIC');m=r['metadata'];fs=r['flights']
    assert len(fs)==len({f['id'] for f in fs}) and fs
    assert not m['failed_queries'] and not m['uncollected_queries']
    assert m['coverage']['queries_captured']==len(cfg['manifest']['routes'])
    assert m['coverage']['rejected_records']==0
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in fs)
    assert all(not f.get('price') or f['price']['currency'] in {'USD','EUR','MYR'} for f in fs)
    day=flights.replay_day(DAY,'pacific_flights')
    assert len(day['services'])==len(fs) and day['timezone']=='UTC'
    assert all(day['start']<=f['departure']<f['arrival']<day['end'] for f in fs)
    for path in day['paths'].values():
        assert all(abs(b[0]-a[0])<180 for a,b in zip(path['coordinates'],path['coordinates'][1:]))


def test_pacific_http_cache_and_date_rejection(tmp_path,monkeypatch):
    from flask import Flask
    from dashboard import replay_http as http
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    app=Flask(__name__);http.register_replay_routes(app);client=app.test_client()
    info=http.descriptor(DAY,'pacific_flights');first=client.get(info['url'])
    assert first.status_code==200
    assert client.get(info['url'],headers={'If-None-Match':first.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace(DAY,'2026-11-03')).status_code==404
