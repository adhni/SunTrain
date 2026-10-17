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
