"""Türkiye's sourced footprint, exact dates, original currencies and offline replay."""
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
from scripts.prepare_turkiye_routes import DAY
from scripts.prepare_turkiye_flights import collection_routes,prepare_cached,seed,validate_query
from scripts.prepare_google_flights import country_config,expected_queries,parse_results
from tests.test_google_flights import segment,scripts

CITY='turkiye_flights'


def query(currency='USD'):
    cfg=country_config('TR')
    rows=[segment('IST','ADB',[23,30],[1,30],120,carrier='TK',number='100')]
    rows[0][21]=[2026,11,3]
    fs=parse_results(scripts(*rows),'IST','ADB',DAY,cfg['zones'],max_duration=86400)
    for f in fs:f['price']=dict(currency=currency,amount_minor=10000,adults=1,cabin='economy',trip_type='one_way')
    return dict(date=DAY,origin='IST',destination='ADB',captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr='+currency,status='results',flights=fs,page_sha256='0'*64)


def test_manifest_uses_sources_one_date_and_separate_airport_identities():
    cfg=country_config('TR');m=cfg['manifest'];hubs=set(m['launch_airports'])
    assert hubs=={'IST','SAW','ESB','ADB','AYT'} and set(m['worldwide_hubs'])=={'IST','SAW'}
    assert cfg['currency']=='USD' and cfg['max_duration']==86400
    assert {q[0] for q in expected_queries(DAY,m['routes'],cfg)}=={DAY}
    assert len(m['routes'])==len(set(map(tuple,m['routes'])))
    assert {(r['origin'],r['destination']) for r in m['evidence']}==set(map(tuple,m['routes']))
    assert all(r['sources'] for r in m['evidence'])
    air={a['code']:a for a in m['airports']}
    reused={(r['origin'],r['destination']) for r in m['reuse_sources']}|set(map(tuple,m['archive_reuse_routes']))
    for a,b in m['routes']:
        assert any(air[c]['country']=='TR' for c in (a,b))
        if air[a]['country']!=air[b]['country'] and any(air[c]['country']=='TR' and c not in hubs for c in (a,b)):assert (a,b) in reused
    for a,b in m['new_collection_routes']:
        if air[a]['country']!=air[b]['country']:assert all(air[c]['country']!='TR' or c in hubs for c in (a,b))
    domestic={(a,b) for a,b in m['new_collection_routes'] if air[a]['country']==air[b]['country']=='TR'}
    assert len(domestic)==306 and len({c for pair in domestic for c in pair})==49
    assert {('IST','TZX'),('TZX','IST'),('SAW','VAN'),('VAN','SAW'),('ESB','COV'),('COV','ESB')}<=domestic
    assert ('VAN','TZX') not in domestic  # No unsupported regional all-pairs expansion.
    for a,b in domestic:
        assert {a,b}&hubs
        assert any(source['source'].endswith('-routes.svg') for row in m['evidence'] if (row['origin'],row['destination'])==(a,b) for source in row['sources'])
    assert air['IST']['icao']=='LTFM' and air['SAW']['icao']=='LTFJ'
    assert not m['archive_reuse_routes']
    assert 'ISL' not in hubs
    assert ['IST','SAW'] not in m['new_collection_routes']
    for a,b in m['new_collection_routes']:
        if air[a]['country']!=air[b]['country']:assert {a,b}&{'IST','SAW'}
    assert not any('replay_timezone' in a for a in air.values())
    assert CITIES[CITY]['default_flight_scope']=='both' and CITIES[CITY]['flight_view_kind']=='country'
    assert CITY not in international_network.CITIES
    assert country_config('US')['currency']=='USD' and country_config('EUROPE_AMERICAS')['currency']=='EUR'


def test_missing_reuse_only_capture_never_triggers_expansion(tmp_path):
    cfg=country_config('TR');m=cfg['manifest']
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
        path=directory/f'{DAY}-IST-ADB.json';path.write_text(json.dumps(q));sources.append(path)
    empty={**query(),'origin':'ADB','destination':'IST','flights':[],'status':'no_matching_direct_flights','capture_context':{'max_duration':28800}}
    (sources[0].parent/f'{DAY}-ADB-IST.json').write_text(json.dumps(empty))
    originals={p:p.read_bytes() for p in sources};cache=tmp_path/'prepared-cache'
    report=seed(cache,country_config('TR'))
    assert report['seeded']==1 and report['incompatible_sources']=={'Short parser empty result':1}
    q=json.loads((cache/f'{DAY}-IST-ADB.json').read_text())
    assert q['flights'][0]['price']['currency']=='EUR'
    assert q['reused_capture_sha256']==hashlib.sha256(originals[sources[1]]).hexdigest()
    assert not (cache/f'{DAY}-ADB-IST.json').exists()
    assert all(p.read_bytes()==originals[p] for p in sources)
    assert seed(cache,country_config('TR'))['seeded']==0


@pytest.mark.parametrize('mutation',['airport','date','duration','currency','quote','timestamp','conflict','rejected','unverified','empty_short_parser'])
def test_reuse_rejects_incompatible_data(mutation):
    q=query();cfg=country_config('TR')
    if mutation=='airport':q['destination']='ISL'
    if mutation=='date':q['flights'][0]['departure']+=86400;q['flights'][0]['arrival']+=86400
    if mutation=='duration':q['flights'][0]['arrival']=q['flights'][0]['departure']+86401
    if mutation=='currency':q['flights'][0]['price']['currency']='EUR'
    if mutation=='quote':q['flights'][0]['price']['adults']=2
    if mutation=='timestamp':q['captured_at']='2026-10-27T00:00:00'
    if mutation=='conflict':q['flights'].append({**q['flights'][0],'airline':'Conflict'})
    if mutation=='rejected':q['rejected_flights']=[{'reason':'Ambiguous date'}]
    if mutation=='unverified':q['price_error']='Unknown context'
    if mutation=='empty_short_parser':q.update(flights=[],status='no_matching_direct_flights')
    with pytest.raises(ValueError):validate_query(q,(DAY,'IST','ADB'),cfg)


@pytest.mark.parametrize('currency',['USD','EUR','MYR'])
def test_cached_quotes_preserve_original_currency_and_overnight_arrivals(currency):
    q=query(currency);validate_query(q,(DAY,'IST','ADB'),country_config('TR'))
    assert datetime.fromtimestamp(q['flights'][0]['arrival'],ZoneInfo('Europe/Istanbul')).date().isoformat()=='2026-11-03'
    assert q['flights'][0]['price']['currency']==currency


def test_short_regional_and_long_haul_duration_limits():
    cfg=country_config('TR')
    for minutes in [1,2,120,1000,1440]:
        q=query();q['flights'][0]['arrival']=q['flights'][0]['departure']+minutes*60
        validate_query(q,(DAY,'IST','ADB'),cfg)
    assert country_config('SOUTH_AMERICA')['max_duration']==28800


def test_source_duration_and_turkish_airport_clocks():
    cfg=country_config('TR')
    for code in cfg['manifest']['launch_airports']:
        for month in [1,7,11]:
            local=datetime(2026,month,2,12,tzinfo=ZoneInfo(cfg['zones'][code]))
            assert local.utcoffset().total_seconds()==3*3600
    row=segment('IST','ADB',[12,0],[13,0],60,carrier='TK',number='1')
    assert len(parse_results(scripts(row),'IST','ADB',DAY,cfg['zones'],max_duration=86400))==1
    row[11]=100
    with pytest.raises(ValueError,match='Source duration'):
        parse_results(scripts(row),'IST','ADB',DAY,cfg['zones'],max_duration=86400)
    row=segment('GNJ','IST',[12,0],[13,0],120,carrier='TK',number='2')
    assert cfg['zones']['GNJ']=='Asia/Baku'
    assert len(parse_results(scripts(row),'GNJ','IST',DAY,cfg['zones'],max_duration=86400))==1


def test_offline_preparation_missing_queries_mixed_quotes_and_http(tmp_path,monkeypatch):
    cfg=country_config('TR');pairs=[['IST','ADB'],['ADB','IST']]
    cfg={**cfg,'manifest':{**cfg['manifest'],'routes':pairs},'queries':[(DAY,a,b) for a,b in pairs]}
    cache=tmp_path/'cache';cache.mkdir();q=query('EUR');q['reused_source']='original-eur.json'
    path=cache/f'{DAY}-IST-ADB.json';path.write_text(json.dumps(q));original=path.read_bytes()
    out=tmp_path/'day.gz';prepare_cached(cache,out,cfg);first=out.read_bytes();prepare_cached(cache,out,cfg)
    assert out.read_bytes()==first and path.read_bytes()==original
    raw=load_domestic(out,'TR');assert len(raw['flights'])==1
    assert raw['flights'][0]['flight_scope']=='domestic' and raw['flights'][0]['price']['currency']=='EUR'
    assert raw['metadata']['uncollected_queries']==[[DAY,'ADB','IST']]
    assert raw['metadata']['queries_reused']==1
    monkeypatch.setenv('SUNTRAIN_TURKIYE_FLIGHTS_REFERENCE',str(out));monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    replay=flights.replay_day(DAY,CITY);assert len(replay['services'])==1 and replay['timezone']=='Europe/Istanbul'
    assert replay['flight_view_kind']=='country'
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client();url=replay_http.descriptor(DAY,CITY)['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'});assert response.status_code==200
    assert json.loads(gzip.decompress(response.data))['city']==CITY
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404
    bad=deepcopy(raw);bad['flights'][0]['price']['currency']='GBP'
    with gzip.open(out,'wt') as stream:json.dump(bad,stream)
    with pytest.raises(ValueError):load_domestic(out,'TR')


