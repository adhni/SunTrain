from __future__ import annotations

import importlib
from types import SimpleNamespace

from dash import no_update
from dash.exceptions import PreventUpdate
import pandas as pd
import pytest


@pytest.fixture
def app_module(monkeypatch, sample_parquet):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))

    import dashboard.data as data_module
    import dashboard.app as dashboard_app

    importlib.reload(data_module)
    return importlib.reload(dashboard_app)


def component_text(component) -> str:
    if component is None:
        return ""
    if isinstance(component, (str, int, float)):
        return str(component)
    if isinstance(component, (list, tuple)):
        return " ".join(component_text(item) for item in component)
    return component_text(getattr(component, "children", None))


def test_scope_summary_shows_every_active_filter(app_module):
    payload = app_module.serialize_filters(
        "2023-07-10",
        "2023-07-11",
        ["Normal Weekday"],
        ["Werribee"],
        ["Western"],
        ["U"],
        ["Newport"],
        [7, 8, 9],
    )

    summary = app_module.scope_summary(payload, {"days": 2, "stations": 1})
    text = " ".join(component_text(summary).split())

    assert "Date: 10 Jul 2023 to 11 Jul 2023" in text
    assert "Day type: Normal Weekday" in text
    assert "Service groups: Western" in text
    assert "Stations: Newport" in text
    assert "Hours: 3 selected" in text
    assert "2 days / 1 station" in text


def test_more_filters_reports_active_categories(app_module):
    payload = app_module.serialize_filters(
        "2023-07-10",
        "2023-07-10",
        ["Normal Weekday"],
        [],
        ["Western"],
        [],
        ["Newport"],
        [7, 8, 9],
    )

    closed = app_module.toggle_advanced_filters(None, payload)
    opened = app_module.toggle_advanced_filters(1, payload)

    assert closed == ({"display": "none"}, "More filters (4)", False)
    assert opened == ({"display": "grid"}, "Hide filters (4)", True)


def test_commuter_preset_preserves_unrelated_filters_and_clears_command(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "callback_context",
        SimpleNamespace(triggered=[{"prop_id": "preset-dropdown.value"}]),
    )

    result = app_module.apply_presets(
        "weekday-am-inbound",
        None,
        "2023-07-10",
        "2023-07-11",
        ["Saturday"],
        ["Werribee"],
        ["Western"],
        ["D"],
        ["Newport"],
        [12],
    )

    assert result == (
        "2023-07-10",
        "2023-07-11",
        ["Normal Weekday"],
        ["Werribee"],
        ["Western"],
        ["U"],
        ["Newport"],
        [7, 8, 9],
        None,
    )


def test_reset_clears_filters_and_preset_command(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "callback_context",
        SimpleNamespace(triggered=[{"prop_id": "reset-filters.n_clicks"}]),
    )

    result = app_module.apply_presets(
        None,
        1,
        "2023-07-11",
        "2023-07-11",
        ["Normal Weekday"],
        ["Werribee"],
        ["Western"],
        ["U"],
        ["Newport"],
        [7],
    )

    assert result == (
        app_module.DEFAULT_START,
        app_module.DEFAULT_END,
        [],
        [],
        [],
        [],
        [],
        [],
        None,
    )


@pytest.mark.parametrize(
    ("callback_name", "subtab"),
    [
        ("update_overview_panel", "overview"),
        ("update_lines_panel", "lines"),
        ("update_service_panel", "lines"),
        ("update_segment_panel", "segments"),
        ("update_station_panel", "network"),
    ],
)
def test_inactive_panels_do_not_query(app_module, monkeypatch, callback_name, subtab):
    monkeypatch.setattr(
        app_module,
        "deserialize_filters",
        lambda _data: pytest.fail("inactive panel queried data"),
    )

    with pytest.raises(PreventUpdate):
        getattr(app_module, callback_name)({}, "replay", subtab)
    with pytest.raises(PreventUpdate):
        getattr(app_module, callback_name)({}, "overview", "other")


def test_raw_preview_does_not_query_while_collapsed(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "deserialize_filters",
        lambda _data: pytest.fail("collapsed raw data queried data"),
    )

    with pytest.raises(PreventUpdate):
        app_module.update_rows_panel({}, 20, None)


def test_heavy_callbacks_include_active_tab_input(app_module):
    graph_ids = {
        "origin-hour-graph",
        "line-boardings-graph",
        "peak-train-graph",
        "segment-speed-graph",
        "station-graph",
    }

    for graph_id in graph_ids:
        callback = next(
            value
            for key, value in app_module.app.callback_map.items()
            if f"{graph_id}.figure" in key
        )
        assert {"id": "analysis-view", "property": "data"} in callback["inputs"]
        assert {"id": "overview-tabs", "property": "value"} in callback["inputs"]


