"""Targeted search coverage, Pacific clocks, source isolation and international replay."""
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

import pytest
from dashboard import flights,replay_http
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from tests.test_google_flights import segment,scripts
from tests.test_indonesian_international_flights import write_reference

CONFIG=country_config('AU','international')


def test_targeted_manifest_has_exact_gateway_and_foreign_airports():
    m=CONFIG['manifest'];airports={a['code']:a for a in m['airports']}
    local={c for c,a in airports.items() if a['country']=='AU'}
    assert local==set('ADL AVV BNE CBR CNS DRW HBA MCY MEL NTL OOL PER SYD WSI'.split())
    assert not {'ABX','DBO','MQL','WGA','BME'} & local
    assert len(m['routes'])==402
    for a,b in m['routes']:
        assert (airports[a]['country']=='AU') != (airports[b]['country']=='AU')
        assert [b,a] in m['routes']
    assert ['AVV','DPS'] in m['routes'] and ['WSI','AKL'] in m['routes']
    assert ['NTL','SIN'] not in m['routes'] and ['MCY','SIN'] not in m['routes']
    assert ['WSI','SIN'] not in m['routes'] and ['ADL','SFO'] not in m['routes']
    assert ['PER','CDG'] in m['routes'] and ['CDG','PER'] in m['routes']
    assert ['ADL','HKG'] not in m['routes'] and ['MEL','ICN'] not in m['routes']
    assert airports['MEL']['lon']!=airports['AVV']['lon']
    assert airports['SYD']['lon']!=airports['WSI']['lon']
    assert not m['unresolved_airports']
    assert all(ZoneInfo(a['timezone']) for a in airports.values())
    assert airports['ADL']['timezone']=='Australia/Adelaide'
    assert airports['DFW']['timezone']=='America/Chicago'
    assert airports['RAR']['timezone']=='Pacific/Rarotonga'
    assert country_config()['manifest'] is None  # Preserve existing AU CLI defaults.


def test_queries_cover_dateline_carry_ins_and_next_day_new_zealand():
    pairs=[('LAX','SYD'),('SYD','LAX'),('AKL','SYD'),('LHR','PER')]
    queries=set(expected_queries('2026-11-02',pairs,CONFIG))
    start=int(datetime(2026,11,2,tzinfo=ZoneInfo('Australia/Melbourne')).timestamp())
    for a,b in pairs:
        for at in range(start-86400,start+86400,900):
            local=datetime.fromtimestamp(at,ZoneInfo(CONFIG['zones'][a])).date().isoformat()
            assert (local,a,b) in queries
    assert ('2026-10-31','LAX','SYD') in queries
    assert ('2026-11-03','AKL','SYD') in queries
    assert ('2026-11-04','AKL','SYD') not in queries


def test_pacific_flights_preserve_reversed_local_dates_and_us_dst():
    # Sydney to LA arrives on the same local calendar day, but earlier by the clock.
    row=segment('SYD','LAX',[11,0],[5,0],780)
    f=parse_results(scripts(row,row),'SYD','LAX','2026-11-02',CONFIG['zones'],max_duration=86400)[0]
    assert f['arrival']-f['departure']==13*3600
    row=segment('SYD','RAR',[9,0],[18,0],360);row[21]=[2026,11,1]
    f=parse_results(scripts(row),'SYD','RAR','2026-11-02',CONFIG['zones'],max_duration=86400)[0]
    assert f['arrival']>f['departure']
    assert datetime.fromtimestamp(f['arrival'],ZoneInfo('Pacific/Rarotonga')).date().isoformat()=='2026-11-01'
    # Return crosses the date line; November 1 ends daylight saving in California.
    row=segment('LAX','SYD',[22,0],[8,0],900);row[20]=[2026,11,1];row[21]=[2026,11,3]
    f=parse_results(scripts(row),'LAX','SYD','2026-11-01',CONFIG['zones'],max_duration=86400)[0]
    assert f['arrival']-f['departure']==15*3600
    row[11]=901+2
    with pytest.raises(ValueError,match='duration differs'):
        parse_results(scripts(row),'LAX','SYD','2026-11-01',CONFIG['zones'],max_duration=86400)


@pytest.mark.parametrize('a,b',[([151.177,-33.95],[-118.408,33.94]),([151.177,-33.95],[-70.79,-33.39]),([115.97,-31.94],[-0.45,51.47])])
def test_illustrative_arcs_stay_continuous_across_the_dateline(a,b):
    forward=flights.continuous_arc(a,b);reverse=flights.continuous_arc(b,a)
    assert all(abs(q[0]-p[0])<180 for p,q in zip(forward,forward[1:]))
    assert forward==list(reversed(reverse))
    assert (forward[-1][0]-b[0])%360==pytest.approx(0)
    assert forward[-1][1]==b[1]


