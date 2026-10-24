"""Exercise captured MYR fares in the shared flight map and airport boards."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8866'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"malaysia_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="malaysia_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.schedule.fare_context.currency')=='MYR'
    assert page.evaluate('suntrainReplay.day.stations.filter(a=>["KUL","SZB"].includes(a.code)).length')==2
    count=len(downloads)
    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="KUL"))')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="KUL" && suntrainReplay.departures.services===suntrainReplay.filtered')
    assert page.locator('.departure-fare').count()>0
    assert 'MYR' in page.locator('#replay-departures').inner_text()
    assert 'MYT' in page.locator('#replay-departures').inner_text()
    assert page.evaluate('suntrainReplay.filtered.every(s=>s.stops.some(stop=>suntrainReplay.day.stations[stop[0]].code==="KUL"))')
    page.get_by_role('button',name='Expand board',exact=True).click()
    page.locator('.departure-row').filter(has_text='MYR').first.click()
    assert 'MYR' in page.locator('.replay-flight-fare').inner_text()
    assert '1 adult' in page.locator('#replay-details').inner_text()
    assert page.locator('[data-fare-captured-at]').count()==1
    before=page.evaluate('suntrainReplay.now')
    page.locator('#language-select').select_option('id')
    assert 'Dewasa' in page.locator('#replay-details').inner_text() or 'dewasa' in page.locator('#replay-details').inner_text()
    assert 'Dicatat:' in page.locator('#replay-details').inner_text()
    assert page.evaluate('suntrainReplay.now')==before
    page.locator('#language-select').select_option('en')
    page.get_by_role('button',name='Back to airport board',exact=True).click()
    page.locator('[data-event="arrival"]').click()
    assert page.evaluate('suntrainReplay.departures.calls.length && suntrainReplay.departures.calls.every(c=>c.event==="arrival")')
    page.screenshot(path='.cache/malaysia-flights-board-desktop.png')
    page.evaluate('suntrainReplay.departures.close();suntrainReplay.select(suntrainReplay.filtered.find(s=>!s.price).id)')
    assert page.locator('.replay-flight-fare').inner_text()=='Price unavailable'
    assert page.locator('[data-fare-captured-at]').count()==0
    page.locator('#language-select').select_option('id')
    assert page.locator('.replay-flight-fare').inner_text()=='Harga tidak tersedia'
    page.locator('#language-select').select_option('en')
    print('Exact airports, priced and unpriced previews, local clocks, translation and fullscreen return passed',flush=True)

    page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="KCH"))')
    page.wait_for_function('suntrainReplay.filters.airports[0]==="KCH" && suntrainReplay.departures.services===suntrainReplay.filtered')
    assert page.evaluate('suntrainReplay.departures.timezone')=='Asia/Kuching'
    assert 'MYT' in page.locator('#replay-departures').inner_text()
    page.locator('[data-event="destinations"]').click()
    page.wait_for_function('suntrainReplay.departures.destinationRows.length>0')
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:["AK"]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('suntrainReplay.frequencyView && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="AK")')
    features=page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.end)')
    assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        page.locator('#theme-toggle').select_option(theme)
        assert page.evaluate('JSON.stringify(suntrainReplay.frequencyFeatures)')==features
    assert len(downloads)==count
    page.locator('#theme-toggle').select_option('dark')
    page.evaluate('suntrainReplay.seek(suntrainReplay.day.start)')
    page.locator('[data-event="departure"]').click()
    page.evaluate('suntrainReplay.departures.setExpanded(true)')
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(300)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert 'MYR' in page.locator('#replay-departures').inner_text()
    page.screenshot(path='.cache/malaysia-flights-board-mobile.png')
    print('East Malaysia, destinations, airline filtering, frequency counts, themes and mobile passed',flush=True)
    assert not errors,errors
    browser.close()