def test_export_limit_prevents_materialization(app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_kpis",
        lambda _filters: {"stop_rows": app_module.MAX_EXPORT_ROWS + 1},
    )
    monkeypatch.setattr(
        app_module,
        "get_filtered_export",
        lambda _filters: pytest.fail("oversized export was materialized"),
    )

    result = app_module.download_filtered_rows(
        1,
        "2023-07-10",
        "2023-07-11",
        [],
        [],
        [],
        [],
        [],
        [],
    )

    assert result is no_update


def test_allowed_export_builds_csv_once(app_module, monkeypatch):
    exported = pd.DataFrame([{"Line": "Werribee", "Boardings": 120}])
    calls = {"export": 0, "send": 0}

    monkeypatch.setattr(app_module, "get_kpis", lambda _filters: {"stop_rows": 1})

    def fake_export(_filters):
        calls["export"] += 1
        return exported

    def fake_send_data_frame(writer, filename, **kwargs):
        calls["send"] += 1
        assert writer.__self__ is exported
        assert filename == "suntrain_export_2023-07-10_to_2023-07-10.csv"
        assert kwargs == {"index": False}
        return {"filename": filename}

    monkeypatch.setattr(app_module, "get_filtered_export", fake_export)
    monkeypatch.setattr(app_module.dcc, "send_data_frame", fake_send_data_frame)

    result = app_module.download_filtered_rows(
        1,
        "2023-07-10",
        "2023-07-10",
        [],
        ["Werribee"],
        [],
        [],
        [],
        [],
    )

    assert result == {"filename": "suntrain_export_2023-07-10_to_2023-07-10.csv"}
    assert calls == {"export": 1, "send": 1}


def test_index_route_renders(app_module):
    response = app_module.server.test_client().get("/")

    assert response.status_code == 200
    assert b"SunTrain" in response.data


def test_replay_descriptors_only_load_when_visible_and_selection_changes(app_module, monkeypatch):
    import dashboard.replay_view as view
    calls = []
    monkeypatch.setattr(view, "descriptor", lambda day, city, modes: calls.append((day, city, modes)) or {"city": city, "modes": list(modes)})
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2023-07-10", "inactive", "melbourne", None)
    info, message = app_module.load_replay_day("2023-07-10", "replay", "melbourne", None)
    assert info == {"city": "melbourne", "modes": ["train"]} and message == ""
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2023-07-10", "overview", "melbourne", {**info, "business_date": "2023-07-10"})
    app_module.load_replay_day("2023-07-10", "replay", "melbourne", {**info, "business_date": "2023-07-10"}, ["tram"])
    assert calls == [("2023-07-10", "melbourne", ("train",)), ("2023-07-10", "melbourne", ("tram",))]


def test_replay_switches_city_and_ignores_transient_out_of_range_date(app_module, monkeypatch):
    import dashboard.replay_view as view
    calls = []
    monkeypatch.setattr(view, "descriptor", lambda day, city, modes: calls.append(city) or {"city": city})
    app_module.load_replay_day("2024-06-24", "replay", "boston", {"business_date": "2024-06-24", "city": "melbourne"})
    assert calls == ["boston"]
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-05-27", "replay", "boston", None)
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-06-24", "replay", "chicago", None)


def test_mode_changes_download_only_selected_modes_for_london(app_module):
    info, _ = app_module.load_replay_day("2026-10-05", "replay", "london", None)
    assert not info["bus_data_loaded"] and "services" not in info and "url" in info
    rail = {**info, "business_date": "2026-10-05"}
    bus, _ = app_module.load_replay_day("2026-10-05", "replay", "london", rail, ["bus"])
    assert bus["bus_data_loaded"] and bus["modes"] == ["bus"]
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2026-10-05", "replay", "london", bus, ["bus"])
    all_modes, _ = app_module.load_replay_day("2026-10-05", "replay", "london", rail, [])
    assert all_modes["bus_data_loaded"] and len(all_modes["modes"]) == 4


def test_startup_contains_no_charts_and_analysis_mounts_only_active_panel(app_module):
    from dash import dcc, dash_table
    def walk(component):
        if isinstance(component, (list, tuple)):
            for child in component:
                yield from walk(child)
        elif component is not None:
            yield component
            yield from walk(getattr(component, "children", None))
    assert not any(isinstance(c, (dcc.Graph, dash_table.DataTable)) for c in walk(app_module.app.layout))
    assert app_module.mount_analysis_panels("replay", "overview", 1)[:5] == [[], [], [], no_update, []]
    panels = app_module.mount_analysis_panels("overview", "network", 0)
    assert panels[3] and all(not panel for i, panel in enumerate(panels[:5]) if i != 3)
    assert app_module.mount_analysis_panels("replay", "network", 0, True, "analysis-network-ready")[3] == []


