const test=require('node:test');
const assert=require('node:assert/strict');
const network=require('../assets/02_flight_network.js');
const core=require('../assets/train_replay.js');
const stations=[{code:'CGK',name:'Jakarta'},{code:'MEL',name:'Melbourne'},{code:'AVV',name:'Avalon'}];
const day={start:1000,end:2000,stations,paths:{out:{coordinates:[[100,0],[140,-30]]},back:{coordinates:[[140,-30],[100,0]]},other:{coordinates:[[100,0],[141,-30]]}}};
function flight(id,a,b,at,carrier='ID') {return {id,number:id,mode:'flight',carrier,operator:'Batik Air',line:`${a}-${b}`,direction:'',legs:[b===2?'other':a===0?'out':'back'],stops:[[a,at,at],[b,at+500,at+500]]};}
const flights=[flight('out1',0,1,1000),flight('out2',0,1,1500,'OD'),flight('back',1,0,1600),flight('avv',0,2,1700),flight('carry',0,1,999),flight('next',0,1,2000)];
test('daily network owns unique departures at half-open boundaries, excluding carry-ins and transit',()=>{
 const input=[...flights,flights[0],{...flights[0],id:'train',mode:'train'}];
 assert.deepEqual(network.ownedFlights(input,day).map(s=>s.id),['out1','out2','back','avv']);
 const features=network.frequencyNetwork(input,day);
 assert.equal(features.reduce((n,f)=>n+f.properties.count,0),4);
 assert.equal(features.length,2);
 const pair=features.find(f=>f.properties.label==='CGK ↔ MEL').properties;
 assert.equal(pair.count,3);assert.equal(pair.forward,2);assert.equal(pair.reverse,1);
 assert.equal(pair.carriers,'ID, OD');
});
test('destinations count only outbound departures, group airlines by code and retain exact airports',()=>{
 const rows=network.destinations([...flights,flights[0]],0,day);
 assert.deepEqual(rows.map(r=>[stations[r.destination].code,r.count]),[['MEL',2],['AVV',1]]);
 assert.deepEqual(rows[0].carriers,[['ID','Batik Air'],['OD','Batik Air']]);
 assert.equal(network.destinations(flights,1,day)[0].count,1);
 assert.deepEqual(network.destinations(flights,2,day),[]);
});
test('code filters apply across both ends and distinguish same-name carriers and nearby airports',()=>{
 const filters={modes:[],operators:[],lines:[],directions:[],stations:[],number:'',carriers:['OD'],airports:['MEL']};
 assert.deepEqual(flights.filter(s=>core.matches(s,filters,day)).map(s=>s.id),['out2']);
 assert.equal(core.matches(flight('other',0,2,1100,'OD'),filters,day),false);
 assert.equal(core.matches(flight('inbound',1,0,1100,'OD'),filters,day),true);
 assert.equal(core.matches({...flights[0],mode:'train'},filters,day),true);
 const selected=flights.filter(s=>core.matches(s,{...filters,carriers:[],airports:['AVV']},day));
 assert.equal(network.frequencyNetwork(selected,day)[0].properties.count,1);
});
test('fixed frequency scale is monotonic, bounded and comparable when filters change',()=>{
 assert.ok(network.frequencyWidth(1)<network.frequencyWidth(10));
 assert.ok(network.frequencyWidth(10)<network.frequencyWidth(100));
 assert.equal(network.frequencyWidth(100000),12);
 const all=network.frequencyNetwork(flights,day).find(f=>f.properties.count===1);
 const subset=network.frequencyNetwork([flights[3]],day)[0];
 assert.equal(all.properties.width,subset.properties.width);
});

test('airport traffic restricts the correct endpoint, supports multiple airports and ignores transit',()=>{
 const filters={modes:[],operators:[],lines:[],directions:[],stations:[],number:'',airports:['CGK']};
 const out=flight('out',0,1,1100),back=flight('in',1,0,1100),unrelated=flight('other',1,2,1100);
 assert.equal(core.matches(out,{...filters,airportDirection:'departures'},day),true);
 assert.equal(core.matches(back,{...filters,airportDirection:'departures'},day),false);
 assert.equal(core.matches(out,{...filters,airportDirection:'arrivals'},day),false);
 assert.equal(core.matches(back,{...filters,airportDirection:'arrivals'},day),true);
 for(const airportDirection of ['both','arrivals','departures']) assert.equal(core.matches(unrelated,{...filters,airportDirection},day),false);
 assert.equal(core.matches(unrelated,{...filters,airports:['CGK','AVV'],airportDirection:'arrivals'},day),true);
 assert.equal(core.matches(out,{...filters,airports:[],airportDirection:'arrivals'},day),true);
 assert.equal(core.matches({...out,mode:'train'},{...filters,airportDirection:'arrivals'},day),true);
});

test('arrival frequency, timeline and overview own arrivals, including carry-ins and excluding next-day arrivals',()=>{
 const {summarize}=require('../assets/02_city_overview.js');
 const arrivals=[flight('carry-in',1,0,500),flight('today',1,0,1300),flight('midnight-end',1,0,1500),flight('tomorrow',1,0,1900)];
 const duplicate=[...arrivals,arrivals[0]];
 assert.deepEqual(network.ownedFlights(duplicate,day,'arrival').map(s=>s.id),['carry-in','today']);
 const features=network.frequencyNetwork(duplicate,day,'arrival');
 assert.equal(features[0].properties.count,2);
 assert.equal(core.departureActivity(arrivals,day.start,day.end,'arrival').reduce((a,b)=>a+b,0),2);
 const summary=summarize({...day,replay_kind:'flights',services:arrivals,timezone:'Asia/Jakarta'},
  {modes:[],operators:[],lines:[],directions:[],stations:[],number:'',airports:['CGK'],airportDirection:'arrivals'},core);
 assert.equal(summary.arrivals,true);assert.equal(summary.departures,2);
 assert.equal(summary.hours.reduce((n,h)=>n+h.departures,0),2);
});
