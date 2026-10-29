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
    const marker = Object.freeze({planeZoom: 4.5, dotRadius: 2.2, dotStroke: 0.8,
        planeSize: 16, selectedSize: 22, pickingRadius: 12});
    const movingLayers = ['replay-flight-dots', 'replay-planes', 'replay-selected-plane', 'replay-selected-flight'];
    const planeKeys = new Map();
    function planeKey(service) {
        const carrier = service.carrier || 'Unknown', colour = service.color || '#f57c28';
        if (!planeKeys.has(carrier)) planeKeys.set(carrier, new Map());
        const colours = planeKeys.get(carrier);
        if (!colours.has(colour)) colours.set(colour, 'plane-' + JSON.stringify([carrier, colour]));
        return colours.get(colour);
    }
    function openingBounds(day) {
        if (!['hub', 'network'].includes(day.flight_view_kind)) return day.bounds;
        const ids = new Set(day.services.flatMap(s => s.stops.map(stop => stop[0])));
        return bounds([...ids].map(id => day.stations[id]), day.flight_geometry ? 0 : 135) || day.bounds;
    }
    function greatCircle(a, b, segments = 64, anchor = 0) {
        const rad = Math.PI / 180;
        const vector = ([lon, lat]) => [Math.cos(lat*rad)*Math.cos(lon*rad), Math.cos(lat*rad)*Math.sin(lon*rad), Math.sin(lat*rad)];
        const u = vector(a), v = vector(b), angle = Math.acos(Math.max(-1, Math.min(1, u.reduce((n,x,i)=>n+x*v[i],0))));
        const coordinates = [], distances = [0];
        for (let i=0; i<=segments; i++) {
            const f = i / segments;
            const p = angle < 1e-10 ? u : u.map((x,j)=>(Math.sin((1-f)*angle)*x + Math.sin(f*angle)*v[j])/Math.sin(angle));
            coordinates.push(angle < 1e-10 ? [...a] : [Math.round(Math.atan2(p[1],p[0])/rad*1e6)/1e6,
                Math.round(Math.atan2(p[2],Math.hypot(p[0],p[1]))/rad*1e6)/1e6]);
        }
        coordinates[0] = [...a]; coordinates[segments] = [...b];
        let previous = anchor;
        for (const p of coordinates) {
            const shift = (previous-p[0])/360, lower = Math.floor(shift);
            // Python's existing arc generator rounds exact world-copy ties to even.
            const worlds = shift-lower === 0.5 ? (lower%2 === 0 ? lower : lower+1) : Math.round(shift);
            p[0] += 360*worlds; previous = p[0];
        }
        for (let i=1; i<coordinates.length; i++) {
            const a=coordinates[i-1], b=coordinates[i];
            const x=(b[0]-a[0])*rad*Math.cos((a[1]+b[1])/2*rad), y=(b[1]-a[1])*rad;
            distances.push(Math.round((distances[i-1]+Math.hypot(x,y)*6371000)*100)/100);
        }
        return {coordinates, distances};
    }
    function hydratePaths(day) {
        if (day.flight_geometry !== 'great_circle_v1' || day._flightPathsHydrated) return;
        day._flightPathsHydrated = true; day._generatedFlightPaths = 0;
        for (const path of Object.values(day.paths)) {
            const generate = () => {
                const [a,b] = path.endpoints.map(i=>day.stations[i]);
                const arc = greatCircle([a.lon,a.lat], [b.lon,b.lat], path.segments, path.anchor);
                Object.defineProperties(path, {coordinates: {value:arc.coordinates, enumerable:true, configurable:true},
                    distances: {value:arc.distances, enumerable:true, configurable:true}});
                day._generatedFlightPaths++;
                return arc;
            };
            Object.defineProperties(path, {coordinates: {get:()=>generate().coordinates, enumerable:true, configurable:true},
                distances: {get:()=>generate().distances, enumerable:true, configurable:true}});
        }
    }
    function paintInterval(day, zoom) {
        return day.flight_geometry === 'great_circle_v1' && zoom < marker.planeZoom ? 250 : 60;
    }
    // Project the nearest world copy; routes may contain longitudes beyond ±180°.
    function project(map, coordinate) {
        const lon = coordinate[0] + 360 * Math.round((map.getCenter().lng - coordinate[0]) / 360);
        return map.project([lon, coordinate[1]]);
    }
    function viewport(map, padding = 0) {
        const centre = map.getCenter().lng;
        const wrap = lon => lon + 360 * Math.round((centre - lon) / 360);
        // An unrotated, level Mercator viewport is a geographic rectangle.
        // Read it once instead of projecting every flight and reading layout per point.
        if (map.getBounds && !map.getBearing() && !map.getPitch() && (!padding || map.unproject)) {
            const box = map.getBounds();
            let west = box.getWest(), east = box.getEast(), south = box.getSouth(), north = box.getNorth();
            if (padding) {
                const canvas=map.getContainer(), sw=map.unproject([-padding,canvas.clientHeight+padding]), ne=map.unproject([canvas.clientWidth+padding,-padding]);
                west=sw.lng; east=ne.lng; south=sw.lat; north=ne.lat;
            }
            return ([lon, lat]) => lat >= south && lat <= north && wrap(lon) >= west && wrap(lon) <= east;
        }
        const canvas = map.getContainer(), width = canvas.clientWidth, height = canvas.clientHeight;
        return ([lon, lat]) => {
            const p = map.project([wrap(lon), lat]);
            return p.x >= -padding && p.y >= -padding && p.x <= width+padding && p.y <= height+padding;
        };
    }
    function inside(map, coordinate) {
        return viewport(map)(coordinate);
    }
    function visibleCount(map, features, knownUnique = false) {
        const contains = viewport(map);
        if (knownUnique) {
            let count=0;
            for (const feature of features) if (contains(feature.geometry.coordinates)) count++;
            return count;
        }
        const identities = new Set();
        for (const feature of features) if (contains(feature.geometry.coordinates)) identities.add(feature.properties.id);
        return identities.size;
    }
    function nearest(map, features, point) {
        let match = null, distance = marker.pickingRadius ** 2;
        for (const feature of features) {
            const p = project(map, feature.geometry.coordinates), d = (p.x-point.x)**2 + (p.y-point.y)**2;
            if (d <= distance) { match = feature; distance = d; }
        }
        return match;
    }
    function nextDeparture(map, services, day, now) {
        let next = null;
        const contains = viewport(map), airports = new Map();
        for (const service of services) {
            const stop = service.stops[0], at = stop[2], airport = day.stations[stop[0]];
            if (at <= now || at > day.end || (next !== null && at >= next)) continue;
            if (!airports.has(stop[0])) airports.set(stop[0], contains([airport.lon, airport.lat]));
            if (airports.get(stop[0])) next = at;
        }
        return next;
    }
    function scopeLabel(day) {
        if (day.flight_geometry === 'great_circle_v1') return 'Combined captures';
        if (day.city === 'europe_flights') return 'Selected airline networks';
        if (['united_states_flights', 'south_america_flights', 'americas_flights'].includes(day.city)) return 'Selected airports';
        return day.flight_view_kind === 'hub' ? 'Airport connections' : 'Selected routes';
    }
    function priceLabel(service) {
        const p=service.price;
        if (!p || !Number.isSafeInteger(p.amount_minor) || p.amount_minor<=0 || !['MYR','USD','EUR'].includes(p.currency)) return 'Price unavailable';
        return new Intl.NumberFormat(root.suntrainI18n?.locale || 'en-MY', {style:'currency',currency:p.currency,currencyDisplay:'code'}).format(p.amount_minor/100);
    }
    function cheapestQuotes(service) {
        const cheapest = new Map();
        for (const quote of service.fare_quotes || (service.price ? [service.price] : [])) {
            if (!cheapest.has(quote.currency) || quote.amount_minor < cheapest.get(quote.currency).amount_minor)
                cheapest.set(quote.currency, quote);
        }
        return ['USD', 'EUR', 'MYR'].filter(currency => cheapest.has(currency)).map(currency => cheapest.get(currency));
    }
    function captureTime(at, timezone) {
        const text=new Intl.DateTimeFormat(root.suntrainI18n?.locale || 'en-AU', {
            timeZone:timezone,year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZoneName:'shortOffset'
        }).format(new Date(at));
        if (timezone==='Pacific/Auckland') return text.replace(/GMT\+(12|13)/, (_,offset)=>offset==='13'?'NZDT':'NZST');
        const label={'Asia/Kathmandu':'NPT','Asia/Taipei':'CST','Asia/Hong_Kong':'HKT','Asia/Brunei':'BNT','Asia/Phnom_Penh':'ICT','Asia/Vientiane':'ICT','Asia/Yangon':'MMT','Asia/Rangoon':'MMT','Asia/Dili':'TLT','Asia/Ho_Chi_Minh':'ICT','Asia/Manila':'PHT','Asia/Bangkok':'ICT','Asia/Kuala_Lumpur':'MYT','Asia/Singapore':'SGT','Asia/Kolkata':'IST','Asia/Seoul':'KST','Asia/Tokyo':'JST','Asia/Shanghai':'CST'}[timezone];
        return timezone==='UTC'?text.replace(/GMT(?:\+0)?/,'UTC'):label?text.replace(/GMT\+(?:13|[789]|[56][.:]30|5[.:]45)/,label):text;
    }
    let planeCanvas, airportCanvas;
    function planeImage(color = '#f57c28') {
        const canvas = planeCanvas || (planeCanvas=document.createElement('canvas'));
        if (canvas.width!==64 || canvas.height!==64) canvas.width = canvas.height = 64;
        const ctx = canvas.getContext('2d', {willReadFrequently: true});
        ctx.clearRect(0,0,64,64);
        const points = [[32,5],[36,10],[37,25],[57,39],[57,44],[37,37],[36,50],[43,55],
            [43,59],[32,55],[21,59],[21,55],[28,50],[27,37],[7,44],[7,39],[27,25],[28,10]];
        ctx.beginPath(); points.forEach(([x,y], i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.closePath();
        ctx.lineJoin = 'round'; ctx.strokeStyle = '#17212b'; ctx.lineWidth = 7; ctx.stroke();
        ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 4; ctx.stroke(); ctx.fillStyle = color; ctx.fill();
        return ctx.getImageData(0, 0, 64, 64);
    }
    function airportImage(code) {
        const canvas = airportCanvas || (airportCanvas=document.createElement('canvas'));
        if (canvas.width!==88 || canvas.height!==40) {canvas.width=88;canvas.height=40;}
        const ctx = canvas.getContext('2d', {willReadFrequently: true});
        ctx.clearRect(0,0,88,40);
        ctx.font = 'bold 22px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.lineJoin = 'round'; ctx.lineWidth = 6; ctx.strokeStyle = '#17212b'; ctx.strokeText(code, 44, 20);
        ctx.fillStyle = '#fff'; ctx.fillText(code, 44, 20);
        return ctx.getImageData(0, 0, 88, 40);
    }
    const api = {bearing, bounds, marker, movingLayers, planeKey, openingBounds, greatCircle, hydratePaths, paintInterval, project, viewport, inside,
        visibleCount, nearest, nextDeparture, scopeLabel, priceLabel, cheapestQuotes, captureTime, planeImage, airportImage};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    root.suntrainFlights = api;
})(typeof window !== 'undefined' ? window : globalThis);
