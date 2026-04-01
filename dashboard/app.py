from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
import plotly.express as px
import plotly.graph_objects as go

from dashboard.data import (
    get_direction_flow,
    get_filter_state,
    get_filtered_export,
    get_hourly_activity,
    get_kpis,
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
DEFAULT_LINE = "Werribee" if "Werribee" in META["lines"] else META["lines"][0]
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

app = Dash(
    __name__,
    title="SunTrain Dashboard",
    assets_folder=str(ROOT / "assets"),
)
server = app.server


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


app.layout = html.Div(
    className="page-shell",
    children=[
        html.A("Skip to dashboard", href="#main-content", className="skip-link"),
        html.Div(className="page-glow page-glow-a"),
        html.Div(className="page-glow page-glow-b"),
        dcc.Download(id="download-data"),
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
                                                        html.Label("Lines", className="finder-label"),
                                                        dcc.Dropdown(
                                                            id="line-filter",
                                                            options=[{"label": line, "value": line} for line in META["lines"]],
                                                            value=[DEFAULT_LINE],
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
                                        dcc.Graph(id="origin-hour-graph", config={"displayModeBar": False}),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Stop-Level Activity by Scheduled Departure Hour"),
                                        dcc.Graph(id="stop-hour-graph", config={"displayModeBar": False}),
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
                                        dcc.Graph(id="direction-graph", config={"displayModeBar": False}),
                                    ],
                                ),
                                html.Div(
                                    className="viz-card",
                                    children=[
                                        html.Div(className="viz-title", children="Service Stop Pattern Mix"),
                                        dcc.Graph(id="pattern-graph", config={"displayModeBar": False}),
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
                                        dcc.Graph(id="station-graph", config={"displayModeBar": False}),
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
                                dcc.Graph(id="station-map-graph", config={"displayModeBar": False}),
                            ],
                        ),
                        html.Div(
                            className="table-card",
                            children=[
                                html.Div(className="viz-title", children="Stations in Current Map View"),
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
                                        dcc.Graph(id="peak-train-graph", config={"displayModeBar": False}),
                                    ],
                                ),
                                html.Div(
                                    className="table-card compact-card",
                                    children=[
                                        html.Div(className="viz-title", children="Service Summary"),
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
    Output("date-range", "start_date"),
    Output("date-range", "end_date"),
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
    Input("reset-filters", "n_clicks"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    prevent_initial_call=True,
)
def apply_presets(_one_day, _one_week, _full_range, _morning_peak, _afternoon_peak, _reset, start_date, end_date):
    triggered = callback_context.triggered[0]["prop_id"].split(".")[0]
    start = start_date or DEFAULT_START
    end = end_date or DEFAULT_END
    if triggered == "preset-one-day":
        return start, start, [DEFAULT_LINE], [], [], [], []
    if triggered == "preset-one-week":
        start_obj = parse_iso(start)
        end_obj = min(start_obj + timedelta(days=6), parse_iso(META["max_date"]))
        return start, end_obj.isoformat(), [DEFAULT_LINE], [], [], [], []
    if triggered == "preset-full-range":
        return META["min_date"], META["max_date"], [DEFAULT_LINE], [], [], [], []
    if triggered == "preset-morning-peak":
        return start, end, [DEFAULT_LINE], [], [], [], MORNING_PEAK_HOURS
    if triggered == "preset-afternoon-peak":
        return start, end, [DEFAULT_LINE], [], [], [], AFTERNOON_PEAK_HOURS
    return DEFAULT_START, DEFAULT_END, [DEFAULT_LINE], [], [], [], []


@app.callback(
    Output("station-filter", "options"),
    Output("station-filter", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("line-filter", "value"),
    Input("group-filter", "value"),
    Input("direction-filter", "value"),
    Input("station-filter", "value"),
    Input("hour-filter", "value"),
    Input("station-graph", "clickData"),
    Input("station-map-graph", "clickData"),
)
def update_station_options(start_date, end_date, lines, groups, directions, selected_stations, hours, station_bar_click, station_map_click):
    filters = get_filter_state(start_date, end_date, lines, groups, directions, [], hours)
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
    Output("selection-summary", "children"),
    Output("metric-stop-rows", "children"),
    Output("metric-services", "children"),
    Output("metric-stations", "children"),
    Output("metric-days", "children"),
    Output("metric-boardings", "children"),
    Output("metric-peak-load", "children"),
    Output("origin-hour-graph", "figure"),
    Output("stop-hour-graph", "figure"),
    Output("direction-graph", "figure"),
    Output("station-graph", "figure"),
    Output("station-map-graph", "figure"),
    Output("map-station-table", "data"),
    Output("map-station-table", "columns"),
    Output("pattern-graph", "figure"),
    Output("peak-train-graph", "figure"),
    Output("service-table", "data"),
    Output("service-table", "columns"),
    Output("preview-table", "data"),
    Output("preview-table", "columns"),
    Output("preview-table", "page_size"),
    Output("overview-panel", "style"),
    Output("stations-panel", "style"),
    Output("map-panel", "style"),
    Output("services-panel", "style"),
    Output("rows-panel", "style"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("line-filter", "value"),
    Input("group-filter", "value"),
    Input("direction-filter", "value"),
    Input("station-filter", "value"),
    Input("hour-filter", "value"),
    Input("view-tabs", "value"),
    Input("preview-row-count", "value"),
)
def update_dashboard(start_date, end_date, lines, groups, directions, stations, hours, active_tab, preview_row_count):
    filters = get_filter_state(start_date, end_date, lines, groups, directions, stations, hours)
    kpis = get_kpis(filters)
    origin_hourly = get_origin_departure_activity(filters)
    stop_hourly = get_hourly_activity(filters)
    direction = get_direction_flow(filters)
    station = get_station_activity(filters).head(18)
    station_map = get_station_map_data(filters)
    line_paths = get_line_paths(filters)
    patterns = get_service_patterns(filters)
    peak_trains = get_peak_trains(filters, limit=18)
    service_summary = get_service_summary(filters, limit=200)
    preview = get_preview_rows(filters, limit=100)

    selection_parts = [f"{start_date} to {end_date}"]
    if lines:
        selection_parts.append(", ".join(lines[:3]) + (" +" if len(lines) > 3 else ""))
    if groups:
        selection_parts.append(", ".join(groups[:2]) + (" +" if len(groups) > 2 else ""))
    if directions:
        selection_parts.append(" / ".join(directions))
    if stations:
        selection_parts.append(", ".join(stations[:2]) + (" +" if len(stations) > 2 else ""))
    if hours:
        selection_parts.append(f"hours {min(hours):02d}:00-{max(hours):02d}:59")
    selection_summary = " · ".join(selection_parts)

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
        station_map_fig = build_empty_figure("Station Map")
        map_station_records = []
        map_station_columns = []
    else:
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
                        opacity=0.5,
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
                center={
                    "lat": float(station_map["latitude"].mean()),
                    "lon": float(station_map["longitude"].mean()),
                },
                zoom=map_zoom_for_bounds(lat_span, lon_span),
            ),
            margin=dict(l=0, r=0, t=20, b=0),
            height=720,
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )
        map_station_view = station_map.copy()
        map_station_columns = [
            {"name": "Station", "id": "Station_Name"},
            {"name": "Lines", "id": "line_names_label"},
            {"name": "Boardings", "id": "boardings"},
            {"name": "Alightings", "id": "alightings"},
            {"name": "Services", "id": "services"},
        ]
        map_station_records = map_station_view[["Station_Name", "line_names_label", "boardings", "alightings", "services"]].to_dict("records")

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

    if peak_trains.empty:
        peak_fig = build_empty_figure("Peak Load by Service")
    else:
        peak_trains["label"] = (
            peak_trains["Train_Number"]
            + " · "
            + peak_trains["line_name"]
            + " · "
            + peak_trains["direction"]
        )
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

    service_columns = [{"name": col.replace("_", " "), "id": col} for col in service_summary.columns]
    preview_columns = [{"name": col.replace("_", " "), "id": col} for col in preview.columns]

    return (
        selection_summary,
        format_count(kpis["stop_rows"]),
        format_count(kpis["services"]),
        format_count(kpis["stations"]),
        format_count(kpis["days"]),
        format_count(kpis["boardings"]),
        format_count(kpis["peak_load"]),
        origin_fig,
        stop_fig,
        direction_fig,
        station_fig,
        station_map_fig,
        map_station_records,
        map_station_columns,
        pattern_fig,
        peak_fig,
        service_summary.to_dict("records"),
        service_columns,
        preview.to_dict("records"),
        preview_columns,
        preview_row_count or 20,
        tab_style(active_tab == "overview"),
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
    State("line-filter", "value"),
    State("group-filter", "value"),
    State("direction-filter", "value"),
    State("station-filter", "value"),
    State("hour-filter", "value"),
    prevent_initial_call=True,
)
def download_filtered_rows(_n_clicks, start_date, end_date, lines, groups, directions, stations, hours):
    filters = get_filter_state(start_date, end_date, lines, groups, directions, stations, hours)
    df = get_filtered_export(filters)
    if df.empty:
        df = get_preview_rows(filters, limit=1)
    filename = f"suntrain_export_{start_date}_to_{end_date}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
