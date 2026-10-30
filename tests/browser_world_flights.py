"""Global union, lazy geometry, filters, local boards, fares and view transitions."""
import json
import gzip
import os
from collections import Counter
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path(os.environ.get('SUNTRAIN_WORLD_TEST_OUTPUT','.cache/world-flights'));OUT.mkdir(parents=True,exist_ok=True)
with gzip.open(os.environ.get('SUNTRAIN_WORLD_FLIGHTS_REFERENCE','data/reference/world_flights/2026-11-02.json.gz'),'rt') as stream:
 expected=json.load(stream)
TOTAL=len(expected['flights']);SCOPES=Counter(f['flight_scope'] for f in expected['flights'])
ROUTES=expected['metadata']['coverage']['routes_returned']
ACTIVE_1500=sum(f['departure']<=1793577600+15*3600<=f['arrival'] for f in expected['flights'])
CAMERA='({center:suntrainReplay.graph.getCenter().toArray().map(n=>+n.toFixed(6)),zoom:+suntrainReplay.graph.getZoom().toFixed(6)})'
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8898'),wait_until='domcontentloaded')
 page.wait_for_function('window.suntrainHome?.ready')
 assert page.evaluate('suntrainHome.places.find(p=>p.id==="world_flights").home_marker') is False
 assert page.locator('#home-world-flights').is_visible()
 page.locator('#home-world-flights').click()
 def ready(city):
  page.wait_for_function('(city)=>suntrainReplay.day?.city===city && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length===suntrainReplay.day.services.length',arg=city,timeout=120000)
  page.wait_for_timeout(200)
 def load(city):
  page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city);ready(city)
 def set_filter(id,value,condition):
  page.evaluate('([id,value])=>dash_clientside.set_props(id,{value})',[id,value]);page.wait_for_function(condition)
 def clear():
  page.evaluate('''()=>{suntrainReplay.departures.close();for(const id of ['replay-carriers','replay-airports','replay-lines','replay-from-countries','replay-to-countries'])dash_clientside.set_props(id,{value:[]});dash_clientside.set_props('replay-airport-direction',{value:'both'});dash_clientside.set_props('replay-flight-scope',{value:'both'});}''')
  page.wait_for_function('(n)=>suntrainReplay.filtered.length===n',arg=TOTAL)
 ready('world_flights')
 print('World opened.',flush=True)
 assert page.locator('#replay-clock').inner_text()=='10:00:00'
 assert page.evaluate('suntrainReplay.playing') is False
 assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
 assert page.evaluate('suntrainReplay.filtered.length')==TOTAL
 assert page.evaluate('suntrainReplay.day._generatedFlightPaths')<ROUTES
 assert f'{TOTAL:,}' in page.locator('#replay-world-coverage').inner_text()
 assert 'Combined captures' in page.locator('#replay-flight-key').inner_text()
 original=page.evaluate(CAMERA);now=page.evaluate('suntrainReplay.now')
 page.locator('#replay-map').screenshot(path=str(OUT/'global-1000.png'))
 page.evaluate('suntrainReplay.seek(suntrainReplay.day.start+15*3600)')
 assert page.evaluate('suntrainReplay.activePositions.length')==ACTIVE_1500
 page.locator('#replay-map').screenshot(path=str(OUT/'global-peak.png'))
 # Near the dateline, source transfer is limited to viewport+12px, counts use centres.
 page.evaluate('()=>{suntrainReplay.graph.jumpTo({center:[180,0],zoom:3});suntrainReplay.paint(true);}')
 page.wait_for_timeout(400)
 assert page.evaluate('''()=>{const r=suntrainReplay,features=r.graph.getSource('replay-trains')._data.features,inside=suntrainFlights.viewport(r.graph,12);return features.length<r.activePositions.length && features.every(f=>inside(f.geometry.coordinates)) && r.visibleFlights===suntrainFlights.visibleCount(r.graph,r.activePositions) && new Set(features.map(f=>f.properties.id)).size===features.length;}''')
 page.locator('#replay-map').screenshot(path=str(OUT/'pacific-viewport.png'))
 # Nearby planes and airport codes request their artwork lazily, with nearest picking.
 page.evaluate('()=>{suntrainReplay.graph.jumpTo({center:[8,50],zoom:5.5});}')
 page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-planes"]}).length>0')
 page.wait_for_function('suntrainReplay.graph.queryRenderedFeatures({layers:["replay-airport-labels"]}).length>0')
 hit=page.evaluate('''()=>{const r=suntrainReplay;for(const f of r.graph.queryRenderedFeatures({layers:['replay-planes']})) {
  const p=suntrainFlights.project(r.graph,f.geometry.coordinates);p.x+=5;
  const hit=r.vehicleNear(p);if(hit && !r.graph.queryRenderedFeatures(p,{layers:['replay-airport-labels']}).length)return {point:p,id:hit.properties.id};}}''')
 assert hit
 page.evaluate('(hit)=>{const m=suntrainReplay.graph,ll=m.unproject([hit.point.x,hit.point.y]);m.fire("click",{point:m.project(ll),lngLat:ll});}',hit)
 page.wait_for_function('(id)=>suntrainReplay.selected?.id===id',arg=hit['id'])
 page.wait_for_function('suntrainReplay.graph.hasImage(suntrainFlights.planeKey(suntrainReplay.selected))')
 assert page.evaluate('suntrainReplay.graph.getLayoutProperty("replay-selected-flight","icon-size")*32')==22
 assert page.evaluate('suntrainReplay.graph.getSource("replay-selected-route")._data.features.length')==1
 page.locator('#replay-map').screenshot(path=str(OUT/'nearby-planes.png'))
 page.locator('#replay-close-details').click()
 page.locator('#replay-melbourne').click();page.wait_for_timeout(150)
 assert page.evaluate(CAMERA)==original
 now=page.evaluate('suntrainReplay.now')
 set_filter('replay-from-countries',['AU'],'suntrainReplay.filters.fromCountries[0]==="AU"')
 set_filter('replay-to-countries',['US'],'suntrainReplay.filters.toCountries[0]==="US"')
 assert page.evaluate('suntrainReplay.filtered.length>0 && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country==="AU" && suntrainReplay.day.stations[s.stops[1][0]].country==="US")')
 assert page.evaluate(CAMERA)==original and page.evaluate('suntrainReplay.now')==now
 page.locator('#replay-fit').click();page.wait_for_timeout(250)
 assert page.evaluate(CAMERA)!=original
 page.locator('#replay-melbourne').click();page.wait_for_timeout(200)
 assert page.evaluate(CAMERA)==original
 clear()
 for scope,count in [('domestic',SCOPES['domestic']),('international',SCOPES['international']),('both',TOTAL)]:
  set_filter('replay-flight-scope',scope,f'suntrainReplay.filters.flightScope==="{scope}" && suntrainReplay.filtered.length==={count}')
 if 'world_international_expansion' in expected['metadata']['member_views']:
  set_filter('replay-from-countries',['ES'],'suntrainReplay.filters.fromCountries[0]==="ES"')
  set_filter('replay-to-countries',['CU'],'suntrainReplay.filters.toCountries[0]==="CU"')
  assert page.evaluate('suntrainReplay.filtered.length>0 && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country==="ES" && suntrainReplay.day.stations[s.stops[1][0]].country==="CU")')
  assert page.evaluate(CAMERA)==original
  clear()
 if 'data/reference/south_america_domestic/2026-11-02.json.gz' in expected['metadata']['inputs']:
  airport_country={a['code']:a['country'] for a in expected['airports']}
  for country in ['AR','PE','CL']:
   count=sum(airport_country[f['origin']]==country and airport_country[f['destination']]==country for f in expected['flights'])
   assert count>0
   set_filter('replay-from-countries',[country],f'suntrainReplay.filters.fromCountries[0]==="{country}"')
   set_filter('replay-to-countries',[country],f'suntrainReplay.filters.toCountries[0]==="{country}" && suntrainReplay.filtered.length==={count}')
   assert page.evaluate(CAMERA)==original
  clear()
 if any(f['origin']=='HND' and f['destination']=='LHR' and f['number']=='NH211' for f in expected['flights']):
  set_filter('replay-from-countries',['JP'],'suntrainReplay.filters.fromCountries[0]==="JP"')
  set_filter('replay-to-countries',['GB'],'suntrainReplay.filters.toCountries[0]==="GB"')
  assert page.evaluate('suntrainReplay.filtered.some(s=>s.number==="NH211")')
  assert page.evaluate(CAMERA)==original
  clear()
 winter=[f for f in expected['flights'] if f['origin']=='BOD' and f['destination']=='LGW']
 if winter:
  set_filter('replay-from-countries',['FR'],'suntrainReplay.filters.fromCountries[0]==="FR"')
  set_filter('replay-to-countries',['GB'],'suntrainReplay.filters.toCountries[0]==="GB"')
  numbers=sorted(f['number'] for f in winter)
  assert page.evaluate('suntrainReplay.filtered.filter(s=>s.route_id==="BOD-LGW").map(s=>s.number).sort()')==numbers
  assert page.evaluate(CAMERA)==original
  clear()
 set_filter('replay-carriers',['brand:lufthansa'],'suntrainReplay.filters.carriers[0]==="brand:lufthansa"')
 assert page.evaluate('suntrainReplay.filtered.length>0 && suntrainReplay.filtered.every(s=>s.flight_brand==="lufthansa")')
 clear()
 # Boards own only in-window events and use the airport's preserved local clock.
 boards=[('LHR','Europe/London'),('YVR','Etc/GMT+7'),('SYD','Australia/Sydney')]
 if winter:boards.extend([('BOD','Europe/Paris'),('SXB','Europe/Paris')])
 if 'data/reference/south_america_domestic/2026-11-02.json.gz' in expected['metadata']['inputs']:
  boards.extend([('BRC','America/Argentina/Salta'),('CUZ','America/Lima'),('BBA','America/Coyhaique')])
 if 'world_international_expansion' in expected['metadata']['member_views']:
  boards.extend([('HAV','America/Havana'),('BDA','Atlantic/Bermuda')])
 for code,zone in boards:
  page.evaluate('(code)=>{const r=suntrainReplay;r.seek(r.day.start);r.departures.open(r.day.stations.findIndex(a=>a.code===code));}',code)
  page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code && suntrainReplay.departures.services===suntrainReplay.filtered',arg=code)
  assert page.evaluate('suntrainReplay.departures.timezone')==zone, (code,zone)
  assert page.evaluate('suntrainReplay.departures.calls.every(c=>c.at>=suntrainReplay.day.start && c.at<suntrainReplay.day.end)')
  assert page.evaluate(CAMERA)==original
  for event in ['arrival','departure','destinations']:
   page.locator(f'[data-event="{event}"]').click()
   page.wait_for_function('(event)=>suntrainReplay.departures.event===event',arg=event)
  assert page.evaluate('suntrainReplay.departures.destinationRows.length')>0
  page.get_by_role('button',name='Expand board',exact=True).click()
  page.locator('[data-event="departure"]').click()
  assert page.evaluate('suntrainReplay.departures.expanded')
  if code=='LHR':page.screenshot(path=str(OUT/'heathrow-board.png'))
  if code=='BOD':page.screenshot(path=str(OUT/'bordeaux-board.png'))
  page.locator('.departure-row').first.click()
  page.get_by_role('button',name='Back to airport board',exact=True).click()
  assert page.evaluate('suntrainReplay.departures.expanded')
  page.evaluate('suntrainReplay.departures.close()')
 clear()
 print('Local boards passed.',flush=True)
 # Multiple currency quotes and aircraft disagreement are visible without conversion.
 page.evaluate('''()=>{const r=suntrainReplay,s=r.filtered.find(s=>new Set(s.fare_quotes?.map(q=>q.currency)).size>1);r.select(s.id);}''')
 page.locator('.replay-captured-quotes').evaluate('(e)=>{e.open=true;}')
 assert 'USD' in page.locator('.replay-captured-quotes').inner_text()
 assert 'No currency conversion' in page.locator('.replay-captured-quotes').inner_text()
 before=page.evaluate('({now:suntrainReplay.now,filters:suntrainReplay.filterSignature})')
 page.locator('#language-select').select_option('id')
 assert 'Tanpa konversi' in page.locator('.replay-captured-quotes').inner_text()
 assert before==page.evaluate('({now:suntrainReplay.now,filters:suntrainReplay.filterSignature})')
 page.locator('#language-select').select_option('en')
 conflicts=page.evaluate('suntrainReplay.filtered.filter(s=>s.aircraft_variants?.length).length')
 if conflicts:
  page.evaluate('()=>{const r=suntrainReplay;r.select(r.filtered.find(s=>s.aircraft_variants?.length).id);}')
  assert 'differs between captures' in page.locator('#replay-details').inner_text()
 page.locator('#replay-close-details').click()
 # Frequency totals count departures within the UTC window, not all overlapping flights.
 set_filter('replay-flight-view','frequency','suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length>0')
 assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainFlightNetwork.ownedFlights(suntrainReplay.filtered,suntrainReplay.day).length')
 assert page.evaluate('suntrainFlights.movingLayers.every(id=>suntrainReplay.graph.getLayoutProperty(id,"visibility")==="none")')
 page.locator('#replay-map').screenshot(path=str(OUT/'frequency.png'))
 set_filter('replay-flight-view','planes','!suntrainReplay.frequencyView')
 set_filter('replay-display',['routes'],'!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
 set_filter('replay-display',['routes','stations'],'suntrainReplay.graph.getSource("replay-stations")._data.features.length>0')
 # Shared colours remain stable, and country palettes survive a World round trip.
 palettes=[]
 for city in ['world_flights','europe_flights','singapore_flights','europe_flights','world_flights']:
  if page.evaluate('suntrainReplay.day.city')!=city:load(city)
  palettes.append(page.evaluate('()=>{const s=suntrainReplay.day.services.find(s=>s.carrier==="LH");return {key:suntrainFlights.planeKey(s),color:s.color};}'))
 assert palettes[0]==palettes[4] and palettes[1]==palettes[3] and palettes[1]!=palettes[2]
 page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
 page.wait_for_function('document.querySelector("#city-overview-content").textContent.includes("Collection evidence by source")')
 assert 'undefined' not in page.locator('#city-overview-content').inner_text()
 assert page.locator('.world-source-evidence > details').count()==len(expected['metadata']['member_views'])
 if 'world_international_expansion' in expected['metadata']['member_views']:
  assert 'International expansion' in page.locator('.world-source-evidence > details > summary').all_text_contents()
 page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
 page.set_viewport_size({'width':390,'height':844})
 for theme in ['light','dark','sunrise','blueprint','heritage']:
  page.locator('#theme-toggle').select_option(theme)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.locator('#language-select').select_option('id')
 assert 'penerbangan unik' in page.locator('#replay-world-coverage').inner_text()
 page.locator('#replay-fullscreen').click();page.wait_for_timeout(200)
 page.keyboard.press('ArrowRight');page.keyboard.press('Escape')
 assert not page.evaluate('suntrainReplay.isFullscreen()')
 page.screenshot(path=str(OUT/'mobile.png'))
 assert not errors,errors
 print('World flight assertions passed: union, peak, dateline viewport, country and scope filters, local boards, quotes, frequency, palettes, evidence, languages, themes and mobile.',flush=True)
 browser.close();print('World browser shutdown completed.',flush=True)
