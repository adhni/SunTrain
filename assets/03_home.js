(function (root) {
    "use strict";

    function placeCenter(place) {
        const [[west, south], [east, north]] = place.bounds;
        const longitude = (west + east) / 2;
        // Dateline-spanning bounds may use longitudes beyond 180 degrees.
        return [longitude > 180 || longitude < -180 ? ((longitude + 180) % 360 + 360) % 360 - 180 : longitude, (south + north) / 2];
    }
    function groupPlaces(places, project, radius = 42) {
        // A few dozen catalogue points: group nearby screen positions without
        // downloading any schedules or adding another geographic dependency.
        const points = places.filter(place => place.home_marker !== false).map(place => {
            const coordinates = placeCenter(place);
            return {place, coordinates, point: project(coordinates)};
        });
        const parents = points.map((_, i) => i);
        const find = i => parents[i] === i ? i : (parents[i] = find(parents[i]));
        const extents = points.map(p=>[p.point.x,p.point.y,p.point.x,p.point.y]);
        for (let i = 0; i < points.length; i++) for (let j = 0; j < i; j++) {
            if (Math.hypot(points[i].point.x - points[j].point.x, points[i].point.y - points[j].point.y) >= radius) continue;
            const a=find(i), b=find(j); if(a===b)continue;
            const box=[Math.min(extents[a][0],extents[b][0]),Math.min(extents[a][1],extents[b][1]),
                Math.max(extents[a][2],extents[b][2]),Math.max(extents[a][3],extents[b][3])];
            // Country discovery adds hundreds of pins. Bound each cluster's
            // screen footprint instead of chaining an entire continent together.
            if (box[2]-box[0] <= radius*2 && box[3]-box[1] <= radius*2) { parents[a]=b; extents[b]=box; }
        }
        const groups = new Map();
        points.forEach((point, i) => {
            const key = find(i);
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(point);
        });
        return [...groups.values()].map(members => ({
            members, coordinates: [0, 1].map(axis => members.reduce((sum, item) => sum + item.coordinates[axis], 0) / members.length),
        }));
    }
    function eligiblePlaces(places, kind) {
        return places.filter(place => kind === 'all' || (kind === 'flights'
            ? place.modes.includes('flight') : place.modes.some(mode => mode !== 'flight')));
    }
    function surprise(experiences, kind, previous, random = Math.random) {
        const eligible = experiences.filter(item => kind === 'all' || item.kind === kind);
        const candidates = eligible.length > 1 ? eligible.filter(item => item.id !== previous) : eligible;
        return candidates[Math.floor(random() * candidates.length)] || null;
    }
    if (typeof module !== "undefined" && module.exports) module.exports = {groupPlaces, placeCenter, eligiblePlaces, surprise};
    if (!root.document) return;

    const $ = id => document.getElementById(id);
    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) { if (root.suntrainI18n) root.suntrainI18n.bind(element, text); else element.textContent = text; }
        if (className) element.className = className;
        return element;
    }
    const modeNames = {flight: "Flights", train: "Trains", subway: "Metro", tram: "Trams", light_rail: "Light rail",
        regional_rail: "Regional rail", commuter_rail: "Commuter rail", limited_express: "Limited express",
        airport_rail: "Airport rail", high_speed_rail: "High-speed rail", ferry: "Ferries", silver_line: "Silver Line"};
    let dateFormat = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});

    class WorldMap {
        constructor() { this.markers = []; this.sequence = 0; this.kind = 'all'; }
        duration() { return root.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 650; }
        async start() {
            if (this.starting) return this.starting;
            this.places = JSON.parse($("home-panel").dataset.places);
            this.experiences = JSON.parse($("home-panel").dataset.experiences);
            this.starting = new Promise((resolve, reject) => {
                try {
                    this.map = new root.maplibregl.Map({container: "home-map", style: root.suntrainTheme.mapStyle(),
                        center: [25, 20], zoom: 1, minZoom: -1, maxZoom: 18, renderWorldCopies: false,
                        dragRotate: false, pitchWithRotate: false});
                    this.map.addControl(new root.maplibregl.NavigationControl({showCompass: false}), "top-right");
                    this.map.once("style.load", () => {
                        this.ready = true; this.reset(false); this.renderMarkers(); resolve();
                    });
                    this.map.on("zoomend", () => this.renderMarkers());
                    this.map.on("resize", () => this.renderMarkers());
                    $("home-reset").addEventListener("click", () => this.reset(true));
                    for (const button of document.querySelectorAll('[data-home-kind]'))
                        button.addEventListener('click', () => this.setKind(button.dataset.homeKind));
                    for (const button of document.querySelectorAll('[data-watch]'))
                        button.addEventListener('click', () => this.watch(button.dataset.watch));
                    for (const button of document.querySelectorAll('[data-flight-place]'))
                        button.addEventListener('click', () => this.openReplay(button.dataset.flightPlace));
                    $('home-surprise').addEventListener('click', () => {
                        const item = surprise(this.experiences, this.kind, this.lastExperience);
                        if (item) this.watch(item.id);
                    });
                    this.formatExperiences();
                    document.addEventListener("suntrain:themechange", () => root.suntrainTheme.styleMap(this.map));
                    this.observer = new ResizeObserver(entries => {
                        if (entries[0].contentRect.width > 0) this.map.resize();
                    });
                    this.observer.observe($("home-map"));
                } catch (error) { reject(error); }
            });
            return this.starting;
        }
        reset(animate) {
            this.popup?.remove();
            this.map.fitBounds([[-170, -52], [180, 72]], {padding: 24, duration: animate ? this.duration() : 0});
            if (animate) root.dash_clientside.set_props("home-place", {value: null});
        }
        formatExperiences() {
            for (const item of this.experiences || []) {
                const tile = document.querySelector(`[data-experience="${item.id}"]`);
                const date = dateFormat.format(new Date(item.date + 'T12:00:00Z'));
                tile.querySelector('.home-experience-time').textContent = date + ' · ' + item.time + (item.zone === 'UTC' ? ' UTC' : ' · ');
            }
        }
        setKind(kind) {
            this.kind = kind;
            this.popup?.remove(); this.openPlace = null;
            for (const button of document.querySelectorAll('[data-home-kind]'))
                button.setAttribute('aria-pressed', String(button.dataset.homeKind === kind));
            const places = eligiblePlaces(this.places, kind);
            root.dash_clientside.set_props('home-kind', {data:kind});
            root.dash_clientside.set_props('home-place', {value:null});
            $('home-flight-regions').hidden = kind !== 'flights';
            root.suntrainI18n.bind($('home-count'), `${places.length} places to explore`);
            for (const tile of document.querySelectorAll('[data-experience]'))
                tile.hidden = kind !== 'all' && tile.dataset.kind !== kind;
            this.renderMarkers();
        }
        renderMarkers() {
            if (!this.ready || !this.map.getContainer().clientWidth) return;
            this.markers.forEach(marker => marker.remove()); this.markers = [];
            const groups = groupPlaces(eligiblePlaces(this.places, this.kind), coordinates => this.map.project(coordinates));
            for (const group of groups) {
                const cluster = group.members.length > 1;
                const flightCount=group.members.filter(member=>member.place.modes.includes('flight')).length;
                const kind=!flightCount?'transit':flightCount===group.members.length?'flights':'mixed';
                const button = node("button", undefined, `home-pin home-pin-${kind}${cluster ? " home-cluster" : ""}`);
                button.type = "button";
                const title = cluster ? `Explore ${group.members.length} places` : `Explore ${root.suntrainPlaces.placeName(group.members[0].place)}`;
                if(root.suntrainI18n) root.suntrainI18n.bind(button, title, "aria-label"); else button.setAttribute("aria-label", title); if(root.suntrainI18n)root.suntrainI18n.bind(button,title,"title");else button.title = title;
                if(flightCount) {
                    if(root.suntrainI18n)root.suntrainI18n.bind(button,'Includes flights','aria-description');
                    else button.setAttribute('aria-description','Includes flights');
                }
                const dot=node("span", cluster ? String(group.members.length) : flightCount ? '\u2708\uFE0E' : '▤', "home-pin-dot");
                dot.setAttribute('aria-hidden','true');button.append(dot);
                if (!cluster) button.append(node("span", root.suntrainPlaces.placeName(group.members[0].place), "home-pin-label"));
                button.addEventListener("click", event => {
                    event.stopPropagation();
                    if (!cluster) { this.showPlace(group.members[0].place.id); return; }
                    this.showCluster(group);
                });
                this.markers.push(new root.maplibregl.Marker({element: button}).setLngLat(group.coordinates).addTo(this.map));
            }
        }
        showCluster(group) {
            this.popup?.remove(); this.openPlace = null;
            const content = node('div', undefined, 'home-cluster-list');
            content.append(node('h3', 'Choose a place'));
            for (const {place} of [...group.members].sort((a,b)=>root.suntrainPlaces.placeName(a.place).localeCompare(root.suntrainPlaces.placeName(b.place)))) {
                const flight = place.modes.includes('flight');
                const button = node('button', undefined, 'home-cluster-place');
                button.type = 'button';
                button.append(node('span', flight ? '✈︎' : '▤', flight ? 'home-place-flight' : 'home-place-transit'), node('span', root.suntrainPlaces.placeName(place)));
                button.addEventListener('click', () => this.openReplay(place.id));
                content.append(button);
            }
            this.popup = new root.maplibregl.Popup({className:'home-popup', offset:22, maxWidth:'330px'})
                .setLngLat(group.coordinates).setDOMContent(content).addTo(this.map);
            content.querySelector('button')?.focus({preventScroll:true});
        }
        watch(id) {
            const item = this.experiences.find(item => item.id === id);
            if (!item) return;
            this.lastExperience = id;
            this.openReplay(item.place || item.city, id);
        }
        openReplay(city, experience = null) {
            this.places ||= JSON.parse($('home-panel').dataset.places);
            const place = this.places?.find(p=>p.id===city);
            if (!place) return;
            const shared = place && ['world','region','country','airport','experience'].includes(place.kind);
            const base = shared ? 'world_flights' : city;
            const replay = root.suntrainReplay;
            const continuing = !experience && shared && replay?.active && !replay.loading && replay.day?.city === base;
            if (!continuing) replay?.pause();
            const sequence = ++this.sequence;
            this.pendingExperience = experience ? {item:this.experiences.find(item => item.id === experience), sequence} : null;
            this.navSelection = city;
            root.dash_clientside.set_props('replay-place',{value:city});
            root.dash_clientside.set_props('replay-flight-place',{data:shared?city:null});
            if (!continuing) root.dash_clientside.set_props("home-choice", {data: {city:base, experience, sequence}});
            root.suntrainPlayground?.closePanels();
        }
        applyExperience(replay) {
            const pending = this.pendingExperience;
            if (!pending || !replay.active || replay.loading || !replay.mapReady || replay.day?.city !== pending.item.city) return;
            const item = pending.item;
            if (item.city === 'world_flights' && replay.place?.id !== (item.place || 'world_flights')) return;
            if (!pending.configured) {
                pending.configured = true;
                for (const id of ['replay-lines', 'replay-operators', 'replay-directions', 'replay-stations', 'replay-carriers', 'replay-airports', 'replay-from-countries', 'replay-to-countries'])
                    root.dash_clientside.set_props(id, {value:[]});
                root.dash_clientside.set_props('replay-number', {value:''});
                root.dash_clientside.set_props('replay-flight-scope', {value:'both'});
                root.dash_clientside.set_props('replay-flight-view', {value:'planes'});
                root.dash_clientside.set_props('replay-airport-direction', {value:'both'});
                root.dash_clientside.set_props('replay-map-mode', {value:'trains'});
                root.dash_clientside.set_props('replay-modes', {value:item.modes});
                root.dash_clientside.set_props('replay-speed', {value:60});
                root.dash_clientside.set_props('replay-date', {data:item.date});
                return;
            }
            const expected = item.city === 'world_flights' ? replay.day.services.filter(s=>root.suntrainPlaces.matchesPlace(s,replay.place,replay.day)).length : replay.day.services.length;
            if (replay.day.business_date !== item.date || replay.frequencyView || replay.filtered.length !== expected) return;
            if (JSON.stringify([...replay.day.loaded_modes].sort()) !== JSON.stringify([...item.modes].sort())) return;
            this.pendingExperience = null;
            replay.selected = null; replay.emptyDetails(); replay.departures.reset();
            replay.pause(); replay.speed = 60; replay.metroView(); replay.seek(item.at);
            if (!root.matchMedia('(prefers-reduced-motion: reduce)').matches) replay.play();
        }
        showPlace(id) {
            this.openPlace=id;
            const place = this.places.find(place => place.id === id);
            if (!place) return;
            if (place.home_marker === false) { this.openReplay(id); return; }
            const name = root.suntrainPlaces.placeName(place);
            const content = node("div", undefined, "home-place-card");
            content.append(node("span", "NEXT STOP", "replay-eyebrow"), node("h3", name));
            content.append(node("p", [...new Set(place.modes.map(mode => root.suntrainI18n?.translate(modeNames[mode] || "Buses") || modeNames[mode] || "Buses"))].join(" · "), "home-place-modes"));
            const formatDate = value => dateFormat.format(new Date(value + "T12:00:00Z"));
            content.append(node("p", place.start === place.end ? formatDate(place.start) : `${formatDate(place.start)} – ${formatDate(place.end)}`, "home-place-dates"));
            const open = node("button", "Open replay →", "home-open-replay"); open.type = "button";
            if(root.suntrainI18n) root.suntrainI18n.bind(open, `Open ${name} replay`, "aria-label"); else open.setAttribute("aria-label", `Open ${name} replay`);
            open.addEventListener("click", () => this.openReplay(place.id));
            content.append(open);
            this.popup?.remove();
            this.map.fitBounds(place.bounds, {padding: {top: 140, bottom: 65, left: 40, right: 40}, maxZoom: 7, duration: this.duration()});
            this.popup = new root.maplibregl.Popup({className: "home-popup", offset: 22, maxWidth: "310px"})
                .setLngLat(placeCenter(place)).setDOMContent(content).addTo(this.map);
        }
    }
    const home = new WorldMap();
    document.addEventListener("suntrain:languagechange", () => {
        dateFormat = new Intl.DateTimeFormat(root.suntrainI18n.locale, {day:"numeric",month:"short",year:"numeric",timeZone:"UTC"});
        home.renderMarkers();
        home.formatExperiences();
        const place=home.places?.find(place=>place.id===home.openPlace);
        const dates=document.querySelector('.home-place-dates'), modes=document.querySelector('.home-place-modes');
        if(place && dates){const format=value=>dateFormat.format(new Date(value+'T12:00:00Z'));dates.textContent=place.start===place.end?format(place.start):format(place.start)+' – '+format(place.end);}
        if(place && modes)modes.textContent=[...new Set(place.modes.map(mode=>root.suntrainI18n.translate(modeNames[mode] || 'Buses')))].join(' · ');
    });
    root.suntrainHome = home;
    root.dash_clientside = Object.assign({}, root.dash_clientside, {suntrainHome: {
        sync: async function (tab, place) {
            if (tab !== "home") return root.dash_clientside.no_update;
            try {
                await home.start();
                if (!$("main-content").classList.contains("home-active")) return root.dash_clientside.no_update;
                home.map.resize();
                if (place && place !== home.searchSelection) home.showPlace(place);
                home.searchSelection = place;
                return {ready: true};
            } catch (error) {
                $("home-map-message").textContent = "The world map could not load. Use Menu to open Map or Overview.";
                return {ready: false};
            }
        },
    }});
})(typeof window !== "undefined" ? window : globalThis);
