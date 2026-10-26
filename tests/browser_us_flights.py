"""Top-twenty US map, six IANA zones, fares, boards and existing replay smoke checks."""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from playwright.sync_api import sync_playwright

AUDIT=Path('.cache/us-flights-audit')
AUDIT.mkdir(parents=True,exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8884'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    assert page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places).some(p=>p.id==="united_states_flights" && p.modes.includes("flight"))')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"united_states_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="united_states_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='America/New_York'
    assert page.evaluate('suntrainReplay.filters.flightScope')=='domestic'
    assert not page.locator('#replay-flight-scope-field').is_visible()
    assert 'EST' in page.locator('#replay-clock-date').inner_text()
    assert page.evaluate('suntrainReplay.day.stations.length')==20
    assert page.evaluate('suntrainReplay.day.end-suntrainReplay.day.start>27*3600')
    assert page.evaluate('suntrainReplay.graph.getBounds().contains([-118.408,33.942]) && suntrainReplay.graph.getBounds().contains([-73.778,40.641])')
    assert page.evaluate('Object.values(suntrainReplay.day.paths).every(p=>p.coordinates.every(c=>c[0]<0))')
    count=len(downloads);total=page.evaluate('suntrainReplay.filtered.length')
    page.screenshot(path=str(AUDIT/'map.png'))
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
    page.wait_for_function('!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length && suntrainReplay.filters.airportDirection==="departures"')
    for carrier in page.evaluate('[...new Set(suntrainReplay.filtered.map(s=>s.carrier))]'):
        page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
        page.wait_for_function('(c)=>suntrainReplay.filters.carriers[0]===c && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.carriers.length')
    airports=json.loads(Path('data/sources/united_states_flights_routes.json').read_text())['airports']
    for airport in airports:
        code,zone=airport['code'],airport['timezone']
        offset='GMT'+str(int(datetime(2026,11,2,tzinfo=ZoneInfo(zone)).utcoffset().total_seconds()/3600))
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered && suntrainReplay.departures.calls.length')
        assert page.evaluate('suntrainReplay.departures.timezone')==zone
        assert offset in page.locator('#replay-departures').inner_text()
        if code=='LAX':
            page.get_by_role('button',name='Expand board',exact=True).click()
            page.get_by_role('button',name='Next',exact=True).click();assert page.evaluate('suntrainReplay.departures.page')==1
            page.get_by_role('button',name='Previous',exact=True).click()
            before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='USD').first.click()
            assert page.evaluate('suntrainReplay.now')==before and 'USD' in page.locator('.replay-flight-fare').inner_text()
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
            page.screenshot(path=str(AUDIT/'board.png'))
            for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
            page.locator('#theme-toggle').select_option('dark')
            page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
            assert 'waktu Timur' in page.locator('#replay-departures').inner_text()
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
            page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(AUDIT/'mobile.png'))
            page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)',arg=code)
        page.locator('[data-event="destinations"]').click();page.wait_for_function('suntrainReplay.departures.destinationRows.length')
        page.locator('[data-event="departure"]').click();page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
        page.evaluate('suntrainReplay.departures.close()');print(code,'local board passed',flush=True)
    page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.airports.length && suntrainReplay.frequencyView && suntrainReplay.filtered.length===n && suntrainReplay.frequencyFeatures.length',arg=total)
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainReplay.filtered.length')
    assert len(downloads)==count
    page.screenshot(path=str(AUDIT/'frequency.png'))
    for city in ['australia_flights','melbourne']:
        page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
        page.wait_for_function('(city)=>suntrainReplay.day.city===city && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
        assert page.evaluate('suntrainReplay.day.end-suntrainReplay.day.start')==86400
    assert not errors,errors
    print(f'{total} US records: top twenty, six IANA zones, USD, airline/airport filters, boards, overnight timeline, frequency, themes, Indonesian, mobile and Australia/Melbourne passed',flush=True)
    browser.close()
