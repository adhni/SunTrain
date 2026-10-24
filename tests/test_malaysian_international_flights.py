"""International MYR fares, exact gateways, local dates and shared reference merging."""
from datetime import datetime
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dashboard import flights,replay_http
from scripts.prepare_google_flights import country_config,expected_queries,parse_results,prepare
from scripts.flight_prices import cheapest_prices
from tests.test_google_flights import segment,scripts
from tests.test_flight_prices import offer
from tests.test_indonesian_international_flights import write_reference

CONFIG=country_config('MY','international')


def test_unverified_fare_context_preserves_schedules_without_assigning_prices(tmp_path,monkeypatch):
    import asyncio
    import sys
    from types import SimpleNamespace
    from scripts.prepare_google_flights import capture
    urls=[]
    row=segment('KUL','SIN',[8,0],[9,0],60,carrier='AK',number='701')
    class Page:
        url='https://www.google.com/travel/flights'
        async def goto(self,url,**kwargs):urls.append(url)
        async def wait_for_function(self,*args,**kwargs):pass
        def locator(self,*args):return self
        async def all_text_contents(self):return scripts(offer(row,99))
        async def inner_text(self,**kwargs):return 'Round trip\n1\nEconomy\nCurrencyUSD'
        async def close(self):pass
    class Browser:
        async def close(self):pass
        async def new_context(self,**kwargs):return self
        async def new_page(self):return Page()
    class Playwright:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return False
        @property
        def chromium(self):return self
        async def launch(self,**kwargs):return Browser()
    monkeypatch.setitem(sys.modules,'playwright.async_api',SimpleNamespace(async_playwright=Playwright))
    asyncio.run(capture(tmp_path,'2026-11-02',[('KUL','SIN')],2,CONFIG))
    q=json.loads((tmp_path/'2026-11-02-KUL-SIN.json').read_text())
    assert len(q['flights'])==1 and 'price' not in q['flights'][0]
    assert q['status']=='results' and 'Unverified' in q['price_error']
    assert all('curr=MYR' in url and 'one+adult+economy' in url for url in urls)
    assert not list(tmp_path.glob('*.error.json'))


def test_manifest_targets_gateways_with_separate_airports_and_both_directions():
    m=CONFIG['manifest'];airports={a['code']:a for a in m['airports']}
    local={c for c,a in airports.items() if a['country']=='MY'}
    assert local==set('KUL SZB PEN BKI JHB KCH LGK TWU KBR IPH KUA MKZ MYY SBW'.split())
    assert not {'BBN','BKM','LBP','LKH','LGL'} & local
    assert ['MKZ','SIN'] in m['routes'] and ['IPH','SIN'] in m['routes']
    assert ['KUL','LHR'] in m['routes'] and ['SZB','XSP'] in m['routes']
    for a,b in m['routes']:
        assert (airports[a]['country']=='MY') != (airports[b]['country']=='MY')
        assert [b,a] in m['routes']
    assert airports['KUL']['lon']!=airports['SZB']['lon']
    assert airports['BKI']['timezone']=='Asia/Kuching'
    assert airports['MKZ']['island_group']=='Peninsular Malaysia'
    assert all(ZoneInfo(a['timezone']) for a in airports.values())
    assert CONFIG['capture_prices'] and CONFIG['currency']=='MYR'
    assert not m['unresolved_airports']


def test_query_dates_cover_foreign_carry_ins_and_next_day_eastern_airports():
    pairs=[('LHR','KUL'),('KUL','LHR'),('AKL','KUL'),('KUL','AKL')]
    queries=set(expected_queries('2026-11-02',pairs,CONFIG))
    start=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Kuala_Lumpur')).timestamp())
    for a,b in pairs:
        for at in range(start-86400,start+86400,900):
            local=datetime.fromtimestamp(at,ZoneInfo(CONFIG['zones'][a])).date().isoformat()
            assert (local,a,b) in queries
    assert ('2026-10-31','LHR','KUL') in queries
    assert ('2026-11-03','AKL','KUL') in queries
    assert ('2026-11-04','AKL','KUL') not in queries