def test_merged_australian_reference_and_http_revision_respect_custom_fixtures(tmp_path,monkeypatch):
    airports={a['code']:a for a in CONFIG['manifest']['airports']}
    start=int(datetime(2026,11,2,tzinfo=ZoneInfo('Australia/Melbourne')).timestamp())
    base=dict(carrier='QF',number='QF1',airline='Qantas',origin='SYD',departure=start,arrival=start+3600)
    domestic=tmp_path/'domestic.gz';international=tmp_path/'international.gz'
    write_reference(domestic,[airports['SYD'],airports['MEL']],[dict(base,id='domestic',destination='MEL')])
    write_reference(international,[airports['SYD'],airports['LAX']],[dict(base,id='international',destination='LAX',arrival=start+13*3600)],{'scope':'international'})
    monkeypatch.setenv('SUNTRAIN_AUSTRALIA_FLIGHTS_REFERENCE',str(domestic))
    assert len(flights.reference_paths('2026-11-02'))==1
    assert {s['flight_scope'] for s in flights.replay_day('2026-11-02')['services']}=={'domestic'}
    monkeypatch.setenv('SUNTRAIN_AUSTRALIA_INTERNATIONAL_REFERENCE',str(international))
    payload=flights.replay_day('2026-11-02')
    assert {s['flight_scope'] for s in payload['services']}=={'domestic','international'}
    assert len(flights.reference_paths('2013-03-04'))==1
    old=replay_http.descriptor('2026-11-02','australia_flights')['revision']
    write_reference(international,[airports['SYD'],airports['LAX']],[],{'scope':'international'})
    assert replay_http.descriptor('2026-11-02','australia_flights')['revision']!=old
    write_reference(international,[airports['LAX'],airports['LHR']],[dict(base,id='wrong',origin='LAX',destination='LHR')],{'scope':'international'})
    with pytest.raises(ValueError,match='endpoint'):flights.replay_day('2026-11-02')
    write_reference(international,[airports['SYD'],airports['MEL']],[dict(base,id='wrong',destination='MEL')],{'scope':'international'})
    with pytest.raises(ValueError,match='domestic flight'):flights.replay_day('2026-11-02')


def test_australian_international_preparation_is_deterministic_and_reports_missing_queries(tmp_path):
    cache=tmp_path/'cache';cache.mkdir()
    row=segment('SYD','LAX',[11,0],[5,0],780)
    f=parse_results(scripts(row),'SYD','LAX','2026-11-02',CONFIG['zones'],max_duration=86400)[0]
    (cache/'2026-11-02-SYD-LAX.json').write_text(json.dumps(dict(origin='SYD',destination='LAX',date='2026-11-02',flights=[f],status='results',captured_at='2026-10-25T00:00:00+00:00')))
    output=tmp_path/'reference.gz'
    prepare(cache,output,'2026-11-02',[('SYD','LAX')],CONFIG)
    first=output.read_bytes();prepare(cache,output,'2026-11-02',[('SYD','LAX')],CONFIG)
    assert output.read_bytes()==first
    metadata=json.loads(gzip.decompress(first))['metadata']
    assert metadata['country']=='AU' and metadata['scope']=='international'
    assert metadata['coverage']['failed_or_missing_queries']>0
    assert 'Melbourne time' in metadata['replay_note'] and 'WIB' not in metadata['replay_note']
    with pytest.raises(ValueError,match='exactly one'):
        prepare(cache,output,'2026-11-02',[('SYD','MEL')],CONFIG)


def test_prepared_australian_supplement_has_real_international_endpoints_and_continuous_paths():
    payload=flights.replay_day('2026-11-02')
    services=[s for s in payload['services'] if s['flight_scope']=='international']
    assert services and payload['flight_scopes']
    assert payload['end']-payload['start']==86400
    assert len({s['id'] for s in payload['services']})==len(payload['services'])
    assert payload['schedule']['coverage_by_scope']['international']['routes_planned']==402
    for s in services:
        a,b=[payload['stations'][stop[0]] for stop in s['stops']]
        assert (a['country']=='AU') != (b['country']=='AU')
        assert s['stops'][0][2]<payload['end'] and s['stops'][1][1]>=payload['start']
        assert 60<=s['stops'][1][1]-s['stops'][0][2]<=86400
        assert a['code']+'-'+b['code']==s['route_id']
        assert ZoneInfo(a['timezone']) and ZoneInfo(b['timezone'])
        points=payload['paths'][s['legs'][0]]['coordinates']
        assert all(abs(q[0]-p[0])<180 for p,q in zip(points,points[1:]))
