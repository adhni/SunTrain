(function (root) {
    "use strict";
    const TRAIN_COLORS = {
        alamein: "#152C6B", belgrave: "#152C6B", glenwaverley: "#152C6B", lilydale: "#152C6B",
        craigieburn: "#FFBE00", sunbury: "#FFBE00", upfield: "#FFBE00",
        cranbourne: "#279FD5", pakenham: "#279FD5",
        frankston: "#028430", werribee: "#028430", williamstown: "#028430", stonypoint: "#028430",
        hurstbridge: "#BE1014", mernda: "#BE1014", sandringham: "#F178AF",
        flemingtonracecourse: "#95979A", showgrounds: "#95979A",
        eastern: "#8F1A95", northeast: "#8F1A95", northern: "#8F1A95", southwestern: "#8F1A95", western: "#8F1A95",
    };
    const TRAM_COLORS = {
        "1": "#B5BD00", "3": "#8DC8E8", "3a": "#8DC8E8", "5": "#D50032", "6": "#01426A",
        "11": "#6ECEB2", "12": "#007E92", "16": "#FBD872", "19": "#8A1B61", "30": "#534F96",
        "35": "#6B3529", "48": "#333434", "57": "#00C1D5", "58": "#969696", "59": "#00653A",
        "64": "#00AB8E", "67": "#956C58", "70": "#F59BBB", "72": "#9ABEAA", "75": "#00A9E0",
        "78": "#A0A0D6", "82": "#D2D755", "86": "#FFB500", "96": "#C6007E", "109": "#E87722",
    };
    const BUS_COLOR = "#FF8200";
    const ROAD_MODES = new Set(["bus", "mikrotrans", "feeder_bus", "transjabodetabek", "rusun_bus", "royaltrans", "shuttle_bus", "tourist_bus"]);
    function lineColor(line) {
        const name = String(line || "").toLowerCase().replace(/[^a-z0-9]/g, "");
        if (TRAIN_COLORS[name]) return TRAIN_COLORS[name];
        for (const [key, color] of Object.entries(TRAIN_COLORS)) {
            if (name.includes(key)) return color;
        }
        return "#95979A";
    }
    function tramRoute(service) {
        const name = String(service.route_short_name ?? service.route ?? service.line ?? "").trim();
        return name.match(/^(?:tram(?:\s+route)?\s*|route\s*)?0*(\d+[a-z]?)\b/i)?.[1].toLowerCase() || "";
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
    // Maintain the running set rather than checking the full service day each frame.
    class ActiveServices {
        constructor(services) {
            const rows = services.map(service => ({service,
                start: stopValue(service, 0, 1) + (service.timeOffset || 0),
                end: stopValue(service, stopCount(service) - 1, 2) + (service.timeOffset || 0)}));
            this.starts = rows.slice().sort((a, b) => a.start - b.start);
            this.ends = rows.sort((a, b) => a.end - b.end);
            this.active = new Set(); this.time = null; this.startCursor = 0; this.endCursor = 0;
        }
        at(now, rebuild = false) {
            if (rebuild || this.time === null || now < this.time) {
                this.active.clear(); this.startCursor = 0; this.endCursor = 0;
                while (this.startCursor < this.starts.length && this.starts[this.startCursor].start <= now) {
                    const row = this.starts[this.startCursor++];
                    if (row.end >= now) this.active.add(row.service);
                }
                while (this.endCursor < this.ends.length && this.ends[this.endCursor].end < now) this.endCursor++;
            } else {
                while (this.startCursor < this.starts.length && this.starts[this.startCursor].start <= now)
                    this.active.add(this.starts[this.startCursor++].service);
                while (this.endCursor < this.ends.length && this.ends[this.endCursor].end < now)
                    this.active.delete(this.ends[this.endCursor++].service);
            }
            this.time = now;
            return this.active;
        }
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
    function stopCount(service) { return service.stopIds ? service.stopIds.length : service.stops.length; }
    function stopValue(service, index, column) {
        return service.stopIds ? (column === 0 ? service.stopIds[index] : column < 3 ? service.times[2 * index + column - 1] : null) : service.stops[index][column];
    }
    function* stopIds(service) {
        if (service.stopIds) yield* service.stopIds;
        else for (const stop of service.stops) yield stop[0];
    }
    function servicePosition(service, now, day) {
        const length = stopCount(service);
        // Transit patterns retain relative times; train stops already use epoch seconds.
        now -= service.timeOffset || 0;
        if (!length || now < stopValue(service, 0, 1) || now > stopValue(service, length - 1, 2)) return null;
        // Find the most recent arrival. Exact departure belongs to the next leg.
        let lo = 0, hi = length;
        while (lo < hi) {
            const mid = (lo + hi) >>> 1;
            if (stopValue(service, mid, 1) <= now) lo = mid + 1;
            else hi = mid;
        }
        const i = Math.max(0, lo - 1), departure = stopValue(service, i, 2), stationId = stopValue(service, i, 0);
        if (now < departure || i === length - 1) {
            const station = day.stations[stationId];
            const located = Number.isFinite(station.lon) && Number.isFinite(station.lat);
            return {lon: located ? station.lon : null, lat: located ? station.lat : null, load: stopValue(service, i, now < departure ? 3 : 4) ?? null,
                    index: i, state: !located ? "Position unavailable" : service.mode === "ferry" ? "At pier" : service.mode && service.mode !== "train" ? "At stop" : "At station", station: station.name, next: i + 1 < length ? day.stations[stopValue(service, i + 1, 0)].name : null,
                    approximate: !located};
        }
        const duration = stopValue(service, i + 1, 1) - departure;
        if (duration <= 0) return null;
        const path = day.paths[service.legs[i]];
        const point = pointAlong(path, (now - departure) / duration);
        return {lon: point ? point[0] : null, lat: point ? point[1] : null, load: stopValue(service, i, 4) ?? null, index: i,
                state: point ? (service.mode === "ferry" ? "Between piers" : service.mode && service.mode !== "train" ? "Between stops" : "Between stations") : "Position unavailable",
                station: day.stations[stationId].name, next: day.stations[stopValue(service, i + 1, 0)].name,
                approximate: !point};
    }
    function matches(service, filters, day) {
        const inScope = (values, value) => !values.length || values.includes(value);
        return inScope(filters.modes || [], service.mode || "train") && inScope(filters.operators, service.operator) && inScope(filters.lines, service.line) &&
            inScope(filters.directions, service.direction) &&
            (!filters.number || service.number.toLowerCase().includes(filters.number.toLowerCase().trim())) &&
            (!filters.stations.length || (service.stopIds ? service.stopIds.some(id => filters.stations.includes(day.stations[id].name)) :
                service.stops.some(stop => filters.stations.includes(day.stations[stop[0]].name))));
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
        // Attach shared references only: never duplicate stop arrays for individual trips.
        for (const service of day.services) {
            if (!service.pattern || service.stops || service.stopIds) continue;
            const pattern = day.transit_patterns[service.pattern];
            for (const key of ["operator", "line", "direction", "origin", "destination", "color", "route_id", "frequency_based", "terminal_arrival_missing"]) {
                if (pattern[key] !== undefined) service[key] = pattern[key];
            }
            if (pattern.stop_pattern) {
                const topology = day.transit_stop_patterns[pattern.stop_pattern];
                service.stopIds = topology.stations; service.times = pattern.times; service.legs = topology.legs;
            } else { service.stops = pattern.stops; service.legs = pattern.legs; }
            service.timeOffset = service.departure;
        }
        return day;
    }
    function stopTime(service, stop, column) {
        return stop[column] + (service.timeOffset || 0);
    }
    function firstDeparture(service) {
        return stopValue(service, 0, 2) + (service.timeOffset || 0);
    }
    function departureActivity(services, start, end) {
        // Fifteen elapsed minutes per bin keeps DST and overnight days aligned
        // with the actual replay range. Count once when filters change.
        const counts = new Uint32Array(Math.max(1, Math.ceil((end - start) / 900)));
        for (const service of services) {
            const departure = firstDeparture(service);
            if (departure >= start && departure < end) counts[Math.floor((departure - start) / 900)]++;
        }
        return counts;
    }
    function* uniqueSchedules(services) {
        const seen = new Set();
        for (const service of services) {
            const key = service.stopIds || service.stops;
            if (seen.has(key)) continue;
            seen.add(key);
            yield service;
        }
    }
    function vehicleColor(service, city) {
        if (ROAD_MODES.has(service.mode)) {
            if (!city || city === "melbourne") return BUS_COLOR;
            if (city === "london") return "#DC241F";
            if (/^#[0-9a-f]{6}$/i.test(service.color || "")) return service.color;
            return {boston: "#FFC72C", london: "#DC241F"}[city] || "#6F818E";
        }
        if (/^#[0-9a-f]{6}$/i.test(service.color || "")) return service.color;
        if (service.mode === "silver_line") return "#7C878E";
        if (service.mode === "tram") {
            const route = tramRoute(service);
            return TRAM_COLORS[route] || TRAM_COLORS[route.replace(/[a-z]$/, "")] || "#95979A";
        }
        if (String(service.operator || "").toLowerCase().replace(/[^a-z]/g, "") === "vline") return "#8F1A95";
        return lineColor(service.line);
    }
    function directionLabel(service) {
        const label=rawDirectionLabel(service);return root.suntrainI18n?.translate(label) || label;
    }
    function rawDirectionLabel(service) {
        if (["subway", "light_rail", "regional_rail", "commuter_rail", "airport_rail", "silver_line", "high_speed_rail"].includes(service.mode)) return service.direction || "Scheduled service";
        if (!service.mode || service.mode === "train") {
            if (service.direction === "U") return "Toward city";
            if (service.direction === "D") return "Away from city";
            return service.direction || "Scheduled service";
        }
        return service.direction ? (/^Direction /.test(service.direction) ? service.direction : `Direction ${service.direction}`) : "Scheduled service";
    }
    function markerScale(load, sizeByPassengers) {
        return sizeByPassengers && Number.isFinite(load) ? 0.8 + 0.4 * Math.sqrt(Math.min(3000, Math.max(0, load)) / 3000) : 1;
    }
    function markerRadius(halo = 0) {
        const scale = ["coalesce", ["get", "sizeFactor"], 1];
        return ["interpolate", ["linear"], ["zoom"], ...root.suntrainVehicles.radiusStops.flatMap(([zoom, radius]) =>
            [zoom, ["+", halo, ["*", radius, scale]]])];
    }
    const core = {ActiveServices, pointAlong, servicePosition, matches, lineColor, routeFeatures, hydrate, stopTime, vehicleColor, firstDeparture, departureActivity};
    if (typeof module !== "undefined" && module.exports) module.exports = core;
    if (!root.document) return;

    let clockFormat, dateFormat, shortTime, shortDate;
    const $ = id => document.getElementById(id);
    const setText = (id, text) => { const element = $(id); if (element) { if (root.suntrainI18n) root.suntrainI18n.bind(element, text); else if(element.textContent !== String(text)) element.textContent = text; } };
    function node(tag, text, className) {
        const result = document.createElement(tag);
        if (text !== undefined) { if (root.suntrainI18n) root.suntrainI18n.bind(result, text); else result.textContent = text; }
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
            this.demandIndex = null; this.demandSnapshot = null; this.demandMinute = null;
            this.active = false; this.playing = false; this.now = 0; this.speed = 60;
            this.display = ["routes", "stations"]; this.frame = null; this.busy = false;
            this.graph = null; this.staticDirty = true; this.lastUI = 0; this.lastPaint = 0;
            this.needsFit = true; this.generation = 0; this.loading = false;
            this.frameCount = 0; this.renderMilliseconds = 0;
            this.activeIndex = null; this.qualityBySchedule = new Map(); this.requestGeneration = 0;
            document.addEventListener("visibilitychange", () => { if (document.hidden) this.pause(); });
            document.addEventListener("fullscreenchange", () => this.syncFullscreen());
            document.addEventListener("suntrain:themechange", () => this.applyTheme());
            document.addEventListener("suntrain:languagechange", () => {
                if (!this.day) return;
                this.localeFormatters(this.day);
                this.setupTimeline();
                this.updateActivity();
                if (this.departures?.visible) { this.departures.updateLocale(); }
                const status=$("replay-service-status"); if(status) status.dataset.signature="";
                for(const cell of document.querySelectorAll('[data-scheduled-at]')) {
                    const at=new Date(Number(cell.dataset.scheduledAt)*1000);
                    cell.textContent=shortTime.format(at)+(cell.dataset.withDate==='true'?' · '+shortDate.format(at):'');
                }
                this.departures?.updateJourneyLocale();
                this.paint(true);
                this.updateLegend();
            });
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
                const bounds = this.day?.bounds || MELBOURNE_BOUNDS;
                this.graph = new root.maplibregl.Map({container: "replay-map", bounds, fitBoundsOptions: {padding: 25},
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
                    if (this.departures?.expanded) { this.departures.setExpanded(false); return; }
                    this.selected = null; this.emptyDetails(); this.staticDirty = true; this.paint(true);
                    $("replay-open-departures").focus();
                });
                this.graph.on("dragstart", () => this.setFollow(false));
                this.graph.on("zoom", () => this.paint(true));
                // Train playback must not wait for external background tiles.
                this.graph.once("style.load", () => {
                    for (const id of ["routes", "stations", "selected-route", "trains", "selected-train", "demand"]) {
                        this.graph.addSource(`replay-${id}`, {type: "geojson", data: collection([])});
                    }
                    this.graph.addLayer({id: "replay-routes", type: "line", source: "replay-routes",
                        paint: {"line-color": "#78908a",
                            "line-width": ["interpolate", ["linear"], ["zoom"], 6, 0.8, 12, 1.2, 15, 1.6],
                            "line-opacity": ["interpolate", ["linear"], ["zoom"], 6, 0.28, 12, 0.4, 15, 0.5]}});
                    this.graph.addLayer({id: "replay-demand-glow", type: "heatmap", source: "replay-demand", layout: {visibility: "none"},
                        paint: {"heatmap-weight": ["interpolate", ["linear"], ["get", "boardings"], 0, 0, 1000, 1],
                            "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 6, 22, 10, 38, 14, 60],
                            "heatmap-intensity": 1.8, "heatmap-opacity": 0.65,
                            "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
                                0, "rgba(68,1,84,0)", 0.15, "rgba(68,1,84,0.5)", 0.3, "#3b528b", 0.5, "#21918c", 0.75, "#5ec962", 1, "#fde725"]}});
                    this.graph.addLayer({id: "replay-selected-route", type: "line", source: "replay-selected-route",
                        paint: {"line-color": "#115d51", "line-width": 4, "line-opacity": 0.8}});
                    this.graph.addLayer({id: "replay-stations", type: "circle", source: "replay-stations",
                        filter: ["in", ["get", "mode"], ["literal", ["train", "ferry"]]],
                        paint: {"circle-color": "#6d8980", "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 2, 9, 3, 12, 4, 15, 4.5],
                            "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 9, 1.2, 15, 1.5], "circle-stroke-color": "white",
                            "circle-opacity": ["interpolate", ["linear"], ["zoom"], 6, 0.4, 9, 0.7, 12, 0.9, 15, 1],
                            "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 6, 0.4, 9, 0.7, 12, 0.9, 15, 1]}});
                    this.graph.addLayer({id: "replay-local-stops", type: "circle", source: "replay-stations", minzoom: 12,
                        filter: ["in", ["get", "mode"], ["literal", ["tram", "bus"]]],
                        paint: {"circle-color": "#6d8980", "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 1.7, 15, 2.5],
                            "circle-stroke-width": 0.5, "circle-stroke-color": "white",
                            "circle-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0, 13, 0.75, 15, 1],
                            "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0, 13, 0.75, 15, 1]}});
                    this.graph.addLayer({id: "replay-demand-stations", type: "circle", source: "replay-demand", layout: {visibility: "none", "circle-sort-key": ["get", "boardings"]},
                        paint: {"circle-color": ["interpolate", ["linear"], ["get", "boardings"], ...root.suntrainDemand.scale.flat()],
                            "circle-radius": ["interpolate", ["linear"], ["get", "boardings"], 0, 5, 500, 7, 2000, 10, 5000, 13],
                            "circle-stroke-color": "#fff", "circle-stroke-width": 1.5, "circle-opacity": 0.95}});
                    this.graph.addLayer({id: "replay-station-focus", type: "circle", source: "replay-stations",
                        filter: ["==", ["get", "id"], -1],
                        paint: {"circle-radius": 8, "circle-opacity": 0, "circle-stroke-width": 2, "circle-stroke-color": "#1caa92"}});
                    this.graph.addLayer({id: "replay-vehicle-outline", type: "circle", source: "replay-trains",
                        paint: {"circle-color": "#17212b", "circle-radius": markerRadius(1.7), "circle-opacity": 0.9}});
                    this.graph.addLayer({id: "replay-selected-train", type: "circle", source: "replay-selected-train",
                        paint: {"circle-radius": markerRadius(3), "circle-opacity": 0,
                            "circle-stroke-color": "#18232d", "circle-stroke-width": 1.5}});
                    this.graph.addLayer({id: "replay-trains", type: "circle", source: "replay-trains",
                        paint: {"circle-color": ["get", "color"], "circle-radius": markerRadius(),
                            "circle-stroke-color": "#fff", "circle-stroke-width": 1.2, "circle-opacity": 0.95}});
                    this.popup = new root.maplibregl.Popup({closeButton: false, closeOnClick: false, offset: 10});
                    this.graph.on("click", e => {
                        const vehicles = this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]});
                        if (vehicles.length) { this.select(vehicles[0].properties.id); return; }
                        const station = this.stationNear(e.point);
                        if (!station) return;
                        if (this.mapMode === "trains") this.departures.open(Number(station.properties.id));
                        else { this.demandPinned = true; this.showDemandPopup(Number(station.properties.id)); }
                    });
                    this.graph.on("mousemove", e => {
                        const features = this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]});
                        if (!features.length) {
                            if (this.vehicleHover) { this.vehicleHover = false; this.popup.remove(); this.graph.getCanvas().style.cursor = ""; }
                            return;
                        }
                        this.vehicleHover = true;
                        this.graph.getCanvas().style.cursor = "pointer";
                        this.demandPinned = false; this.demandPopupId = null;
                        const feature = features[0], service = this.filtered.find(s => s.id === feature.properties.id);
                        if (!service) return;
                        const content = node("div", undefined, "replay-map-tooltip");
                        content.append(node("strong", `${service.line} · ${service.number}`),
                            node("div", `${service.origin} → ${service.destination}`));
                        if (feature.properties.load != null)
                            content.append(node("div", `${feature.properties.load} passengers (rounded)`));
                        if (feature.properties.approximate) content.append(node("div", "Approximate route"));
                        this.popup.setLngLat(feature.geometry.coordinates).setDOMContent(content).addTo(this.graph);
                    });
                    this.graph.on("mouseout", () => { this.stationHover = false; this.vehicleHover = false; this.graph.getCanvas().style.cursor = ""; if (!this.demandPinned) this.popup.remove(); });
                    for (const event of ["click", "mousemove"]) this.graph.on(event, "replay-demand-stations", e => {
                        if (this.graph.queryRenderedFeatures(e.point, {layers: ["replay-trains"]}).length) return;
                        this.graph.getCanvas().style.cursor = "pointer";
                        if (event === "mousemove" && this.demandPinned) return;
                        this.demandPinned = event === "click";
                        this.showDemandPopup(Number(e.features[0].properties.id));
                    });
                    this.graph.on("mouseleave", "replay-demand-stations", () => {
                        if (!this.demandPinned) { this.demandPopupId = null; this.popup.remove(); }
                        this.graph.getCanvas().style.cursor = "";
                    });
                    this.graph.on("mousemove", e => {
                        if (this.mapMode !== "trains") return;
                        if (this.vehicleHover) { this.stationHover = false; return; }
                        const station = this.stationNear(e.point);
                        this.graph.getCanvas().style.cursor = station ? "pointer" : "";
                        if (station) {
                            this.stationHover = true;
                            const content = node("div", undefined, "replay-map-tooltip");
                            content.append(node("strong", station.properties.name), node("div", "Click for departures"));
                            this.popup.setLngLat(station.geometry.coordinates).setDOMContent(content).addTo(this.graph);
                        } else if (this.stationHover) { this.stationHover = false; this.popup.remove(); }
                    });
                    this.mapReady = true;
                    this.demandLegendMedia = root.matchMedia("(max-width: 520px)");
                    const resizeLegend = () => { $("replay-demand-legend").open = !this.demandLegendMedia.matches; };
                    this.demandLegendMedia.addEventListener("change", resizeLegend);
                    resizeLegend();
                    this.applyTheme();
                    root.dash_clientside.set_props("replay-fullscreen", {disabled: false});
                    this.observer = new ResizeObserver(() => {
                        this.graph.resize(); this.revealTab();
                        const workspace=document.querySelector('.replay-workspace'),toolbar=document.querySelector('.replay-map-toolbar');
                        if(workspace && toolbar)workspace.style.setProperty('--replay-detail-top',Math.max(0,toolbar.getBoundingClientRect().bottom-workspace.getBoundingClientRect().top+8)+'px');
                    });
                    this.observer.observe(document.querySelector('.replay-map-toolbar'));
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
                if(root.suntrainI18n) root.suntrainI18n.bind(slider, "Replay time", "aria-label"); else slider.setAttribute("aria-label", "Replay time");
                const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("viewBox", "0 0 1000 32"); svg.setAttribute("preserveAspectRatio", "none");
                svg.setAttribute("aria-hidden", "true"); svg.classList.add("replay-activity");
                const preview = node("output", undefined, "replay-time-preview"); preview.hidden = true;
                preview.setAttribute("aria-hidden", "true");
                slider.addEventListener("input", () => { this.seek(Number(slider.value)); this.previewTime(Number(slider.value)); });
                const timeAt = event => {
                    const bounds = slider.getBoundingClientRect();
                    const fraction = Math.max(0, Math.min(1, (event.clientX - bounds.left - 8) / Math.max(1, bounds.width - 16)));
                    return this.day.start + fraction * (this.day.end - this.day.start);
                };
                host.addEventListener("pointermove", event => this.previewTime(timeAt(event)));
                host.addEventListener("pointerdown", event => {
                    if (event.target === slider || event.button !== 0) return;
                    slider.focus(); this.seek(Math.round(timeAt(event))); this.previewTime(this.now);
                });
                slider.addEventListener("focus", () => this.previewTime(Number(slider.value)));
                host.addEventListener("pointerleave", () => { preview.hidden = true; });
                slider.addEventListener("blur", () => { preview.hidden = true; });
                host.append(svg, slider, preview);
            }
            slider.min = String(this.day.start); slider.max = String(this.day.end); slider.value = String(this.now);
            setText("replay-range-start", shortTime.format(new Date(this.day.start * 1000)));
            setText("replay-range-end", shortTime.format(new Date(this.day.end * 1000)));
            if(root.suntrainI18n) root.suntrainI18n.bind($("replay-range-end"),"Next day","title"); else $("replay-range-end").title = "Next day";
            $("replay-range-end").setAttribute("aria-label", `${shortTime.format(new Date(this.day.end * 1000))} next day`);
            const labels = $("replay-timeline-labels");
            labels.querySelectorAll(".replay-time-tick").forEach(tick => tick.remove());
            // Position local-hour ticks by elapsed time, including daylight-saving days.
            for (let time = this.day.start + 900; time < this.day.end; time += 900) {
                if (this.day.end - time < 3600) continue; // Keep the last hour label clear of the arrival endpoint.
                const text = shortTime.format(new Date(time * 1000));
                if (!["06:00", "12:00", "18:00", "00:00"].includes(text)) continue;
                const tick = node("span", text, "replay-time-tick");
                tick.style.left = `${100 * (time - this.day.start) / (this.day.end - this.day.start)}%`;
                labels.append(tick);
            }
            labels.append($("replay-range-end"));
        }
        previewTime(time) {
            const host = $("replay-timeline"), preview = host.querySelector("output");
            if (!preview || !this.day) return;
            const date = new Date(Math.round(time) * 1000);
            if(root.suntrainI18n) root.suntrainI18n.bind(preview, `${clockFormat.format(date)} · ${shortDate.format(date)}`); else preview.textContent = `${clockFormat.format(date)} · ${shortDate.format(date)}`;
            preview.style.left = `${Math.max(84, Math.min(host.clientWidth - 84, host.clientWidth * (time - this.day.start) / (this.day.end - this.day.start)))}px`;
            preview.hidden = false;
        }
        updateActivity() {
            const svg = $("replay-timeline").querySelector("svg");
            if (!svg) return;
            const counts = departureActivity(this.filtered, this.day.start, this.day.end);
            const maximum = Math.max(1, ...counts), width = 1000 / counts.length;
            svg.replaceChildren();
            counts.forEach((count, index) => {
                if (!count) return;
                const bar = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                const height = Math.max(2, 30 * count / maximum);
                bar.setAttribute("x", String(index * width)); bar.setAttribute("y", String(32 - height));
                bar.setAttribute("width", String(Math.max(1, width - 1.5))); bar.setAttribute("height", String(height));
                bar.setAttribute("rx", "1.5"); svg.append(bar);
            });
        }
        revealTab() {
            if (!this.active) return;
            const tabs = document.querySelector(".view-tabs"), selected = tabs?.querySelector(".tab--selected");
            if (!selected || tabs.scrollWidth <= tabs.clientWidth) return;
            const item = selected.getBoundingClientRect(), host = tabs.getBoundingClientRect();
            if (item.right > host.right) tabs.scrollLeft += item.right - host.right;
            else if (item.left < host.left) tabs.scrollLeft -= host.left - item.left;
        }
        stationNear(point) {
            if (!this.display.includes("stations")) return null;
            const candidates = this.graph.queryRenderedFeatures([[point.x - 8, point.y - 8], [point.x + 8, point.y + 8]],
                {layers: ["replay-stations", "replay-local-stops"]});
            const distance = feature => {
                const p = this.graph.project(feature.geometry.coordinates);
                return Math.hypot(p.x - point.x, p.y - point.y);
            };
            return candidates.filter(f => distance(f) <= 10).sort((a, b) => distance(a) - distance(b))[0] || null;
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
            const focusable = [...panel.querySelectorAll('button, input, select, textarea, summary, a[href], [tabindex]:not([tabindex="-1"])')]
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
            this.graph.fitBounds(this.day?.bounds || MELBOURNE_BOUNDS, {padding: 25, duration: 0});
            this.needsFit = false;
        }
        localeFormatters(day) {
            const timeZone = day.timezone || "Australia/Melbourne";
            clockFormat = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {timeZone, hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"});
            dateFormat = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {timeZone, day: "numeric", month: "short", year: "numeric", timeZoneName: "short"});
            shortTime = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {timeZone, hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
            shortDate = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {timeZone, day: "numeric", month: "short"});
        }
        load(day) {
            const sameDay = this.day?.city === day.city && this.day?.business_date === day.business_date;
            const previousNow = this.now;
            this.pause(); this.generation++;
            if (this.day?.city !== day.city) this.needsFit = true;
            this.localeFormatters(day);
            this.filtered = []; this.filterSignature = null; this.activeIndex = null; this.activePositions = [];
            this.demandIndex = null; this.demandSnapshot = null; this.qualityBySchedule.clear();
            this.popup?.remove(); this.demandPopupId = null;
            if (this.mapReady) for (const id of ["replay-trains", "replay-selected-train", "replay-routes", "replay-stations", "replay-selected-route", "replay-demand"])
                this.graph.getSource(id)?.setData(collection([]));
            this.day = hydrate(day);
            if (root.suntrainI18n) {
                root.suntrainI18n.sourceNames.clear();
                for (const station of day.stations) root.suntrainI18n.sourceNames.add(station.name);
                for (const service of day.services) for (const key of ["line","operator","origin","destination","number"]) if(service[key]) root.suntrainI18n.sourceNames.add(service[key]);
            }
             this.now = Math.min(day.end, Math.max(day.start, sameDay ? previousNow : day.initial));
            this.departures?.reset();
            if ($("replay-vehicle-help")) $("replay-vehicle-help").hidden = day.city !== "melbourne";
            this.selected = null; this.staticDirty = true; this.setupTimeline(); this.emptyDetails();
            if(root.suntrainI18n) root.suntrainI18n.bind($("replay-melbourne"), `Return to the ${day.city_name} starting view`, "title");
            const options = [...new Set(day.stations.map(s => s.name))].sort();
            root.dash_clientside.set_props("replay-stations", {options});
            const attribution = $("replay-attribution");
            attribution.replaceChildren();
            if (day.schedule) {
                if (day.schedule.attribution) {
                    const source = node("a", day.schedule.attribution);
                    source.href = day.schedule.source_url;
                    const license = node("a", day.schedule.license);
                    license.href = day.schedule.license_url;
                    for (const link of [source, license]) {link.target = "_blank"; link.rel = "noopener noreferrer";}
                    attribution.append(source, document.createTextNode(" · "), license);
                    for (const credit of [day.schedule, ...(day.schedule.additional_geometry_sources || [])]) {
                        for (const key of ["geometry_source", "geometry_license"]) {
                            if (!credit[key] || !credit[key + "_url"]) continue;
                            const link = node("a", credit[key]); link.href = credit[key + "_url"];
                            link.target = "_blank"; link.rel = "noopener noreferrer";
                            attribution.append(document.createTextNode(" · "), link);
                        }
                    }
                    if (day.bus_schedule && day.bus_schedule.source_url !== day.schedule.source_url) {
                        const buses = node("a", day.bus_schedule.attribution); buses.href = day.bus_schedule.source_url;
                        buses.target = "_blank"; buses.rel = "noopener noreferrer";
                        attribution.append(document.createTextNode(" · "), buses);
                        for (const [label, url] of [["Bus timetable licence", day.bus_schedule.license_url], [day.bus_schedule.geometry_source || "Bus road geometry", day.bus_schedule.geometry_source_url]]) {
                            if (!url) continue;
                            const link = node("a", label); link.href = url;
                            link.target = "_blank"; link.rel = "noopener noreferrer";
                            attribution.append(document.createTextNode(" · "), link);
                        }
                    }
                    attribution.append(node("span", ". Scheduled positions are estimates. SunTrain is independent of the data providers and operators."));
                    return;
                }
                if (day.city === "singapore") {
                    const source = node("a", `LTA GTFS Schedule (Train), accessed ${day.schedule.source_date}`);
                    source.href = day.schedule.source_url;
                    const license = node("a", day.schedule.license);
                    license.href = day.schedule.license_url;
                    const osm = node("a", "Railway geometry © OpenStreetMap contributors · ODbL 1.0");
                    osm.href = "https://www.openstreetmap.org/copyright";
                    for (const link of [source, license, osm]) {link.target = "_blank"; link.rel = "noopener noreferrer";}
                    attribution.append(source, document.createTextNode(" · "), license, document.createTextNode(" · "), osm,
                        node("span", ". Snapshot schedules applied to 5–11 October 2026; positions are estimates. One Sunday NS trip has unresolved geometry. SunTrain is independent of LTA and the operators."));
                    return;
                }
                const chicago = day.city === "chicago";
                const nyc = day.city === "nyc";
                const link = node("a", nyc ? "MTA schedule data obtained from historical archives and hosted by SunTrain" : chicago ? "Data provided by Chicago Transit Authority · historical GTFS via MobilityDatabase" : "Data provided by MassDOT / MBTA · historical GTFS archive");
                link.href = day.schedule.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
                const license = node("a", day.schedule.license);
                license.href = day.schedule.license_url; license.target = "_blank"; license.rel = "noopener noreferrer";
                attribution.append(link, document.createTextNode(" · "), license,
                    node("span", nyc ? ". Regular December 2025–January 2026 NYC Subway and Staten Island Railway schedules; estimated positions follow published shapes, without guaranteed track-level accuracy or temporary service changes. Train passenger loads are unavailable. SunTrain is independent of MTA." : chicago ? ". Scheduled CTA transit replay for 2025; positions are estimates. Passenger counts are unavailable. This application is independent of CTA." :
                        ". Scheduled rail and Silver Line replay; positions are estimates. Passenger counts are unavailable. This application is independent of MBTA."));
                return;
            }
            if (day.geometry.source_url) {
                const link = node("a", `${day.geometry.source} · geographic reference ${day.geometry.source_date}`);
                link.href = day.geometry.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
                const license = node("a", day.geometry.license || "CC BY 4.0");
                license.href = day.geometry.license_url; license.target = "_blank"; license.rel = "noopener noreferrer";
                attribution.append(link, document.createTextNode(" · "), license,
                    node("span", ". Route geography may differ from FY 2023–24. Passenger counts are rounded to the nearest 10."));
            } else {
                if(root.suntrainI18n) root.suntrainI18n.bind(attribution, "Railway geometry is unavailable. Train positions are shown at stations only. Passenger counts are rounded to the nearest 10."); else attribution.textContent = "Railway geometry is unavailable. Train positions are shown at stations only. Passenger counts are rounded to the nearest 10.";
            }
            if (day.transit?.available) {
                const link = node("a", `Tram & bus timetables: PTV archive ${day.transit.source_date} · CC BY 4.0`);
                link.href = day.transit.source_url; link.target = "_blank"; link.rel = "noopener noreferrer";
                attribution.append(document.createTextNode(" "), link, node("span", ". Buses cover Victoria, including regional coaches and SkyBus where scheduled. Tram/bus passenger counts are unavailable."));
            }
        }
        applyTheme() {
            const dark = root.suntrainTheme.isDark;
            if (this.mapReady) {
                root.suntrainTheme.styleMap(this.graph);
                this.graph.setPaintProperty("replay-selected-route", "line-color", this.selected ? vehicleColor(this.selected, this.day?.city) : dark ? "#8ae1ca" : "#115d51");
                this.graph.setPaintProperty("replay-demand-stations", "circle-stroke-color", dark ? "#e4eef0" : "#fff");
                for (const layer of ["replay-stations", "replay-local-stops"]) {
                    this.graph.setPaintProperty(layer, "circle-color", dark ? "#17212b" : "#fff");
                    this.graph.setPaintProperty(layer, "circle-stroke-color", dark ? "#bccbc7" : "#526d66");
                }
                this.graph.setPaintProperty("replay-selected-train", "circle-stroke-color", dark ? "#f2f8fa" : "#18232d");
                this.graph.setPaintProperty("replay-trains", "circle-stroke-color", "#fff");
                this.graph.setPaintProperty("replay-routes", "line-color", dark ? "#789b92" : "#78908a");
            }
            this.updateLegend();
            const detail = document.querySelector(".replay-detail-line");
            if (detail && this.selected) detail.style.borderLeftColor = vehicleColor(this.selected, this.day?.city);
            if (this.day && this.mapReady) this.paint(true);
        }
        updateLegend() {
            if (!$("replay-legend")) return;
            const legend = $("replay-legend"), items = $("replay-legend-items"); items.replaceChildren();
            const entries = new Map();
            for (const service of this.filtered) {
                const label = service.mode === "tram" ? (this.day.city === "netherlands" ? service.line :
                    this.day.city === "toronto" ? `Streetcar ${service.line}` : `Tram ${tramRoute(service) || "other"}`) :
                    service.mode === "mikrotrans" ? "Mikrotrans" :
                    service.mode === "bus" && !["chicago", "perth"].includes(this.day.city) ? "Buses" : service.line;
                entries.set(`${service.mode || "train"}:${label}`, {label, color: vehicleColor(service, this.day?.city)});
            }
            setText("replay-legend-label", `Line colours · ${entries.size}`);
            const disclosure = `${this.day?.city || ""}:${entries.size <= 8}`;
            if (disclosure !== this.legendDisclosure) {
                legend.open = entries.size <= 8;
                this.legendDisclosure = disclosure;
            }
            legend.hidden = !entries.size || this.mapMode === "demand";
            for (const {label, color} of [...entries.values()].sort((a, b) => a.label.localeCompare(b.label, "en", {numeric: true}))) {
                const item = node("span", undefined, "replay-legend-item");
                const swatch = node("span", undefined, "replay-legend-swatch"); swatch.style.background = color;
                item.append(swatch, node("span", label)); items.append(item);
            }
        }
        applyFilters(filters, display) {
            this.filters = filters; this.display = display;
            const sizeHelp = $("replay-size-help");
            if (sizeHelp) sizeHelp.hidden = !display.includes("load");
            this.filtered = this.day.services.filter(service => matches(service, filters, this.day));
            this.departures?.refresh();
            this.updateActivity();
            const routes = this.day.services.filter(service => matches(service, {...filters, lines: [], stations: [], directions: [], number: ""}, this.day));
            root.dash_clientside.set_props("replay-lines", {options: [...new Set(routes.map(s => s.line))].sort()});
            this.demandIndex = null;
            this.activeIndex = new ActiveServices(this.filtered);
            this.demandPinned = false;
            this.demandMinute = null; this.demandPopupId = null; this.popup?.remove();
            if (this.selected && !this.filtered.some(s => s.id === this.selected.id)) {
                this.selected = null; this.emptyDetails();
            }
            this.staticDirty = true;
            this.updateLegend();
            let approximate = 0, total = 0, uncertain = 0;
            for (const service of this.filtered) {
                const key = service.stopIds || service.legs;
                if (!this.qualityBySchedule.has(key)) this.qualityBySchedule.set(key, {
                    total: service.legs.length,
                    approximate: service.legs.reduce((sum, id) => sum + Number(!["track", "shape"].includes(this.day.paths[id].quality)), 0)});
                const quality = this.qualityBySchedule.get(key);
                total += quality.total; approximate += quality.approximate;
                uncertain += service.timing_uncertain ? 1 : 0;
            }
            const pieces = [];
            if (!this.filtered.length) pieces.push(this.day.services.length ? "No services match these filters. Clear a filter to explore this day." : "No recorded services for this business date.");
            if (approximate) pieces.push(`${approximate.toLocaleString(root.suntrainI18n?.locale || "en-AU")} of ${total.toLocaleString(root.suntrainI18n?.locale || "en-AU")} journey legs have unresolved paths. These are left as gaps; vehicle positions are hidden between those stops.`);
            else if (total) pieces.push("All selected journey legs have route geometry.");
            if (this.day.schedule?.note_messages) pieces.push(...this.day.schedule.note_messages.map(message=>message.key));
            else if (this.day.schedule?.replay_note) pieces.push(...this.day.schedule.replay_note.split(/(?<=[.!?])\s+/));
            else if (this.day.city === "boston") pieces.push("Rail and Silver Line open first. Select Buses under Transport for regular MBTA buses. Rail replacement shuttles are excluded; calendars follow the historical archive.");
            else if (this.day.city === "chicago") pieces.push("CTA trains use November–December 2025 schedules. Select Buses under Transport to include CTA buses. Metra is excluded; direction A/B follows the feed where compass directions are not supplied.");
            else if (this.day.city === "nyc") pieces.push("NYC Subway and Staten Island Railway regular schedules for December 2025–January 2026. Express/local patterns and branches follow the feed; shapes do not establish individual running tracks. LIRR, Metro-North and buses are excluded.");
            else if (this.day.city === "singapore") pieces.push("Singapore MRT and LRT schedules on OpenStreetMap railway paths. The timetable snapshot does not reconstruct every past disruption. One anomalous Sunday NS trip has no interpolated movement.");
            else if (!this.day.transit?.available) pieces.push("Tram and bus timetables are unavailable for this date.");
            if (uncertain) pieces.push(`${uncertain} services contain ambiguous daylight-saving times; earliest consistent times are shown.`);
            if (this.day.excluded_services) pieces.push(`${this.day.excluded_services} services omitted because their source times or coordinates are invalid.`);
            const qualityHost=$("replay-quality");qualityHost.replaceChildren();
            for(const text of pieces)qualityHost.append(node("span",text),document.createTextNode(" "));
            setText("replay-matching-count", ` · ${this.filtered.length.toLocaleString(root.suntrainI18n?.locale || "en-AU")} services in this day`);
        }
        fit() {
            const ids = new Set();
            for (const service of uniqueSchedules(this.filtered)) for (const id of stopIds(service)) ids.add(id);
            if (!ids.size || !this.graph) return;
            this.setFollow(false);
            const stations = [...ids].map(i => this.day.stations[i]).filter(s => Number.isFinite(s.lon) && Number.isFinite(s.lat));
            if (!stations.length) return;
            const latitudes = stations.map(s => s.lat), longitudes = stations.map(s => s.lon);
            const south = Math.min(...latitudes), north = Math.max(...latitudes), west = Math.min(...longitudes), east = Math.max(...longitudes);
            this.graph.fitBounds([[west, south], [east, north]], {padding: 40, maxZoom: 13, duration: 0});
            this.needsFit = false;
        }
        seek(value) {
            if (!this.day || this.loading) return;
            this.now = Math.min(this.day.end, Math.max(this.day.start, value));
            this.previousTick = performance.now();
            this.activeIndex?.at(this.now, true);
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
            this.departures?.close();
            this.setFollow(false);
            this.showDetails(false);
            if ($("replay-close-details")) $("replay-close-details").hidden = true;
            const host = $("replay-details");
            if (host) host.replaceChildren(node("h3", "Follow a service"),
                node("p", "Click a moving vehicle to see its journey and scheduled stops.", "replay-muted"),
                node("div", this.day?.passenger_data === false ? `Positions follow scheduled times. Passenger counts are unavailable for ${this.day.city_name}.` :
                    "Positions follow scheduled times. Train passenger counts are available; tram and bus counts are unavailable.", "replay-detail-note"));
        }
        showDetails(visible) {
            const panel = $("replay-panel");
            if (!panel || panel.classList.contains("replay-has-selection") === visible) return;
            panel.classList.toggle("replay-has-selection", visible);
            if (this.graph) requestAnimationFrame(() => this.graph.resize());
        }
        select(id, departureCall = null) {
            const service = this.filtered.find(s => s.id === id);
            if (!service) return;
            this.selected = service; this.staticDirty = true;
            if (this.mapReady) this.graph.setPaintProperty("replay-selected-route", "line-color", vehicleColor(service, this.day?.city));
            this.showDetails(true);
            $("replay-close-details").hidden = false;
            this.setFollow(this.followSelected);
            const host = $("replay-details"); host.replaceChildren();
            this.departures?.journey(host, departureCall);
            host.style.setProperty("--journey-color", vehicleColor(service, this.day?.city));
            const line = node("div", service.line, "replay-detail-line");
            const trainNumber = ["train", "high_speed_rail"].includes(service.mode) || this.day.city === "us_rail" && service.mode === "commuter_rail";
            const operator = service.operator === "VLine" ? "V/Line" : service.operator;
            host.append(line, node("h3", service.destination), node("p", `From ${service.origin}`, "replay-detail-route"),
                node("p", `${trainNumber ? `Train ${service.number} · ` : ""}${operator} · ${directionLabel(service)}`, "replay-muted replay-small"));
            const live = node("div", undefined, "replay-service-status"); live.id = "replay-service-status"; host.append(live);
            this.selectedHasLoads = this.day.passenger_data !== false && !service.stopIds && service.stops.some(stop => stop[4] != null);
            const allStops = node("details", undefined, "replay-all-stops");
            allStops.append(node("summary", `All ${service.mode === "ferry" ? "piers" : "stops"} · ${stopCount(service)}`));
            // Long bus schedules only become DOM rows when someone asks for them.
            allStops.addEventListener("toggle", () => {
                if (!allStops.isConnected || !allStops.open || allStops.dataset.built || this.selected?.id !== service.id) return;
                allStops.dataset.built = "true";
                this.renderStopTable(service, allStops);
                live.dataset.signature = ""; this.paint(true);
            });
            host.append(allStops);
            this.paint(true);
            if (departureCall) { host.tabIndex = -1; host.focus(); }
        }
        renderStopTable(service, host) {
            const scroll = node("div", undefined, "replay-stop-list"), table = node("table");
            const head = node("thead"), heading = node("tr");
            const columns = [service.mode === "ferry" ? "Pier" : "Stop / station", "Arr.", "Dep."];
            if (this.selectedHasLoads) columns.push("Load");
            columns.forEach(label => heading.append(node("th", label)));
            head.append(heading); table.append(head);
            const body = node("tbody");
            const stopDate = this.day.city === "us_rail" ? new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {
                timeZone: this.day.timezone, day: "numeric", month: "short"}) : null;
            const scheduledTime = timestamp => {
                const date = new Date(timestamp * 1000);
                return shortTime.format(date) + (stopDate ? ` · ${stopDate.format(date)}` : "");
            };
            for (let i = 0; i < stopCount(service); i++) {
                const stop = service.stopIds ? [stopValue(service, i, 0), stopValue(service, i, 1), stopValue(service, i, 2)] : service.stops[i];
                const row = node("tr"); row.dataset.stopIndex = String(i);
                row.append(node("td", this.day.stations[stop[0]].name));
                for(const column of [1,2]){
                    const at=stopTime(service,stop,column), cell=node("td",scheduledTime(at));
                    cell.dataset.scheduledAt=String(at);cell.dataset.withDate=String(!!stopDate);row.append(cell);
                }
                if (this.selectedHasLoads) {
                    row.append(node("td", stop[4] == null ? "—" : stop[4].toLocaleString(root.suntrainI18n?.locale || "en-AU")));
                    if(root.suntrainI18n) root.suntrainI18n.bind(row,`Boardings: ${stop[5] ?? "unknown"}; alightings: ${stop[6] ?? "unknown"}`,"title"); else row.title = `Boardings: ${stop[5] ?? "unknown"}; alightings: ${stop[6] ?? "unknown"}`;
                }
                body.append(row);
            }
            table.append(body); scroll.append(table); host.append(scroll);
            const unresolved = service.legs.filter(id => !["track", "shape"].includes(this.day.paths[id]?.quality)).length;
            if (unresolved) host.append(node("p", `${unresolved} journey leg${unresolved === 1 ? " has" : "s have"} unresolved geometry. The route has gaps and this vehicle is hidden between those stops.`, "replay-approximate replay-small"));
            host.append(node("p", `Trip ${service.source_trip_id || service.number}`, "replay-muted replay-small"));
            if (this.selectedHasLoads) host.append(node("p", "Load = recorded departure passenger count, rounded to the nearest 10.", "replay-muted replay-small"));
        }
        detailStatus(position) {
            if (!this.selected) return;
            const host = $("replay-service-status"); if (!host) return;
            const upcoming = this.now < stopValue(this.selected, 0, 1) + (this.selected.timeOffset || 0);
            const index = position?.index ?? (upcoming ? 0 : stopCount(this.selected) - 1);
            const text = position ? position.state : upcoming ? "Not started yet" : "Journey finished";
            const signature = `${index}|${text}|${position?.load}|${position?.approximate}`;
            if (host.dataset.signature !== signature) {
                host.dataset.signature = signature;
                const stops = node("ol", undefined, "replay-journey-stops");
                for (const i of [index, index + 1]) {
                    if (i >= stopCount(this.selected)) continue;
                    const current = i === index;
                    const label = current ? (position ? "Now" : upcoming ? "Starts at" : "Arrived at") : "Next stop";
                    const station = this.day.stations[stopValue(this.selected, i, 0)];
                    const departure = current && (position || upcoming);
                    const at = new Date((stopValue(this.selected, i, departure ? 2 : 1) + (this.selected.timeOffset || 0)) * 1000);
                    const row = node("li", undefined, `replay-journey-stop${current ? " is-current" : ""}`);
                    row.append(node("span", label, "replay-journey-label"), node("strong", station.name),
                        node("span", `${root.suntrainI18n?.translate(departure ? "Dep." : "Arr.") || (departure ? "Dep." : "Arr.")} ${shortTime.format(at)} · ${shortDate.format(at)}`, "replay-journey-time"));
                    stops.append(row);
                }
                host.replaceChildren(node("div", text, "replay-journey-state"), stops);
                if (position) {
                    if (this.selectedHasLoads) host.append(node("div", position.load == null ? "Passenger load unavailable" : `${position.load.toLocaleString(root.suntrainI18n?.locale || "en-AU")} passengers · rounded estimate`));
                    if (position.approximate) host.append(node("div", this.selected.mode === "ferry" ? "Water path unresolved. Position hidden until the next scheduled pier." : ROAD_MODES.has(this.selected.mode) ? "Road path unresolved. Position hidden until the next scheduled stop." : "Railway path unresolved. Position hidden until the next recorded station.", "replay-approximate"));
                }
                if (this.selected.timing_uncertain) host.append(node("div", "Daylight-saving times are ambiguous for this service.", "replay-approximate"));
                if (this.selected.frequency_based) host.append(node("div", "Frequency-based estimate · not an exact departure.", "replay-muted replay-small"));
                if (this.selected.terminal_arrival_missing) host.append(node("div", "Terminal arrival time unavailable; animation ends at the last published stop.", "replay-muted replay-small"));
                $("replay-details").querySelectorAll("tr[data-stop-index]").forEach(row => {
                    row.classList.toggle("replay-current-stop", !!position && Number(row.dataset.stopIndex) === position.index);
                });
            }
        }
        updateStaticLayers() {
            const ids = new Set(), stationIds = new Set();
            for (const service of uniqueSchedules(this.filtered)) {
                if (this.mapMode === "demand" && service.mode !== "train") continue;
                for (const id of stopIds(service)) stationIds.add(id);
                if (this.display.includes("routes")) for (const id of service.legs) ids.add(id);
            }
            const routes = routeFeatures(this.day.paths, ids);
            const selected = this.selected ? routeFeatures(this.day.paths, this.selected.legs) : [];
            const stations = this.display.includes("stations") ? [...stationIds].map(i => ({...this.day.stations[i], id: i})).filter(s => Number.isFinite(s.lon) && Number.isFinite(s.lat)) : [];
            this.graph.getSource("replay-routes").setData(collection(routes));
            this.graph.getSource("replay-stations").setData(collection(stations.map(s => pointFeature([s.lon, s.lat], {name: s.name, id: s.id, mode: s.mode || "train"}))));
            this.graph.getSource("replay-selected-route").setData(collection(selected));
            this.graph.setFilter("replay-station-focus", ["==", ["get", "id"], (this.departures?.visible || this.departures?.previewCall) ? this.departures.station : -1]);
        }
        setMapMode(mode, minutes) {
            mode = ["trains", "demand", "both"].includes(mode) ? mode : "trains";
            minutes = [15, 30, 60].includes(Number(minutes)) ? Number(minutes) : 30;
            const changed = this.mapMode !== mode || this.demandWindow !== minutes;
            this.mapMode = mode; this.demandWindow = minutes;
            $("replay-panel").classList.toggle("replay-demand-only", mode === "demand");
            for (const id of ["replay-trains", "replay-vehicle-outline", "replay-selected-train", "replay-selected-route"])
                this.graph.setLayoutProperty(id, "visibility", mode === "demand" ? "none" : "visible");
            for (const id of ["replay-demand-glow", "replay-demand-stations"])
                this.graph.setLayoutProperty(id, "visibility", mode === "trains" ? "none" : "visible");
            $("replay-demand-legend").hidden = mode === "trains";
            $("replay-demand-window-field").hidden = mode === "trains";
            $("replay-legend").hidden = mode === "demand";
            if (changed) {
                this.staticDirty = true;
                this.demandPinned = false;
                this.demandMinute = null; this.demandPopupId = null; this.popup?.remove();
                this.setFollow(this.followSelected);
            }
        }
        showDemandPopup(id) {
            const row = this.demandSnapshot?.rows.find(row => row.id === id);
            if (!row) return;
            this.demandPopupId = id;
            const content = node("div", undefined, "replay-map-tooltip");
            const label = !row.knownCalls && row.missingCalls ? "Boardings unavailable" : `${row.boardings.toLocaleString(root.suntrainI18n?.locale || "en-AU")} recorded boardings`;
            content.append(node("strong", row.name), node("div", `${label} · last ${this.demandWindow} minutes`),
                node("div", `${shortTime.format(new Date(this.demandSnapshot.start * 1000))}–${shortTime.format(new Date(this.demandSnapshot.end * 1000))}`));
            if (!row.knownCalls && !row.missingCalls) content.append(node("div", "No recorded departures in this window."));
            if (row.missingCalls) content.append(node("div", `${row.missingCalls} departure counts unavailable.`));
            content.append(node("div", "Counts rounded to the nearest 10."));
            const departures = node("button", "Departures", "finder-chip"); departures.type = "button";
            departures.addEventListener("click", () => this.departures.open(id));
            content.append(departures);
            this.popup.setLngLat([row.lon, row.lat]).setDOMContent(content).addTo(this.graph);
        }
        paintDemand(force) {
            if (this.mapMode === "trains") return;
            if (!this.demandIndex) this.demandIndex = root.suntrainDemand.buildIndex(this.filtered, this.day);
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
                    tick.append(swatch, document.createTextNode(count.toLocaleString(root.suntrainI18n?.locale || "en-AU") + (count === 5000 ? "+" : "")));
                    $("replay-demand-scale").append(tick);
                }
            }
            setText("replay-demand-range", `Last ${this.demandWindow} min · ${shortTime.format(new Date(snapshot.start * 1000))}–${shortTime.format(new Date(snapshot.end * 1000))}`);
            setText("replay-demand-total", !snapshot.knownCalls && snapshot.missingCalls ? "Boarding counts unavailable" :
                `${snapshot.total.toLocaleString(root.suntrainI18n?.locale || "en-AU")} boardings · ${snapshot.stationCount} stations`);
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
            if (!this.active || !this.day || !this.activeIndex || this.loading || !this.mapReady) return;
            if (this.busy) { this.paintAgain = true; return; }
            this.busy = true;
            const started = performance.now(), generation = this.generation;
            try {
                const trains = [], vehicleDots = [];
                const zoom = this.graph.getZoom();
                let selectedPosition = null, selectedMarker = null, activeCount = 0, missingCount = 0;
                for (const service of this.activeIndex.at(this.now)) {
                    const position = servicePosition(service, this.now, this.day);
                    if (!position) continue;
                    activeCount++;
                    if (service.id === this.selected?.id) selectedPosition = position;
                    if (position.lon === null || position.lat === null) { missingCount++; continue; }
                    const kind = root.suntrainVehicles.bodyKind(this.day.city, service.mode);
                    const sizeFactor = markerScale(position.load, this.display.includes("load"));
                    const spacing = (2 * root.suntrainVehicles.radius(zoom, sizeFactor) + 1) *
                        156543.033928 * Math.cos(position.lat * Math.PI / 180) / 2 ** zoom;
                    const coordinates = kind ? root.suntrainVehicles.footprint(service, position, this.day, this.now, spacing, pointAlong) : [[position.lon, position.lat]];
                    const properties = {id: service.id, color: vehicleColor(service, this.day.city), body: kind,
                        sizeFactor, load: position.load, approximate: position.approximate, dotCount: coordinates.length};
                    const marker = pointFeature(coordinates[0], {...properties, part: 0});
                    trains.push(marker);
                    for (let part = 0; part < coordinates.length; part++)
                        vehicleDots.push(pointFeature(coordinates[part], {...properties, part}));
                    if (service.id === this.selected?.id) selectedMarker = marker;
                }
                if (this.staticDirty) {
                    this.updateStaticLayers(); this.staticDirty = false;
                }
                this.paintDemand(force);
                this.activePositions = trains;
                this.missingPositions = missingCount;
                const selectedVisible = selectedPosition && selectedPosition.lon !== null && selectedPosition.lat !== null;
                this.graph.getSource("replay-trains").setData(collection(vehicleDots));
                this.graph.getSource("replay-selected-train").setData(collection(selectedMarker ? [selectedMarker] : []));
                if (generation !== this.generation) { this.staticDirty = true; this.paintAgain = true; return; }
                if (this.needsFit) this.metroView();
                if (this.followSelected && selectedVisible) this.graph.setCenter([selectedPosition.lon, selectedPosition.lat]);
                else if (this.followSelected && this.now > stopValue(this.selected, stopCount(this.selected) - 1, 2) + (this.selected.timeOffset || 0)) this.setFollow(false);
                if (force || performance.now() - this.lastUI >= 200 || !this.playing) {
                    this.lastUI = performance.now();
                    setText("replay-clock", clockFormat.format(new Date(this.now * 1000)));
                    setText("replay-clock-date", dateFormat.format(new Date(this.now * 1000)));
                    setText("replay-active-count", activeCount.toLocaleString(root.suntrainI18n?.locale || "en-AU"));
                    setText("replay-position-note", missingCount ? ` · ${missingCount.toLocaleString(root.suntrainI18n?.locale || "en-AU")} vehicle position${missingCount === 1 ? "" : "s"} unavailable` : "");
                    const slider = $("replay-timeline")?.querySelector("input");
                    if (slider) {
                        slider.value = String(this.now);
                        slider.setAttribute("aria-valuetext", `${clockFormat.format(new Date(this.now * 1000))} ${dateFormat.format(new Date(this.now * 1000))}`);
                        slider.parentElement.style.setProperty("--replay-progress", `${100 * (this.now - this.day.start) / (this.day.end - this.day.start)}%`);
                    }
                    this.detailStatus(selectedPosition);
                    this.departures?.update();
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
        async sync(day, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, trigger, city = "melbourne") {
            if (!this.departures) this.departures = new root.suntrainDepartures.Board(this, core);
            this.lastTrigger = trigger;
            this.active = tab === "replay";
            if (!this.active) { this.pause(); this.departures.setExpanded(false); if (this.isFullscreen()) this.exitFullscreen(); }
            this.revealTab();
            if (!day || day.business_date !== date || (day.city || "melbourne") !== city || day.error) {
                root.suntrainOverview.pending(city, date, !!day?.error);
                this.pause(); this.loading = true;
                if (tab !== "home") { this.departures.reset(); this.selected = null; this.emptyDetails(); }
                $("replay-open-departures").disabled = true;
                this.demandMinute = null; this.demandSnapshot = null; this.demandPopupId = null; this.popup?.remove();
                if ($("replay-demand-legend")) $("replay-demand-legend").hidden = true;
                setText("replay-position-note", "");
                root.dash_clientside.set_props("replay-play", {disabled: true});
                if ($("replay-map")) $("replay-map").classList.add("replay-is-loading");
                setText("replay-active-count", "—"); setText("replay-matching-count", day?.error ? " · Could not load this day" : " · Loading this day…");
                return;
            }
            this.loading = false;
            $("replay-open-departures").disabled = false;
            $("replay-map")?.classList.remove("replay-is-loading");
            const newDay = !this.day || this.day.city !== day.city || this.day.business_date !== day.business_date || this.day.revision !== day.revision;
            if (newDay) this.load(day);
            const filters = {modes: modes || [], operators: operators || [], lines: lines || [], directions: directions || [], stations: stations || [], number: number || ""};
            if (tab === "overview") {
                const routes = this.day.services.filter(service => matches(service, {...filters, lines: [], stations: [], directions: [], number: ""}, this.day));
                root.dash_clientside.set_props("replay-lines", {options: [...new Set(routes.map(s => s.line))].sort()});
                root.suntrainOverview.render(this.day, filters, core);
                return;
            }
            if (!this.mapReady && !await this.connect()) return;
            if (!this.active || this.day.city !== city || this.day.business_date !== day.business_date) return;
            this.speed = Number(speed) || 60;
            this.setMapMode(this.day.passenger_data === false ? "trains" : mode, demandWindow);
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
    root.suntrainReplayCore=core;
    // Exposed diagnostics support browser verification without transmitting frames.
    root.suntrainReplay = replay;
    root.dash_clientside = Object.assign({}, root.dash_clientside, {suntrainReplay: {
        sync: async function (info, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, play, restart, back, forward, fit, city) {
            const context = root.dash_clientside.callback_context;
            const trigger = context.triggered_id || context.triggered?.[0]?.prop_id?.split(".")[0];
            const generation = ++replay.requestGeneration;
            const run = day => replay.sync(day, tab, date, modes, operators, lines, directions, stations, number, display, mode, demandWindow, speed, trigger, city);
            const valid = info && !info.error && info.business_date === date && info.city === city;
            try {
                if (!["replay", "overview"].includes(tab) || !valid) {
                    replay.download?.controller.abort(); replay.download = null;
                    await run(null);
                    return root.dash_clientside.no_update;
                }
                let day = replay.day;
                if (!day || day.revision !== info.revision || day.city !== city || day.business_date !== date) {
                    await run(null);
                    if (replay.download?.url !== info.url) {
                        replay.download?.controller.abort();
                        const controller = new AbortController();
                        replay.download = {url: info.url, controller, promise: fetch(info.url, {signal: controller.signal}).then(response => {
                            if (!response.ok) throw new Error(`Replay download failed (${response.status})`);
                            return response.json();
                        })};
                    }
                    const pending = replay.download;
                    day = await pending.promise;
                    if (generation !== replay.requestGeneration) return root.dash_clientside.no_update;
                    if (replay.download === pending) replay.download = null;
                }
                if (generation !== replay.requestGeneration) return root.dash_clientside.no_update;
                setText("replay-load-message", "");
                await run(day);
                if (generation !== replay.requestGeneration) return root.dash_clientside.no_update;
                return {business_date: date, city, modes: info.modes, bus_data_loaded: !!info.bus_data_loaded};
            } catch (error) {
                if (error.name === "AbortError" || generation !== replay.requestGeneration) return root.dash_clientside.no_update;
                replay.download = null; replay.pause();
                root.suntrainOverview.pending(city, date, true);
                console.error("Train replay failed", error);
                setText("replay-load-message", "The replay could not load. Choose another date or return to this tab to retry.");
                return {business_date: date, city, error: true};
            }
        }
    }});
})(typeof window !== "undefined" ? window : globalThis);
