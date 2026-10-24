(function (root) {
    'use strict';
    // The replay day owns departures by UTC instant; carry-ins never add frequency.
    function ownedFlights(services, day) {
        const seen = new Set();
        return services.filter(s => {
            const at = s.stops?.[0]?.[2];
            if (s.mode !== 'flight' || seen.has(s.id) || !Number.isFinite(at) || at < day.start || at >= day.end) return false;
            seen.add(s.id); return true;
        });
    }
    function destinations(services, station, day) {
        const groups = new Map();
        for (const s of ownedFlights(services, day)) {
            if (s.stops[0][0] !== station) continue;
            const destination = s.stops.at(-1)[0];
            if (!groups.has(destination)) groups.set(destination, {destination, count: 0, carriers: new Map()});
            const row = groups.get(destination); row.count++;
            row.carriers.set(s.carrier, s.operator);
        }
        return [...groups.values()].map(row => ({...row, carriers: [...row.carriers].sort((a,b) => a[0].localeCompare(b[0]))}))
            .sort((a,b) => b.count-a.count || day.stations[a.destination].code.localeCompare(day.stations[b.destination].code));
    }
    function frequencyWidth(count) { return Math.min(12, 0.8 + Math.sqrt(count) * 0.85); }
    function frequencyNetwork(services, day) {
        const groups = new Map();
        for (const s of ownedFlights(services, day)) {
            const origin = s.stops[0][0], destination = s.stops.at(-1)[0];
            const codes = [day.stations[origin].code, day.stations[destination].code].sort();
            const key = codes.join('-');
            if (!groups.has(key)) groups.set(key, {a: origin, b: destination, count: 0, forward: 0, reverse: 0, path: s.legs[0], carriers: new Set()});
            const row = groups.get(key); row.count++; row.carriers.add(s.carrier);
            if (origin === row.a) row.forward++; else row.reverse++;
        }
        return [...groups.values()].map(row => ({type: 'Feature', properties: {
            a: row.a, b: row.b, count: row.count, forward: row.forward, reverse: row.reverse,
            carriers: [...row.carriers].sort().join(', '), width: frequencyWidth(row.count),
            label: `${day.stations[row.a].code} ↔ ${day.stations[row.b].code}`},
            geometry: {type: 'LineString', coordinates: day.paths[row.path].coordinates}}));
    }
    const api = {ownedFlights, destinations, frequencyNetwork, frequencyWidth};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainFlightNetwork = api;
})(typeof window !== 'undefined' ? window : globalThis);
