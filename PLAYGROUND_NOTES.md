# Transport playground

The homepage is a lightweight discovery map. Transport choices filter its pins, search and four curated scenes together. Numbered pins open place lists. Decorative SVG previews use no tiles or timetable requests.

Watch opens each scene's captured date, local clock and modes, clears old filters/selections and starts at 60×. Reduced-motion users start paused at the exact preset. New selections and direct replay interaction supersede a pending scene. Back restores the discovery camera and transport choice.

Replay uses one viewport with playback below the map, a filter drawer, removable chips, a tools menu and mobile detail sheets. Source explanations and credits are under About this view; scheduled replay and flight coverage labels remain visible. Overview remains available through Menu. Replay HTTP format stays at 28; no captures or reference files changed.

## Validation

- Python: 104 checks passed (app, discovery presets, bilingual catalogues, flight presentation and replay HTTP/cache behavior).
- JavaScript: 99 checks passed (discovery, themes, bilingual copy, replay animation, flight markers/network, World and overview).
- Browser: playground acceptance, 13-view flight presentation, World, Melbourne, bilingual and five-theme/chart suites passed. Browser shutdown completed in the final runs; no shutdown failures remained. Logs and summaries are under ignored `.cache/playground/`.
- Before screenshots: `.cache/uiux-exploration-audit/`. After screenshots, scene clocks and coverage: `.cache/playground/`.
- The browser checks cover all four scenes, zero homepage replay downloads, desktop/phone viewport fit, cluster/search choices, filter chips, dropdown/drawer Escape, fullscreen boards and filters, settings, both languages, rapid selection and reduced motion. Existing World, Melbourne, flight presentation and theme/chart checks are also exercised.

Browser measurements use local headless Chrome with software rendering. Screenshot capture waits for layout transitions; flight picking checks wait for rendered labels rather than assuming a fixed paint delay. These checks establish local behavior, not hosted or physical-device load-time guarantees.
