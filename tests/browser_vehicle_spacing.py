"""Check visible dot spacing, rather than only the underlying metre offsets."""
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True,
        args=['--enable-unsafe-swiftshader', '--use-angle=swiftshader'])
    for pixel_ratio in [1, 2]:
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=pixel_ratio, ignore_https_errors=True)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(os.environ.get('SUNTRAIN_TEST_URL', 'http://127.0.0.1:8862'), wait_until='domcontentloaded')
        page.wait_for_function('window.dash_clientside && document.querySelector("#replay-panel")')
        page.evaluate('dash_clientside.set_props("view-tabs", {value:"replay"})')
        page.wait_for_function('suntrainReplay.mapReady && !suntrainReplay.loading && suntrainReplay.filtered.length', timeout=120000)
        page.evaluate('suntrainReplay.pause()')
        for zoom in [8, 9.5, 11, 12.5, 15]:
            result = page.evaluate('''async zoom => {
                const r = suntrainReplay, map = r.graph;
                map.jumpTo({center: [144.85, -37.83], zoom}); await r.paint(true);
                const groups = new Map();
                for (const feature of map.getSource('replay-trains')._data.features) {
                    const id = feature.properties.id;
                    if (!groups.has(id)) groups.set(id, []);
                    groups.get(id).push(feature);
                }
                let count = 0, largestRatio = 0, largestWidth = 0;
                for (const group of groups.values()) {
                    if (group.length !== 3) continue;
                    const radius = suntrainVehicles.radius(zoom, group[0].properties.sizeFactor);
                    const pixels = group.map(f => map.project(f.geometry.coordinates));
                    for (let i = 1; i < pixels.length; i++) {
                        const distance = Math.hypot(pixels[i].x-pixels[i-1].x, pixels[i].y-pixels[i-1].y);
                        largestRatio = Math.max(largestRatio, distance / (2 * radius));
                    }
                    const width = Math.hypot(pixels[2].x-pixels[0].x, pixels[2].y-pixels[0].y) + 2 * (radius + 1.2);
                    largestWidth = Math.max(largestWidth, width); count++;
                }
                return {zoom, count, largestRatio, largestWidth};
            }''', zoom)
            print({'pixel_ratio':pixel_ratio, **result}, flush=True)
            assert result['count'] > 10
            assert result['largestRatio'] <= 1.15, result
            assert result['largestWidth'] < 26, result
        if pixel_ratio == 1:
            page.evaluate('suntrainReplay.graph.jumpTo({center:[144.73,-37.85],zoom:10.6})')
            page.locator('#replay-map').screenshot(path='.cache/melbourne-compact-western.png')
            page.evaluate('suntrainReplay.graph.jumpTo({center:[144.967,-37.818],zoom:12.2})')
            page.locator('#replay-map').screenshot(path='.cache/melbourne-compact-cbd.png')
        assert not errors, errors
        page.close()
    browser.close()
    print('Compact spacing passed across five zooms and both pixel densities', flush=True)
