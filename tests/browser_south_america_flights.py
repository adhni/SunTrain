"""South American regional map and local time zones, fares, boards and existing replay smoke checks."""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from playwright.sync_api import sync_playwright

AUDIT=Path('.cache/south-america-flights-audit')
AUDIT.mkdir(parents=True,exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8885'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    assert page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places).some(p=>p.id==="south_america_flights" && p.modes.includes("flight"))')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"south_america_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="south_america_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
    assert page.evaluate('suntrainReplay.filters.flightScope')=='both'
    assert page.locator('#replay-flight-scope-field').is_visible()
    assert page.locator('#replay-country-controls').is_visible()
    assert 'UTC' in page.locator('#replay-clock-date').inner_text()
    assert page.evaluate('suntrainReplay.day.stations.length')==27
    assert page.evaluate('suntrainReplay.day.end-suntrainReplay.day.start>=26*3600')
    assert page.evaluate('suntrainReplay.graph.getBounds().contains([-74.15,4.7]) && suntrainReplay.graph.getBounds().contains([-46.47,-23.43])')
    assert page.evaluate('Object.values(suntrainReplay.day.paths).every(p=>p.coordinates.every(c=>c[0]<0))')
    assert page.evaluate('suntrainReplay.graph.getBounds().contains([-70.8,-33.4]) && suntrainReplay.graph.getBounds().contains([-58.4,-34.6])')
    assert page.evaluate('new Date(suntrainReplay.day.start*1000).toISOString()')=='2026-11-02T03:00:00.000Z'
    assert page.evaluate('suntrainReplay.graph.getSource("replay-stations")._data.features.length')==27
    count=len(downloads);total=page.evaluate('suntrainReplay.filtered.length')
    page.screenshot(path=str(AUDIT/'map.png'))
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
    page.wait_for_function('!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length && suntrainReplay.filters.airportDirection==="departures"')
    for scope in ['domestic','international','both']:
        page.evaluate('(scope)=>dash_clientside.set_props("replay-flight-scope",{value:scope})',scope)
        page.wait_for_function('(scope)=>suntrainReplay.filters.flightScope===scope && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>scope==="both" || s.flight_scope===scope)',arg=scope)
        assert page.evaluate('(scope)=>suntrainReplay.filtered.every(s=>scope==="both" || ((suntrainReplay.day.stations[s.stops[0][0]].country)===(suntrainReplay.day.stations[s.stops[1][0]].country))===(scope==="domestic"))',scope)
    for origin,destination in [('BR','BR'),('CO','CO'),('AR','BR'),('CL','PE'),('CO','BR'),('EC','CO'),('BO','BR'),('UY','AR'),('PY','BR'),('VE','CO')]:
        page.evaluate('([a,b])=>{dash_clientside.set_props("replay-from-countries",{value:[a]});dash_clientside.set_props("replay-to-countries",{value:[b]})}',[origin,destination])
        page.wait_for_function('([a,b])=>suntrainReplay.filters.fromCountries[0]===a && suntrainReplay.filters.toCountries[0]===b && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country===a && suntrainReplay.day.stations[s.stops[1][0]].country===b)',arg=[origin,destination])
        assert page.evaluate('suntrainReplay.filtered.some(s=>s.price?.currency==="USD") && suntrainReplay.filtered.every(s=>!s.price || s.price.currency==="USD")')
    manifest=json.loads(Path('data/sources/south_america_flights_routes.json').read_text())
    assert page.evaluate('new Set(suntrainReplay.day.stations.map(a=>a.country)).size')==12
    for country in manifest['country_gateways']:
        expected=page.evaluate('(c)=>suntrainReplay.day.services.filter(s=>suntrainReplay.day.stations[s.stops[0][0]].country===c).length',country)
        page.evaluate('(c)=>{dash_clientside.set_props("replay-from-countries",{value:[c]});dash_clientside.set_props("replay-to-countries",{value:[]})}',country)
        page.wait_for_function('([c,n])=>suntrainReplay.filters.fromCountries[0]===c && !suntrainReplay.filters.toCountries.length && suntrainReplay.filtered.length===n',arg=[country,expected])
    page.evaluate('dash_clientside.set_props("replay-from-countries",{value:[]});dash_clientside.set_props("replay-to-countries",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.fromCountries.length && !suntrainReplay.filters.toCountries.length')
    for carrier in page.evaluate('[...new Set(suntrainReplay.filtered.map(s=>s.carrier))]'):
        page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
        page.wait_for_function('(c)=>suntrainReplay.filters.carriers[0]===c && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.carriers.length')
    airports=json.loads(Path('data/sources/south_america_flights_routes.json').read_text())['airports']
    for airport in airports:
        code,zone=airport['code'],airport.get('replay_timezone',airport['timezone'])
        offset='GMT'+str(int(datetime(2026,11,2,tzinfo=ZoneInfo(zone)).utcoffset().total_seconds()/3600))
        expected=page.evaluate('(code)=>suntrainReplay.day.services.filter(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code).length',code)
        arriving=page.evaluate('(code)=>suntrainReplay.day.services.filter(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code).length',code)
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('([code,n])=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length===n && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=[code,expected])
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('(n)=>suntrainReplay.departures.services===suntrainReplay.filtered && suntrainReplay.departures.calls.length===n',arg=expected)
        if not expected and not arriving:
            assert 'No captured flights for this airport' in page.locator('#replay-departures').inner_text()
            assert page.evaluate('suntrainReplay.departures.catalogue.length')==27
            assert page.evaluate('suntrainReplay.departures.choices.value')==str(page.evaluate('suntrainReplay.departures.station'))
        assert page.evaluate('suntrainReplay.departures.timezone')==zone
        assert offset in page.locator('#replay-departures').inner_text()
        if code=='GRU':
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
            assert 'UTC' in page.locator('#replay-departures').inner_text()
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
            page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(AUDIT/'mobile.png'))
            page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('([code,n])=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length===n && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)',arg=[code,arriving])
        page.locator('[data-event="destinations"]').click();page.wait_for_function('(has)=>Boolean(suntrainReplay.departures.destinationRows.length)===has',arg=bool(expected))
        page.locator('[data-event="departure"]').click();page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
        page.evaluate('suntrainReplay.departures.close()');print(code,'local board passed',flush=True)
    # A carrier/airport combination with no captured service still has a usable board.
    empty=page.evaluate('''()=>{const d=suntrainReplay.day;for(const a of d.stations)for(const c of new Set(d.services.map(s=>s.carrier)))if(!d.services.some(s=>s.carrier===c && d.stations[s.stops[0][0]].code===a.code))return [a.code,c]}''')
    page.evaluate('([a,c])=>{dash_clientside.set_props("replay-airports",{value:[a]});dash_clientside.set_props("replay-carriers",{value:[c]})}',empty)
    page.wait_for_function('([a,c])=>suntrainReplay.filters.airports[0]===a && suntrainReplay.filters.carriers[0]===c && !suntrainReplay.filtered.length',arg=empty)
    page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',empty[0])
    page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered && !suntrainReplay.departures.calls.length')
    assert page.locator('#replay-departures').is_visible()
    assert page.evaluate('(code)=>suntrainReplay.graph.getSource("replay-stations")._data.features.some(f=>f.properties.code===code)',empty[0])
    page.screenshot(path=str(AUDIT/'empty-board.png'))
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-carriers",{value:[]})')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.airports.length && suntrainReplay.frequencyView && suntrainReplay.filtered.length===n && suntrainReplay.frequencyFeatures.length',arg=total)
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainReplay.filtered.length')
    assert len(downloads)==count
    page.screenshot(path=str(AUDIT/'frequency.png'))
    for city in ['united_states_flights','australia_flights','melbourne']:
        page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
        page.wait_for_function('(city)=>suntrainReplay.day.city===city && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
        if city=='united_states_flights':
            assert page.evaluate('suntrainReplay.day.services.length')==9668
        else:assert page.evaluate('suntrainReplay.day.end-suntrainReplay.day.start')==86400
    assert not errors,errors
    print(f'{total} regional records: South America, twenty-seven airports, USD, airline/airport filters, boards, overnight timeline, frequency, themes, Indonesian, mobile and North America/Australia/Melbourne passed',flush=True)
    browser.close()
