const test = require('node:test');
const assert = require('node:assert/strict');
const {pointAlong, servicePosition, matches, lineColor} = require('../assets/train_replay.js');

const path = {coordinates: [[0, 0], [2, 0], [2, 1]], distances: [0, 2, 3], quality: 'track'};
const day = {stations: [{name: 'Alpha', lon: 0, lat: 0}, {name: 'Bravo', lon: 2, lat: 1}], paths: {curve: path}};
const service = {id: 'one', operator: 'Metro', line: 'Werribee', direction: 'U', number: 'X100',
    stops: [[0, 0, 10, 5, 50], [1, 20, 30, 50, 0]], legs: ['curve']};

test('active-service index agrees with full scans at boundaries, large jumps and backwards seeks', () => {
    const {ActiveServices} = require('../assets/train_replay.js');
    const services = Array.from({length: 10000}, (_, i) => ({...service, id: String(i), timeOffset: i * 10}));
    const index = new ActiveServices(services);
    for (const now of [-1, 0, 10, 30, 30.001, 30000, 99999, 100030, 20, 15, 0]) {
        const expected = services.filter(s => servicePosition(s, now, day));
        assert.deepEqual([...index.at(now)].map(s => s.id).sort(), expected.map(s => s.id).sort());
    }
    assert.equal(index.at(0, true).size, 1);
});

test('packed buses share flat times and stop sequences without expanding schedules', () => {
    const {hydrate} = require('../assets/train_replay.js');
    const flat = [0, 10, 20, 30];
    const ids = [0, 1];
    const packed = {...day, transit_stop_patterns: {sequence: {stations: ids, legs: ['curve']}},
        transit_patterns: {timing: {stop_pattern: 'sequence', times: flat, operator: 'London bus', line: 'Bus 1'}},
        services: Array.from({length: 10000}, (_, i) => ({mode: 'bus', pattern: 'timing', departure: 1000 + 60 * i, number: String(i)}))};
    hydrate(packed);
    assert.ok(packed.services.every(s => !s.stops && s.stopIds === ids && s.times === flat));
    const first = packed.services[0];
    assert.equal(servicePosition(first, 1005, packed).state, 'At stop');
    assert.equal(servicePosition(first, 1015, packed).lon, 1.5);
    assert.equal(servicePosition(first, 1020, packed).station, 'Bravo');
    assert.equal(servicePosition(first, 1031, packed), null);
    assert.equal(servicePosition(first, 1015, {...packed, paths: {curve: {...path, quality: 'approximate'}}}).lon, null);
    const filters = {modes: ['bus'], operators: [], lines: [], directions: [], stations: ['Bravo'], number: ''};
    assert.equal(matches(first, filters, packed), true);
    assert.equal(matches(first, {...filters, stations: ['Missing']}, packed), false);
    servicePosition(packed.services[1], 1075, packed);
    assert.deepEqual(flat, [0, 10, 20, 30]);
});

test('curve interpolation uses distance, with exact endpoints', () => {
    assert.deepEqual(pointAlong(path, 0), [0, 0]);
    assert.deepEqual(pointAlong(path, 1), [2, 1]);
    assert.deepEqual(pointAlong(path, 0.5), [1.5, 0]);
    assert.deepEqual(pointAlong(path, 5 / 6), [2, 0.5]);
});
test('station dwell, departure and arrival select the recorded load', () => {
    assert.deepEqual(servicePosition(service, 5, day), {lon: 0, lat: 0, load: 5, index: 0, state: 'At station', station: 'Alpha', next: 'Bravo', approximate: false});
    assert.equal(servicePosition(service, 10, day).load, 50);
    assert.equal(servicePosition(service, 15, day).lon, 1.5);
    assert.equal(servicePosition(service, 20, day).station, 'Bravo');
    assert.equal(servicePosition(service, 30, day).load, 0);
});
test('services appear and disappear at their recorded bounds', () => {
    assert.equal(servicePosition(service, -1, day), null);
    assert.equal(servicePosition(service, 31, day), null);
    assert.ok(servicePosition(service, 0, day));
    assert.ok(servicePosition(service, 30, day));
});
test('approximate legs are distinguishable from matched tracks', () => {
    const approximateDay = {...day, paths: {curve: {...path, quality: 'approximate'}}};
    assert.equal(servicePosition(service, 15, approximateDay).approximate, true);
});
test('station filtering keeps whole services and combines with other filters', () => {
    const filters = {operators: [], lines: [], directions: [], stations: ['Bravo'], number: 'x1'};
    assert.equal(matches(service, filters, day), true);
    assert.equal(service.stops.length, 2);
    assert.equal(matches(service, {...filters, operators: ['VLine']}, day), false);
    assert.equal(matches(service, {...filters, lines: ['Sunbury']}, day), false);
    assert.equal(matches(service, {...filters, directions: ['D']}, day), false);
    assert.equal(matches(service, {...filters, stations: ['Other']}, day), false);
});
test('line colors remain stable across days and filter selections', () => {
    assert.equal(lineColor('Werribee'), lineColor('Werribee'));
    assert.notEqual(lineColor('Werribee'), lineColor('Sunbury'));
});

