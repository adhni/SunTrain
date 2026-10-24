(function (root) {
    'use strict';
    // A visual shorthand for relative vehicle capacity, not a fleet formation.
    const radiusStops = [[5, 1.8], [9, 3.1], [12, 4], [15, 5]];
    function bodyKind(city, mode = 'train') {
        return city === 'melbourne' && ['train', 'tram'].includes(mode) ? mode : '';
    }
    function radius(zoom, scale = 1) {
        for (let i = 1; i < radiusStops.length; i++) {
            if (zoom <= radiusStops[i][0]) {
                const [z0, r0] = radiusStops[i - 1], [z1, r1] = radiusStops[i];
                return (r0 + (r1 - r0) * Math.max(0, (zoom - z0) / (z1 - z0))) * scale;
            }
        }
        return radiusStops.at(-1)[1] * scale;
    }
    function separation(a, b) {
        const latitude = (a[1] + b[1]) * Math.PI / 360;
        return Math.hypot((a[0] - b[0]) * Math.cos(latitude), a[1] - b[1]) * Math.PI / 180 * 6371000;
    }
    function footprint(service, position, day, now, spacing, pointAlong) {
        const points = [[position.lon, position.lat]];
        const dots = !service.mode || service.mode === 'train' ? 4 : service.mode === 'tram' ? 2 : 1;
        if (dots === 1 || position.approximate || !(spacing > 0)) return points;
        const count = service.stopIds ? service.stopIds.length : service.stops.length;
        const time = (i, column) => service.stopIds ? service.times[i * 2 + column - 1] : service.stops[i][column];
        const localNow = now - (service.timeOffset || 0);
        let index = position.index, fraction;
        if (index > 0 && (index === count - 1 || localNow < time(index, 2))) {
            index--; fraction = 1; // A dwelling vehicle keeps its body on the incoming track.
        } else {
            const duration = index + 1 < count ? time(index + 1, 1) - time(index, 2) : 0;
            fraction = duration > 0 ? Math.max(0, Math.min(1, (localNow - time(index, 2)) / duration)) : 0;
        }
        const pathAt = leg => {
            const path = day.paths[service.legs?.[leg]];
            return path && ['track', 'shape'].includes(path.quality) && path.distances?.at(-1) > 0 ? path : null;
        };
        const current = pathAt(index);
        if (!current) return points;
        // Sample spatial offsets from ONE scheduled position. No independently
        // delayed animations, rotated sprites, or straight shortcuts across bends.
        for (let dot = 1; dot < dots; dot++) {
            let leg = index, path = current, distance = fraction * current.distances.at(-1) - dot * spacing;
            while (distance < 0) {
                const previous = leg > 0 ? pathAt(leg - 1) : null;
                // Never bridge unresolved geometry or jump between disconnected legs.
                if (!previous || separation(previous.coordinates.at(-1), path.coordinates[0]) > 25) return points;
                path = previous; leg--; distance += path.distances.at(-1);
            }
            const point = pointAlong(path, distance / path.distances.at(-1));
            if (!point) break;
            points.push(point);
        }
        return points;
    }
    const api = {bodyKind, radiusStops, radius, footprint};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainVehicles = api;
})(typeof window !== 'undefined' ? window : globalThis);
