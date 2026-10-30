"""The global union inherits validated views, never raw superseded captures."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest
from dashboard import world_flights as world
from dashboard.flight_sources import cached_reference_reads, read_reference


def airport(code='AAA', **extra):
    return dict(code=code, name=code, country='AU', icao=code, timezone='Australia/Melbourne',
                lon=145, lat=-38, mode='flight', **extra)


def flight(id='one', **extra):
    return {**dict(id=id, number='ZZ1', carrier='ZZ', origin='AAA', destination='BBB',
                departure=world.START+3600, arrival=world.START+7200, flight_scope='domestic'), **extra}


def view(city, records):
    return city, {'airports': [airport(), airport('BBB')], 'flights': records,
                  'metadata': {'coverage': {}}}, (world.START-86400, world.END+86400)


def quote(currency='USD', amount=10000, **extra):
    return {**dict(currency=currency, amount_minor=amount, adults=1, cabin='economy', trip_type='one_way'), **extra}


def test_exact_dedup_distinct_numbers_alias_ids_and_input_immutability():
    a=flight();same=flight('other-source');distinct=flight('two', number='ZZ2')
    inputs=[view('a',[a,distinct]),view('b',[same])];before=deepcopy(inputs)
    result=world.merge_views(inputs)
    assert inputs==before and len(result['flights'])==2
    merged=next(f for f in result['flights'] if f['number']=='ZZ1')
    assert merged['id'].startswith('world:')
    assert merged['provenance']['source_ids']==['one','other-source']
    assert merged['provenance']['views']==['a','b']
    with pytest.raises(ValueError,match='source flight ID'):
        world.merge_views([view('a',[a]),view('b',[flight(departure=world.START+3601)])])


def test_window_includes_midnight_arrivals_and_overnights_but_not_next_day_departures():
    records=[flight('arrives-at-start',departure=world.START-60,arrival=world.START),
             flight('overnight',departure=world.END-60,arrival=world.END+60),
             flight('too-early',departure=world.START-120,arrival=world.START-1),
             flight('next-day',departure=world.END,arrival=world.END+60)]
    result=world.merge_views([view('a',records)])
    assert {f['id'] for f in result['flights']}=={'arrives-at-start','overnight'}


def test_preserve_all_quotes_choose_cheapest_per_currency_and_prefer_usd():
    inputs=[view('a',[flight(price=quote('EUR',10),aircraft='A320')]),
            view('b',[flight(price=quote('USD',15000))]),
            view('c',[flight(price=quote('USD',10000))]),
            view('d',[flight(price=quote('MYR',20))])]
    result=world.merge_views(inputs)['flights'][0]
    assert result['price']==quote('USD',10000)
    assert len(result['fare_quotes'])==4 and result['aircraft']=='A320'
    for unknown in ['Unknown','unknown','Aircraft not specified','N/A','']:
        known=world.merge_views([view('a',[flight(aircraft=unknown)]),view('b',[flight(aircraft='A320')])])['flights'][0]
        assert known['aircraft']=='A320' and 'aircraft_variants' not in known
    assert {q['currency'] for q in result['fare_quotes']}=={'USD','MYR','EUR'}
    with pytest.raises(ValueError,match='Incompatible captured fare'):
        world.merge_views([view('a',[flight(price=quote(adults=2))])])
    conflict=world.merge_views([view('a',[flight(aircraft='A320')]),view('b',[flight(aircraft='B737')])])['flights'][0]
    assert conflict['aircraft']=='Aircraft differs between captures'
    assert {v['aircraft'] for v in conflict['aircraft_variants']}=={'A320','B737'}


def test_reviewed_airport_aliases_frozen_zones_and_unexpected_conflicts():
    for code,(canonical,aliases) in world.TIMEZONES.items():
        for alias in aliases:
            a={**airport(code),'timezone':alias,'icao':world.ICAOS.get(code,(code,))[0]}
            assert world.canonical_airport(a)['timezone']==canonical
    for code,(canonical,aliases) in world.ICAOS.items():
        for alias in aliases:
            a={**airport(code),'icao':alias,'timezone':world.TIMEZONES.get(code,('Australia/Melbourne',))[0]}
            assert world.canonical_airport(a)['icao']==canonical
    vancouver={**airport('YVR'),'country':'CA','timezone':'America/Vancouver'}
    assert world.canonical_airport(vancouver)['replay_timezone']=='Etc/GMT+7'
    airports={};world.merge_airport(airports,airport())
    for field,value in [('country','ID'),('lat',-37),('lon',146),('timezone','UTC')]:
        with pytest.raises(ValueError,match='airport identity'):
            world.merge_airport(airports,{**airport(),field:value})
    with pytest.raises(ValueError,match='Unreviewed'):
        world.canonical_airport({**airport('GVA'),'timezone':'UTC'})


def test_preparation_cache_reads_once_isolates_mutation_and_releases(tmp_path,monkeypatch):
    path=tmp_path/'source.gz';path.write_bytes(gzip.compress(b'{"flights": [1]}',mtime=0))
    read=Path.read_bytes;calls=[]
    def tracked(p):calls.append(p);return read(p)
    monkeypatch.setattr(Path,'read_bytes',tracked)
    with cached_reference_reads() as inputs:
        first=read_reference(path);first['flights'].append(2)
        assert read_reference(path)=={'flights':[1]}
        assert inputs[path.resolve()]['sha256']==hashlib.sha256(read(path)).hexdigest()
    assert calls==[path.resolve()]
    path.write_bytes(gzip.compress(b'{"flights": [3]}',mtime=0))
    assert read_reference(path)=={'flights':[3]}


def test_compact_http_uses_only_snapshot_preserves_records_and_cache(tmp_path, monkeypatch):
    from flask import Flask
    from dashboard import flights, replay_http as http
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE', str(tmp_path/'http'))
    original = flights.load_reference
    calls = []
    def load(day, city):
        assert city == 'world_flights', 'HTTP rebuilt a member view'
        calls.append(city)
        return original(day, city)
    monkeypatch.setattr(flights, 'load_reference', load)
    app=Flask(__name__);http.register_replay_routes(app)
    client=app.test_client();info=http.descriptor(world.DAY,'world_flights')
    response=client.get(info['url'], headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200
    payload=json.loads(gzip.decompress(response.data))
    source=world.load_reference(world.DAY)
    # Data expansion increases the total download; keep the compact transfer
    # density bounded rather than pretending the original corpus is unchanged.
    assert len(response.data)<=max(5*1024*1024,110*len(source['flights']))
    assert calls==['world_flights'] and len(payload['services'])==len(source['flights'])
    assert payload['flight_geometry']=='great_circle_v1'
    assert payload['flight_view_kind']=='network' and payload['timezone']=='UTC'
    assert payload['initial']==world.START+36000 and payload['end']==world.END
    assert len(payload['paths'])==source['metadata']['coverage']['routes_returned']
    assert all('coordinates' not in p and len(p['endpoints'])==2 for p in payload['paths'].values())
    assert not {'queries','wizzair_inventory'} & payload['schedule'].keys()
    assert {s['id'] for s in payload['services']}=={f['id'] for f in source['flights']}
    by_id={f['id']:f for f in source['flights']}
    for service in payload['services']:
        f=by_id[service['id']]
        assert service.get('price')==f.get('price')
        assert service.get('fare_quotes')==f.get('fare_quotes')
        assert service.get('aircraft_variants')==f.get('aircraft_variants')
        assert payload['stations'][service['stops'][0][0]]['code']==f['origin']
        assert payload['stations'][service['stops'][1][0]]['code']==f['destination']
        assert service['stops'][0][2]==f['departure'] and service['stops'][1][1]==f['arrival']
    cached=client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']})
    assert cached.status_code==304 and calls==['world_flights']
    assert client.get(info['url'].replace(world.DAY,'2026-11-03')).status_code==404


def test_prepared_real_union_counts_inputs_and_reproducibility(tmp_path,monkeypatch):
    from dashboard import south_america_domestic as domestic
    snapshot=world.load_reference(world.DAY);meta=snapshot['metadata']
    added=domestic.load_reference()['metadata']['coverage']['new_world_identities'] if domestic.enabled() else 0
    assert len(snapshot['flights'])==meta['coverage']['flights']
    assert meta['scopes']['domestic']==27898+added and meta['scopes']['international']>25693
    assert len(meta['member_views'])==41 and len(meta['inputs'])==45+int(domestic.enabled())
    assert len({world.identity(f) for f in snapshot['flights']})==len(snapshot['flights'])
    assert len({f['id'] for f in snapshot['flights']})==len(snapshot['flights'])
    paths={world.ROOT/p for p in meta['inputs']};read=Path.read_bytes;calls=[]
    def tracked(p):
        if p in paths:calls.append(p)
        return read(p)
    monkeypatch.setattr(Path,'read_bytes',tracked)
    output=tmp_path/'world.gz';result=world.prepare(output)
    assert set(calls)==paths and len(calls)==len(paths)
    assert result==snapshot
    assert output.read_bytes()==world.reference_path().read_bytes()
    for path,info in meta['inputs'].items():
        assert hashlib.sha256(read(world.ROOT/path)).hexdigest()==info['sha256']
    with pytest.raises(ValueError,match='Unsupported World'):
        world.load_reference('2026-11-03')


def test_original_40_view_union_is_byte_identical_without_supplement(tmp_path,monkeypatch):
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE',str(tmp_path/'absent.gz'))
    monkeypatch.setenv('SUNTRAIN_SOUTH_AMERICA_DOMESTIC_REFERENCE',str(tmp_path/'absent-domestic.gz'))
    output=tmp_path/'original.gz'
    original=world.prepare(output)
    assert len(original['flights'])==53591
    assert original['metadata']['scopes']=={'domestic':27898,'international':25693}
    assert len(original['metadata']['inputs'])==44
    assert hashlib.sha256(output.read_bytes()).hexdigest()=='2de7eb21702c1027c6d0976c49d76a16e8fdf2ee7ebf228e9a4dd4bb620d677a'