test('unresolved legs hide positions between stations and reappear at arrival', () => {
    const missingDay = {...day, paths: {curve: {coordinates: [], distances: [], quality: 'approximate'}}};
    const missing = servicePosition(service, 15, missingDay);
    assert.equal(missing.lon, null);
    assert.equal(missing.lat, null);
    assert.equal(missing.state, 'Position unavailable');
    assert.equal(missing.load, 50);
    assert.equal(missing.next, 'Bravo');
    assert.equal(servicePosition(service, 20, missingDay).lon, 2);
    assert.equal(servicePosition(service, 20, missingDay).approximate, false);
});
test('old straight fallback paths cannot animate or enter selected-route highlights', () => {
    const {routeFeatures} = require('../assets/train_replay.js');
    const paths = {curve: path, shortcut: {...path, quality: 'approximate'}};
    assert.equal(pointAlong(paths.shortcut, 0.5), null);
    const features = routeFeatures(paths, ['shortcut', 'curve', 'curve']);
    assert.equal(features.length, 1);
    assert.deepEqual(features[0].geometry.coordinates, path.coordinates);
    assert.equal(features[0].properties.quality, 'track');
});

test('tram/bus trips retain shared relative stops and follow their shape at absolute times', () => {
    const {hydrate, stopTime, routeFeatures, vehicleColor} = require('../assets/train_replay.js');
    const transitDay = {...day, paths: {curve: {...path, quality: 'shape'}},
        transit_patterns: {p: {stops: [[0, 0, 10], [1, 20, 30]], legs: ['curve']}},
        services: [{id: 'bus', mode: 'bus', operator: 'PTV bus', line: 'Bus 1', direction: 'A', number: 'one', pattern: 'p', departure: 100}]};
    const bus = hydrate(transitDay).services[0];
    assert.strictEqual(bus.stops,transitDay.transit_patterns.p.stops);
    assert.deepEqual(bus.stops[0], [0,0,10]);
    assert.equal(stopTime(bus,bus.stops[0],1),100);
    hydrate(transitDay);
    assert.equal(stopTime(bus,bus.stops[0],1),100);
    assert.equal(servicePosition(bus,115,transitDay).lon,1.5);
    assert.equal(servicePosition(bus,115,transitDay).load,null);
    assert.equal(routeFeatures(transitDay.paths,bus.legs).length,1);
    const filters = {modes:['tram'],operators:[],lines:[],directions:[],stations:[],number:''};
    assert.equal(matches(bus,filters,transitDay),false);
    assert.equal(matches(bus,{...filters,modes:['bus']},transitDay),true);
    assert.notEqual(vehicleColor(bus),vehicleColor({...bus,mode:'tram'}));
});

test('thousands of trips never copy a shared schedule or change one another’s timing', () => {
    const {hydrate,stopTime}=require('../assets/train_replay.js');
    const stops=Object.freeze([Object.freeze([0,0,10]),Object.freeze([1,20,30])]);
    const relativeDay={...day,transit_patterns:{p:{stops,legs:['curve']}},services:
        Array.from({length:25000},(_,i)=>({id:String(i),mode:'bus',pattern:'p',departure:100+i*60}))};
    hydrate(relativeDay);
    assert.equal(new Set(relativeDay.services.map(s=>s.stops)).size,1);
    assert.strictEqual(relativeDay.services[24999].stops,stops);
    const first=relativeDay.services[0],later=relativeDay.services[1];
    assert.equal(servicePosition(first,115,relativeDay).lon,1.5);
    assert.equal(servicePosition(later,115,relativeDay),null);
    assert.equal(servicePosition(later,175,relativeDay).lon,1.5);
    assert.equal(stopTime(later,stops[1],2),190);
    assert.equal(servicePosition(first,131,relativeDay),null);
    assert.equal(servicePosition(first,105,relativeDay).state,'At stop');
    assert.equal(servicePosition(first,120,relativeDay).station,'Bravo');
    assert.equal(servicePosition(first,105,relativeDay).load,null);
    hydrate(relativeDay);
    assert.equal(stopTime(later,stops[1],2),190);
});

