"""Australian scope controls, Pacific movement, local boards and cached filtering."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/australia_flights/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8865'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"australia_flights"})')
    page.wait_for_function('suntrainReplay?.day?.city==="australia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.locator('#replay-flight-scope-field').is_visible()
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
    count=len(downloads)
    page.locator('#replay-flight-scope').click()
    page.get_by_role('option',name='International',exact=True).click()
    page.wait_for_function('suntrainReplay.filters.flightScope==="international" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.flight_scope==="international")')
    assert len(downloads)==count
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["SYD"]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="SYD" && suntrainReplay.filters.airportDirection==="departures"')
    flight=page.evaluate('''()=>{const r=suntrainReplay,s=r.filtered.find(s=>s.stops[0][2]>=r.day.start && r.day.stations[s.stops[1][0]].code==='LAX');return {id:s.id,start:s.stops[0][2],end:s.stops[1][1]};}''')
    # Around the date line, consecutive positions stay close and continue east.
    page.evaluate('(f)=>{suntrainReplay.pause();suntrainReplay.seek(f.start+(f.end-f.start)*.45)}',flight)
    a=page.evaluate('(id)=>suntrainReplay.activePositions.find(f=>f.properties.id===id).geometry.coordinates',flight['id'])
    page.evaluate('(f)=>suntrainReplay.seek(f.start+(f.end-f.start)*.55)',flight)
    b=page.evaluate('(id)=>suntrainReplay.activePositions.find(f=>f.properties.id===id).geometry.coordinates',flight['id'])
    assert b[0]>a[0] and b[0]-a[0]<30,(a,b)
    page.evaluate('''()=>{const r=suntrainReplay,s=r.filtered.find(s=>s.stops[0][2]>=r.day.start && r.day.stations[s.stops[1][0]].code==='LAX');dash_clientside.set_props('replay-lines',{value:[s.line]});}''')
    page.wait_for_function('suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code==="LAX")')
    page.evaluate('suntrainReplay.fit()')
    centre=page.evaluate('(suntrainReplay.graph.getCenter().lng%360+360)%360')
    assert 180<centre<220,centre  # Fit centres the Pacific rather than the Atlantic.
    page.screenshot(path='.cache/australia-international-pacific.png')
    print('Australia defaults, actual scope control, cached filtering, date-line movement and Pacific fit passed',flush=True)
    page.evaluate('dash_clientside.set_props("replay-lines",{value:[]});dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-airport-direction",{value:"both"});suntrainReplay.seek(suntrainReplay.day.start)')
    page.wait_for_function('!suntrainReplay.filters.airports.length && !suntrainReplay.filters.lines.length && suntrainReplay.filters.airportDirection==="both"')
    for code,zone in [('LAX','America/Los_Angeles'),('LHR','Europe/London')]:
        page.evaluate('(code)=>suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.departures.services===suntrainReplay.filtered',arg=code)
        assert page.evaluate('suntrainReplay.departures.timezone')==zone
        assert 'replay clock uses Melbourne time' in page.locator('#replay-departures').inner_text()
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('suntrainReplay.filters.airportDirection==="arrivals"')
        assert page.evaluate('suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===suntrainReplay.filters.airports[0])')
        if code=='LHR':
            # The reverse search returned LHR-PER even when PER-LHR was absent.
            page.locator('[data-event="departure"]').click()
            page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
        page.get_by_role('button',name='Expand board',exact=True).click()
        assert page.evaluate('suntrainReplay.departures.expanded')
        if page.locator('.departure-row').count():
            now=page.evaluate('suntrainReplay.now')
            page.locator('.departure-row').first.click()
            assert page.evaluate('suntrainReplay.now')==now
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
        page.evaluate('suntrainReplay.departures.close()')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["SYD"]});dash_clientside.set_props("replay-airport-direction",{value:"arrivals"});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.filters.airports[0]==="SYD" && suntrainReplay.flightEvent==="arrival"')
    assert page.evaluate('suntrainReplay.frequencyFeatures.every(f=>f.properties.count>0)')
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        page.locator('#theme-toggle').select_option(theme)
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert page.locator('#replay-activity-title').inner_text()=='Kedatangan sepanjang hari'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/australia-international-mobile.png')
    page.locator('#language-select').select_option('en')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Scheduled arrivals")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-scope",{value:"both"})')
    page.wait_for_function('new Set(suntrainReplay.filtered.map(s=>s.flight_scope)).size===2')
    assert len(downloads)==count
    assert not errors,errors
    print('Foreign boards, fullscreen/return, arrivals, frequency, themes, Indonesian, mobile, Overview and both scopes passed',flush=True)
    browser.close()
