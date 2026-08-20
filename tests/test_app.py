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
    ("callback_name", "inactive_tab"),
    [
        ("update_overview_panel", "lines"),
        ("update_lines_panel", "network"),
        ("update_service_panel", "segments"),
        ("update_segment_panel", "overview"),
        ("update_station_panel", "lines"),
    ],
)
def test_inactive_panels_do_not_query(app_module, monkeypatch, callback_name, inactive_tab):
    monkeypatch.setattr(
        app_module,
        "deserialize_filters",
        lambda _data: pytest.fail("inactive panel queried data"),
    )

    with pytest.raises(PreventUpdate):
        getattr(app_module, callback_name)({}, inactive_tab)


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
