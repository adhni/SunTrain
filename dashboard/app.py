from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from flask import jsonify
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.data import (
    get_direction_flow,
    get_filter_state,
    get_filtered_export,
    get_hourly_activity,
    get_kpis,
    get_line_capacity_summary,
    get_line_paths,
    get_metadata,
    get_origin_departure_activity,
    get_peak_trains,
    get_preview_rows,
    get_service_patterns,
    get_service_summary,
    get_station_activity,
    get_station_map_data,
    get_station_options,
)


META = get_metadata()
DEFAULT_START = "2023-07-10" if META["min_date"] <= "2023-07-10" <= META["max_date"] else META["min_date"]
DEFAULT_END = DEFAULT_START
ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "ink": "#1b2432",
    "paper": "#f6f1e8",
    "card": "rgba(255, 249, 240, 0.82)",
    "card_strong": "#fffaf2",
    "accent": "#d96c06",
    "accent_soft": "#ffd8a8",
    "teal": "#0f766e",
    "berry": "#b4235f",
    "grid": "#d8c8b2",
    "olive": "#6b7a18",
}
HOUR_OPTIONS = [{"label": f"{hour:02d}:00", "value": hour} for hour in range(24)]
MORNING_PEAK_HOURS = [7, 8, 9]
AFTERNOON_PEAK_HOURS = [16, 17, 18]
COMMUTER_DAY_TYPES = ["Normal Weekday"]

app = Dash(
    __name__,
    title="SunTrain Dashboard",
    assets_folder=str(ROOT / "assets"),
)
server = app.server


@server.get("/health")
def health():
    return jsonify({"status": "ok", "app": "suntrain-dashboard"})


def metric_card(title: str, subtitle: str, value_id: str) -> html.Div:
    return html.Div(
        className="metric-card",
        children=[
            html.Div(title, className="metric-label"),
            html.Div(id=value_id, className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


def section_title(title: str, note: str) -> html.Div:
    return html.Div(
        className="section-heading",
        children=[
            html.Div(title, className="section-title"),
            html.Div(note, className="section-note"),
        ],
    )


def build_empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=48, b=20),
        font=dict(color=COLORS["ink"]),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="No data for the current filter selection",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14),
            )
        ],
    )
    return fig


def build_error_figure(title: str, message: str) -> go.Figure:
    fig = build_empty_figure(title)
    fig.update_layout(
        annotations=[
            dict(
                text=f"Could not load this view.<br><span style='font-size:12px'>{message}</span>",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14),
            )
        ]
    )
    return fig


