"""Philippine scopes, separate MNL/CRK, local boards and shared UTC filters."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8876'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"philippines_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="philippines_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.filters.flightScope')=='both'
    page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"domestic"})')
    page.wait_for_function('suntrainReplay.filters.flightScope==="domestic"')
    assert page.locator('#replay-flight-scope-field').is_visible()
    assert page.evaluate('suntrainReplay.day.timezone')=='Asia/Manila'
    assert 'PHT' in page.locator('#replay-clock-date').inner_text()
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
    assert page.evaluate('suntrainReplay.graph.getBounds().getNorth()-suntrainReplay.graph.getBounds().getSouth()<40')
    assert page.evaluate('suntrainReplay.day.stations.some(a=>a.code==="MNL") && suntrainReplay.day.stations.some(a=>a.code==="CRK")')
    count=len(downloads);domestic=page.evaluate('suntrainReplay.filtered.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
    page.wait_for_function('!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length && suntrainReplay.filters.airportDirection==="departures"')
    page.screenshot(path='.cache/philippines-flights-audit/domestic-map.png')
    for code in ['MNL','CRK','CEB','DVO','ILO','TAG','USU','PPS']:
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered && suntrainReplay.departures.calls.length')
        assert page.evaluate('suntrainReplay.departures.timezone')=='Asia/Manila'
        assert 'PHT' in page.locator('#replay-departures').inner_text()
        if code=='MNL':
            carrier=page.evaluate('suntrainReplay.filtered[0].carrier')
            page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
            page.wait_for_function('(c)=>suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
            page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
            page.wait_for_function('!suntrainReplay.filters.carriers.length')
            page.get_by_role('button',name='Expand board',exact=True).click()
            page.get_by_role('button',name='Next',exact=True).click();assert page.evaluate('suntrainReplay.departures.page')==1
            page.get_by_role('button',name='Previous',exact=True).click()
            before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='USD').first.click()
            assert page.evaluate('suntrainReplay.now')==before and 'USD' in page.locator('.replay-flight-fare').inner_text()
            assert 'PHT' in page.locator('[data-fare-captured-at]').inner_text()
            page.get_by_role('button',name='Back to airport board',exact=True).click();assert page.evaluate('suntrainReplay.departures.expanded')
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)',arg=code)
        page.locator('[data-event="destinations"]').click();page.wait_for_function('suntrainReplay.departures.destinationRows.length')
        page.locator('[data-event="departure"]').click();page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
        page.evaluate('suntrainReplay.departures.close()');print(code,'domestic board passed',flush=True)
    page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-scope",{value:"international"})')
    page.wait_for_function('!suntrainReplay.filters.airports.length && suntrainReplay.filters.flightScope==="international" && suntrainReplay.filtered.length')
    intl=page.evaluate('suntrainReplay.filtered.length')
    assert page.evaluate('suntrainReplay.filtered.every(s=>(suntrainReplay.day.stations[s.stops[0][0]].country==="PH")!==(suntrainReplay.day.stations[s.stops[1][0]].country==="PH"))')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["ICN"]})');page.wait_for_function('suntrainReplay.filters.airports[0]==="ICN" && suntrainReplay.filtered.length')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="ICN"))')
    page.wait_for_function('suntrainReplay.departures.timezone==="Asia/Seoul" && suntrainReplay.departures.calls.length')
    text=page.locator('#replay-departures').inner_text();assert 'KST' in text and 'Philippine time (UTC+8)' in text
    page.get_by_role('button',name='Expand board',exact=True).click()
    page.screenshot(path='.cache/philippines-flights-audit/international-board.png')
    for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
    page.locator('#theme-toggle').select_option('dark')
    page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
    assert 'waktu Filipina (UTC+8)' in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/philippines-flights-audit/mobile.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-scope",{value:"both"});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('(n)=>suntrainReplay.frequencyView && suntrainReplay.filters.flightScope==="both" && suntrainReplay.filtered.length===n && suntrainReplay.frequencyFeatures.length',arg=domestic+intl)
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    features=page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)');page.evaluate('suntrainReplay.seek(suntrainReplay.day.end)');assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    assert len(downloads)==count
    page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
    page.evaluate('dash_clientside.set_props("replay-city",{value:"international_network"})')
    page.wait_for_function('suntrainReplay.day.city==="international_network" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='UTC' and page.locator('#replay-country-controls').is_visible()
    for destination in ['TH','JP','MY','AU']:
        page.evaluate('(c)=>{dash_clientside.set_props("replay-from-countries",{value:["PH"]});dash_clientside.set_props("replay-to-countries",{value:[c]})}',destination)
        page.wait_for_function('(c)=>suntrainReplay.filters.fromCountries[0]==="PH" && suntrainReplay.filters.toCountries[0]===c && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country==="PH" && suntrainReplay.day.stations[s.stops[1][0]].country===c)',arg=destination)
    assert not errors,errors
    print(f'{domestic} domestic / {intl} international: PHT, exact airports, USD previews, local foreign boards, fullscreen/mobile, themes, Indonesian, frequency and PH network filters passed',flush=True)
    browser.close()
