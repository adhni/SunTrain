"""Remaining ASEAN views, country clocks, exact airports and shared network."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from dashboard.asean_flights import PROFILES

AUDIT=Path('.cache/asean-flights-audit');AUDIT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8878'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
    for country,profile in PROFILES.items():
        city=profile['slug']+'_flights'
        page.evaluate('(c)=>dash_clientside.set_props("replay-city",{value:c})',city)
        page.wait_for_function('(c)=>window.suntrainReplay?.day?.city===c && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',arg=city,timeout=120000)
        assert page.evaluate('suntrainReplay.day.timezone')==profile['zone']
        assert page.evaluate('suntrainReplay.filters.flightScope')==profile['default_scope']
        assert profile['label'] in page.locator('#replay-clock-date').inner_text()
        assert page.locator('#replay-flight-scope-field').is_visible()==profile['domestic']
        assert not page.evaluate('suntrainReplay.day.stations.some(a=>["PNH","REP"].includes(a.code))')
        if profile['domestic']:
            page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"domestic"})')
            page.wait_for_function('suntrainReplay.filters.flightScope==="domestic"')
            assert page.evaluate('suntrainReplay.filtered.every(s=>s.flight_scope==="domestic")')
            if country in {'KH','TL'}:assert not page.evaluate('suntrainReplay.filtered.length')
            page.evaluate('dash_clientside.set_props("replay-flight-scope",{value:"international"})')
            page.wait_for_function('suntrainReplay.filters.flightScope==="international" && suntrainReplay.filtered.length')
        # Use an actually captured departure airport; no assumptions about service.
        code=page.evaluate('(c)=>suntrainReplay.day.stations.find(a=>a.country===c && suntrainReplay.filtered.some(s=>suntrainReplay.day.stations[s.stops[0][0]].code===a.code)).code',country)
        page.evaluate('(code)=>{dash_clientside.set_props("replay-airport-direction",{value:"departures"});dash_clientside.set_props("replay-airports",{value:[code]})}',code)
        page.wait_for_function('(code)=>suntrainReplay.filtered.length && suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        carrier=page.evaluate('suntrainReplay.filtered[0].carrier')
        page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
        page.wait_for_function('(c)=>suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
        page.evaluate('(code)=>{dash_clientside.set_props("replay-carriers",{value:[]});suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('suntrainReplay.departures.calls.length && suntrainReplay.departures.services===suntrainReplay.filtered')
        assert profile['label'] in page.locator('#replay-departures').inner_text()
        page.get_by_role('button',name='Expand board',exact=True).click()
        if page.locator('.departure-row').filter(has_text='USD').count():
            before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='USD').first.click()
            assert page.evaluate('suntrainReplay.now')==before
            assert 'USD' in page.locator('.replay-flight-fare').inner_text()
            assert profile['label'] in page.locator('[data-fare-captured-at]').inner_text()
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
        page.locator('[data-event="arrival"]').click()
        page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops.at(-1)[0]].code===code)',arg=code)
        page.locator('[data-event="destinations"]').click();page.wait_for_function('suntrainReplay.departures.destinationRows.length')
        page.screenshot(path=str(AUDIT/f'{country}-board.png'))
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        page.screenshot(path=str(AUDIT/f'{country}-mobile.png'))
        page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
        assert 'Waktu bandara' in page.locator('#replay-departures').inner_text()
        page.locator('#language-select').select_option('en')
        page.evaluate('suntrainReplay.departures.close();dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
        page.wait_for_function('!suntrainReplay.filters.airports.length && suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length')
        assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
        page.set_viewport_size({'width':1440,'height':1100})
        page.screenshot(path=str(AUDIT/f'{country}-frequency.png'))
        for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
        page.locator('#theme-toggle').select_option('dark')
        page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})')
        page.wait_for_function('!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
        page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]})')
        page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length')
        print(country,city,profile['label'],'boards, quotes, filters, fullscreen/mobile, Indonesian, themes and frequency passed',flush=True)
    page.evaluate('dash_clientside.set_props("replay-city",{value:"international_network"})')
    page.wait_for_function('suntrainReplay.day.city==="international_network" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    for country in PROFILES:
        page.evaluate('(c)=>{dash_clientside.set_props("replay-from-countries",{value:[c]});dash_clientside.set_props("replay-to-countries",{value:[]})}',country)
        page.wait_for_function('(c)=>suntrainReplay.filters.fromCountries[0]===c && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country===c)',arg=country)
        print(country,'UTC network filter passed',flush=True)
    assert not errors,errors
    browser.close()
