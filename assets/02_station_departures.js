(function (root) {
    "use strict";
    const PAGE_SIZE = 15;
    const count = service => service.stopIds ? service.stopIds.length : service.stops.length;
    const stopId = (service, index) => service.stopIds ? service.stopIds[index] : service.stops[index][0];
    const departure = (service, index) => (service.stopIds ? service.times[index * 2 + 1] : service.stops[index][2]) + (service.timeOffset || 0);

    function stationCalls(services, station, start, end, event = 'departure') {
        const calls = [], occurrences = new Map();
        for (const service of services) {
            const topology = service.stopIds || service.stops;
            if (!occurrences.has(topology)) {
                const indices = [];
                // Final clocks are often copied arrivals, not departures.
                const arrival = event === 'arrival';
                for (let i = arrival ? 1 : 0; i < count(service) - (arrival ? 0 : 1); i++) if (stopId(service, i) === station) indices.push(i);
                occurrences.set(topology, indices);
            }
            for (const index of occurrences.get(topology)) {
                const at = event === 'arrival' ? (service.stopIds ? service.times[index * 2] : service.stops[index][1]) + (service.timeOffset || 0) : departure(service, index);
                if (Number.isFinite(at) && at >= start && (service.mode === 'flight' ? at < end : at <= end))
                    calls.push({service, index, at, event, key: JSON.stringify([service.id, index, event])});
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
            const rawMode=(service.mode || "train").replaceAll("_", " ");
            const label = `${root.suntrainI18n?.translate(rawMode[0].toUpperCase()+rawMode.slice(1)) || rawMode} · ${service.line}`;
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
    const airportZoneLabels = {'Asia/Ho_Chi_Minh':'ICT','Asia/Manila':'PHT','Asia/Bangkok':'ICT','Asia/Jakarta': 'WIB', 'Asia/Pontianak': 'WIB', 'Asia/Makassar': 'WITA', 'Asia/Jayapura': 'WIT', 'Asia/Kuala_Lumpur': 'MYT', 'Asia/Kuching': 'MYT', 'Asia/Singapore':'SGT','Asia/Kolkata':'IST','Asia/Seoul':'KST','Asia/Tokyo':'JST','Asia/Shanghai':'CST'};
    function formatCallTime(at, timezone) {
        const formatted = new Intl.DateTimeFormat(root.suntrainI18n?.locale || "en-AU", {timeZone: timezone, day: "numeric", month: "short",
            hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "shortOffset"}).format(new Date(at * 1000));
        return airportZoneLabels[timezone] ? formatted.replace(/GMT\+(?:[789]|5[.:]30)/, airportZoneLabels[timezone]) : formatted;
    }
    function formatBoardTime(at, now, timezone) {
        const locale = root.suntrainI18n?.locale || "en-AU";
        const day = new Intl.DateTimeFormat('en-AU', {timeZone: timezone, year: 'numeric', month: 'numeric', day: 'numeric'});
        const date = new Intl.DateTimeFormat(locale, {timeZone: timezone, day: 'numeric', month: 'short'});
        const time = new Intl.DateTimeFormat(locale, {timeZone: timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).format(new Date(at * 1000));
        return time + (day.format(new Date(at * 1000)) !== day.format(new Date(now * 1000)) ? ' · ' + date.format(new Date(at * 1000)) : '');
    }
    const api = {stationCalls, upcomingPage, stationCatalogue, formatCallTime, formatBoardTime};
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    if (!root.document) return;
    const $ = id => document.getElementById(id);
    function node(tag, text, className) {
        const element = document.createElement(tag);
        if (text !== undefined) { if (root.suntrainI18n) root.suntrainI18n.bind(element, text); else element.textContent = text; }
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
            document.addEventListener("keydown", event => {
                if (!this.expanded) return;
                if (event.key === "Escape") { event.preventDefault(); event.stopImmediatePropagation(); this.setExpanded(false); return; }
                if (event.key !== "Tab") return;
                const card = this.host.closest(".replay-detail-card");
                const controls = [...card.querySelectorAll('button, input, select, summary, [tabindex]')]
                    .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length);
                const first = controls[0], last = controls.at(-1);
                if (event.shiftKey && (document.activeElement === first || !card.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
                else if (!event.shiftKey && (document.activeElement === last || !card.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
            }, true);
        }
        reset() {
            this.close(); this.station = null; this.services = null; this.catalogue = null; this.calls = []; this.page = 0;
            this.event = 'departure'; this.fullDay = false;
            this.host.replaceChildren(); this.list = null; this.search = null; this.choices = null;
        }
        close() {
            this.setExpanded(false);
            this.previewCall=null;
            this.visible = false; this.host.hidden = true;
            $("replay-details").hidden = false;
            $("replay-panel").classList.remove("replay-browsing");
            const eyebrow = document.querySelector('.replay-detail-heading .replay-eyebrow');
            if (eyebrow) root.suntrainI18n?.bind(eyebrow, 'YOUR JOURNEY');
            $("replay-open-departures").setAttribute("aria-expanded", "false");
        }
        setExpanded(value) {
            value = !!value && this.visible && this.station !== null;
            if (!!this.expanded === value) return;
            this.expanded = value;
            const card = this.host.closest(".replay-detail-card");
            $("replay-panel").classList.toggle("replay-board-expanded", value);
            document.body.classList.toggle("replay-board-lock", value);
            if (value) {
                this.replay.pause(); card.scrollTop = 0;
                card.setAttribute('role', 'dialog'); card.setAttribute('aria-modal', 'true'); card.setAttribute('aria-labelledby', 'departure-title');
            } else {
                for (const name of ['role', 'aria-modal', 'aria-labelledby']) card.removeAttribute(name);
            }
            const close = $("replay-close-details");
            const label = value ? "Back to map" : "Close";
            const ariaLabel = value ? "Back to map" : "Close service details";
            if (root.suntrainI18n) { root.suntrainI18n.bind(close, label); root.suntrainI18n.bind(close, ariaLabel, 'aria-label'); }
            else { close.textContent = label; close.setAttribute('aria-label', ariaLabel); }
            this.expandButton?.setAttribute('aria-expanded', String(value));
            if (this.list) this.update(true);
            if (this.replay.active) (value ? close : this.expandButton)?.focus({preventScroll: true});
        }
        refresh() {
            const replay = this.replay;
            if (this.services !== replay.filtered) {
                this.services = replay.filtered; this.catalogue = null; this.page = 0; this.signature = null;
                this.calls = this.station === null ? [] : stationCalls(this.services, this.station, replay.day.start, replay.day.end, this.event);
                this.destinationRows = this.station === null || replay.day.replay_kind !== 'flights' ? [] : root.suntrainFlightNetwork.destinations(this.services, this.station, replay.day);
                if (this.visible) this.render();
            }
        }
        open(station = this.station, fullDay = station === this.station && this.fullDay) {
            const replay = this.replay;
            if (!replay.day || replay.loading) return;
            if (replay.day.replay_kind === 'flights' && station != null) {
                const code = replay.day.stations[station].code;
                if (replay.filters.airports?.length !== 1 || replay.filters.airports[0] !== code)
                    root.dash_clientside.set_props('replay-airports', {value: [code]});
                if (replay.filters.airportDirection === 'arrivals') this.event = 'arrival';
            }
            this.fullDay = !!fullDay;
            if (station !== this.station) { this.station = station; this.services = null; this.page = 0; }
            this.visible = false; this.refresh(); this.visible = true;
            replay.selected = null; replay.setFollow(false); replay.staticDirty = true;
            replay.demandPinned = false; replay.demandPopupId = null;
            replay.popup?.remove(); replay.showDetails(true);
            $("replay-close-details").hidden = false; $("replay-details").hidden = true;
            $("replay-panel").classList.add("replay-browsing");
            const eyebrow = document.querySelector('.replay-detail-heading .replay-eyebrow');
            if (eyebrow) root.suntrainI18n?.bind(eyebrow, replay.day.replay_kind === 'flights' ? 'AIRPORT BOARD' : 'STATION DEPARTURES');
            $("replay-open-departures").setAttribute("aria-expanded", "true");
            this.host.hidden = false; this.render(); replay.paint(true);
            (this.station === null ? this.search : this.title).focus();
        }
        render() {
            const replay = this.replay;
            const flights = replay.day.replay_kind === 'flights', arrivals = flights && this.event === 'arrival';
            this.timezone = flights && this.station !== null ? replay.day.stations[this.station].timezone : replay.day.timezone;
            this.host.replaceChildren(); this.signature = null;
            this.title = node("h3", this.station === null ? (flights ? 'Airports' : "Station departures") : replay.day.stations[this.station].name);
            this.title.tabIndex = -1; this.title.id = "departure-title";
            this.expandButton = button(flights ? 'Expand board' : "Expand departures", () => this.setExpanded(!this.expanded));
            this.expandButton.disabled = this.station === null;
            this.expandButton.setAttribute('aria-expanded', String(!!this.expanded));
            const actions = node('div', undefined, 'departure-board-actions'); actions.append(this.expandButton);
            this.host.append(actions);
            this.host.append(this.title, node("p", flights ?
                `Board window: ${formatCallTime(replay.day.start, this.timezone)} → ${formatCallTime(replay.day.end, this.timezone)}` :
                `${replay.day.business_date} · ${this.timezone} · Loaded replay services only`, "replay-muted replay-small"));
            if (flights) {
                const tabs = node('div', undefined, 'departure-event-tabs');
                for (const [event, label] of [['departure', 'Departures'], ['arrival', 'Arrivals'], ['destinations', 'Destinations']]) {
                    const control = button(label, () => {
                        root.dash_clientside.set_props('replay-airport-direction', {value: event === 'arrival' ? 'arrivals' : 'departures'});
                        this.event = event; this.fullDay = false; this.services = null; this.page = 0; this.refresh();
                        this.host.querySelector(`[data-event="${event}"]`)?.focus();
                    });
                    control.disabled = event === 'destinations' && this.station === null;
                    control.dataset.event = event; control.setAttribute('aria-pressed', String(event === this.event)); tabs.append(control);
                }
                const clockNote=replay.day.timezone==='Asia/Ho_Chi_Minh'?'Airport times are local. The replay clock uses Vietnam time (ICT, UTC+7).':replay.day.timezone==='Asia/Manila'?'Airport times are local. The replay clock uses Philippine time (UTC+8).':replay.day.timezone==='Asia/Bangkok'?'Airport times are local. The replay clock uses ICT (UTC+7).':replay.day.timezone==='UTC'?'Airport times and dates are local. The replay clock uses UTC.':replay.day.timezone==='Asia/Shanghai'?(replay.day.flight_scopes?'Airport times are local. The replay clock uses China time (UTC+8).':'Airport times and the replay clock use China time (UTC+8).'):replay.day.timezone==='Asia/Tokyo'?'Airport times are local. The replay clock uses JST.':replay.day.timezone==='Asia/Seoul'?'Airport times are local. The replay clock uses KST.':replay.day.timezone==='Asia/Kolkata'?'Airport times are local. The replay clock uses IST.':replay.day.timezone==='Asia/Singapore'?'Airport times are local. The replay clock uses SGT.':replay.day.timezone==='Asia/Dubai'?'Airport times are local. The replay clock uses Dubai time (UTC+4).':replay.day.timezone === 'Asia/Jakarta' ? 'Airport times are local. The replay clock uses WIB.' : replay.day.timezone === 'Asia/Kuala_Lumpur' ? 'Airport times are local. The replay clock uses MYT.' : 'Airport times are local. The replay clock uses Melbourne time.';
                this.host.append(tabs,node('p',clockNote,'replay-muted replay-small'));
                if (replay.day.schedule?.fare_context) this.host.append(node('p', 'Captured fares · 1 adult · Economy · One-way. Prices may change.', 'replay-muted replay-small'));
                if (replay.day.schedule?.fare_context?.currency==='mixed') this.host.append(node('p','Captured fares retain their original currencies. No currency conversion.','replay-muted replay-small'));
            }
            const picker = node("details"); picker.open = this.station === null;
            picker.append(node("summary", this.station === null ? (flights ? 'Choose an airport' : "Choose a stop") : (flights ? 'Change airport' : "Change stop")));
            const label = node("label", flights ? 'Find an airport by name or code' : "Find a station, stop or pier"); label.htmlFor = "departure-search";
            this.search = node("input"); this.search.id = "departure-search"; this.search.type = "search";
            root.suntrainI18n ? root.suntrainI18n.bind(this.search,"Search by name or route…","placeholder") : this.search.placeholder = "Search by name or route…";
            this.choices = node("select"); this.choices.size = 5; if(root.suntrainI18n) root.suntrainI18n.bind(this.choices, "Matching stops", "aria-label"); else this.choices.setAttribute("aria-label", "Matching stops");
            this.matchCount = node("p", "", "replay-muted replay-small");
            this.search.addEventListener("input", () => this.updateChoices());
            this.choose = button("Open departures", () => { if (this.choices.value !== "") this.open(Number(this.choices.value)); });
            this.choices.addEventListener("change", () => { this.choose.disabled = this.choices.value === ""; });
            picker.append(label, this.search, this.choices, this.matchCount, this.choose); this.host.append(picker); this.updateChoices();
            this.clock = node("p", "", "replay-muted replay-small");
            this.list = node("div", undefined, "departure-list");
            this.previous = button("Previous", () => { this.page--; this.update(true); if (this.event === "destinations") this.host.closest(".replay-detail-card").scrollTop = 0; });
            this.next = button("Next", () => { this.page++; this.update(true); if (this.event === "destinations") this.host.closest(".replay-detail-card").scrollTop = 0; });
            this.pageLabel = node("span");
            const nav = node("nav", undefined, "departure-pagination"); if(root.suntrainI18n) root.suntrainI18n.bind(nav, "Departure pages", "aria-label"); else nav.setAttribute("aria-label", "Departure pages");
            nav.append(this.previous, this.pageLabel, this.next);
            const columns = node('div', undefined, 'departure-columns'); columns.hidden = this.event === 'destinations'; columns.setAttribute('aria-hidden', 'true');
            for (const title of [arrivals ? 'Arrival' : 'Departure', flights ? 'Flight' : 'Route', arrivals ? 'Origin' : 'Destination', 'Operator']) columns.append(node('span', title));
            this.host.append(this.clock, node("p", flights ? 'Replay paused · scheduled flights' : "Replay paused · scheduled departures", "departure-board-note replay-muted"), columns, this.list, nav,
                node("p", flights ? 'Schedule snapshot. Loaded flights only; search coverage is partial.' : "Scheduled replay events; boarding permissions may differ. Final stops are excluded.", "replay-muted replay-small"));
            this.update(true);
        }
        updateLocale() {
            const page=this.page, query=this.search?.value || '', open=this.host.querySelector('details')?.open;
            this.catalogue=null;this.render();this.search.value=query;this.updateChoices();
            if(open!==undefined)this.host.querySelector('details').open=open;
            this.page=page;this.update(true);
        }
        updateJourneyLocale() {
            const host=document.querySelector('.departure-context');
            if(host && this.previewCall) {
                const text=`${this.replay.day.replay_kind === 'flights' ? 'At' : 'From'} ${this.replay.day.stations[this.station].name} · ${formatCallTime(this.previewCall.at,this.timezone || this.replay.day.timezone)}`;
                if(root.suntrainI18n)root.suntrainI18n.bind(host,text);else host.textContent=text;
            }
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
            if(root.suntrainI18n) root.suntrainI18n.bind(this.matchCount, matches.length > 60 ? `Showing 60 of ${matches.length} stops. Refine your search.` : `${matches.length} matching stops`); else this.matchCount.textContent = matches.length > 60 ? `Showing 60 of ${matches.length} stops. Refine your search.` : `${matches.length} matching stops`;
        }
        update(force = false) {
            if (!this.visible || !this.list) return;
            const replay = this.replay;
            const flights = replay.day.replay_kind === 'flights', arrivals = flights && this.event === 'arrival';
            if (flights && this.event === 'destinations') { this.updateDestinations(force); return; }
            const clockText = this.fullDay ? (arrivals ? 'Full selected replay day · arrivals' : 'Full selected replay day · departures') : `${arrivals ? 'Arrivals from' : 'Departures from'} ${formatCallTime(replay.now, this.timezone)}`;
            if(root.suntrainI18n) root.suntrainI18n.bind(this.clock, clockText); else this.clock.textContent = clockText;
            // Keep a keyboard-focused departure stable until focus leaves the list.
            if (!force && this.list.contains(document.activeElement)) return;
            const result = upcomingPage(this.calls, this.fullDay ? replay.day.start : replay.now, this.page); this.page = result.page;
            const signature = JSON.stringify([this.page, result.total, result.rows.map(row => row.key)]);
            if (!force && signature === this.signature) return;
            this.signature = signature; this.list.replaceChildren();
            if (!result.rows.length) this.list.append(node("p", this.station === null ? (flights ? 'Choose an airport to explore its flights.' : "Choose a stop to explore its journeys.") : (flights ? 'No upcoming flights match. Try an earlier replay time or change the filters.' : "No upcoming departures match the current filters. Try an earlier replay time or change the filters."), "replay-muted"));
            for (const call of result.rows) {
                const service = call.service;
                const row = button("", () => replay.select(service.id, call)); row.className = "departure-row";
                row.style.setProperty("--journey-color", this.core.vehicleColor(service, replay.day.city));
                row.append(node("strong", this.expanded ? formatBoardTime(call.at, replay.now, this.timezone) : formatCallTime(call.at, this.timezone), 'departure-time'),
                    node("span", flights ? service.number : service.line, 'departure-route'), node("span", arrivals ? service.origin : service.destination, 'departure-destination'),
                    node("small", flights ? service.operator : `${service.operator} · ${service.number}`, 'departure-operator'));
                if (service.frequency_based) row.append(node("small", "Frequency-based estimate"));
                if (service.terminal_arrival_missing) row.append(node("small", "Terminal arrival unavailable"));
                if (flights && replay.day.schedule?.fare_context) row.append(node('small', root.suntrainFlights.priceLabel(service), 'departure-fare'));
                this.list.append(row);
            }
            const pageText = `${result.page + 1} / ${result.pages} · ${result.total} ${flights ? 'flights' : 'departures'}`;
            if(root.suntrainI18n) root.suntrainI18n.bind(this.pageLabel, pageText); else this.pageLabel.textContent = pageText;
            this.previous.disabled = !result.page; this.next.disabled = result.page + 1 >= result.pages;
        }
        updateDestinations(force) {
            root.suntrainI18n.bind(this.clock, 'Captured departures in the full selected replay day. Click a destination to see its flights.');
            const rows = this.destinationRows || [], pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
            this.page = Math.max(0, Math.min(this.page, pages - 1));
            const signature = JSON.stringify(['destinations', this.page, rows]);
            if (!force && signature === this.signature) return;
            this.signature = signature; this.list.replaceChildren();
            if (!rows.length) this.list.append(node('p', 'No captured destinations match this airport and these filters.', 'replay-muted'));
            for (const row of rows.slice(this.page * PAGE_SIZE, (this.page + 1) * PAGE_SIZE)) {
                const airport = this.replay.day.stations[row.destination];
                const control = button('', () => this.replay.focusFlightConnection(this.station, row.destination));
                control.className = 'destination-row';
                control.append(node('strong', airport.code, 'destination-code'), node('span', airport.name),
                    node('strong', `${row.count} captured departures`),
                    node('small', row.carriers.map(([code,name]) => `${code} · ${name}`).join(' / ')));
                this.list.append(control);
            }
            root.suntrainI18n.bind(this.pageLabel, `${this.page + 1} / ${pages} · ${rows.length} destinations`);
            this.previous.disabled = this.page === 0; this.next.disabled = this.page + 1 >= pages;
        }
        journey(host, call) {
            const wasExpanded = !!this.expanded;
            this.setExpanded(false);
            this.previewCall=call;
            const eyebrow = document.querySelector('.replay-detail-heading .replay-eyebrow');
            if (eyebrow) root.suntrainI18n?.bind(eyebrow, 'YOUR JOURNEY');
            this.visible = false; this.host.hidden = true; $("replay-details").hidden = false;
            if (!call) { this.close(); return; }
            const replay = this.replay;
            replay.setFollow(false);
            host.append(button(replay.day.replay_kind === 'flights' ? 'Back to airport board' : "Back to departures", () => { this.open(); if (wasExpanded) this.setExpanded(true); }),
                button(call.event === 'arrival' ? 'Go to arrival' : "Go to departure", () => {
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
            host.append(node("p", `${replay.day.replay_kind === 'flights' ? 'At' : 'From'} ${replay.day.stations[this.station].name} · ${formatCallTime(call.at, this.timezone)}`, "replay-muted replay-small departure-context"));
        }
    }
    root.suntrainDepartures = {...api, Board};
})(typeof window !== "undefined" ? window : globalThis);
