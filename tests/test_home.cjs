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
