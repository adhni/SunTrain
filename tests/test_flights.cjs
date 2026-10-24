const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../assets/train_replay.js');
const {stationCalls, formatCallTime} = require('../assets/02_station_departures.js');
const {summarize} = require('../assets/02_city_overview.js');
const {bearing} = require('../assets/02_flights.js');
const stations = [{name:'Perth (PER)',lon:116,lat:-32,timezone:'Australia/Perth'},
    {name:'Melbourne (MEL)',lon:145,lat:-38,timezone:'Australia/Melbourne'}];
const start = Date.parse('2013-03-03T13:00:00Z') / 1000;
const service = {id:'flight',number:'JQ1',mode:'flight',line:'PER → MEL',operator:'Jetstar',legs:['arc'],
    stops:[[0,start-3600,start-3600],[1,start+7200,start+7200]]};
const day = {city:'australia_flights',day_start_hour:0,timezone:'Australia/Melbourne',start,end:start+86400,
    stations,services:[service],paths:{arc:{quality:'illustrative',coordinates:[[116,-32],[130,-37],[145,-38]],distances:[0,1500,3000]}}};

test('airport departures exclude terminal calls; arrivals include actual scheduled endpoints and overnight flights', () => {
    assert.equal(stationCalls([service],0,day.start,day.end).length,0);
    assert.equal(stationCalls([service],1,day.start,day.end).length,0);
    const calls=stationCalls([service],1,day.start,day.end,'arrival');
    assert.equal(calls.length,1);
    assert.equal(calls[0].at,start+7200);
    assert.equal(calls[0].index,1);
    assert.equal(calls[0].event,'arrival');
    assert.equal(stationCalls([service],0,0,day.end,'arrival').length,0);
    assert.equal(stationCalls([service],1,day.start,start+7200,'arrival').length,0,'flight boards use a half-open date window');
});
test('illustrative paths animate planes and remain selectable without making unresolved rail animate', () => {
    assert.equal(core.servicePosition(service,start,day).state,'Scheduled flight in progress');
    assert.notEqual(core.servicePosition(service,start,day).lon,null);
    assert.equal(core.routeFeatures(day.paths,['arc']).length,1);
    assert.equal(core.pointAlong({...day.paths.arc,quality:'unresolved'},0.5),null);
    assert.equal(core.servicePosition(service,start+7201,day),null);
    assert.deepEqual(core.servicePosition(service,start,day),core.servicePosition(service,start,day));
    assert.ok(Math.abs(bearing([0,0],[1,0])-90)<0.001);
    assert.ok(Math.abs(bearing([0,0],[0,1]))<0.001);
});
test('flight overview owns departures by Melbourne midnight and excludes carry-ins from totals', () => {
    const result=summarize({...day,services:[service,{...service,id:'today',stops:[[0,start,start],[1,start+7200,start+7200]]}]},
        {modes:[],operators:[],lines:[],directions:[],stations:[],number:''},core);
    assert.equal(result.departures,1);
    assert.equal(result.hours[0].hour,0);
    assert.equal(result.hours[0].departures,1);
    assert.equal(result.routes[0].mode,'Flight');
    assert.notEqual(formatCallTime(start,stations[0].timezone),formatCallTime(start,stations[1].timezone));
});
