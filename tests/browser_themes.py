"""Optional Chrome smoke test against a running local SunTrain server."""
import os
from playwright.sync_api import sync_playwright
from browser_controls import click_tool, select_setting

THEMES = {'light':'#18232d','dark':'#e4eef0','sunrise':'#33291f','blueprint':'#edf5ff','heritage':'#29372d'}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':900},ignore_https_errors=True)
    errors,downloads=[],[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8850'),wait_until='domcontentloaded')
    page.wait_for_function('window.suntrainHome?.ready')
    assert page.locator('#theme-toggle option').count()==5
    for theme in THEMES:
        select_setting(page, '#theme-toggle', theme)
        page.wait_for_function('(t)=>suntrainTheme.current===t && document.querySelector("#replay-theme-toggle").value===t',arg=theme)
        assert page.evaluate('suntrainHome.map.getPaintProperty("background","background-color")')==page.evaluate('suntrainTheme.mapStyle().layers[0].paint["background-color"]')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function('window.suntrainHome?.ready')
    assert page.locator('#theme-toggle').input_value()=='heritage'
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
    page.wait_for_function('suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    page.evaluate('''() => { const r=suntrainReplay; r.pause();
        r.departures.open(r.filtered[0].stopIds?.[0] ?? r.filtered[0].stops[0][0]); }''')
    before=page.evaluate('({time:suntrainReplay.now,center:suntrainReplay.graph.getCenter().toArray(),day:suntrainReplay.day.revision,filters:suntrainReplay.filterSignature,colors:suntrainReplay.filtered.slice(0,10).map(s=>s.color)})')
    request_count=len(downloads)
    for theme in THEMES:
        select_setting(page, '#theme-toggle', theme)
        after=page.evaluate('({time:suntrainReplay.now,center:suntrainReplay.graph.getCenter().toArray(),day:suntrainReplay.day.revision,filters:suntrainReplay.filterSignature,colors:suntrainReplay.filtered.slice(0,10).map(s=>s.color)})')
        assert before==after
        assert page.locator('#replay-departures').is_visible()
        page.wait_for_function('suntrainReplay.graph.getPaintProperty("background","background-color")===suntrainTheme.mapStyle().layers[0].paint["background-color"]')
        page.wait_for_timeout(350)
        page.screenshot(path=f'.cache/five-themes-{theme}.png',full_page=True)
    assert len(downloads)==request_count
    page.locator('#replay-play').click()
    page.wait_for_function('suntrainReplay.playing')
    select_setting(page, '#theme-toggle', 'blueprint')
    assert page.evaluate('suntrainReplay.playing')
    page.locator('#replay-play').click()
    page.set_viewport_size({'width':390,'height':844})
    for theme in THEMES:
        select_setting(page, '#theme-toggle', theme)
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
    click_tool(page, '#replay-fullscreen')
    page.wait_for_function('suntrainReplay.isFullscreen()')
    select_setting(page, '#replay-theme-toggle', 'blueprint')
    assert page.locator('#theme-toggle').input_value()=='blueprint'
    page.screenshot(path='.cache/five-themes-mobile-fullscreen.png',full_page=True)
    page.keyboard.press('Escape')
    page.set_viewport_size({'width':1280,'height':900})
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.locator('#melbourne-analysis-toggle').click()
    page.wait_for_selector('#overview-panel .js-plotly-plot')
    for theme,ink in THEMES.items():
        select_setting(page, '#theme-toggle', theme)
        page.wait_for_function('(ink)=>document.querySelector("#overview-panel .js-plotly-plot")?.layout?.font?.color===ink',arg=ink,timeout=60000)
    # Settings is keyboard-reachable; native choices persist and synchronize.
    summary=page.locator('.playground-settings > summary')
    if summary.evaluate('(el)=>el.parentElement.open'): summary.click()
    summary.focus(); page.keyboard.press('Enter'); page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.id')=='theme-toggle'
    page.locator('#theme-toggle').select_option('blueprint')
    page.wait_for_function('suntrainTheme.current==="blueprint"')
    assert page.evaluate('localStorage.getItem("suntrain-theme")')=='blueprint'
    page.keyboard.press('Escape')
    assert summary.evaluate('(el)=>!el.parentElement.open && document.activeElement===el')
    assert not errors,errors
    print({'themes':list(THEMES),'desktop_mobile_fullscreen':'passed','persistence_and_charts':'passed','page_errors':errors},flush=True)
    browser.close()