test('shared schedules preserve overnight times and complete-journey stop filters', () => {
    const {hydrate,stopTime}=require('../assets/train_replay.js');
    const midnight=Date.parse('2024-06-24T00:00:00+10:00')/1000;
    const overnight={...day,transit_patterns:{p:{stops:[[0,0,0],[1,1200,1200]],legs:['curve']}},
        services:[{id:'late',mode:'tram',operator:'PTV tram',line:'Tram 1',direction:'A',number:'late',pattern:'p',departure:midnight+25*3600}]};
    const trip=hydrate(overnight).services[0];
    assert.equal(new Date(stopTime(trip,trip.stops[1],1)*1000).toISOString(),'2024-06-24T15:20:00.000Z');
    assert.equal(servicePosition(trip,trip.departure+600,overnight).lon,1.5);
    assert.equal(matches(trip,{operators:[],lines:[],directions:[],stations:['Bravo'],number:''},overnight),true);
    assert.equal(trip.stops.length,2);
});

test('Boston rail shares schedules, retains MBTA route colors and has no passenger loads', () => {
    const {hydrate, vehicleColor} = require('../assets/train_replay.js');
    const boston = {...day, transit_patterns: {p: {operator:'MBTA', line:'Blue Line', color:'#003DA5', route_id:'Blue',
        direction:'North', origin:'Alpha', destination:'Bravo', stops:[[0,0,10],[1,20,30]], legs:['curve']}},
        services:[{id:'boston', mode:'subway', pattern:'p', departure:100, number:'trip'}]};
    const subway = hydrate(boston).services[0];
    assert.equal(vehicleColor(subway),'#003DA5');
    assert.equal(subway.route_id,'Blue');
    assert.equal(subway.direction,'North');
    assert.equal(servicePosition(subway,115,boston).lon,1.5);
    assert.equal(servicePosition(subway,115,boston).load,null);
    assert.strictEqual(subway.stops,boston.transit_patterns.p.stops);
    assert.equal(matches(subway,{modes:['commuter_rail'],operators:[],lines:[],directions:[],stations:[],number:''},boston),false);
    assert.equal(matches(subway,{modes:['subway'],operators:['MBTA'],lines:['Blue Line'],directions:['North'],stations:[],number:''},boston),true);
});

test('Silver Line stays silver, retains its route identities and filters separately from rail', () => {
    const {hydrate,vehicleColor}=require('../assets/train_replay.js');
    const silver={...day,transit_patterns:{p:{operator:'MBTA',line:'SL1 · Airport - South Station',route_id:'741',
        color:'#7C878E',direction:'Inbound',stops:[[0,0,10],[1,20,30]],legs:['curve']}},
        services:[{id:'silver',mode:'silver_line',pattern:'p',departure:100,number:'trip'}]};
    const bus=hydrate(silver).services[0];
    assert.equal(vehicleColor(bus),'#7C878E');
    assert.equal(vehicleColor({...bus,color:undefined}),'#7C878E');
    assert.equal(vehicleColor({...bus,mode:'bus'}),'#FF8200');
    assert.equal(vehicleColor({...bus,mode:'bus'},'london'),'#DC241F');
    assert.equal(bus.route_id,'741');
    assert.strictEqual(bus.stops,silver.transit_patterns.p.stops);
    assert.equal(servicePosition(bus,115,silver).lon,1.5);
    assert.equal(servicePosition(bus,115,silver).load,null);
    const filters={modes:['silver_line'],operators:['MBTA'],lines:[bus.line],directions:['Inbound'],stations:[],number:''};
    assert.equal(matches(bus,filters,silver),true);
    assert.equal(matches(bus,{...filters,modes:['subway']},silver),false);
});
