"""Optional browser smoke test. Run against a local SunTrain server with Playwright installed."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width':1280,'height':900}, ignore_https_errors=True)
    errors, downloads = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: downloads.append(request.url) if '/api/replay/' in request.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8843'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs", {value:"replay"})')
    page.wait_for_function('suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    page.locator('#replay-open-departures').click()
    page.locator('#departure-search').fill('Flinders')
    choices=page.locator('#replay-departures select option')
    assert choices.count()>0
    page.locator('#replay-departures select').select_option(choices.first.get_attribute('value'))
    page.get_by_role('button',name='Open departures',exact=True).click()
    page.wait_for_selector('.departure-row')
    assert page.locator('.departure-row').count()<=15
    requests=len(downloads)
    before=page.evaluate('suntrainReplay.now')
    target=page.evaluate('suntrainDepartures.upcomingPage(suntrainReplay.departures.calls,suntrainReplay.now).rows[0].at')
    page.locator('.departure-row').first.click()
    assert page.evaluate('suntrainReplay.now')==before
    assert page.locator('#replay-details').is_visible()
    page.get_by_role('button',name='Go to departure',exact=True).click()
    assert page.evaluate('suntrainReplay.now')==target
    assert page.evaluate('!suntrainReplay.playing && !suntrainReplay.followSelected')
    page.get_by_role('button',name='Back to departures',exact=True).click()
    page.locator('.departure-row').first.focus()
    page.keyboard.press('Enter')
    assert page.locator('#replay-details').is_visible()
    page.get_by_role('button',name='Back to departures',exact=True).click()
    assert len(downloads)==requests
    # Global filters and backward seeking update the board without downloads.
    page.evaluate('dash_clientside.set_props("replay-number", {value:"no-such-service-xyz"})')
    page.wait_for_function('suntrainReplay.filtered.length===0')
    assert 'No upcoming departures' in page.locator('#replay-departures').inner_text()
    page.evaluate('dash_clientside.set_props("replay-number", {value:""})')
    page.wait_for_function('suntrainReplay.filtered.length>0')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start)')
    page.wait_for_selector('.departure-row')
    page.evaluate('(at)=>suntrainReplay.seek(at)',before)
    assert len(downloads)==requests
    # Click an actual rendered station, avoiding vehicle markers and toolbars.
    page.locator('#replay-close-details').click()
    hit=page.evaluate('''() => {
        const r=suntrainReplay, map=r.graph, height=map.getContainer().clientHeight;
        for(const feature of map.queryRenderedFeatures({layers:['replay-stations']})) {
            const point=map.project(feature.geometry.coordinates);
            if(point.y>150 && point.y<height-60 && point.x>30 && point.x<600 &&
                !map.queryRenderedFeatures(point,{layers:['replay-trains']}).length)
                return {x:point.x,y:point.y,id:Number(feature.properties.id)};
        }
    }''')
    assert hit
    box=page.locator('#replay-map').bounding_box()
    page.mouse.click(box['x']+hit['x'],box['y']+hit['y'])
    page.wait_for_function('(id)=>suntrainReplay.departures.station===id && suntrainReplay.departures.visible',arg=hit['id'])
    # Heatmap popup keeps its boardings and offers a working departure action.
    page.evaluate('dash_clientside.set_props("replay-map-mode", {value:"demand"})')
    page.wait_for_function('suntrainReplay.mapMode==="demand" && suntrainReplay.demandSnapshot?.rows.length')
    page.evaluate('''() => { const r=suntrainReplay; r.demandPinned=true;
        r.showDemandPopup(r.demandSnapshot.rows.find(s=>s.name.includes("Flinders")).id); }''')
    page.locator('.replay-map-tooltip button').click()
    assert page.locator('#replay-departures').is_visible()
    page.locator('.departure-row').first.click()
    page.get_by_role('button',name='Go to departure',exact=True).click()
    page.wait_for_function('suntrainReplay.mapMode==="both"')
    page.get_by_role('button',name='Back to departures',exact=True).click()
    page.screenshot(path='.cache/station-departures-desktop.png',full_page=True)
    page.locator('#theme-toggle').select_option('light')
    page.set_viewport_size({'width':390,'height':844})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.locator('#replay-open-departures').click()
    assert page.locator('#replay-departures').is_visible()
    page.screenshot(path='.cache/station-departures-mobile.png',full_page=True)
    page.locator('#replay-fullscreen').click()
    page.wait_for_function('suntrainReplay.isFullscreen()')
    assert page.locator('#replay-departures').is_visible()
    page.locator('#replay-close-details').click()
    assert not page.locator('#replay-departures').is_visible()
    page.keyboard.press('Escape')
    page.set_viewport_size({'width':1280,'height':900})
    # A failed replacement download must not leave actionable old station calls.
    page.route('**/api/replay/melbourne/**',lambda route:route.abort())
    page.evaluate('dash_clientside.set_props("replay-date", {data:"2024-05-28"})')
    page.wait_for_function('document.querySelector("#replay-load-message").textContent.includes("could not load")')
    assert page.evaluate('suntrainReplay.departures.station===null && !suntrainReplay.departures.visible')
    page.unroute('**/api/replay/melbourne/**')
    for city,modes in [('netherlands',['ferry']),('jakarta',['bus'])]:
        page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
        page.wait_for_function('(city)=>suntrainReplay.day?.city===city && !suntrainReplay.loading',arg=city,timeout=120000)
        assert page.evaluate('suntrainReplay.departures.station===null')
        page.evaluate('(modes)=>dash_clientside.set_props("replay-modes",{value:modes})',modes)
        page.wait_for_function('(mode)=>!suntrainReplay.loading && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.mode===mode)',arg=modes[0],timeout=120000)
        page.evaluate('''() => { const r=suntrainReplay; r.pause(); r.seek(r.day.start);
            const s=r.filtered[0]; r.departures.open(s.stopIds?s.stopIds[0]:s.stops[0][0]); }''')
        page.wait_for_selector('.departure-row')
        assert page.locator('.departure-row').count()<=15
        page.locator('.departure-row').first.click()
        page.get_by_role('button',name='Go to departure',exact=True).click()
        assert page.evaluate('!suntrainReplay.playing')
    assert not errors,errors
    print({'result':'passed','page_errors':errors,'schedule_requests':len(downloads)},flush=True)
    browser.close()
