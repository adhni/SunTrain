(function (root) {
    "use strict";
    const scale = [[0, "#440154"], [100, "#3b528b"], [500, "#21918c"], [2000, "#5ec962"], [5000, "#fde725"]];
    function upperBound(times, time) {
        let low = 0, high = times.length;
        while (low < high) {
            const middle = (low + high) >>> 1;
            if (times[middle] <= time) low = middle + 1;
            else high = middle;
        }
        return low;
    }
    function buildIndex(services, day) {
        const stations = new Map();
        for (const service of services.filter(s => !s.mode || s.mode === "train")) for (const stop of service.stops) {
            const [id, , departure, , , boardings] = stop;
            if (!Number.isFinite(departure)) continue;
            if (!stations.has(id)) stations.set(id, {...day.stations[id], id, events: []});
            stations.get(id).events.push([departure, boardings]);
        }
        return [...stations.values()].map(station => {
            station.events.sort((a, b) => a[0] - b[0]);
            const times = [], totals = [0], known = [0], missing = [0];
            for (const [time, count] of station.events) {
                const valid = Number.isFinite(count) && count >= 0;
                times.push(time);
                totals.push(totals[totals.length - 1] + (valid ? count : 0));
                known.push(known[known.length - 1] + Number(valid));
                missing.push(missing[missing.length - 1] + Number(!valid));
            }
            const {events, ...location} = station;
            return {...location, times, totals, known, missing};
        });
    }
    function snapshot(index, end, seconds) {
        const rows = [], features = [];
        let total = 0, missingCalls = 0, knownCalls = 0;
        for (const station of index) {
            // Right-closed window: (end - seconds, end]. Seeking never accumulates counts.
            const first = upperBound(station.times, end - seconds), last = upperBound(station.times, end);
            const row = {id: station.id, name: station.name, lon: station.lon, lat: station.lat,
                boardings: station.totals[last] - station.totals[first],
                knownCalls: station.known[last] - station.known[first], missingCalls: station.missing[last] - station.missing[first]};
            rows.push(row); total += row.boardings; missingCalls += row.missingCalls; knownCalls += row.knownCalls;
            if (row.boardings > 0) features.push({type: "Feature", properties: row,
                geometry: {type: "Point", coordinates: [row.lon, row.lat]}});
        }
        return {rows, features, total, stationCount: features.length, missingCalls, knownCalls, end, start: end - seconds};
    }
    const api = {scale, buildIndex, snapshot};
    root.suntrainDemand = api;
    if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
