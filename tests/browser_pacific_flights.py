"""Pacific date-line map, local boards, filters and mobile browser verification."""
import gzip,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
AUDIT=Path('.cache/pacific-flights-audit');AUDIT.mkdir(exist_ok=True)
with gzip.open('data/reference/pacific_flights/2026-11-02.json.gz','rt') as f:raw=json.load(f)
air={a['code']:a for a in raw['airports']};total=len(raw['flights']);returned={f[k] for f in raw['flights'] for k in ('origin','destination')}
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8893'),wait_until='domcontentloaded')
 page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
 places=page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places)')
 assert any(x['id']=='pacific_flights' for x in places)
 page.wait_for_function('suntrainHome?.ready && suntrainHome.markers.length')
 page.get_by_role('button',name='Explore Pacific Islands · Flights',exact=True).click()
 page.get_by_role('button',name='Open Pacific Islands · Flights replay',exact=True).click()
 page.wait_for_function('window.suntrainReplay?.day?.city==="pacific_flights" && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',timeout=120000)
 assert page.evaluate('suntrainReplay.day.timezone')=='UTC'
 assert page.evaluate('suntrainReplay.day.services.length')==total
 center=page.evaluate('(suntrainReplay.graph.getCenter().lng+360)%360');assert 160<center<220,center
 page.screenshot(path=str(AUDIT/'pacific-map.png'))
 for scope in ['domestic','international','both']:
  page.evaluate('(scope)=>dash_clientside.set_props("replay-flight-scope",{value:scope})',scope)
  page.wait_for_function('(scope)=>suntrainReplay.filters.flightScope===scope && suntrainReplay.filtered.every(s=>scope==="both" || s.flight_scope===scope)',arg=scope)
 page.evaluate('dash_clientside.set_props("replay-from-countries",{value:["PG"]})')
 page.wait_for_function('suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[0][0]].country==="PG")')
 page.evaluate('dash_clientside.set_props("replay-from-countries",{value:[]})')
 page.wait_for_function('(n)=>suntrainReplay.filtered.length===n',arg=total)
 carrier=raw['flights'][0]['carrier']
 page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
 page.wait_for_function('(c)=>suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
 page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})');page.wait_for_function('(n)=>suntrainReplay.filtered.length===n',arg=total)
 checked=[]
 for airport in ['POM','BUA','NAN','GUM','PPT','NHV','APW','PPG','HNL','CHT','IPC']:
  if airport not in returned:continue
  page.evaluate('(c)=>dash_clientside.set_props("replay-airports",{value:[c]})',airport)
  page.wait_for_function('(c)=>suntrainReplay.filters.airports[0]===c',arg=airport)
  page.evaluate('(c)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===c))}',airport)
  page.wait_for_function('(z)=>suntrainReplay.departures.timezone===z && suntrainReplay.departures.services===suntrainReplay.filtered',arg=air[airport]['timezone'])
  assert 'The replay clock uses UTC.' in page.locator('.replay-detail-card').inner_text()
  for event,direction in [('arrival','arrivals'),('departure','departures')]:
   page.locator(f'[data-event="{event}"]').click()
   page.wait_for_function('([c,d])=>suntrainReplay.filters.airportDirection===d && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[d==="arrivals"?1:0][0]].code===c)',arg=[airport,direction])
  page.locator('[data-event="destinations"]').click();page.wait_for_function('suntrainReplay.departures.event==="destinations"')
  page.locator('[data-event="departure"]').click();page.get_by_role('button',name='Expand board',exact=True).click()
  page.wait_for_function('suntrainReplay.departures.expanded')
  page.screenshot(path=str(AUDIT/f'pacific-{airport}-board.png'));page.evaluate('suntrainReplay.departures.close()');checked.append(airport)
 page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
 page.wait_for_function('(n)=>suntrainReplay.filtered.length===n && suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length',arg=total)
 assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainReplay.filtered.length')
 page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"planes"})')
 for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
 page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
 page.set_viewport_size({'width':390,'height':844});page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(AUDIT/'pacific-mobile.png'));page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
 for city in ['australia_flights','new_zealand_flights','united_states_flights','pakistan_flights','melbourne']:
  if not any(x['id']==city for x in places):continue
  page.evaluate('(c)=>dash_clientside.set_props("replay-city",{value:c})',city)
  page.wait_for_function('(c)=>window.suntrainReplay?.day?.city===c && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
 assert not errors,errors
 browser.close();print('Pacific',total,'flights; local boards',checked,'date-line fit, filters, frequency, themes, Indonesian and mobile passed',flush=True)
