"""Cached Europe–Americas connections, original EUR prices and independent regional views."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

AUDIT=Path('.cache/europe-americas-flights-audit')
AUDIT.mkdir(parents=True,exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8887'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    places=page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places)')
    assert all(any(p['id']==city for p in places) for city in ['europe_americas_flights','europe_flights','americas_flights'])
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"europe_americas_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="europe_americas_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
    assert page.evaluate('suntrainReplay.day.stations.length')==72
    assert page.evaluate('suntrainReplay.filters.flightScope')=='international'
    assert not page.locator('#replay-flight-scope-field').is_visible()
    assert page.evaluate('suntrainReplay.graph.getBounds().contains([-122.4,37.6]) && suntrainReplay.graph.getBounds().contains([16.6,48.1])')
    total=page.evaluate('suntrainReplay.filtered.length');count=len(downloads)
    assert total==748
    page.screenshot(path=str(AUDIT/'map.png'))
    print('Europe–Americas map and complete archive loaded',flush=True)
    for a,b in [('GB','US'),('US','GB'),('FR','US'),('US','FR'),('ES','BR'),('BR','ES')]:
        expected=page.evaluate('([a,b])=>suntrainReplay.day.services.filter(s=>suntrainReplay.day.stations[s.stops[0][0]].country===a && suntrainReplay.day.stations[s.stops[1][0]].country===b).length',[a,b])
        assert expected>0,(a,b)
        page.evaluate('([a,b])=>{dash_clientside.set_props("replay-from-countries",{value:[a]});dash_clientside.set_props("replay-to-countries",{value:[b]})}',[a,b])
        page.wait_for_function('([a,b,n])=>suntrainReplay.filters.fromCountries[0]===a && suntrainReplay.filters.toCountries[0]===b && suntrainReplay.filtered.length===n',arg=[a,b,expected])
    page.evaluate('dash_clientside.set_props("replay-from-countries",{value:[]});dash_clientside.set_props("replay-to-countries",{value:[]})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.fromCountries.length && !suntrainReplay.filters.toCountries.length && suntrainReplay.filtered.length===n',arg=total)
    for carrier in ['BA','UA','VS','LA','KL']:
        page.evaluate('(carrier)=>dash_clientside.set_props("replay-carriers",{value:[carrier]})',carrier)
        page.wait_for_function('(carrier)=>suntrainReplay.filters.carriers[0]===carrier && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===carrier)',arg=carrier)
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.carriers.length && suntrainReplay.filtered.length===n',arg=total)
    page.evaluate('dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
    print('Cross-region countries, scopes and airline filters passed',flush=True)
    # Every exact airport is selectable, including separate city airports and both hemispheres.
    airports=json.loads(Path('data/sources/europe_americas_flights_routes.json').read_text())['airports']
    for airport in airports:
        code=airport['code'];zone=airport.get('replay_timezone',airport['timezone'])
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('(zone)=>suntrainReplay.departures.timezone===zone && suntrainReplay.departures.services===suntrainReplay.filtered',arg=zone)
        for mode,direction in [('arrival','arrivals'),('departure','departures')]:
            page.locator(f'[data-event="{mode}"]').click()
            page.wait_for_function('([code,direction])=>suntrainReplay.filters.airportDirection===direction && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[direction==="arrivals"?1:0][0]].code===code)',arg=[code,direction])
        if code=='LHR':
            page.get_by_role('button',name='Expand board',exact=True).click()
            page.get_by_role('button',name='Next',exact=True).click();assert page.evaluate('suntrainReplay.departures.page')==1
            page.get_by_role('button',name='Previous',exact=True).click()
            before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='EUR').first.click()
            assert page.evaluate('suntrainReplay.now')==before
            assert 'EUR' in page.locator('.replay-flight-fare').inner_text()
            page.get_by_role('button',name='Back to airport board',exact=True).click()
            assert page.evaluate('suntrainReplay.departures.expanded')
            page.locator('[data-event="destinations"]').click()
            page.wait_for_function('suntrainReplay.departures.destinationRows.length')
            page.screenshot(path=str(AUDIT/'destinations.png'))
            page.locator('[data-event="departure"]').click()
            for theme in ['light','dark','sunrise','blueprint','heritage']:
                page.locator('#theme-toggle').select_option(theme)
            page.locator('#language-select').select_option('id')
            page.wait_for_function('document.documentElement.lang==="id"')
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(AUDIT/'mobile.png'))
            page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
        page.evaluate('suntrainReplay.departures.close()')
        print(code,'exact airport board passed',flush=True)
    page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.airports.length && suntrainReplay.frequencyView && suntrainReplay.filtered.length===n && suntrainReplay.frequencyFeatures.length',arg=total)
    assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainReplay.filtered.length')
    assert len(downloads)==count
    page.screenshot(path=str(AUDIT/'frequency.png'))
    for city,expected in [('europe_flights',None),('americas_flights',11783),('united_states_flights',9668),('south_america_flights',1629),('australia_flights',None),('melbourne',None)]:
        page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
        page.wait_for_function('(city)=>suntrainReplay.day.city===city && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
        if expected:
            assert page.evaluate('suntrainReplay.day.services.length')==expected
    assert not errors,errors
    print(f'{total} services: cross-Americas filters, all 72 airport boards, EUR, frequency, fullscreen/back, themes, Indonesian, mobile and existing regional/transit regressions passed',flush=True)
    browser.close()
