"""Flight map, airport-local boards, arrivals, fullscreen and transit regression."""
import os
from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, ignore_https_errors=True)
    errors, downloads = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: downloads.append(request.url) if '/api/replay/australia_flights/' in request.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL', 'http://127.0.0.1:8863'), wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"australia_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city === "australia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length', timeout=120000)
    page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-planes"]}).length > 0')
    assert page.evaluate('suntrainReplay.day.stations.length') >= 18
    assert page.evaluate('new Set(suntrainReplay.filtered.map(s=>s.operator)).size') >= 3
    assert page.evaluate('suntrainReplay.day.stations.filter(a=>["MEL","AVV"].includes(a.code)).length') == 2
    assert page.evaluate('suntrainReplay.day.day_start_hour') == 0
    assert page.locator('#replay-range-start').inner_text() == '00:00'
    assert page.evaluate('suntrainReplay.graph.getSource("replay-routes")._data.features.length') == 0
    query_count = len(downloads)
    page.evaluate('dash_clientside.set_props("replay-operators",{value:["Qantas"]})')
    page.wait_for_function('() => suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.operator==="Qantas")')
    assert page.evaluate('suntrainReplay.activePositions.every(f=>f.properties.color==="#e53935")')
    page.evaluate('dash_clientside.set_props("replay-operators",{value:[]})')
    page.wait_for_function('() => new Set(suntrainReplay.filtered.map(s=>s.operator)).size>=3')
    assert len(downloads) == query_count
    assert page.evaluate('suntrainReplay.activePositions.every(f=>Number.isFinite(f.properties.bearing))')
    original = page.evaluate('JSON.stringify(suntrainReplay.activePositions)')
    now = page.evaluate('suntrainReplay.now')
    page.evaluate('(now)=>suntrainReplay.seek(now+600)', now)
    assert page.evaluate('JSON.stringify(suntrainReplay.activePositions)') != original
    page.evaluate('(now)=>suntrainReplay.seek(now)', now)
    assert page.evaluate('JSON.stringify(suntrainReplay.activePositions)') == original
    page.screenshot(path='.cache/australia-flights-map.png', full_page=True)
    print('Flight movement, headings, route visibility and deterministic seeking passed', flush=True)

    # Click Perth's code label; its board must be three hours behind the replay clock.
    point = page.evaluate('''() => {
        const r=suntrainReplay, airport=r.day.stations.find(a=>a.code==='PER');
        const point=r.graph.project([airport.lon,airport.lat]); point.y+=16; return point;
    }''')
    box = page.locator('#replay-map').bounding_box()
    page.mouse.click(box['x'] + point['x'], box['y'] + point['y'])
    page.wait_for_function('suntrainReplay.departures.visible && suntrainReplay.day.stations[suntrainReplay.departures.station].code === "PER"')
    assert 'GMT+8' in page.locator('#replay-departures').inner_text()
    assert page.evaluate('suntrainReplay.departures.timezone') == 'Australia/Perth'
    assert page.evaluate('suntrainReplay.activePositions.some(f=>f.properties.opacity===0.2)')
    assert page.evaluate('suntrainReplay.graph.getSource("replay-routes")._data.features.length') > 0
    page.locator('[data-event="arrival"]').click()
    assert page.evaluate('suntrainReplay.departures.calls.every(c=>c.index===1 && c.event==="arrival")')
    assert page.evaluate('suntrainReplay.departures.calls.length') > 0
    print('Actual airport click, Perth local times, airport focus and terminal arrivals passed', flush=True)

    # Melbourne has enough flights to exercise board paging and journey return state.
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="AVV"))')
    assert '(AVV)' in page.locator('#departure-title').inner_text()
    avv_calls = page.evaluate('suntrainReplay.departures.calls.length')
    assert avv_calls > 0
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="MEL"))')
    assert '(MEL)' in page.locator('#departure-title').inner_text()
    assert page.evaluate('suntrainReplay.departures.calls.length') > avv_calls
    page.get_by_role('button', name='Expand board', exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded && !suntrainReplay.playing')
    page.locator('.departure-pagination button').last.click()
    assert page.evaluate('suntrainReplay.departures.page') == 1
    page.locator('.departure-row').first.click()
    assert page.evaluate('suntrainReplay.now') == now  # Previewing does not seek.
    assert page.evaluate('suntrainReplay.departures.previewCall.event') == 'arrival'
    assert page.locator('#replay-details').inner_text().count('GMT+') >= 2
    page.get_by_role('button', name='Back to airport board', exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded && suntrainReplay.departures.page===1 && suntrainReplay.departures.event==="arrival"')
    page.screenshot(path='.cache/australia-flights-board-desktop.png')
    page.locator('.departure-row').first.click()
    arrival_at = page.evaluate('suntrainReplay.departures.previewCall.at')
    page.get_by_role('button', name='Go to arrival', exact=True).click()
    assert page.evaluate('suntrainReplay.now') == arrival_at
    assert 'Arrived' in page.locator('#replay-service-status').inner_text()
    page.get_by_role('button', name='Back to airport board', exact=True).click()
    assert page.evaluate('suntrainReplay.departures.expanded')
    page.keyboard.press('Escape')
    assert not page.evaluate('suntrainReplay.departures.expanded')
    print('Expanded board, arrival pages, preview/seek and return state passed', flush=True)

    for theme in ['light', 'dark', 'sunrise', 'blueprint', 'heritage']:
        page.locator('#theme-toggle').select_option(theme)
        assert page.evaluate('suntrainReplay.graph.hasImage("suntrain-plane")')
    page.locator('#theme-toggle').select_option('dark')
    count = len(downloads)
    page.locator('#language-select').select_option('id')
    assert page.locator('[data-event="arrival"]').inner_text() == 'Kedatangan'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('suntrainReplay.departures.setExpanded(true)')
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().y === 0')
    assert page.evaluate('document.querySelector(".replay-detail-card").scrollWidth <= innerWidth')
    page.screenshot(path='.cache/australia-flights-board-mobile.png')
    assert len(downloads) == count
    page.keyboard.press('Escape')
    page.evaluate('suntrainI18n.setLanguage("en")')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-context").textContent.includes("00:00–00:00")')
    assert 'Airports served' in page.locator('#city-overview-content').inner_text()
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-date",{data:"2026-11-02"})')
    page.wait_for_function('suntrainReplay.day.business_date === "2026-11-02" && !suntrainReplay.loading')
    assert page.evaluate('suntrainReplay.day.services.length') > 150
    page.evaluate('dash_clientside.set_props("replay-display",{value:[]})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length === 0')
    page.evaluate('dash_clientside.set_props("replay-city",{value:"melbourne"})')
    page.wait_for_function('suntrainReplay.day.city === "melbourne" && !suntrainReplay.loading && suntrainReplay.filtered.length', timeout=120000)
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.mode!=="flight")')
    assert page.locator('#replay-open-departures').inner_text() == 'Departures'
    assert not errors, errors
    print('Themes, Indonesian, mobile board, Overview, last date, station toggle and Melbourne return passed', flush=True)
    browser.close()
