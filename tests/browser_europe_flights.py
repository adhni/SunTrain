"""Both European brands, real-country scopes, local boards and EUR mobile fares."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True);errors=[];downloads=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
 page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8879'),wait_until='domcontentloaded')
 page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
 page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:"europe_flights"})')
 page.wait_for_function('window.suntrainReplay?.day?.city==="europe_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
 assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
 assert page.evaluate('suntrainReplay.filters.flightScope')=='both' and not page.evaluate('suntrainReplay.frequencyView')
 assert page.locator('#replay-country-controls').is_visible() and page.locator('#replay-flight-scope-field').is_visible()
 assert 'UTC' in page.locator('#replay-clock-date').inner_text()
 page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
 page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("monthly route timetables captured")')
 assert 'dated flight searches captured' in page.locator('#city-overview-content').inner_text()
 page.locator('#language-select').select_option('id');page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("jadwal rute bulanan tersimpan")')
 page.locator('#language-select').select_option('en');page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
 page.wait_for_function('suntrainReplay.active && suntrainReplay.mapReady && !suntrainReplay.loading')
 assert page.evaluate('new Set(suntrainReplay.filtered.map(s=>s.flight_brand)).size')==2
 assert page.evaluate('suntrainReplay.day.stations.some(a=>a.code==="STN") && suntrainReplay.day.stations.some(a=>a.code==="LGW")')
 count=len(downloads);total=page.evaluate('suntrainReplay.filtered.length')
 page.evaluate('dash_clientside.set_props("replay-display",{value:["routes"]})');page.wait_for_function('!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
 page.evaluate('dash_clientside.set_props("replay-display",{value:["routes","stations"]})');page.wait_for_function('suntrainReplay.graph.getSource("replay-stations")._data.features.length')
 page.screenshot(path='.cache/europe-flights-audit/map.png')
 for brand in ['ryanair','easyjet']:
  page.evaluate('(brand)=>dash_clientside.set_props("replay-carriers",{value:["brand:"+brand]})',brand)
  page.wait_for_function('(brand)=>suntrainReplay.filters.carriers[0]==="brand:"+brand && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.flight_brand===brand)',arg=brand)
  assert page.evaluate('new Set(suntrainReplay.filtered.map(s=>s.color)).size')==1
 page.evaluate('dash_clientside.set_props("replay-carriers",{value:["RK"]})')
 page.wait_for_function('suntrainReplay.filters.carriers[0]==="RK" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier==="RK")')
 page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})');page.wait_for_function('!suntrainReplay.filters.carriers.length')
 for scope in ['domestic','international','both']:
  page.evaluate('(scope)=>dash_clientside.set_props("replay-flight-scope",{value:scope})',scope)
  page.wait_for_function('(scope)=>suntrainReplay.filters.flightScope===scope && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>scope==="both" || s.flight_scope===scope)',arg=scope)
  assert page.evaluate('(scope)=>suntrainReplay.filtered.every(s=>scope==="both" || (suntrainReplay.day.stations[s.stops[0][0]].country===suntrainReplay.day.stations[s.stops[1][0]].country)===(scope==="domestic"))',scope)
 for origin,destination in [('GB','IE'),('GB','MA'),('IT','IT')]:
  page.evaluate('([a,b])=>{dash_clientside.set_props("replay-from-countries",{value:[a]});dash_clientside.set_props("replay-to-countries",{value:[b]})}',[origin,destination])
  page.wait_for_function('([a,b])=>suntrainReplay.filters.fromCountries[0]===a && suntrainReplay.filters.toCountries[0]===b && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country===a && suntrainReplay.day.stations[s.stops[1][0]].country===b)',arg=[origin,destination])
 page.evaluate('dash_clientside.set_props("replay-from-countries",{value:[]});dash_clientside.set_props("replay-to-countries",{value:[]});dash_clientside.set_props("replay-airport-direction",{value:"departures"})')
 page.wait_for_function('!suntrainReplay.filters.fromCountries.length && !suntrainReplay.filters.toCountries.length && suntrainReplay.filters.airportDirection==="departures"')
 for code in ['STN','LGW','DUB','BGY','GVA','BSL']:
  page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',code)
  page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].code===code)',arg=code)
  page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',code)
  page.wait_for_function('suntrainReplay.departures.services===suntrainReplay.filtered && suntrainReplay.departures.calls.length')
  if code=='STN':
   page.get_by_role('button',name='Expand board',exact=True).click();page.get_by_role('button',name='Next',exact=True).click();assert page.evaluate('suntrainReplay.departures.page')==1
   page.get_by_role('button',name='Previous',exact=True).click();before=page.evaluate('suntrainReplay.now');page.locator('.departure-row').filter(has_text='EUR').first.click()
   assert page.evaluate('suntrainReplay.now')==before and 'EUR' in page.locator('.replay-flight-fare').inner_text()
   page.get_by_role('button',name='Back to airport board',exact=True).click();assert page.evaluate('suntrainReplay.departures.expanded')
  if code=='GVA':
   assert page.evaluate('suntrainReplay.departures.timezone')=='Europe/Zurich'
   assert 'GMT+1' in page.locator('#replay-departures').inner_text() and 'UTC' in page.locator('#replay-departures').inner_text()
   page.get_by_role('button',name='Expand board',exact=True).click();page.screenshot(path='.cache/europe-flights-audit/board.png')
   for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
   page.locator('#theme-toggle').select_option('dark');page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
   assert 'Keberangkatan' in page.locator('#replay-departures').inner_text()
   page.set_viewport_size({'width':390,'height':844});page.wait_for_function('document.querySelector(".replay-detail-card").getBoundingClientRect().height===innerHeight')
   page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path='.cache/europe-flights-audit/mobile.png');page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
  page.locator('[data-event="arrival"]').click();page.wait_for_function('(code)=>suntrainReplay.filters.airportDirection==="arrivals" && suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[1][0]].code===code)',arg=code)
  page.locator('[data-event="destinations"]').click();page.wait_for_function('suntrainReplay.departures.destinationRows.length')
  page.locator('[data-event="departure"]').click();page.wait_for_function('suntrainReplay.filters.airportDirection==="departures"');page.evaluate('suntrainReplay.departures.close()');print(code,'board passed',flush=True)
 page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
 page.wait_for_function('(n)=>!suntrainReplay.filters.airports.length && suntrainReplay.frequencyView && suntrainReplay.filtered.length===n && suntrainReplay.frequencyFeatures.length',arg=total)
 assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
 assert len(downloads)==count
 page.evaluate('dash_clientside.set_props("replay-city",{value:"nepal_flights"})')
 page.wait_for_function('suntrainReplay.day.city==="nepal_flights" && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
 assert page.evaluate('suntrainReplay.filters.flightScope')=='domestic' and not page.evaluate('suntrainReplay.day.flight_brands')
 assert not errors,errors
 print(f'{total} records: brand/carrier filters, actual-country scopes, UTC/local clocks, EUR, boards, mobile, themes, Indonesian and existing-country reset passed',flush=True);browser.close()
