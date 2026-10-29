"""Africa's sourced footprint, exact dates, original currencies and offline replay."""
from copy import deepcopy
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights,international_network,replay_http
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from scripts.prepare_africa_routes import AFRICAN,DAY
from scripts.prepare_africa_flights import collection_routes,prepare_cached,seed,validate_query
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from tests.test_google_flights import segment,scripts

CITY='africa_flights'


def query(currency='USD'):
    cfg=country_config('AFRICA')
    rows=[segment('JNB','CPT',[23,30],[1,30],120,carrier='FA',number='100')]
    rows[0][21]=[2026,11,3]
    fs=parse_results(scripts(*rows),'JNB','CPT',DAY,cfg['zones'],max_duration=86400)
    for f in fs:f['price']=dict(currency=currency,amount_minor=10000,adults=1,cabin='economy',trip_type='one_way')
    return dict(date=DAY,origin='JNB',destination='CPT',captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)


def test_manifest_uses_sources_one_date_and_separate_airport_identities():
    cfg=country_config('AFRICA');m=cfg['manifest'];hubs=set(m['launch_airports'])
    assert len(hubs)==30 and {'BJR','GRJ','SSH','AGA','MBA','ZNZ'}<=hubs
    assert cfg['currency']=='USD' and cfg['max_duration']==86400
    assert {q[0] for q in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert {(r['origin'],r['destination']) for r in m['evidence']}==set(map(tuple,m['routes']))
    assert all(r['sources'] for r in m['evidence'])
    air={a['code']:a for a in m['airports']}
    expanded=set(map(tuple,m['expanded_routes']))
    reused={(r['origin'],r['destination']) for r in m['reuse_sources']}|set(map(tuple,m['archive_reuse_routes']))|expanded
    for a,b in m['routes']:
        assert any(air[c]['country'] in AFRICAN for c in (a,b))
        if any(air[c]['country'] in AFRICAN and c not in hubs for c in (a,b)):assert (a,b) in reused
    for a,b in m['new_collection_routes']:
        assert (a,b) in expanded or all(air[c]['country'] not in AFRICAN or c in hubs for c in (a,b))
    assert air['CAI']['timezone']=='Africa/Cairo' and air['CMN']['timezone']=='Africa/Casablanca'
    assert air['JNB']['icao']!=air.get('HLA',{}).get('icao')
    assert not any('replay_timezone' in a for a in air.values())
    assert CITIES[CITY]['default_flight_scope']=='both' and CITIES[CITY]['flight_view_kind']=='region'
    assert CITY not in international_network.CITIES
    assert country_config('US')['currency']=='USD' and country_config('EUROPE_AMERICAS')['currency']=='EUR'


def test_missing_reuse_only_capture_never_triggers_expansion(tmp_path):
    cfg=country_config('AFRICA');m=cfg['manifest']
    pending=set(collection_routes(tmp_path,cfg))
    assert pending==set(map(tuple,m['new_collection_routes']))
    assert pending<set(map(tuple,m['routes']))


def test_seed_preserves_intact_latest_source_and_rejects_short_empty_captures(tmp_path,monkeypatch):
    from scripts import prepare_africa_flights as collector
    import hashlib
    monkeypatch.setattr(collector,'ROOT',tmp_path)
    sources=[]
    for currency,stamp in [('USD','2026-10-27T05:00:00+08:00'),('EUR','2026-10-27T00:00:00Z')]:
        directory=tmp_path/f'.cache/google-flights-test-{currency}';directory.mkdir(parents=True)
        q=query(currency);q['captured_at']=stamp
        path=directory/f'{DAY}-JNB-CPT.json';path.write_text(json.dumps(q));sources.append(path)
    empty={**query(),'origin':'CPT','destination':'JNB','flights':[],'status':'no_matching_direct_flights','capture_context':{'max_duration':28800}}
    (sources[0].parent/f'{DAY}-CPT-JNB.json').write_text(json.dumps(empty))
    originals={p:p.read_bytes() for p in sources};cache=tmp_path/'prepared-cache'
    report=seed(cache,country_config('AFRICA'))
    assert report['seeded']==1 and report['incompatible_sources']=={'Short parser empty result':1}
    q=json.loads((cache/f'{DAY}-JNB-CPT.json').read_text())
    assert q['flights'][0]['price']['currency']=='EUR'
    assert q['reused_capture_sha256']==hashlib.sha256(originals[sources[1]]).hexdigest()
    assert not (cache/f'{DAY}-CPT-JNB.json').exists()
    assert all(p.read_bytes()==originals[p] for p in sources)
    assert seed(cache,country_config('AFRICA'))['seeded']==0


@pytest.mark.parametrize('mutation',['airport','date','duration','currency','quote','timestamp','conflict','rejected','unverified','empty_short_parser'])
def test_reuse_rejects_incompatible_data(mutation):
    q=query();cfg=country_config('AFRICA')
    if mutation=='airport':q['destination']='HLA'
    if mutation=='date':q['flights'][0]['departure']+=86400;q['flights'][0]['arrival']+=86400
    if mutation=='duration':q['flights'][0]['arrival']=q['flights'][0]['departure']+86401
    if mutation=='currency':q['flights'][0]['price']['currency']='EUR'
    if mutation=='quote':q['flights'][0]['price']['adults']=2
    if mutation=='timestamp':q['captured_at']='2026-10-27T00:00:00'
    if mutation=='conflict':q['flights'].append({**q['flights'][0],'airline':'Conflict'})
    if mutation=='rejected':q['rejected_flights']=[{'reason':'Ambiguous date'}]
    if mutation=='unverified':q['price_error']='Unknown context'
    if mutation=='empty_short_parser':q.update(flights=[],status='no_matching_direct_flights')
    with pytest.raises(ValueError):validate_query(q,(DAY,'JNB','CPT'),cfg)


@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_cached_quotes_preserve_original_currency_and_overnight_arrivals(currency):
    q=query(currency);validate_query(q,(DAY,'JNB','CPT'),country_config('AFRICA'))
    assert datetime.fromtimestamp(q['flights'][0]['arrival'],ZoneInfo('Africa/Johannesburg')).date().isoformat()=='2026-11-03'
    assert q['flights'][0]['price']['currency']==currency


def test_short_regional_and_long_haul_duration_limits():
    cfg=country_config('AFRICA')
    for minutes in [1,2,120,1000,1440]:
        q=query();q['flights'][0]['arrival']=q['flights'][0]['departure']+minutes*60
        validate_query(q,(DAY,'JNB','CPT'),cfg)
    assert country_config('SOUTH_AMERICA')['max_duration']==28800


def test_source_duration_and_seasonal_airport_clocks():
    cfg=country_config('AFRICA')
    for code,hours in [('CAI',2),('CMN',0),('ADD',3),('JNB',2),('MRU',4)]:
        local=datetime(2026,11,2,12,tzinfo=ZoneInfo(cfg['zones'][code]))
        assert local.utcoffset().total_seconds()==hours*3600
    row=segment('CAI','CMN',[12,0],[16,0],360,carrier='MS',number='1')
    assert len(parse_results(scripts(row),'CAI','CMN',DAY,cfg['zones'],max_duration=86400))==1
    row[11]=100
    with pytest.raises(ValueError,match='Source duration'):
        parse_results(scripts(row),'CAI','CMN',DAY,cfg['zones'],max_duration=86400)


def test_offline_preparation_missing_queries_mixed_quotes_and_http(tmp_path,monkeypatch):
    cfg=country_config('AFRICA');pairs=[['JNB','CPT'],['CPT','JNB']]
    manifest={k:v for k,v in cfg['manifest'].items() if k not in {'starter_record_audit','offline_recovery_audit'}}
    cfg={**cfg,'manifest':{**manifest,'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    cache=tmp_path/'cache';cache.mkdir();q=query('EUR');q['reused_source']='original-eur.json'
    path=cache/f'{DAY}-JNB-CPT.json';path.write_text(json.dumps(q));original=path.read_bytes()
    out=tmp_path/'day.gz';prepare_cached(cache,out,cfg);first=out.read_bytes();prepare_cached(cache,out,cfg)
    assert out.read_bytes()==first and path.read_bytes()==original
    raw=load_domestic(out,'AFRICA');assert len(raw['flights'])==1
    assert raw['flights'][0]['flight_scope']=='domestic' and raw['flights'][0]['price']['currency']=='EUR'
    assert raw['metadata']['uncollected_queries']==[[DAY,'CPT','JNB']]
    assert raw['metadata']['queries_reused']==1
    monkeypatch.setenv('SUNTRAIN_AFRICA_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    replay=flights.replay_day(DAY,CITY);assert len(replay['services'])==1 and replay['timezone']=='UTC'
    assert replay['flight_view_kind']=='region'
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();url=replay_http.descriptor(DAY,CITY)['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['city']==CITY
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404
    bad=deepcopy(raw);bad['flights'][0]['price']['currency']='GBP'
    with gzip.open(out,'wt') as stream:json.dump(bad,stream)
    with pytest.raises(ValueError):load_domestic(out,'AFRICA')


def test_reference_records_unique_and_origin_local_date():
    raw=load_domestic(flights.reference_path(DAY,CITY),'AFRICA');cfg=country_config('AFRICA')
    assert raw['flights'] and len(raw['flights'])==len({f['id'] for f in raw['flights']})
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in raw['flights'])
    assert sum(v['flights'] for v in raw['metadata']['coverage_by_geography'].values())==len(raw['flights'])
    assert len(raw['flights'])==3693 and len({f['carrier'] for f in raw['flights']})==137
    assert raw['metadata']['coverage']['queries_captured']==2749
    assert raw['metadata']['coverage']['routes_returned']==1591
    assert not raw['metadata']['uncollected_queries'] and not raw['metadata']['failed_queries']
    assert raw['metadata']['queries_reused']==587
    assert raw['metadata']['google_capture_coverage']=={'queries':2655,'reused':493,'not_returned':1166}
    assert sum(bool(f.get('price')) for f in raw['flights'])==2932
    assert raw['metadata']['coverage_by_geography']['domestic']['flights']==1253
    assert raw['metadata']['coverage_by_geography']['intra_african']['flights']==586


def test_all_existing_dated_europe_africa_records_retained_without_inventing_fares():
    from scripts.prepare_africa_routes import ROOT
    with gzip.open(ROOT/'data/reference/europe_flights/2026-11-02.json.gz','rt') as stream:old=json.load(stream)
    air={a['code']:a for a in old['airports']}
    original={f['id']:f for f in old['flights'] if f.get('source_date')==DAY and any(air[f[k]]['country'] in AFRICAN for k in ('origin','destination'))}
    raw=load_domestic(flights.reference_path(DAY,CITY),'AFRICA');records={f['id']:f for f in raw['flights']}
    assert len(original)>=516 and original.keys()<=records.keys()
    supplement=raw['metadata']['archive_supplement']
    assert supplement['added_flights']==105 and supplement['directions_without_google_capture']==94
    for key in supplement['added_flight_ids']:
        assert not records[key].get('price')
        for field in ['departure','arrival','source_page','source_captured_at','timing_basis']:
            assert records[key][field]==original[key][field]


def test_every_replay_note_sentence_is_translated():
    import re
    from dashboard.i18n import CATALOGUES
    for sentence in re.split(r'(?<=[.!?])\s+',country_config('AFRICA')['manifest']['replay_note']):
        assert sentence in CATALOGUES['id'] and CATALOGUES['id'][sentence]!=sentence
