(function (root) {
    "use strict";
    const modeNames = {train: "Train", subway: "Subway", tram: "Tram", bus: "Bus", mikrotrans: "Mikrotrans", feeder_bus: "Feeder bus",
        light_rail: "Light rail", regional_rail: "Regional rail", commuter_rail: "Commuter rail", airport_rail: "Airport rail", limited_express: "Limited express", silver_line: "Silver Line", ferry: "Ferry",
        transjabodetabek: "Transjabodetabek", rusun_bus: "Rusun feeder", royaltrans: "Royaltrans", shuttle_bus: "Shuttle", tourist_bus: "Tourist bus"};

    function summarize(day, filters, core) {
        const hours = Array.from({length: 24}, (_, i) => ({hour: (i + 3) % 24, departures: 0}));
        const routes = new Map(), stops = new Set(), seenSchedules = new Set(), minuteHours = new Map();
        const formatter = new Intl.DateTimeFormat("en-GB", {timeZone: day.timezone, hour: "2-digit", hourCycle: "h23"});
        let departures = 0, estimatedDepartures = 0;
        for (const service of day.services) {
            if (!core.matches(service, filters, day)) continue;
            const departure = core.firstDeparture(service);
            if (departure < day.start || departure >= day.end) continue;
            departures++;
            if (service.frequency_based) estimatedDepartures++;
            const minute = Math.floor(departure / 60);
            if (!minuteHours.has(minute)) minuteHours.set(minute, Number(formatter.format(new Date(departure * 1000))));
            hours[(minuteHours.get(minute) + 21) % 24].departures++;
            const mode = service.mode || "train";
            const key = JSON.stringify([mode, service.operator, service.route_id || service.line]);
            const germanMode = day.city === "germany" ? {commuter_rail: "S-Bahn", subway: "U-Bahn / Stadtbahn"}[mode] : null;
            if (!routes.has(key)) routes.set(key, {line: service.line, mode: germanMode || modeNames[mode] || mode,
                operator: service.operator, departures: 0, color: core.vehicleColor(service, day.city)});
            routes.get(key).departures++;
            const schedule = service.stopIds || service.stops;
            if (seenSchedules.has(schedule)) continue;
            seenSchedules.add(schedule);
            for (const stop of schedule) {
                const station = day.stations[service.stopIds ? stop : stop[0]];
                if (Number.isFinite(station.lon) && Number.isFinite(station.lat)) stops.add(JSON.stringify([station.name, station.lon, station.lat]));
            }
        }
        return {departures, estimatedDepartures, stops: stops.size, routes: [...routes.values()], hours};
    }
    if (typeof module !== "undefined" && module.exports) module.exports = {summarize};
    if (!root.document) return;

    const $ = id => document.getElementById(id);
    const count = value => value.toLocaleString("en-AU");
    function element(tag, text, className) {
        const item = document.createElement(tag);
        if (text !== undefined) item.textContent = text;
        if (className) item.className = className;
        return item;
    }
    let cachedKey, cachedSummary, renderedKey;
    function pending(city, date, failed = false) {
        const host = $("city-overview-content");
        if (!host) return;
        const names = JSON.parse($("city-overview").dataset.cities);
        $("city-overview-title").textContent = `${names[city] || city} overview`;
        $("city-overview-context").textContent = date || "";
        host.replaceChildren(element("p", failed ? "This day could not load. Choose another date or return to this tab to retry." : "Loading this day…", "replay-muted"));
        host.setAttribute("aria-busy", String(!failed));
        renderedKey = null;
    }
    function routeTable(rows) {
        const card = element("section", undefined, "table-card city-routes");
        card.append(element("h3", "Routes and services", "viz-title"));
        const scroll = element("div", undefined, "city-table-scroll"), table = element("table");
        const head = element("thead"), header = element("tr"), body = element("tbody");
        let sortKey = "departures", descending = true, page = 0;
        const columns = [["line", "Route / line"], ["mode", "Transport"], ["operator", "Operator"], ["departures", "Departures"]];
        const headings = [];
        for (const [key, label] of columns) {
            const cell = element("th"), button = element("button", label);
            cell.scope = "col"; button.type = "button";
            button.addEventListener("click", () => {
                descending = sortKey === key ? !descending : key === "departures";
                sortKey = key; page = 0; update();
            });
            headings.push([cell, button, key, label]); cell.append(button); header.append(cell);
        }
        head.append(header); table.append(head, body); scroll.append(table); card.append(scroll);
        const nav = element("div", undefined, "city-table-pagination");
        const previous = element("button", "Previous", "finder-chip"), next = element("button", "Next", "finder-chip");
        const label = element("span");
        previous.type = next.type = "button";
        previous.addEventListener("click", () => { page--; update(); });
        next.addEventListener("click", () => { page++; update(); });
        nav.append(previous, label, next); card.append(nav);
        function update() {
            const sorted = rows.slice().sort((a, b) => {
                const comparison = sortKey === "departures" ? a.departures - b.departures :
                    String(a[sortKey]).localeCompare(String(b[sortKey]), "en", {numeric: true});
                return (descending ? -comparison : comparison) || a.line.localeCompare(b.line, "en", {numeric: true});
            });
            for (const [cell, button, key, text] of headings) {
                cell.setAttribute("aria-sort", key === sortKey ? descending ? "descending" : "ascending" : "none");
                button.textContent = text + (key === sortKey ? descending ? " ↓" : " ↑" : "");
            }
            body.replaceChildren();
            for (const row of sorted.slice(page * 15, (page + 1) * 15)) {
                const tr = element("tr"), route = element("td"), swatch = element("i", undefined, "city-route-swatch");
                swatch.style.backgroundColor = row.color; swatch.setAttribute("aria-hidden", "true");
                route.append(swatch, document.createTextNode(row.line));
                tr.append(route, element("td", row.mode), element("td", row.operator), element("td", count(row.departures)));
                body.append(tr);
            }
            const pages = Math.max(1, Math.ceil(rows.length / 15));
            label.textContent = `Page ${page + 1} of ${pages} · ${count(rows.length)} routes / lines`;
            previous.disabled = page === 0; next.disabled = page + 1 >= pages;
        }
        update(); return card;
    }
    function render(day, filters, core) {
        const host = $("city-overview-content");
        if (!host) return;
        const key = JSON.stringify([day.revision, day.city, day.business_date, filters]);
        if (key === renderedKey) return;
        if (key !== cachedKey) { cachedSummary = summarize(day, filters, core); cachedKey = key; }
        const summary = cachedSummary;
        $("city-overview-title").textContent = `${day.city_name} overview`;
        const date = new Intl.DateTimeFormat("en-AU", {timeZone: day.timezone, day: "numeric", month: "short", year: "numeric"})
            .format(new Date(day.start * 1000));
        $("city-overview-context").textContent = `${date} · 03:00–03:00 next day · ${day.timezone} · Current filters`;
        const cards = element("div", undefined, "status-grid city-overview-metrics");
        for (const [label, value, subtitle] of [[summary.estimatedDepartures ? "Replay departures" : "Scheduled departures", summary.departures,
            summary.estimatedDepartures ? "Includes frequency-based estimates" : "Starting in this business day"],
            ["Routes / lines", summary.routes.length, "Represented in the selection"], ["Stops served", summary.stops, "Distinct mapped stops / platforms"]]) {
            const card = element("div", undefined, "metric-card");
            card.append(element("div", label, "metric-label"), element("div", count(value), "metric-value"), element("div", subtitle, "metric-subtitle"));
            cards.append(card);
        }
        host.replaceChildren(cards); host.setAttribute("aria-busy", "false");
        if (!summary.departures) {
            host.append(element("p", "No scheduled departures match this date and these filters. Clear a filter or choose another date.", "city-empty replay-muted"));
        } else {
            const figure = element("figure", undefined, "viz-card city-hour-chart");
            figure.append(element("figcaption", "Departures through the day · local time", "viz-title"));
            const bars = element("div", undefined, "city-hour-bars");
            const peak = Math.max(...summary.hours.map(hour => hour.departures), 1);
            const magnitude = 10 ** Math.floor(Math.log10(peak));
            const maximum = Math.ceil(peak / magnitude) * magnitude;
            const plot = element("div", undefined, "city-hour-plot"), axis = element("div", undefined, "city-hour-axis");
            axis.setAttribute("aria-hidden", "true");
            axis.append(element("span", count(maximum)), element("span", "0"));
            for (const [i, hour] of summary.hours.entries()) {
                const column = element("div", undefined, "city-hour-column"), track = element("div", undefined, "city-hour-track");
                const bar = element("div", undefined, "city-hour-bar"), text = `${String(hour.hour).padStart(2, "0")}:00`;
                column.title = `${text} · ${count(hour.departures)} departures`;
                column.setAttribute("role", "img"); column.setAttribute("aria-label", column.title);
                bar.style.height = `${100 * hour.departures / maximum}%`;
                if (hour.departures === peak) bar.classList.add("city-hour-peak");
                track.append(bar); column.append(track, element("span", i % 3 === 0 ? text : "", "city-hour-label")); bars.append(column);
            }
            plot.append(axis, bars);
            figure.append(plot, element("p", `Busiest hour: ${String(summary.hours.find(h => h.departures === peak).hour).padStart(2, "0")}:00 · ${count(peak)} departures`, "replay-muted city-chart-note"));
            host.append(figure, routeTable(summary.routes));
        }
        renderedKey = key;
    }
    root.suntrainOverview = {summarize, pending, render};
})(typeof window !== "undefined" ? window : globalThis);
