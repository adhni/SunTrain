const test = require('node:test');
const assert = require('node:assert/strict');
const flight = require('../assets/02_flights.js');
// A viewport crossing the dateline, using the same unwrapped pixels as MapLibre.
const map = {getCenter:()=>({lng:180}),getContainer:()=>({clientWidth:100,clientHeight:100}),
    project:([lon,lat])=>({x:lon-130,y:50-lat})};
const feature = (id,lon,lat=0)=>({properties:{id},geometry:{coordinates:[lon,lat]}});

test('individual identities count once across Pacific world copies and viewport edges',()=>{
 assert.equal(flight.visibleCount(map,[feature('a',-179),feature('a',181),feature('b',130),feature('c',230),feature('d',231)]),3);
 assert.equal(flight.inside(map,[-179,0]),true);
 assert.equal(flight.inside(map,[541,0]),true);
 assert.equal(flight.inside(map,[160,51]),false);
});

test('picking chooses the closest identity within 12 CSS pixels across the dateline',()=>{
 const features=[feature('far',176),feature('near',-179)];
 assert.equal(flight.nearest(map,features,{x:52,y:50}).properties.id,'near');
 assert.equal(flight.nearest(map,features,{x:63,y:50}).properties.id,'near');
 assert.equal(flight.nearest(map,features,{x:64,y:50}),null);
});

test('opening policy uses configured country/region bounds and captured hub/network endpoints',()=>{
 const day={bounds:[[1,2],[3,4]],stations:[{lon:170,lat:-20},{lon:-170,lat:20},{lon:0,lat:80}],services:[{stops:[[0,0,0],[1,0,0]]}]};
 for(const kind of ['country','region'])assert.deepEqual(flight.openingBounds({...day,flight_view_kind:kind}),day.bounds);
 for(const kind of ['hub','network'])assert.deepEqual(flight.openingBounds({...day,flight_view_kind:kind}),[[170,-20],[190,20]]);
 assert.deepEqual(flight.openingBounds({...day,services:[],flight_view_kind:'hub'}),day.bounds);
});

test('sprite identity includes both the carrier and its actual palette colour',()=>{
 const eu={carrier:'LH',color:'#efcf58'},sg={carrier:'LH',color:'#ba8fc4'};
 assert.notEqual(flight.planeKey(eu),flight.planeKey(sg));
 assert.equal(flight.planeKey(eu),flight.planeKey({...eu}));
 assert.notEqual(flight.planeKey(eu),flight.planeKey({...eu,carrier:'LX'}));
});

test('next departure uses exact future timestamps at origins inside the viewport',()=>{
 const day={end:500,stations:[{lon:170,lat:0},{lon:0,lat:0}]};
 const services=[{stops:[[0,99,99]]},{stops:[[1,102,102]]},{stops:[[0,123,123]]},{stops:[[0,200,200]]}];
 assert.equal(flight.nextDeparture(map,services,day,100),123);
 assert.equal(flight.nextDeparture(map,services,day,123),200);
 assert.equal(flight.nextDeparture(map,services,day,201),null);
 assert.equal(flight.nextDeparture(map,[{stops:[[0,501,501]]}],day,100),null);
});
