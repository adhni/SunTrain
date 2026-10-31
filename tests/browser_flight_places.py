"""Geographical discovery, ranked dropdowns, stable playback and original replays."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_controls import click_tool, select_setting

OUT = Path('.cache/flight-geography'); OUT.mkdir(parents=True, exist_ok=True)
CAMERA = '({center:suntrainReplay.graph.getCenter().toArray(),zoom:suntrainReplay.graph.getZoom()})'

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True, args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, ignore_https_errors=True)
    errors, downloads = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8050'), wait_until='domcontentloaded')
    page.wait_for_function('suntrainHome.ready')
    assert not downloads
    page.locator('[data-home-kind=flights]').click()
    assert page.locator('[data-flight-place]').count() == 7
    page.locator('#home-place').click()
    search = page.locator('input.dash-dropdown-search:visible')
    for query in ['MEL','LHR']:
        search.fill(query)
        page.locator('[role=option]').filter(has=page.locator(f'input[value="airport:{query}"]')).wait_for()
        assert page.locator('#home-place').get_attribute('aria-expanded') == 'true'
    search.fill('UK')
    option = page.locator('[role=option]').filter(has=page.locator('input[value="country:GB"]'))
    option.wait_for()
    page.screenshot(path=str(OUT/'search-uk.png'))
    page.keyboard.press('Enter')
    page.locator('.home-open-replay').click()
    page.wait_for_function('suntrainReplay.place?.id==="country:GB" && !suntrainReplay.loading && !suntrainReplay.needsFit', timeout=120000)
    assert page.evaluate('suntrainReplay.filtered.length') == 4208
    assert page.evaluate('suntrainReplay.totalFlights') == 4208
    print('Country search and combined UK captures passed',flush=True)
    assert page.locator('#replay-place-breadcrumbs').inner_text().replace('\n','').endswith('United Kingdom')
    page.screenshot(path=str(OUT/'uk-desktop.png'))
    initial_downloads = len(downloads)
    page.evaluate('suntrainReplay.play()')
    before = page.evaluate('suntrainReplay.now')
    page.locator('#replay-place').click()
    page.locator('input.dash-dropdown-search:visible').fill('LHR')
    page.locator('[role=option]').filter(has=page.locator('input[value="airport:LHR"]')).click()
    page.wait_for_function('suntrainReplay.place?.id==="airport:LHR"')
    state = page.evaluate('({playing:suntrainReplay.playing,now:suntrainReplay.now,valid:suntrainReplay.filtered.every(s=>suntrainPlaces.matchesPlace(s,suntrainReplay.place,suntrainReplay.day))})')
    assert state['playing'] and state['now'] >= before and state['valid'], state
    assert len(downloads) == initial_downloads
    print('Airport drill-down preserves playback and reuses the loaded replay',flush=True)
    page.evaluate('suntrainReplay.pause()')
    page.locator('#replay-fullscreen-filters').click()
    page.locator('#replay-carriers').click()
    page.screenshot(path=str(OUT/'airlines-desktop.png'))
    rows = page.locator('.dash-dropdown-options:visible [role=option]').evaluate_all('els=>els.map(el=>({value:el.querySelector("input").value,count:Number(el.dataset.exploreCount?.replaceAll(",","")||0)}))')
    airlines = [r for r in rows if ':' not in r['value']]
    assert airlines[0]['value'] == 'BA', airlines[:5]
    assert [r['count'] for r in airlines] == sorted([r['count'] for r in airlines], reverse=True)
    print('Airline count ordering passed',flush=True)
    # Counts update even if carrier names and their ranking do not change.
    page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"international"})')
    page.wait_for_function('suntrainReplay.filters.flightScope==="international"')
    page.wait_for_function('''()=>{const r=suntrainReplay,expected=r.day.services.filter(s=>s.carrier==='BA' && suntrainReplayCore.matches(s,{...r.filters,carriers:[]},r.day)).length;
        return document.querySelector('.dash-dropdown-option input[value="BA"]')?.closest('[role=option]').dataset.exploreCount===expected.toLocaleString(suntrainI18n.locale)}''')
    page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"both"})')
    page.wait_for_function('suntrainReplay.filters.flightScope==="both"')
    page.locator('[role=option]').filter(has=page.locator('input[value="BA"]')).click()
    page.keyboard.press('Escape')
    page.wait_for_function('suntrainReplay.filters.carriers.includes("BA")')
    page.keyboard.press('Escape')
    page.wait_for_function('!document.querySelector("#replay-panel").classList.contains("replay-show-filters")')
    now = page.evaluate('suntrainReplay.now')
    camera = page.evaluate(CAMERA)
    # Reset filter choices without moving the current place's camera or clock.
    page.evaluate('suntrainPlayground.clearFilters()')
    page.wait_for_function('!suntrainReplay.filters.carriers.length')
    assert page.evaluate(CAMERA) == camera and page.evaluate('suntrainReplay.now') == now
    # Parent navigation uses the same loaded data and preserves the current time.
    page.locator('#replay-place-breadcrumbs').get_by_role('button',name='Europe',exact=True).click()
    page.wait_for_function('suntrainReplay.place?.id==="region:europe"')
    assert page.evaluate('suntrainReplay.now') == now
    assert len(downloads) == initial_downloads
    for id in ['region:oceania','country:SG','experience:atlantic','country:GB','airport:AVV']:
        page.evaluate('(id)=>suntrainHome.openReplay(id)',id)
    page.wait_for_function('suntrainReplay.place?.id==="airport:AVV"')
    assert page.evaluate('suntrainReplay.filtered.every(s=>suntrainPlaces.matchesPlace(s,{kind:"airport",code:"AVV"},suntrainReplay.day))')
    page.evaluate('suntrainHome.openReplay("region:pacific-islands")')
    page.wait_for_function('suntrainReplay.place?.id==="region:pacific-islands"')
    camera = page.evaluate(CAMERA)
    page.evaluate('suntrainReplay.graph.jumpTo({center:[0,0],zoom:2})')
    click_tool(page,'#replay-melbourne')
    assert page.evaluate(CAMERA) == camera
    # New filters share the same frequency totals and airport boards.
    page.evaluate('suntrainHome.openReplay("airport:SIN")')
    page.wait_for_function('suntrainReplay.place?.id==="airport:SIN"')
    page.get_by_text('Flight frequency',exact=True).first.click()
    page.wait_for_function('suntrainReplay.frequencyView && !suntrainReplay.frequencyDirty')
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    page.get_by_text('Moving flights',exact=True).first.click()
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="SIN"))')
    page.wait_for_selector('.departure-row')
    page.get_by_role('button', name='Expand board', exact=True).click()
    page.wait_for_function('suntrainReplay.departures.expanded')
    page.keyboard.press('Escape'); page.locator('#replay-close-details').click()
    # Locale changes retain the country, clock and carrier choices.
    page.evaluate('suntrainHome.openReplay("country:GB")')
    page.wait_for_function('suntrainReplay.place?.id==="country:GB"')
    now=page.evaluate('suntrainReplay.now')
    select_setting(page,'#language-select','id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert page.evaluate('suntrainReplay.place.id') == 'country:GB'
    assert page.evaluate('suntrainReplay.now') == now
    local_name = page.evaluate('new Intl.DisplayNames([suntrainI18n.locale],{type:"region"}).of("GB")')
    assert local_name in page.locator('#replay-place-breadcrumbs').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(200)
    assert page.locator('#replay-play').bounding_box()['y']+page.locator('#replay-play').bounding_box()['height'] <= 844
    assert page.locator('#replay-map').bounding_box()['height'] > 300
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    page.screenshot(path=str(OUT/'uk-mobile-id.png'))
    page.locator('#replay-place').click()
    page.locator('input.dash-dropdown-search:visible').fill('SIN')
    page.screenshot(path=str(OUT/'places-mobile-id.png'))
    page.keyboard.press('Escape')
    select_setting(page,'#language-select','en')
    # Original local-day/week views remain available and retain their original clocks.
    page.evaluate('suntrainHome.openReplay("indonesia_flights")')
    page.wait_for_function('suntrainReplay.day?.city==="indonesia_flights" && !suntrainReplay.loading',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone') == 'Asia/Jakarta'
    assert page.locator('#replay-place-breadcrumbs').is_hidden()
    page.evaluate('dash_clientside.set_props("replay-date",{data:"2026-11-08"})')
    page.wait_for_function('suntrainReplay.day?.business_date==="2026-11-08" && !suntrainReplay.loading',timeout=120000)
    page.evaluate('suntrainHome.openReplay("country:SG")')
    page.wait_for_function('suntrainReplay.place?.id==="country:SG" && suntrainReplay.day?.business_date==="2026-11-02" && !suntrainReplay.loading',timeout=120000)
    assert page.evaluate('suntrainReplay.filtered.length') == 1067
    assert page.evaluate('suntrainReplay.day.timezone') == 'UTC'
    # Back retains the Explore transport choice and its camera.
    page.locator('#replay-back-explore').click()
    page.wait_for_function('document.querySelector("#main-content").classList.contains("home-active")')
    assert page.evaluate('suntrainHome.kind') == 'flights'
    assert not errors, errors
    (OUT/'validation.json').write_text(json.dumps({'assertions':'passed','page_errors':errors,'replay_requests':len(downloads),'top_heathrow_airlines':airlines[:6]},indent=2))
    print('Flight geography, dropdowns, playback, boards, mobile, language and dated replay assertions passed',flush=True)
    browser.close()
    print('Browser shutdown completed',flush=True)
