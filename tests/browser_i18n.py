"""Optional bilingual explorer/calendar regression checks against a running SunTrain."""
import os
from playwright.sync_api import sync_playwright
from browser_controls import click_tool, select_setting

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-unsafe-swiftshader','--use-angle=swiftshader'])
    page=browser.new_page(viewport={'width':1280,'height':900},locale='id-ID',ignore_https_errors=True)
    errors,downloads=[],[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda r:downloads.append(r.url) if '/api/replay/' in r.url else None)
    page.goto(os.environ.get('SUNTRAIN_TEST_URL','http://127.0.0.1:8857'),wait_until='domcontentloaded')
    page.wait_for_selector('#language-select',state='attached')
    assert page.locator('html').get_attribute('lang')=='en'
    select_setting(page, '#language-select', 'id')
    page.wait_for_function('document.querySelector("#home-panel").textContent.includes("Dunia yang terus bergerak")')
    page.wait_for_function('document.querySelector("#home-place").textContent.includes("Cari kota atau negara")')
    assert page.locator('#replay-language-select').input_value()=='id'
    page.reload(wait_until='domcontentloaded')
    page.wait_for_selector('#language-select',state='attached')
    assert page.locator('#language-select').input_value()=='id'
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
    page.wait_for_function('suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length',timeout=120000)
    page.locator('#replay-about > summary').click()
    assert 'Data penumpang hanya tersedia untuk kereta' in page.locator('#replay-description').inner_text()
    assert 'belum dapat ditentukan' in page.locator('#replay-quality').inner_text()
    page.locator('#replay-about > summary').click()
    page.evaluate('''() => { const r=suntrainReplay; r.pause();
        r.departures.open(r.day.stations.findIndex(s=>s.name==='Flinders Street')); }''')
    page.wait_for_selector('.departure-row')
    page.locator('.departure-row').first.click()
    page.locator('.replay-all-stops summary').click()
    state=page.evaluate('({now:suntrainReplay.now,selected:suntrainReplay.selected.id,center:suntrainReplay.graph.getCenter().toArray(),filters:suntrainReplay.filterSignature,day:suntrainReplay.day.revision})')
    count=len(downloads)
    select_setting(page, '#language-select', 'en')
    assert page.get_by_role('button',name='Go to departure',exact=True).is_visible()
    assert page.evaluate('({now:suntrainReplay.now,selected:suntrainReplay.selected.id,center:suntrainReplay.graph.getCenter().toArray(),filters:suntrainReplay.filterSignature,day:suntrainReplay.day.revision})')==state
    select_setting(page, '#language-select', 'id')
    assert page.get_by_role('button',name='Ke waktu keberangkatan',exact=True).is_visible()
    assert page.locator('.replay-all-stops').get_attribute('open') is not None
    assert len(downloads)==count
    page.get_by_role('button',name='Kembali ke keberangkatan',exact=True).click()
    page.get_by_role('button',name='Berikutnya',exact=True).click()
    board_page=page.evaluate('suntrainReplay.departures.page')
    select_setting(page, '#language-select', 'en')
    assert page.evaluate('suntrainReplay.departures.page')==board_page
    assert page.locator('#replay-departures h3').inner_text()=='Flinders Street'
    select_setting(page, '#language-select', 'id')
    page.screenshot(path='.cache/bilingual-replay.png',full_page=True)
    select_setting(page, '#language-select', 'en')
    # Calendar month, selected date and replay state survive language switching.
    page.locator('#replay-date-open').click()
    assert page.locator('#replay-calendar').is_visible()
    page.get_by_role('button',name='Next month',exact=True).click()
    page.evaluate('suntrainI18n.setLanguage("id")')
    assert 'Juni 2024' in page.locator('.calendar-navigation').inner_text()
    assert page.evaluate('suntrainReplay.now')==state['now']
    page.keyboard.press('Escape')
    assert not page.locator('#replay-calendar').is_visible()
    # Bounded arrow navigation at the first supported date; Enter selects ISO day.
    minimum=page.evaluate('document.querySelector("#replay-date-open").textContent')
    page.locator('#replay-date-open').click()
    page.keyboard.press('ArrowLeft')
    assert page.locator('#replay-calendar button:focus').get_attribute('data-date')=='2024-05-27'
    page.keyboard.press('ArrowRight');page.keyboard.press('Enter')
    page.wait_for_function('suntrainReplay.day.business_date==="2024-05-28" && !suntrainReplay.loading',timeout=120000)
    page.set_viewport_size({'width':390,'height':844})
    for theme in ['light','dark','sunrise','blueprint','heritage']:
        select_setting(page, '#theme-toggle', theme)
        page.locator('#replay-date-open').click()
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.keyboard.press('Escape')
    click_tool(page, '#replay-fullscreen')
    page.wait_for_function('suntrainReplay.isFullscreen()')
    select_setting(page, '#replay-language-select', 'en')
    # Date remains directly available beside the place in fullscreen.
    page.locator('#replay-date-open').click()
    page.keyboard.press('Escape')
    assert page.evaluate('suntrainReplay.isFullscreen()')
    page.screenshot(path='.cache/bilingual-mobile-fullscreen.png',full_page=True)
    page.keyboard.press('Escape')
    page.set_viewport_size({'width':1280,'height':900})
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"overview"})')
    page.wait_for_selector('#city-overview',state='visible')
    select_setting(page, '#language-select', 'id')
    assert 'Ringkasan Melbourne' in page.locator('#city-overview-title').inner_text()
    assert 'Keberangkatan terjadwal' in page.locator('#city-overview').inner_text()
    page.screenshot(path='.cache/bilingual-overview.png',full_page=True)
    # Swap a network while translated; provenance and new options must stay translated.
    page.evaluate('dash_clientside.set_props("replay-city",{value:"jakarta"})')
    page.wait_for_function('suntrainReplay.day?.city==="jakarta" && !suntrainReplay.loading',timeout=120000)
    page.evaluate('dash_clientside.set_props("view-tabs",{value:"replay"})')
    page.wait_for_function('suntrainReplay.active && suntrainReplay.filtered.length')
    page.locator('#replay-about > summary').click()
    assert 'Waktu tiba di terminal' in page.locator('#replay-quality').inner_text()
    assert page.evaluate('suntrainReplay.day.schedule.note_messages.length')>0
    page.locator('#replay-about > summary').click()
    page.screenshot(path='.cache/bilingual-jakarta.png',full_page=True)
    # Language switches during failed replacement downloads keep actionable old calls cleared.
    page.route('**/api/replay/jakarta/**',lambda route:route.abort())
    page.evaluate('''() => { dash_clientside.set_props('replay-date',{data:'2025-12-16'}); suntrainI18n.setLanguage('en'); }''')
    page.wait_for_function('document.querySelector("#replay-load-message").textContent.includes("could not load")')
    select_setting(page, '#language-select', 'id')
    assert 'Pemutaran tidak dapat dimuat' in page.locator('#replay-load-message').inner_text()
    assert page.evaluate('!suntrainReplay.departures.visible && suntrainReplay.departures.station===null')
    assert not errors,errors
    print({'languages':'en/id','state_preservation':'passed','calendar_keyboard_mobile_fullscreen':'passed','provenance':'passed','page_errors':errors},flush=True)
    browser.close()
