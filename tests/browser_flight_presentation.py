"""Presentation regression using frozen captures, including the original 13 map comparisons."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path('.cache/flight-display-consistency'); OUT.mkdir(parents=True, exist_ok=True)
CASES = ['australia_flights','south_korea_flights','europe_flights','africa_flights','singapore_flights',
         'gulf_flights','hong_kong_flights','bahrain_flights','nepal_flights','laos_flights',
         'taiwan_flights','myanmar_flights','pacific_flights']
CAMERA = '({center:suntrainReplay.graph.getCenter().toArray().map(n=>+n.toFixed(6)),zoom:+suntrainReplay.graph.getZoom().toFixed(6)})'
METRICS = '''() => {const r=suntrainReplay,m=r.graph;return {city:r.day.city,kind:r.day.flight_view_kind,
 zoom:m.getZoom(),center:m.getCenter().toArray(),bounds:m.getBounds().toArray(),clock:document.querySelector('#replay-clock').textContent,
 isoTime:new Date(r.now*1000).toISOString(),total:r.day.services.length,filtered:r.filtered.length,
 active:r.activePositions.length,inViewport:r.visibleFlights,scope:r.filters.flightScope,airports:r.filters.airports,
 counts:document.querySelector('.replay-map-counts').textContent,
 planeSize:m.getLayoutProperty('replay-planes','icon-size')*32};}'''
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True)
 errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8898'),wait_until='domcontentloaded')
 page.wait_for_function('window.suntrainHome?.ready')
 def load(city):
  repeated=page.evaluate('(city)=>suntrainReplay.day?.city===city',city)
  if repeated:
   page.evaluate('''() => {for(const id of ['replay-carriers','replay-airports','replay-lines'])dash_clientside.set_props(id,{value:[]});dash_clientside.set_props('replay-flight-scope',{value:'both'});dash_clientside.set_props('replay-flight-view',{value:'planes'});}''')
  page.evaluate('(city)=>{dash_clientside.set_props("view-tabs",{value:"replay"});dash_clientside.set_props("replay-city",{value:city})}',city)
  page.wait_for_function('(city)=>suntrainReplay.day?.city===city && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length===suntrainReplay.day.services.length && suntrainReplay.filters.flightScope==="both" && !suntrainReplay.filters.airports.length && !suntrainReplay.filters.carriers.length',arg=city,timeout=120000)
  page.evaluate('suntrainReplay.pause()')
  if repeated: page.evaluate('suntrainReplay.seek(suntrainReplay.day.initial);suntrainReplay.metroView()')
  page.wait_for_timeout(500)
 def set_filter(id,value,condition):
  page.evaluate('([id,value])=>dash_clientside.set_props(id,{value})',[id,value]);page.wait_for_function(condition)
 rows=[]
 for city in ([] if os.environ.get('SKIP_MAP_COMPARISONS') else CASES):
  load(city)
  assert page.locator('#replay-clock').inner_text()=='10:00:00'
  assert page.locator('#replay-flight-key').is_visible()
  assert 'Partial coverage' in page.locator('#replay-flight-key').inner_text()
  assert page.locator('#replay-fit').inner_text()=='Fit flights'
  row=page.evaluate(METRICS); original=page.evaluate(CAMERA); now=page.evaluate('suntrainReplay.now')
  projected=page.evaluate('''() => {const r=suntrainReplay,m=r.graph,c=m.getContainer();return new Set(r.activePositions.filter(f=>{
   const coordinate=f.geometry.coordinates,p=m.project([coordinate[0]+360*Math.round((m.getCenter().lng-coordinate[0])/360),coordinate[1]]);
   return p.x>=0 && p.y>=0 && p.x<=c.clientWidth && p.y<=c.clientHeight;
  }).map(f=>f.properties.id)).size;}''')
  assert row['inViewport']==projected,(city,row['inViewport'],projected)

  page.locator('#replay-map').screenshot(path=str(OUT/(city+'-opening.png')))
  page.locator('#replay-melbourne').click();page.wait_for_timeout(150)
  assert page.evaluate(CAMERA)==original and page.evaluate('suntrainReplay.now')==now, (original,page.evaluate(CAMERA))
  rows.append(row);print(json.dumps(row),flush=True)
 if rows: (OUT/'maps.json').write_text(json.dumps(rows,indent=2))
 # Dots/planes meet exactly at 4.5; selected artwork remains 22 px at every zoom.
 load('europe_flights')
 print('Europe interaction replay loaded.',flush=True)
 assert page.evaluate('suntrainReplay.graph.getLayer("replay-flight-dots").maxzoom')==4.5
 assert page.evaluate('suntrainReplay.graph.getLayer("replay-planes").minzoom')==4.5
 assert page.evaluate('suntrainReplay.graph.getPaintProperty("replay-flight-dots","circle-radius")')==2.2
 assert page.evaluate('suntrainReplay.graph.getPaintProperty("replay-flight-dots","circle-stroke-width")')==.8
 for zoom in [4.49,4.5,8]:
  page.evaluate('(zoom)=>{suntrainReplay.graph.jumpTo({center:[8,50],zoom});}',zoom);page.wait_for_timeout(300)
  sizes=page.evaluate('[suntrainReplay.graph.getLayoutProperty("replay-planes","icon-size")*32,suntrainReplay.graph.getLayoutProperty("replay-selected-flight","icon-size")*32]')
  assert sizes==[16,22]
  layer='replay-flight-dots' if zoom<4.5 else 'replay-planes'
  other='replay-planes' if zoom<4.5 else 'replay-flight-dots'
  page.wait_for_function('(layer)=>suntrainReplay.graph.queryRenderedFeatures({layers:[layer]}).length>0',arg=layer)
  assert page.evaluate('(layer)=>suntrainReplay.graph.getLayer(layer).isHidden(suntrainReplay.graph.getZoom())',other)
  hit=page.evaluate('''(layer)=>{const r=suntrainReplay;for(const f of r.graph.queryRenderedFeatures({layers:[layer]})) {
   const p=suntrainFlights.project(r.graph,f.geometry.coordinates);p.x+=5;
   const hit=r.vehicleNear(p);if(hit && !r.graph.queryRenderedFeatures(p,{layers:['replay-airport-labels']}).length)return {point:p,id:hit.properties.id};}}''',layer)
  assert hit
  page.evaluate('(hit)=>{const m=suntrainReplay.graph,ll=m.unproject([hit.point.x,hit.point.y]);m.fire("click",{point:m.project(ll),lngLat:ll});}',hit)
  page.wait_for_function('(id)=>suntrainReplay.selected?.id===id',arg=hit['id'])
  assert page.evaluate('suntrainReplay.graph.getSource("replay-selected-train")._data.features[0].properties.id')==hit['id']
 page.locator('#replay-close-details').click()
 page.evaluate('suntrainReplay.metroView()');page.wait_for_timeout(150)
 print('Marker thresholds, selection and picking passed.',flush=True)
 # Filters and boards retain camera/time; explicit Fit differs from Reset.
 before=page.evaluate(CAMERA);now=page.evaluate('suntrainReplay.now')
 set_filter('replay-carriers',['LH'],'suntrainReplay.filters.carriers[0]==="LH"')
 assert page.evaluate(CAMERA)==before and page.evaluate('suntrainReplay.now')==now
 set_filter('replay-flight-scope','international','suntrainReplay.filters.flightScope==="international"')
 assert page.evaluate(CAMERA)==before and page.evaluate('suntrainReplay.now')==now
 page.evaluate('suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code==="LHR"))')
 page.wait_for_function('suntrainReplay.filters.airports[0]==="LHR" && suntrainReplay.departures.services===suntrainReplay.filtered')
 assert page.evaluate(CAMERA)==before and page.evaluate('suntrainReplay.now')==now
 page.locator('#replay-fit').click();page.wait_for_timeout(150)
 assert page.evaluate(CAMERA)!=before
 page.locator('#replay-melbourne').click();page.wait_for_timeout(150)
 assert page.evaluate(CAMERA)==before and page.evaluate('suntrainReplay.now')==now
 print('Camera and board stability passed.',flush=True)
 # Frequency removes every moving representation, including a selected journey.
 set_filter('replay-flight-view','frequency','suntrainReplay.frequencyView')
 assert page.evaluate('suntrainFlights.movingLayers.every(id=>suntrainReplay.graph.getLayoutProperty(id,"visibility")==="none")')
 assert 'captured departures' in page.locator('#replay-matching-count').inner_text()
 set_filter('replay-flight-view','planes','!suntrainReplay.frequencyView')
 set_filter('replay-display',['routes'],'!suntrainReplay.graph.getSource("replay-stations")._data.features.length')
 page.wait_for_function('!suntrainReplay.graph.queryRenderedFeatures({layers:["replay-airport-labels"]}).length')
 set_filter('replay-display',['routes','stations'],'suntrainReplay.graph.getSource("replay-stations")._data.features.length>0')
 # Airport labels take priority over nearby flights and remain directly selectable.
 page.locator('#replay-close-details').click()
 page.evaluate('() => {suntrainReplay.graph.jumpTo({center:[-.45,51.47],zoom:7});}');page.wait_for_timeout(400)
 label=page.evaluate('''() => {const r=suntrainReplay;for(const f of r.graph.queryRenderedFeatures({layers:['replay-airport-labels']})) {
 const p=suntrainFlights.project(r.graph,f.geometry.coordinates);p.y+=15;
 const label=r.graph.queryRenderedFeatures(p,{layers:['replay-airport-labels']})[0];
 if(label)return {id:Number(label.properties.id),point:p};}}''')
 assert label
 page.evaluate('(hit)=>{const m=suntrainReplay.graph,ll=m.unproject([hit.point.x,hit.point.y]);m.fire("click",{point:m.project(ll),lngLat:ll});}',label)
 page.wait_for_function('(id)=>suntrainReplay.departures.visible && suntrainReplay.departures.station===id',arg=label['id'])
 # Palette switching cannot reuse different-colour artwork for the same carrier.
 palettes=[]
 for city in ['europe_flights','singapore_flights','europe_flights']:
  load(city)
  palettes.append(page.evaluate('''() => {const r=suntrainReplay,s=r.day.services.find(s=>s.carrier==='LH');
   const key=suntrainFlights.planeKey(s);return {key,color:s.color,exists:r.graph.hasImage(key)};}'''))
 assert palettes[0]==palettes[2] and palettes[0]['key']!=palettes[1]['key'] and all(p['exists'] for p in palettes)
 # Laos has no domestic flight at 10:00; next departure is the captured LK212 at 12:15.
 load('laos_flights');set_filter('replay-flight-scope','domestic','suntrainReplay.filters.flightScope==="domestic"')
 assert page.locator('#replay-flight-empty').is_visible()
 assert page.locator('#replay-next-departure').is_visible()
 next_at=page.evaluate('suntrainReplay.filtered.find(s=>s.number==="LK212").stops[0][2]')
 page.locator('#replay-next-departure').click()
 assert page.evaluate('suntrainReplay.now')==next_at and not page.evaluate('suntrainReplay.playing')
 assert page.locator('#replay-clock').inner_text()=='12:15:00'
 page.evaluate('() => {suntrainReplay.seek(suntrainReplay.day.initial);suntrainReplay.graph.jumpTo({center:[0,0],zoom:6});}')
 page.wait_for_timeout(250)
 assert page.locator('#replay-flight-empty-hint').is_visible() and not page.locator('#replay-next-departure').is_visible()
 # Language/theme/mobile round trips preserve state and expose both count lines.
 load('taiwan_flights')
 state=page.evaluate('({camera:'+CAMERA+',now:suntrainReplay.now,filters:suntrainReplay.filterSignature})')
 for language in ['id','en']:
  page.locator('#language-select').select_option(language)
  page.wait_for_function('(language)=>document.documentElement.lang===language',arg=language)
  assert page.evaluate('({camera:'+CAMERA+',now:suntrainReplay.now,filters:suntrainReplay.filterSignature})')==state
  assert ('tersimpan' if language=='id' else 'captured flights') in page.locator('#replay-matching-count').inner_text()
 page.set_viewport_size({'width':390,'height':844})
 for theme in ['light','dark','sunrise','blueprint','heritage']:
  page.locator('#theme-toggle').select_option(theme)
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  assert page.locator('#replay-matching-count').is_visible()
 page.locator('#replay-fullscreen').click();page.wait_for_timeout(150)
 page.keyboard.press('ArrowRight');page.keyboard.press('Escape')
 assert not page.evaluate('suntrainReplay.isFullscreen()')
 page.screenshot(path=str(OUT/'mobile.png'))
 assert not errors,errors
 print('Flight presentation assertions passed.',flush=True)
 browser.close()
 print('Browser shutdown completed.',flush=True)