def format_count(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def parse_iso(value: str) -> date:
    return datetime.fromisoformat(value).date()


def tab_style(active: bool) -> dict[str, str]:
    return {"display": "block" if active else "none"}


def map_zoom_for_bounds(lat_span: float, lon_span: float) -> float:
    span = max(lat_span, lon_span)
    if span > 12:
        return 3.2
    if span > 6:
        return 4.3
    if span > 3:
        return 5.2
    if span > 1.2:
        return 7
    if span > 0.6:
        return 8.2
    if span > 0.3:
        return 9.3
    if span > 0.15:
        return 10.4
    return 11.4


def serialize_filters(start_date, end_date, day_types, lines, groups, directions, stations, hours) -> dict[str, object]:
    return {
        "start_date": start_date,
        "end_date": end_date,
        "day_types": day_types or [],
        "lines": lines or [],
        "groups": groups or [],
        "directions": directions or [],
        "stations": stations or [],
        "hours": hours or [],
    }


def deserialize_filters(data: dict[str, object]) -> tuple[dict[str, object], object]:
    payload = data or serialize_filters(DEFAULT_START, DEFAULT_END, [], [], [], [], [], [])
    filters = get_filter_state(
        payload["start_date"],
        payload["end_date"],
        payload.get("day_types"),
        payload.get("lines"),
        payload.get("groups"),
        payload.get("directions"),
        payload.get("stations"),
        payload.get("hours"),
    )
    return payload, filters


app.layout = html.Div(
    className="page-shell",
    children=[
        html.A("Skip to dashboard", href="#main-content", className="skip-link"),
        html.Div(className="page-glow page-glow-a"),
        html.Div(className="page-glow page-glow-b"),
        dcc.Download(id="download-data"),
        dcc.Store(
            id="filter-store",
            data=serialize_filters(DEFAULT_START, DEFAULT_END, [], [], [], [], [], []),
        ),
        html.Main(
            id="main-content",
            className="app",
            children=[
                html.Section(
                    className="hero",
                    children=[
                        html.Div(
                            className="hero-copy",
                            children=[
                                html.P("Victorian Train Service Passenger Counts", className="eyebrow"),
                                html.H1("Passenger demand, services, and stop patterns"),
                                html.P(
                                    "Explore every recorded service-stop entry across the full FY 2023-2024 warehouse. "
                                    "Start with one day on one line, then widen out to compare stations, service patterns, and demand by origin departure time."
                                ),
                                html.Div(
                                    className="hero-meta",
                                    children=[
                                        html.Div("Warehouse-backed", className="hero-pill"),
                                        html.Div("Multi-day ready", className="hero-pill"),
                                        html.Div("HH:MM time formatting", className="hero-pill"),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="finder-shell",
                            children=[
                                html.Div(
                                    className="finder-grid",
                                    children=[
                                        html.Div(
                                            className="finder-fields",
                                            children=[
                                                html.Div(
                                                    className="finder-field finder-field-wide",
                                                    children=[
                                                        html.Label("Business Date Range", className="finder-label"),
                                                        dcc.DatePickerRange(
                                                            id="date-range",
                                                            min_date_allowed=META["min_date"],
                                                            max_date_allowed=META["max_date"],
                                                            start_date=DEFAULT_START,
                                                            end_date=DEFAULT_END,
                                                            display_format="YYYY-MM-DD",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Day Type", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="day-type-filter",
                                                            options=[
                                                                {"label": day_type, "value": day_type}
                                                                for day_type in META["day_types"]
                                                            ],
                                                            value=[],
                                                            multi=True,
                                                            placeholder="All day types",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Lines", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="line-filter",
                                                            options=[{"label": line, "value": line} for line in META["lines"]],
                                                            value=[],
                                                            multi=True,
                                                            placeholder="Select line(s)",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Groups", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="group-filter",
                                                            options=[{"label": group, "value": group} for group in META["groups"]],
                                                            value=[],
                                                            multi=True,
                                                            placeholder="All groups",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Directions", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="direction-filter",
                                                            options=[
                                                                {"label": "Up (toward city)", "value": "U"},
                                                                {"label": "Down (away from city)", "value": "D"},
                                                            ],
                                                            value=[],
                                                            multi=True,
                                                            placeholder="All directions",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Stations", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="station-filter",
                                                            options=[],
                                                            value=[],
                                                            multi=True,
                                                            placeholder="All stations in current selection",
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    className="finder-field",
                                                    children=[
                                                        html.Label("Hours", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="hour-filter",
                                                            options=HOUR_OPTIONS,
                                                            value=[],
                                                            multi=True,
                                                            placeholder="All hours",
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            className="finder-actions",
                                            children=[
                                                html.Button("1 Day", id="preset-one-day", className="finder-chip"),
                                                html.Button("1 Week", id="preset-one-week", className="finder-chip"),
                                                html.Button("Full FY", id="preset-full-range", className="finder-chip"),
                                                html.Button("Morning Peak", id="preset-morning-peak", className="finder-chip"),
                                                html.Button("Afternoon Peak", id="preset-afternoon-peak", className="finder-chip"),
                                                html.Button("Weekday All-Day", id="preset-weekday-all-day", className="finder-chip"),
                                                html.Button("Weekday AM Inbound", id="preset-weekday-am-inbound", className="finder-chip"),
                                                html.Button("Weekday PM Outbound", id="preset-weekday-pm-outbound", className="finder-chip"),
                                                html.Button("Reset Filters", id="reset-filters", className="finder-chip"),
                                                html.Button("Download CSV", id="download-button", className="primary-button"),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="finder-support",
                                    children=[
                                        html.Div(
                                            className="finder-panel",
                                            children=[
                                                html.H3("How to read this"),
                                                html.P(
                                                    "The new origin-departure chart groups each train by its first scheduled departure time in the filtered window, while the stop-level chart keeps the familiar per-stop activity view."
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            className="finder-panel",
                                            children=[
                                                html.H3("Direction guide"),
                                                html.P("U = toward Flinders Street. D = away from Flinders Street."),
                                            ],
                                        ),
                                        html.Div(
                                            className="finder-panel",
                                            children=[
                                                html.H3("Commuter presets"),
                                                html.P("Weekday AM inbound uses `Normal Weekday`, `U`, and `07:00-09:59`. Weekday PM outbound uses `Normal Weekday`, `D`, and `16:00-18:59`."),
                                            ],
                                        ),
                                        html.Div(
                                            className="finder-panel",
                                            children=[
                                                html.H3("Current focus"),
                                                html.P(id="selection-summary"),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Section(
                    className="status-banner",
                    children=[
                        html.Div(id="status-message", className="status-message"),
                        html.Div(
                            className="status-grid",
                            children=[
                                metric_card("Recorded Stops", "Rows in the filtered stop-level dataset", "metric-stop-rows"),
                                metric_card("Train Services", "Distinct train runs in the current selection", "metric-services"),
                                metric_card("Stations Served", "Distinct stations touched by the filter", "metric-stations"),
                                metric_card("Business Dates", "How many business dates are in view", "metric-days"),
                                metric_card("Total Boardings", "Rounded boardings summed across filtered rows", "metric-boardings"),
                                metric_card("Peak Onboard Load", "Highest departure load observed", "metric-peak-load"),
                            ],
                        ),
                    ],
                ),
                dcc.Tabs(
                    id="view-tabs",
                    value="overview",
                    className="view-tabs",
                    children=[
                        dcc.Tab(label="Overview", value="overview"),
                        dcc.Tab(label="Lines", value="lines"),
                        dcc.Tab(label="Stations", value="stations"),
                        dcc.Tab(label="Map", value="map"),
                        dcc.Tab(label="Services", value="services"),
                        dcc.Tab(label="Explore Rows", value="rows"),
                    ],
                ),
                html.Div(
                    id="overview-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Demand Through the Day",
                            "The left chart groups services by each train's first recorded departure time. The right chart keeps the familiar stop-level hourly activity.",
                        ),
                        html.Div(
                            className="viz-grid viz-grid-two",
                            children=[
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Services by Origin Departure Hour"),
                                        dcc.Loading(dcc.Graph(id="origin-hour-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Stop-Level Activity by Scheduled Departure Hour"),
                                        dcc.Loading(dcc.Graph(id="stop-hour-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="viz-grid",
                            children=[
                                html.Div(
                                    className="viz-card viz-card-full",
                                    children=[
                                        html.Div(className="viz-title", children="Weekday Commuter Split by Line"),
                                        dcc.Loading(dcc.Graph(id="line-commuter-split-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="viz-grid viz-grid-two",
                            children=[
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Direction Mix"),
                                        dcc.Loading(dcc.Graph(id="direction-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Service Stop Pattern Mix"),
                                        dcc.Loading(dcc.Graph(id="pattern-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="lines-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Line Demand and Capacity Signals",
                            "These charts compare train lines using service-level metrics. Read average boardings as demand captured by a service, and average peak load as the busiest onboard load observed on that service.",
                        ),
                        html.Div(
                            className="viz-grid viz-grid-two",
                            children=[
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Average Boardings per Service by Line"),
                                        dcc.Loading(dcc.Graph(id="line-boardings-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Demand vs Peak Load by Line"),
                                        dcc.Loading(dcc.Graph(id="line-capacity-scatter", config={"displayModeBar": False})),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="viz-grid viz-grid-two",
                            children=[
                                html.Div(
                                    className="table-card compact-card",
                                    children=[
                                        html.Div(className="viz-title", children="Line Summary"),
                                        dcc.Loading(
                                            dash_table.DataTable(
                                                id="line-summary-table",
                                                page_size=15,
                                                sort_action="native",
                                                style_table={"overflowX": "auto"},
                                                style_header={"backgroundColor": COLORS["ink"], "color": "#fffdf9", "border": "none"},
                                                style_cell={
                                                    "backgroundColor": "transparent",
                                                    "color": COLORS["ink"],
                                                    "borderBottom": f"1px solid {COLORS['grid']}",
                                                    "padding": "10px 12px",
                                                    "fontFamily": "'Avenir Next', 'Segoe UI', sans-serif",
                                                    "fontSize": "13px",
                                                    "textAlign": "left",
                                                },
                                            )
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card nuance-card",
                                    children=[
                                        html.Div(className="viz-title", children="How to Read This"),
                                        html.Div(
                                            className="nuance-copy",
                                            children=[
                                                html.P(
                                                    "Average boardings per service is a demand metric. It tells you how many passengers boarded the typical service on a line during the filtered window."
                                                ),
                                                html.P(
                                                    "Average peak load per service is the stronger crowding proxy. It looks at the busiest onboard moment of each service, then averages those peaks by line."
                                                ),
                                                html.P(
                                                    "The commuter split chart below compares two fixed slices side by side: weekday AM inbound (`U`, `07:00-09:59`) and weekday PM outbound (`D`, `16:00-18:59`). It respects your current date range and line, group, and station scope."
                                                ),
                                                html.P(
                                                    "These are not literal train capacities. The source dataset rounds passenger counts to the nearest 10 and does not include rolling-stock capacity, so load factor needs a separate train-capacity lookup."
                                                ),
                                                html.P(
                                                    "Some values in `Line_Name` behave more like corridor or operating group labels than simple passenger lines. Treat those as network buckets unless you explicitly want that broader grouping."
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="stations-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Stations",
                            "Compare stations by demand and focus the selection before jumping into the full map view.",
                        ),
                        html.Div(
                            className="viz-grid",
                            children=[
                                html.Div(
                                    className="viz-card viz-card-full",
                                    children=[
                                        html.Div(className="viz-title", children="Top Station Activity"),
                                        dcc.Loading(dcc.Graph(id="station-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="map-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Network Map",
                            "A dedicated station map with route traces, visible station markers, and click-to-filter behavior.",
                        ),
                        html.Div(
                            className="viz-card map-card",
                            children=[
                                html.Div(className="viz-title", children="Interactive Station Map"),
                                dcc.Loading(dcc.Graph(id="station-map-graph", config={"displayModeBar": False})),
                            ],
                        ),
                        html.Div(
                            className="table-card",
                            children=[
                                html.Div(className="viz-title", children="Stations in Current Map View"),
                                dcc.Loading(
                                    dash_table.DataTable(
                                        id="map-station-table",
                                        page_size=12,
                                        sort_action="native",
                                        style_table={"overflowX": "auto"},
                                        style_header={"backgroundColor": COLORS["ink"], "color": "#fffdf9", "border": "none"},
                                        style_cell={
                                            "backgroundColor": "transparent",
                                            "color": COLORS["ink"],
                                            "borderBottom": f"1px solid {COLORS['grid']}",
                                            "padding": "10px 12px",
                                            "fontFamily": "'Avenir Next', 'Segoe UI', sans-serif",
                                            "fontSize": "13px",
                                            "textAlign": "left",
                                        },
                                    )
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="services-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Services",
                            "Spot the heaviest services and review origin-to-destination summaries with first departure times in HH:MM.",
                        ),
                        html.Div(
                            className="viz-grid viz-grid-two",
                            children=[
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Peak Load by Service"),
                                        dcc.Loading(dcc.Graph(id="peak-train-graph", config={"displayModeBar": False})),
                                    ],
                                ),
                                html.Div(
                                    className="table-card compact-card",
                                    children=[
                                        html.Div(className="viz-title", children="Service Summary"),
                                        dcc.Loading(
                                            dash_table.DataTable(
                                                id="service-table",
                                                page_size=10,
                                                sort_action="native",
                                                style_table={"overflowX": "auto"},
                                                style_header={"backgroundColor": COLORS["ink"], "color": "#fffdf9", "border": "none"},
                                                style_cell={
                                                    "backgroundColor": "transparent",
                                                    "color": COLORS["ink"],
                                                    "borderBottom": f"1px solid {COLORS['grid']}",
                                                    "padding": "10px 12px",
                                                    "fontFamily": "'Avenir Next', 'Segoe UI', sans-serif",
                                                    "fontSize": "13px",
                                                    "textAlign": "left",
                                                },
                                            )
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id="rows-panel",
                    className="tab-panel",
                    children=[
                        section_title(
                            "Explore Raw Rows",
                            "Useful when you need to inspect actual stop-level records with cleaner HH:MM times.",
                        ),
                        html.Div(
                            className="table-toolbar",
                            children=[
                                html.Div("Rows per page", className="toolbar-label"),
                                dcc.Dropdown(
                                    id="preview-row-count",
                                    options=[{"label": str(n), "value": n} for n in (10, 20, 30, 40, 50)],
                                    value=20,
                                    clearable=False,
                                    searchable=False,
                                    className="page-size-dropdown",
                                ),
                            ],
                        ),
                        html.Div(
                            className="table-card",
                            children=[
                                html.Div(className="viz-title", children="Preview Rows"),
                                dcc.Loading(
                                    dash_table.DataTable(
                                        id="preview-table",
                                        page_size=20,
                                        sort_action="native",
                                        filter_action="native",
                                        fixed_rows={"headers": True},
                                        style_table={"overflowX": "auto", "maxHeight": "680px"},
                                        style_header={"backgroundColor": COLORS["ink"], "color": "#fffdf9", "border": "none"},
                                        style_cell={
                                            "backgroundColor": "transparent",
                                            "color": COLORS["ink"],
                                            "borderBottom": f"1px solid {COLORS['grid']}",
                                            "padding": "10px 12px",
                                            "fontFamily": "'Avenir Next', 'Segoe UI', sans-serif",
                                            "fontSize": "13px",
                                            "textAlign": "left",
                                            "minWidth": "110px",
                                            "width": "110px",
                                            "maxWidth": "220px",
                                        },
                                    )
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)
@app.callback(
    Output("filter-store", "data"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("day-type-filter", "value"),
    Input("line-filter", "value"),
    Input("group-filter", "value"),
    Input("direction-filter", "value"),
    Input("station-filter", "value"),
    Input("hour-filter", "value"),
)
def sync_filter_store(start_date, end_date, day_types, lines, groups, directions, stations, hours):
    return serialize_filters(start_date, end_date, day_types, lines, groups, directions, stations, hours)


@app.callback(
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
    Output("day-type-filter", "value"),
    Output("line-filter", "value"),
    Output("group-filter", "value"),
    Output("direction-filter", "value"),
    Output("station-filter", "value"),
    Output("hour-filter", "value"),
    Input("preset-one-day", "n_clicks"),
    Input("preset-one-week", "n_clicks"),
    Input("preset-full-range", "n_clicks"),
    Input("preset-morning-peak", "n_clicks"),
    Input("preset-afternoon-peak", "n_clicks"),
    Input("preset-weekday-all-day", "n_clicks"),
    Input("preset-weekday-am-inbound", "n_clicks"),
    Input("preset-weekday-pm-outbound", "n_clicks"),
    Input("reset-filters", "n_clicks"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    State("line-filter", "value"),
    prevent_initial_call=True,
)
def apply_presets(
    _one_day,
    _one_week,
    _full_range,
    _morning_peak,
    _afternoon_peak,
    _weekday_all_day,
    _weekday_am_inbound,
    _weekday_pm_outbound,
    _reset,
    start_date,
    end_date,
    current_lines,
):
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]
    start = start_date or DEFAULT_START
    end = end_date or DEFAULT_END
    lines = current_lines or []
    if triggered == "preset-one-day":
        return start, start, [], lines, [], [], [], []
    if triggered == "preset-one-week":
        start_obj = parse_iso(start)
        end_obj = min(start_obj + timedelta(days=6), parse_iso(META["max_date"]))
        return start, end_obj.isoformat(), [], lines, [], [], [], []
    if triggered == "preset-full-range":
        return META["min_date"], META["max_date"], [], lines, [], [], [], []
    if triggered == "preset-morning-peak":
        return start, end, [], lines, [], [], [], MORNING_PEAK_HOURS
    if triggered == "preset-afternoon-peak":
        return start, end, [], lines, [], [], [], AFTERNOON_PEAK_HOURS
    if triggered == "preset-weekday-all-day":
        return start, end, COMMUTER_DAY_TYPES, lines, [], [], [], []
    if triggered == "preset-weekday-am-inbound":
        return start, end, COMMUTER_DAY_TYPES, lines, [], ["U"], [], MORNING_PEAK_HOURS
    if triggered == "preset-weekday-pm-outbound":
        return start, end, COMMUTER_DAY_TYPES, lines, [], ["D"], [], AFTERNOON_PEAK_HOURS
    return DEFAULT_START, DEFAULT_END, [], [], [], [], [], []


@app.callback(
    Output("station-filter", "options"),
    Output("station-filter", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("day-type-filter", "value"),
    Input("line-filter", "value"),
    Input("group-filter", "value"),
    Input("direction-filter", "value"),
    Input("station-filter", "value"),
    Input("hour-filter", "value"),
    Input("station-graph", "clickData"),
    Input("station-map-graph", "clickData"),
)
def update_station_options(start_date, end_date, day_types, lines, groups, directions, selected_stations, hours, station_bar_click, station_map_click):
    filters = get_filter_state(start_date, end_date, day_types, lines, groups, directions, [], hours)
    stations = get_station_options(filters)
    selected = [station for station in (selected_stations or []) if station in stations]

    triggered = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else None
    clicked_station = None
    if triggered == "station-graph" and station_bar_click:
        clicked_station = station_bar_click["points"][0].get("y")
    if triggered == "station-map-graph" and station_map_click:
        clicked_station = station_map_click["points"][0].get("customdata", [None])[0]

    if clicked_station and clicked_station in stations:
        selected = [clicked_station]

    options = [{"label": station, "value": station} for station in stations]
    return options, selected


@app.callback(
    Output("status-message", "children"),
    Output("selection-summary", "children"),
    Output("metric-stop-rows", "children"),
    Output("metric-services", "children"),
    Output("metric-stations", "children"),
    Output("metric-days", "children"),
    Output("metric-boardings", "children"),
    Output("metric-peak-load", "children"),
    Input("filter-store", "data"),
)
def update_summary(data):
    try:
        payload, filters = deserialize_filters(data)
        kpis = get_kpis(filters)
        selection_parts = [f"{payload['start_date']} to {payload['end_date']}"]
        if payload["day_types"]:
            selection_parts.append(", ".join(payload["day_types"][:2]) + (" +" if len(payload["day_types"]) > 2 else ""))
        if payload["lines"]:
            selection_parts.append(", ".join(payload["lines"][:3]) + (" +" if len(payload["lines"]) > 3 else ""))
        else:
            selection_parts.append("All lines")
        if payload["groups"]:
            selection_parts.append(", ".join(payload["groups"][:2]) + (" +" if len(payload["groups"]) > 2 else ""))
        if payload["directions"]:
            selection_parts.append(" / ".join(payload["directions"]))
        if payload["stations"]:
            selection_parts.append(", ".join(payload["stations"][:2]) + (" +" if len(payload["stations"]) > 2 else ""))
        if payload["hours"]:
            selection_parts.append(f"hours {min(payload['hours']):02d}:00-{max(payload['hours']):02d}:59")
        return (
            "",
            " · ".join(selection_parts),
            format_count(kpis["stop_rows"]),
            format_count(kpis["services"]),
            format_count(kpis["stations"]),
            format_count(kpis["days"]),
            format_count(kpis["boardings"]),
            format_count(kpis["peak_load"]),
        )
    except Exception as exc:
        message = html.Div(f"Dashboard summary error: {exc}", className="status-error")
        return (message, "Current selection unavailable", "0", "0", "0", "0", "0", "0")


@app.callback(
    Output("origin-hour-graph", "figure"),
    Output("stop-hour-graph", "figure"),
    Output("direction-graph", "figure"),
    Output("pattern-graph", "figure"),
    Input("filter-store", "data"),
)
def update_overview_panel(data):
    try:
        _, filters = deserialize_filters(data)
        origin_hourly = get_origin_departure_activity(filters)
        stop_hourly = get_hourly_activity(filters)
        direction = get_direction_flow(filters)
        patterns = get_service_patterns(filters)

        if origin_hourly.empty:
            origin_fig = build_empty_figure("Services by Origin Departure Hour")
        else:
            origin_fig = px.bar(
                origin_hourly,
                x="origin_departure_hour",
                y="services",
                color="boardings",
                color_continuous_scale=["#ffe2bd", COLORS["accent"], "#7a3414"],
                hover_data={"alightings": ":,.0f", "max_peak_load": ":,.0f", "origin_departure_hour": True},
            )
            origin_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Origin departure hour",
                yaxis_title="Services",
                coloraxis_colorbar_title="Boardings",
            )
            origin_fig.update_xaxes(dtick=1, gridcolor=COLORS["grid"])
            origin_fig.update_yaxes(gridcolor=COLORS["grid"])

        if stop_hourly.empty:
            stop_fig = build_empty_figure("Stop-Level Activity by Scheduled Departure Hour")
        else:
            stop_fig = px.line(
                stop_hourly,
                x="departure_hour",
                y=["boardings", "alightings"],
                markers=True,
                color_discrete_sequence=[COLORS["teal"], COLORS["berry"]],
            )
            stop_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Scheduled departure hour",
                yaxis_title="Passengers",
                legend_title_text="",
            )
            stop_fig.update_xaxes(dtick=1, gridcolor=COLORS["grid"])
            stop_fig.update_yaxes(gridcolor=COLORS["grid"])

        if direction.empty:
            direction_fig = build_empty_figure("Direction Mix")
        else:
            direction_fig = px.bar(
                direction,
                x="Direction",
                y=["boardings", "alightings"],
                barmode="group",
                color_discrete_sequence=[COLORS["accent"], COLORS["accent_soft"]],
            )
            direction_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Direction",
                yaxis_title="Passengers",
                legend_title_text="",
            )

        if patterns.empty:
            pattern_fig = build_empty_figure("Service Stop Pattern Mix")
        else:
            pattern_fig = px.bar(
                patterns,
                x="stop_count",
                y="service_count",
                color="service_count",
                color_continuous_scale=["#f3d7b6", COLORS["berry"]],
            )
            pattern_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Recorded stops per service",
                yaxis_title="Services",
                coloraxis_showscale=False,
            )
        return origin_fig, stop_fig, direction_fig, pattern_fig
    except Exception as exc:
        return (
            build_error_figure("Services by Origin Departure Hour", str(exc)),
            build_error_figure("Stop-Level Activity by Scheduled Departure Hour", str(exc)),
            build_error_figure("Direction Mix", str(exc)),
            build_error_figure("Service Stop Pattern Mix", str(exc)),
        )


@app.callback(
    Output("line-boardings-graph", "figure"),
    Output("line-capacity-scatter", "figure"),
    Output("line-commuter-split-graph", "figure"),
    Output("line-summary-table", "data"),
    Output("line-summary-table", "columns"),
    Input("filter-store", "data"),
)
def update_lines_panel(data):
    try:
        payload, filters = deserialize_filters(data)
        line_summary = get_line_capacity_summary(filters)
        line_columns = [{"name": col.replace("_", " "), "id": col} for col in line_summary.columns]

        if line_summary.empty:
            empty = build_empty_figure("Average Boardings per Service by Line")
            return empty, build_empty_figure("Demand vs Peak Load by Line"), build_empty_figure("Weekday Commuter Split by Line"), [], []

        boardings_fig = px.bar(
            line_summary.sort_values("avg_boardings_per_service"),
            x="avg_boardings_per_service",
            y="Line_Name",
            orientation="h",
            color="avg_peak_load_per_service",
            color_continuous_scale=["#ffe2bd", COLORS["accent"], "#7a3414"],
            hover_data={
                "services": ":,.0f",
                "business_dates": ":,.0f",
                "avg_trains_per_day": ":,.1f",
                "median_boardings_per_service": ":,.1f",
                "avg_peak_load_per_service": ":,.1f",
            },
        )
        boardings_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Average boardings per service",
            yaxis_title="Line",
            coloraxis_colorbar_title="Avg peak load",
        )
        boardings_fig.update_yaxes(categoryorder="total ascending")
        boardings_fig.update_xaxes(gridcolor=COLORS["grid"])

        scatter_fig = px.scatter(
            line_summary,
            x="avg_boardings_per_service",
            y="avg_peak_load_per_service",
            size="services",
            color="business_dates",
            text="Line_Name",
            hover_data={
                "avg_trains_per_day": ":,.1f",
                "services": ":,.0f",
                "median_boardings_per_service": ":,.1f",
                "median_peak_load_per_service": ":,.1f",
                "max_peak_load": ":,.0f",
                "avg_recorded_stops_per_service": ":,.1f",
            },
            color_continuous_scale=["#dff5ee", COLORS["teal"], "#0b3d3a"],
            size_max=34,
        )
        scatter_fig.update_traces(textposition="top center")
        scatter_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Average boardings per service",
            yaxis_title="Average peak load per service",
            coloraxis_colorbar_title="Business dates",
        )
        scatter_fig.update_xaxes(gridcolor=COLORS["grid"])
        scatter_fig.update_yaxes(gridcolor=COLORS["grid"])

        commuter_slices = []
        for label, directions, hours, color in (
            ("Weekday AM Inbound", ["U"], MORNING_PEAK_HOURS, COLORS["teal"]),
            ("Weekday PM Outbound", ["D"], AFTERNOON_PEAK_HOURS, COLORS["berry"]),
        ):
            commuter_filters = get_filter_state(
                payload["start_date"],
                payload["end_date"],
                COMMUTER_DAY_TYPES,
                payload.get("lines"),
                payload.get("groups"),
                directions,
                payload.get("stations"),
                hours,
            )
            commuter_df = get_line_capacity_summary(commuter_filters)
            if commuter_df.empty:
                continue
            commuter_df = commuter_df.copy()
            commuter_df["slice"] = label
            commuter_df["slice_color"] = color
            commuter_slices.append(commuter_df)

        if commuter_slices:
            commuter_df = pd.concat(commuter_slices, ignore_index=True)
            commuter_rank = (
                commuter_df.groupby("Line_Name", as_index=False)["avg_peak_load_per_service"]
                .max()
                .sort_values("avg_peak_load_per_service", ascending=True)
            )
            commuter_df["Line_Name"] = pd.Categorical(
                commuter_df["Line_Name"],
                categories=commuter_rank["Line_Name"].tolist(),
                ordered=True,
            )
            commuter_fig = px.bar(
                commuter_df.sort_values("Line_Name"),
                x="avg_peak_load_per_service",
                y="Line_Name",
                color="slice",
                orientation="h",
                barmode="group",
                color_discrete_map={
                    "Weekday AM Inbound": COLORS["teal"],
                    "Weekday PM Outbound": COLORS["berry"],
                },
                hover_data={
                    "avg_boardings_per_service": ":,.1f",
                    "avg_trains_per_day": ":,.1f",
                    "services": ":,.0f",
                    "business_dates": ":,.0f",
                },
            )
            commuter_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Average peak load per service",
                yaxis_title="Line",
                legend_title_text="",
            )
            commuter_fig.update_xaxes(gridcolor=COLORS["grid"])
        else:
            commuter_fig = build_empty_figure("Weekday Commuter Split by Line")

        return boardings_fig, scatter_fig, commuter_fig, line_summary.to_dict("records"), line_columns
    except Exception as exc:
        return (
            build_error_figure("Average Boardings per Service by Line", str(exc)),
            build_error_figure("Demand vs Peak Load by Line", str(exc)),
            build_error_figure("Weekday Commuter Split by Line", str(exc)),
            [],
            [],
        )


@app.callback(
    Output("station-graph", "figure"),
    Output("station-map-graph", "figure"),
    Output("map-station-table", "data"),
    Output("map-station-table", "columns"),
    Input("filter-store", "data"),
)
def update_station_panel(data):
    try:
        _, filters = deserialize_filters(data)
        station = get_station_activity(filters).head(18)
        station_map = get_station_map_data(filters)
        line_paths = get_line_paths(filters)

        if station.empty:
            station_fig = build_empty_figure("Top Station Activity")
        else:
            station_fig = px.bar(
                station.sort_values("boardings"),
                x="boardings",
                y="Station_Name",
                orientation="h",
                color="avg_departure_load",
                color_continuous_scale=["#ffe2bd", COLORS["accent"], "#7a3414"],
                custom_data=["Station_Name"],
            )
            station_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Boardings",
                yaxis_title="Station",
                coloraxis_colorbar_title="Avg load",
            )
            station_fig.update_yaxes(categoryorder="total ascending")

        if station_map.empty:
            return station_fig, build_empty_figure("Station Map"), [], []

        station_map = station_map.copy()
        station_map["line_names_label"] = station_map["line_names"].apply(lambda values: ", ".join(values))
        lat_span = float(station_map["latitude"].max() - station_map["latitude"].min())
        lon_span = float(station_map["longitude"].max() - station_map["longitude"].min())
        station_map_fig = go.Figure()

        if not line_paths.empty:
            palette = ["#0f766e", "#b45309", "#9f1239", "#6b7a18", "#2f4858", "#7c3aed"]
            for idx, (line_name, path_df) in enumerate(line_paths.groupby("Line_Name")):
                path_df = path_df.sort_values("station_order")
                station_map_fig.add_trace(
                    go.Scattermapbox(
                        mode="lines",
                        lon=path_df["longitude"],
                        lat=path_df["latitude"],
                        line={"width": 3, "color": palette[idx % len(palette)]},
                        name=line_name,
                        hoverinfo="skip",
                        opacity=0.55,
                    )
                )

        marker_sizes = station_map["boardings"].clip(lower=1)
        marker_sizes = (marker_sizes / marker_sizes.max()) * 18 + 8
        station_map_fig.add_trace(
            go.Scattermapbox(
                lon=station_map["longitude"],
                lat=station_map["latitude"],
                text=station_map["Station_Name"],
                customdata=station_map[["Station_Name", "services", "boardings", "alightings", "line_names_label"]],
                mode="markers",
                marker=dict(
                    size=marker_sizes,
                    color=station_map["boardings"],
                    colorscale=[[0, "#d8efe9"], [0.5, "#0f766e"], [1, "#9f1239"]],
                    colorbar=dict(title="Boardings"),
                    opacity=0.92,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b>"
                    "<br>Boardings=%{customdata[2]:,.0f}"
                    "<br>Alightings=%{customdata[3]:,.0f}"
                    "<br>Services=%{customdata[1]:,.0f}"
                    "<br>Lines=%{customdata[4]}"
                    "<extra></extra>"
                ),
            )
        )
        station_map_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            mapbox=dict(
                style="carto-positron",
                center={"lat": float(station_map["latitude"].mean()), "lon": float(station_map["longitude"].mean())},
                zoom=map_zoom_for_bounds(lat_span, lon_span),
            ),
            margin=dict(l=0, r=0, t=20, b=0),
            height=720,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )
        map_station_columns = [
            {"name": "Station", "id": "Station_Name"},
            {"name": "Lines", "id": "line_names_label"},
            {"name": "Boardings", "id": "boardings"},
            {"name": "Alightings", "id": "alightings"},
            {"name": "Services", "id": "services"},
        ]
        map_station_records = station_map[["Station_Name", "line_names_label", "boardings", "alightings", "services"]].to_dict("records")
        return station_fig, station_map_fig, map_station_records, map_station_columns
    except Exception as exc:
        return build_error_figure("Top Station Activity", str(exc)), build_error_figure("Station Map", str(exc)), [], []


@app.callback(
    Output("peak-train-graph", "figure"),
    Output("service-table", "data"),
    Output("service-table", "columns"),
    Input("filter-store", "data"),
)
def update_service_panel(data):
    try:
        _, filters = deserialize_filters(data)
        peak_trains = get_peak_trains(filters, limit=18)
        service_summary = get_service_summary(filters, limit=200)
        service_columns = [{"name": col.replace("_", " "), "id": col} for col in service_summary.columns]

        if peak_trains.empty:
            peak_fig = build_empty_figure("Peak Load by Service")
        else:
            peak_trains["label"] = peak_trains["Train_Number"] + " · " + peak_trains["line_name"] + " · " + peak_trains["direction"]
            peak_fig = px.bar(
                peak_trains.sort_values("peak_load"),
                x="peak_load",
                y="label",
                orientation="h",
                color="total_boardings",
                color_continuous_scale=["#dff5ee", COLORS["teal"]],
            )
            peak_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Peak departure load",
                yaxis_title="Service",
                coloraxis_colorbar_title="Boardings",
            )
        return peak_fig, service_summary.to_dict("records"), service_columns
    except Exception as exc:
        return build_error_figure("Peak Load by Service", str(exc)), [], []


@app.callback(
    Output("preview-table", "data"),
    Output("preview-table", "columns"),
    Output("preview-table", "page_size"),
    Input("filter-store", "data"),
    Input("preview-row-count", "value"),
)
def update_rows_panel(data, preview_row_count):
    try:
        _, filters = deserialize_filters(data)
        preview = get_preview_rows(filters, limit=100)
        preview_columns = [{"name": col.replace("_", " "), "id": col} for col in preview.columns]
        return preview.to_dict("records"), preview_columns, preview_row_count or 20
    except Exception:
        return [], [], preview_row_count or 20


@app.callback(
    Output("overview-panel", "style"),
    Output("lines-panel", "style"),
    Output("stations-panel", "style"),
    Output("map-panel", "style"),
    Output("services-panel", "style"),
    Output("rows-panel", "style"),
    Input("view-tabs", "value"),
)
def update_tab_visibility(active_tab):
    return (
        tab_style(active_tab == "overview"),
        tab_style(active_tab == "lines"),
        tab_style(active_tab == "stations"),
        tab_style(active_tab == "map"),
        tab_style(active_tab == "services"),
        tab_style(active_tab == "rows"),
    )


@app.callback(
    Output("download-data", "data"),
    Input("download-button", "n_clicks"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    State("day-type-filter", "value"),
    State("line-filter", "value"),
    State("group-filter", "value"),
    State("direction-filter", "value"),
    State("station-filter", "value"),
    State("hour-filter", "value"),
    prevent_initial_call=True,
)
def download_filtered_rows(_n_clicks, start_date, end_date, day_types, lines, groups, directions, stations, hours):
    filters = get_filter_state(start_date, end_date, day_types, lines, groups, directions, stations, hours)
    df = get_filtered_export(filters)
    if df.empty:
        df = get_preview_rows(filters, limit=1)
    filename = f"suntrain_export_{start_date}_to_{end_date}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
