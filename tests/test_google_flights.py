import json
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from scripts.prepare_google_flights import parse_results, ZONES


def test_browser_cleanup_only_overlaps_batches_after_disconnection():
    import asyncio
    from scripts.prepare_google_flights import close_browser,browser_cleanup_tasks
    async def check():
        class Browser:
            def __init__(self,connected):self.connected=connected;self.release=asyncio.Event()
            async def close(self):await self.release.wait()
            def is_connected(self):return self.connected
        closed=Browser(False)
        with pytest.raises(ValueError,match='stop collection'):
            async with browser_cleanup_tasks() as cleanups:
                await close_browser(closed,cleanups,timeout=0.001)
                assert len(cleanups)==1 and not cleanups[0].done()
                closed.release.set()
                raise ValueError('stop collection')
        assert cleanups[0].done()
        live=Browser(True);cleanups=[]
        closing=asyncio.create_task(close_browser(live,cleanups,timeout=0.001))
        await asyncio.sleep(0.01)
        assert not closing.done() and not cleanups
        live.release.set();await closing
    asyncio.run(check())


def segment(origin='MEL', destination='SYD', departure=None, arrival=None, duration=90, carrier='QF', number='400'):
    row = [None] * 33
    row[3], row[6], row[8], row[10], row[11] = origin, destination, departure or [6, None], arrival or [7, 30], duration
    row[17], row[20], row[21], row[22] = 'Boeing 737', [2026, 11, 2], [2026, 11, 2], [carrier, number, None, 'Qantas']
    return row


def scripts(*rows):
    return ["AF_initDataCallback({key: 'ds:1', hash: '5', data:" + json.dumps([rows]) + ', sideChannel:{}});']


def test_exact_airports_keep_mel_and_avv_separate_and_do_not_mix_connecting_segments():
    rows = scripts(segment(), segment('AVV'), segment('MEL', 'BNE', duration=30))
    mel = parse_results(rows, 'MEL', 'SYD', '2026-11-02')
    avv = parse_results(rows, 'AVV', 'SYD', '2026-11-02')
    assert len(mel) == len(avv) == 1
    assert mel[0]['origin'] == 'MEL' and avv[0]['origin'] == 'AVV'
    assert mel[0]['id'] != avv[0]['id']


def test_published_identity_zero_minutes_and_duplicate_search_options():
    row = segment()
    flights = parse_results(scripts(row, row), 'MEL', 'SYD', '2026-11-02')
    assert len(flights) == 1 and flights[0]['number'] == 'QF400'
    assert datetime.fromtimestamp(flights[0]['departure'], ZoneInfo('Australia/Melbourne')).strftime('%H:%M') == '06:00'
    assert not parse_results(scripts(row), 'MEL', 'SYD', '2026-11-03')


def test_half_hour_zone_is_verified_against_published_duration():
    assert ZONES['BHQ'] == 'Australia/Broken_Hill'
    row = segment('BHQ', 'SYD', [10, None], [12, 30], 120)
    assert len(parse_results(scripts(row), 'BHQ', 'SYD', '2026-11-02')) == 1
    row[11] = 150
    with pytest.raises(ValueError, match='duration differs'):
        parse_results(scripts(row), 'BHQ', 'SYD', '2026-11-02')


def test_conflicting_times_are_not_silently_merged():
    row = segment()
    other = segment(departure=[8,None], arrival=[9,30])
    with pytest.raises(ValueError, match='Conflicting'):
        parse_results(scripts(row, other), 'MEL', 'SYD', '2026-11-02')


def test_access_challenge_before_schedule_readiness_stops_remaining_queries(tmp_path,monkeypatch):
    import asyncio
    import sys
    from types import SimpleNamespace
    from scripts.prepare_google_flights import capture
    visits=[]
    class Page:
        url='https://www.google.com/travel/flights'
        async def goto(self,url,**kwargs):
            visits.append(url)
        async def wait_for_function(self,*args,**kwargs):
            raise TimeoutError('No schedule data appeared')
        def locator(self,*args):
            return self
        async def inner_text(self,**kwargs):
            return 'Our systems have detected unusual traffic from your computer network.'
    class Context:
        async def new_page(self):
            return Page()
    class Browser:
        async def close(self):
            pass
        async def new_context(self,**kwargs):
            return Context()
    class Playwright:
        async def __aenter__(self):
            return self
        async def __aexit__(self,*args):
            return False
        @property
        def chromium(self):
            return self
        async def launch(self,**kwargs):
            return Browser()
    monkeypatch.setitem(sys.modules,'playwright.async_api',SimpleNamespace(async_playwright=Playwright))
    with pytest.raises(RuntimeError,match='access limited'):
        asyncio.run(capture(tmp_path,'2026-11-02',[('MEL','SYD'),('MEL','BNE')],1))
    assert len(visits)==1
    assert not list(tmp_path.glob('*.json'))

    visits.clear()
    monkeypatch.setattr('shutil.disk_usage',lambda _:SimpleNamespace(free=0))
    with pytest.raises(RuntimeError,match='Low disk space'):
        asyncio.run(capture(tmp_path,'2026-11-02',[('MEL','SYD')],1))
    assert not visits


def test_collection_lock_prevents_overlapping_browser_workers(tmp_path):
    import asyncio
    import fcntl
    from scripts.prepare_google_flights import capture
    with (tmp_path/'.collection.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(RuntimeError,match='Another collector'):
            asyncio.run(capture(tmp_path,'2026-11-02',[('MEL','SYD')],2))
