from __future__ import annotations

import importlib


def _load_data_module(monkeypatch, sample_parquet):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))
    import dashboard.data as data_module

    return importlib.reload(data_module)


def test_get_metadata_uses_selected_dataset(monkeypatch, sample_parquet):
    data_module = _load_data_module(monkeypatch, sample_parquet)

    metadata = data_module.get_metadata()

    assert metadata["min_date"] == "2023-07-10"
    assert metadata["max_date"] == "2023-07-11"
    assert metadata["day_types"] == ["Normal Weekday"]
    assert metadata["lines"] == ["Sunbury", "Werribee"]
    assert metadata["groups"] == ["Northern", "Western"]
    assert metadata["directions"] == ["D", "U"]


def test_get_kpis_and_station_options_respect_filters(monkeypatch, sample_parquet):
    data_module = _load_data_module(monkeypatch, sample_parquet)
    filters = data_module.get_filter_state(
        "2023-07-10",
        "2023-07-10",
        ["Normal Weekday"],
        ["Werribee"],
        ["Western"],
        ["U"],
        [],
        [7],
    )

    kpis = data_module.get_kpis(filters)
    stations = data_module.get_station_options(filters)
    hourly = data_module.get_hourly_activity(filters)

    assert kpis["stop_rows"] == 2
    assert kpis["services"] == 1
    assert kpis["stations"] == 2
    assert kpis["days"] == 1
    assert kpis["boardings"] == 150
    assert kpis["alightings"] == 30
    assert kpis["peak_load"] == 130
    assert stations == ["Newport", "Werribee"]
    assert hourly.to_dict("records") == [
        {"departure_hour": 7, "boardings": 150.0, "alightings": 30.0, "services": 1}
    ]


def test_service_summary_and_export_shape(monkeypatch, sample_parquet):
    data_module = _load_data_module(monkeypatch, sample_parquet)
    filters = data_module.get_filter_state("2023-07-10", "2023-07-11", [], [], [], [], [], [])

    summary = data_module.get_service_summary(filters)
    exported = data_module.get_filtered_export(filters)

    assert len(summary) == 2
    assert set(summary["Train_Number"]) == {"1001", "2002"}
    assert summary.loc[summary["Train_Number"] == "1001", "peak_load"].item() == 130
    assert len(exported) == 4
    assert "Arrival_Time_HHMM" in exported.columns
    assert "Departure_Time_HHMM" in exported.columns
