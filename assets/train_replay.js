(function (root) {
    "use strict";
    const LINE_NAMES = ["Alamein", "Belgrave", "Craigieburn", "Cranbourne", "Eastern", "Flemington Racecourse", "Frankston", "Glen Waverley", "Hurstbridge", "Lilydale", "Mernda", "North East", "Northern", "Pakenham", "Richmond and City Loop", "Sandringham", "South Western", "Stony Point", "Sunbury", "Upfield", "Werribee", "Western", "Williamstown"];
    const PALETTE = ["#9b4a9a", "#326bb3", "#b05829", "#329a5b", "#a34978", "#847423", "#22767a", "#775cba", "#c34548", "#297a46", "#bb663c", "#7662a1", "#907c1a", "#237da1", "#796969", "#ca4f84", "#84704e", "#536c9a", "#5d8634", "#aa5264", "#087f75", "#8550ac", "#56733f"];
    function lineColor(line) {
        const index = LINE_NAMES.indexOf(line);
        const dark = root.suntrainTheme?.current === "dark";
        if (index >= 0) {
            const color = PALETTE[index];
            if (!dark) return color;
            return "#" + color.slice(1).match(/../g).map(part => Math.round(parseInt(part, 16) * 0.7 + 255 * 0.3).toString(16).padStart(2, "0")).join("");
        }
        let hash = 0;
        for (const c of line) hash = ((hash << 5) - hash + c.charCodeAt(0)) | 0;
        return `hsl(${Math.abs(hash) % 360},55%,${dark ? 65 : 38}%)`;
    }
    function upperBound(values, value) {
        let lo = 0, hi = values.length;
        while (lo < hi) {
            const mid = (lo + hi) >>> 1;
            if (values[mid] <= value) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }
    function pointAlong(path, fraction) {
        const points = path.coordinates, distances = path.distances;
        if (fraction <= 0 || !distances.length || !distances[distances.length - 1]) return points[0];
        if (fraction >= 1) return points[points.length - 1];
        const distance = fraction * distances[distances.length - 1];
        const i = Math.min(upperBound(distances, distance), points.length - 1);
        const segment = distances[i] - distances[i - 1];
        const f = segment ? (distance - distances[i - 1]) / segment : 0;
        return [points[i - 1][0] + f * (points[i][0] - points[i - 1][0]),
                points[i - 1][1] + f * (points[i][1] - points[i - 1][1])];
    }
    function servicePosition(service, now, day) {
        const stops = service.stops;
        if (!stops.length || now < stops[0][1] || now > stops[stops.length - 1][2]) return null;
        // Find the most recent arrival. Exact departure belongs to the next leg.
        let lo = 0, hi = stops.length;
        while (lo < hi) {
            const mid = (lo + hi) >>> 1;
            if (stops[mid][1] <= now) lo = mid + 1;
            else hi = mid;
        }
        const i = Math.max(0, lo - 1), stop = stops[i];
        if (now < stop[2] || i === stops.length - 1) {
            const station = day.stations[stop[0]];
            return {lon: station.lon, lat: station.lat, load: now < stop[2] ? stop[3] : stop[4],
                    index: i, state: "At station", station: station.name, next: stops[i + 1] ? day.stations[stops[i + 1][0]].name : null,
                    approximate: false};
        }
        const next = stops[i + 1], duration = next[1] - stop[2];
        if (duration <= 0) return null;
        const path = day.paths[service.legs[i]];
        const point = pointAlong(path, (now - stop[2]) / duration);
        return {lon: point[0], lat: point[1], load: stop[4], index: i, state: "Between stations",
                station: day.stations[stop[0]].name, next: day.stations[next[0]].name,
                approximate: path.quality !== "track"};
    }
    function matches(service, filters, day) {
        const inScope = (values, value) => !values.length || values.includes(value);
        return inScope(filters.operators, service.operator) && inScope(filters.lines, service.line) &&
            inScope(filters.directions, service.direction) &&
            (!filters.number || service.number.toLowerCase().includes(filters.number.toLowerCase().trim())) &&
            (!filters.stations.length || service.stops.some(stop => filters.stations.includes(day.stations[stop[0]].name)));
    }
    const core = {pointAlong, servicePosition, matches, lineColor};
    if (typeof module !== "undefined" && module.exports) module.exports = core;
    if (!root.document) return;

    const clockFormat = new Intl.DateTimeFormat("en-AU", {timeZone: "Australia/Melbourne", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"});
    const dateFormat = new Intl.DateTimeFormat("en-AU", {timeZone: "Australia/Melbourne", day: "numeric", month: "short", year: "numeric", timeZoneName: "short"});
    const shortTime = new Intl.DateTimeFormat("en-AU", {timeZone: "Australia/Melbourne", hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
    const $ = id => document.getElementById(id);
    const setText = (id, text) => { const element = $(id); if (element && element.textContent !== String(text)) element.textContent = text; };
    function node(tag, text, className) {
        const result = document.createElement(tag);
        if (text !== undefined) result.textContent = text;
        if (className) result.className = className;
        return result;
    }
    const collection = features => ({type: "FeatureCollection", features});
    const pointFeature = (coordinates, properties = {}) => ({type: "Feature", properties, geometry: {type: "Point", coordinates}});
    const lineFeature = (path, properties = {}) => ({type: "Feature", properties,
        geometry: {type: "LineString", coordinates: path.coordinates.length > 1 ? path.coordinates : [path.coordinates[0], path.coordinates[0]]}});
    const MELBOURNE_BOUNDS = [[144.55, -38.15], [145.6, -37.48]];
    class Replay {
        constructor() {
            this.day = null; this.filtered = []; this.selected = null;
            this.active = false; this.playing = false; this.now = 0; this.speed = 60;
            this.display = ["routes", "stations"]; this.frame = null; this.busy = false;
            this.graph = null; this.staticDirty = true; this.lastUI = 0; this.lastPaint = 0;
            this.needsFit = true; this.generation = 0; this.loading = false;
            this.frameCount = 0; this.renderMilliseconds = 0;
            document.addEventListener("visibilitychange", () => { if (document.hidden) this.pause(); });
            document.addEventListener("fullscreenchange", () => this.syncFullscreen());
            document.addEventListener("suntrain:themechange", () => this.applyTheme());
            document.addEventListener("keydown", event => this.fullscreenKey(event));
        }
        pause() {
            this.playing = false;
            if (this.frame !== null) cancelAnimationFrame(this.frame);
            this.frame = null;
            setText("replay-play", "Play");
            const button = $("replay-play");
            if (button) button.setAttribute("aria-pressed", "false");
        }
        async connect() {
            if (this.connecting) return this.connecting;
            this.connecting = new Promise((resolve, reject) => {
                if (!root.maplibregl) { reject(new Error("MapLibre could not load")); return; }
                this.graph = new root.maplibregl.Map({container: "replay-map", center: [145.02, -37.82], zoom: 9,
                    dragRotate: false, pitchWithRotate: false, style: root.suntrainTheme.mapStyle()});
                this.graph.addControl(new root.maplibregl.NavigationControl({showCompass: false}), "top-right");
                this.graph.addControl(new root.maplibregl.ScaleControl({unit: "metric"}));
                $("replay-melbourne").addEventListener("click", () => this.metroView());
                $("replay-fullscreen").addEventListener("click", () => this.toggleFullscreen());
                $("replay-fullscreen-filters").addEventListener("click", () => {
                    const visible = $("replay-panel").classList.toggle("replay-show-filters");
                    $("replay-fullscreen-filters").setAttribute("aria-expanded", String(visible));
                });
                $("replay-follow").addEventListener("click", () => {
                    this.setFollow(!this.followSelected);
                    if (this.followSelected) this.graph.setZoom(Math.max(10, this.graph.getZoom()));
                    this.paint(true);
                });
                $("replay-close-details").addEventListener("click", () => {
                    this.selected = null; this.emptyDetails(); this.staticDirty = true; this.paint(true);
                });
                this.graph.on("dragstart", () => this.setFollow(false));
                // Train playback must not wait for external background tiles.
                this.graph.once("style.load", () => {
                    for (const id of ["routes", "stations", "selected-route", "trains", "selected-train"]) {
                        this.graph.addSource(`replay-${id}`, {type: "geojson", data: collection([])});
                    }
                    this.graph.addLayer({id: "replay-routes", type: "line", source: "replay-routes",
                        paint: {"line-color": ["case", ["==", ["get", "quality"], "track"], "#75978f", "#bd873d"], "line-width": 2, "line-opacity": 0.55}});
                    this.graph.addLayer({id: "replay-selected-route", type: "line", source: "replay-selected-route",
                        paint: {"line-color": "#115d51", "line-width": 4, "line-opacity": 0.8}});
                    this.graph.addLayer({id: "replay-stations", type: "circle", source: "replay-stations",
                        paint: {"circle-color": "#6d8980", "circle-radius": 2.5, "circle-stroke-width": 0.7, "circle-stroke-color": "white"}});
                    this.graph.addLayer({id: "replay-selected-train", type: "circle", source: "replay-selected-train",
                        paint: {"circle-color": "#18232d", "circle-radius": 11, "circle-opacity": 0.85}});
                    this.graph.addLayer({id: "replay-trains", type: "circle", source: "replay-trains",
                        paint: {"circle-color": ["get", "color"], "circle-radius": ["get", "radius"],
                            "circle-stroke-color": "#fff", "circle-stroke-width": 1.1, "circle-opacity": 0.95}});
                    this.popup = new root.maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 10});
                    this.graph.on("click", "replay-trains", e => this.select(e.features[0].properties.id));
                    this.graph.on("mousemove", "replay-trains", e => {
                        this.graph.getCanvas().style.cursor = "pointer";
                        const feature = e.features[0], service = this.filtered.find(s => s.id === feature.properties.id);
                        if (!service) return;
                        const content = node("div", undefined, "replay-map-tooltip");
                        content.append(node("strong", `${service.line} · ${service.number}`),
                            node("div", `${service.origin} → ${service.destination}`),
                            node("div", `${feature.properties.load ?? "Unknown"} passengers (rounded)`));
                        if (feature.properties.approximate) content.append(node("div", "Approximate route"));
                        this.popup.setLngLat(feature.geometry.coordinates).setDOMContent(content).addTo(this.graph);
                    });
                    this.graph.on("mouseleave", "replay-trains", () => { this.graph.getCanvas().style.cursor = ""; this.popup.remove(); });
                    this.graph.on("click", "replay-stations", e => {
                        if (this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]}).length) return;
                        this.popup.setLngLat(e.features[0].geometry.coordinates).setDOMContent(node("strong", e.features[0].properties.name)).addTo(this.graph);
                    });
                    this.mapReady = true;
                    this.applyTheme();
                    root.dash_clientside.set_props("replay-fullscreen", {disabled: false});
                    this.observer = new ResizeObserver(() => { this.graph.resize(); this.revealTab(); });
                    this.observer.observe($("replay-map"));
                    resolve(true);
                });
            }).catch(error => {
                console.error("Replay map initialization failed", error);
                setText("replay-load-message", "The map needs a browser with WebGL enabled. Reload the page to try again.");
                return false;
            });
            return this.connecting;
        }
        setupTimeline() {
            const host = $("replay-timeline");
            if (!host) return;
            let slider = host.querySelector("input");
            if (!slider) {
                slider = node("input"); slider.type = "range"; slider.step = "1";
                slider.setAttribute("aria-label", "Replay time");
                slider.addEventListener("input", () => this.seek(Number(slider.value)));
                host.append(slider);
            }
            slider.min = String(this.day.start); slider.max = String(this.day.end); slider.value = String(this.now);
            setText("replay-range-start", `${shortTime.format(new Date(this.day.start * 1000))} · ${dateFormat.format(new Date(this.day.start * 1000))}`);
            setText("replay-range-end", `${shortTime.format(new Date(this.day.end * 1000))} · ${dateFormat.format(new Date(this.day.end * 1000))}`);
        }
        revealTab() {
            if (!this.active) return;
            const tabs = document.querySelector(".view-tabs"), selected = tabs?.querySelector(".tab--selected");
            if (!selected || tabs.scrollWidth <= tabs.clientWidth) return;
            const item = selected.getBoundingClientRect(), host = tabs.getBoundingClientRect();
            if (item.right > host.right) tabs.scrollLeft += item.right - host.right;
            else if (item.left < host.left) tabs.scrollLeft -= host.left - item.left;
        }
        isFullscreen() {
            const panel = $("replay-panel");
            return !!panel && (document.fullscreenElement === panel || panel.classList.contains("replay-expanded"));
        }
        async toggleFullscreen() {
            if (this.isFullscreen()) { this.exitFullscreen(); return; }
            const panel = $("replay-panel");
            this.returnFocus = document.activeElement;
            if (panel.requestFullscreen && document.fullscreenEnabled) {
                try { await panel.requestFullscreen(); }
                catch (_) { panel.classList.add("replay-expanded"); }
            } else panel.classList.add("replay-expanded");
            this.syncFullscreen();
            panel.focus({preventScroll: true});
        }
        exitFullscreen() {
            $("replay-panel")?.classList.remove("replay-expanded");
            if (document.fullscreenElement === $("replay-panel")) {
                document.exitFullscreen().catch(() => {});
            }
            this.syncFullscreen();
        }
        syncFullscreen() {
            const expanded = !!this.isFullscreen(), panel = $("replay-panel");
            const wasExpanded = this.fullscreen;
            this.fullscreen = expanded;
            document.body.classList.toggle("replay-fullscreen-lock", expanded);
            root.dash_clientside.set_props("replay-fullscreen", {children: expanded ? "Exit fullscreen" : "Fullscreen"});
            $("replay-fullscreen")?.setAttribute("aria-pressed", String(expanded));
            if (!expanded) {
                panel?.classList.remove("replay-show-filters");
                $("replay-fullscreen-filters")?.setAttribute("aria-expanded", "false");
                if (wasExpanded && this.returnFocus?.isConnected && this.active) this.returnFocus.focus({preventScroll: true});
            }
            if (this.graph) requestAnimationFrame(() => this.graph.resize());
        }
        fullscreenKey(event) {
            if (!this.isFullscreen() || event.defaultPrevented) return;
            const panel = $("replay-panel");
            if (event.key === "Escape") {
                event.preventDefault(); this.exitFullscreen(); return;
            }
            if (event.key !== "Tab") return;
            const focusable = [...panel.querySelectorAll('button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])')]
                .filter(el => !el.disabled && el.getClientRects().length && el.tabIndex >= 0);
            if (!focusable.length) return;
            const first = focusable[0], last = focusable[focusable.length - 1];
            if (event.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) {
                event.preventDefault(); first.focus();
            }
        }
        setFollow(value) {
            this.followSelected = !!value && !!this.selected;
            root.dash_clientside.set_props("replay-follow", {children: this.followSelected ? "Following train" : "Follow train", disabled: !this.selected});
            $("replay-follow")?.setAttribute("aria-pressed", String(this.followSelected));
        }
        metroView() {
            if (!this.mapReady) return;
            this.setFollow(false);
            this.graph.fitBounds(MELBOURNE_BOUNDS, {padding: 25, duration: 0});
            this.needsFit = false;
        }
        load(day) {
            this.pause(); this.generation++;
            this.day = day; this.now = Math.min(day.end, Math.max(day.start, day.initial));
            this.selected = null; this.staticDirty = true; this.setupTimeline(); this.emptyDetails();
            const options = [...new Set(day.stations.map(s => s.name))].sort();
            root.dash_clientside.set_props("replay-stations", {options});
            const attribution = $("replay-attribution");
            attribution.replaceChildren();
            if (day.geometry.source_url) {
                const link = node("a", `${day.geometry.source} · geographic reference ${day.geometry.source_date}`);
                link.href = day.geometry.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
                const license = node("a", day.geometry.license || "CC BY 4.0");
                license.href = day.geometry.license_url; license.target = "_blank"; license.rel = "noopener noreferrer";
                attribution.append(link, document.createTextNode(" · "), license,
                    document.createTextNode(". Route geography may differ from FY 2023–24. Passenger counts are rounded to the nearest 10."));
            } else {
                attribution.textContent = "Railway geometry is unavailable. Paths are approximate station links. Passenger counts are rounded to the nearest 10.";
            }
        }
        applyTheme() {
            const dark = root.suntrainTheme.current === "dark";
            if (this.mapReady) {
                root.suntrainTheme.styleMap(this.graph);
                this.graph.setPaintProperty("replay-selected-route", "line-color", dark ? "#8ae1ca" : "#115d51");
                this.graph.setPaintProperty("replay-stations", "circle-color", dark ? "#a6bdb5" : "#6d8980");
                this.graph.setPaintProperty("replay-stations", "circle-stroke-color", dark ? "#17212b" : "#fff");
                this.graph.setPaintProperty("replay-selected-train", "circle-color", dark ? "#f2f8fa" : "#18232d");
                this.graph.setPaintProperty("replay-trains", "circle-stroke-color", dark ? "#101a23" : "#fff");
                this.graph.setPaintProperty("replay-routes", "line-color", ["case", ["==", ["get", "quality"], "track"], dark ? "#88aea4" : "#75978f", dark ? "#edb36b" : "#bd873d"]);
            }
            this.updateLegend();
            const detail = document.querySelector(".replay-detail-line");
            if (detail && this.selected) detail.style.color = lineColor(this.selected.line);
            if (this.day && this.mapReady) this.paint(true);
        }
        updateLegend() {
            if (!$("replay-legend")) return;
            const legend = $("replay-legend"); legend.replaceChildren();
            const lines = [...new Set(this.filtered.map(s => s.line))].sort();
            for (const line of lines) {
                const item = node("span", undefined, "replay-legend-item");
                const swatch = node("span", undefined, "replay-legend-swatch"); swatch.style.background = lineColor(line);
                item.append(swatch, document.createTextNode(line)); legend.append(item);
            }
        }
        applyFilters(filters, display) {
            this.filters = filters; this.display = display;
            const sizeHelp = $("replay-size-help");
            if (sizeHelp) sizeHelp.hidden = !display.includes("load");
            this.filtered = this.day.services.filter(service => matches(service, filters, this.day));
            if (this.selected && !this.filtered.some(s => s.id === this.selected.id)) {
                this.selected = null; this.emptyDetails();
            }
            this.staticDirty = true;
            this.updateLegend();
            let approximate = 0, total = 0, uncertain = 0;
            for (const service of this.filtered) {
                for (const id of service.legs) { total++; approximate += this.day.paths[id].quality !== "track"; }
                uncertain += service.timing_uncertain ? 1 : 0;
            }
            const pieces = [];
            if (!this.filtered.length) pieces.push(this.day.services.length ? "No services match these filters. Clear a filter to explore this day." : "No recorded services for this business date.");
            if (approximate) pieces.push(`${approximate.toLocaleString()} of ${total.toLocaleString()} journey legs use approximate station links (amber).`);
            else if (total) pieces.push("All selected journey legs have matched railway geometry.");
            if (uncertain) pieces.push(`${uncertain} services contain ambiguous daylight-saving times; earliest consistent times are shown.`);
            if (this.day.excluded_services) pieces.push(`${this.day.excluded_services} services omitted because their source times or coordinates are invalid.`);
            setText("replay-quality", pieces.join(" "));
            setText("replay-matching-count", ` · ${this.filtered.length.toLocaleString()} services in this day`);
        }
        fit() {
            const ids = new Set(this.filtered.flatMap(service => service.stops.map(stop => stop[0])));
            if (!ids.size || !this.graph) return;
            this.setFollow(false);
            const stations = [...ids].map(i => this.day.stations[i]);
            const latitudes = stations.map(s => s.lat), longitudes = stations.map(s => s.lon);
            const south = Math.min(...latitudes), north = Math.max(...latitudes), west = Math.min(...longitudes), east = Math.max(...longitudes);
            this.graph.fitBounds([[west, south], [east, north]], {padding: 40, maxZoom: 13, duration: 0});
            this.needsFit = false;
        }
        seek(value) {
            if (!this.day || this.loading) return;
            this.now = Math.min(this.day.end, Math.max(this.day.start, value));
            this.previousTick = performance.now();
            if (this.now === this.day.end) this.pause();
            this.paint(true);
        }
        play() {
            if (!this.active || !this.day || this.loading || !this.filtered.length || document.hidden) return;
            if (this.now >= this.day.end) this.now = this.day.start;
            this.playing = true; this.previousTick = performance.now();
            setText("replay-play", "Pause"); $("replay-play").setAttribute("aria-pressed", "true");
            if (this.frame === null) this.frame = requestAnimationFrame(t => this.tick(t));
        }
        tick(timestamp) {
            this.frame = null;
            if (!this.playing || !this.active || document.hidden) { this.pause(); return; }
            this.now = Math.min(this.day.end, this.now + (timestamp - this.previousTick) / 1000 * this.speed);
            this.previousTick = timestamp;
            if (timestamp - this.lastPaint >= 60) { this.lastPaint = timestamp; this.paint(); }
            if (this.now >= this.day.end) { this.pause(); this.paint(true); }
            else this.frame = requestAnimationFrame(t => this.tick(t));
        }
        emptyDetails() {
            this.setFollow(false);
            $("replay-panel")?.classList.remove("replay-has-selection");
            if ($("replay-close-details")) $("replay-close-details").hidden = true;
            const host = $("replay-details");
            if (host) host.replaceChildren(node("h3", "Follow a train"),
                node("p", "Click a moving train to see its journey, scheduled stops and passenger counts.", "replay-muted"),
                node("div", "Every dot is a recorded service. Movement between its stops is estimated from the timetable.", "replay-detail-note"));
        }
        select(id) {
            const service = this.filtered.find(s => s.id === id);
            if (!service) return;
            this.selected = service; this.staticDirty = true;
            $("replay-panel").classList.add("replay-has-selection");
            $("replay-close-details").hidden = false;
            this.setFollow(this.followSelected);
            const host = $("replay-details"); host.replaceChildren();
            const line = node("div", service.line, "replay-detail-line"); line.style.color = lineColor(service.line);
            host.append(line, node("h3", `Train ${service.number}`), node("p", `${service.origin} → ${service.destination}`, "replay-detail-route"),
                node("p", `${service.operator === "VLine" ? "V/Line" : service.operator} · ${service.direction === "U" ? "Toward city" : "Away from city"}`, "replay-muted"));
            const live = node("div", undefined, "replay-service-status"); live.id = "replay-service-status"; host.append(live);
            host.append(node("h4", "Scheduled stops"));
            const scroll = node("div", undefined, "replay-stop-list"), table = node("table");
            const head = node("thead"), heading = node("tr");
            ["Station", "Arr.", "Dep.", "Load"].forEach(label => heading.append(node("th", label)));
            head.append(heading); table.append(head);
            const body = node("tbody");
            service.stops.forEach((stop, i) => {
                const row = node("tr"); row.dataset.stopIndex = String(i);
                row.append(node("td", this.day.stations[stop[0]].name), node("td", shortTime.format(new Date(stop[1] * 1000))),
                    node("td", shortTime.format(new Date(stop[2] * 1000))), node("td", stop[4] === null ? "—" : stop[4].toLocaleString()));
                row.title = `Boardings: ${stop[5] ?? "unknown"}; alightings: ${stop[6] ?? "unknown"}`;
                body.append(row);
            });
            table.append(body); scroll.append(table); host.append(scroll,
                node("p", "Load = recorded departure passenger count, rounded to the nearest 10.", "replay-muted replay-small"));
            this.paint(true);
        }
        detailStatus(position) {
            if (!this.selected) return;
            const host = $("replay-service-status"); if (!host) return;
            const text = position ? `${position.state}: ${position.station}${position.next ? ` → ${position.next}` : " · Terminus"}` :
                (this.now < this.selected.stops[0][1] ? "This service has not started yet." : "This service has finished.");
            const signature = `${text}|${position?.load}|${position?.approximate}`;
            if (host.dataset.signature !== signature) {
                host.dataset.signature = signature; host.replaceChildren(node("strong", text));
                if (position) {
                    host.append(node("div", position.load === null ? "Passenger load unavailable" : `${position.load.toLocaleString()} passengers · rounded estimate`));
                    if (position.approximate) host.append(node("div", "Approximate route between these stations", "replay-approximate"));
                }
                if (this.selected.timing_uncertain) host.append(node("div", "Daylight-saving times are ambiguous for this service.", "replay-approximate"));
                $("replay-details").querySelectorAll("tr[data-stop-index]").forEach(row => {
                    row.classList.toggle("replay-current-stop", !!position && Number(row.dataset.stopIndex) === position.index);
                });
            }
        }
        updateStaticLayers() {
            const routes = [], selected = [];
            const seen = new Set(), stationIds = new Set();
            for (const service of this.filtered) {
                for (const stop of service.stops) stationIds.add(stop[0]);
                for (const id of service.legs) {
                    if (!seen.has(id) && this.display.includes("routes")) {
                        seen.add(id); const path = this.day.paths[id]; routes.push(lineFeature(path, {quality: path.quality}));
                    }
                }
            }
            if (this.selected) for (const id of this.selected.legs) selected.push(lineFeature(this.day.paths[id]));
            const stations = this.display.includes("stations") ? [...stationIds].map(i => this.day.stations[i]) : [];
            this.graph.getSource("replay-routes").setData(collection(routes));
            this.graph.getSource("replay-stations").setData(collection(stations.map(s => pointFeature([s.lon, s.lat], {name: s.name}))));
            this.graph.getSource("replay-selected-route").setData(collection(selected));
        }
        async paint(force = false) {
            if (!this.active || !this.day || this.loading || !this.mapReady) return;
            if (this.busy) { this.paintAgain = true; return; }
            this.busy = true;
            const started = performance.now(), generation = this.generation;
            try {
                const trains = [];
                let selectedPosition = null;
                for (const service of this.filtered) {
                    const position = servicePosition(service, this.now, this.day);
                    if (!position) continue;
                    const size = this.display.includes("load") ? 8 + Math.min(22, Math.sqrt(Math.max(0, position.load || 0)) * 0.6) : 11;
                    trains.push(pointFeature([position.lon, position.lat], {id: service.id, color: lineColor(service.line), radius: size / 2,
                        load: position.load, approximate: position.approximate}));
                    if (service.id === this.selected?.id) selectedPosition = position;
                }
                if (this.staticDirty) {
                    this.updateStaticLayers(); this.staticDirty = false;
                }
                this.activePositions = trains;
                this.graph.getSource("replay-trains").setData(collection(trains));
                this.graph.getSource("replay-selected-train").setData(collection(selectedPosition ? [pointFeature([selectedPosition.lon, selectedPosition.lat])] : []));
                if (generation !== this.generation) { this.staticDirty = true; this.paintAgain = true; return; }
                if (this.needsFit) this.metroView();
                if (this.followSelected && selectedPosition) this.graph.setCenter([selectedPosition.lon, selectedPosition.lat]);
                else if (this.followSelected && this.now > this.selected.stops[this.selected.stops.length - 1][2]) this.setFollow(false);
                if (force || performance.now() - this.lastUI >= 200 || !this.playing) {
                    this.lastUI = performance.now();
                    setText("replay-clock", clockFormat.format(new Date(this.now * 1000)));
                    setText("replay-clock-date", dateFormat.format(new Date(this.now * 1000)));
                    setText("replay-active-count", trains.length.toLocaleString());
                    const slider = $("replay-timeline")?.querySelector("input");
                    if (slider) { slider.value = String(this.now); slider.setAttribute("aria-valuetext", `${clockFormat.format(new Date(this.now * 1000))} ${dateFormat.format(new Date(this.now * 1000))}`); }
                    this.detailStatus(selectedPosition);
                }
                this.frameCount++; this.renderMilliseconds += performance.now() - started;
            } catch (error) {
                console.error("Train replay rendering failed", error); this.pause();
                setText("replay-load-message", "The map could not render. Reload this page to try again.");
            } finally {
                this.busy = false;
                if (this.paintAgain) { this.paintAgain = false; requestAnimationFrame(() => this.paint(true)); }
            }
        }
        async sync(day, tab, date, operators, lines, directions, stations, number, display, speed, trigger) {
            this.lastTrigger = trigger;
            this.active = tab === "replay";
            if (!this.active) { this.pause(); if (this.isFullscreen()) this.exitFullscreen(); return; }
            this.revealTab();
            if (!day || day.business_date !== date || day.error) {
                this.pause(); this.loading = true;
                root.dash_clientside.set_props("replay-play", {disabled: true});
                if ($("replay-map")) $("replay-map").classList.add("replay-is-loading");
                setText("replay-active-count", "—"); setText("replay-matching-count", day?.error ? " · Could not load this day" : " · Loading this day…");
                return;
            }
            this.loading = false;
            $("replay-map")?.classList.remove("replay-is-loading");
            const newDay = !this.day || this.day.business_date !== day.business_date || this.day.revision !== day.revision;
            if (newDay) this.load(day);
            if (!this.mapReady && !await this.connect()) return;
            if (!this.active || this.day.business_date !== day.business_date) return;
            this.speed = Number(speed) || 60;
            const filters = {operators: operators || [], lines: lines || [], directions: directions || [], stations: stations || [], number: number || ""};
            const filterSignature = JSON.stringify([filters, display]);
            if (newDay || this.filterSignature !== filterSignature) {
                this.filterSignature = filterSignature; this.applyFilters(filters, display || []);
            }
            root.dash_clientside.set_props("replay-play", {disabled: !this.filtered.length});
            if (!this.filtered.length) this.pause();
            // A queued button event must not restart a newly selected date.
            if (!newDay) {
                if (trigger === "replay-play") { if (this.playing) this.pause(); else this.play(); }
                if (trigger === "replay-restart") this.seek(day.start);
                if (trigger === "replay-back") this.seek(this.now - 60);
                if (trigger === "replay-forward") this.seek(this.now + 60);
            }
            if (trigger === "replay-fit") this.fit();
            this.paint(true);
            this.graph.resize();
        }
    }
    const replay = new Replay();
    // Exposed diagnostics support browser verification without transmitting frames.
    root.suntrainReplay = replay;
    root.dash_clientside = Object.assign({}, root.dash_clientside, {suntrainReplay: {
        sync: function (day, tab, date, operators, lines, directions, stations, number, display, speed, play, restart, back, forward, fit) {
            const context = root.dash_clientside.callback_context;
            const trigger = context.triggered_id || context.triggered?.[0]?.prop_id?.split(".")[0];
            replay.sync(day, tab, date, operators, lines, directions, stations, number, display, speed, trigger).catch(error => {
                console.error("Train replay failed", error); replay.pause();
                setText("replay-load-message", "The replay could not start. Reload this page to try again.");
            });
            return root.dash_clientside.no_update;
        }
    }});
})(typeof window !== "undefined" ? window : globalThis);
