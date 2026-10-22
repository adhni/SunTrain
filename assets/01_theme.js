(function (root) {
    "use strict";
    const STORAGE_KEY = "suntrain-theme";
    const palettes = {
        light: {ink: "#18232d", surface: "#ffffff", grid: "#e0e6e3", background: "#edf1ef"},
        dark: {ink: "#e4eef0", surface: "#17212b", grid: "#34434e", background: "#101a23"}
    };
    let theme = "dark";
    try { if (localStorage.getItem(STORAGE_KEY) === "light") theme = "light"; } catch (_) {}
    document.documentElement.dataset.theme = theme;

    function rasterPaint() {
        return theme === "dark" ? {"raster-saturation": -1, "raster-contrast": 0.05,
            "raster-brightness-min": 0.82, "raster-brightness-max": 0.10, "raster-opacity": 0.7} :
            {"raster-saturation": -0.85, "raster-contrast": -0.05, "raster-brightness-min": 0, "raster-brightness-max": 1, "raster-opacity": 0.75};
    }
    function mapStyle() {
        return {version: 8, metadata: {"suntrain-theme": theme}, sources: {basemap: {
            type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}},
            layers: [{id: "background", type: "background", paint: {"background-color": palettes[theme].background}},
                     {id: "basemap", type: "raster", source: "basemap", paint: rasterPaint()}]};
    }
    function styleMap(map) {
        if (!map?.getLayer("basemap")) return;
        map.setPaintProperty("background", "background-color", palettes[theme].background);
        for (const [key, value] of Object.entries(rasterPaint())) map.setPaintProperty("basemap", key, value);
    }
    function updateButtons() {
        for (const button of document.querySelectorAll("[data-theme-toggle]")) {
            const label = theme === "dark" ? "Light mode" : "Dark mode";
            if (button.textContent !== label) {
                if (root.dash_clientside?.set_props && button.id) root.dash_clientside.set_props(button.id, {children: label});
                else button.textContent = label;
            }
            button.setAttribute("aria-pressed", String(theme === "dark"));
            button.title = `Switch site and maps to ${theme === "dark" ? "light" : "dark"} mode`;
        }
    }

    const observed = new WeakSet(), busy = new WeakSet(), pending = new Set(), plotted = new WeakSet(), announced = new WeakSet();
    const chartColors = {"#0d6f67": "#50c4b2", "#b13b5c": "#e981a0", "#b76a16": "#edb36b", "#657142": "#b0c489"};
    function chartColor(value) {
        if (typeof value !== "string") return value;
        if (theme === "dark") return chartColors[value.toLowerCase()] || value;
        return Object.entries(chartColors).find(([, bright]) => bright === value.toLowerCase())?.[0] || value;
    }
    let plotFrame = null;
    function schedulePlot(graph) {
        pending.add(graph);
        if (plotFrame !== null) return;
        plotFrame = requestAnimationFrame(() => {
            plotFrame = null;
            const graphs = [...pending]; pending.clear();
            for (const element of graphs) applyPlot(element);
        });
    }
    async function applyPlot(graph) {
        if (!graph.isConnected || !root.Plotly || !graph._fullLayout || !plotted.has(graph)) return;
        if (busy.has(graph)) { pending.add(graph); return; }
        busy.add(graph);
        try {
            const colors = palettes[theme], layout = graph.layout, update = {};
            const put = (key, actual, desired) => { if (actual !== desired) update[key] = desired; };
            put("font.color", layout.font?.color, colors.ink);
            put("hoverlabel.font.color", layout.hoverlabel?.font?.color, colors.ink);
            put("hoverlabel.bgcolor", layout.hoverlabel?.bgcolor, colors.surface);
            put("hoverlabel.bordercolor", layout.hoverlabel?.bordercolor, colors.grid);
            put("paper_bgcolor", layout.paper_bgcolor, "rgba(0,0,0,0)");
            put("plot_bgcolor", layout.plot_bgcolor, "rgba(0,0,0,0)");
            for (const key of Object.keys(graph._fullLayout)) {
                if (/^[xy]axis\d*$/.test(key)) {
                    put(`${key}.gridcolor`, layout[key]?.gridcolor, colors.grid);
                    put(`${key}.zerolinecolor`, layout[key]?.zerolinecolor, colors.grid);
                }
                if (/^map(box)?\d*$/.test(key)) {
                    // Repaint the basemap without replacing its style while Plotly
                    // is adding sources or a lazily mounted graph is being removed.
                    const map = graph._fullLayout[key]?._subplot?.map;
                    if (map?.isStyleLoaded()) styleMap(map);
                    else if (map?.once) map.once("load", () => { if (graph.isConnected) styleMap(map); });
                }
            }
            (layout.annotations || []).forEach((annotation, index) => put(`annotations[${index}].font.color`, annotation.font?.color, colors.ink));
            if (Object.keys(update).length) await root.Plotly.relayout(graph, update);
            if (!graph.isConnected || !graph.data) return;
            for (const key of ["marker.color", "line.color"]) {
                const indices = [], values = [], [object, property] = key.split(".");
                graph.data.forEach((trace, index) => {
                    const current = trace[object]?.[property], desired = chartColor(current);
                    if (current !== desired) { indices.push(index); values.push(desired); }
                });
                if (indices.length) await root.Plotly.restyle(graph, {[key]: values}, indices);
            }
        } catch (error) {
            console.warn("Could not update chart theme", error);
        } finally {
            busy.delete(graph);
            const map = graph._fullLayout?.mapbox?._subplot?.map;
            if (graph.isConnected && graph.closest("#station-map-graph") && plotted.has(graph) && map?.isStyleLoaded() && !announced.has(graph)) {
                announced.add(graph);
                root.dash_clientside?.set_props("analysis-network-ready", {data: true});
            }
            if (pending.has(graph)) schedulePlot(graph);
        }
    }
    function refresh() {
        updateButtons();
        let notReady = false;
        for (const graph of document.querySelectorAll(".js-plotly-plot")) {
            if (typeof graph.on !== "function") { notReady = true; continue; }
            if (!observed.has(graph)) {
                observed.add(graph);
                graph.on("plotly_beforeplot", () => {
                    plotted.delete(graph);
                    if (announced.has(graph)) {
                        announced.delete(graph);
                        root.dash_clientside?.set_props("analysis-network-ready", {data: false});
                    }
                });
                graph.on("plotly_afterplot", () => { plotted.add(graph); schedulePlot(graph); });
            }
            schedulePlot(graph);
        }
        if (notReady) setTimeout(refresh, 150);
    }
    function setTheme(value) {
        if (value !== "dark" && value !== "light") return;
        theme = value;
        document.documentElement.dataset.theme = theme;
        try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
        refresh();
        document.dispatchEvent(new CustomEvent("suntrain:themechange", {detail: {theme}}));
    }
    root.suntrainTheme = {get current() { return theme; }, setTheme, mapStyle, styleMap};
    document.addEventListener("click", event => {
        if (event.target.closest?.("[data-theme-toggle]")) setTheme(theme === "dark" ? "light" : "dark");
    });
    function start() {
        refresh();
        new MutationObserver(mutations => {
            const relevant = mutations.some(mutation => mutation.type === "attributes" ? mutation.target.matches(".js-plotly-plot") :
                [...mutation.addedNodes].some(element => element.nodeType === 1 &&
                    (element.matches(".js-plotly-plot, [data-theme-toggle]") || element.querySelector(".js-plotly-plot, [data-theme-toggle]"))));
            if (relevant) refresh();
        }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["class"]});
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
    else start();
})(window);
