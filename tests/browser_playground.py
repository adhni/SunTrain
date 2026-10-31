"""Map-first discovery, preset navigation and mobile controls using existing captures."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_controls import click_tool, select_setting

OUT = Path('.cache/playground'); OUT.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('SUNTRAIN_TEST_URL', 'http://127.0.0.1:8051')
CAMERA = '({center:suntrainReplay.graph.getCenter().toArray(),zoom:suntrainReplay.graph.getZoom()})'


def take_shot(page, path):
    # Let MapLibre and native fullscreen transitions settle before capturing pixels.
    page.wait_for_timeout(300)
    page.screenshot(path=str(path))

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':960}, ignore_https_errors=True)
    errors, downloads = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(URL, wait_until='domcontentloaded')
    page.wait_for_function('window.suntrainHome?.ready')
    page.wait_for_timeout(300)
    assert not downloads, downloads
    take_shot(page, OUT/'home-desktop.png')
    # Transport choice filters pins, search results, cards and Surprise me together.
    page.locator('[data-home-kind="transit"]').click()
    page.wait_for_function('suntrainHome.kind==="transit"')
    assert page.locator('[data-experience]:visible').count() == 2
    page.locator('#home-place').click()
    page.locator('input[type=search]:visible').fill('World')
    page.wait_for_timeout(250)
    assert page.get_by_text('No options found', exact=True).is_visible()
    page.keyboard.press('Escape')
    page.locator('[data-home-kind="all"]').click()
    print('Home kind and search passed',flush=True)
    # A numbered pin offers actual places directly.
    page.locator('.home-cluster').first.click()
    page.wait_for_selector('.home-cluster-place')
    assert page.locator('.home-cluster-place').count() > 1
    selected = page.locator('.home-cluster-place').first.inner_text().split('\n')[-1]
    page.locator('.home-cluster-place').first.click()
    page.wait_for_function('suntrainReplay.day && suntrainReplay.mapReady && !suntrainReplay.loading', timeout=120000)
    assert not page.evaluate('suntrainReplay.playing')
    page.locator('#replay-back-explore').click()
    page.wait_for_selector('#home-panel', state='visible')
    print('Cluster selection passed',flush=True)
    # Four presets have independent dates/timezones and real visible activity.
    records = []
    for scene in ['melbourne', 'tokyo', 'singapore', 'world']:
        page.evaluate('(id)=>suntrainHome.watch(id)', scene)
        page.wait_for_function('(id)=>suntrainReplay.day?.city===suntrainHome.experiences.find(s=>s.id===id).city && suntrainReplay.active && !suntrainReplay.loading && !suntrainHome.pendingExperience', arg=scene, timeout=120000)
        state = page.evaluate('''(id)=>{const r=suntrainReplay,s=suntrainHome.experiences.find(s=>s.id===id),playing=r.playing;r.pause();return {id,playing,date:r.day.business_date,expectedDate:s.date,at:r.now,expected:s.at,speed:r.speed,visible:r.visibleFlights,active:r.activePositions.length};}''', scene)
        assert state['date'] == state['expectedDate']
        assert state['playing'] and 0 <= state['at']-state['expected'] < 600, state
        assert state['speed'] == 60 and state['active'] > 0, state
        if scene in ['world','singapore']: assert state['visible'] > 0, state
        records.append(state)
        print('Scene ready:',scene,flush=True)
        map_box = page.locator('#replay-map').bounding_box()
        play_box = page.locator('#replay-play').bounding_box()
        assert map_box['height'] > 350 and 0 <= map_box['y'] < 300, map_box
        assert play_box['y']+play_box['height'] <= 960, play_box
        assert page.locator('.workspace-header').bounding_box()['y'] >= 0
        take_shot(page, OUT/(scene+'-desktop.png'))
    print('Four scenes, autoplay, clocks and desktop layout passed', flush=True)
    # Filter drawer traps focus; active chips remove only their filter.
    original = page.evaluate(CAMERA); now = page.evaluate('suntrainReplay.now')
    page.locator('#replay-fullscreen-filters').click()
    assert page.locator('#replay-filter-controls').is_visible()
    for _ in range(18):
        page.keyboard.press('Tab')
        assert page.evaluate('document.querySelector("#replay-filter-controls").contains(document.activeElement)')
    page.locator('#replay-flight-scope').click()
    page.keyboard.press('Escape')
    page.wait_for_function('document.querySelector("#replay-flight-scope").getAttribute("aria-expanded")==="false"')
    assert page.locator('#replay-filter-controls').is_visible()
    take_shot(page, OUT/'filters-desktop.png')
    page.keyboard.press('Escape')
    page.wait_for_function('document.activeElement.id==="replay-fullscreen-filters" && !document.querySelector("#replay-panel").classList.contains("replay-show-filters")')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["MEL"]})')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="MEL"')
    assert page.evaluate(CAMERA) == original and page.evaluate('suntrainReplay.now') == now
    page.get_by_role('button', name='Remove filter: MEL', exact=True).click()
    page.wait_for_function('!suntrainReplay.filters.airports.length')
    assert page.evaluate(CAMERA) == original and page.evaluate('suntrainReplay.now') == now
    page.evaluate('''() => {dash_clientside.set_props('replay-airports',{value:['MEL']});dash_clientside.set_props('replay-carriers',{value:['QF']});}''')
    page.wait_for_function('suntrainReplay.filters.carriers[0]==="QF" && suntrainReplay.filters.airports[0]==="MEL"')
    page.locator('#replay-filter-chips').get_by_role('button',name='Clear filters',exact=True).click()
    page.wait_for_function('!suntrainReplay.filters.carriers.length && !suntrainReplay.filters.airports.length')
    assert page.evaluate(CAMERA) == original and page.evaluate('suntrainReplay.now') == now
    page.get_by_text('Flight frequency', exact=True).first.click()
    page.wait_for_function('suntrainReplay.frequencyView')
    page.get_by_text('Moving flights', exact=True).first.click()
    page.wait_for_function('!suntrainReplay.frequencyView')
    # Phone: map and playback remain visible, while boards open as sheets.
    page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(300)
    map_box = page.locator('#replay-map').bounding_box(); play_box = page.locator('#replay-play').bounding_box()
    assert map_box['height'] > 350 and map_box['y'] < 200, map_box
    assert play_box['y'] + play_box['height'] <= 844, play_box
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    assert page.locator('.workspace-header').bounding_box()['y'] >= 0
    page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-flight-dots"]}).length>0')
    take_shot(page, OUT/'world-mobile.png')
    page.locator('#replay-fullscreen-filters').click()
    assert page.locator('#replay-filter-controls').bounding_box()['y'] > 0
    take_shot(page, OUT/'filters-mobile.png')
    page.keyboard.press('Escape')
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="MEL"))')
    page.wait_for_selector('.departure-row')
    assert page.evaluate('suntrainReplay.departures.visible')
    page.locator('#replay-expand-details').click()
    assert page.locator('#replay-panel').evaluate('(el)=>el.classList.contains("replay-sheet-expanded")')
    take_shot(page, OUT/'airport-sheet-mobile.png')
    page.get_by_role('button', name='Expand board', exact=True).click()
    page.wait_for_function('suntrainReplay.departures.expanded')
    take_shot(page, OUT/'airport-board-mobile.png')
    page.keyboard.press('Escape')
    assert not page.evaluate('suntrainReplay.departures.expanded')
    page.locator('#replay-close-details').click()
    assert not page.evaluate('suntrainReplay.departures.visible')
    assert not page.locator('#replay-panel').evaluate('(el)=>el.classList.contains("replay-sheet-expanded")')
    click_tool(page, '#replay-fullscreen')
    page.wait_for_function('suntrainReplay.isFullscreen()')
    page.locator('#replay-fullscreen-filters').click()
    page.locator('#replay-flight-scope').click()
    page.get_by_role('option',name='Domestic',exact=True).click()
    page.wait_for_function('suntrainReplay.filters.flightScope==="domestic"')
    page.keyboard.press('Escape')
    assert page.evaluate('suntrainReplay.isFullscreen()')
    page.keyboard.press('Escape')
    page.wait_for_function('!suntrainReplay.isFullscreen()')
    # Settings preserve camera, clock and captures; visible copy is bilingual.
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        select_setting(page, '#theme-toggle', theme)
        take_shot(page, OUT/('mobile-'+theme+'.png'))
    select_setting(page, '#language-select', 'id')
    assert page.get_by_role('button', name='Kembali menjelajah', exact=True).is_visible()
    take_shot(page, OUT/'world-mobile-id.png')
    page.locator('#replay-back-explore').click()
    page.wait_for_selector('#home-panel', state='visible')
    assert 'Dunia bergerak' in page.locator('[data-experience="world"]').inner_text()
    take_shot(page, OUT/'home-mobile-id.png')
    select_setting(page, '#language-select', 'en')
    home_camera = page.evaluate('({center:suntrainHome.map.getCenter().toArray(),zoom:suntrainHome.map.getZoom()})')
    page.locator('[data-home-kind="transit"]').click()
    page.locator('#home-surprise').click()
    page.wait_for_function('!suntrainHome.pendingExperience && suntrainReplay.active && ["melbourne","tokyo"].includes(suntrainReplay.day?.city)',timeout=120000)
    first = page.evaluate('suntrainHome.lastExperience')
    page.locator('#replay-back-explore').click()
    page.wait_for_selector('#home-panel',state='visible')
    assert page.evaluate('suntrainHome.kind') == 'transit'
    assert page.evaluate('({center:suntrainHome.map.getCenter().toArray(),zoom:suntrainHome.map.getZoom()})') == home_camera
    page.locator('#home-surprise').click()
    page.wait_for_function('(first)=>!suntrainHome.pendingExperience && suntrainReplay.active && suntrainHome.lastExperience!==first',arg=first,timeout=120000)
    # A superseded download cannot apply its preset later.
    held=[]
    page.route('**/api/replay/singapore_flights/**',lambda route:held.append(route))
    page.evaluate('suntrainHome.watch("singapore")')
    page.wait_for_timeout(400)
    page.evaluate('suntrainHome.watch("world")')
    page.wait_for_function('suntrainReplay.day?.city==="world_flights" && !suntrainHome.pendingExperience && !suntrainReplay.loading',timeout=120000)
    for route in held: route.abort()
    page.wait_for_timeout(300)
    assert page.evaluate('suntrainReplay.day.city') == 'world_flights'
    assert not errors, errors
    # Reduced motion keeps explicitly chosen scenes paused at their exact preset.
    reduced = browser.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce', ignore_https_errors=True)
    rp = reduced.new_page(); rp.goto(URL,wait_until='domcontentloaded')
    rp.wait_for_function('window.suntrainHome?.ready')
    for scene in ['melbourne','tokyo','singapore','world']:
        rp.evaluate('(id)=>suntrainHome.watch(id)',scene)
        rp.wait_for_function('(id)=>suntrainReplay.day?.city===suntrainHome.experiences.find(s=>s.id===id).city && !suntrainHome.pendingExperience && !suntrainReplay.loading',arg=scene,timeout=120000)
        assert rp.evaluate('(id)=>suntrainReplay.now===suntrainHome.experiences.find(s=>s.id===id).at && !suntrainReplay.playing',scene)
        take_shot(rp, OUT/(scene+'-mobile.png'))
    rp.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="MEL"))')
    rp.wait_for_function('suntrainReplay.departures.visible')
    rp.evaluate('suntrainHome.watch("world")')
    rp.wait_for_function('!suntrainHome.pendingExperience && !suntrainReplay.loading && !suntrainReplay.departures.visible')
    assert rp.evaluate('!suntrainReplay.selected && !suntrainReplay.playing && suntrainReplay.now===suntrainHome.experiences.find(s=>s.id==="world").at')
    (OUT/'validation.json').write_text(json.dumps({'scenes':records,'homepage_replay_downloads':0,'page_errors':errors,'desktop_mobile_sheets_filters_settings_races':'passed'},indent=2))
    print('Discovery, filters, mobile sheets, fullscreen, themes, bilingual state, rapid selection and reduced motion passed',flush=True)
    reduced.close(); browser.close()
