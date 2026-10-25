(function (root) {
    "use strict";
    function bearing(a, b) {
        const rad = Math.PI / 180, lat1 = a[1] * rad, lat2 = b[1] * rad, delta = (b[0] - a[0]) * rad;
        return (Math.atan2(Math.sin(delta) * Math.cos(lat2),
            Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(delta)) / rad + 360) % 360;
    }
    function bounds(stations, centre = 135) {
        if (!stations.length) return null;
        const lons = stations.map(s => (s.lon % 360 + 360) % 360).sort((a,b) => a-b);
        let gap = -1, first = lons[0];
        for (let i=0; i<lons.length; i++) {
            const next = lons[(i+1)%lons.length] + (i===lons.length-1 ? 360 : 0);
            if (next-lons[i]>gap) { gap=next-lons[i]; first=next%360; }
        }
        const west = first, east = first+360-gap;
        const shift = 360*Math.round((centre-(west+east)/2)/360);
        return [[west+shift, Math.min(...stations.map(s=>s.lat))],
            [east+shift, Math.max(...stations.map(s=>s.lat))]];
    }
    function priceLabel(service) {
        const p=service.price;
        if (!p || !Number.isSafeInteger(p.amount_minor) || p.amount_minor<=0 || !['MYR','USD'].includes(p.currency)) return 'Price unavailable';
        return new Intl.NumberFormat(root.suntrainI18n?.locale || 'en-MY', {style:'currency',currency:p.currency,currencyDisplay:'code'}).format(p.amount_minor/100);
    }
    function captureTime(at, timezone) {
        const text=new Intl.DateTimeFormat(root.suntrainI18n?.locale || 'en-AU', {
            timeZone:timezone,year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZoneName:'shortOffset'
        }).format(new Date(at));
        const label={'Asia/Kuala_Lumpur':'MYT','Asia/Singapore':'SGT','Asia/Kolkata':'IST','Asia/Seoul':'KST'}[timezone];
        return label?text.replace(/GMT\+(?:[89]|5[.:]30)/,label):text;
    }
    function planeImage(color = '#f57c28') {
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const points = [[32,5],[36,10],[37,25],[57,39],[57,44],[37,37],[36,50],[43,55],
            [43,59],[32,55],[21,59],[21,55],[28,50],[27,37],[7,44],[7,39],[27,25],[28,10]];
        ctx.beginPath(); points.forEach(([x,y], i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.closePath();
        ctx.lineJoin = 'round'; ctx.strokeStyle = '#17212b'; ctx.lineWidth = 7; ctx.stroke();
        ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 4; ctx.stroke(); ctx.fillStyle = color; ctx.fill();
        return ctx.getImageData(0, 0, 64, 64);
    }
    function airportImage(code) {
        const canvas = document.createElement('canvas'); canvas.width = 88; canvas.height = 40;
        const ctx = canvas.getContext('2d');
        ctx.font = 'bold 22px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.lineJoin = 'round'; ctx.lineWidth = 6; ctx.strokeStyle = '#17212b'; ctx.strokeText(code, 44, 20);
        ctx.fillStyle = '#fff'; ctx.fillText(code, 44, 20);
        return ctx.getImageData(0, 0, 88, 40);
    }
    const api = {bearing, bounds, priceLabel, captureTime, planeImage, airportImage};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainFlights = api;
})(typeof window !== 'undefined' ? window : globalThis);
