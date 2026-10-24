"""Exact airports, Indonesian clocks, week boundaries and honest capture coverage."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask
import pytest

from dashboard import flights, replay_http
from dashboard.cities import city_settings
from dashboard.replay import get_replay_day
from scripts.prepare_google_flights import country_config, expected_queries, parse_results, prepare
from scripts.prepare_indonesia_airports import airport_zone
from tests.test_google_flights import segment, scripts

CONFIG = country_config('ID')


def test_manifest_is_domestic_exact_and_covers_islands_and_regions():
    m = CONFIG['manifest']
    airports = {a['code']: a for a in m['airports']}
    assert airports['CGK'] != airports['HLP']
    assert airports['YIA'] != airports['JOG']
    assert {a['island_group'] for a in airports.values()} == {
        'Java', 'Sumatra', 'Kalimantan', 'Sulawesi', 'Bali & Nusa Tenggara', 'Maluku', 'Papua'}
    assert airport_zone('ID-KB')[0] == airport_zone('ID-KT')[0] == 'Asia/Pontianak'
    assert airport_zone('ID-KI')[0] == 'Asia/Makassar'
    assert all(a != b and a in airports and b in airports for a, b in m['routes'])
    assert len(m['routes']) == len(set(map(tuple, m['routes'])))
    assert all([b, a] in m['routes'] for a, b in m['routes'])
    assert any(e.get('frequency_only') for e in m['evidence'])
    assert m['unresolved_airports']
    with pytest.raises(ValueError):
        airport_zone('ID-UNKNOWN')


def test_all_nine_dates_are_collected_for_every_exact_pair():
    queries = list(expected_queries('2026-11-02', [('CGK','DPS'), ('DPS','CGK')], CONFIG))
    assert len(queries) == 18
    assert {d for d, _, _ in queries} == {f'2026-11-{n:02}' for n in range(1,10)}


def test_exact_airports_short_flights_and_all_time_zones():
    rows = scripts(segment('CGK','DPS',[6,None],[8,None],60),
        segment('HLP','DPS',[6,None],[8,None],60))
    assert parse_results(rows,'CGK','DPS','2026-11-02',CONFIG['zones'])[0]['origin'] == 'CGK'
    assert parse_results(rows,'HLP','DPS','2026-11-02',CONFIG['zones'])[0]['origin'] == 'HLP'
    for origin, destination, depart, arrive, duration in [
        ('PNK','KTG',[6,0],[6,10],10), ('DPS','CGK',[7,0],[7,0],60),
        ('UPG','AMQ',[6,0],[8,30],90), ('DJJ','WMX',[7,0],[7,30],30)]:
        row=segment(origin,destination,depart,arrive,duration)
        result=parse_results(scripts(row,row),origin,destination,'2026-11-02',CONFIG['zones'])
        assert len(result)==1
        assert result[0]['arrival']-result[0]['departure']==duration*60
    row=segment('CGK','DJJ',[23,0],[6,0],300)
    row[21]=[2026,11,3]
    flight=parse_results(scripts(row),'CGK','DJJ','2026-11-02',CONFIG['zones'])[0]
    assert flight['arrival']-flight['departure']==5*3600
    row[11]=60
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'CGK','DJJ','2026-11-02',CONFIG['zones'])


def test_prepare_is_reproducible_and_distinguishes_missing_empty_and_failed(tmp_path):
    cache=tmp_path/'cache';cache.mkdir()
    f=parse_results(scripts(segment('CGK','DPS',[6,0],[8,0],60)), 'CGK','DPS','2026-11-02', CONFIG['zones'])[0]
    def save(day, records):
        (cache/f'{day}-CGK-DPS.json').write_text(json.dumps(dict(date=day,origin='CGK',destination='DPS',
            captured_at='2026-10-24T00:00:00+00:00',flights=records,status='results' if records else 'no_matching_direct_flights')))
    save('2026-11-02',[f]);save('2026-11-03',[])
    (cache/'2026-11-04-CGK-DPS.error.json').write_text(json.dumps(dict(date='2026-11-04',error='timeout')))
    output=tmp_path/'snapshot.json.gz'
    prepare(cache,output,'2026-11-02',[('CGK','DPS'),('HLP','SUB')],CONFIG)
    first=output.read_bytes()
    prepare(cache,output,'2026-11-02',[('CGK','DPS'),('HLP','SUB')],CONFIG)
    assert first==output.read_bytes()
    data=json.loads(gzip.decompress(first));c=data['metadata']['coverage']
    assert c['queries_captured']==2 and c['queries_planned']==18
    assert c['queries_not_returned']==1 and c['failed_queries']==1 and c['unattempted_queries']==15
    assert c['airports_searched']==2 and c['airports_planned']==4
    assert c['routes_searched']==1 and c['routes_planned']==2
    assert len(data['flights'])==1
    assert {a['code'] for a in data['airports']}=={'CGK','DPS'}


@pytest.mark.parametrize('day',[f'2026-11-{n:02}' for n in range(2,9)])
def test_prepared_week_has_real_flights_and_half_open_days(day):
    payload=get_replay_day(day,'indonesia_flights')
    assert payload['replay_kind']=='flights' and payload['timezone']=='Asia/Jakarta'
    assert payload['end']-payload['start']==86400
    assert datetime.fromtimestamp(payload['start'],ZoneInfo('Asia/Jakarta')).hour==0
    assert payload['services']
    assert len({s['id'] for s in payload['services']})==len(payload['services'])
    for s in payload['services']:
        assert s['stops'][0][1] < payload['end'] and s['stops'][-1][1] >= payload['start']
        assert s['mode']=='flight' and s['carrier'] != 'Unknown'


def test_flight_capability_http_cache_date_limits_and_country_separation(tmp_path,monkeypatch):
    monkeypatch.setenv('SUNTRAIN_REPLAY_CACHE',str(tmp_path))
    app=Flask(__name__);replay_http.register_replay_routes(app);client=app.test_client()
    info=replay_http.descriptor('2026-11-08','indonesia_flights')
    response=client.get(info['url'],headers={'Accept-Encoding':'gzip'})
    assert response.status_code==200
    data=json.loads(gzip.decompress(response.data))
    assert data['city']=='indonesia_flights' and data['loaded_modes']==['flight']
    assert data['schedule']['coverage']
    assert client.get(info['url'],headers={'Accept-Encoding':'gzip','If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(info['url'].replace('2026-11-08','2026-11-09')).status_code==404
    assert client.get(info['url'].replace('modes=flight','modes=train')).status_code==404
    assert flights.reference_path()!=flights.reference_path(city='indonesia_flights')
    assert city_settings('australia_flights')['replay_kind']=='flights'
    assert flights.airline_style('ZZ','Example')==flights.airline_style('ZZ','Example')


def test_midnight_arrivals_are_retained_for_the_new_days_board(tmp_path, monkeypatch):
    start=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Jakarta')).timestamp())
    airports=[a for a in CONFIG['manifest']['airports'] if a['code'] in {'CGK','DPS'}]
    base=dict(number='TEST',carrier='ZZ',airline='Example',origin='CGK',destination='DPS')
    reference=dict(metadata={},airports=airports,flights=[
        dict(base,id='midnight-arrival',departure=start-3600,arrival=start),
        dict(base,id='before-day',departure=start-7200,arrival=start-1),
        dict(base,id='next-day',departure=start+86400,arrival=start+90000)])
    path=tmp_path/'reference.json.gz'
    with gzip.open(path,'wt') as stream:
        json.dump(reference,stream)
    monkeypatch.setenv('SUNTRAIN_INDONESIA_FLIGHTS_REFERENCE',str(path))
    day=flights.replay_day('2026-11-02',city='indonesia_flights')
    assert [s['id'] for s in day['services']]==['midnight-arrival']
    assert day['services'][0]['aircraft']=='Aircraft not specified'


def test_invalid_source_record_does_not_hide_other_valid_flights():
    valid=segment('CGK','DPS',[6,0],[8,0],60,number='1')
    bad=segment('CGK','DPS',[6,0],[23,0],960,number='2')
    rejected=[]
    result=parse_results(scripts(valid,bad,bad),'CGK','DPS','2026-11-02',CONFIG['zones'],rejected)
    assert [f['number'] for f in result]==['QF1']
    assert len(rejected)==1 and rejected[0]['number']=='QF2'
    assert 'Invalid domestic flight duration' in rejected[0]['reason']
    conflict=segment('CGK','DPS',[8,0],[10,0],60,number='1')
    rejected=[]
    assert parse_results(scripts(valid,conflict,valid),'CGK','DPS','2026-11-02',CONFIG['zones'],rejected)==[]
    assert rejected[0]['reason']=='Conflicting duplicate flight'
