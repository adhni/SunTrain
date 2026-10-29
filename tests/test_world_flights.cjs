const test=require('node:test');
const assert=require('node:assert/strict');
const flights=require('../assets/02_flights.js');
const core=require('../assets/train_replay.js');
const boards=require('../assets/02_station_departures.js');
const fixtures=require('./fixtures/world-flight-arcs.json');

test('lazy global arcs agree with the existing Python algorithm, including date-line ties',()=>{
 for(const expected of fixtures){
  const actual=flights.greatCircle(expected.a,expected.b);
  assert.equal(actual.coordinates.length,65);
  for(let i=0;i<65;i++){
   for(let axis=0;axis<2;axis++)assert.ok(Math.abs(actual.coordinates[i][axis]-expected.coordinates[i][axis])<1.01e-6);
   assert.ok(Math.abs(actual.distances[i]-expected.distances[i])<1);
   if(i)assert.ok(Math.abs(actual.coordinates[i][0]-actual.coordinates[i-1][0])<=180);
  }
 }
});

test('endpoint paths generate once on demand and animate through the shared replay',()=>{
 const [a,b]=[[151,-34],[-118,34]];
 const day={flight_geometry:'great_circle_v1',paths:{route:{quality:'illustrative',endpoints:[0,1],segments:64,anchor:0}},
  stations:[{lon:a[0],lat:a[1]},{lon:b[0],lat:b[1]}],services:[]};
 const service={mode:'flight',stops:[[0,100,100],[1,1000,1000]],legs:['route']};day.services=[service];
 core.hydrate(day);assert.equal(day._generatedFlightPaths,0);
 const point=core.servicePosition(service,550,day);assert.ok(Number.isFinite(point.lon));
 assert.equal(day._generatedFlightPaths,1);const path=day.paths.route.coordinates;
 assert.equal(core.routeFeatures(day.paths,['route']).length,1);
 core.hydrate(day);assert.equal(day.paths.route.coordinates,path);assert.equal(day._generatedFlightPaths,1);
 const legacy={paths:{route:{quality:'illustrative',coordinates:[[0,0],[1,1]],distances:[0,1]}},services:[]};
 const before=JSON.stringify(legacy);core.hydrate(legacy);assert.equal(JSON.stringify(legacy),before);
});

test('global cadence changes exactly at 4.5 without affecting existing views',()=>{
 for(const z of [0,4.49])assert.equal(flights.paintInterval({flight_geometry:'great_circle_v1'},z),250);
 for(const z of [4.5,10])assert.equal(flights.paintInterval({flight_geometry:'great_circle_v1'},z),60);
 for(const z of [0,4.49,4.5,10])assert.equal(flights.paintInterval({},z),60);
});

test('viewport margin keeps partially visible markers without inflating centre counts',()=>{
 const map={getCenter:()=>({lng:0}),getContainer:()=>({clientWidth:100,clientHeight:100}),project:([x,y])=>({x,y})};
 const contains=flights.viewport(map,12);
 assert.equal(contains([-12,50]),true);assert.equal(contains([-13,50]),false);
 assert.equal(contains([112,50]),true);assert.equal(contains([113,50]),false);
 assert.equal(flights.visibleCount(map,[{properties:{id:'one'},geometry:{coordinates:[-1,50]}}]),0);
});

test('alternate quotes choose within currencies without converting or hiding observations',()=>{
 const fare_quotes=[{currency:'EUR',amount_minor:20},{currency:'USD',amount_minor:10000},
  {currency:'USD',amount_minor:8000},{currency:'MYR',amount_minor:50}];
 const before=JSON.stringify(fare_quotes),best=flights.cheapestQuotes({fare_quotes});
 assert.deepEqual(best,[fare_quotes[2],fare_quotes[0],fare_quotes[3]]);
 assert.equal(JSON.stringify(fare_quotes),before);
});

test('global airport picker keeps exact airport IDs searchable without scanning flights',()=>{
 const stations=[{code:'MEL',name:'Melbourne Airport'},{code:'AVV',name:'Avalon Airport'},
  {code:'CGK',name:'Jakarta Airport'},{code:'HLP',name:'Jakarta Airport'}];
 const rows=boards.airportCatalogue(stations);
 assert.deepEqual(rows.map(r=>r.id).sort(),[0,1,2,3]);
 for (const row of rows) assert.equal(row.label,`${stations[row.id].code} · ${stations[row.id].name}`);
 assert.equal(new Set(rows.map(r=>r.label)).size,4);
});

test('World interpolation preserves legacy positions at boundaries and through long-haul arcs',()=>{
 for (const fixture of fixtures) {
  const stations=[{lon:fixture.a[0],lat:fixture.a[1],name:'A'},{lon:fixture.b[0],lat:fixture.b[1],name:'B'}];
  const service={mode:'flight',stops:[[0,100,100],[1,1000,1000]],legs:['route']};
  const world={flight_geometry:'great_circle_v1',stations,services:[service],paths:{route:{endpoints:[0,1],segments:64,anchor:0,quality:'illustrative'}}};
  const legacy={stations,services:[service],paths:{route:{coordinates:fixture.coordinates,distances:fixture.distances,quality:'illustrative'}}};
  core.hydrate(world);
  for (const now of [99,100,101,550,999,1000,1001]) {
   const actual=core.servicePosition(service,now,world), expected=core.servicePosition(service,now,legacy);
   if (!expected)assert.equal(actual,null);
   else for (const key of ['lon','lat'])assert.ok(Math.abs(actual[key]-expected[key])<2e-5,`${key} at ${now}`);
  }
 }
});
