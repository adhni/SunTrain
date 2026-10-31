(function (root) {
    'use strict';
    if (!root.document) return;
    const $ = id => document.getElementById(id);
    const bind = (element, text) => root.suntrainI18n.bind(element, text);
    const fields = [
        ['lines', 'replay-lines', 'Route / line'], ['carriers', 'replay-carriers', 'Airline / code'],
        ['airports', 'replay-airports', 'Airport / code'], ['fromCountries', 'replay-from-countries', 'From country'],
        ['toCountries', 'replay-to-countries', 'To country'], ['operators', 'replay-operators', 'Operator / feed'],
        ['directions', 'replay-directions', 'Direction'], ['stations', 'replay-stations', 'Services calling at'],
    ];
    let drawerFocus, lastSignature;
    function closeFilters(focus = false) {
        $('replay-panel')?.classList.remove('replay-show-filters');
        $('replay-fullscreen-filters')?.setAttribute('aria-expanded', 'false');
        $('replay-filter-controls')?.removeAttribute('aria-modal');
        if (focus) (drawerFocus || $('replay-fullscreen-filters'))?.focus({preventScroll:true});
    }
    function closePanels() {
        closeFilters();
        for (const menu of document.querySelectorAll('.playground-navigation, .playground-settings, #replay-tools, #replay-about')) menu.open = false;
    }
    function toggleFilters() {
        const panel = $('replay-panel');
        if (panel.classList.contains('replay-show-filters')) { closeFilters(true); return; }
        closePanels(); drawerFocus = document.activeElement;
        panel.classList.add('replay-show-filters');
        $('replay-filter-controls').setAttribute('aria-modal', 'true');
        $('replay-fullscreen-filters').setAttribute('aria-expanded', 'true');
        $('replay-close-filters').focus({preventScroll:true});
    }
    function navigate(tab) {
        root.suntrainReplay?.pause();
        if (root.suntrainHome) root.suntrainHome.pendingExperience = null;
        closePanels();
        if (root.suntrainReplay?.isFullscreen()) root.suntrainReplay.exitFullscreen();
        root.dash_clientside.set_props('view-tabs', {value:tab});
    }
    function clearFilters() {
        for (const [, id] of fields) root.dash_clientside.set_props(id, {value:[]});
        root.dash_clientside.set_props('replay-number', {value:''});
        root.dash_clientside.set_props('replay-flight-scope', {value:'both'});
        root.dash_clientside.set_props('replay-airport-direction', {value:'both'});
        const place = root.suntrainHome?.places?.find(p => p.id === root.suntrainReplay?.day?.city);
        if (place) root.dash_clientside.set_props('replay-modes', {value:place.default_modes});
    }
    function chip(label, title, action) {
        const button = document.createElement('button'); button.type = 'button';
        const text = document.createElement('span'); bind(text, label);
        const cross = document.createElement('span'); cross.textContent = '×'; cross.setAttribute('aria-hidden', 'true');
        button.append(text, cross);
        root.suntrainI18n.bind(button, 'Remove filter: ' + title, 'aria-label');
        button.addEventListener('click', action); return button;
    }
    function update(replay, force = false) {
        const flight = replay.day?.replay_kind === 'flights';
        if ($('replay-flight-view-field')) $('replay-flight-view-field').hidden = !flight;
        const filters = replay.filters;
        if (!filters) return;
        const signature = JSON.stringify([replay.day.city, filters, root.suntrainI18n.language]);
        if (!force && signature === lastSignature) return;
        lastSignature = signature;
        const host = $('replay-filter-chips'); host.replaceChildren();
        for (const [key, id, name] of fields) for (const value of filters[key] || []) {
            if (!flight && ['carriers','airports','fromCountries','toCountries'].includes(key)) continue;
            if (flight && ['operators','directions','stations'].includes(key)) continue;
            let label = value;
            if (key === 'carriers') label = replay.day.flight_groups?.[value.replace('group:', '')]
                || replay.day.flight_brands?.[value.replace('brand:', '')] || value;
            if (key === 'fromCountries' || key === 'toCountries') {
                const country = new Intl.DisplayNames([root.suntrainI18n.locale], {type:'region'}).of(value);
                label = root.suntrainI18n.t(name) + ': ' + country;
            }
            host.append(chip(label, value, () => root.dash_clientside.set_props(id, {value:filters[key].filter(v => v !== value)})));
        }
        if (filters.number) host.append(chip(filters.number, filters.number, () => root.dash_clientside.set_props('replay-number', {value:''})));
        if (flight && filters.flightScope !== 'both') host.append(chip(filters.flightScope === 'domestic' ? 'Domestic' : 'International', 'Flights', () => root.dash_clientside.set_props('replay-flight-scope', {value:'both'})));
        if (flight && filters.airports.length && filters.airportDirection !== 'both') host.append(chip(filters.airportDirection === 'arrivals' ? 'Arrivals' : 'Departures', 'Airport traffic', () => root.dash_clientside.set_props('replay-airport-direction', {value:'both'})));
        const place = root.suntrainHome?.places?.find(p => p.id === replay.day.city);
        if (!flight && place && JSON.stringify([...(filters.modes || [])].sort()) !== JSON.stringify([...place.default_modes].sort()))
            host.append(chip('Transport', 'Transport', () => root.dash_clientside.set_props('replay-modes', {value:place.default_modes})));
        if (host.children.length) {
            const clear = document.createElement('button'); clear.type = 'button'; bind(clear, 'Clear filters');
            clear.addEventListener('click', clearFilters); host.append(clear);
        }
    }
    document.addEventListener('pointerdown', event => {
        // Explicit exploration takes over from any scene still waiting to load.
        if (event.target.closest('#replay-panel') && root.suntrainHome)
            root.suntrainHome.pendingExperience = null;
    });
    document.addEventListener('click', event => {
        const target = event.target.closest('button');
        const id = target?.id;
        if (id === 'replay-back-explore' || id === 'nav-explore') navigate('home');
        if (id === 'nav-map') navigate('replay');
        if (id === 'nav-overview') navigate('overview');
        if (id === 'replay-fullscreen-filters') toggleFilters();
        if (id === 'replay-close-filters' || id === 'replay-drawer-backdrop') closeFilters(true);
        if (id === 'replay-clear-filters') clearFilters();
        if (id === 'replay-expand-details') {
            const expanded = $('replay-panel').classList.toggle('replay-sheet-expanded');
            target.setAttribute('aria-expanded', String(expanded));
            bind(target, expanded ? 'Collapse details' : 'Expand details');
        }
        if (event.target.closest('#replay-tools button') && !event.target.closest('.replay-options')) {
            $('replay-tools').open = false;
            if (id === 'replay-fullscreen' && root.suntrainReplay) root.suntrainReplay.returnFocus = $('replay-tools').querySelector('summary');
        }
        for (const menu of document.querySelectorAll('.playground-navigation, .playground-settings, #replay-tools, #replay-about'))
            if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener('keydown', event => {
        const drawer = $('replay-filter-controls'), opened = $('replay-panel')?.classList.contains('replay-show-filters');
        if (opened && !$('replay-calendar')?.hidden) return;
        if (root.suntrainReplay?.departures?.expanded) return;
        // Dash dropdowns render their option lists in a portal outside the drawer.
        const dropdowns = opened ? [...drawer.querySelectorAll('[aria-expanded="true"][aria-controls]')]
            .filter(el => $(el.getAttribute('aria-controls'))) : [];
        const popups = dropdowns.map(el => $(el.getAttribute('aria-controls')));
        if (popups.length && event.key === 'Escape') {
            event.preventDefault(); event.stopImmediatePropagation();
            for (const control of dropdowns) control.click();
            requestAnimationFrame(() => dropdowns[0].focus({preventScroll:true}));
            return;
        }
        if (event.key === 'Escape') {
            if (opened) { event.preventDefault(); event.stopImmediatePropagation(); closeFilters(true); return; }
            const menu = [...document.querySelectorAll('.playground-navigation[open], .playground-settings[open], #replay-tools[open], #replay-about[open]')].at(-1);
            if (menu) { event.preventDefault(); event.stopImmediatePropagation(); menu.open = false; menu.querySelector('summary').focus(); return; }
            if ($('replay-panel')?.classList.contains('replay-sheet-expanded')) {
                event.preventDefault(); event.stopImmediatePropagation(); $('replay-panel').classList.remove('replay-sheet-expanded');
                $('replay-expand-details').setAttribute('aria-expanded', 'false'); bind($('replay-expand-details'), 'Expand details');
                $('replay-expand-details').focus(); return;
            }
        }
        if (!opened || event.key !== 'Tab') return;
        const roots = [drawer, ...popups];
        const containsFocus = roots.some(el => el.contains(document.activeElement));
        const nodes = roots.flatMap(el => [...el.querySelectorAll('button, input, select, summary, [tabindex]')])
            .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length && (!el.checkVisibility || el.checkVisibility()));
        if (!nodes.length) return;
        const index = containsFocus ? nodes.indexOf(document.activeElement) : -1;
        const next = index < 0 ? (event.shiftKey ? nodes.length - 1 : 0)
            : (index + (event.shiftKey ? -1 : 1) + nodes.length) % nodes.length;
        event.preventDefault(); nodes[next].focus({preventScroll:true});
    }, true);
    document.addEventListener('suntrain:languagechange', () => { if (root.suntrainReplay?.day) update(root.suntrainReplay, true); });
    root.suntrainPlayground = {closePanels, closeFilters, clearFilters, update};
})(typeof window !== 'undefined' ? window : globalThis);
