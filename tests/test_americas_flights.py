"""Sourced route budgets, offline regional reuse, exact airports and cross-region dates."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from flask import Flask
from dashboard import flights, international_network, replay_http
from dashboard.cities import CITIES
from dashboard.flight_profiles import load_domestic
from scripts.prepare_americas_routes import build, combined_manifest, budget, DAY, ROOT
from scripts.prepare_americas_flights import prepare_combined
from scripts.prepare_google_flights import country_config, expected_queries, parse_results
from tests.test_google_flights import segment, scripts


def test_sourced_shortlist_has_no_cartesian_expansion_or_city_airport_substitution():
    shortlist = build()
    assert shortlist == json.loads((ROOT/'data/sources/americas_connections_routes.json').read_text())
    assert combined_manifest(shortlist) == json.loads((ROOT/'data/sources/americas_flights_routes.json').read_text())
    north, south = map(set, [shortlist['regions']['north'], shortlist['regions']['south']])
    assert (len(north), len(south)) == (50,27)
    pairs = set(map(tuple, shortlist['routes']))
    assert len(pairs) == 338 and len(shortlist['routes']) == len(pairs)
    assert all(((a in north and b in south) or (a in south and b in north)) and (b,a) in pairs for a,b in pairs)
    evidence = {(e['origin'], e['destination']) for e in shortlist['evidence']}
    assert all((a,b) in evidence or (b,a) in evidence for a,b in pairs)
    assert all(s in shortlist['sources'] for e in shortlist['evidence'] for s in e['source_ids'])
    assert all(not set(p)&{'CGH','SDU','AEP','CWB','LGA','DCA'} for p in pairs)
    assert ('GRU','JFK') in pairs and ('EZE','MIA') in pairs and ('GEO','PTY') in pairs
    assert ('PBM','MIA') not in pairs and ('BOG','LAX') not in pairs and ('BOG','DEN') not in pairs
    assert ('GRU','YYC') not in pairs and ('SCL','DFW') not in pairs
    # SJO's official list adds CTG even though the reviewed southern directory omitted it.
    assert ('SJO','CTG') in pairs and ('CTG','SJO') in pairs
    assert {q[0] for q in shortlist['queries']} == {DAY}
    assert {tuple(q[1:]) for q in shortlist['queries']} == pairs


def test_budget_reuses_only_matching_successful_usd_queries(tmp_path):
    manifest = build()
    a,b = manifest['routes'][0]
    path = tmp_path/f'{DAY}-{a}-{b}.json'
    q = dict(date=DAY,origin=a,destination=b,status='no_matching_direct_flights',flights=[],url='https://www.google.com/travel/flights?curr=USD')
    path.write_text(json.dumps(q))
    report = budget(manifest,tmp_path)
    assert report['new_queries']==337 and report['reusable_queries']==1
    assert report['directions_avoided']==2362 and report['possible_cross_region_directions']==2700
    assert report['currency']=='USD' and report['dates']==[DAY] and report['concurrency']==2
    q['url']=q['url'].replace('USD','BRL');path.write_text(json.dumps(q))
    assert budget(manifest,tmp_path)['incompatible_captures']==[str(path)]
    path.write_text('{')
    assert budget(manifest,tmp_path)['reusable_queries']==0


def test_cross_region_local_day_long_duration_overnight_and_frozen_canadian_clock():
    cfg=country_config('AMERICAS')
    assert len(cfg['manifest']['routes'])==3490
    assert list(expected_queries(DAY,[('MIA','GRU'),('GRU','MIA')],cfg))==[(DAY,'GRU','MIA'),(DAY,'MIA','GRU')]
    assert cfg['zones']['YVR']=='Etc/GMT+7' and cfg['zones']['YYZ']=='America/Toronto'
    assert cfg['max_duration']==57600 and cfg['currency']=='USD'
    row=segment('LAX','GRU',[22,0],[13,0],600,carrier='LA',number='9000');row[21]=[2026,11,3]
    with pytest.raises(ValueError,match='duration'):
        parse_results(scripts(row),'LAX','GRU',DAY,cfg['zones'])
    result=parse_results(scripts(row,row),'LAX','GRU',DAY,cfg['zones'],max_duration=cfg['max_duration'])
    assert len(result)==1 and result[0]['arrival']-result[0]['departure']==36000
    assert datetime.fromtimestamp(result[0]['departure'],ZoneInfo('UTC')).date().isoformat()=='2026-11-03'
    assert CITIES['americas_flights']['timezone']=='UTC' and CITIES['americas_flights']['default_flight_scope']=='both'
    assert 'americas_flights' not in international_network.CITIES


def test_combination_preserves_every_existing_record_and_handles_missing_cross_queries(tmp_path,monkeypatch):
    cfg=country_config('AMERICAS');out=tmp_path/'week.gz';cache=tmp_path/'cache';cache.mkdir()
    row=segment('LAX','GRU',[22,0],[13,0],600,carrier='LA',number='9000');row[21]=[2026,11,3]
    fs=parse_results(scripts(row),'LAX','GRU',DAY,cfg['zones'],max_duration=cfg['max_duration'])
    q=dict(date=DAY,origin='LAX',destination='GRU',status='results',flights=fs,
        captured_at='2026-10-27T00:00:00Z',url='https://www.google.com/travel/flights?curr=USD')
    (cache/f'{DAY}-LAX-GRU.json').write_text(json.dumps(q))
    (cache/f'{DAY}-GRU-LAX.error.json').write_text(json.dumps(dict(date=DAY,origin='GRU',destination='LAX',error='fixture failure')))
    prepare_combined(cache,out,cfg);first=out.read_bytes();prepare_combined(cache,out,cfg)
    assert out.read_bytes()==first
    raw=load_domestic(out,'AMERICAS')
    assert len(raw['airports'])==77 and len(raw['flights'])==9668+1629+1
    meta=raw['metadata'];counts=meta['coverage']
    assert meta['profile']=='americas' and len(meta['queries'])==3153 and len(meta['uncollected_queries'])==337
    assert counts['failed_queries']==1 and counts['unattempted_queries']==336
    assert len({f['id'] for f in raw['flights']})==len(raw['flights'])
    records={f['id']:f for f in raw['flights']}
    for item,code in zip(cfg['manifest']['input_snapshots'],['US','SOUTH_AMERICA']):
        for f in load_domestic(ROOT/item['path'],code)['flights']:
            assert records[f['id']]==f
    monkeypatch.setenv('SUNTRAIN_AMERICAS_FLIGHTS_REFERENCE',str(out))
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path/'http'))
    replay=flights.replay_day(DAY,'americas_flights')
    assert len(replay['services'])==len(raw['flights']) and len(replay['stations'])==77
    assert all(replay['start']<=s['stops'][0][1]<s['stops'][1][1]<replay['end'] for s in replay['services'])
    assert all(c[0]<0 for p in replay['paths'].values() for c in p['coordinates'])
    assert all(f['flight_scope']=='domestic' for f in raw['flights'] if {f['origin'],f['destination']}=={'JFK','SJU'})
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    url=replay_http.descriptor(DAY,'americas_flights')['url']
    response=client.get(url,headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200 and json.loads(gzip.decompress(response.data))['city']=='americas_flights'
    assert client.get(url,headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(url.replace(DAY,'2026-11-03')).status_code==404


def test_published_archive_preserves_inputs_and_search_budget():
    path=flights.reference_path(DAY,'americas_flights')
    if not path.exists():
        pytest.skip('Collection not yet prepared')
    raw=load_domestic(path,'AMERICAS');cfg=country_config('AMERICAS')
    pairs=set(map(tuple,cfg['manifest']['routes']))
    assert len(raw['metadata']['queries'])+len(raw['metadata']['uncollected_queries'])==3490
    assert {a['code'] for a in raw['airports']}=={a['code'] for a in cfg['manifest']['airports']}
    for f in raw['flights']:
        assert (f['origin'],f['destination']) in pairs
        assert datetime.fromtimestamp(f['departure'],ZoneInfo(cfg['zones'][f['origin']])).date().isoformat()==DAY
        assert not f.get('price') or f['price']['currency']=='USD'
