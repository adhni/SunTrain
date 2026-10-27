"""Africa connections, original currencies and independent regional views."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

AUDIT=Path('.cache/africa-expansion-audit')
AUDIT.mkdir(parents=True,exist_ok=True)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True)
    errors=[];downloads=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8888'),wait_until='domcontentloaded')
    page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
    places=page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places)')
    assert all(any(p['id']==city for p in places) for city in ['africa_flights','europe_flights','americas_flights'])
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"africa_flights"})')
    page.wait_for_function('window.suntrainReplay?.day?.city==="africa_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
    assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
    assert page.evaluate('suntrainReplay.day.stations.length')==len(json.loads(Path('data/sources/africa_flights_routes.json').read_text())['airports'])
    assert page.evaluate('suntrainReplay.filters.flightScope')=='both'
    assert page.locator('#replay-flight-scope-field').is_visible()
    assert page.evaluate('suntrainReplay.day.regional_start_view && Math.abs(suntrainReplay.graph.getCenter().lng-20)<10 && Math.abs(suntrainReplay.graph.getCenter().lat)<15')
    total=page.evaluate('suntrainReplay.filtered.length');count=len(downloads)
    assert total>700
    page.screenshot(path=str(AUDIT/'map.png'))
    print('Africa map and captured snapshot loaded',flush=True)
    for scope in ['domestic','international','both']:
        page.evaluate('(scope)=>dash_clientside.set_props("replay-flight-scope",{value:scope})',scope)
        page.wait_for_function('(scope)=>suntrainReplay.filters.flightScope===scope && suntrainReplay.filtered.length && (scope==="both" || suntrainReplay.filtered.every(s=>s.flight_scope===scope))',arg=scope)
    for a,b in [('NG','NG'),('ET','ET'),('ZA','ZA'),('DZ','DZ'),('ET','KE'),('KE','GH')]:
        expected=page.evaluate('([a,b])=>suntrainReplay.day.services.filter(s=>suntrainReplay.day.stations[s.stops[0][0]].country===a && suntrainReplay.day.stations[s.stops[1][0]].country===b).length',[a,b])
        if not expected:continue
        page.evaluate('([a,b])=>{dash_clientside.set_props("replay-from-countries",{value:[a]});dash_clientside.set_props("replay-to-countries",{value:[b]})}',[a,b])
        page.wait_for_function('([a,b,n])=>suntrainReplay.filters.fromCountries[0]===a && suntrainReplay.filters.toCountries[0]===b && suntrainReplay.filtered.length===n',arg=[a,b,expected])
    page.evaluate('dash_clientside.set_props("replay-from-countries",{value:[]});dash_clientside.set_props("replay-to-countries",{value:[]})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.fromCountries.length && !suntrainReplay.filters.toCountries.length && suntrainReplay.filtered.length===n',arg=total)
    for carrier in ['ET','KQ','P4']:
        page.evaluate('(carrier)=>dash_clientside.set_props("replay-carriers",{value:[carrier]})',carrier)
        page.wait_for_function('(carrier)=>suntrainReplay.filters.carriers[0]===carrier && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===carrier)',arg=carrier)
    page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
    page.wait_for_function('(n)=>!suntrainReplay.filters.carriers.length && suntrainReplay.filtered.length===n',arg=total)
    page.evaluate('dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
    page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"')
    print('Cross-region countries, scopes and airline filters passed',flush=True)
    # Every exact airport is selectable, including separate city airports and both hemispheres.
    airports=json.loads(Path('data/sources/africa_flights_routes.json').read_text())['airports']
    selected=set(json.loads(Path('data/sources/africa_flights_routes.json').read_text())['launch_airports'])|{'HLA','PLZ','PHC','KAN','DIR','GDQ','KIS','JRO','FBM','LFW','TNR'}
    for airport in [a for a in airports if a['code'] in selected]:
        code=airport['code'];zone=airport.get('replay_timezone',airport['timezone'])
        page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
        page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
        page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
        page.wait_for_function('(zone)=>suntrainReplay.departures.timezone===zone && suntrainReplay.departures.services===suntrainReplay.filtered',arg=zone)
        for mode,direction in [('arrival','arrivals'),('departure','departures')]:
            page.locator(f'[data-event="{mode}"]').click()
            page.wait_for_function('([code,direction])=>suntrainReplay.filters.airportDirection===direction && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[direction==="arrivals"?1:0][0]].code===code)',arg=[code,direction])
        if code=='ADD':
            page.get_by_role('button',name='Expand board',exact=True).click()
            page.get_by_role('button',name='Next',exact=True).click();assert page.evaluate('suntrainReplay.departures.page')==1
            page.get_by_role('button',name='Previous',exact=True).click()
            before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='USD').first.click()
            assert page.evaluate('suntrainReplay.now')==before
            assert 'USD' in page.locator('.replay-flight-fare').inner_text()
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
    page.evaluate('dash_clientside.set_props("replay-display",{value:[]})')
    page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length===0')
    page.evaluate('suntrainReplay.metroView()')
    assert page.evaluate('Math.abs(suntrainReplay.graph.getCenter().lng-20)<10')
    for city,expected in [('europe_flights',None),('americas_flights',11783),('united_states_flights',9668),('south_america_flights',1629),('australia_flights',None),('melbourne',None)]:
        page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
        page.wait_for_function('(city)=>suntrainReplay.day.city===city && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
        if expected:
            assert page.evaluate('suntrainReplay.day.services.length')==expected
    assert not errors,errors
    print(f'{total} services: country filters, starter and expanded airport boards, original currencies, frequency, fullscreen/back, themes, Indonesian, mobile and existing regional/transit regressions passed',flush=True)
    browser.close()