def test_long_haul_local_dates_fares_and_cached_preparation(tmp_path):
    row=segment('LHR','KUL',[22,0],[19,0],780,carrier='MH',number='1');row[20]=[2026,11,1]
    f=parse_results(scripts(row),'LHR','KUL','2026-11-01',CONFIG['zones'],max_duration=86400)[0]
    f['price']={**cheapest_prices(scripts(offer(row,2500),offer(row,2400)),[f],'MYR')[f['id']],'captured_at':'2026-10-25T00:00:00+00:00'}
    assert f['price']['amount_minor']==240000
    cache=tmp_path/'cache';cache.mkdir()
    (cache/'2026-11-01-LHR-KUL.json').write_text(json.dumps(dict(origin='LHR',destination='KUL',date='2026-11-01',flights=[f],status='results',captured_at='2026-10-25T00:00:00+00:00')))
    out=tmp_path/'reference.gz';prepare(cache,out,'2026-11-02',[('LHR','KUL')],CONFIG);first=out.read_bytes()
    prepare(cache,out,'2026-11-02',[('LHR','KUL')],CONFIG);assert out.read_bytes()==first
    reference=json.loads(gzip.decompress(first));meta=reference['metadata']
    assert reference['flights']==[f]
    assert meta['scope']=='international' and meta['country']=='MY' and meta['priced_flights']==1
    assert meta['coverage']['failed_or_missing_queries']==2
    assert 'MYT' in meta['replay_note'] and 'airport boards use local time' in meta['replay_note']
    with pytest.raises(ValueError,match='exactly one'):
        prepare(cache,out,'2026-11-02',[('KUL','PEN')],CONFIG)


def test_fare_preserving_scope_merge_fixture_isolation_and_http_revision(tmp_path,monkeypatch):
    airports={a['code']:a for a in CONFIG['manifest']['airports']}
    domestic_airports={a['code']:a for a in country_config('MY')['manifest']['airports']}
    start=int(datetime(2026,11,2,tzinfo=ZoneInfo('Asia/Kuala_Lumpur')).timestamp())
    price=dict(amount_minor=13400,currency='MYR',adults=1,cabin='economy',trip_type='one_way',captured_at='2026-10-25T00:00:00+00:00')
    context=dict(currency='MYR',adults=1,cabin='economy',trip_type='one_way')
    base=dict(carrier='MH',number='MH1',airline='Malaysia Airlines',origin='KUL',departure=start+3600,arrival=start+7200,price=price)
    domestic=tmp_path/'domestic.gz';international=tmp_path/'international.gz'
    write_reference(domestic,[airports['KUL'],domestic_airports['PEN']],[dict(base,id='domestic',destination='PEN')],{'fare_context':context,'priced_flights':1})
    write_reference(international,[airports['KUL'],airports['LHR']],[dict(base,id='international',destination='LHR',arrival=start+14*3600)],{'scope':'international','fare_context':context,'priced_flights':1})
    monkeypatch.setenv('SUNTRAIN_MALAYSIA_FLIGHTS_REFERENCE',str(domestic))
    assert len(flights.reference_paths('2026-11-02','malaysia_flights'))==1
    monkeypatch.setenv('SUNTRAIN_MALAYSIA_INTERNATIONAL_REFERENCE',str(international))
    payload=flights.replay_day('2026-11-02','malaysia_flights')
    assert {s['flight_scope'] for s in payload['services']}=={'domestic','international'}
    assert all(s['price']==price for s in payload['services'])
    assert payload['schedule']['fare_context']==context and payload['schedule']['priced_flights']==2
    assert payload['schedule']['priced_flights_by_scope']=={'domestic':1,'international':1}
    assert 'MYT' in payload['schedule']['replay_note'] and 'Melbourne time' not in payload['schedule']['replay_note']
    old=replay_http.descriptor('2026-11-02','malaysia_flights')['revision']
    write_reference(international,[airports['KUL'],airports['LHR']],[],{'scope':'international'})
    assert replay_http.descriptor('2026-11-02','malaysia_flights')['revision']!=old
    write_reference(international,[airports['KUL'],domestic_airports['PEN']],[dict(base,id='wrong',destination='PEN')],{'scope':'international'})
    with pytest.raises(ValueError,match='domestic flight'):
        flights.replay_day('2026-11-02','malaysia_flights')


def test_captured_supplement_preserves_prices_national_endpoints_and_day_windows():
    root=Path(__file__).resolve().parents[1]
    reference=json.loads(gzip.decompress((root/'data/reference/malaysia_flights/2026-11-02-international.json.gz').read_bytes()))
    meta=reference['metadata'];records=reference['flights']
    assert meta['scope']=='international' and meta['country']=='MY'
    assert meta['priced_flights']==sum('price' in f for f in records)>0
    for f in records:
        if 'price' in f:
            p=f['price'];assert p['currency']=='MYR' and type(p['amount_minor']) is int and p['amount_minor']>0
    payload=flights.replay_day('2026-11-02','malaysia_flights')
    assert payload['flight_scopes'] and payload['end']-payload['start']==86400
    assert len({s['id'] for s in payload['services']})==len(payload['services'])
    assert payload['schedule']['priced_flights']==sum('price' in s for s in payload['services'])
    for s in payload['services']:
        if s['flight_scope']=='international':
            a,b=[payload['stations'][stop[0]] for stop in s['stops']]
            assert (a['country']=='MY') != (b['country']=='MY')
            assert s['stops'][0][2]<payload['end'] and s['stops'][1][1]>=payload['start']
