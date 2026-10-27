"""Four sourced views, distinct Amman airports, original fares and independent country clocks."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip,json,re
import pytest
from dashboard import flights,international_network
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from dashboard.arabia_jordan_flights import COUNTRIES
from dashboard.i18n import CATALOGUES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from scripts.sourced_flights import prepare_cached,collection_routes,validate_query
from tests.test_google_flights import segment,scripts
DAY='2026-11-02'

@pytest.mark.parametrize('code',COUNTRIES)
def test_source_footprint_and_correct_national_clock(code,tmp_path):
    p=COUNTRIES[code];cfg=country_config(code);m=cfg['manifest'];a={a['code']:a for a in m['airports']};city=p['slug']+'_flights'
    assert city in CITIES and city not in international_network.CITIES
    assert cfg['currency']=='USD' and cfg['max_duration']==86400 and m['timezone']==p['zone']
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert all(a[x]['country']==code or a[y]['country']==code for x,y in m['routes'])
    assert {(e['origin'],e['destination']) for e in m['evidence']}==set(map(tuple,m['routes']))
    assert all(e['sources'] for e in m['evidence'])
    assert set(collection_routes(tmp_path,cfg))==set(map(tuple,m['new_collection_routes']))
    assert not m['archive_reuse_routes']
    for airport in a.values():
        if airport['country']==code:
            assert airport['timezone']==p['zone']
            for month in [1,7,11]:assert datetime(2026,month,2,12,tzinfo=ZoneInfo(airport['timezone'])).utcoffset().total_seconds()==(14400 if code=='OM' else 10800)
    if code=='KW':assert a['KWI']['icao']=='OKKK'
    if code=='BH':assert a['BAH']['icao']=='OBBI'
    if code in {'KW','BH'}:
        assert not CITIES[city]['flight_scopes'] and CITIES[city]['default_flight_scope']=='international'
        assert not any(a[x]['country']==a[y]['country']==code for x,y in m['routes'])
    if code=='JO':
        assert a['AMM']['icao']=='OJAI' and a['ADJ']['icao']=='OJAM' and a['AQJ']['icao']=='OJAQ'
        assert ['AMM','AQJ'] in m['routes'] and ['AQJ','AMM'] in m['routes']
    if code=='OM':
        assert a['MCT']['icao']=='OOMS' and a['SLL']['icao']=='OOSA'
        assert ['SLL','PRG'] in m['routes'] and ['OHS','SLL'] in m['routes']
    for sentence in re.split(r'(?<=[.!?])\s+',m['replay_note']):assert CATALOGUES['id'][sentence]!=sentence

@pytest.mark.parametrize('code,origin,destination,carrier',[('OM','MCT','SLL','WY'),('KW','KWI','MCT','KU'),('BH','BAH','AMM','GF'),('JO','AMM','AQJ','RJ')])
def test_overnight_fares_local_clocks_and_deterministic_partial_preparation(code,origin,destination,carrier,tmp_path):
    cfg=country_config(code);p=COUNTRIES[code];city=p['slug']+'_flights'
    z=cfg['zones'];duration=120+(datetime(2026,11,2,tzinfo=ZoneInfo(z[origin])).utcoffset()-datetime(2026,11,2,tzinfo=ZoneInfo(z[destination])).utcoffset()).total_seconds()/60
    row=segment(origin,destination,[23,30],[1,30],duration,carrier=carrier,number='100');row[21]=[2026,11,3]
    fs=parse_results(scripts(row),origin,destination,DAY,z,[],86400);assert len(fs)==1
    fs[0]['price']=dict(currency='EUR',amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    q=dict(date=DAY,origin=origin,destination=destination,captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr=EUR',status='results',flights=fs,page_sha256='0'*64)
    validate_query(q,(DAY,origin,destination),cfg)
    pairs=[[origin,destination],[destination,origin]];cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    path=tmp_path/f'{DAY}-{origin}-{destination}.json';path.write_text(json.dumps(q));original=path.read_bytes();out=tmp_path/'day.gz'
    prepare_cached(tmp_path,out,cfg);first=out.read_bytes();prepare_cached(tmp_path,out,cfg)
    assert first==out.read_bytes() and original==path.read_bytes()
    raw=load_domestic(out,code);assert len(raw['flights'])==1 and raw['flights'][0]['price']['currency']=='EUR'
    assert raw['metadata']['uncollected_queries']==[[DAY,destination,origin]]
    assert datetime.fromtimestamp(fs[0]['arrival'],ZoneInfo(z[destination])).date().isoformat()=='2026-11-03'

@pytest.mark.parametrize('slug,airport,count',[('oman','SLL',16),('jordan','AQJ',5)])
def test_frozen_nonstop_supplements_have_verifiable_fact_hashes(slug,airport,count):
    import hashlib
    root=Path(__file__).resolve().parents[1]
    m=json.loads((root/f'data/sources/{slug}_flights_discovery.json').read_text())
    r=m['supplemental_airport_maps'][0]
    assert r['airport']==airport and len(r['destinations'])==count
    canonical=json.dumps(dict(airport=airport,destinations=r['destinations']),sort_keys=True,separators=(',',':')).encode()
    assert r['documents'][0]['facts_sha256']==hashlib.sha256(canonical).hexdigest()
    assert 'sha256' not in r['documents'][0]
    assert 'IST' not in r['destinations']  # A connecting suggestion, not a nonstop candidate.

@pytest.mark.parametrize('code,total,domestic,queries,reused',[('OM',211,16,220,66),('KW',167,0,184,49),('BH',173,0,112,53),('JO',179,6,194,66)])
def test_prepared_references_are_unique_dated_and_report_capture_gaps(code,total,domestic,queries,reused):
    p=COUNTRIES[code];r=load_domestic(flights.reference_path(DAY,p['slug']+'_flights'),code);m=r['metadata'];fs=r['flights'];zones=country_config(code)['zones']
    assert len(fs)==len({f['id'] for f in fs})==total
    assert sum(f['flight_scope']=='domestic' for f in fs)==domestic
    assert m['coverage']['queries_captured']==queries and m['queries_reused']==reused
    assert not m['uncollected_queries'] and not m['failed_queries'] and m['coverage']['rejected_records']==0
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(zones[f['origin']])).date().isoformat()==DAY for f in fs)
    assert all(f.get('price',{}).get('currency','USD') in {'USD','EUR','MYR'} for f in fs)
