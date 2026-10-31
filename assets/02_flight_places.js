(function (root) {
    'use strict';
    const $ = id => root.document?.getElementById(id);
    const t = text => root.suntrainI18n?.translate(text) || text;
    const locale = () => root.suntrainI18n?.locale || 'en-AU';
    const number = n => n.toLocaleString(locale());
    const regionNames = new Map();
    function regionName(code) {
        if (!regionNames.has(locale())) regionNames.set(locale(), new Map());
        const names = regionNames.get(locale());
        if (!names.has(code)) names.set(code, new Intl.DisplayNames([locale()], {type:'region'}).of(code));
        return names.get(code);
    }
    // Keep native labels as strings. Dynamic Dash component labels can remount
    // the popover and restore an earlier search_value while typing (Dash 4).
    // Extra presentation uses attributes/pseudo-elements, never React's children.
    const decorations = new Map();
    const label = (value, name, detail, count) => {
        decorations.set(value, {detail, count});
        return name;
    };
    function placeName(place) {
        if (place.kind === 'country') return regionName(place.country);
        if (place.kind === 'world') return t('World flights');
        return ['region','experience'].includes(place.kind) ? t(place.name) : place.name;
    }
    function matchesPlace(service, place, day) {
        if (!place || place.kind === 'world') return true;
        const a = day.stations[service.stops[0][0]], b = day.stations[service.stops.at(-1)[0]];
        if (place.kind === 'airport') return a.code === place.code || b.code === place.code;
        if (place.kind === 'country') return a.country === place.country || b.country === place.country;
        if (place.kind === 'experience') {
            if (place.carriers) return place.carriers.includes(service.carrier);
            if (place.codes) return place.codes.includes(a.code) || place.codes.includes(b.code);
            if (place.scope) return service.flight_scope === place.scope;
            return place.between[0].includes(a.country) && place.between[1].includes(b.country) ||
                place.between[0].includes(b.country) && place.between[1].includes(a.country);
        }
        return place.countries.includes(a.country) || place.countries.includes(b.country);
    }
    function airlineOptions(services, day, selected = []) {
        const carriers = new Map(), brands = new Map(), groups = new Map(), seen = new Set();
        const add = (map, code, name, color) => {
            if (!map.has(code)) map.set(code, {value:code, name, count:0, color});
            map.get(code).count++;
        };
        for (const service of services) {
            if (seen.has(service.id)) continue;
            seen.add(service.id);
            add(carriers, service.carrier, service.operator, service.color);
            if (service.flight_brand) add(brands, 'brand:'+service.flight_brand, day.flight_brands?.[service.flight_brand] || service.flight_brand);
            if (service.flight_group) add(groups, 'group:'+service.flight_group, day.flight_groups?.[service.flight_group] || service.flight_group);
        }
        // Keep a selected option removable even if another filter gives it zero matches.
        for (const value of selected) {
            const map = value.startsWith('group:') ? groups : value.startsWith('brand:') ? brands : carriers;
            if (!map.has(value)) {
                const service = day.services.find(s => s.carrier === value);
                map.set(value, {value, name:service?.operator || day.flight_groups?.[value.slice(6)] || day.flight_brands?.[value.slice(6)] || value, count:0});
            }
        }
        return [[carriers,'Airline'], [groups,'Airline group'], [brands,'Airline network']].flatMap(([map, kind]) =>
            [...map.values()].sort((a,b) => b.count-a.count || a.name.localeCompare(b.name,'en') || a.value.localeCompare(b.value,'en'))
                .map(row => ({value:row.value, count:row.count, search:`${row.value} ${row.name}`,
                    label:label(row.value, row.name, `${row.value.replace(/^(brand|group):/, '')} · ${t(kind)} · ${t('Captured flights')}`, row.count)})));
    }
    function placeOptions(places, kind = 'all', query = '', selected = null) {
        const q = (query || '').trim().toLocaleLowerCase(locale());
        const current = places.find(p => p.id === selected);
        const eligible = places.filter(p => kind === 'all' || (kind === 'flights' ? p.modes.includes('flight') : p.kind === 'transit'));
        const text = p => `${placeName(p)} ${p.name} ${p.code || ''} ${p.municipality || ''} ${p.country ? regionName(p.country) : ''} ${p.country || ''} ${p.kind === 'replay' ? t('Dated replay')+' saved original local replay' : ''} ${p.country==='GB'?'UK Britain':p.country==='US'?'USA United States':''}`;
        const groups = [['world','World flights'], ['region','Regions'], ['country','Countries & territories'],
            ['airport','Airports'], ['experience','Flight experiences'], ['transit','Rail & local transport'], ['replay','Dated replays']];
        const result = [];
        for (const [type, heading] of groups) {
            let rows = eligible.filter(p => p.kind === type && (!q || text(p).toLocaleLowerCase(locale()).includes(q)));
            if (!q && type === 'region') rows = rows.filter(p => !p.region || current?.id === 'region:'+p.region);
            if (!q && ['country','airport'].includes(type)) {
                if (current?.country && type === 'airport') rows = rows.filter(p => p.country === current.country);
                else if (current?.kind === 'region') rows = rows.filter(p => current.countries.includes(p.country));
                else if (current?.region) rows = rows.filter(p => p.region === current.region);
            }
            rows.sort((a,b) => {
                if (q) {
                    const rank = p => (p.country==='GB' && ['uk','britain'].includes(q) || p.country==='US' && q==='usa') ? 0 :
                        [p.code, p.country, placeName(p)].some(s => s?.toLowerCase() === q) ? 0 :
                        [placeName(p), p.municipality].some(s=>s?.toLowerCase().startsWith(q)) ? 1 : 2;
                    if (rank(a) !== rank(b)) return rank(a)-rank(b);
                }
                return type === 'region' ? 0 : type==='airport' || !q && type==='country' ? b.count-a.count || placeName(a).localeCompare(placeName(b)) : placeName(a).localeCompare(placeName(b));
            });
            const limit = q ? (type === 'airport' ? 35 : 25) : type === 'replay' ? 0 : type === 'airport' ? 8 : type === 'country' ? 12 : 100;
            rows = rows.slice(0, limit);
            // Keep the value valid while a different search is in progress.
            // The native dropdown still hides it when its search text differs.
            if (current?.kind === type && !rows.includes(current)) rows.push(current);
            if (!rows.length) continue;
            // A searchable list with clear sections; headings cannot become selections.
            if (!q) result.push({value:'heading:'+type, disabled:true, label:t(heading)});
            for (const p of rows) {
                const detail = p.kind === 'airport' ? `${p.code} · ${p.municipality || regionName(p.country)} · ${regionName(p.country)}` :
                    p.kind === 'replay' ? `${t(p.collection_scope || 'Original capture')} · ${p.start}${p.start!==p.end?'–'+p.end:''} · ${p.timezone==='UTC'?'UTC':t('Local timeline')}` :
                    p.kind === 'transit' ? t('Rail & local transport') : p.kind==='region' && p.region ?
                        `${t(places.find(row=>row.id==='region:'+p.region)?.name || p.region)} · ${t('Regions')}` : `${t(heading)} · ${t('Captured flights')}`;
                result.push({value:p.id, search:text(p), label:label(p.id, placeName(p), detail, p.count)});
            }
        }
        return result;
    }
    const api = {placeName, matchesPlace, airlineOptions, placeOptions};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainPlaces = api;
    if (!root.document) return;
    function decorate() {
        for (const input of root.document.querySelectorAll('.dash-dropdown-option input')) {
            const row=input.closest('.dash-dropdown-option'), copy=row.querySelector('.dash-options-list-option-text');
            const decoration=decorations.get(input.value);
            row.toggleAttribute('data-explore-heading',input.value.startsWith('heading:'));
            if (!copy) continue;
            if (decoration) {
                copy.setAttribute('data-explore-detail',decoration.detail);
                row.setAttribute('data-explore-count',Number.isFinite(decoration.count)?number(decoration.count):'');
            } else {
                copy.removeAttribute('data-explore-detail');row.removeAttribute('data-explore-count');
            }
        }
    }
    function observeOptions() {
        let queued=false;
        new MutationObserver(()=>{
            if (!queued) { queued=true; queueMicrotask(()=>{queued=false;decorate();}); }
        }).observe(document.body,{childList:true,subtree:true});
        decorate();
    }
    if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',observeOptions,{once:true}); else observeOptions();
    function places() { return root.suntrainHome?.places || JSON.parse($('home-panel')?.dataset.places || '[]'); }
    function updateAirlines(replay) {
        if (replay.day?.replay_kind !== 'flights' || !replay.filters) return;
        const filters = {...replay.filters, carriers:[]};
        const services = replay.day.services.filter(s => root.suntrainReplayCore.matches(s, filters, replay.day));
        const options = airlineOptions(services, replay.day, replay.filters.carriers);
        const signature = JSON.stringify([options.map(o=>[o.value,o.count]), root.suntrainI18n?.language]);
        if (signature !== replay.airlineOptionsSignature) {
            replay.airlineOptionsSignature = signature;
            root.dash_clientside.set_props('replay-carriers', {options:options.map(({count,...option})=>option)});
        }
        decorate();
    }
    function breadcrumbs(place) {
        const host = $('replay-place-breadcrumbs');
        host.hidden = !place;
        host.replaceChildren();
        if (!place) return;
        const all = places();
        const ids = ['world_flights'];
        if (place.kind === 'region' && place.region) ids.push('region:'+place.region);
        if (!['world','experience'].includes(place.kind)) ids.push(place.kind === 'region' ? place.id : 'region:'+place.region);
        if (place.kind === 'experience') ids.push(place.id);
        if (place.country) ids.push('country:'+place.country);
        if (place.kind === 'airport') ids.push(place.id);
        for (const id of ids) {
            const item = all.find(p=>p.id===id); if (!item) continue;
            if (host.children.length) { const gap=document.createElement('span'); gap.textContent='›'; gap.setAttribute('aria-hidden','true'); host.append(gap); }
            const button = document.createElement('button'); button.type='button'; button.textContent=placeName(item);
            button.addEventListener('click',()=>root.suntrainHome.openReplay(id));
            if (id === place.id) button.setAttribute('aria-current','location');
            host.append(button);
        }
    }
    function apply(replay, place, force = false) {
        const id = place?.id || replay.day.city;
        const changed = replay.placeSignature !== `${replay.day.revision}:${id}`;
        replay.placeSignature = `${replay.day.revision}:${id}`;
        replay.place = place;
        if (!changed && !force) return;
        breadcrumbs(place);
        const base = place ? replay.day.services.filter(s=>matchesPlace(s,place,replay.day)) : replay.day.services;
        replay.totalFlights = new Set(base.map(s=>s.id)).size;
        if (place) {
            replay.placeCoverage = {flights:replay.totalFlights, routes_returned:new Set(base.map(s=>s.route_id)).size,
                airports_returned:new Set(base.flatMap(s=>[s.stops[0][0],s.stops.at(-1)[0]])).size};
            const endpoints = [...new Set(base.flatMap(s=>[s.stops[0][0],s.stops.at(-1)[0]]))].map(i=>replay.day.stations[i]);
            const connections = ['airport','experience'].includes(place.kind) || place.kind === 'country' && place.airports <= 2;
            replay.openingFrame = connections ? root.suntrainFlights.bounds(endpoints, 0) || place.bounds :
                place.kind === 'world' ? root.suntrainFlights.openingBounds(replay.day) : place.bounds;
            root.suntrainI18n.bind($('replay-flight-scope-note'), place.kind === 'world' ? 'Combined captures' : place.kind === 'experience' ? placeName(place) : 'To, from and within '+placeName(place));
        } else replay.placeCoverage = null;
        if (changed && replay.mapReady) {
            replay.openingCamera = null;
            if (replay.departures?.station != null) replay.departures.reset();
            replay.metroView();
        }
    }
    function syncSelection(day, placeId) {
        const place = day.city === 'world_flights' ? places().find(p=>p.id === placeId && ['world','region','country','airport','experience'].includes(p.kind)) || places().find(p=>p.id==='world_flights') : null;
        const value = place?.id || day.city;
        root.suntrainHome.navSelection = value;
        root.dash_clientside.set_props('replay-place', {value});
        return place;
    }
    Object.assign(api, {updateAirlines, apply, syncSelection, places, breadcrumbs});
    root.dash_clientside = Object.assign({}, root.dash_clientside, {suntrainPlaces:{
        homeOptions:(query,kind,value)=>placeOptions(places(),kind,query,value),
        replayOptions:(query,value)=>placeOptions(places(),'all',query,value),
        choose:value=>{
            if (value && value !== root.suntrainHome?.navSelection) root.suntrainHome.openReplay(value);
            return {place:value};
        },
    }});
    document.addEventListener('suntrain:languagechange',()=>{
        for (const id of ['home-place','replay-place']) {
            const query=$(id)?.querySelector('input')?.value || '';
            root.dash_clientside.set_props(id,{options:placeOptions(places(),id==='home-place'?root.suntrainHome.kind:'all',query,
                id==='replay-place'?root.suntrainHome.navSelection:root.suntrainHome.searchSelection)});
        }
        const r=root.suntrainReplay;
        if (r?.day) { updateAirlines(r); apply(r,r.place,true); }
    });
})(typeof window !== 'undefined' ? window : globalThis);
