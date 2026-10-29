const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {stationCalls, upcomingPage, stationCatalogue, formatCallTime} = require('../assets/02_station_departures.js');
const {hydrate, matches} = require('../assets/train_replay.js');
const legacy = {id:'legacy', mode:'train', line:'Loop', operator:'Rail', number:'1', destination:'Terminus',
    stops:[[0,90,100],[1,110,120],[0,130,140],[2,150,150]], legs:['a','b','c']};
const stations = [{name:'Central',lat:1,lon:1},{name:'Central',lat:2,lon:2},{name:'Terminus',lat:null,lon:null}];

function browserBoardContext() {
    const root = {document: {createElement: tag => ({tagName: tag.toUpperCase()})}, suntrainI18n: {
        bind(element, text) {
            assert.notEqual(element.tagName, 'OPTION', 'Source option labels must bypass translation matching');
            element.textContent = text;
        },
    }};
    root.window = root;
    vm.runInNewContext(fs.readFileSync(require.resolve('../assets/02_station_departures.js'), 'utf8'), root);
    return root;
}

test('picker keeps source labels as text, limits choices and searches without translating data', () => {
    const root = browserBoardContext();
    const choices = {children: [], replaceChildren() { this.children = []; }, append(option) { this.children.push(option); }};
    const catalogue = Array.from({length: 70}, (_, id) => ({id, label: `Airport ${id} <b>ABC</b> · Flight · AAA → BBB`}));
    const board = {catalogue, choices, station: 3, search: {value: ''}, choose: {}, matchCount: {}};
    const update = () => root.suntrainDepartures.Board.prototype.updateChoices.call(board);
    update();
    assert.equal(choices.children.length, 60);
    assert.equal(choices.value, '3');
    assert.equal(board.choose.disabled, false);
    assert.match(board.matchCount.textContent, /Showing 60 of 70 stops/);
    assert.equal(choices.children[0].textContent, catalogue[0].label);
    assert.equal(choices.children[0].title, catalogue[0].label);
    assert.equal(choices.children[0].innerHTML, undefined);
    board.search.value = 'AIRPORT 69'; board.station = 69; update();
    assert.equal(choices.children.length, 1);
    assert.equal(choices.children[0].value, '69');
    assert.equal(choices.children[0].textContent, catalogue[69].label);
});

test('catalogue translates interface tokens while preserving source names and routes', () => {
    const root = browserBoardContext();
    let language = 'en';
    root.suntrainI18n.translate = text => {
        assert.ok(['Flight', 'Location unavailable'].includes(text), 'Only interface tokens should be translated');
        return language === 'id' ? {'Flight': 'Penerbangan', 'Location unavailable': 'Lokasi tidak tersedia'}[text] : text;
    };
    const airports = [{name: 'Source <b>Airport</b> (ABC)', lat: null, lon: null}, {name: 'Other (DEF)', lat: 1, lon: 2}];
    const service = {mode: 'flight', line: 'ABC → DEF', stops: [[0, 0, 0], [1, 60, 60]]};
    const label = () => root.suntrainDepartures.stationCatalogue([service], airports, true).find(row => row.id === 0).label;
    const english = label();
    assert.equal(english, 'Source <b>Airport</b> (ABC) · Flight · ABC → DEF · Location unavailable');
    language = 'id';
    assert.equal(label(), 'Source <b>Airport</b> (ABC) · Penerbangan · ABC → DEF · Lokasi tidak tersedia');
    language = 'en'; assert.equal(label(), english);
});

