"""Dash controls for the browser-owned historical replay."""
from __future__ import annotations

import logging

from dash import ClientsideFunction, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from dashboard.replay import get_replay_day

LOGGER = logging.getLogger(__name__)


def field(label, control):
    return html.Div([html.Label(label, htmlFor=control.id, className="finder-label"), control], className="finder-field")


def build_replay_panel(metadata, default_date):
    return html.Div(id="replay-panel", className="tab-panel replay-panel", style={"display": "block"}, tabIndex=-1, children=[
        dcc.Store(id="replay-day", storage_type="memory"),
        dcc.Store(id="replay-client-state", storage_type="memory"),
        html.Div(className="replay-heading", children=[
            html.Div([html.Div("THE NETWORK IN MOTION", className="replay-eyebrow"),
                      html.H2("Train Replay"), html.P("Explore a day on Victoria’s railway network.")]),
            html.Span("Historical · FY 2023–24", className="replay-badge"),
        ]),
        html.Div(id="replay-filter-controls", className="replay-filters", children=[
            field("Business date", dcc.DatePickerSingle(id="replay-date", date=default_date,
                  min_date_allowed=metadata["min_date"], max_date_allowed=metadata["max_date"],
                  display_format="DD MMM YYYY", first_day_of_week=1, clearable=False)),
            field("Operator", dcc.Dropdown(id="replay-operators", options=[{"label": "Metro", "value": "Metro"},
                  {"label": "V/Line", "value": "VLine"}], value=[], multi=True, placeholder="All operators")),
            field("Lines", dcc.Dropdown(id="replay-lines", options=metadata["lines"], value=[], multi=True, placeholder="All lines")),
            field("Direction", dcc.Dropdown(id="replay-directions", options=[{"label": "Toward city", "value": "U"},
                  {"label": "Away from city", "value": "D"}], value=[], multi=True, placeholder="Both directions")),
            field("Services calling at", dcc.Dropdown(id="replay-stations", options=[], value=[], multi=True, placeholder="Any station")),
            field("Train number", dcc.Input(id="replay-number", type="search", placeholder="e.g. 6200", value="", debounce=0.3,
                  className="replay-search")),
        ]),
        html.Div(id="replay-load-message", role="status", className="replay-load-message"),
        html.Div(className="replay-workspace", children=[
            html.Div(className="replay-map-card", children=[
                html.Div(className="replay-map-toolbar", children=[
                    html.Div([html.Strong("—", id="replay-active-count"), html.Span(" active trains"),
                              html.Span("", id="replay-matching-count", className="replay-muted"),
                              html.Span("", id="replay-position-note", className="replay-approximate")]),
                    html.Div(className="replay-map-actions", children=[
                        html.Button("Melbourne", id="replay-melbourne", className="finder-chip", title="Return to metropolitan Melbourne"),
                        html.Button("Fit selection", id="replay-fit", className="finder-chip", title="Show the full extent of the filtered services"),
                        html.Button("Follow train", id="replay-follow", className="finder-chip", disabled=True,
                                    title="Select a train to follow its position", **{"aria-pressed": False}),
                        html.Button("Filters", id="replay-fullscreen-filters", className="finder-chip replay-fullscreen-filter-button",
                                    **{"aria-expanded": False, "aria-controls": "replay-filter-controls"}),
                        html.Button("Fullscreen", id="replay-fullscreen", className="finder-chip", disabled=True,
                                    **{"aria-pressed": False}),
                        html.Button("Dark mode", id="replay-theme-toggle", className="finder-chip theme-toggle",
                                    **{"data-theme-toggle": "true", "aria-pressed": False}),
                    ]),
                ]),
                html.Div(id="replay-map", className="replay-map", role="region", **{"aria-label": "Historical train replay map"}),
                html.Div(className="replay-map-footer", children=[
                    dcc.Checklist(id="replay-display", options=[{"label": " Railway paths", "value": "routes"},
                                  {"label": " Stations", "value": "stations"},
                                  {"label": " Size by passengers", "value": "load"}], value=["routes", "stations"], inline=True),
                    html.Span("Estimated positions from scheduled times", className="replay-estimate"),
                    html.Span("Bigger dots mean more passengers on board. Sizes are scaled for readability; click a train for its recorded count.",
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
                                **{"aria-label": "Close train details"}),
                ]),
                html.Div(id="replay-details", children=[html.H3("Follow a train"),
                         html.P("Click a moving train to see its journey, scheduled stops and passenger counts.", className="replay-muted"),
                         html.Div("Every dot is a recorded service. Movement between its stops is estimated from the timetable.", className="replay-detail-note")]),
            ]),
        ]),
        html.Div(id="replay-legend", className="replay-legend", **{"aria-label": "Line colors"}),
        html.Div(id="replay-quality", className="replay-quality", role="status"),
        html.P(id="replay-attribution", className="replay-attribution"),
    ])


def register_replay_callbacks(app):
    @app.callback(Output("replay-day", "data"), Output("replay-load-message", "children"),
                  Input("replay-date", "date"), Input("view-tabs", "value"), State("replay-day", "data"))
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
        Input("replay-operators", "value"), Input("replay-lines", "value"), Input("replay-directions", "value"),
        Input("replay-stations", "value"), Input("replay-number", "value"), Input("replay-display", "value"),
        Input("replay-speed", "value"), Input("replay-play", "n_clicks"), Input("replay-restart", "n_clicks"),
        Input("replay-back", "n_clicks"), Input("replay-forward", "n_clicks"), Input("replay-fit", "n_clicks"),
    )
    return load_replay_day
