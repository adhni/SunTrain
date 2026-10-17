"""Dash controls for the browser-owned historical replay."""
from __future__ import annotations

import logging
from datetime import date

from dash import ClientsideFunction, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from dashboard.replay import get_replay_day
from dashboard.transit import available_range

LOGGER = logging.getLogger(__name__)


def field(label, control):
    return html.Div([html.Label(label, htmlFor=control.id, className="finder-label"), control], className="finder-field")


def build_replay_panel(metadata, default_date):
    coverage = available_range()
    shared_period = coverage and metadata["min_date"] <= coverage[0] and metadata["max_date"] >= coverage[1]
    minimum, maximum = coverage if shared_period else (metadata["min_date"], metadata["max_date"])
    default_date = minimum if shared_period else default_date
    badge = f"{date.fromisoformat(minimum):%d %b}–{date.fromisoformat(maximum):%d %b %Y}" if shared_period else "Historical · FY 2023–24"
    return html.Div(id="replay-panel", className="tab-panel replay-panel", style={"display": "block"}, tabIndex=-1, children=[
        dcc.Store(id="replay-day", storage_type="memory"),
        dcc.Store(id="replay-client-state", storage_type="memory"),
        html.Div(className="replay-heading", children=[
            html.Div([html.Div("THE NETWORK IN MOTION", className="replay-eyebrow"),
                      html.H2("Transport Replay"), html.P("Trains, trams and buses on one moving map. Passenger data is available for trains only.")]),
            html.Span(badge, className="replay-badge"),
        ]),
        html.Div(id="replay-filter-controls", className="replay-filters", children=[
            field("Business date", dcc.DatePickerSingle(id="replay-date", date=default_date,
                  min_date_allowed=minimum, max_date_allowed=maximum,
                  display_format="DD MMM YYYY", first_day_of_week=1, clearable=False)),
            field("Transport", dcc.Dropdown(id="replay-modes", options=[{"label": "Trains", "value": "train"},
                  {"label": "Trams", "value": "tram"}, {"label": "Buses", "value": "bus"}], value=[], multi=True, placeholder="All modes")),
            field("Operator / feed", dcc.Dropdown(id="replay-operators", options=[{"label": "Metro", "value": "Metro"},
                  {"label": "V/Line", "value": "VLine"}, {"label": "PTV tram", "value": "PTV tram"},
                  {"label": "PTV bus", "value": "PTV bus"}], value=[], multi=True, placeholder="All operators / feeds")),
            field("Lines", dcc.Dropdown(id="replay-lines", options=metadata["lines"], value=[], multi=True, placeholder="All lines")),
            field("Direction", dcc.Dropdown(id="replay-directions", options=[{"label": "Train · toward city", "value": "U"},
                  {"label": "Train · away from city", "value": "D"}, {"label": "Tram/bus · direction A", "value": "A"},
                  {"label": "Tram/bus · direction B", "value": "B"}], value=[], multi=True, placeholder="All directions")),
            field("Services calling at", dcc.Dropdown(id="replay-stations", options=[], value=[], multi=True, placeholder="Any stop or station")),
            field("Service number / trip", dcc.Input(id="replay-number", type="search", placeholder="e.g. 6200", value="", debounce=0.3,
                  className="replay-search")),
        ]),
        html.Div(id="replay-load-message", role="status", className="replay-load-message"),
        html.Div(className="replay-workspace", children=[
            html.Div(className="replay-map-card", children=[
                html.Div(className="replay-map-toolbar", children=[
                    html.Div([html.Strong("—", id="replay-active-count"), html.Span(" active services"),
                              html.Span("", id="replay-matching-count", className="replay-muted"),
                              html.Span("", id="replay-position-note", className="replay-approximate")]),
                    html.Div(className="replay-map-actions", children=[
                        html.Button("Melbourne", id="replay-melbourne", className="finder-chip", title="Return to metropolitan Melbourne"),
                        html.Button("Fit selection", id="replay-fit", className="finder-chip", title="Show the full extent of the filtered services"),
                        html.Button("Follow service", id="replay-follow", className="finder-chip", disabled=True,
                                    title="Select a service to follow its position", **{"aria-pressed": False}),
                        html.Button("Filters", id="replay-fullscreen-filters", className="finder-chip replay-fullscreen-filter-button",
                                    **{"aria-expanded": False, "aria-controls": "replay-filter-controls"}),
                        html.Button("Fullscreen", id="replay-fullscreen", className="finder-chip", disabled=True,
                                    **{"aria-pressed": False}),
                        html.Button("Dark mode", id="replay-theme-toggle", className="finder-chip theme-toggle",
                                    **{"data-theme-toggle": "true", "aria-pressed": False}),
                    ]),
                ]),
                html.Div(className="replay-map-wrap", children=[
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
                html.Div(className="replay-demand-controls", children=[
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
                    dcc.Checklist(id="replay-display", options=[{"label": " Route paths", "value": "routes"},
                                  {"label": " Stops & stations", "value": "stations"},
                                  {"label": " Size trains by passengers", "value": "load"}], value=["routes", "stations"], inline=True),
                    html.Span("Estimated positions from scheduled times", className="replay-estimate"),
                    html.Span("Bigger train dots mean more passengers on board. All vehicles grow as you zoom in; passenger sizes stay within readable limits. Click a train for its recorded count.",
                              id="replay-size-help", className="replay-estimate", hidden=True),
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
                    html.Div(id="replay-timeline", className="replay-timeline"),
                    html.Div([html.Span("03:00", id="replay-range-start"), html.Span("03:00 next day", id="replay-range-end")], className="replay-timeline-labels"),
                ]),
            ]),
            html.Aside(className="replay-detail-card", children=[
                html.Div(className="replay-detail-heading", children=[
                    html.Div("SERVICE DETAILS", className="replay-eyebrow"),
                    html.Button("Close", id="replay-close-details", className="finder-chip", hidden=True,
                                **{"aria-label": "Close service details"}),
                ]),
                html.Div(id="replay-details", children=[html.H3("Follow a service"),
                         html.P("Click a moving vehicle to see its journey and scheduled stops.", className="replay-muted"),
                         html.Div("Positions follow scheduled times. Train passenger counts are available; tram and bus counts are unavailable.", className="replay-detail-note")]),
            ]),
        ]),
        html.Div(id="replay-legend", className="replay-legend", **{"aria-label": "Line colors"}),
        html.Div(id="replay-quality", className="replay-quality", role="status"),
        html.P(id="replay-attribution", className="replay-attribution"),
    ])


def register_replay_callbacks(app):
    @app.callback(Output("replay-day", "data"), Output("replay-load-message", "children"),
                  Input("replay-date", "date"), Input("view-tabs", "value"), State("replay-client-state", "data"))
    def load_replay_day(business_date, active_tab, current):
        if active_tab != "replay" or not business_date:
            raise PreventUpdate
        if current and not current.get("error") and current.get("business_date") == business_date:
            raise PreventUpdate
        try:
            return get_replay_day(business_date), ""
        except Exception:
            LOGGER.exception("Could not load train replay for %s", business_date)
            return {"business_date": business_date, "error": True}, "Could not load this day. Choose another date, or return to this tab to retry."

    app.clientside_callback(
        ClientsideFunction(namespace="suntrainReplay", function_name="sync"),
        Output("replay-client-state", "data"),
        Input("replay-day", "data"), Input("view-tabs", "value"), Input("replay-date", "date"),
        Input("replay-modes", "value"), Input("replay-operators", "value"), Input("replay-lines", "value"), Input("replay-directions", "value"),
        Input("replay-stations", "value"), Input("replay-number", "value"), Input("replay-display", "value"),
        Input("replay-map-mode", "value"), Input("replay-demand-window", "value"),
        Input("replay-speed", "value"), Input("replay-play", "n_clicks"), Input("replay-restart", "n_clicks"),
        Input("replay-back", "n_clicks"), Input("replay-forward", "n_clicks"), Input("replay-fit", "n_clicks"),
    )
    return load_replay_day
