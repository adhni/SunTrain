(function (root) {
    "use strict";
    const PAGE_SIZE = 15;
    const count = service => service.stopIds ? service.stopIds.length : service.stops.length;
    const stopId = (service, index) => service.stopIds ? service.stopIds[index] : service.stops[index][0];
    const departure = (service, index) => (service.stopIds ? service.times[index * 2 + 1] : service.stops[index][2]) + (service.timeOffset || 0);

    function stationCalls(services, station, start, end) {
        const calls = [], occurrences = new Map();
        for (const service of services) {
            const topology = service.stopIds || service.stops;
            if (!occurrences.has(topology)) {
                const indices = [];
                // Final clocks are often copied arrivals, not departures.
                for (let i = 0; i < count(service) - 1; i++) if (stopId(service, i) === station) indices.push(i);
                occurrences.set(topology, indices);
            }
            for (const index of occurrences.get(topology)) {
                const at = departure(service, index);
                if (Number.isFinite(at) && at >= start && at <= end) calls.push({service, index, at, key: JSON.stringify([service.id, index])});
            }
        }
        return calls.sort((a, b) => a.at - b.at || String(a.service.id).localeCompare(String(b.service.id)) || a.index - b.index);
    }
    function upcomingPage(calls, now, page = 0) {
        let low = 0, high = calls.length;
        while (low < high) {
            const middle = (low + high) >>> 1;
            if (calls[middle].at < now) low = middle + 1; else high = middle;
        }
        const total = calls.length - low, pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        page = Math.max(0, Math.min(page, pages - 1));
        return {rows: calls.slice(low + page * PAGE_SIZE, low + (page + 1) * PAGE_SIZE), total, page, pages};
    }
    function stationCatalogue(services, stations) {
        const records = new Map(), seen = new Map();
        for (const service of services) {
            const topology = service.stopIds || service.stops;
            const label = `${(service.mode || "train").replaceAll("_", " ")} · ${service.line}`;
            if (!seen.has(topology)) seen.set(topology, new Set());
            if (seen.get(topology).has(label)) continue;
            seen.get(topology).add(label);
            for (let index = 0; index < count(service); index++) {
                const id = stopId(service, index);
                if (!records.has(id)) records.set(id, {id, name: stations[id].name, routes: new Set()});
                records.get(id).routes.add(label);
            }
        }
        return [...records.values()].map(row => {
            const station = stations[row.id], routes = [...row.routes].sort().join(" / ");
            const location = Number.isFinite(station.lat) && Number.isFinite(station.lon) ? `${station.lat.toFixed(5)}, ${station.lon.toFixed(5)}` : "Location unavailable";
            return {...row, label: `${row.name} · ${routes} · ${location}`};
        }).sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
    }
    function formatCallTime(at, timezone) {
        return new Intl.DateTimeFormat("en-AU", {timeZone: timezone, day: "numeric", month: "short",
            hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "shortOffset"}).format(new Date(at * 1000));
    }
    const api = {stationCalls, upcomingPage, stationCatalogue, formatCallTime};
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    if (!root.document) return;
    const $ = id => document.getElementById(id);
    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        if (className) element.className = className;
        return element;
    }
    function button(text, action) {
        const element = node("button", text, "finder-chip"); element.type = "button";
        element.addEventListener("click", action); return element;
    }
    class Board {
        constructor(replay, core) {
            this.replay = replay; this.core = core; this.station = null; this.page = 0;
            this.host = $("replay-departures");
            $("replay-open-departures").addEventListener("click", () => this.open());
        }
        reset() {
            this.close(); this.station = null; this.services = null; this.catalogue = null; this.calls = []; this.page = 0;
            this.host.replaceChildren(); this.list = null; this.search = null; this.choices = null;
        }
        close() {
            this.visible = false; this.host.hidden = true;
            $("replay-details").hidden = false;
            $("replay-panel").classList.remove("replay-browsing");
            $("replay-open-departures").setAttribute("aria-expanded", "false");
        }
        refresh() {
            const replay = this.replay;
            if (this.services !== replay.filtered) {
                this.services = replay.filtered; this.catalogue = null; this.page = 0; this.signature = null;
                this.calls = this.station === null ? [] : stationCalls(this.services, this.station, replay.day.start, replay.day.end);
                if (this.visible) this.render();
            }
        }
        open(station = this.station) {
            const replay = this.replay;
            if (!replay.day || replay.loading) return;
            if (station !== this.station) { this.station = station; this.services = null; this.page = 0; }
            this.visible = false; this.refresh(); this.visible = true;
            replay.selected = null; replay.setFollow(false); replay.staticDirty = true;
            replay.demandPinned = false; replay.demandPopupId = null;
            replay.popup?.remove(); replay.showDetails(true);
            $("replay-close-details").hidden = false; $("replay-details").hidden = true;
            $("replay-panel").classList.add("replay-browsing");
            $("replay-open-departures").setAttribute("aria-expanded", "true");
            this.host.hidden = false; this.render(); replay.paint(true);
            (this.station === null ? this.search : this.title).focus();
        }
        render() {
            const replay = this.replay;
            this.host.replaceChildren(); this.signature = null;
            this.title = node("h3", this.station === null ? "Station departures" : replay.day.stations[this.station].name);
            this.title.tabIndex = -1;
            this.host.append(this.title, node("p", `${replay.day.business_date} · ${replay.day.timezone} · Loaded replay services only`, "replay-muted replay-small"));
            const picker = node("details"); picker.open = this.station === null;
            picker.append(node("summary", this.station === null ? "Choose a stop" : "Change stop"));
            const label = node("label", "Find a station, stop or pier"); label.htmlFor = "departure-search";
            this.search = node("input"); this.search.id = "departure-search"; this.search.type = "search";
            this.search.placeholder = "Search by name or route…";
            this.choices = node("select"); this.choices.size = 5; this.choices.setAttribute("aria-label", "Matching stops");
            this.matchCount = node("p", "", "replay-muted replay-small");
            this.search.addEventListener("input", () => this.updateChoices());
            this.choose = button("Open departures", () => { if (this.choices.value !== "") this.open(Number(this.choices.value)); });
            this.choices.addEventListener("change", () => { this.choose.disabled = this.choices.value === ""; });
            picker.append(label, this.search, this.choices, this.matchCount, this.choose); this.host.append(picker); this.updateChoices();
            this.clock = node("p", "", "replay-muted replay-small");
            this.list = node("div", undefined, "departure-list");
            this.previous = button("Previous", () => { this.page--; this.update(true); });
            this.next = button("Next", () => { this.page++; this.update(true); });
            this.pageLabel = node("span");
            const nav = node("nav", undefined, "departure-pagination"); nav.setAttribute("aria-label", "Departure pages");
            nav.append(this.previous, this.pageLabel, this.next);
            this.host.append(this.clock, this.list, nav, node("p", "Scheduled replay events; boarding permissions may differ. Final stops are excluded.", "replay-muted replay-small"));
            this.update(true);
        }
        updateChoices() {
            if (!this.catalogue) this.catalogue = stationCatalogue(this.services, this.replay.day.stations);
            const query = this.search.value.trim().toLocaleLowerCase();
            const matches = this.catalogue.filter(row => row.label.toLocaleLowerCase().includes(query));
            this.choices.replaceChildren();
            for (const row of matches.slice(0, 60)) {
                const option = node("option", row.label); option.value = String(row.id); option.title = row.label;
                this.choices.append(option);
            }
            this.choices.value = this.station === null ? "" : String(this.station);
            this.choose.disabled = this.choices.value === "";
            this.matchCount.textContent = matches.length > 60 ? `Showing 60 of ${matches.length} stops. Refine your search.` : `${matches.length} matching stops`;
        }
        update(force = false) {
            if (!this.visible || !this.list) return;
            const replay = this.replay;
            this.clock.textContent = `Departures from ${formatCallTime(replay.now, replay.day.timezone)}`;
            // Keep a keyboard-focused departure stable until focus leaves the list.
            if (!force && this.list.contains(document.activeElement)) return;
            const result = upcomingPage(this.calls, replay.now, this.page); this.page = result.page;
            const signature = JSON.stringify([this.page, result.total, result.rows.map(row => row.key)]);
            if (!force && signature === this.signature) return;
            this.signature = signature; this.list.replaceChildren();
            if (!result.rows.length) this.list.append(node("p", this.station === null ? "Choose a stop to explore its journeys." : "No upcoming departures match the current filters. Try an earlier replay time or change the filters.", "replay-muted"));
            for (const call of result.rows) {
                const service = call.service;
                const row = button("", () => replay.select(service.id, call)); row.className = "departure-row";
                row.style.setProperty("--journey-color", this.core.vehicleColor(service, replay.day.city));
                row.append(node("strong", formatCallTime(call.at, replay.day.timezone)),
                    node("span", `${service.line} → ${service.destination}`),
                    node("small", `${service.operator} · ${service.number}`));
                if (service.frequency_based) row.append(node("small", "Frequency-based estimate"));
                if (service.terminal_arrival_missing) row.append(node("small", "Terminal arrival unavailable"));
                this.list.append(row);
            }
            this.pageLabel.textContent = `${result.page + 1} / ${result.pages} · ${result.total} departures`;
            this.previous.disabled = !result.page; this.next.disabled = result.page + 1 >= result.pages;
        }
        journey(host, call) {
            this.visible = false; this.host.hidden = true; $("replay-details").hidden = false;
            if (!call) { this.close(); return; }
            const replay = this.replay;
            replay.setFollow(false);
            host.append(button("Back to departures", () => this.open()),
                button("Go to departure", () => {
                    replay.pause();
                    if (replay.mapMode === "demand") {
                        root.dash_clientside.set_props("replay-map-mode", {value: "both"});
                        replay.setMapMode("both", replay.demandWindow);
                    }
                    replay.seek(call.at);
                    const station = replay.day.stations[this.station];
                    if (replay.mapReady && Number.isFinite(station.lon) && Number.isFinite(station.lat))
                        replay.graph.setCenter([station.lon, station.lat]);
                }));
            host.append(node("p", `From ${replay.day.stations[this.station].name} · ${formatCallTime(call.at, replay.day.timezone)}`, "replay-muted replay-small"));
        }
    }
    root.suntrainDepartures = {...api, Board};
})(typeof window !== "undefined" ? window : globalThis);
