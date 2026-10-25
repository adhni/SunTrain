"""Domestic-only KST/USD explorer, regional boards and existing transit isolation."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, ignore_https_errors=True)
    errors = []; downloads = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: downloads.append(r.url) if '/api/replay/south_korea_flights/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL', 'http://127.0.0.1:8869'), wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"south_korea_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="south_korea_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length', timeout=120000)
    assert not page.locator('#replay-flight-scope-field').is_visible()
    assert not page.locator('#replay-flight-hubs-field').is_visible()
    assert page.evaluate('suntrainReplay.day.timezone') == 'Asia/Seoul'
    assert page.evaluate('suntrainReplay.day.schedule.fare_context.currency') == 'USD'
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
    assert 'KST' in page.locator('#replay-clock-date').inner_text()
    assert page.evaluate('suntrainReplay.graph.getBounds().getNorth()-suntrainReplay.graph.getBounds().getSouth()<10')
    count = len(downloads)
    page.evaluate('dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
    page.wait_for_function('!suntrainReplay.display.includes("stations") && !suntrainReplay.graph.getSource("replay-stations")._data.features.length')
    page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length===12')
    page.screenshot(path='.cache/south-korea-flights-map.png')
    for code in ['GMP', 'CJU', 'PUS', 'WJU', 'HIN']:
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})', code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)', arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}', code)
        page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered')
        assert page.evaluate('suntrainReplay.departures.timezone') == 'Asia/Seoul'
        assert 'KST' in page.locator('#replay-departures').inner_text()
        assert 'USD' in page.locator('#replay-departures').inner_text()
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)', arg=code)
        page.locator('[data-event="departure"]').click()
        page.wait_for_function('suntrainReplay.filters.airportDirection==="departures" && suntrainReplay.departures.calls.length')
        page.get_by_role('button', name='Expand board', exact=True).click()
        before = page.evaluate('suntrainReplay.now')
        page.locator('.departure-row').filter(has_text='USD').first.click()
        assert page.evaluate('suntrainReplay.now') == before
        assert 'USD' in page.locator('.replay-flight-fare').inner_text()
        assert 'KST' in page.locator('[data-fare-captured-at]').inner_text()
        page.get_by_role('button', name='Back to airport board', exact=True).click()
        assert page.evaluate('suntrainReplay.departures.expanded')
        page.evaluate('suntrainReplay.departures.close()')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["GMP"]});dash_clientside.set_props("replay-carriers",{value:["KE"]})')
    page.wait_for_function('suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="KE" && suntrainReplay.day.stations[s.stops[0][0]].code==="GMP")')
    page.evaluate('dash_clientside.set_props("replay-airports",{value:["WJU"]})')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="WJU" && !suntrainReplay.filtered.length')
    assert page.evaluate('suntrainReplay.filters.carriers[0]') == 'KE'
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]});dash_clientside.set_props("replay-airports",{value:["GMP"]})')
    page.wait_for_function('!suntrainReplay.filters.carriers.length && suntrainReplay.filters.airports[0]==="GMP" && suntrainReplay.filtered.length')
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="GMP"))')
    page.get_by_role('button', name='Expand board', exact=True).click()
    next_page = page.get_by_role('button', name='Next', exact=True)
    assert next_page.is_enabled()
    next_page.click()
    assert page.evaluate('suntrainReplay.departures.page') == 1
    page.get_by_role('button', name='Previous', exact=True).click()
    assert page.evaluate('suntrainReplay.departures.page') == 0
    page.screenshot(path='.cache/south-korea-flights-desktop.png')
    page.locator('[data-event="destinations"]').click()
    page.wait_for_function('suntrainReplay.departures.destinationRows.length>0')
    page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length')
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
    features = page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.end)')
    assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)') == features
    for theme in ['light', 'dark', 'sunrise', 'blueprint', 'heritage']:
        page.locator('#theme-toggle').select_option(theme)
    page.locator('#theme-toggle').select_option('dark')
    page.locator('#language-select').select_option('id')
    page.wait_for_function('document.documentElement.lang==="id"')
    assert 'Tujuan' in page.locator('#replay-departures').inner_text()
    assert 'KST' in page.locator('#replay-clock-date').inner_text()
    assert 'GMT+9' not in page.locator('#replay-departures').inner_text()
    page.set_viewport_size({'width':390, 'height':844})
    page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
    page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='.cache/south-korea-flights-mobile.png')
    page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("76")')
    assert len(downloads) == count
    assert not errors, errors
    print('KST, USD, five airport boards, airline filters, fullscreen/back, pagination, destinations, frequency, themes, Indonesian, mobile and cache reuse passed', flush=True)
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"seoul"})')
    page.wait_for_function('suntrainReplay.day.city==="seoul" && !suntrainReplay.loading && suntrainReplay.filtered.length', timeout=120000)
    assert page.evaluate('suntrainReplay.day.replay_kind') == 'transit'
    assert not page.locator('#replay-flight-controls').is_visible()
    assert 'KST' in page.locator('#replay-clock-date').inner_text()
    assert not errors, errors
    print('Existing Seoul transit remains separate and functional', flush=True)
    browser.close()
