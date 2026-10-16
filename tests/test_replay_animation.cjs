const test = require('node:test');
const assert = require('node:assert/strict');
const {pointAlong, servicePosition, matches, lineColor} = require('../assets/train_replay.js');

const path = {coordinates: [[0, 0], [2, 0], [2, 1]], distances: [0, 2, 3], quality: 'track'};
const day = {stations: [{name: 'Alpha', lon: 0, lat: 0}, {name: 'Bravo', lon: 2, lat: 1}], paths: {curve: path}};
const service = {id: 'one', operator: 'Metro', line: 'Werribee', direction: 'U', number: 'X100',
    stops: [[0, 0, 10, 5, 50], [1, 20, 30, 50, 0]], legs: ['curve']};

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
