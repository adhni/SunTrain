const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../assets/train_replay.js');
const {stationCalls, formatCallTime} = require('../assets/02_station_departures.js');
const {summarize} = require('../assets/02_city_overview.js');
const {bearing} = require('../assets/02_flights.js');
const {priceLabel} = require('../assets/02_flights.js');

test('Thai flight boards and captured fares use ICT UTC+7 independently of WIB',()=>{
 const {captureTime}=require('../assets/02_flights.js');
 const at=Date.parse('2026-11-01T17:00:00Z')/1000;
 assert.match(formatCallTime(at,'Asia/Bangkok'),/2 Nov.*00:00 ICT/);
 assert.match(captureTime('2026-11-01T17:00:00Z','Asia/Bangkok'),/2 Nov.*00:00 ICT/);
 assert.match(formatCallTime(at,'Asia/Jakarta'),/2 Nov.*00:00 WIB/);
});

test('China airport and fare clocks use UTC+8 CST without changing American clocks',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-01T16:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Shanghai'),/00:00 CST/);
    assert.match(formatCallTime(at-60,'Asia/Shanghai'),/23:59 CST/);
    assert.match(captureTime('2026-11-01T16:00:00Z','Asia/Shanghai'),/2 Nov.*00:00 CST/);
    assert.match(formatCallTime(at,'America/Chicago'),/GMT-6/);
});

test('Japanese airport and fare capture clocks retain JST at midnight',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-01T15:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Tokyo'),/00:00 JST/);
    assert.match(formatCallTime(at-60,'Asia/Tokyo'),/23:59 JST/);
    assert.match(captureTime('2026-11-01T15:00:00Z','Asia/Tokyo'),/2 Nov.*00:00 JST/);
});

test('Korean airport and capture clocks own midnight in KST',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-01T15:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Seoul'),/00:00 KST/);
    assert.match(captureTime('2026-11-01T15:00:00Z','Asia/Seoul'),/2 Nov.*00:00 KST/);
    assert.match(formatCallTime(at-60,'Asia/Seoul'),/23:59 KST/);
});

test('Captured MYR and USD fares format minor units without inventing missing prices', () => {
    assert.match(priceLabel({price:{amount_minor:12050,currency:'MYR'}}), /MYR\s*120\.50/);
    assert.match(priceLabel({price:{amount_minor:13400,currency:'USD'}}),/USD\s*134\.00/);
    for (const price of [undefined, {}, {amount_minor:0,currency:'MYR'}, {amount_minor:134.5,currency:'MYR'}, {amount_minor:13400,currency:'ZZZ'}]) {
        assert.equal(priceLabel({price}), 'Price unavailable');
    }
    const at=Date.parse('2026-11-02T00:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Kuala_Lumpur'), /08:00 MYT/);
    assert.match(formatCallTime(at,'Asia/Kuching'), /08:00 MYT/);
});

test('Gulf airport clocks differ by one hour and capture times keep their zone',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-02T00:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Dubai'),/04:00 GMT\+4/);
    assert.match(formatCallTime(at,'Asia/Qatar'),/03:00 GMT\+3/);
    assert.match(captureTime('2026-11-02T00:00:00Z','Asia/Dubai'),/04:00 GMT\+4/);
    assert.match(captureTime('2026-11-02T00:00:00Z','Asia/Kuala_Lumpur'),/08:00 MYT/);
});
test('Singapore airport and capture clocks use SGT while foreign clocks stay local',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-02T00:00:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Singapore'),/08:00 SGT/);
    assert.match(captureTime('2026-11-02T00:00:00Z','Asia/Singapore'),/08:00 SGT/);
    assert.match(formatCallTime(at,'America/New_York'),/19:00 GMT-5/);
});
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

test('Indonesian airport clocks show WIB, WITA and WIT for the same instant', () => {
    const at = Date.parse('2026-11-02T00:00:00Z') / 1000;
    assert.match(formatCallTime(at, 'Asia/Jakarta'), /07:00 WIB/);
    assert.match(formatCallTime(at, 'Asia/Pontianak'), /07:00 WIB/);
    assert.match(formatCallTime(at, 'Asia/Makassar'), /08:00 WITA/);
    assert.match(formatCallTime(at, 'Asia/Jayapura'), /09:00 WIT/);
});

