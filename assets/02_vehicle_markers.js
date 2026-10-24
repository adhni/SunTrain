(function (root) {
    'use strict';
    // A visual shorthand for relative vehicle capacity, not a fleet formation.
    function bodyKind(city, mode = 'train') {
        return city === 'melbourne' && ['train', 'tram'].includes(mode) ? mode : '';
    }
    function heading(service, position, day, now, pointAlong) {
        const count = service.stopIds ? service.stopIds.length : service.stops.length;
        const time = (i, column) => service.stopIds ? service.times[i * 2 + column - 1] : service.stops[i][column];
        const index = Math.min(position.index, count - 2);
        const path = day.paths[service.legs?.[index]];
        if (!path || position.approximate || !['track', 'shape'].includes(path.quality)) return null;
        const duration = time(index + 1, 1) - time(index, 2);
        const fraction = duration > 0 ? Math.max(0, Math.min(1, (now - (service.timeOffset || 0) - time(index, 2)) / duration)) : 0;
        const a = pointAlong(path, Math.max(0, fraction - 0.002));
        const b = pointAlong(path, Math.min(1, fraction + 0.002));
        if (!a || !b || (a[0] === b[0] && a[1] === b[1])) return null;
        return (Math.atan2((b[0] - a[0]) * Math.cos(a[1] * Math.PI / 180), b[1] - a[1]) * 180 / Math.PI + 360) % 360;
    }
    function image(map, kind, color) {
        const key = `vehicle-${kind}-${color}`;
        if (map.hasImage(key)) return key;
        const dots = kind === 'train' ? 4 : 2;
        const canvas = document.createElement('canvas');
        canvas.width = 16 * 2; canvas.height = (16 + (dots - 1) * 9) * 2;
        const ctx = canvas.getContext('2d'); ctx.scale(2, 2);
        ctx.lineCap = 'round';
        for (const [stroke, width] of [['#17212b', 5.5], ['#fff', 3.5], [color, 1.5]]) {
            ctx.beginPath(); ctx.moveTo(8, 8); ctx.lineTo(8, 8 + (dots - 1) * 9);
            ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke();
        }
        for (let i = dots - 1; i >= 0; i--) {
            ctx.beginPath(); ctx.arc(8, 8 + i * 9, 3.4, 0, Math.PI * 2);
            ctx.fillStyle = color; ctx.fill(); ctx.strokeStyle = '#17212b'; ctx.lineWidth = 2.8; ctx.stroke();
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.4; ctx.stroke();
        }
        map.addImage(key, ctx.getImageData(0, 0, canvas.width, canvas.height), {pixelRatio: 2});
        return key;
    }
    const api = {bodyKind, heading, image};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainVehicles = api;
})(typeof window !== 'undefined' ? window : globalThis);
