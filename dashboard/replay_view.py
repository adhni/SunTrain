"""Dash controls for the browser-owned historical replay."""
from __future__ import annotations

import logging
from datetime import date

from dash import ClientsideFunction, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from dashboard.replay_http import descriptor, selected_modes
from dashboard.transit import available_range
from dashboard.cities import CITIES, city_settings
from dashboard.theme_view import theme_picker, language_picker
from dashboard.i18n import message

LOGGER = logging.getLogger(__name__)


def field(label, control, **props):
    return html.Div([html.Label(label, htmlFor=control.id, className="finder-label"), control], className="finder-field", **props)


def period_label(minimum, maximum):
    first, last = date.fromisoformat(minimum), date.fromisoformat(maximum)
    if first == last:
        return first.strftime("%d %b %Y")
    start = first.strftime("%d %b %Y" if first.year != last.year else "%d %b")
    return f"{start}–{last:%d %b %Y}"


def build_replay_panel(metadata, default_date):
    coverage = available_range()
    shared_period = coverage and metadata["min_date"] <= coverage[0] and metadata["max_date"] >= coverage[1]
    minimum, maximum = coverage if shared_period else (metadata["min_date"], metadata["max_date"])
    default_date = minimum if shared_period else default_date
    badge = period_label(minimum, maximum) if shared_period else "Historical · FY 2023–24"
    return html.Div(id="replay-panel", className="tab-panel replay-panel", style={"display": "block"}, tabIndex=-1, children=[
        dcc.Store(id="replay-day", storage_type="memory"),
        dcc.Store(id="replay-client-state", storage_type="memory"),
        html.Div(className="replay-heading", children=[
            html.P(CITIES["melbourne"]["description"], id="replay-description"),
            html.Span(badge, id="replay-period", className="replay-badge"),
        ]),
        html.Div(id="replay-filter-controls", className="replay-filters", children=[
            field("Location", dcc.Dropdown(id="replay-city", options=[{"label": value["name"], "value": key}
                  for key, value in sorted(CITIES.items(), key=lambda item: item[1]["name"].casefold())],
                  value="melbourne", clearable=False, searchable=True)),
            html.Div(className="finder-field replay-calendar-field", children=[
                html.Label("Date", htmlFor="replay-date-open", className="finder-label"),
                dcc.Store(id="replay-date", data=default_date),
                dcc.Store(id="replay-date-min", data=minimum), dcc.Store(id="replay-date-max", data=maximum),
                dcc.Store(id="replay-calendar-state"),
                html.Button("Choose date", id="replay-date-open", **{"aria-haspopup":"dialog", "aria-expanded":False}),
            ]),
            field("Transport", dcc.Dropdown(id="replay-modes", options=[{"label": "Trains", "value": "train"},
                  {"label": "Trams", "value": "tram"}, {"label": "Buses", "value": "bus"}], value=["train"], multi=True, placeholder="All modes"), id="replay-transport-field"),
            field("Flights", dcc.Dropdown(id="replay-flight-scope", options=[{"label": label, "value": value} for label, value in [("Domestic", "domestic"), ("International", "international"), ("Both", "both")]], value="domestic", clearable=False, searchable=False), id="replay-flight-scope-field", style={"display": "none"}),
            field("Route / line", dcc.Dropdown(id="replay-lines", options=metadata["lines"], value=[], multi=True, placeholder="All routes / lines")),
            html.Div(id="replay-flight-controls", className="replay-flight-controls", style={"display": "none"}, children=[
                field("Hub",html.Div(id='replay-flight-hubs',className='replay-hub-buttons'),id='replay-flight-hubs-field',style={'display':'none'}),
                field("Airline / code", dcc.Dropdown(id="replay-carriers", options=[], value=[], multi=True, placeholder="All airlines")),
                field("Airport / code", dcc.Dropdown(id="replay-airports", options=[], value=[], multi=True, placeholder="All airports")),
                field("Airport traffic", dcc.Dropdown(id="replay-airport-direction", options=[{"label": label, "value": value} for label, value in [("Departures", "departures"), ("Arrivals", "arrivals"), ("Both", "both")]], value="both", disabled=True, clearable=False, searchable=False)),
                field("Flight map", dcc.Dropdown(id="replay-flight-view", options=[{"label": "Moving planes", "value": "planes"}, {"label": "Flight frequency", "value": "frequency"}], value="planes", clearable=False, searchable=False)),
                html.Div(id='replay-country-controls',className='replay-country-controls',style={'display':'none'},children=[
                    field('From country',dcc.Dropdown(id='replay-from-countries',options=[],value=[],multi=True,placeholder='All countries')),
                    field('To country',dcc.Dropdown(id='replay-to-countries',options=[],value=[],multi=True,placeholder='All countries')),
                ]),
            ]),
            html.Details(id="replay-more-filters", className="replay-more-filters", children=[
                html.Summary("More filters", id="replay-more-filters-label"),
                html.Div(className="replay-advanced-filters", children=[
                    field("Operator / feed", dcc.Dropdown(id="replay-operators", options=[{"label": label, "value": value}
                          for label, value in CITIES["melbourne"]["operators"]], value=[], multi=True, placeholder="All operators / feeds"), id="replay-generic-operator-field"),
                    field("Direction", dcc.Dropdown(id="replay-directions", options=[{"label": "Train · toward city", "value": "U"},
                          {"label": "Train · away from city", "value": "D"}, {"label": "Tram/bus · direction A", "value": "A"},
                          {"label": "Tram/bus · direction B", "value": "B"}], value=[], multi=True, placeholder="All directions")),
                    field("Services calling at", dcc.Dropdown(id="replay-stations", options=[], value=[], multi=True, placeholder="Any stop or station"), id="replay-generic-station-field"),
                    field("Service number / trip", dcc.Input(id="replay-number", type="search", placeholder="e.g. 6200", value="", debounce=0.3,
                          className="replay-search")),
                ]),
            ]),
        ]),
        html.Div(id="replay-calendar", hidden=True),
        html.Div(id="replay-load-message", role="status", className="replay-load-message"),
        html.Div(className="replay-workspace", children=[
            html.Div(className="replay-map-card", children=[
                html.Div(className="replay-map-wrap", children=[
                    html.Div(className="replay-map-toolbar", children=[
                        html.Div([html.Strong("—", id="replay-active-count"), html.Span(" active services", id="replay-active-label"),
                                  html.Span("", id="replay-matching-count", className="replay-muted"),
                                  html.Span("", id="replay-position-note", className="replay-approximate")], className="replay-map-counts"),
                        html.Div(className="replay-map-actions", children=[
                            html.Button("Departures", id="replay-open-departures", className="finder-chip",
                                        disabled=True, **{"aria-expanded": False, "aria-controls": "replay-departures"}),
                            html.Button("Reset view", id="replay-melbourne", className="finder-chip", title="Return to the Melbourne starting view"),
                            html.Button("Fit selection", id="replay-fit", className="finder-chip", title="Show the full extent of the filtered services"),
                            html.Button("Follow service", id="replay-follow", className="finder-chip", disabled=True,
                                        title="Select a service to follow its position", **{"aria-pressed": False}),
                            html.Button("Filters", id="replay-fullscreen-filters", className="finder-chip replay-fullscreen-filter-button",
                                        **{"aria-expanded": False, "aria-controls": "replay-filter-controls"}),
                            html.Button("Fullscreen", id="replay-fullscreen", className="finder-chip", disabled=True,
                                        **{"aria-pressed": False}),
                            theme_picker("replay-theme-toggle"),
                            language_picker("replay-language-select"),
                        ]),
                    ]),
                    html.P("Thicker lines mean more captured flights that day (both directions). Click a line to explore.", id="replay-frequency-help", className="replay-frequency-help", hidden=True),
                    html.Div(id="replay-map", className="replay-map", role="region", **{"aria-label": "Historical train, tram and bus replay and train passenger demand map"}),
                    html.Details(id="replay-demand-legend", className="replay-demand-legend", hidden=True, open=True,
                               **{"aria-label": "Passenger boarding scale"}, children=[
                        html.Summary(children=[
                            html.Strong("Train station boardings", className="replay-demand-title"),
                            html.Div(id="replay-demand-range", className="replay-muted"),
                            html.Div(id="replay-demand-scale", className="replay-demand-scale"),
                        ]),
                        html.Div(id="replay-demand-total", className="replay-demand-total"),
                        html.Div(id="replay-demand-note", className="replay-muted"),
                        html.Div("Marker colors use this fixed scale. Glow shows nearby concentration.", className="replay-muted"),
                    ]),
                ]),
                html.Div(className="replay-transport", children=[
                    html.Div(className="replay-transport-top", children=[
                        html.Div(className="replay-buttons", children=[
                            html.Button("↺", id="replay-restart", className="replay-icon-button", title="Restart at 03:00", **{"aria-label": "Restart at 03:00"}),
                            html.Button("−1 min", id="replay-back", className="replay-step-button"),
                            html.Button("Play", id="replay-play", className="replay-play-button", disabled=True),
                            html.Button("+1 min", id="replay-forward", className="replay-step-button"),
                        ]),
                        html.Div([html.Time("08:00:00", id="replay-clock"), html.Div("", id="replay-clock-date")], className="replay-clock-wrap"),
                        field("Playback speed", dcc.Dropdown(id="replay-speed", options=[{"label": f"{n:,}×", "value": n} for n in [1, 10, 60, 300, 1000, 2000]],
                              value=60, clearable=False, searchable=False)),
                    ]),
                    html.Div(className="replay-timeline-heading", children=[
                        html.Span("Departures through the day", id="replay-activity-title"), html.Span("Drag to explore"),
                    ]),
                    html.Div(id="replay-timeline", className="replay-timeline"),
                    html.Div([html.Span("03:00", id="replay-range-start"), html.Span("03:00", id="replay-range-end")],
                             id="replay-timeline-labels", className="replay-timeline-labels"),
                ]),
                html.Details(className="replay-options", children=[
                    html.Summary("Map options"),
                    html.Div(className="replay-options-body", children=[
                        html.Div(id="replay-demand-controls", className="replay-demand-controls", children=[
                            html.Div(children=[html.Label("Map view", className="finder-label"),
                                dcc.RadioItems(id="replay-map-mode", options=[{"label": " Vehicles", "value": "trains"},
                                    {"label": " Passenger heatmap", "value": "demand"}, {"label": " Both", "value": "both"}],
                                    value="trains", inline=True, className="replay-map-modes")]),
                            html.Div(id="replay-demand-window-field", hidden=True, children=[
                                field("Boarding window", dcc.Dropdown(id="replay-demand-window", options=[
                                    {"label": f"Last {n} minutes", "value": n} for n in (15, 30, 60)],
                                    value=30, clearable=False, searchable=False)),
                            ]),
                        ]),
                        html.Div(className="replay-map-footer", children=[
                            dcc.Checklist(id="replay-display", options=[{"label": message("Route paths"), "value": "routes"},
                                          {"label": message("Stops & stations"), "value": "stations"},
                                          {"label": message("Size trains by passengers"), "value": "load"}], value=["routes", "stations"], inline=True),
                            html.Span("Estimated positions from scheduled times", className="replay-estimate"),
                            html.Span("Train ···  Tram ··  Bus · — illustrative vehicle size, not carriage counts or occupancy.",
                                      id="replay-vehicle-help", className="replay-estimate"),
                            html.Span("Select a vehicle for details", className="replay-selection-hint replay-muted"),
                            html.Span("Bigger train dots mean more passengers on board. All vehicles grow as you zoom in; passenger sizes stay within readable limits. Click a train for its recorded count.",
                                      id="replay-size-help", className="replay-estimate", hidden=True),
                        ]),
                    ]),
                ]),
            ]),
            html.Aside(className="replay-detail-card", children=[
                html.Div(className="replay-detail-heading", children=[
                    html.Div("YOUR JOURNEY", className="replay-eyebrow"),
                    html.Button("Close", id="replay-close-details", className="finder-chip", hidden=True,
                                **{"aria-label": "Close service details"}),
                ]),
                html.Div(id="replay-departures", hidden=True),
                html.Div(id="replay-details", children=[html.H3("Follow a service"),
                         html.P("Click a moving vehicle to see its journey and scheduled stops.", className="replay-muted"),
                         html.Div("Positions follow scheduled times. Train passenger counts are available; tram and bus counts are unavailable.", className="replay-detail-note")]),
            ]),
        ]),
        html.Details(id="replay-legend", className="replay-legend", open=True, children=[
            html.Summary("Line colours", id="replay-legend-label"),
            html.Div(id="replay-legend-items", className="replay-legend-items"),
        ]),
        html.Div(id="replay-quality", className="replay-quality", role="status"),
        html.P(id="replay-attribution", className="replay-attribution"),
    ])