test('eastern Indonesia next-day departures stay in the Jakarta day without duplicated board events', () => {
    const start = Date.parse('2026-11-01T17:00:00Z') / 1000, end = start + 86400;
    const s = {...service, id:'east', stops:[[0,end-1800,end-1800],[1,end+3600,end+3600]]};
    assert.equal(stationCalls([s],0,start,end).length,1);
    assert.equal(stationCalls([s],0,end,end+86400).length,0);
    assert.equal(stationCalls([s],1,start,end,'arrival').length,0);
    assert.equal(stationCalls([s],1,end,end+86400,'arrival').length,1);
    assert.match(formatCallTime(end-1800, 'Asia/Jayapura'), /01:30 WIT/);
});

test('flight scopes filter map, airport boards and overview while preserving transit filters', () => {
    const filters={modes:[],operators:[],lines:[],directions:[],stations:[],number:'',flightScope:'international'};
    const today={...service,stops:[[0,start,start],[1,start+7200,start+7200]]};
    const domestic={...today,id:'domestic',flight_scope:'domestic'};
    const international={...today,id:'international',flight_scope:'international'};
    const mixed={...day,services:[domestic,international]};
    assert.equal(core.matches(domestic,filters,mixed),false);
    assert.equal(core.matches(international,filters,mixed),true);
    assert.equal(core.matches({...today,mode:'train'},filters,mixed),true);
    assert.equal(core.matches(today,{...filters,flightScope:'domestic'},mixed),true,'legacy flights default to domestic');
    const selected=mixed.services.filter(s=>core.matches(s,filters,mixed));
    assert.equal(stationCalls(selected,0,start,day.end).length,1);
    assert.equal(summarize(mixed,filters,core).departures,1);
    assert.equal(summarize(mixed,{...filters,flightScope:'both'},core).departures,2);
    assert.equal(core.matches(international,{...filters,operators:['Other airline']},mixed),false);
});

test('foreign airport clocks keep local dates and daylight-saving offsets', () => {
    const at=Date.parse('2026-11-01T17:00:00Z')/1000;
    assert.match(formatCallTime(at,'Australia/Adelaide'),/2 Nov.*03:30 GMT\+10:30/);
    assert.match(formatCallTime(at,'Europe/Amsterdam'),/1 Nov.*18:00 GMT\+1/);
    assert.match(formatCallTime(at,'Pacific/Auckland'),/2 Nov.*06:00 GMT\+13/);
});

test('Pacific airport bounds choose the short longitude span in either direction',()=>{
 const {bounds}=require('../assets/02_flights.js');
 const airports=[{lon:151.177,lat:-33.95},{lon:-118.408,lat:33.94}];
 const box=bounds(airports);
 assert.ok(box[1][0]-box[0][0]<100);
 assert.deepEqual(bounds([...airports].reverse()),box);
 assert.ok(Math.abs(box[0][0]-151.177)<1e-9);
 assert.ok(Math.abs(box[1][0]-241.592)<1e-9);
 const europe=bounds([{lon:4.7,lat:52.3},{lon:115.2,lat:-8.7}]);
 assert.ok(Math.abs(europe[0][0]-4.7)<1e-9 && Math.abs(europe[1][0]-115.2)<1e-9);
 assert.equal(europe[0][1],-8.7);assert.equal(europe[1][1],52.3);
 assert.equal(bounds([]),null);
});

test('Indian airport and fare capture times retain the half-hour IST offset',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    const at=Date.parse('2026-11-01T18:30:00Z')/1000;
    assert.match(formatCallTime(at,'Asia/Kolkata'),/2 Nov.*00:00 IST/);
    assert.match(captureTime('2026-11-01T18:30:00Z','Asia/Kolkata'),/2 Nov.*00:00 IST/);
    assert.match(formatCallTime(at,'America/New_York'),/1 Nov.*13:30 GMT-5/);
});

test('Indonesian locale uses IST despite formatting half-hour offsets with a dot',()=>{
    const {captureTime}=require('../assets/02_flights.js');
    globalThis.suntrainI18n={locale:'id-ID'};
    try {
        assert.match(formatCallTime(Date.parse('2026-11-01T18:30:00Z')/1000,'Asia/Kolkata'),/IST/);
        assert.match(captureTime('2026-11-01T18:30:00Z','Asia/Kolkata'),/IST/);
    } finally { delete globalThis.suntrainI18n; }
});

test('original USD and MYR amounts are labelled independently without implicit conversion',()=>{
    const {priceLabel}=require('../assets/02_flights.js');
    assert.match(priceLabel({price:{currency:'USD',amount_minor:10000}}),/USD.*100\.00/);
    assert.match(priceLabel({price:{currency:'MYR',amount_minor:10000}}),/MYR.*100\.00/);
    assert.equal(priceLabel({price:{currency:'CNY',amount_minor:10000}}),'Price unavailable');
    assert.equal(priceLabel({}),'Price unavailable');
});
