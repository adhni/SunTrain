"""Airport/airline codes, full-day destinations, and frequency lines on actual captures."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8864'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"indonesia_flights"})')
    page.wait_for_function('suntrainReplay?.day?.city==="indonesia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.locator('#replay-flight-controls').is_visible()
    assert not page.locator('#replay-generic-operator-field').is_visible()
    count=len(downloads)
    page.locator('#replay-carriers').click()
    page.get_by_text('GA · Garuda Indonesia',exact=True).click()
    page.keyboard.press('Escape')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["CGK"]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="GA" && s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="CGK"))')
    assert page.evaluate('suntrainReplay.graph.getLayoutProperty("replay-planes","visibility")')=='none'
    assert page.locator('#replay-play').is_disabled()
    assert not page.locator('#replay-legend').is_visible()
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    features=page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.end)')
    assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        page.locator('#theme-toggle').select_option(theme)
        assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    page.locator('#theme-toggle').select_option('dark')
    page.screenshot(path='.cache/flight-frequency-map.png')
    hit=page.evaluate('''() => {
        const r=suntrainReplay,m=r.graph,h=m.getContainer().clientHeight,w=m.getContainer().clientWidth;
        for(const f of r.frequencyFeatures) for(const c of f.geometry.coordinates.slice(10,-10)) {
            const p=m.project(c);if(p.x<40||p.x>w-40||p.y<120||p.y>h-110)continue;
            if(r.stationNear(p))continue;
            if(m.queryRenderedFeatures(p,{layers:['replay-frequency']}).length)return {x:p.x,y:p.y};
        }
    }''')
    assert hit
    box=page.locator('#replay-map').bounding_box()
    page.mouse.click(box['x']+hit['x'],box['y']+hit['y'])
    page.wait_for_function('suntrainReplay.departures.visible && suntrainReplay.filters.lines.length>0')
    assert page.evaluate('suntrainReplay.departures.fullDay')
    assert page.evaluate('suntrainReplay.now===suntrainReplay.day.end')
    assert page.locator('.departure-row').count()>0
    print('Code filters, frequency counts, fixed seeking, themes and actual line click passed',flush=True)
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-carriers",{value:[]});dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-lines",{value:[]})')
    page.wait_for_function('!suntrainReplay.filters.carriers.length && !suntrainReplay.filters.airports.length && !suntrainReplay.filters.lines.length')
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="CGK"))')
    page.locator('[data-event="destinations"]').click()
    assert page.evaluate('suntrainReplay.departures.destinationRows.length')>15
    assert page.evaluate('suntrainReplay.departures.destinationRows.reduce((n,r)=>n+r.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).filter(s=>s.stops[0][0]===suntrainReplay.departures.station).length')
    page.get_by_role('button',name='Expand board',exact=True).click()
    page.locator('.departure-pagination button').last.click()
    assert page.evaluate('suntrainReplay.departures.page')==1
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Tujuan' in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    print('Mobile board layout',page.evaluate('({cards:document.querySelectorAll(".replay-detail-card").length,heads:document.querySelectorAll(".replay-detail-heading").length,height:document.querySelector(".replay-detail-card").getBoundingClientRect().height,viewport:innerHeight})'),flush=True)
    page.screenshot(path='.cache/flight-destinations-mobile.png')
    now=page.evaluate('suntrainReplay.now')
    page.locator('.destination-row').first.click()
    page.wait_for_function('suntrainReplay.departures.event==="departure" && suntrainReplay.filters.lines.length>0')
    assert page.evaluate('suntrainReplay.departures.expanded && suntrainReplay.departures.fullDay')
    assert 'Sepanjang hari pemutaran terpilih' in page.locator('#replay-departures').inner_text()
    assert page.evaluate('suntrainReplay.now')==now
    assert page.locator('.departure-row').count()>0
    page.locator('.departure-row').first.click()
    assert page.evaluate('suntrainReplay.now')==now
    page.get_by_role('button',name='Kembali ke papan bandara',exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded && suntrainReplay.departures.fullDay')
    page.keyboard.press('Escape')
    page.evaluate('suntrainReplay.departures.close()')
    page.locator('#language-select').select_option('en')
    page.set_viewport_size({'width':1440,'height':1100})
    page.evaluate('dash_clientside.set_props("replay-lines",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"planes"})')
    page.wait_for_function('!suntrainReplay.frequencyView && suntrainReplay.graph.getLayoutProperty("replay-planes","visibility")==="visible"')
    assert len(downloads)==count
    page.evaluate('dash_clientside.set_props("replay-city",{value:"australia_flights"})')
    page.wait_for_function('suntrainReplay.day.city==="australia_flights" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.locator('#replay-flight-controls').is_visible()
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["AVV"]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="AVV"))')
    assert not errors,errors
    print('Destinations, pagination, full-day drill-down without seeking, Indonesian, mobile, plane restoration and Australian exact airports passed',flush=True)
    browser.close()
