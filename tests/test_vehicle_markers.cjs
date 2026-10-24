const test = require('node:test');
const assert = require('node:assert/strict');
const {bodyKind, radius, footprint} = require('../assets/02_vehicle_markers.js');
const {pointAlong, servicePosition} = require('../assets/train_replay.js');
const {formatBoardTime} = require('../assets/02_station_departures.js');

test('illustrative bodies apply to Melbourne trains and trams only', () => {
    assert.equal(bodyKind('melbourne'), 'train');
    assert.equal(bodyKind('melbourne', 'tram'), 'tram');
    for (const mode of ['bus', 'ferry', 'unknown']) assert.equal(bodyKind('melbourne', mode), '');
    assert.equal(bodyKind('tokyo', 'train'), '');
});

const service = {mode: 'train', stops: [[0, 0, 0], [1, 100, 110], [2, 200, 210]], legs: ['bend', 'next']};
const day = {stations: [{lon: 0, lat: 0}, {lon: .001, lat: .001}, {lon: .002, lat: .001}], paths: {
    bend: {quality: 'track', coordinates: [[0, 0], [.001, 0], [.001, .001]], distances: [0, 100, 200]},
    next: {quality: 'shape', coordinates: [[.001, .001], [.002, .001]], distances: [0, 100]}
}};
function dots(at, value = service, data = day, spacing = 25) {
    return footprint(value, servicePosition(value, at, data), data, at, spacing, pointAlong);
}
function near(actual, expected) {
    assert.equal(actual.length, expected.length);
    actual.forEach((p, i) => p.forEach((n, j) => assert.ok(Math.abs(n - expected[i][j]) < 1e-9, `${actual} vs ${expected}`)));
}

test('one spatial footprint bends along the route instead of rotating a straight body', () => {
    near(dots(75), [[.001, .0005], [.001, .00025], [.001, 0], [.00075, 0]]);
    const before = dots(49), after = dots(51);
    for (let i = 0; i < 4; i++) {
        assert.ok(Math.hypot(after[i][0]-before[i][0], after[i][1]-before[i][1]) <= .000041);
    }
    assert.deepEqual(dots(75), dots(75)); // Seeking back is independent of animation history.
    assert.equal(dots(75, {...service, mode: 'tram'}).length, 2);
    assert.equal(dots(75, {...service, mode: 'bus'}).length, 1);
});

test('the entire vehicle stays together through a dwell and across successive route legs', () => {
    near(dots(100), dots(105));
    near(dots(105), dots(110));
    const continued = dots(120);
    near(continued, [[.001 + 10/90 * .001, .001], [.001, .0008611111111111111], [.001, .0006111111111111111], [.001, .0003611111111111111]]);
    const compact = {mode: 'train', stopIds: [0, 1, 2], times: [0, 0, 100, 110, 200, 210], legs: service.legs, timeOffset: 1000};
    near(dots(1075, compact), dots(75));
});

test('vehicle bodies never bridge missing geometry, disconnected legs or the start of a route', () => {
    assert.equal(dots(0).length, 1);
    const broken = {...day, paths: {...day.paths, bend: {...day.paths.bend, quality: 'unresolved'}}};
    assert.equal(dots(120, service, broken).length, 1);
    const disconnected = {...day, paths: {...day.paths, bend: {...day.paths.bend, coordinates: [[1, 1], [2, 1]]}}};
    assert.equal(dots(120, service, disconnected).length, 1);
    assert.equal(footprint(service, {lon: 0, lat: 0, index: 0, approximate: true}, day, 75, 25, pointAlong).length, 1);
});

test('one radius rule controls every dot and its spacing at all zoom and passenger sizes', () => {
    assert.equal(radius(5), 1.8);
    assert.equal(radius(9), 3.1);
    assert.equal(radius(12), 4);
    assert.equal(radius(15), 5);
    assert.equal(radius(20), 5);
    assert.equal(radius(1), 1.8);
    assert.equal(radius(10.5), 3.55);
    assert.equal(radius(12, .8), 3.2);
});

test('expanded departure times make overnight dates explicit and use Melbourne local time', () => {
    const at = value => Date.parse(value) / 1000;
    const now = at('2024-05-27T13:50:00Z'); // 23:50 Melbourne
    assert.equal(formatBoardTime(now, now, 'Australia/Melbourne'), '23:50');
    assert.equal(formatBoardTime(at('2024-05-27T14:05:00Z'), now, 'Australia/Melbourne'), '00:05 · 28 May');
});
