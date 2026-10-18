const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../assets/train_replay.js');
const {summarize} = require('../assets/02_city_overview.js');
const start = Date.parse('2024-06-24T03:00:00Z') / 1000;
const filters = {modes: [], operators: [], lines: [], directions: [], stations: [], number: ''};
const stations = [{name: 'Alpha', lon: 1, lat: 2}, {name: 'Bravo', lon: 2, lat: 3}, {name: 'Alpha', lon: 1, lat: 2}];
function service(departure, extra = {}) {
    return {mode: 'train', operator: 'Metro', line: 'Red', route_id: 'R', direction: 'U', number: 'one',
        stops: [[0, departure - 10, departure], [1, departure + 60, departure + 70], [2, departure + 120, departure + 120]], ...extra};
}
function day(services, extra = {}) {
    return {city: 'melbourne', city_name: 'Melbourne', timezone: 'UTC', start, end: start + 86400, stations, services, ...extra};
}

test('counts departure ownership in the half-open business window, not overlapping journeys', () => {
    const result = summarize(day([service(start - 1), service(start), service(start + 86399), service(start + 86400)]), filters, core);
    assert.equal(result.departures, 2);
    assert.equal(result.routes.length, 1);
    assert.equal(result.stops, 2, 'repeated calls and identical mapped stops are not counted twice');
    assert.equal(result.hours.reduce((total, hour) => total + hour.departures, 0), 2);
    assert.deepEqual(result.hours.map(h => h.hour), [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2]);
});

test('groups route branches but keeps operators and modes separate', () => {
    const result = summarize(day([service(start), service(start + 10, {line: 'Red branch'}),
        service(start + 20, {operator: 'Other'}), service(start + 30, {mode: 'bus', color: '#123456'})], {city: 'perth'}), filters, core);
    assert.equal(result.routes.length, 3);
    assert.equal(result.routes[0].departures, 2);
    assert.equal(result.routes.find(r => r.mode === 'Bus').color, '#123456');
});

test('every shared filter applies, including calling-at whole-journey matching', () => {
    const input = day([service(start), service(start + 10, {operator: 'Other', number: 'two', direction: 'D'})]);
    const selected = {...filters, modes: ['train'], operators: ['Metro'], lines: ['Red'], directions: ['U'], stations: ['Bravo'], number: 'ONE'};
    assert.equal(summarize(input, selected, core).departures, 1);
    assert.equal(summarize(input, {...selected, stations: ['Missing']}, core).departures, 0);
    const empty = summarize(input, {...selected, modes: ['bus']}, core);
    assert.equal(empty.stops, 0);
    assert.deepEqual(empty.routes, []);
});

test('compact schedules stay shared and stop lists are scanned once per topology', () => {
    let scans = 0;
    const ids = new Proxy(Object.freeze([0, 1, 2]), {get(target, key) {
        if (key === Symbol.iterator) { scans++; return target[Symbol.iterator].bind(target); }
        return Reflect.get(target, key);
    }});
    const times = Object.freeze([0, 10, 60, 70, 120, 120]);
    const services = Array.from({length: 10000}, (_, i) => ({...service(0), stops: undefined, stopIds: ids, times, timeOffset: start + i}));
    const result = summarize(day(services), filters, core);
    assert.equal(result.departures, 10000);
    assert.equal(scans, 1);
    assert.ok(services.every(s => !s.stops && s.stopIds === ids && s.times === times));
    assert.deepEqual(times, [0, 10, 60, 70, 120, 120]);
});

test('uses city local time including half-hour offsets', () => {
    const departure = Date.parse('2024-06-24T00:45:00Z') / 1000;
    const input = day([service(departure)], {timezone: 'Australia/Adelaide', start: departure - 3600, end: departure + 3600});
    assert.equal(summarize(input, filters, core).hours.find(h => h.hour === 10).departures, 1);
});

test('combines repeated local hours without losing departures on a 25-hour day', () => {
    const first = Date.parse('2025-11-02T05:30:00Z') / 1000;
    const second = Date.parse('2025-11-02T06:30:00Z') / 1000;
    const input = day([service(first), service(second)], {timezone: 'America/New_York',
        start: Date.parse('2025-11-01T07:00:00Z') / 1000, end: Date.parse('2025-11-02T08:00:00Z') / 1000});
    const result = summarize(input, filters, core);
    assert.equal(result.departures, 2);
    assert.equal(result.hours.find(h => h.hour === 1).departures, 2);
});

test('Melbourne lines without GTFS route IDs still get their own summary rows', () => {
    const input = day([service(start, {route_id: undefined}), service(start + 10, {route_id: undefined, line: 'Yellow'})]);
    const original = JSON.stringify(input);
    assert.equal(summarize(input, filters, core).routes.length, 2);
    assert.equal(JSON.stringify(input), original);
});
