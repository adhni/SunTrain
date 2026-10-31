"""Lightweight discovery map; schedules load only after choosing a replay."""
import json
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from dash import ClientsideFunction, Input, Output, dcc, html

from dashboard.cities import CITIES
from dashboard.transit import PERIOD_END, PERIOD_START


EXPERIENCES = [
    {"id": "world", "city": "world_flights", "title": "World in motion", "kind": "flights",
     "date": "2026-11-02", "time": "10:00", "zone": "UTC", "modes": ["flight"]},
    {"id": "melbourne", "city": "melbourne", "title": "Melbourne morning rush", "kind": "transit",
     "date": "2024-05-27", "time": "08:00", "zone": "Australia/Melbourne", "modes": ["train"]},
    {"id": "tokyo", "city": "tokyo", "title": "Tokyo’s rail network", "kind": "transit",
     "date": "2026-10-20", "time": "08:00", "zone": "Asia/Tokyo", "modes": ["train", "subway"]},
    {"id": "singapore", "city": "singapore_flights", "title": "Singapore’s connections", "kind": "flights",
     "date": "2026-11-02", "time": "10:00", "zone": "Asia/Singapore", "modes": ["flight"]},
]
for _experience in EXPERIENCES:
    _experience["at"] = int(datetime.fromisoformat(_experience["date"] + "T" + _experience["time"])
                            .replace(tzinfo=ZoneInfo(_experience["zone"])).timestamp())


def home_places():
    return [{"id": key, "name": settings["name"], "bounds": settings["bounds"],
             "home_marker": settings.get("home_marker", True),
             "modes": [mode for _, mode in settings["modes"]],
             "default_modes": settings.get("default_modes", [mode for _, mode in settings["modes"]]),
             "start": settings.get("start_date", PERIOD_START),
             "end": settings.get("end_date", PERIOD_END)}
            for key, settings in sorted(CITIES.items(), key=lambda item: item[1]["name"].casefold())]


def preview_src(experience):
    """Decorative vector maps, with no tiles or replay downloads."""
    if experience["kind"] == "flights":
        land = '<path d="M15 20 32 12 51 17 60 30 48 40 40 62 30 42 17 35ZM65 45 78 42 88 53 80 76 71 63ZM98 18 122 12 143 22 172 20 190 34 170 43 151 38 139 51 126 39 120 65 106 62 98 43ZM166 62 180 56 194 66 184 76 169 73Z" fill="#284b54"/>'
        routes = '<path d="M39 30Q88 -5 124 28M39 30Q80 24 78 55M124 28Q169 4 178 65M124 28Q150 29 156 44"/>'
        if experience["id"] == "singapore":
            routes = '<path d="M156 47Q108 -4 39 30M156 47Q148 12 124 28M156 47Q190 40 178 65M156 47Q114 32 78 55"/>'
        drawing = land + '<g fill="none" stroke="#f5a24b" stroke-width="1.6" opacity=".9">' + routes + '</g><g fill="#f5a24b"><circle cx="39" cy="30" r="2"/><circle cx="124" cy="28" r="2"/><circle cx="156" cy="47" r="3"/><circle cx="178" cy="65" r="2"/></g>'
    else:
        drawing = '<path d="M130 0 120 22 138 40 135 58 160 85H210V0Z" fill="#284b54"/><g fill="none" stroke-linecap="round" stroke-width="2">'
        paths = [('M28 16 73 28 103 46 143 61 185 70', '#67d6c1'), ('M58 0 82 28 103 46 116 65 117 85', '#f5c55a'), ('M17 65 61 58 103 46 149 21 172 0', '#f191b1'), ('M90 0 98 26 103 46 73 75', '#8db9ec')]
        if experience['id'] == 'tokyo':
            paths = [('M63 20 109 13 142 31 139 60 100 71 63 55Z', '#67d6c1'), ('M10 58 63 55 104 45 142 31 194 17', '#f5c55a'), ('M83 0 100 25 104 45 100 71 89 85', '#f191b1'), ('M18 15 63 20 104 45 153 67 202 70', '#8db9ec')]
        drawing += ''.join('<path d="%s" stroke="%s"/>' % pair for pair in paths)
        drawing += '</g><g fill="#e5f5f0">' + ''.join('<circle cx="%s" cy="%s" r="2.4"/>' % pair for pair in [(73, 28), (103, 46), (143, 61), (61, 58), (149, 21), (116, 65)]) + '</g>'
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 210 85"><rect width="210" height="85" fill="#152c34"/>' + drawing + '</svg>'
    return "data:image/svg+xml," + quote(svg)


def build_home_panel():
    places = home_places()
    return html.Section(id="home-panel", className="home-panel", **{
        "data-places": json.dumps(places), "data-experiences": json.dumps(EXPERIENCES)}, children=[
        dcc.Store(id="home-map-state"), dcc.Store(id="home-choice"),
        html.Div(className="home-world", children=[
            html.Div(id="home-map", role="region", **{"aria-label": "World map of available transport replays. Pan, zoom, or choose a place using search."}),
            html.Div(className="home-search", children=[
                html.H2("The world, in motion."),
                html.Label("Where shall we go?", htmlFor="home-place"),
                dcc.Dropdown(id="home-place", options=[{"label": place["name"], "value": place["id"]} for place in places],
                             placeholder="Find a city or country…", searchable=True, clearable=True),
                html.Div(className="home-kind-switch", role="group", **{"aria-label": "Explore transport"}, children=[
                    html.Button(label, **{"data-home-kind": value, "aria-pressed": value == "all"})
                    for value, label in [("all", "All"), ("transit", "Rail & local transport"), ("flights", "Flights")]
                ]),
                html.Span(f"{len(places)} places to explore", id="home-count", className="home-count"),
            ]),
            html.Button("World view", id="home-reset", className="finder-chip home-reset", title="Zoom out to the world"),
            html.Div(className="home-discover", children=[
                html.Div(className="home-discover-heading", children=[
                    html.Strong("Try this"),
                    html.Button("Surprise me", id="home-surprise", className="finder-chip"),
                ]),
                html.Div(className="home-experiences", children=[
                    html.Article(className="home-experience home-experience-" + item["kind"], **{"data-experience": item["id"], "data-kind": item["kind"]}, children=[
                        html.Img(src=preview_src(item), alt="", className="home-experience-preview"),
                        html.Div(className="home-experience-copy", children=[
                            html.H3(item["title"]),
                            html.Span(item["time"] + (" UTC" if item["zone"] == "UTC" else " · "), className="home-experience-time"),
                            html.Span("Local time" if item["zone"] != "UTC" else "", className="home-experience-zone"),
                            html.Button("Watch", id="home-world-flights" if item["id"] == "world" else "home-watch-" + item["id"], **{"data-watch": item["id"], "aria-label": "Watch " + item["title"]}),
                        ]),
                    ]) for item in EXPERIENCES
                ]),
            ]),
            html.Span("Drag to explore · Scroll or pinch to zoom", className="home-map-hint"),
        ]),
        html.P(id="home-map-message", role="status", className="replay-muted home-map-message"),
    ])


def register_home_callbacks(app):
    app.clientside_callback(
        ClientsideFunction(namespace="suntrainHome", function_name="sync"),
        Output("home-map-state", "data"), Input("view-tabs", "value"), Input("home-place", "value"),
    )
    app.clientside_callback(
        """function(choice) {
            if (!choice) return [dash_clientside.no_update, dash_clientside.no_update];
            return [choice.city, 'replay'];
        }""",
        Output("replay-city", "value"), Output("view-tabs", "value"), Input("home-choice", "data"),
        prevent_initial_call=True,
    )
