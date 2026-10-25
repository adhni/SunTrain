"""India domestic/international scopes, captured USD fares and IST/local boards."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/india_flights/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8868'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"india_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="india_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
    assert 'IST' in page.locator('#replay-clock-date').inner_text()
    count=len(downloads)
    assert page.evaluate('suntrainReplay.day.timezone')=='Asia/Kolkata'
    page.screenshot(path='.cache/india-flights-map.png')
    for code in ['NMI','DXN','GOI','GOX']:
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.stops.some(t=>suntrainReplay.day.stations[t[0]].code===code))',arg=code)
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="DEL"))')
    page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered')
    assert 'IST' in page.locator('#replay-departures').inner_text()
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.airports.length')
    page.locator('#replay-flight-scope').click()
    page.get_by_role('option',name='International',exact=True).click()
    page.wait_for_function('suntrainReplay.filters.flightScope==="international" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.flight_scope==="international")')
    assert len(downloads)==count
    assert page.evaluate('suntrainReplay.day.schedule.fare_context.currency')=='USD'
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="LHR"))')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="LHR" && suntrainReplay.departures.services===suntrainReplay.filtered')
    assert page.evaluate('suntrainReplay.departures.timezone')=='Europe/London'
    assert 'GMT' in page.locator('#replay-departures').inner_text()
    assert 'replay clock uses IST' in page.locator('#replay-departures').inner_text()
    page.locator('[data-event="arrival"]').click()
    page.wait_for_function('suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.departures.calls.length>0')
    assert 'USD' in page.locator('#replay-departures').inner_text()
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="LHR"))')
    page.get_by_role('button',name='Expand board',exact=True).click()
    before=page.evaluate('suntrainReplay.now')
    page.locator('.departure-row').filter(has_text='USD').first.click()
    assert page.evaluate('suntrainReplay.now')==before
    assert 'USD' in page.locator('.replay-flight-fare').inner_text()
    assert '1 adult' in page.locator('#replay-details').inner_text()
    assert 'IST' in page.locator('[data-fare-captured-at]').inner_text()
    page.get_by_role('button',name='Back to airport board',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded')
    page.screenshot(path='.cache/india-flights-london-board.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airport-direction",{value:"departures"});dash_clientside.set_props("replay-airports",{value:["DEL"]});dash_clientside.set_props("replay-carriers",{value:["6E"]})')
    page.wait_for_function('suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="6E" && s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="DEL"))')
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="DEL"))')
    page.locator('[data-event="arrival"]').click()
    page.wait_for_function('suntrainReplay.filters.airportDirection==="arrivals"')
    assert page.evaluate('suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code==="DEL")')
    page.locator('[data-event="destinations"]').click()
    page.wait_for_function('suntrainReplay.departures.destinationRows.length>0')
    page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length')
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    features=page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.end)')
    assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        page.locator('#theme-toggle').select_option(theme)
    page.locator('#theme-toggle').select_option('dark')
    next_page=page.get_by_role('button',name='Next',exact=True)
    if next_page.is_enabled():
        next_page.click()
        assert page.evaluate('suntrainReplay.departures.page')==1
        page.get_by_role('button',name='Previous',exact=True).click()
        assert page.evaluate('suntrainReplay.departures.page')==0
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Tujuan' in page.locator('#replay-departures').inner_text()
    assert 'GMT+5' not in page.locator('#replay-departures').inner_text()
    assert 'IST' in page.locator('#replay-clock-date').inner_text()
    page.evaluate('suntrainReplay.departures.setExpanded(true)')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.locator('.replay-detail-heading:visible').count()==1
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/india-flights-mobile.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-carriers",{value:[]});dash_clientside.set_props("replay-flight-scope",{value:"both"})')
    page.wait_for_function('new Set(suntrainReplay.filtered.map(s=>s.flight_scope)).size===2')
    assert len(downloads)==count
    assert not errors,errors
    print('Domestic default, international/both, USD fares, London local board, fullscreen return, airline/airport filters, arrivals, destinations, frequency, themes and mobile passed',flush=True)
    browser.close()
