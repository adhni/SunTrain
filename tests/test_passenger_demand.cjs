const test = require('node:test');
const assert = require('node:assert/strict');
const {buildIndex, snapshot, scale} = require('../assets/02_passenger_demand.js');
const day = {stations:[{name:'Alpha',lon:144,lat:-37},{name:'Bravo',lon:145,lat:-38}]};
const service = stops => ({stops:stops.map(([id,time,count])=>[id,time-10,time,999,999,count,0])});
const services = [service([[0,0,10],[1,60,20]]),service([[0,30,100],[1,90,200]])];

test('station boardings use scheduled departures and combine services once',()=>{
    const result=snapshot(buildIndex(services,day),60,60);
    assert.equal(result.total,120); // Excludes departure at 0, includes departure at 60.
    assert.equal(result.stationCount,2);
    assert.equal(result.rows[0].boardings,100);
    assert.equal(result.rows[1].boardings,20);
    assert.equal(result.knownCalls,2);
});
test('rolling windows are right-closed and cannot include future departures',()=>{
    const index=buildIndex(services,day);
    assert.equal(snapshot(index,29,30).total,10);
    assert.equal(snapshot(index,30,30).total,100);
    assert.equal(snapshot(index,89,30).total,20);
    assert.equal(snapshot(index,90,30).total,200);
    assert.equal(snapshot(index,-1,3600).total,0);
});
test('backward seeks recompute counts without accumulating previous frames',()=>{
    const index=buildIndex(services,day);
    const initial=snapshot(index,60,60);
    snapshot(index,90,60);
    assert.deepEqual(snapshot(index,60,60),initial);
});
test('zero boarding counts remain known while missing and invalid counts stay unavailable',()=>{
    const index=buildIndex([service([[0,10,null],[0,20,0],[1,30,-10],[1,40,NaN]])],day);
    const result=snapshot(index,40,60);
    assert.equal(result.total,0);
    assert.equal(result.knownCalls,1);
    assert.equal(result.missingCalls,3);
    assert.equal(result.features.length,0);
});
test('service filters are honored and source data stays unchanged',()=>{
    const before=JSON.stringify(services);
    assert.equal(snapshot(buildIndex([services[0]],day),60,120).total,30);
    assert.equal(snapshot(buildIndex([],day),60,120).total,0);
    assert.equal(JSON.stringify(services),before);
});
test('boarding windows cross midnight in elapsed seconds',()=>{
    const midnight=Date.parse('2023-07-10T14:00:00Z')/1000;
    const index=buildIndex([service([[0,midnight-60,30],[0,midnight+60,40]])],day);
    assert.equal(snapshot(index,midnight+60,120).total,40);
    assert.equal(snapshot(index,midnight+60,180).total,70);
});
test('longer windows keep raw counts on the same passenger color scale',()=>{
    const index=buildIndex(services,day);
    assert.equal(snapshot(index,90,30).total,200);
    assert.equal(snapshot(index,90,60).total,220);
    assert.equal(snapshot(index,90,120).total,330);
    assert.deepEqual(scale.map(([count])=>count),[0,100,500,2000,5000]);
});

test('repeated daylight-saving clock hours use elapsed time rather than clock labels',()=>{
    const first=Date.parse('2024-04-07T02:45:00+11:00')/1000;
    const repeated=Date.parse('2024-04-07T02:45:00+10:00')/1000;
    const index=buildIndex([service([[0,first,30],[0,repeated,40]])],day);
    assert.equal(snapshot(index,repeated,3600).total,40);
    assert.equal(snapshot(index,repeated,5400).total,70);
});
test('station demand remains available when a train has no resolved railway path',()=>{
    const noGeometry={...services[0],legs:['unresolved']};
    assert.equal(snapshot(buildIndex([noGeometry],day),60,120).total,30);
});
