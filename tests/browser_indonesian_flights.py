"""Indonesia airport identities, local boards, week navigation and responsive replay."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/indonesia_flights/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8864'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"indonesia_flights"})')
    page.wait_for_function('suntrainReplay?.day?.city==="indonesia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.replay_kind')=='flights'
    assert page.evaluate('suntrainReplay.day.timezone')=='Asia/Jakarta'
    assert page.locator('#replay-range-start').inner_text()=='00:00'
    assert 'WIB' in page.locator('#replay-clock-date').inner_text()
    page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-planes"]}).length>0')
    assert page.evaluate('suntrainReplay.graph.getSource("replay-routes")._data.features.length')==0
    assert page.evaluate('suntrainReplay.activePositions.every(f=>Number.isFinite(f.properties.bearing))')
    count=len(downloads)
    operator=page.evaluate('suntrainReplay.filtered[0].operator')
    page.evaluate('(operator)=>dash_clientside.set_props("replay-operators",{value:[operator]})',operator)
    page.wait_for_function('(operator)=>suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.operator===operator)',arg=operator)
    page.evaluate('dash_clientside.set_props("replay-operators",{value:[]})')
    page.wait_for_function('new Set(suntrainReplay.filtered.map(s=>s.operator)).size>1')
    assert len(downloads)==count
    page.screenshot(path='.cache/indonesia-flights-map.png',full_page=True)
    now=page.evaluate('suntrainReplay.now')
    # Use real map clicks for airports in all three Indonesian time zones.
    for code,zone,label in [('KTG','Asia/Pontianak','WIB'),('UPG','Asia/Makassar','WITA'),('DJJ','Asia/Jayapura','WIT')]:
        page.evaluate('suntrainReplay.graph.resize()')
        print('Checking airport',code,flush=True)
        point=page.evaluate('''(code)=>{
            const r=suntrainReplay,a=r.day.stations.find(a=>a.code===code);
            const p=r.graph.project([a.lon,a.lat]); p.y+=16; return {x:p.x,y:p.y};
        }''',code)
        box=page.locator('#replay-map').bounding_box()
        page.mouse.click(box['x']+point['x'],box['y']+point['y'])
        page.wait_for_function('(code)=>suntrainReplay.departures.visible && suntrainReplay.day.stations[suntrainReplay.departures.station].code===code',arg=code)
        assert page.evaluate('suntrainReplay.departures.timezone')==zone
        assert label in page.locator('#replay-departures').inner_text()
        assert 'replay clock uses WIB' in page.locator('#replay-departures').inner_text()
        page.locator('[data-event="arrival"]').click()
        assert page.evaluate('suntrainReplay.departures.calls.every(c=>c.event==="arrival" && c.index===1)')
        if code != 'DJJ':
            assert page.evaluate('suntrainReplay.departures.calls.length')>0
        page.evaluate('suntrainReplay.departures.close()')
    page.evaluate("suntrainReplay.departures.event='departure';suntrainReplay.departures.services=null")
    for code in ['CGK','HLP']:
        page.evaluate('(code)=>suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))',code)
        assert f'({code})' in page.locator('#departure-title').inner_text()
        assert page.evaluate('suntrainReplay.departures.calls.length')>0
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="CGK"))')
    page.get_by_role('button',name='Expand board',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded && !suntrainReplay.playing')
    page.locator('.departure-pagination button').last.click()
    assert page.evaluate('suntrainReplay.departures.page')==1
    page.locator('.departure-row').first.click()
    assert page.evaluate('suntrainReplay.now')==now
    page.get_by_role('button',name='Back to airport board',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded && suntrainReplay.departures.page===1')
    page.locator('.departure-row').first.click()
    departure=page.evaluate('suntrainReplay.departures.previewCall.at')
    page.get_by_role('button',name='Go to departure',exact=True).click()
    assert page.evaluate('suntrainReplay.now')==departure
    page.get_by_role('button',name='Back to airport board',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded')
    page.screenshot(path='.cache/indonesia-flights-board-desktop.png',full_page=True)
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        page.locator('#theme-toggle').select_option(theme)
        assert page.evaluate('suntrainReplay.departures.expanded')
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Jam pemutaran menggunakan WIB' in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    assert page.locator('#replay-departures').bounding_box()['y']<100
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.screenshot(path='.cache/indonesia-flights-board-mobile.png')
    page.locator('#language-select').select_option('en')
    page.set_viewport_size({'width':1440,'height':1000})
    page.evaluate('suntrainReplay.departures.close()')
    for n in range(2,9):
        day=f'2026-11-{n:02}'
        page.evaluate('(day)=>dash_clientside.set_props("replay-date",{data:day})',day)
        page.wait_for_function('(day)=>suntrainReplay.day.business_date===day && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=day,timeout=120000)
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("queries captured")')
    assert 'Airports served' in page.locator('#city-overview-content').inner_text()
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-display",{value:[]})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length===0')
    page.evaluate('dash_clientside.set_props("replay-city",{value:"australia_flights"})')
    page.wait_for_function('suntrainReplay.day.city==="australia_flights" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.replay_kind')=='flights'
    assert page.locator('#replay-open-departures').inner_text()=='Airports'
    assert not errors,errors
    print('Indonesia map, distinct airports, local boards, filters, fullscreen, themes, Indonesian, mobile and all seven dates passed',flush=True)
    browser.close()