test('legacy and compact schedules give equivalent departures, preserving repeated visits and shared buffers', () => {
    const day = hydrate({transit_stop_patterns:{s:{stations:[0,1,0,2],legs:['a','b','c']}},
        transit_patterns:{p:{stop_pattern:'s',times:[0,10,20,30,40,50,60,60],line:'Loop'}},
        services:[{id:'packed',pattern:'p',departure:90}]});
    const packed=day.services[0], before=JSON.stringify(day);
    assert.deepEqual(stationCalls([legacy],0,0,200).map(c=>[c.index,c.at]),[[0,100],[2,140]]);
    assert.deepEqual(stationCalls([packed],0,0,200).map(c=>[c.index,c.at]),[[0,100],[2,140]]);
    assert.strictEqual(packed.times,day.transit_patterns.p.times);
    assert.strictEqual(packed.stopIds,day.transit_stop_patterns.s.stations);
    assert.equal(JSON.stringify(day),before);
    assert.equal(stationCalls([packed],2,0,200).length,0);
});

test('stop IDs distinguish identical names and unlocated stops remain searchable', () => {
    assert.deepEqual(stationCalls([legacy],1,0,200).map(c=>c.at),[120]);
    const catalogue=stationCatalogue([legacy],stations);
    assert.equal(catalogue.length,3);
    assert.notEqual(catalogue.find(s=>s.id===0).label,catalogue.find(s=>s.id===1).label);
    assert.match(catalogue.find(s=>s.id===2).label,/Location unavailable/);
});

test('upcoming departures include exact boundaries, clamp pages, and support backwards seeking', () => {
    const calls=stationCalls(Array.from({length:40},(_,i)=>({...legacy,id:String(i),timeOffset:i*100})),1,0,5000);
    assert.equal(upcomingPage(calls,120).rows[0].at,120);
    assert.equal(upcomingPage(calls,120.1).rows[0].at,220);
    assert.equal(upcomingPage(calls,0).rows.length,15);
    assert.equal(upcomingPage(calls,0,99).page,2);
    assert.equal(upcomingPage(calls,5000).total,0);
    assert.equal(upcomingPage(calls,120).total,40);
    assert.equal(stationCalls([legacy],0,110,140).length,1);
});

test('all selected modes, estimates, and incomplete schedules retain their identity without geometry', () => {
    const services=['train','subway','tram','bus','ferry'].map((mode,i)=>({...legacy,id:mode,mode,frequency_based:mode==='bus',terminal_arrival_missing:mode==='tram'}));
    const filtered=services.filter(service=>matches(service,{modes:['bus','ferry'],operators:[],lines:[],directions:[],stations:[],number:''},{stations}));
    const calls=stationCalls(filtered,0,0,200);
    assert.equal(calls.length,4);
    assert.equal(calls.filter(c=>c.service.frequency_based).length,2);
    assert.strictEqual(calls[0].service,filtered[0]);
    assert.equal(stationCalls(services,2,0,200).length,0);
    assert.equal(stationCalls([],0,0,200).length,0);
});

test('overnight calls and repeated local DST hours sort by instant, with explicit dates and offsets', () => {
    const first=Date.parse('2026-04-04T15:30:00Z')/1000, second=first+3600;
    const services=[{...legacy,id:'later',stops:[[0,second,second],[1,second+60,second+60]]},
        {...legacy,id:'earlier',stops:[[0,first,first],[1,first+60,first+60]]}];
    assert.deepEqual(stationCalls(services,0,first,second).map(c=>c.service.id),['earlier','later']);
    const a=formatCallTime(first,'Australia/Melbourne'),b=formatCallTime(second,'Australia/Melbourne');
    assert.match(a,/02:30/); assert.match(b,/02:30/); assert.notEqual(a,b);
    assert.match(a,/GMT\+11/); assert.match(b,/GMT\+10/);
    assert.notEqual(formatCallTime(first-86400,'Australia/Melbourne'),a);
});

test('large shared patterns stay shared and results are bounded without losing calls', () => {
    const services=Array.from({length:10000},(_,i)=>({...legacy,id:String(i),timeOffset:i*60}));
    const calls=stationCalls(services,0,0,1000000);
    assert.equal(calls.length,20000);
    assert.equal(upcomingPage(calls,0).rows.length,15);
    assert.ok(services.every(s=>s.stops===legacy.stops));
});
