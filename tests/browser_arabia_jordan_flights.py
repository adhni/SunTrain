"""Country maps, local boards, filters and fullscreen across the four new flight views."""
import gzip,json,os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from dashboard.arabia_jordan_flights import COUNTRIES
AUDIT=Path('.cache/arabia-jordan-flights-audit');AUDIT.mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
 page=browser.new_page(viewport={'width':1440,'height':1100},ignore_https_errors=True);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8891'),wait_until='domcontentloaded')
 page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
 places=page.evaluate('JSON.parse(document.querySelector("#home-panel").dataset.places)')
 assert all(any(x['id']==p['slug']+'_flights' for x in places) for p in COUNTRIES.values())
 page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
 for code,profile in COUNTRIES.items():
  slug=profile['slug'];city=slug+'_flights'
  with gzip.open(f'data/reference/{slug}_flights/2026-11-02.json.gz','rt') as f:raw=json.load(f)
  national={a['code'] for a in raw['airports'] if a['country']==code};returned={c for f in raw['flights'] for c in (f['origin'],f['destination'])}&national
  page.evaluate('(city)=>dash_clientside.set_props("replay-city",{value:city})',city)
  page.wait_for_function('(city)=>window.suntrainReplay?.day?.city===city && suntrainReplay.mapReady && !suntrainReplay.loading && !suntrainReplay.needsFit && suntrainReplay.filtered.length',arg=city,timeout=120000)
  assert page.evaluate('suntrainReplay.day.timezone')==profile['zone']
  assert page.evaluate('suntrainReplay.day.services.length')==len(raw['flights'])
  assert page.evaluate('suntrainReplay.filters.flightScope')==('both' if profile['scopes'] else 'international')
  if profile['scopes']:
   for scope in ['domestic','international','both']:
    page.evaluate('(scope)=>dash_clientside.set_props("replay-flight-scope",{value:scope})',scope)
    page.wait_for_function('(scope)=>suntrainReplay.filters.flightScope===scope && suntrainReplay.filtered.every(s=>scope==="both" || s.flight_scope===scope)',arg=scope)
  total=len(raw['flights'])
  carrier=raw['flights'][0]['carrier']
  page.evaluate('(c)=>dash_clientside.set_props("replay-carriers",{value:[c]})',carrier)
  page.wait_for_function('(c)=>suntrainReplay.filtered.length && suntrainReplay.filtered.every(s=>s.carrier===c)',arg=carrier)
  page.evaluate('dash_clientside.set_props("replay-carriers",{value:[]})')
  page.wait_for_function('(n)=>suntrainReplay.filtered.length===n',arg=total)
  page.screenshot(path=str(AUDIT/f'{slug}-map.png'))
  for airport in sorted(returned):
   page.evaluate('(code)=>dash_clientside.set_props("replay-airports",{value:[code]})',airport)
   page.wait_for_function('(code)=>suntrainReplay.filters.airports[0]===code',arg=airport)
   page.evaluate('(code)=>{suntrainReplay.seek(suntrainReplay.day.start);suntrainReplay.departures.open(suntrainReplay.day.stations.findIndex(a=>a.code===code))}',airport)
   page.wait_for_function('(z)=>suntrainReplay.departures.timezone===z && suntrainReplay.departures.services===suntrainReplay.filtered',arg=profile['zone'])
   assert f"The replay clock uses {profile['clock']}." in page.locator('.replay-detail-card').inner_text()
   for mode,direction in [('arrival','arrivals'),('departure','departures')]:
    page.locator(f'[data-event="{mode}"]').click()
    page.wait_for_function('([code,d])=>suntrainReplay.filters.airportDirection===d && suntrainReplay.filtered.every(s=>suntrainReplay.day.stations[s.stops[d==="arrivals"?1:0][0]].code===code)',arg=[airport,direction])
   page.locator('[data-event="destinations"]').click()
   page.wait_for_function('suntrainReplay.departures.event==="destinations"')
   page.locator('[data-event="departure"]').click()
   page.get_by_role('button',name='Expand board',exact=True).click()
   page.wait_for_function('suntrainReplay.departures.expanded')
   page.screenshot(path=str(AUDIT/f'{slug}-{airport}-board.png'))
   page.evaluate('suntrainReplay.departures.close()')
  page.evaluate('dash_clientside.set_props("replay-airports",{value:[]});dash_clientside.set_props("replay-flight-view",{value:"frequency"})')
  page.wait_for_function('(n)=>suntrainReplay.filtered.length===n && suntrainReplay.frequencyView && suntrainReplay.frequencyFeatures.length',arg=total)
  assert page.evaluate('suntrainReplay.frequencyFeatures.reduce((n,f)=>n+f.properties.count,0)===suntrainReplay.filtered.length')
  page.evaluate('dash_clientside.set_props("replay-flight-view",{value:"planes"})')
  for theme in ['light','dark','sunrise','blueprint','heritage']:page.locator('#theme-toggle').select_option(theme)
  page.locator('#language-select').select_option('id');page.wait_for_function('document.documentElement.lang==="id"')
  page.set_viewport_size({'width':390,'height':844});page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.screenshot(path=str(AUDIT/f'{slug}-mobile.png'))
  page.locator('#language-select').select_option('en');page.set_viewport_size({'width':1440,'height':1100})
  print(slug,total,'services; boards',sorted(returned),'passed',flush=True)
 for city,n in [('saudi_flights',1153),('turkiye_flights',2249),('africa_flights',2468),('melbourne',None)]:
  page.evaluate('(c)=>dash_clientside.set_props("replay-city",{value:c})',city)
  page.wait_for_function('(c)=>window.suntrainReplay?.day?.city===c && !suntrainReplay.loading && suntrainReplay.filtered.length',arg=city,timeout=120000)
  if n:assert page.evaluate('suntrainReplay.day.services.length')==n
 assert not errors,errors
 browser.close();print('Four new country views, themes, Indonesian, mobile and Saudi/Türkiye/Africa/Melbourne regressions passed',flush=True)
