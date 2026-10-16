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
        if (!path || !["track", "shape"].includes(path.quality) || path.coordinates.length < 2) return null;
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
                    index: i, state: service.mode && service.mode !== "train" ? "At stop" : "At station", station: station.name, next: stops[i + 1] ? day.stations[stops[i + 1][0]].name : null,
                    approximate: false};
        }
        const next = stops[i + 1], duration = next[1] - stop[2];
        if (duration <= 0) return null;
        const path = day.paths[service.legs[i]];
        const point = pointAlong(path, (now - stop[2]) / duration);
        return {lon: point ? point[0] : null, lat: point ? point[1] : null, load: stop[4], index: i,
                state: point ? (service.mode && service.mode !== "train" ? "Between stops" : "Between stations") : "Position unavailable",
                station: day.stations[stop[0]].name, next: day.stations[next[0]].name,
                approximate: !point};
    }
    function matches(service, filters, day) {
        const inScope = (values, value) => !values.length || values.includes(value);
        return inScope(filters.modes || [], service.mode || "train") && inScope(filters.operators, service.operator) && inScope(filters.lines, service.line) &&
            inScope(filters.directions, service.direction) &&
            (!filters.number || service.number.toLowerCase().includes(filters.number.toLowerCase().trim())) &&
            (!filters.stations.length || service.stops.some(stop => filters.stations.includes(day.stations[stop[0]].name)));
    }
    function routeFeatures(paths, ids) {
        return [...new Set(ids)].flatMap(id => {
            const path = paths[id];
            if (!path || !["track", "shape"].includes(path.quality) || path.coordinates.length < 2) return [];
            return [{type: "Feature", properties: {quality: path.quality},
                geometry: {type: "LineString", coordinates: path.coordinates}}];
        });
    }
    function hydrate(day) {
        // Shared relative schedules keep the day payload small; expand once in this browser.
        for (const service of day.services) {
            if (!service.pattern || service.stops) continue;
            const pattern = day.transit_patterns[service.pattern];
            for (const key of ["operator", "line", "direction", "origin", "destination"]) {
                if (pattern[key] !== undefined) service[key] = pattern[key];
            }
            service.stops = pattern.stops.map(([id, arrival, departure]) =>
                [id, service.departure + arrival, service.departure + departure, null, null, null, null]);
            service.legs = pattern.legs;
        }
        return day;
    }
    function vehicleColor(service) {
        if (service.mode === "tram") return root.suntrainTheme?.current === "dark" ? "#ffb56b" : "#c45e00";
        if (service.mode === "bus") return root.suntrainTheme?.current === "dark" ? "#70d4b0" : "#067b58";
        return lineColor(service.line);
    }
    function directionLabel(service) {
        if (!service.mode || service.mode === "train") return service.direction === "U" ? "Toward city" : "Away from city";
        return service.direction ? `Direction ${service.direction}` : "Scheduled service";
    }
    const core = {pointAlong, servicePosition, matches, lineColor, routeFeatures, hydrate, vehicleColor};
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
    const MELBOURNE_BOUNDS = [[144.55, -38.15], [145.6, -37.48]];
    class Replay {
        constructor() {
            this.day = null; this.filtered = []; this.selected = null;
            this.mapMode = "trains"; this.demandWindow = 30;
            this.demandIndex = []; this.demandSnapshot = null; this.demandMinute = null;
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
                    for (const id of ["routes", "stations", "selected-route", "trains", "selected-train", "demand"]) {
                        this.graph.addSource(`replay-${id}`, {type: "geojson", data: collection([])});
                    }
                    this.graph.addLayer({id: "replay-routes", type: "line", source: "replay-routes",
                        paint: {"line-color": ["case", ["==", ["get", "quality"], "track"], "#75978f", "#bd873d"], "line-width": 2, "line-opacity": 0.55}});
                    this.graph.addLayer({id: "replay-demand-glow", type: "heatmap", source: "replay-demand", layout: {visibility: "none"},
                        paint: {"heatmap-weight": ["interpolate", ["linear"], ["get", "boardings"], 0, 0, 1000, 1],
                            "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 6, 22, 10, 38, 14, 60],
                            "heatmap-intensity": 1.8, "heatmap-opacity": 0.65,
                            "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
                                0, "rgba(68,1,84,0)", 0.15, "rgba(68,1,84,0.5)", 0.3, "#3b528b", 0.5, "#21918c", 0.75, "#5ec962", 1, "#fde725"]}});
                    this.graph.addLayer({id: "replay-selected-route", type: "line", source: "replay-selected-route",
                        paint: {"line-color": "#115d51", "line-width": 4, "line-opacity": 0.8}});
                    this.graph.addLayer({id: "replay-stations", type: "circle", source: "replay-stations",
                        paint: {"circle-color": "#6d8980", "circle-radius": 2.5, "circle-stroke-width": 0.7, "circle-stroke-color": "white"}});
                    this.graph.addLayer({id: "replay-demand-stations", type: "circle", source: "replay-demand", layout: {visibility: "none", "circle-sort-key": ["get", "boardings"]},
                        paint: {"circle-color": ["interpolate", ["linear"], ["get", "boardings"], ...root.suntrainDemand.scale.flat()],
                            "circle-radius": ["interpolate", ["linear"], ["get", "boardings"], 0, 5, 500, 7, 2000, 10, 5000, 13],
                            "circle-stroke-color": "#fff", "circle-stroke-width": 1.5, "circle-opacity": 0.95}});
                    this.graph.addLayer({id: "replay-selected-train", type: "circle", source: "replay-selected-train",
                        paint: {"circle-color": "#18232d", "circle-radius": 11, "circle-opacity": 0.85}});
                    this.graph.addLayer({id: "replay-trains", type: "circle", source: "replay-trains",
                        paint: {"circle-color": ["get", "color"], "circle-radius": ["get", "radius"],
                            "circle-stroke-color": "#fff", "circle-stroke-width": 1.1, "circle-opacity": 0.95}});
                    this.popup = new root.maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 10});
                    this.graph.on("click", "replay-trains", e => this.select(e.features[0].properties.id));
                    this.graph.on("mousemove", "replay-trains", e => {
                        this.graph.getCanvas().style.cursor = "pointer";
                        this.demandPopupId = null;
                        const feature = e.features[0], service = this.filtered.find(s => s.id === feature.properties.id);
                        if (!service) return;
                        const content = node("div", undefined, "replay-map-tooltip");
                        content.append(node("strong", `${service.line} · ${service.number}`),
                            node("div", `${service.origin} → ${service.destination}`),
                            node("div", service.mode === "train" ? `${feature.properties.load ?? "Unknown"} passengers (rounded)` : "Passenger counts unavailable"));
                        if (feature.properties.approximate) content.append(node("div", "Approximate route"));
                        this.popup.setLngLat(feature.geometry.coordinates).setDOMContent(content).addTo(this.graph);
                    });
                    this.graph.on("mouseleave", "replay-trains", () => { this.graph.getCanvas().style.cursor = ""; this.popup.remove(); });
                    for (const event of ["click", "mousemove"]) this.graph.on(event, "replay-demand-stations", e => {
                        if (this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]}).length) return;
                        this.graph.getCanvas().style.cursor = "pointer";
                        this.showDemandPopup(Number(e.features[0].properties.id));
                    });
                    this.graph.on("mouseleave", "replay-demand-stations", () => {
                        this.demandPopupId = null; this.graph.getCanvas().style.cursor = ""; this.popup.remove();
                    });
                    this.graph.on("click", "replay-stations", e => {
                        if (this.mapMode !== "trains") {
                            if (!this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]}).length) this.showDemandPopup(Number(e.features[0].properties.id));
                            return;
                        }
                        if (this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]}).length) return;
                        this.popup.setLngLat(e.features[0].geometry.coordinates).setDOMContent(node("strong", e.features[0].properties.name)).addTo(this.graph);
                    });
                    this.mapReady = true;
                    this.demandLegendMedia = root.matchMedia("(max-width: 520px)");
                    const resizeLegend = () => { $("replay-demand-legend").open = !this.demandLegendMedia.matches; };
                    this.demandLegendMedia.addEventListener("change", resizeLegend);
                    resizeLegend();
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
            this.followSelected = !!value && !!this.selected && this.mapMode !== "demand";
            root.dash_clientside.set_props("replay-follow", {children: this.followSelected ? "Following service" : "Follow service", disabled: !this.selected || this.mapMode === "demand"});
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
            this.day = hydrate(day); this.now = Math.min(day.end, Math.max(day.start, day.initial));
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
                attribution.textContent = "Railway geometry is unavailable. Train positions are shown at stations only. Passenger counts are rounded to the nearest 10.";
            }
            if (day.transit?.available) {
                const link = node("a", `Tram & bus timetables: PTV archive ${day.transit.source_date} · CC BY 4.0`);
                link.href = day.transit.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
                attribution.append(document.createTextNode(" "), link, document.createTextNode(". Buses include complete journeys serving Melbourne and surrounds. Tram/bus passenger counts are unavailable."));
            }
        }
        applyTheme() {
            const dark = root.suntrainTheme.current === "dark";
            if (this.mapReady) {
                root.suntrainTheme.styleMap(this.graph);
                this.graph.setPaintProperty("replay-selected-route", "line-color", dark ? "#8ae1ca" : "#115d51");
                this.graph.setPaintProperty("replay-demand-stations", "circle-stroke-color", dark ? "#e4eef0" : "#fff");
                this.graph.setPaintProperty("replay-stations", "circle-color", dark ? "#a6bdb5" : "#6d8980");
                this.graph.setPaintProperty("replay-stations", "circle-stroke-color", dark ? "#17212b" : "#fff");
                this.graph.setPaintProperty("replay-selected-train", "circle-color", dark ? "#f2f8fa" : "#18232d");
                this.graph.setPaintProperty("replay-trains", "circle-stroke-color", dark ? "#101a23" : "#fff");
                this.graph.setPaintProperty("replay-routes", "line-color", ["case", ["==", ["get", "quality"], "track"], dark ? "#88aea4" : "#75978f", dark ? "#edb36b" : "#bd873d"]);
            }
            this.updateLegend();
            const detail = document.querySelector(".replay-detail-line");
            if (detail && this.selected) detail.style.color = vehicleColor(this.selected);
            if (this.day && this.mapReady) this.paint(true);
        }
        updateLegend() {
            if (!$("replay-legend")) return;
            const legend = $("replay-legend"); legend.replaceChildren();
            const lines = [...new Set(this.filtered.map(s => s.mode === "tram" ? "Trams" : s.mode === "bus" ? "Buses" : s.line))].sort();
            for (const line of lines) {
                const item = node("span", undefined, "replay-legend-item");
                const swatch = node("span", undefined, "replay-legend-swatch"); swatch.style.background = line === "Trams" ? vehicleColor({mode: "tram"}) : line === "Buses" ? vehicleColor({mode: "bus"}) : lineColor(line);
                item.append(swatch, document.createTextNode(line)); legend.append(item);
            }
        }
        applyFilters(filters, display) {
            this.filters = filters; this.display = display;
            const sizeHelp = $("replay-size-help");
            if (sizeHelp) sizeHelp.hidden = !display.includes("load");
            this.filtered = this.day.services.filter(service => matches(service, filters, this.day));
            const routes = this.day.services.filter(service => matches(service, {...filters, lines: [], stations: [], directions: [], number: ""}, this.day));
            root.dash_clientside.set_props("replay-lines", {options: [...new Set(routes.map(s => s.line))].sort()});
            this.demandIndex = root.suntrainDemand.buildIndex(this.filtered, this.day);
            this.demandMinute = null; this.demandPopupId = null; this.popup?.remove();
            if (this.selected && !this.filtered.some(s => s.id === this.selected.id)) {
                this.selected = null; this.emptyDetails();
            }
            this.staticDirty = true;
            this.updateLegend();
            let approximate = 0, total = 0, uncertain = 0;
            for (const service of this.filtered) {
                for (const id of service.legs) { total++; approximate += !["track", "shape"].includes(this.day.paths[id].quality); }
                uncertain += service.timing_uncertain ? 1 : 0;
            }
            const pieces = [];
            if (!this.filtered.length) pieces.push(this.day.services.length ? "No services match these filters. Clear a filter to explore this day." : "No recorded services for this business date.");
            if (approximate) pieces.push(`${approximate.toLocaleString()} of ${total.toLocaleString()} journey legs have unresolved paths. These are left as gaps; vehicle positions are hidden between those stops.`);
            else if (total) pieces.push("All selected journey legs have route geometry.");
            if (!this.day.transit?.available) pieces.push("Trams and buses are available for 24–30 June 2024 after preparing the archived timetable.");
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
            if (host) host.replaceChildren(node("h3", "Follow a service"),
                node("p", "Click a moving vehicle to see its journey and scheduled stops.", "replay-muted"),
                node("div", "Positions follow scheduled times. Train passenger counts are available; tram and bus counts are unavailable.", "replay-detail-note"));
        }
        select(id) {
            const service = this.filtered.find(s => s.id === id);
            if (!service) return;
            this.selected = service; this.staticDirty = true;
            $("replay-panel").classList.add("replay-has-selection");
            $("replay-close-details").hidden = false;
            this.setFollow(this.followSelected);
            const host = $("replay-details"); host.replaceChildren();
            const line = node("div", service.line, "replay-detail-line"); line.style.color = vehicleColor(service);
            host.append(line, node("h3", service.mode === "train" ? `Train ${service.number}` : service.line.split(" · ")[0]), node("p", `${service.origin} → ${service.destination}`, "replay-detail-route"),
                node("p", `${service.operator === "VLine" ? "V/Line" : service.operator} · ${directionLabel(service)}`, "replay-muted"));
            if (service.mode !== "train") host.append(node("p", `Trip ${service.number}`, "replay-muted replay-small"));
            const unresolved = service.legs.filter(id => !["track", "shape"].includes(this.day.paths[id]?.quality)).length;
            if (unresolved) host.append(node("p", `${unresolved} journey leg${unresolved === 1 ? " has" : "s have"} unresolved geometry. The route has gaps and this vehicle is hidden between those stops.`, "replay-approximate replay-small"));
            const live = node("div", undefined, "replay-service-status"); live.id = "replay-service-status"; host.append(live);
            host.append(node("h4", "Scheduled stops"));
            const scroll = node("div", undefined, "replay-stop-list"), table = node("table");
            const head = node("thead"), heading = node("tr");
            ["Stop / station", "Arr.", "Dep.", "Load"].forEach(label => heading.append(node("th", label)));
            head.append(heading); table.append(head);
            const body = node("tbody");
            service.stops.forEach((stop, i) => {
                const row = node("tr"); row.dataset.stopIndex = String(i);
                row.append(node("td", this.day.stations[stop[0]].name), node("td", shortTime.format(new Date(stop[1] * 1000))),
                    node("td", shortTime.format(new Date(stop[2] * 1000))), node("td", stop[4] == null ? "—" : stop[4].toLocaleString()));
                row.title = `Boardings: ${stop[5] ?? "unknown"}; alightings: ${stop[6] ?? "unknown"}`;
                body.append(row);
            });
            table.append(body); scroll.append(table); host.append(scroll,
                node("p", service.mode === "train" ? "Load = recorded departure passenger count, rounded to the nearest 10." : "Passenger counts are unavailable for trams and buses.", "replay-muted replay-small"));
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
                    host.append(node("div", position.load == null ? "Passenger load unavailable" : `${position.load.toLocaleString()} passengers · rounded estimate`));
                    if (position.approximate) host.append(node("div", "Railway path unresolved. Position hidden until the next recorded station.", "replay-approximate"));
                }
                if (this.selected.timing_uncertain) host.append(node("div", "Daylight-saving times are ambiguous for this service.", "replay-approximate"));
                $("replay-details").querySelectorAll("tr[data-stop-index]").forEach(row => {
                    row.classList.toggle("replay-current-stop", !!position && Number(row.dataset.stopIndex) === position.index);
                });
            }
        }
        updateStaticLayers() {
            const ids = [], stationIds = new Set();
            for (const service of this.filtered) {
                if (this.mapMode === "demand" && service.mode !== "train") continue;
                for (const stop of service.stops) stationIds.add(stop[0]);
                if (this.display.includes("routes")) ids.push(...service.legs);
            }
            const routes = routeFeatures(this.day.paths, ids);
            const selected = this.selected ? routeFeatures(this.day.paths, this.selected.legs) : [];
            const stations = this.display.includes("stations") ? [...stationIds].map(i => ({...this.day.stations[i], id: i})) : [];
            this.graph.getSource("replay-routes").setData(collection(routes));
            this.graph.getSource("replay-stations").setData(collection(stations.map(s => pointFeature([s.lon, s.lat], {name: s.name, id: s.id}))));
            this.graph.getSource("replay-selected-route").setData(collection(selected));
        }
        setMapMode(mode, minutes) {
            mode = ["trains", "demand", "both"].includes(mode) ? mode : "trains";
            minutes = [15, 30, 60].includes(Number(minutes)) ? Number(minutes) : 30;
            const changed = this.mapMode !== mode || this.demandWindow !== minutes;
            this.mapMode = mode; this.demandWindow = minutes;
            $("replay-panel").classList.toggle("replay-demand-only", mode === "demand");
            for (const id of ["replay-trains", "replay-selected-train", "replay-selected-route"])
                this.graph.setLayoutProperty(id, "visibility", mode === "demand" ? "none" : "visible");
            for (const id of ["replay-demand-glow", "replay-demand-stations"])
                this.graph.setLayoutProperty(id, "visibility", mode === "trains" ? "none" : "visible");
            $("replay-demand-legend").hidden = mode === "trains";
            $("replay-demand-window-field").hidden = mode === "trains";
            $("replay-legend").hidden = mode === "demand";
            if (changed) {
                this.staticDirty = true;
                this.demandMinute = null; this.demandPopupId = null; this.popup?.remove();
                this.setFollow(this.followSelected);
            }
        }
        showDemandPopup(id) {
            const row = this.demandSnapshot?.rows.find(row => row.id === id);
            if (!row) return;
            this.demandPopupId = id;
            const content = node("div", undefined, "replay-map-tooltip");
            const label = !row.knownCalls && row.missingCalls ? "Boardings unavailable" : `${row.boardings.toLocaleString()} recorded boardings`;
            content.append(node("strong", row.name), node("div", `${label} · last ${this.demandWindow} minutes`),
                node("div", `${shortTime.format(new Date(this.demandSnapshot.start * 1000))}–${shortTime.format(new Date(this.demandSnapshot.end * 1000))}`));
            if (!row.knownCalls && !row.missingCalls) content.append(node("div", "No recorded departures in this window."));
            if (row.missingCalls) content.append(node("div", `${row.missingCalls} departure counts unavailable.`));
            content.append(node("div", "Counts rounded to the nearest 10."));
            this.popup.setLngLat([row.lon, row.lat]).setDOMContent(content).addTo(this.graph);
        }
        paintDemand(force) {
            if (this.mapMode === "trains") return;
            const minute = Math.floor(this.now / 60), clock = performance.now();
            if (!force && (this.demandMinute === minute || clock - this.demandPaintTime < 200)) return;
            this.demandMinute = minute; this.demandPaintTime = clock;
            this.demandSnapshot = root.suntrainDemand.snapshot(this.demandIndex, minute * 60, this.demandWindow * 60);
            const snapshot = this.demandSnapshot;
            this.graph.getSource("replay-demand").setData(collection(snapshot.features));
            if (!$("replay-demand-scale").childElementCount) {
                for (const [count, color] of root.suntrainDemand.scale) {
                    const tick = node("span");
                    const swatch = node("i"); swatch.style.background = color;
                    tick.append(swatch, document.createTextNode(count.toLocaleString() + (count === 5000 ? "+" : "")));
                    $("replay-demand-scale").append(tick);
                }
            }
            setText("replay-demand-range", `Last ${this.demandWindow} min · ${shortTime.format(new Date(snapshot.start * 1000))}–${shortTime.format(new Date(snapshot.end * 1000))}`);
            setText("replay-demand-total", !snapshot.knownCalls && snapshot.missingCalls ? "Boarding counts unavailable" :
                `${snapshot.total.toLocaleString()} boardings · ${snapshot.stationCount} stations`);
            const notes = [];
            notes.push("Train passenger data only. Tram/bus counts unavailable.");
            if (!snapshot.stationCount) notes.push("No recorded boardings in this window.");
            if (snapshot.missingCalls) notes.push(`${snapshot.missingCalls} departure counts unavailable.`);
            if (snapshot.start < this.day.start) notes.push("Selected day only; earlier boardings excluded.");
            if (!notes.length) notes.push("Selected day & filters · counts rounded to 10");
            setText("replay-demand-note", notes.join(" "));
            if (this.demandPopupId !== null && this.demandPopupId !== undefined) this.showDemandPopup(this.demandPopupId);
        }
        async paint(force = false) {
            if (!this.active || !this.day || this.loading || !this.mapReady) return;
            if (this.busy) { this.paintAgain = true; return; }
            this.busy = true;
            const started = performance.now(), generation = this.generation;
            try {
                const trains = [];
                let selectedPosition = null, activeCount = 0, missingCount = 0;
                for (const service of this.filtered) {
                    const position = servicePosition(service, this.now, this.day);
                    if (!position) continue;
                    activeCount++;
                    if (service.id === this.selected?.id) selectedPosition = position;
                    if (position.lon === null || position.lat === null) { missingCount++; continue; }
                    const size = this.display.includes("load") && Number.isFinite(position.load) ? 8 + Math.min(22, Math.sqrt(Math.max(0, position.load)) * 0.6) : 11;
                    trains.push(pointFeature([position.lon, position.lat], {id: service.id, color: vehicleColor(service), radius: size / 2,
                        load: position.load, approximate: position.approximate}));
                }
                if (this.staticDirty) {
                    this.updateStaticLayers(); this.staticDirty = false;
                }
                this.paintDemand(force);
                this.activePositions = trains;
                this.missingPositions = missingCount;
                const selectedVisible = selectedPosition && selectedPosition.lon !== null && selectedPosition.lat !== null;
                this.graph.getSource("replay-trains").setData(collection(trains));
                this.graph.getSource("replay-selected-train").setData(collection(selectedVisible ? [pointFeature([selectedPosition.lon, selectedPosition.lat])] : []));
                if (generation !== this.generation) { this.staticDirty = true; this.paintAgain = true; return; }
                if (this.needsFit) this.metroView();
                if (this.followSelected && selectedVisible) this.graph.setCenter([selectedPosition.lon, selectedPosition.lat]);
                else if (this.followSelected && this.now > this.selected.stops[this.selected.stops.length - 1][2]) this.setFollow(false);
                if (force || performance.now() - this.lastUI >= 200 || !this.playing) {
                    this.lastUI = performance.now();
                    setText("replay-clock", clockFormat.format(new Date(this.now * 1000)));
                    setText("replay-clock-date", dateFormat.format(new Date(this.now * 1000)));
                    setText("replay-active-count", activeCount.toLocaleString());
                    setText("replay-position-note", missingCount ? ` · ${missingCount.toLocaleString()} vehicle position${missingCount === 1 ? "" : "s"} unavailable` : "");
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
        async sync(day, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, trigger) {
            this.lastTrigger = trigger;
            this.active = tab === "replay";
            if (!this.active) { this.pause(); if (this.isFullscreen()) this.exitFullscreen(); return; }
            this.revealTab();
            if (!day || day.business_date !== date || day.error) {
                this.pause(); this.loading = true;
                this.demandMinute = null; this.demandSnapshot = null; this.demandPopupId = null; this.popup?.remove();
                if ($("replay-demand-legend")) $("replay-demand-legend").hidden = true;
                setText("replay-position-note", "");
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
            this.setMapMode(mode, demandWindow);
            const filters = {modes: modes || [], operators: operators || [], lines: lines || [], directions: directions || [], stations: stations || [], number: number || ""};
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
        sync: function (day, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, play, restart, back, forward, fit) {
            const context = root.dash_clientside.callback_context;
            const trigger = context.triggered_id || context.triggered?.[0]?.prop_id?.split(".")[0];
            replay.sync(day, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, trigger).catch(error => {
                console.error("Train replay failed", error); replay.pause();
                setText("replay-load-message", "The replay could not start. Reload this page to try again.");
            });
            return day && day.business_date === date ? {business_date: day.business_date, error: !!day.error} : root.dash_clientside.no_update;
        }
    }});
})(typeof window !== "undefined" ? window : globalThis);
