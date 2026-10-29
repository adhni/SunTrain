"""Thai international scopes, exact gateways and foreign local airport boards."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8875'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"thailand_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="thailand_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.filters.flightScope')=='both'
    page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"domestic"})')
    page.wait_for_function('suntrainReplay.filters.flightScope==="domestic"')
    domestic=page.evaluate('suntrainReplay.filtered.length');assert domestic==615
    page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"international"})')
    page.wait_for_function('suntrainReplay.filters.flightScope==="international" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.flight_scope==="international")')
    intl=page.evaluate('suntrainReplay.filtered.length')
    assert page.evaluate('suntrainReplay.filtered.every(s=>(suntrainReplay.day.stations[s.stops[0][0]].country==="TH")!==(suntrainReplay.day.stations[s.stops[1][0]].country==="TH"))')
    assert 'ICT' in page.locator('#replay-clock-date').inner_text()
    for code in ['BKK','DMK','HKT','CNX','USM']:
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length',arg=code)
        assert page.evaluate('(code)=>suntrainReplay.filtered.every(s=>s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code===code))',code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('suntrainReplay.departures.calls.length && suntrainReplay.departures.services===suntrainReplay.filtered')
        assert page.evaluate('suntrainReplay.departures.timezone')=='Asia/Bangkok'
        if code=='BKK':
            carrier=page.evaluate('suntrainReplay.filtered[0].carrier')
            page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
            page.wait_for_function('(c)=>suntrainReplay.filters.carriers[0]===c && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
            page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
            page.wait_for_function('!suntrainReplay.filters.carriers.length')
            page.get_by_role('button',name='Expand board',exact=True).click()
            page.locator('.departure-row').first.click()
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.departures.calls.length')
        page.locator('[data-event="destinations"]').click()
        page.wait_for_function('suntrainReplay.departures.destinationRows.length')
        page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airport-direction",{value:"both"})')
        page.wait_for_function('suntrainReplay.filters.airportDirection==="both"')
        print(code,'international airport filtering and boards passed',flush=True)
    # A foreign board inside the Thai view uses that airport's local zone.
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["ICN"]})')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="ICN" && suntrainReplay.filtered.length')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="ICN"))')
    page.wait_for_function('suntrainReplay.departures.timezone==="Asia/Seoul" && suntrainReplay.departures.calls.length')
    text=page.locator('#replay-departures').inner_text();assert 'KST' in text and 'ICT (UTC+7)' in text and 'Airport times are local.' in text
    page.get_by_role('button',name='Expand board',exact=True).click()
    page.screenshot(path='.cache/thailand-international-audit/foreign-board.png')
    page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Waktu bandara menggunakan waktu setempat.' in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/thailand-international-audit/mobile.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-scope",{value:"both"})')
    page.wait_for_function('(total)=>suntrainReplay.filters.flightScope==="both" && !suntrainReplay.filters.airports.length && suntrainReplay.filtered.length===total',arg=domestic+intl)
    page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length')
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    assert not errors,errors
    print(f'Thai scopes: {domestic} domestic / {intl} international; foreign local clocks, fullscreen, Indonesian, mobile and frequency passed',flush=True)
    browser.close()
