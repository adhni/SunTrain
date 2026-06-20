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


def test_segment_speeds_calculates_scheduled_speed(monkeypatch, sample_parquet):
    data_module = _load_data_module(monkeypatch, sample_parquet)
    filters = data_module.get_filter_state("2023-07-10", "2023-07-10", [], ["Werribee"], [], ["U"], [], [])

    segment_speeds = data_module.get_segment_speeds(filters)

    assert segment_speeds.to_dict("records") == [
        {
            "Line_Name": "Werribee",
            "Direction": "U",
            "from_station": "Werribee",
            "to_station": "Newport",
            "segment_km": 1.0,
            "avg_run_minutes": 20.0,
            "min_run_minutes": 20.0,
            "max_run_minutes": 20.0,
            "avg_scheduled_kmh": 3.0,
            "observed_segments": 1,
        }
    ]


def test_segment_speeds_handles_after_midnight_rollover(monkeypatch, tmp_path):
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "9001",
                "Line_Name": "Night Line",
                "Group": "Night Group",
                "Direction": "U",
                "Origin_Station": "Alpha",
                "Destination_Station": "Bravo",
                "Station_Name": "Alpha",
                "Station_Latitude": -37.0,
                "Station_Longitude": 144.0,
                "Station_Chainage": 0,
                "Stop_Sequence_Number": 1,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 23:57:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 23:58:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "9001",
                "Line_Name": "Night Line",
                "Group": "Night Group",
                "Direction": "U",
                "Origin_Station": "Alpha",
                "Destination_Station": "Bravo",
                "Station_Name": "Bravo",
                "Station_Latitude": -37.1,
                "Station_Longitude": 144.1,
                "Station_Chainage": 3000,
                "Stop_Sequence_Number": 2,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-11 00:03:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-11 00:04:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
        ]
    )
    path = tmp_path / "overnight.parquet"
    frame.to_parquet(path, index=False)

    data_module = _load_data_module(monkeypatch, path)
    filters = data_module.get_filter_state("2023-07-10", "2023-07-10", [], ["Night Line"], [], ["U"], [], [])

    segment_speeds = data_module.get_segment_speeds(filters)

    assert segment_speeds.to_dict("records") == [
        {
            "Line_Name": "Night Line",
            "Direction": "U",
            "from_station": "Alpha",
            "to_station": "Bravo",
            "segment_km": 3.0,
            "avg_run_minutes": 5.0,
            "min_run_minutes": 5.0,
            "max_run_minutes": 5.0,
            "avg_scheduled_kmh": 36.0,
            "observed_segments": 1,
        }
    ]


def test_segment_speed_pairs_and_confidence(monkeypatch, tmp_path):
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "1001",
                "Line_Name": "Pair Line",
                "Group": "Pair Group",
                "Direction": "U",
                "Origin_Station": "Alpha",
                "Destination_Station": "Bravo",
                "Station_Name": "Alpha",
                "Station_Latitude": -37.0,
                "Station_Longitude": 144.0,
                "Station_Chainage": 0,
                "Stop_Sequence_Number": 1,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 07:00:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 07:00:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "1001",
                "Line_Name": "Pair Line",
                "Group": "Pair Group",
                "Direction": "U",
                "Origin_Station": "Alpha",
                "Destination_Station": "Bravo",
                "Station_Name": "Bravo",
                "Station_Latitude": -37.1,
                "Station_Longitude": 144.1,
                "Station_Chainage": 3000,
                "Stop_Sequence_Number": 2,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 07:03:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 07:04:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "2002",
                "Line_Name": "Pair Line",
                "Group": "Pair Group",
                "Direction": "D",
                "Origin_Station": "Bravo",
                "Destination_Station": "Alpha",
                "Station_Name": "Bravo",
                "Station_Latitude": -37.1,
                "Station_Longitude": 144.1,
                "Station_Chainage": 3000,
                "Stop_Sequence_Number": 1,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 08:00:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 08:00:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
            {
                "Business_Date": "2023-07-10",
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "2002",
                "Line_Name": "Pair Line",
                "Group": "Pair Group",
                "Direction": "D",
                "Origin_Station": "Bravo",
                "Destination_Station": "Alpha",
                "Station_Name": "Alpha",
                "Station_Latitude": -37.0,
                "Station_Longitude": 144.0,
                "Station_Chainage": 0,
                "Stop_Sequence_Number": 2,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 08:03:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 08:04:00"),
                "Passenger_Boardings": 0,
                "Passenger_Alightings": 0,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 0,
            },
        ]
    )
    path = tmp_path / "paired.parquet"
    frame.to_parquet(path, index=False)

    data_module = _load_data_module(monkeypatch, path)
    filters = data_module.get_filter_state("2023-07-10", "2023-07-10", [], ["Pair Line"], [], ["U", "D"], [], [])

    paired = data_module.get_segment_speed_pairs(filters)
    labeled = data_module.classify_segment_speed_confidence(paired)

    assert paired.to_dict("records") == [
        {
            "Line_Name": "Pair Line",
            "citybound_from_station": "Alpha",
            "citybound_to_station": "Bravo",
            "segment_km": 3.0,
            "citybound_avg_run_minutes": 3.0,
            "outbound_avg_run_minutes": 3.0,
            "citybound_avg_scheduled_kmh": 60.0,
            "outbound_avg_scheduled_kmh": 60.0,
            "paired_avg_run_minutes": 3.0,
            "paired_avg_scheduled_kmh": 60.0,
            "minute_gap": 0.0,
            "kmh_gap": 0.0,
            "citybound_observed_segments": 1,
            "outbound_observed_segments": 1,
        }
    ]
    assert labeled["confidence_band"].tolist() == ["high"]
