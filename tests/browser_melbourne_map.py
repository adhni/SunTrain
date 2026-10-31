"""Melbourne vehicle readability, station discovery and expanded board regression."""
import os
from playwright.sync_api import sync_playwright
from browser_controls import click_tool, select_setting

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, ignore_https_errors=True)
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if '/api/replay/' in request.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL', 'http://127.0.0.1:8861'), wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs", {value:"replay"})')
    page.wait_for_function('suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length', timeout=120000)
    page.evaluate('''() => {
        const r = suntrainReplay; r.pause(); r.seek(r.day.start + 5 * 3600);
        r.graph.jumpTo({center: [144.97, -37.815], zoom: 12});
    }''')
    camera = '''({center:suntrainReplay.graph.getCenter().toArray().map(n=>+n.toFixed(6)),
        zoom:+suntrainReplay.graph.getZoom().toFixed(6),bearing:suntrainReplay.graph.getBearing(),pitch:suntrainReplay.graph.getPitch()})'''
    before_camera = page.evaluate(camera)
    before_clock = page.evaluate('suntrainReplay.now')
    before_revision = page.evaluate('suntrainReplay.day.revision')
    page.evaluate("dash_clientside.set_props('replay-modes', {value: ['train', 'tram', 'bus']})")
    page.wait_for_function('suntrainReplay.filtered.some(s=>s.mode==="bus")')
    assert page.evaluate('suntrainReplay.day.revision') != before_revision
    assert page.evaluate(camera) == before_camera, 'Adding buses moved the camera'
    assert page.evaluate('suntrainReplay.now') == before_clock
    print('Adding transport modes preserves the camera and clock across a new revision', flush=True)
    page.wait_for_function('suntrainReplay.activePositions.some(f=>f.properties.body==="tram" && f.properties.dotCount===2)')
    assert page.evaluate('suntrainReplay.activePositions.some(f=>f.properties.body==="train" && f.properties.dotCount===3)')
    assert page.evaluate('suntrainReplay.activePositions.some(f=>f.properties.color==="#FF8200" && f.properties.body==="")')
    # Styling adds no synthetic services or inflated vehicle counts.
    assert page.evaluate('new Set(suntrainReplay.activePositions.map(f=>f.properties.id)).size === suntrainReplay.activePositions.length')
    page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-trains"]}).length > 0')
    assert page.evaluate("suntrainReplay.graph.getLayer('replay-trains').type === 'circle' && !suntrainReplay.graph.getLayer('replay-vehicle-bodies')")
    assert page.evaluate("suntrainReplay.graph.getSource('replay-trains')._data.features.length === suntrainReplay.activePositions.reduce((sum, f)=>sum+f.properties.dotCount,0)")
    for theme in ['light', 'dark', 'sunrise', 'blueprint', 'heritage']:
        select_setting(page, '#theme-toggle', theme)
        assert page.evaluate('suntrainReplay.graph.getPaintProperty("replay-trains","circle-stroke-color")==="#fff"')
    select_setting(page, '#theme-toggle', 'dark')
    page.screenshot(path='.cache/melbourne-vehicles.png', full_page=True)
    print('Vehicle rendering and five themes passed', flush=True)
    # Inspect several frames of a real Melbourne train through a curved leg.
    turn = page.evaluate('''() => {
        const r=suntrainReplay;
        const clock=(s,i,c)=>(s.stopIds?s.times[2*i+c-1]:s.stops[i][c])+(s.timeOffset||0);
        for (const service of r.filtered.filter(s=>s.mode==='train')) {
            for (let leg=0; leg<service.legs.length; leg++) {
                const path=r.day.paths[service.legs[leg]], points=path.coordinates;
                if (path.quality!=='track' || points.length<3) continue;
                for (let i=1; i<points.length-1; i++) {
                    if (path.distances[i]<1200 || path.distances.at(-1)-path.distances[i]<100) continue;
                    const a=points[i-1], b=points[i], c=points[i+1];
                    const bearing=(a,b)=>Math.atan2((b[0]-a[0])*Math.cos(b[1]*Math.PI/180),b[1]-a[1]);
                    const angle=Math.abs(Math.atan2(Math.sin(bearing(a,b)-bearing(b,c)),Math.cos(bearing(a,b)-bearing(b,c))));
                    if (angle<.35) continue;
                    const departure=clock(service,leg,2), arrival=clock(service,leg+1,1);
                    return {id:service.id,at:departure+(arrival-departure)*path.distances[i]/path.distances.at(-1),center:b};
                }
            }
        }
    }''')
    assert turn
    before_time = page.evaluate('suntrainReplay.now')
    page.evaluate('(turn)=>{const r=suntrainReplay; r.graph.jumpTo({center:turn.center,zoom:12});}', turn)
    for offset in [-1, 0, 1]:
        page.evaluate('(at)=>suntrainReplay.seek(at)', turn['at']+offset)
        dots = page.evaluate('(id)=>suntrainReplay.graph.getSource("replay-trains")._data.features.filter(f=>f.properties.id===id)', turn['id'])
        assert len(dots)==3
        assert len({dot['properties']['sizeFactor'] for dot in dots})==1
        assert [dot['properties']['part'] for dot in dots]==[0,1,2]
    # Rewinding reproduces the same train; no delayed per-dot animation state.
    page.evaluate('(at)=>suntrainReplay.seek(at)', turn['at']+1)
    assert page.evaluate('(id)=>suntrainReplay.graph.getSource("replay-trains")._data.features.filter(f=>f.properties.id===id)', turn['id'])==dots
    page.evaluate('(at)=>{const r=suntrainReplay;r.seek(at);r.graph.jumpTo({center:[144.97,-37.815],zoom:12});}', before_time)
    print('Real Melbourne curve frames, equal sizes and seeking passed', flush=True)
    # Discover a station by hover and click near its ring, without using search.
    page.wait_for_function('suntrainReplay.graph.loaded() && !suntrainReplay.graph.isMoving()')
    hit = page.evaluate('''() => {
        const r=suntrainReplay, map=r.graph, height=map.getContainer().clientHeight;
        const rect=map.getCanvas().getBoundingClientRect();
        for(const feature of map.queryRenderedFeatures({layers:['replay-stations']})) {
            // Browser mouse events use integer CSS pixels. Quantize before
            // picking so a nearby bus stop cannot win only after the click.
            const point=map.project(feature.geometry.coordinates), target={x:Math.floor(rect.left+point.x+7)-rect.left,y:Math.floor(rect.top+point.y)-rect.top};
            if (point.y<160 || point.y>height-50 || point.x<50 || point.x>800) continue;
            if (map.queryRenderedFeatures([target.x,target.y],{layers:['replay-trains']}).length) continue;
            const nearby=map.queryRenderedFeatures([[target.x-10,target.y-10],[target.x+10,target.y+10]],{layers:['replay-stations','replay-local-stops']});
            const distance=f=>{const p=map.project(f.geometry.coordinates);return Math.hypot(p.x-target.x,p.y-target.y)};
            // Co-located bus/train rings cannot establish an unambiguous ID.
            if(nearby.some(f=>f.properties.id!==feature.properties.id && distance(f)<distance(feature)+2))continue;
            if (r.stationNear(target)?.properties.id === feature.properties.id)
                return {...target,id:Number(feature.properties.id),name:feature.properties.name};
        }
    }''')
    assert hit
    box = page.locator('#replay-map').bounding_box()
    page.mouse.move(box['x']+hit['x'], box['y']+hit['y'])
    page.wait_for_function('(name)=>document.querySelector(".replay-map-tooltip")?.textContent.includes(name)', arg=hit['name'])
    page.mouse.click(box['x']+hit['x'], box['y']+hit['y'])
    page.wait_for_function('(id)=>suntrainReplay.departures.station===id && suntrainReplay.departures.visible', arg=hit['id'])
    # Return to the map and disable stations: both rings and click targets disappear.
    page.locator('#replay-close-details').click()
    page.evaluate('dash_clientside.set_props("replay-display", {value:["routes"]})')
    page.wait_for_function('!suntrainReplay.display.includes("stations")')
    assert page.evaluate('(point)=>suntrainReplay.stationNear(point)===null', hit)
    page.evaluate('dash_clientside.set_props("replay-display", {value:["routes","stations"]})')
    page.wait_for_function('suntrainReplay.display.includes("stations")')
    print('Station hover, click and visibility toggle passed', flush=True)
    # Use the busy Flinders Street board to inspect paging and journey navigation.
    page.evaluate('''() => { const r=suntrainReplay;
        r.departures.open(r.day.stations.findIndex(s=>s.name==='Flinders Street')); }''')
    page.wait_for_selector('.departure-row')
    state = page.evaluate('({now:suntrainReplay.now,center:suntrainReplay.graph.getCenter().toArray(),zoom:suntrainReplay.graph.getZoom(),station:suntrainReplay.departures.station,filters:suntrainReplay.filterSignature})')
    count = len(requests)
    page.locator('#replay-play').click()
    page.get_by_role('button', name='Expand departures', exact=True).click()
    assert page.get_by_role('dialog', name='Flinders Street').is_visible()
    assert page.evaluate('!suntrainReplay.playing')
    assert page.locator('.departure-columns').is_visible()
    assert page.locator('.replay-detail-card').bounding_box()['y'] == 0
    assert page.locator('.departure-row').count() == 15
    page.get_by_role('button', name='Next', exact=True).click()
    assert page.evaluate('suntrainReplay.departures.page') == 1
    page.locator('.departure-row').first.click()
    assert not page.evaluate('suntrainReplay.departures.expanded')
    page.get_by_role('button', name='Back to departures', exact=True).click()
    assert page.get_by_role('dialog', name='Flinders Street').is_visible()
    assert page.evaluate('suntrainReplay.departures.page') == 1
    page.get_by_role('button', name='Previous', exact=True).click()
    page.evaluate('document.querySelector(".replay-detail-card").scrollTop=0')
    page.screenshot(path='.cache/melbourne-board-desktop.png')
    print('Expanded board paging and journey navigation passed', flush=True)
    # Tab remains in the board; Escape restores the map and leaves the replay paused.
    page.locator('.departure-pagination button').last.focus()
    page.keyboard.press('Tab')
    assert page.evaluate('document.querySelector(".replay-detail-card").contains(document.activeElement)')
    page.keyboard.press('Escape')
    assert not page.evaluate('suntrainReplay.departures.expanded')
    # The clock advanced while Play was pressed; every spatial/filter choice remains.
    restored = page.evaluate('({center:suntrainReplay.graph.getCenter().toArray(),zoom:suntrainReplay.graph.getZoom(),station:suntrainReplay.departures.station,filters:suntrainReplay.filterSignature})')
    assert restored == {k:v for k,v in state.items() if k != 'now'}
    assert not page.evaluate('suntrainReplay.playing')
    # Works within the existing fullscreen map, without Escape closing both views.
    click_tool(page, '#replay-fullscreen')
    page.wait_for_function('suntrainReplay.isFullscreen()')
    page.get_by_role('button', name='Expand departures', exact=True).click()
    page.keyboard.press('Escape')
    assert page.evaluate('suntrainReplay.isFullscreen() && !suntrainReplay.departures.expanded')
    page.keyboard.press('Escape')
    page.set_viewport_size({'width':390, 'height':844})
    page.get_by_role('button', name='Expand departures', exact=True).click()
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    assert page.locator('.departure-destination').first.is_visible()
    assert page.locator('.replay-detail-card').bounding_box()['y'] == 0
    page.screenshot(path='.cache/melbourne-board-mobile.png')
    page.evaluate('suntrainI18n.setLanguage("id")')
    assert page.get_by_role('button', name='Kembali ke peta', exact=True).is_visible()
    assert page.evaluate('suntrainReplay.departures.expanded')
    page.get_by_role('button', name='Kembali ke peta', exact=True).click()
    assert len(requests) == count
    assert not errors, errors
    print({'result':'passed', 'page_errors':errors, 'new_schedule_requests':len(requests)-count}, flush=True)
    browser.close()