def test_hidden_analysis_summary_and_station_options_do_not_query(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "get_kpis", lambda *_: pytest.fail("hidden summary queried"))
    monkeypatch.setattr(app_module, "get_station_options", lambda *_: pytest.fail("hidden station options queried"))
    with pytest.raises(PreventUpdate):
        app_module.update_summary({}, "replay")
    with pytest.raises(PreventUpdate):
        app_module.update_station_options(None, None, [], [], [], [], [], [], None, None, "replay")


def test_shared_filters_remain_available_and_passenger_reports_start_collapsed(app_module):
    replay = app_module.update_tab_visibility("replay")
    overview = app_module.update_tab_visibility("overview")
    assert replay[4] == {"display": "block"}
    assert replay[5:8] == ({"display": "none"},) * 3
    assert replay[9] == "app transport-active replay-active"
    assert overview[4] == {"display": "block"}
    assert overview[:4] == ({"display": "none"},) * 4
    assert overview[5:8] == ({"display": "none"},) * 3
    assert overview[10:13] == ({"display": "block"}, {"display": "block"}, {"display": "none"})


def test_home_is_the_opening_view_and_keeps_replay_hidden_without_loading_schedules(app_module, monkeypatch):
    import dashboard.replay_view as replay_view
    from dashboard.cities import CITIES
    from dashboard.home_view import home_places

    monkeypatch.setattr(replay_view, "descriptor", lambda *a, **kw: pytest.fail("home loaded a replay"))
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-05-27", "home", "melbourne", None)
    state=app_module.update_tab_visibility("home")
    assert state[4] == {"display": "none"}
    assert state[9] == "app transport-active home-active"
    assert state[-1] == {"display": "block"}
    assert app_module.update_tab_visibility("replay")[-1] == {"display": "none"}
    places=home_places()
    assert set(CITIES) <= {place["id"] for place in places}
    assert all(place["bounds"] == CITIES[place["id"]]["bounds"] for place in places if place['id'] in CITIES)
    assert all({"id","name","kind","bounds","modes","default_modes","home_marker","start","end"} <= set(place) for place in places)

    def walk(component):
        if isinstance(component,(list,tuple)):
            for child in component:yield from walk(child)
        elif component is not None:
            yield component
            yield from walk(getattr(component,"children",None))
    tabs=next(component for component in walk(app_module.app.layout) if getattr(component,"id",None)=="view-tabs")
    assert tabs.value == "home"


@pytest.mark.parametrize("subtab,index", [("overview", 0), ("lines", 1), ("segments", 2), ("network", 3)])
def test_overview_only_shows_selected_subtab(app_module, subtab, index):
    styles = app_module.update_tab_visibility("overview", subtab, "overview", "melbourne", True)
    for position in range(4):
        assert styles[position] == {"display": "block" if position == index else "none"}
    assert styles[8] == {"display": "block"}
    hidden = app_module.update_tab_visibility("replay", subtab)
    assert hidden[:4] == ({"display": "none"},) * 4
    assert hidden[8] == {"display": "none"}


def test_each_city_gets_an_overview_and_only_melbourne_can_open_passenger_reports(app_module):
    from dashboard.cities import CITIES
    for city in CITIES:
        state = app_module.passenger_analysis_view("overview", city, True)
        assert (state == "overview") == (city == "melbourne")
        styles = app_module.update_tab_visibility("overview", "overview", state, city, True)
        assert styles[10] == {"display": "block"}
        assert styles[11] == {"display": "block" if city == "melbourne" else "none"}
        assert app_module.passenger_analysis_view("overview", city, False) == "inactive"
        assert app_module.passenger_analysis_view("replay", city, True) == "inactive"


def test_collapsed_passenger_reports_do_not_query_even_when_raw_data_was_open(app_module, monkeypatch):
    monkeypatch.setattr(app_module, "deserialize_filters", lambda *_: pytest.fail("hidden report queried data"))
    with pytest.raises(PreventUpdate):
        app_module.update_rows_panel({}, 20, 1, "inactive")
    for name, subtab in [("update_overview_panel", "overview"), ("update_lines_panel", "lines"),
                         ("update_service_panel", "lines"), ("update_station_panel", "network"),
                         ("update_segment_panel", "segments")]:
        with pytest.raises(PreventUpdate):
            getattr(app_module, name)({}, "inactive", subtab)


def test_passenger_reports_seed_supported_filters_only_once(app_module):
    assert app_module.initialize_passenger_analysis(True, False, "2023-07-11", ["Werribee", "Bus 1"]) == (
        "2023-07-11", "2023-07-11", ["Werribee"], True)
    with pytest.raises(PreventUpdate):
        app_module.initialize_passenger_analysis(True, True, "2023-07-10", [])
