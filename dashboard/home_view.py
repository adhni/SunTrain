"""Small location catalogue for the world map; schedules load in replay only."""
import json

from dash import ClientsideFunction, Input, Output, dcc, html

from dashboard.cities import CITIES
from dashboard.transit import PERIOD_END, PERIOD_START


def home_places():
    return [{"id": key, "name": settings["name"], "bounds": settings["bounds"],
             "modes": [mode for _, mode in settings["modes"]],
             "start": settings.get("start_date", PERIOD_START),
             "end": settings.get("end_date", PERIOD_END)}
            for key, settings in sorted(CITIES.items(), key=lambda item: item[1]["name"].casefold())]


def build_home_panel():
    places = home_places()
    return html.Section(id="home-panel", className="home-panel", **{"data-places": json.dumps(places)}, children=[
        dcc.Store(id="home-map-state"), dcc.Store(id="home-choice"),
        html.Div(className="home-intro", children=[
            html.Div([html.H2("The world, in motion."),
                      html.P("Pick a place and bring its transport network to life."),
                      html.Div(className='home-legend',role='list',**{'aria-label':'Map key'},children=[
                          html.Span([html.Span(className='home-key-dot',**{'aria-hidden':'true'}),html.Span('Rail & local transport')],className='home-legend-item',role='listitem'),
                          html.Span([html.Span('\u2708\uFE0E',className='home-key-dot home-key-flight',**{'aria-hidden':'true'}),html.Span('Flights')],className='home-legend-item',role='listitem'),
                          html.Span([html.Span(className='home-key-dot home-key-mixed',**{'aria-hidden':'true'}),html.Span('Both')],className='home-legend-item',role='listitem'),
                      ])]),
            html.Span(f"{len(places)} places to explore", className="home-count"),
        ]),
        html.Div(className="home-world", children=[
            html.Div(className="home-search", children=[
                html.Label("Where shall we go?", htmlFor="home-place"),
                dcc.Dropdown(id="home-place", options=[{"label": place["name"], "value": place["id"]} for place in places],
                             placeholder="Find a city or country…", searchable=True, clearable=True),
            ]),
            html.Div(id="home-map", role="region", **{"aria-label": "World map of available transport replays. Pan, zoom, or choose a place using search."}),
            html.Button("World view", id="home-reset", className="finder-chip home-reset", title="Zoom out to the world"),
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