def test_reference_records_unique_and_origin_local_date():
    raw=load_domestic(flights.reference_path(DAY,CITY),'TR');cfg=country_config('TR')
    assert raw['flights'] and len(raw['flights'])==len({f['id'] for f in raw['flights']})
    assert all(datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY for f in raw['flights'])
    assert sum(v['flights'] for v in raw['metadata']['coverage_by_geography'].values())==len(raw['flights'])
    assert raw['metadata']['queries_reused']==142
    assert len(raw['flights'])==2249 and len({f['carrier'] for f in raw['flights']})==73
    assert raw['metadata']['coverage']['queries_captured']==1128
    assert raw['metadata']['coverage']['routes_returned']==859
    assert not raw['metadata']['uncollected_queries'] and not raw['metadata']['failed_queries']
    assert sum(bool(f.get('price')) for f in raw['flights'])==2201
    assert raw['metadata']['coverage_by_geography']['domestic']['flights']==793
    assert raw['metadata']['coverage_by_geography']['international']['flights']==1456
    domestic_airports={f[k] for f in raw['flights'] if f['flight_scope']=='domestic' for k in ('origin','destination')}
    assert len(domestic_airports)==41 and {'TZX','VAN','COV'}<=domestic_airports
    queries={(q['origin'],q['destination']):q for q in raw['metadata']['queries']}
    assert queries['IST','ESB']['status']=='results'
    assert queries['IST','ESB']['domestic_recheck']['previous_flights']==0
    assert queries['IST','ESB']['domestic_recheck']['flights_returned']==12
    assert sum('domestic_recheck' in q for q in queries.values())==7
    from scripts.prepare_turkiye_routes import ROOT
    with gzip.open(ROOT/'data/reference/europe_flights/2026-11-02.json.gz','rt') as stream:old=json.load(stream)
    air={a['code']:a for a in old['airports']}
    from dashboard.europe_flights import OTHER_NETWORKS
    # Türkiye's frozen snapshot predates the additional European networks.
    original={f['id'] for f in old['flights'] if f.get('brand') not in OTHER_NETWORKS and f.get('source_date')==DAY and any(air[f[k]]['country']=='TR' for k in ('origin','destination'))}
    assert len(original)==38 and original<={f['id'] for f in raw['flights']}


def test_every_replay_note_sentence_is_translated():
    import re
    from dashboard.i18n import CATALOGUES
    for sentence in re.split(r'(?<=[.!?])\s+',country_config('TR')['manifest']['replay_note']):
        assert sentence in CATALOGUES['id'] and CATALOGUES['id'][sentence]!=sentence