def register_replay_callbacks(app, metadata):
    app.clientside_callback(ClientsideFunction(namespace="suntrainCalendar", function_name="sync"),
        Output("replay-calendar-state", "data"), Input("replay-date", "data"),
        Input("replay-date-min", "data"), Input("replay-date-max", "data"))
    @app.callback(
        Output("replay-date-min", "data"), Output("replay-date-max", "data"), Output("replay-date", "data"),
        Output("replay-modes", "options"), Output("replay-modes", "value"),
        Output("replay-operators", "options"), Output("replay-operators", "value"),
        Output("replay-directions", "options"), Output("replay-directions", "value"),
        Output("replay-lines", "value"), Output("replay-stations", "value"), Output("replay-number", "value"),
        Output("replay-description", "children"), Output("replay-period", "children"),
        Output("replay-melbourne", "children"), Output("replay-melbourne", "title"),
        Output("replay-demand-controls", "style"), Output("replay-map-mode", "value"),
        Output("replay-display", "options"), Output("replay-display", "value"),
        Output("replay-transport-field", "style"), Output("replay-flight-scope-field", "style"),
        Output("replay-flight-scope", "value"),
        Output("replay-flight-controls", "style"), Output("replay-carriers", "value"), Output("replay-airports", "value"), Output("replay-flight-view", "value"), Output("replay-airport-direction", "value"),
        Output("replay-generic-operator-field", "style"), Output("replay-generic-station-field", "style"),
        Output('replay-from-countries','value'),Output('replay-to-countries','value'),
        Input("replay-city", "value"), State("replay-date", "data"))
    def configure_city(city, current_date):
        settings = city_settings(city)
        if city != "melbourne":
            minimum, maximum = settings["start_date"], settings["end_date"]
        else:
            coverage = available_range()
            shared = coverage and metadata["min_date"] <= coverage[0] and metadata["max_date"] >= coverage[1]
            minimum, maximum = coverage if shared else (metadata["min_date"], metadata["max_date"])
        chosen = current_date if current_date and minimum <= current_date <= maximum else minimum
        options = lambda key: [{"label": message(label), "value": value} for label, value in settings[key]]
        badge = period_label(minimum, maximum)
        return (minimum, maximum, chosen, options("modes"), settings.get("default_modes", []), options("operators"), [], options("directions"), [], [], [], "",
                message(settings["description"]), badge, message("Reset view"), f"Return to the {settings['name']} starting view",
                {} if settings["passenger_data"] else {"display": "none"}, "trains",
                [{"label": message("Airport connections" if city_settings(city).get('replay_kind') == 'flights' else "Route paths"), "value": "routes"}, {"label": message("Airports" if city_settings(city).get('replay_kind') == 'flights' else "Stops & stations"), "value": "stations"}] +
                ([{"label": message("Size trains by passengers"), "value": "load"}] if settings["passenger_data"] else []),
                ["routes", "stations"],
                {"display": "none"} if settings.get('replay_kind')=='flights' else {},
                {} if settings.get("flight_scopes") else {"display": "none"}, "both" if settings.get('flight_hubs') or settings.get('flight_country_filters') else "domestic",
                {} if settings.get("replay_kind") == "flights" else {"display": "none"}, [], [settings['default_airport']] if settings.get('default_airport') else [], "planes", "both",
                {"display": "none"} if settings.get("replay_kind") == "flights" else {},
                {"display": "none"} if settings.get("replay_kind") == "flights" else {},[],[])

    app.clientside_callback(
        """function(operators, directions, stations, number) {
            const count = [operators, directions, stations].filter(values => values && values.length).length
                + Number(Boolean(number && number.trim()));
            const text = count ? `More filters (${count})` : 'More filters';
            return {namespace:'dash_html_components',type:'Span',props:{children:window.suntrainI18n.translate(text),'data-l10n':text}};
        }""",
        Output("replay-more-filters-label", "children"),
        Input("replay-operators", "value"), Input("replay-directions", "value"),
        Input("replay-stations", "value"), Input("replay-number", "value"),
    )

    def load_replay_day(business_date, active_tab, city, current, modes=None):
        if active_tab not in ("replay", "overview") or not business_date:
            raise PreventUpdate
        settings = city_settings(city)
        if city != "melbourne" and not settings["start_date"] <= business_date <= settings["end_date"]:
            raise PreventUpdate  # The city callback will choose a supported date.
        if city == "melbourne" and not metadata["min_date"] <= business_date <= metadata["max_date"]:
            raise PreventUpdate
        chosen = selected_modes(city, modes)
        if current and not current.get("error") and current.get("business_date") == business_date and current.get("city", "melbourne") == city and current.get("modes") == list(chosen):
            raise PreventUpdate
        try:
            return descriptor(business_date, city, chosen), ""
        except Exception:
            LOGGER.exception("Could not load train replay for %s", business_date)
            return {"business_date": business_date, "city": city, "error": True}, "Could not load this day. Choose another date, or return to this tab to retry."

    @app.callback(Output("replay-day", "data"), Output("replay-load-message", "children"),
                  Input("replay-date", "data"), Input("view-tabs", "value"), Input("replay-city", "value"),
                  Input("replay-modes", "value"), State("replay-client-state", "data"))
    def load_selected_modes(business_date, active_tab, city, modes, current):
        # A city change arrives before its new mode defaults. Open rail first.
        chosen = None if ctx.triggered_id == "replay-city" else modes
        return load_replay_day(business_date, active_tab, city, current, chosen)

    app.clientside_callback(
        ClientsideFunction(namespace="suntrainReplay", function_name="sync"),
        Output("replay-client-state", "data"),
        Input("replay-day", "data"), Input("view-tabs", "value"), Input("replay-date", "data"),
        Input("replay-modes", "value"), Input("replay-operators", "value"), Input("replay-lines", "value"), Input("replay-directions", "value"),
        Input("replay-stations", "value"), Input("replay-number", "value"), Input("replay-display", "value"),
        Input("replay-map-mode", "value"), Input("replay-demand-window", "value"),
        Input("replay-speed", "value"), Input("replay-play", "n_clicks"), Input("replay-restart", "n_clicks"),
        Input("replay-back", "n_clicks"), Input("replay-forward", "n_clicks"), Input("replay-fit", "n_clicks"),
        Input("replay-city", "value"), Input("replay-flight-scope", "value"),
        Input("replay-carriers", "value"), Input("replay-airports", "value"), Input("replay-flight-view", "value"), Input("replay-airport-direction", "value"),
        Input('replay-from-countries','value'),Input('replay-to-countries','value'),
    )
    return load_replay_day
