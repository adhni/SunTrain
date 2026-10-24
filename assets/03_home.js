(function (root) {
    "use strict";

    function groupPlaces(places, project, radius = 42) {
        // A few dozen catalogue points: group nearby screen positions without
        // downloading any schedules or adding another geographic dependency.
        const points = places.map(place => {
            const [[west, south], [east, north]] = place.bounds;
            const coordinates = [(west + east) / 2, (south + north) / 2];
            return {place, coordinates, point: project(coordinates)};
        });
        const parents = points.map((_, i) => i);
        const find = i => parents[i] === i ? i : (parents[i] = find(parents[i]));
        for (let i = 0; i < points.length; i++) for (let j = 0; j < i; j++) {
            if (Math.hypot(points[i].point.x - points[j].point.x, points[i].point.y - points[j].point.y) < radius)
                parents[find(i)] = find(j);
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
    if (typeof module !== "undefined" && module.exports) module.exports = {groupPlaces};
    if (!root.document) return;

    const $ = id => document.getElementById(id);
    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) { if (root.suntrainI18n) root.suntrainI18n.bind(element, text); else element.textContent = text; }
        if (className) element.className = className;
        return element;
    }
    const modeNames = {train: "Trains", subway: "Metro", tram: "Trams", light_rail: "Light rail",
        regional_rail: "Regional rail", commuter_rail: "Commuter rail", limited_express: "Limited express",
        airport_rail: "Airport rail", high_speed_rail: "High-speed rail", ferry: "Ferries", silver_line: "Silver Line"};
    let dateFormat = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {day: "numeric", month: "short", year: "numeric", timeZone: "UTC"});

    class WorldMap {
        constructor() { this.markers = []; this.sequence = 0; }
        duration() { return root.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 650; }
        async start() {
            if (this.starting) return this.starting;
            this.places = JSON.parse($("home-panel").dataset.places);
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
        renderMarkers() {
            if (!this.ready || !this.map.getContainer().clientWidth) return;
            this.markers.forEach(marker => marker.remove()); this.markers = [];
            const groups = groupPlaces(this.places, coordinates => this.map.project(coordinates));
            for (const group of groups) {
                const cluster = group.members.length > 1;
                const button = node("button", undefined, `home-pin${cluster ? " home-cluster" : ""}`);
                button.type = "button";
                const title = cluster ? `Zoom to ${group.members.length} places` : `Explore ${group.members[0].place.name}`;
                if(root.suntrainI18n) root.suntrainI18n.bind(button, title, "aria-label"); else button.setAttribute("aria-label", title); if(root.suntrainI18n)root.suntrainI18n.bind(button,title,"title");else button.title = title;
                button.append(node("span", cluster ? String(group.members.length) : "", "home-pin-dot"));
                if (!cluster) button.append(node("span", group.members[0].place.name, "home-pin-label"));
                button.addEventListener("click", event => {
                    event.stopPropagation();
                    if (!cluster) { this.showPlace(group.members[0].place.id); return; }
                    this.popup?.remove();
                    const coordinates = group.members.map(member => member.coordinates);
                    const bounds = new root.maplibregl.LngLatBounds(coordinates[0], coordinates[0]);
                    coordinates.forEach(point => bounds.extend(point));
                    this.map.fitBounds(bounds, {padding: 90, maxZoom: Math.min(10, this.map.getZoom() + 2.5), duration: this.duration()});
                });
                this.markers.push(new root.maplibregl.Marker({element: button}).setLngLat(group.coordinates).addTo(this.map));
            }
        }
        showPlace(id) {
            this.openPlace=id;
            const place = this.places.find(place => place.id === id);
            if (!place) return;
            const [[west, south], [east, north]] = place.bounds;
            const content = node("div", undefined, "home-place-card");
            content.append(node("span", "NEXT STOP", "replay-eyebrow"), node("h3", place.name));
            content.append(node("p", [...new Set(place.modes.map(mode => root.suntrainI18n?.translate(modeNames[mode] || "Buses") || modeNames[mode] || "Buses"))].join(" · "), "home-place-modes"));
            const formatDate = value => dateFormat.format(new Date(value + "T12:00:00Z"));
            content.append(node("p", place.start === place.end ? formatDate(place.start) : `${formatDate(place.start)} – ${formatDate(place.end)}`, "home-place-dates"));
            const open = node("button", "Open replay →", "home-open-replay"); open.type = "button";
            if(root.suntrainI18n) root.suntrainI18n.bind(open, `Open ${place.name} replay`, "aria-label"); else open.setAttribute("aria-label", `Open ${place.name} replay`);
            open.addEventListener("click", () => root.dash_clientside.set_props("home-choice", {data: {city: place.id, sequence: ++this.sequence}}));
            content.append(open);
            this.popup?.remove();
            this.map.fitBounds(place.bounds, {padding: {top: 140, bottom: 65, left: 40, right: 40}, maxZoom: 7, duration: this.duration()});
            this.popup = new root.maplibregl.Popup({className: "home-popup", offset: 22, maxWidth: "310px"})
                .setLngLat([(west + east) / 2, (south + north) / 2]).setDOMContent(content).addTo(this.map);
        }
    }
    const home = new WorldMap();
    document.addEventListener("suntrain:languagechange", () => {
        dateFormat = new Intl.DateTimeFormat(root.suntrainI18n.locale, {day:"numeric",month:"short",year:"numeric",timeZone:"UTC"});
        home.renderMarkers();
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
                $("home-map-message").textContent = "The world map could not load. Open Transport Replay above to explore a place.";
                return {ready: false};
            }
        },
    }});
})(typeof window !== "undefined" ? window : globalThis);
