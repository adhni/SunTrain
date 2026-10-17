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
        assert {"id": "view-tabs", "property": "value"} in callback["inputs"]
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


def test_replay_only_loads_when_visible_and_date_changes(app_module, monkeypatch):
    import dashboard.replay_view as replay_view

    calls = []
    monkeypatch.setattr(replay_view, "get_replay_day", lambda day, city: calls.append((day, city)) or {"business_date": day})
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2023-07-10", "overview", "melbourne", None)
    assert app_module.load_replay_day("2023-07-10", "replay", "melbourne", None) == ({"business_date": "2023-07-10"}, "")
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2023-07-10", "replay", "melbourne", {"business_date": "2023-07-10"})
    app_module.load_replay_day("2023-07-11", "replay", "melbourne", {"business_date": "2023-07-10"})
    assert calls == [("2023-07-10", "melbourne"), ("2023-07-11", "melbourne")]


def test_replay_switches_city_on_same_date_and_ignores_transient_out_of_range_date(app_module, monkeypatch):
    import dashboard.replay_view as replay_view
    calls = []
    monkeypatch.setattr(replay_view, "get_replay_day", lambda day, city: calls.append((day, city)) or {"city": city})
    result, message = app_module.load_replay_day("2024-06-24", "replay", "boston",
                                                {"business_date": "2024-06-24", "city": "melbourne"})
    assert result == {"city": "boston"} and message == ""
    assert calls == [("2024-06-24", "boston")]
    result, _ = app_module.load_replay_day("2024-06-24", "replay", "melbourne",
                                          {"business_date": "2024-06-24", "city": "boston"})
    assert result == {"city": "melbourne"}
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-06-24", "replay", "boston",
                                   {"business_date": "2024-06-24", "city": "boston"})
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-05-27", "replay", "boston", None)
    with pytest.raises(PreventUpdate):
        app_module.load_replay_day("2024-06-24", "replay", "chicago", None)
    result, _ = app_module.load_replay_day("2025-11-24", "replay", "chicago", None)
    assert result == {"city": "chicago"}


def test_replay_hides_shared_filters_and_restores_them_on_exit(app_module):
    replay = app_module.update_tab_visibility("replay")
    overview = app_module.update_tab_visibility("overview")
    assert replay[4] == {"display": "block"}
    assert replay[5:8] == ({"display": "none"},) * 3
    assert replay[-1] == "app replay-active"
    assert overview[4] == {"display": "none"}
    assert overview[5:8] == ({}, {}, {})


@pytest.mark.parametrize("subtab,index", [("overview", 0), ("lines", 1), ("segments", 2), ("network", 3)])
def test_overview_only_shows_selected_subtab(app_module, subtab, index):
    styles = app_module.update_tab_visibility("overview", subtab)
    for position in range(4):
        assert styles[position] == {"display": "block" if position == index else "none"}
    assert styles[8] == {"display": "block"}
    hidden = app_module.update_tab_visibility("replay", subtab)
    assert hidden[:4] == ({"display": "none"},) * 4
    assert hidden[8] == {"display": "none"}
