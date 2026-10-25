"""Thai exact airports, ICT boards, USD fares and domestic explorer UX."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/thailand_flights/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8874'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"thailand_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="thailand_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert not page.locator('#replay-flight-scope-field').is_visible()
    assert not page.locator('#replay-flight-hubs-field').is_visible()
    assert page.evaluate('suntrainReplay.day.timezone')=='Asia/Bangkok'
    assert page.evaluate('suntrainReplay.day.schedule.fare_context.currency')=='USD'
    assert 'ICT' in page.locator('#replay-clock-date').inner_text()
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
    assert page.evaluate('suntrainReplay.graph.getBounds().getNorth()-suntrainReplay.graph.getBounds().getSouth()<40')
    count=len(downloads)
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
    page.wait_for_function('!suntrainReplay.display.includes("stations") && !suntrainReplay.graph.getSource("replay-stations")._data.features.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length===suntrainReplay.day.stations.length && suntrainReplay.filters.airportDirection==="departures"')
    page.screenshot(path='.cache/thai-flights-map.png')
    for code in ['BKK','DMK','CNX','HKT','USM','HDY','UBP']:
        print(f'Checking {code} departure/arrival boards',flush=True)
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered')
        assert page.evaluate('suntrainReplay.departures.timezone')=='Asia/Bangkok'
        assert 'ICT' in page.locator('#replay-departures').inner_text()
        assert 'ICT (UTC+7)' in page.locator('#replay-departures').inner_text()
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)',arg=code)
        page.locator('[data-event="departure"]').click()
        page.wait_for_function('suntrainReplay.filters.airportDirection==="departures" && suntrainReplay.departures.calls.length')
        if code=='BKK':
            page.get_by_role('button',name='Expand board',exact=True).click()
            before=page.evaluate('suntrainReplay.now')
            page.locator('.departure-row').filter(has_text='USD').first.click()
            assert page.evaluate('suntrainReplay.now')==before
            assert 'USD' in page.locator('.replay-flight-fare').inner_text()
            assert 'ICT' in page.locator('[data-fare-captured-at]').inner_text()
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
        page.evaluate('suntrainReplay.departures.close()')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["BKK"]});dash_clientside.set_props("replay-carriers",{value:["TG"]})')
    page.wait_for_function('suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="TG" && suntrainReplay.day.stations[s.stops[0][0]].code==="BKK")')
    empty_airport=page.evaluate('suntrainReplay.day.stations.find(a=>!suntrainReplay.day.services.some(s=>s.carrier==="PG" && suntrainReplay.day.stations[s.stops[0][0]].code===a.code)).code')
    page.evaluate('(code)=>{dash_clientside.set_props("replay-carriers",{value:["PG"]});dash_clientside.set_props("replay-airports",{value:[code]})}',empty_airport)
    page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filters.carriers[0]==="PG" && !suntrainReplay.filtered.length',arg=empty_airport)
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]});dash_clientside.set_props("replay-airports",{value:["BKK"]})')
    page.wait_for_function('!suntrainReplay.filters.carriers.length && suntrainReplay.filters.airports[0]==="BKK" && suntrainReplay.filtered.length')
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="BKK"))')
    page.get_by_role('button',name='Expand board',exact=True).click()
    next_page=page.get_by_role('button',name='Next',exact=True);assert next_page.is_enabled();next_page.click()
    assert page.evaluate('suntrainReplay.departures.page')==1
    page.get_by_role('button',name='Previous',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.page')==0
    page.screenshot(path='.cache/thai-flights-desktop.png')
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
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Tujuan' in page.locator('#replay-departures').inner_text()
    assert 'ICT' in page.locator('#replay-clock-date').inner_text()
    assert 'GMT+6' not in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight && document.querySelector(".replay-detail-card").getBoundingClientRect().top===0')
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/thai-flights-mobile.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("224")')
    assert len(downloads)==count and not errors,errors
    print('Seven airport boards, USD fares, ICT UTC+7 and separate BKK/DMK, filters, fullscreen/back, pagination, frequency, visibility, themes, Indonesian, mobile and cache reuse passed',flush=True)
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"japan_flights"})')
    page.wait_for_function('suntrainReplay.day.city==="japan_flights" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='Asia/Tokyo'
    assert 'JST' in page.locator('#replay-clock-date').inner_text()
    assert not errors,errors
    print('Existing Japan flight view retains its separate JST clock and domestic default',flush=True)
    browser.close()
