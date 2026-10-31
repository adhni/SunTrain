const test = require('node:test');
const assert = require('node:assert/strict');
const {matchesPlace, airlineOptions, placeOptions} = require('../assets/02_flight_places.js');
const stations = [{code:'MEL',country:'AU'}, {code:'AVV',country:'AU'}, {code:'SIN',country:'SG'}, {code:'LHR',country:'GB'}];
const flight = (id,carrier,a,b,brand,group) => ({id,carrier,operator:{QF:'Qantas',SQ:'Singapore Airlines',BA:'British Airways'}[carrier],color:'#abc',
    mode:'flight',flight_scope:a===0&&b===1?'domestic':'international',flight_brand:brand,flight_group:group,stops:[[a,100,100],[b,200,200]]});
const services = [flight('a','QF',0,2),flight('b','QF',0,1),flight('c','SQ',2,3),flight('d','BA',3,0,'ba','iag')];
const day = {stations,services,flight_groups:{iag:'IAG'},flight_brands:{ba:'British Airways network'}};

test('geographical lenses include either endpoint, once, preserving exact airports',()=>{
    const choose = place => services.filter(s=>matchesPlace(s,place,day)).map(s=>s.id);
    assert.deepEqual(choose({kind:'country',country:'AU'}),['a','b','d']);
    assert.deepEqual(choose({kind:'airport',code:'AVV'}),['b']);
    assert.deepEqual(choose({kind:'region',countries:['SG','AU']}),['a','b','c','d']);
    assert.deepEqual(choose({kind:'world'}),['a','b','c','d']);
    assert.deepEqual(choose({kind:'experience',between:[['GB'],['SG']]}),['c']);
    assert.deepEqual(choose({kind:'experience',scope:'international'}),['a','c','d']);
});
test('airlines sort by unique captured flights with deterministic name ties, preserving group filters',()=>{
    const options = airlineOptions([...services,services[0]],day);
    assert.deepEqual(options.slice(0,3).map(o=>[o.value,o.count]),[['QF',2],['BA',1],['SQ',1]]);
    assert.equal(options.find(o=>o.value==='group:iag').count,1);
    assert.equal(options.find(o=>o.value==='brand:ba').count,1);
    const filtered = airlineOptions([services[2]],day,['QF']);
    assert.deepEqual(filtered.map(o=>[o.value,o.count]),[['SQ',1],['QF',0]]);
    assert.ok(filtered[0].search.includes('Singapore Airlines'));
});
test('place search finds airport names and codes, UK aliases, and separates original replays',()=>{
    const places = [
        {id:'world_flights',kind:'world',name:'World',modes:['flight'],count:4},
        {id:'country:GB',kind:'country',country:'GB',name:'GB',region:'europe',modes:['flight'],count:3},
        {id:'airport:LHR',kind:'airport',country:'GB',region:'europe',name:'Heathrow',municipality:'London',code:'LHR',modes:['flight'],count:2},
        {id:'old',kind:'replay',name:'United Kingdom',start:'2026-11-02',end:'2026-11-02',modes:['flight']},
        {id:'rail',kind:'transit',name:'London',modes:['train']},
    ];
    const values = (kind,q,selected) => placeOptions(places,kind,q,selected).filter(o=>!o.disabled).map(o=>o.value);
    assert.deepEqual(values('flights','LHR'),['airport:LHR']);
    assert.deepEqual(values('flights','London'),['airport:LHR']);
    assert.deepEqual(values('flights','UK'),['country:GB','airport:LHR']);
    assert.ok(values('flights','United Kingdom').includes('old'));
    assert.ok(!values('flights','').includes('old'));
    assert.deepEqual(values('transit','London'),['rail']);
    const uk = placeOptions([...places,{id:'country:UA',kind:'country',name:'UA',country:'UA',modes:['flight'],count:5}],'flights','UK').filter(o=>!o.disabled);
    assert.equal(uk[0].value,'country:GB');
    assert.ok(placeOptions(places,'flights','LHR','country:GB').some(o=>o.value==='country:GB'));
    const london = placeOptions([...places,{id:'airport:LCY',kind:'airport',country:'GB',name:'London City Airport',municipality:'London',code:'LCY',modes:['flight'],count:1}],'flights','London').filter(o=>!o.disabled);
    assert.deepEqual(london.filter(o=>o.value.startsWith('airport:')).map(o=>o.value),['airport:LHR','airport:LCY']);
});

test('geographical and existing airline, direction and country filters compose',()=>{
    const core = require('../assets/train_replay.js');
    const filters = {place:{kind:'country',country:'SG'},modes:[],operators:[],lines:[],directions:[],stations:[],carriers:['QF'],airports:[],fromCountries:[],toCountries:[]};
    assert.deepEqual(services.filter(s=>core.matches(s,filters,day)).map(s=>s.id),['a']);
    assert.deepEqual(services.filter(s=>core.matches(s,{...filters,fromCountries:['GB']},day)),[]);
    const catalogueDay={...day,replay_kind:'flights',flight_country_filters:true};
    assert.deepEqual(core.cataloguedAirports(catalogueDay,{place:{kind:'country',country:'AU'}}),[0,1]);
    assert.deepEqual(core.cataloguedAirports(catalogueDay,{place:{kind:'airport',code:'AVV'}}),[1]);
});
