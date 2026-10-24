const test = require('node:test');
const assert = require('node:assert/strict');
const {bodyKind, heading} = require('../assets/02_vehicle_markers.js');
const {pointAlong} = require('../assets/train_replay.js');
const {formatBoardTime} = require('../assets/02_station_departures.js');

test('illustrative bodies apply to Melbourne trains and trams only', () => {
    assert.equal(bodyKind('melbourne'), 'train');
    assert.equal(bodyKind('melbourne', 'tram'), 'tram');
    for (const mode of ['bus', 'ferry', 'unknown']) assert.equal(bodyKind('melbourne', mode), '');
    assert.equal(bodyKind('tokyo', 'train'), '');
});

test('vehicle orientation follows the route through movement and station dwell', () => {
    const service = {stops: [[0, 100, 110], [1, 200, 210], [2, 300, 310]], legs: ['east', 'north']};
    const day = {paths: {
        east: {quality: 'track', coordinates: [[144, -38], [145, -38]], distances: [0, 1000]},
        north: {quality: 'shape', coordinates: [[145, -38], [145, -37]], distances: [0, 1000]}
    }};
    assert.equal(heading(service, {index: 0}, day, 150, pointAlong), 90);
    assert.equal(heading(service, {index: 0}, day, 105, pointAlong), 90);
    assert.equal(heading(service, {index: 1}, day, 205, pointAlong), 0);
    assert.equal(heading(service, {index: 2}, day, 305, pointAlong), 0);
    const compact = {stopIds: [0, 1, 2], times: [100, 110, 200, 210, 300, 310], legs: service.legs, timeOffset: 1000};
    assert.equal(heading(compact, {index: 0}, day, 1150, pointAlong), 90);
    assert.equal(heading(service, {index: 0, approximate: true}, day, 150, pointAlong), null);
    assert.equal(heading({...service, legs: ['missing']}, {index: 0}, day, 150, pointAlong), null);
});

test('expanded departure times make overnight dates explicit and use Melbourne local time', () => {
    const at = value => Date.parse(value) / 1000;
    const now = at('2024-05-27T13:50:00Z'); // 23:50 Melbourne
    assert.equal(formatBoardTime(now, now, 'Australia/Melbourne'), '23:50');
    assert.equal(formatBoardTime(at('2024-05-27T14:05:00Z'), now, 'Australia/Melbourne'), '00:05 · 28 May');
});
