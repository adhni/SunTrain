"""Map airport selection is a true filter; event direction owns counts consistently."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1050},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8864'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"indonesia_flights"})')
    page.wait_for_function('suntrainReplay?.day?.city==="indonesia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-airport-labels"]}).some(f=>f.properties.code==="CGK") && !suntrainReplay.graph.isMoving()')
    count=len(downloads)
    assert page.evaluate('suntrainReplay.filters.airportDirection')=='both'
    point=page.evaluate('''()=>{const r=suntrainReplay,a=r.day.stations.find(a=>a.code==='CGK'),p=r.graph.project([a.lon,a.lat]);return {x:p.x,y:p.y+16};}''')
    box=page.locator('#replay-map').bounding_box()
    page.mouse.click(box['x']+point['x'],box['y']+point['y'])
    page.wait_for_function('suntrainReplay.departures.visible && suntrainReplay.filters.airports.length===1 && suntrainReplay.filters.airports[0]==="CGK"')
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="CGK"))')
    assert page.evaluate('suntrainReplay.activePositions.every(f=>suntrainReplay.filtered.some(s=>s.id===f.properties.id))')
    assert page.evaluate('suntrainReplay.activePositions.every(f=>(f.properties.opacity ?? 1)===1)')
    page.locator('#replay-airport-direction').click()
    page.get_by_role('option',name='Departures',exact=True).click()
    page.wait_for_function('suntrainReplay.filters.airportDirection==="departures" && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code==="CGK")')
    page.locator('[data-event="arrival"]').click()
    page.wait_for_function('suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.departures.calls.length>0 && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops.at(-1)[0]].code==="CGK")')
    page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.flightEvent==="arrival"')
    expected=page.evaluate('suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day,"arrival").length')
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)')==expected
    assert 'captured arrivals' in page.locator('#replay-matching-count').inner_text()
    assert page.locator('#replay-activity-title').inner_text()=='Arrivals through the day'
    assert page.evaluate('suntrainReplay.departures.calls.every(c=>c.event==="arrival" && c.at>=suntrainReplay.day.start && c.at<suntrainReplay.day.end)')
    # Route drill-down must keep the selected destination and arrival event.
    page.evaluate('''()=>{const r=suntrainReplay,f=r.frequencyFeatures[0].properties;r.focusFlightConnection(f.a,f.b);}''')
    page.wait_for_function('suntrainReplay.filters.lines.length>0 && suntrainReplay.departures.fullDay')
    assert page.evaluate('suntrainReplay.day.stations[suntrainReplay.departures.station].code')=='CGK'
    assert page.evaluate('suntrainReplay.departures.event')=='arrival'
    assert page.locator('.departure-row').count()>0
    page.evaluate('dash_clientside.set_props("replay-lines",{value:[]});dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Scheduled arrivals")')
    assert int(page.locator('#city-overview-content .metric-value').first.inner_text().replace(',',''))==expected
    # Filters changed directly in Overview must stay usable and survive translation.
    page.evaluate('dash_clientside.set_props("replay-airports",{value:[]})')
    page.wait_for_function('!document.querySelector("#city-overview-content").textContent.includes("Scheduled arrivals")')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["CGK"]})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Scheduled arrivals")')
    page.locator('#replay-airport-direction').click()
    page.get_by_role('option',name='Departures',exact=True).click()
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Scheduled departures")')
    departure_count=page.locator('#city-overview-content .metric-value').first.inner_text()
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Keberangkatan terjadwal' in page.locator('#city-overview-content').inner_text()
    assert page.locator('#city-overview-content .metric-value').first.inner_text().replace('.','')==departure_count.replace(',','')
    page.locator('#language-select').select_option('en')
    page.evaluate('dash_clientside.set_props("replay-airport-direction",{value:"arrivals"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Scheduled arrivals")')
    print('Real airport click, strict flight visibility, directional endpoints, arrival frequency/timeline/boards and overview passed',flush=True)
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert page.locator('#replay-activity-title').inner_text()=='Kedatangan sepanjang hari'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.airports.length && suntrainReplay.filtered.some(s=>!s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="CGK"))')
    assert len(downloads)==count
    page.locator('#language-select').select_option('en')
    page.evaluate('dash_clientside.set_props("replay-city",{value:"australia_flights"})')
    page.wait_for_function('suntrainReplay.day.city==="australia_flights" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["AVV"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.filters.airportDirection==="departures" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code==="AVV")')
    assert not errors,errors
    print('Indonesian, mobile, clearing airport focus, cached filtering and exact Australian departure airport passed',flush=True)
    browser.close()
