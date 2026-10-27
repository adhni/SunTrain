"""Pakistan/Bangladesh sourced footprints, exact modern airports, national clocks and fares."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import gzip,json,re
import pytest
from dashboard import flights,international_network
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from dashboard.pakistan_bangladesh_flights import COUNTRIES
from dashboard.i18n import CATALOGUES
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from scripts.sourced_flights import prepare_cached,validate_query,collection_routes
from tests.test_google_flights import segment,scripts
DAY='2026-11-02'

@pytest.mark.parametrize('code,offset,launch,domestic',[('PK',5,23,46),('BD',6,8,22)])
def test_exact_identities_sources_one_date_and_year_round_clocks(code,offset,launch,domestic,tmp_path):
    cfg=country_config(code);m=cfg['manifest'];p=COUNTRIES[code];a={a['code']:a for a in m['airports']};city=p['slug']+'_flights'
    assert city in CITIES and city not in international_network.CITIES
    assert cfg['currency']=='USD' and cfg['max_duration']==86400
    assert len(m['launch_airports'])==launch and not m['archive_reuse_routes']
    assert {d for d,_,_ in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert all(a[x]['country']==code or a[y]['country']==code for x,y in m['routes'])
    assert sum(a[x]['country']==a[y]['country']==code for x,y in m['routes'])==domestic
    assert {(e['origin'],e['destination']) for e in m['evidence']}==set(map(tuple,m['routes']))
    assert all(e['sources'] for e in m['evidence'])
    assert set(collection_routes(tmp_path,cfg))==set(map(tuple,m['new_collection_routes']))
    for port in a.values():
        if port['country']==code:
            assert port['timezone']==p['zone']
            for month in [1,7,11]:assert datetime(2026,month,2,12,tzinfo=ZoneInfo(port['timezone'])).utcoffset().total_seconds()==offset*3600
    if code=='PK':
        assert a['ISB']['icao']=='OPIS' and a['GWD']['icao']=='OPGW' and a['KHI']['icao']=='OPKC'
        assert a['LYP']['icao']=='OPFA' and a['KDU']['icao']=='OPSD'
        assert ['ISB','KDU'] in m['routes'] and ['KDU','ISB'] in m['routes']
    else:
        assert a['DAC']['icao']=='VGHS' and a['CGP']['icao']=='VGEG' and a['ZYL']['icao']=='VGSY'
        assert ['CXB','SPD'] in m['routes'] and ['ZYL','CXB'] in m['routes']
        assert ['BZL','RJH'] not in m['routes']  # No all-pairs expansion.
    for sentence in re.split(r'(?<=[.!?])\s+',m['replay_note']):assert CATALOGUES['id'][sentence]!=sentence

@pytest.mark.parametrize('code,origin,destination,carrier',[('PK','KHI','ISB','PK'),('BD','DAC','CGP','BG')])
@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_overnight_original_fares_and_partial_offline_preparation(code,origin,destination,carrier,currency,tmp_path):
    cfg=country_config(code);row=segment(origin,destination,[23,30],[1,30],120,carrier=carrier,number='100');row[21]=[2026,11,3]
    fs=parse_results(scripts(row),origin,destination,DAY,cfg['zones'],[],86400);assert len(fs)==1
    fs[0]['price']=dict(currency=currency,amount_minor=12345,adults=1,cabin='economy',trip_type='one_way')
    q=dict(date=DAY,origin=origin,destination=destination,captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)
    validate_query(q,(DAY,origin,destination),cfg)
    pairs=[[origin,destination],[destination,origin]];cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    path=tmp_path/f'{DAY}-{origin}-{destination}.json';path.write_text(json.dumps(q));original=path.read_bytes();out=tmp_path/'day.gz'
    prepare_cached(tmp_path,out,cfg);first=out.read_bytes();prepare_cached(tmp_path,out,cfg)
    assert first==out.read_bytes() and original==path.read_bytes()
    r=load_domestic(out,code);assert len(r['flights'])==1 and r['flights'][0]['price']['currency']==currency
    assert r['metadata']['uncollected_queries']==[[DAY,destination,origin]]
    assert datetime.fromtimestamp(fs[0]['arrival'],ZoneInfo(cfg['zones'][destination])).date().isoformat()=='2026-11-03'


def test_regional_government_facts_hash_and_no_fabricated_pdf_hash():
    import hashlib
    root=Path(__file__).resolve().parents[1];m=json.loads((root/'data/sources/bangladesh_flights_discovery.json').read_text())
    for r in m['supplemental_airport_maps']:
        normalized=json.dumps(dict(airport=r['airport'],destinations=r['destinations']),sort_keys=True,separators=(',',':')).encode()
        assert r['documents'][0]['facts_sha256']==hashlib.sha256(normalized).hexdigest()
        assert 'sha256' not in r['documents'][0]

@pytest.mark.parametrize('code,total,domestic,queries,reused',[('PK',293,64,260,124),('BD',243,99,110,55)])
def test_prepared_reference_unique_local_dates_and_honest_prices(code,total,domestic,queries,reused):
    p=COUNTRIES[code];r=load_domestic(flights.reference_path(DAY,p['slug']+'_flights'),code);m=r['metadata'];fs=r['flights'];zones=country_config(code)['zones']
    assert len(fs)==len({f['id'] for f in fs})==total
    assert sum(f['flight_scope']=='domestic' for f in fs)==domestic
    assert m['coverage']['queries_captured']==queries and m['queries_reused']==reused
    assert not m['failed_queries'] and not m['uncollected_queries'] and m['coverage']['rejected_records']==0
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(zones[f['origin']])).date().isoformat()==DAY for f in fs)
    assert sum(bool(f.get('price')) for f in fs)==(289 if code=='PK' else 163)
    if code=='PK':assert len([q for q in m['queries'] if q.get('domestic_recheck')])==1
    else:assert sum(f['flight_scope']=='domestic' and not f.get('price') for f in fs)==43
