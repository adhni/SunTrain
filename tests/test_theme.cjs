const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('chart theming waits for plotting and ignores removed charts', async () => {
    const handlers = {}, frames = [], updates = [];
    const graph = {isConnected: true, _fullLayout: {}, layout: {}, data: [],
        on: (event, callback) => { handlers[event] = callback; }, closest: () => null};
    const document = {readyState: 'complete', documentElement: {dataset: {}}, body: {},
        querySelectorAll: selector => selector === '.js-plotly-plot' ? [graph] : [],
        addEventListener() {}, dispatchEvent() {}};
    const context = {document, console, requestAnimationFrame: callback => { frames.push(callback); return frames.length; },
        MutationObserver: class {observe() {}}, CustomEvent: class {}, setTimeout,
        localStorage: {getItem: () => 'dark', setItem() {}},
        Plotly: {relayout: async (_graph, values) => { updates.push(values); }, restyle: async () => {}}};
    context.window = context;
    vm.runInNewContext(fs.readFileSync(require.resolve('../assets/01_theme.js'), 'utf8'), context);
    const flush = async () => { while (frames.length) frames.shift()(); await new Promise(resolve => setImmediate(resolve)); };
    await flush();
    assert.equal(updates.length, 0, 'must not interrupt initial Plotly/map initialization');
    assert.equal(handlers.plotly_beforeplot(), undefined, 'returning false cancels Plotly rendering');
    handlers.plotly_afterplot();
    await flush();
    assert.equal(updates.length, 1);
    assert.equal(updates[0]['font.color'], '#e4eef0');
    graph.isConnected = false;
    context.suntrainTheme.setTheme('light');
    await flush();
    assert.equal(updates.length, 1, 'a lazily removed graph must not be updated');
});

function themeContext(saved, unavailable = false) {
    const writes=[], events=[], changes={}, selectors=[{value:''},{value:''}];
    const document={readyState:'complete', documentElement:{dataset:{}}, body:{},
        querySelectorAll:selector=>selector==='[data-theme-select]'?selectors:[],
        addEventListener:(name,handler)=>{changes[name]=handler;}, dispatchEvent:event=>events.push(event)};
    const context={document,console,requestAnimationFrame:()=>1,setTimeout,
        MutationObserver:class {observe() {}},CustomEvent:class {constructor(name,options){this.type=name;this.detail=options.detail;}},
        localStorage:{getItem:()=>{if(unavailable)throw Error('blocked');return saved;},setItem:(...args)=>{if(unavailable)throw Error('blocked');writes.push(args);}}};
    context.window=context;
    vm.runInNewContext(fs.readFileSync(require.resolve('../assets/01_theme.js'),'utf8'),context);
    return {api:context.suntrainTheme,document,writes,events,changes,selectors};
}

test('all five themes restore, synchronize selectors, save and emit map updates',()=>{
    for(const theme of ['light','dark','sunrise','blueprint','heritage']) {
        const ctx=themeContext(theme);
        assert.equal(ctx.api.current,theme);
        assert.ok(ctx.selectors.every(s=>s.value===theme));
        assert.equal(ctx.api.isDark,['dark','blueprint'].includes(theme));
        ctx.api.setTheme('light');
        ctx.changes.change({target:{matches:()=>true,value:theme}});
        assert.equal(ctx.document.documentElement.dataset.theme,theme);
        assert.equal(ctx.document.documentElement.dataset.tone,ctx.api.isDark?'dark':'light');
        assert.deepEqual(ctx.writes.at(-1),['suntrain-theme',theme]);
        assert.equal(ctx.events.at(-1).detail.theme,theme);
        assert.ok(ctx.selectors.every(s=>s.value===theme));
    }
});

test('invalid preferences and unavailable storage fall back safely',()=>{
    for(const saved of [null,'old-theme','toString','__proto__']) {
        const ctx=themeContext(saved);assert.equal(ctx.api.current,'dark');
        ctx.api.setTheme(saved);assert.equal(ctx.api.current,'dark');assert.equal(ctx.events.length,0);
    }
    const ctx=themeContext('sunrise',true);
    assert.equal(ctx.api.current,'dark');ctx.api.setTheme('heritage');assert.equal(ctx.api.current,'heritage');
});

test('theme repaint changes only basemap paint, preserving route layers and camera',()=>{
    const ctx=themeContext('light'), updates=[];
    const map={getLayer:id=>id==='basemap',setPaintProperty:(...args)=>updates.push(args)};
    const backgrounds=new Set();
    for(const theme of ['light','dark','sunrise','blueprint','heritage']) {
        ctx.api.setTheme(theme);ctx.api.styleMap(map);
        const style=ctx.api.mapStyle();
        backgrounds.add(style.layers[0].paint['background-color']);
        assert.equal(style.metadata['suntrain-theme'],theme);
        assert.equal(style.sources.basemap.tiles[0],'https://tile.openstreetmap.org/{z}/{x}/{y}.png');
    }
    assert.equal(backgrounds.size,5);
    assert.ok(updates.every(([layer])=>['background','basemap'].includes(layer)));
});
