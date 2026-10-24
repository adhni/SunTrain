"""Cross-border scope, long-haul clocks, cache identity and exact airports."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import flights, replay_http
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from tests.test_google_flights import segment, scripts

CONFIG = country_config('ID', 'international')


def test_manifest_keeps_exact_airports_and_only_indonesian_cross_border_pairs():
    airports = {a['code']: a for a in CONFIG['manifest']['airports']}
    for a, b in CONFIG['manifest']['routes']:
        assert (airports[a]['country'] == 'ID') != (airports[b]['country'] == 'ID')
        assert [b, a] in CONFIG['manifest']['routes']
    for a, b in [('MEL','AVV'), ('BKK','DMK'), ('NRT','HND'), ('CGK','HLP')]:
        assert airports[a]['code'] != airports[b]['code']
        assert (airports[a]['lon'], airports[a]['lat']) != (airports[b]['lon'], airports[b]['lat'])
    assert airports['ADL']['timezone'] == 'Australia/Adelaide'
    assert airports['BKI']['timezone'] == airports['KCH']['timezone'] == 'Asia/Kuching'
    assert flights.airline_style('ID','Batik Air') != flights.airline_style('OD','Batik Air')
    assert all(ZoneInfo(a['timezone']) for a in airports.values())
    assert CONFIG['manifest']['historical_route_year'] == 2023
    assert CONFIG['manifest']['unresolved_airports']  # Invalid domestic row in the official table.


def test_international_queries_cover_origin_local_carry_ins_and_eastern_next_day():
    queries = set(expected_queries('2026-11-02', [('AMS','CGK'), ('AKL','DPS')], CONFIG))
    assert ('2026-10-31','AMS','CGK') in queries
    assert ('2026-11-08','AMS','CGK') in queries
    assert ('2026-11-09','AKL','DPS') in queries
    assert ('2026-11-10','AKL','DPS') not in queries
    # Every departure instant that can overlap the Jakarta week has a query.
    start = int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Jakarta')).timestamp())
    for origin, destination in [('AMS','CGK'), ('AKL','DPS')]:
        for at in range(start-86400, start+7*86400, 1800):
            local_date = datetime.fromtimestamp(at, ZoneInfo(CONFIG['zones'][origin])).date().isoformat()
            assert (local_date,origin,destination) in queries


def test_long_haul_overnight_dst_and_half_hour_offsets_use_source_duration():
    row = segment('AMS','CGK',[11,0],[7,0],840,carrier='GA',number='89')
    row[21] = [2026,11,3]
    result = parse_results(scripts(row,row),'AMS','CGK','2026-11-02',CONFIG['zones'],max_duration=86400)
    assert len(result) == 1 and result[0]['arrival']-result[0]['departure'] == 14*3600
    with pytest.raises(ValueError,match='duration'):
        parse_results(scripts(row),'AMS','CGK','2026-11-02',CONFIG['zones'])
    adl = segment('ADL','DPS',[10,0],[12,30],300)
    assert parse_results(scripts(adl),'ADL','DPS','2026-11-02',CONFIG['zones'],max_duration=86400)
    adl[11] = 330
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(adl),'ADL','DPS','2026-11-02',CONFIG['zones'],max_duration=86400)
    row[21] = [2026,11,4]
    row[11] = 2280
    with pytest.raises(ValueError,match='duration'):
        parse_results(scripts(row),'AMS','CGK','2026-11-02',CONFIG['zones'],max_duration=86400)


def write_reference(path, airports, records, metadata=None):
    with gzip.open(path,'wt') as stream:
        json.dump(dict(airports=airports,flights=records,metadata=metadata or {}),stream)


def test_merged_replay_keeps_foreign_connections_scope_and_custom_fixture_isolation(tmp_path,monkeypatch):
    catalogue = {a['code']: a for a in CONFIG['manifest']['airports']}
    start = int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Jakarta')).timestamp())
    base = dict(number='GA1',carrier='GA',airline='Garuda Indonesia',origin='CGK',departure=start,arrival=start+3600)
    domestic, international = tmp_path/'domestic.gz', tmp_path/'international.gz'
    write_reference(domestic,[catalogue['CGK'],catalogue['DPS']], [dict(base,id='domestic',destination='DPS')])
    write_reference(international,[catalogue['CGK'],catalogue['AMS']], [dict(base,id='international',destination='AMS',arrival=start+14*3600)], {'scope':'international'})
    monkeypatch.setenv('SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE',str(domestic))
    day=flights.replay_day('2026-11-02','indonesia_flights')
    assert [s['flight_scope'] for s in day['services']] == ['domestic']
    monkeypatch.setenv('SUNTRAIN_INDONESIA_INTERNATIONAL_REFERENCE',str(international))
    day=flights.replay_day('2026-11-02','indonesia_flights')
    assert {s['flight_scope'] for s in day['services']} == {'domestic','international'}
    assert len(day['stations']) == 3
    assert day['stations'][day['services'][1]['stops'][1][0]]['timezone'] == 'Europe/Amsterdam'
    before=replay_http.descriptor('2026-11-02','indonesia_flights')['revision']
    write_reference(international,[catalogue['CGK'],catalogue['AMS']], [], {'scope':'international'})
    assert replay_http.descriptor('2026-11-02','indonesia_flights')['revision'] != before
    write_reference(international,[catalogue['ADL'],catalogue['AMS']], [dict(base,id='bad',origin='ADL',destination='AMS')])
    with pytest.raises(ValueError,match='endpoint'):
        flights.replay_day('2026-11-02','indonesia_flights')
    write_reference(international,[catalogue['CGK'],catalogue['DPS']],
        [dict(base,id='bad-domestic',destination='DPS')], {'scope':'international'})
    with pytest.raises(ValueError,match='domestic flight'):
        flights.replay_day('2026-11-02','indonesia_flights')
    monkeypatch.setenv('SUNTRAIN_INDONESIA_INTERNATIONAL_REFERENCE',str(tmp_path/'missing.gz'))
    with pytest.raises(FileNotFoundError):
        flights.replay_day('2026-11-02','indonesia_flights')


def test_international_preparation_is_reproducible_and_refuses_domestic_candidates(tmp_path):
    cache=tmp_path/'cache';cache.mkdir()
    row=segment('AMS','CGK',[11,0],[7,0],840);row[21]=[2026,11,3]
    flight=parse_results(scripts(row),'AMS','CGK','2026-11-02',CONFIG['zones'],max_duration=86400)[0]
    (cache/'2026-11-02-AMS-CGK.json').write_text(json.dumps(dict(origin='AMS',destination='CGK',date='2026-11-02',
        flights=[flight],status='results',captured_at='2026-10-24T00:00:00+00:00')))
    output=tmp_path/'reference.gz'
    prepare(cache,output,'2026-11-02',[('AMS','CGK')],CONFIG)
    first=output.read_bytes()
    prepare(cache,output,'2026-11-02',[('AMS','CGK')],CONFIG)
    assert output.read_bytes()==first
    snapshot=json.loads(gzip.decompress(first))
    assert snapshot['metadata']['scope']=='international'
    assert snapshot['metadata']['coverage']['failed_or_missing_queries']>0
    with pytest.raises(ValueError,match='exactly one'):
        prepare(cache,output,'2026-11-02',[('CGK','DPS')],CONFIG)


@pytest.mark.parametrize('day',[f'2026-11-{n:02}' for n in range(2,9)])
def test_each_prepared_day_has_international_flights_with_exact_national_endpoint(day):
    payload=flights.replay_day(day,'indonesia_flights')
    services=[s for s in payload['services'] if s['flight_scope']=='international']
    assert services
    for service in services:
        a,b=[payload['stations'][stop[0]] for stop in service['stops']]
        assert (a['country']=='ID') != (b['country']=='ID')
        departure,arrival=[stop[1] for stop in service['stops']]
        assert departure < payload['end'] and arrival >= payload['start']
        assert 60 <= arrival-departure <= 86400
        assert a['code']+'-'+b['code']==service['route_id']
