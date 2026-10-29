"""International cache ownership, quote preservation and durable search limits."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from urllib.parse import urlencode

import pytest

from dashboard import international_expansion as adapter, world_flights as world
from scripts import discover_international_expansion as discovery
from scripts import prepare_international_expansion as preparation


AIRPORTS = {
    'AAA': dict(code='AAA', country='AU', icao='YAAA', timezone='UTC', lat=-30, lon=145, mode='flight', name='AAA'),
    'BBB': dict(code='BBB', country='ID', icao='WBBB', timezone='Asia/Jakarta', lat=-6, lon=106, mode='flight', name='BBB'),
}
KEY = (world.DAY, 'AAA', 'BBB')


class Airports:
    def __init__(self, baseline=None):
        self.known = deepcopy(AIRPORTS)
        self.unresolved = {}

    def get(self, code):
        return self.known.get(code)

    def country(self,code):
        return self.known.get(code,{}).get('country')

    def possibly_international(self,a,b):
        return adapter.is_international(self.get(a),self.get(b))


def flight(**extra):
    return {**dict(id='2026-11-02:ZZ1:AAA:BBB', carrier='ZZ', number='ZZ1', airline='Example',
                   origin='AAA', destination='BBB', source_date=world.DAY,
                   departure=world.START+3600, arrival=world.START+7200,
                   aircraft='Aircraft not specified', flight_scope='international'), **extra}


def quote(currency='USD', amount=10000):
    return dict(currency=currency, amount_minor=amount, adults=1, cabin='economy', trip_type='one_way')


def query(records=None, captured='2026-10-29T12:00:00+00:00', currency='USD', **extra):
    records = [flight()] if records is None else records
    return {**dict(date=KEY[0], origin=KEY[1], destination=KEY[2], captured_at=captured,
                   url='https://www.google.com/travel/flights?' + urlencode(dict(
                       q=f'Flights from AAA to BBB on {world.DAY} one way nonstop one adult economy', curr=currency)),
                   flights=records, status='results' if records else 'no_matching_direct_flights',
                   capture_context=dict(max_duration=86400, airline_filter='none')), **extra}


def setup_prepare(tmp_path, monkeypatch, sources, authority=0):
    cache = tmp_path / 'cache'
    base = dict(airports=list(AIRPORTS.values()), flights=[flight()], metadata=dict(inputs={}))
    discovery.save(cache/'baseline.json.gz', base)
    refs = []
    for index, source in enumerate(sources):
        path = tmp_path / f'capture-{index}.json'
        discovery.save(path, source)
        refs.append(dict(path=str(path), sha256=discovery.digest(path.read_bytes()),
                         captured_at=source['captured_at'], status=source['status'], flights=len(source['flights'])))
    discovery.save(cache/'cache-index.json.gz', dict(queries=[dict(query=list(KEY), sources=refs, latest=refs[-1])]))
    monkeypatch.setattr(preparation, 'Airports', Airports)
    monkeypatch.setattr(preparation, 'SOURCE', tmp_path/'no-manifest')
    monkeypatch.setattr(preparation, 'baseline_query_times', lambda _: dict(
        times={'|'.join(KEY): authority}, protected_official_ids=[]))
    return cache, base


def test_capture_validation_exact_airports_local_dates_and_partial_rejection():
    assert discovery.validate_query(query(), KEY, Airports())['flights']
    for change, error in [
        ({'origin': 'MEL'}, 'query identity'),
        ({'captured_at': '2026-10-29'}, 'timezone'),
        ({'rejected_flights': [{'reason': 'bad clock'}]}, 'partially rejected'),
        ({'flights': [], 'status': 'results'}, 'status'),
        ({'capture_context': {'airline_filter': 'ZZ'}}, 'Airline-limited'),
        ({'flights': [flight(departure=world.START-3600)]}, 'departure date'),
        ({'flights': [flight(arrival=world.START+3601)]}, 'duration'),
    ]:
        with pytest.raises(ValueError, match=error):
            discovery.validate_query(query(**change), KEY, Airports())
    with pytest.raises(ValueError, match='short-parser'):
        discovery.validate_query(query([], capture_context={'max_duration': 28800}), KEY, Airports())
    assert discovery.validate_query(query([]), KEY, Airports())['status'] == 'no_matching_direct_flights'
    assert discovery.validate_query(query([], capture_context=None), KEY, Airports(), legacy_duration=86400)['status'] == 'no_matching_direct_flights'


def test_existing_puerto_rico_jurisdiction_is_preserved():
    assert not adapter.is_international({'country': 'PR'}, {'country': 'US'})
    assert not adapter.is_international({'country': 'US'}, {'country': 'PR'})
    assert adapter.is_international({'country': 'PR'}, {'country': 'CA'})
    assert adapter.is_international({'country': 'HK'}, {'country': 'CN'})


@pytest.mark.parametrize('zone,day,departure', [
    ('America/Los_Angeles', '2026-11-01', world.START+1800),
    ('Pacific/Apia', '2026-11-03', world.START+18*3600),
])
def test_adjacent_local_dates_can_depart_inside_the_same_utc_day(zone,day,departure):
    airports = Airports()
    airports.known['AAA']['timezone'] = zone
    key = (day, 'AAA', 'BBB')
    q = query([flight(source_date=day, departure=departure, arrival=departure+3600)])
    q.update(date=day, url=q['url'].replace(world.DAY, day))
    assert discovery.validate_query(q, key, airports)['flights'][0]['departure'] == departure


def test_dated_canadian_offset_is_used_in_cache_validation():
    airports = Airports()
    airports.known['AAA'].update(country='CA', timezone='America/Vancouver', replay_timezone='Etc/GMT+7')
    # The preserved November replay zone is one hour ahead of the old IANA rule.
    departure = world.START+7*3600+1800
    q = query([flight(departure=departure, arrival=departure+3600)])
    assert discovery.validate_query(q, KEY, airports)['flights']
    wrong = query([flight(departure=departure-3600, arrival=departure)])
    with pytest.raises(ValueError, match='departure date'):
        discovery.validate_query(wrong, KEY, airports)


def test_latest_successful_empty_owns_query_and_cannot_resurrect_older_positive(tmp_path, monkeypatch):
    cache, base = setup_prepare(tmp_path, monkeypatch, [query(), query([], captured='2026-10-30T12:00:00Z')])
    result = preparation.prepare(cache, tmp_path/'extra.gz')
    assert not result['flights']
    assert result['metadata']['queries'][0]['status'] == 'no_matching_direct_flights'
    assert not adapter.overlay(base, result)['flights']
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE', str(tmp_path/'extra.gz'))
    assert adapter.load_reference() == result


def test_older_cache_cannot_revive_a_validated_adapter_exclusion(tmp_path, monkeypatch):
    cache, base = setup_prepare(tmp_path, monkeypatch, [query()],
        discovery.timestamp('2026-10-30T00:00:00Z'))
    result = preparation.prepare(cache, tmp_path/'extra.gz')
    assert not result['flights'] and not result['metadata']['queries']
    assert result['metadata']['recovery']['superseded_by_validated_adapter'] == 1
    assert adapter.overlay(base, result)['flights'] == base['flights']


def test_quotes_and_aircraft_from_exact_matching_schedules_are_preserved(tmp_path, monkeypatch):
    sources = [query([flight(price=quote('EUR', 5000), aircraft='A320')], currency='EUR'),
               query([flight(price=quote('USD', 20000), aircraft='B737')], captured='2026-10-30T09:00:00Z'),
               query([flight(price=quote('USD', 15000))], captured='2026-10-30T10:00:00Z')]
    cache, _ = setup_prepare(tmp_path, monkeypatch, sources)
    result = preparation.prepare(cache, tmp_path/'extra.gz')
    assert result['flights'][0]['price'] == quote('USD', 15000)
    assert len(result['flights'][0]['fare_quotes']) == 3
    reference = (adapter.PROFILE, result, (world.START, world.END))
    merged = world.merge_views([reference])['flights'][0]
    assert len(merged['fare_quotes']) == 3
    assert merged['price']['amount_minor'] == 15000
    assert {v['aircraft'] for v in merged['aircraft_variants']} == {'A320', 'B737'}
    assert 'Aircraft differs between captures' not in {v['aircraft'] for v in merged['aircraft_variants']}


def test_explicit_replacement_precedes_identity_conflict_and_does_not_transfer_old_fare(tmp_path, monkeypatch):
    latest = query([flight(departure=world.START+4200, arrival=world.START+7800)], captured='2026-10-30T00:00:00Z')
    cache, base = setup_prepare(tmp_path, monkeypatch, [query([flight(price=quote())]), latest])
    result = preparation.prepare(cache, tmp_path/'extra.gz')
    assert 'price' not in result['flights'][0]
    assert not adapter.overlay(base, result)['flights']
    combined = world.merge_views([('old', adapter.overlay(base, result), (world.START, world.END)),
                                  (adapter.PROFILE, result, (world.START, world.END))])
    assert len(combined['flights']) == 1 and combined['flights'][0]['departure'] == world.START+4200


def test_matching_baseline_quotes_remain_independent_evidence_and_official_absences_survive(tmp_path, monkeypatch):
    cache, base = setup_prepare(tmp_path, monkeypatch, [query([flight(price=quote())])])
    result = preparation.prepare(cache, tmp_path/'extra.gz')
    protected = flight(id='official', number='FR1', schedule_source='ryanair_public_timetable')
    base['flights'].append(protected)
    before = deepcopy(base)
    overlaid = adapter.overlay(base, result)
    assert base == before and len(overlaid['flights']) == 2
    assert world.identity(overlaid['flights'][0]) == world.identity(result['flights'][0])


def test_modified_raw_capture_fails_offline_preparation(tmp_path, monkeypatch):
    cache, _ = setup_prepare(tmp_path, monkeypatch, [query()])
    (tmp_path/'capture-0.json').write_text('{}')
    with pytest.raises(ValueError, match='changed after indexing'):
        preparation.prepare(cache, tmp_path/'extra.gz')


def test_durable_budget_counts_failed_and_crashed_attempts_and_rejects_reset(tmp_path):
    keys = [KEY, (world.DAY, 'BBB', 'AAA'), ('2026-11-01', 'AAA', 'BBB')]
    path = tmp_path/'attempts.json'
    budget = preparation.AttemptBudget(path, keys, limit=2)
    budget.start(keys[0])  # Simulate navigation failure, with no capture saved.
    resumed = preparation.AttemptBudget(path, keys, limit=2)
    assert resumed.used == {KEY}
    with pytest.raises(RuntimeError, match='already attempted'):
        resumed.start(KEY)
    with pytest.raises(RuntimeError, match='outside'):
        resumed.start((world.DAY, 'AAA', 'CCC'))
    resumed.start(keys[1])
    with pytest.raises(RuntimeError, match='limit reached'):
        resumed.start(keys[2])
    assert len(json.loads(path.read_text())['attempts']) == 2
    with pytest.raises(ValueError, match='manifest changed'):
        preparation.AttemptBudget(path, keys[:1], limit=2)
    with pytest.raises(ValueError, match='1,000'):
        preparation.AttemptBudget(path, keys, limit=1001)
    revised = preparation.AttemptBudget(path, keys + [('2026-11-03', 'BBB', 'AAA')], limit=2)
    assert len(revised.state['attempts']) == 2
    with pytest.raises(RuntimeError, match='limit reached'):
        revised.start(('2026-11-03', 'BBB', 'AAA'))


@pytest.mark.parametrize('stale_local',[False,True])
def test_published_attempt_journal_prevents_recollection_after_local_cache_loss(tmp_path,monkeypatch,stale_local):
    source=tmp_path/'published.json.gz'
    cache=tmp_path/'audit'
    captures=tmp_path/'captures'
    discovery.save(source,dict(new_searches=[list(KEY)],search_limit=1,
        airports=list(AIRPORTS.values()),collection=dict(attempts=[dict(query=list(KEY),attempted_at='2026-10-30T00:00:00Z')])))
    discovery.save(cache/'cache-index.json.gz',dict(queries=[]))
    monkeypatch.setattr(preparation,'SOURCE',source)
    monkeypatch.setattr(preparation,'CAPTURES',captures)
    if stale_local:
        discovery.save(captures/'attempts.json',dict(queries_sha256='',attempts=[]))
    async def forbidden(*args,**kwargs):
        raise AssertionError('A completed published campaign must not navigate again')
    monkeypatch.setattr(preparation,'capture',forbidden)
    assert preparation.collect(cache)==0
    assert len(discovery.read(captures/'attempts.json')['attempts'])==1


def test_rebuilding_manifest_keeps_published_journal_without_local_cache(tmp_path,monkeypatch):
    cache=tmp_path/'audit';source=tmp_path/'published.json.gz'
    attempt=dict(query=list(KEY),attempted_at='2026-10-30T00:00:00Z')
    collection=dict(attempts=[attempt],searches_attempted=1)
    discovery.save(source,dict(collection=collection))
    discovery.save(cache/'baseline.json.gz',dict(airports=list(AIRPORTS.values()),flights=[flight()],metadata=dict(inputs={})))
    discovery.save(cache/'cache-index.json.gz',dict(queries=[],invalid_reasons={}))
    discovery.save(cache/'discovery.json',dict(maps=[],gaps=[]))
    monkeypatch.setattr(discovery,'ROOT',tmp_path)
    monkeypatch.setattr(discovery,'Airports',Airports)
    result=discovery.build_manifest(cache,source)
    assert result['new_searches']==[list(KEY)]
    assert result['collection']==collection


def test_missing_published_capture_cannot_erase_prepared_records(tmp_path,monkeypatch):
    cache,_=setup_prepare(tmp_path,monkeypatch,[query([flight(price=quote())])])
    path=tmp_path/'prepared.gz'
    preparation.prepare(cache,path)
    before=path.read_bytes()
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE',str(path))
    discovery.save(preparation.SOURCE,dict(collection=dict(searches_attempted=1)))
    (tmp_path/'capture-0.json').unlink()
    with pytest.raises(ValueError,match='Published raw capture missing'):
        preparation.prepare(cache,path)
    assert path.read_bytes()==before


def test_followup_manifest_survives_published_raw_capture_validation(tmp_path,monkeypatch):
    cache,_=setup_prepare(tmp_path,monkeypatch,[query([flight(price=quote())])])
    path=tmp_path/'prepared.gz'
    preparation.prepare(cache,path)
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE',str(path))
    source=tmp_path/'followup.json.gz'
    discovery.save(source,dict(collection=dict(searches_attempted=1),unresolved_airports={}))
    result=preparation.prepare(cache,path,source=source)
    assert result['flights'][0]['price']==quote()
    assert result['metadata']['source_manifest']==dict(
        path=str(source),sha256=discovery.digest(source.read_bytes()))


def test_merged_journals_keep_newer_local_attempts_and_reject_conflicts(tmp_path):
    first=dict(query=list(KEY),attempted_at='2026-10-30T00:00:00Z')
    second=dict(query=[world.DAY,'BBB','AAA'],attempted_at='2026-10-30T00:01:00Z')
    manifest=dict(collection=dict(attempts=[first]))
    path=tmp_path/'attempts.json'
    discovery.save(path,dict(attempts=[first,second]))
    assert discovery.merged_attempts(manifest,path)==[first,second]
    discovery.save(path,dict(attempts=[{**first,'attempted_at':'2026-10-30T00:02:00Z'}]))
    with pytest.raises(ValueError,match='Conflicting'):
        discovery.merged_attempts(manifest,path)


def test_supplement_rejects_domestic_flights_wrong_context_and_source_changes(tmp_path, monkeypatch):
    cache, _ = setup_prepare(tmp_path, monkeypatch, [query([flight(price=quote())])])
    path = tmp_path/'extra.gz'
    result = preparation.prepare(cache, path)
    monkeypatch.setenv('SUNTRAIN_WORLD_INTERNATIONAL_REFERENCE', str(path))
    assert adapter.load_reference() == result
    result['airports'][1]['country'] = 'AU'
    discovery.save(path, result)
    with pytest.raises(ValueError, match='international flight'):
        adapter.load_reference()
    with pytest.raises(ValueError, match='sources changed'):
        adapter.validate_inputs({'metadata': {'baseline_inputs': {'missing': {'sha256': 'abc'}}}}, {})
