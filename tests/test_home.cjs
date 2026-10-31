const test = require('node:test');
const assert = require('node:assert/strict');
const {groupPlaces} = require('../assets/03_home.js');
const place = (id, x, y) => ({id, name: id, bounds: [[x-1,y-1],[x+1,y+1]]});

test('world pins group nearby places and separate them when zoomed in without losing entries', () => {
    const places=[place('Belgium',4,50),place('Netherlands',5,52),place('Germany',10,51),place('Melbourne',145,-38)];
    const original=JSON.stringify(places);
    const groups=groupPlaces(places,([x,y])=>({x:x*2,y:y*2}));
    assert.equal(groups.length,2);
    assert.equal(groups.find(g=>g.members.length===3).coordinates[0],19/3);
    assert.deepEqual(groups.flatMap(g=>g.members.map(m=>m.place.id)).sort(),places.map(p=>p.id).sort());
    const zoomed=groupPlaces(places,([x,y])=>({x:x*100,y:y*100}));
    assert.equal(zoomed.length,places.length);
    assert.ok(zoomed.every(group=>group.members.length===1));
    assert.equal(JSON.stringify(places),original);
});

test('pin grouping handles empty catalogues and chains of overlapping markers', () => {
    assert.deepEqual(groupPlaces([],([x,y])=>({x,y})),[]);
    const places=[place('a',0,0),place('b',30,0),place('c',60,0)];
    const groups=groupPlaces(places,([x,y])=>({x,y}));
    assert.equal(groups.length,1);
    assert.deepEqual(groups[0].coordinates,[30,0]);
});

test('a dense country catalogue cannot chain into one continent-sized cluster', () => {
    const places = Array.from({length:30},(_,i)=>place(String(i),i*20,0));
    const groups = groupPlaces(places,([x,y])=>({x,y}));
    assert.ok(groups.length>1);
    assert.equal(groups.flatMap(g=>g.members).length,30);
    for (const group of groups) {
        const xs=group.members.map(m=>m.point.x);
        assert.ok(Math.max(...xs)-Math.min(...xs)<=84);
    }
});

// The home map displays one world, so Pacific's 190° centre must be −170°.
test('Pacific dateline bounds produce a pin in the displayed world', () => {
    const pacific={id:'pacific_flights',bounds:[[128,-33],[252,33]]};
    const groups=groupPlaces([pacific],([x,y])=>{assert.equal(x,-170);return {x,y};});
    assert.deepEqual(groups[0].coordinates,[-170,0]);
    assert.deepEqual(pacific.bounds,[[128,-33],[252,33]]);
});

test('World flights is searchable without an arbitrary worldwide map pin',()=>{
 const world={...place('world_flights',0,0),home_marker:false};
 const melbourne=place('melbourne',145,-38);
 assert.deepEqual(groupPlaces([world,melbourne],([x,y])=>({x,y})).flatMap(g=>g.members.map(m=>m.place.id)),['melbourne']);
});

const {eligiblePlaces, surprise} = require('../assets/03_home.js');
test('transport choices apply to catalogue entries, including non-pin networks and mixed modes', () => {
    const places = [
        {id:'rail',modes:['train','tram']}, {id:'flight',modes:['flight'],home_marker:false},
        {id:'mixed',modes:['train','flight']},
    ];
    assert.deepEqual(eligiblePlaces(places,'all').map(p=>p.id),['rail','flight','mixed']);
    assert.deepEqual(eligiblePlaces(places,'transit').map(p=>p.id),['rail','mixed']);
    assert.deepEqual(eligiblePlaces(places,'flights').map(p=>p.id),['flight','mixed']);
});
test('Surprise me respects transport choice, avoids repeats, and handles a single eligible scene', () => {
    const scenes = [{id:'world',kind:'flights'}, {id:'melbourne',kind:'transit'}, {id:'tokyo',kind:'transit'}];
    assert.equal(surprise(scenes,'transit','melbourne',()=>0).id,'tokyo');
    assert.equal(surprise(scenes,'flights','world',()=>0).id,'world');
    assert.equal(surprise(scenes,'all','world',()=>.99).id,'tokyo');
    assert.equal(surprise([],'all',null,()=>0),null);
});
