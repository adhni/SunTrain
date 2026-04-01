from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET_GLOB = ROOT / "data/warehouse/train_service_passenger_counts*.parquet"


@dataclass(frozen=True)
class FilterState:
    start_date: str
    end_date: str
    lines: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    directions: tuple[str, ...] = ()
    stations: tuple[str, ...] = ()
    hours: tuple[int, ...] = ()


def _dataset_path() -> str:
    return os.getenv("SUNTRAIN_PARQUET_GLOB", str(DEFAULT_PARQUET_GLOB))


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def _source_sql() -> str:
    return f"read_parquet('{_dataset_path()}')"


def _normalize_multi(values: Iterable[str] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(v for v in values if v)


def _normalize_hours(values: Iterable[int] | None) -> tuple[int, ...]:
    if not values:
        return ()
    return tuple(sorted({int(v) for v in values}))


def get_filter_state(
    start_date: str,
    end_date: str,
    lines: Iterable[str] | None,
    groups: Iterable[str] | None,
    directions: Iterable[str] | None,
    stations: Iterable[str] | None,
    hours: Iterable[int] | None = None,
) -> FilterState:
    return FilterState(
        start_date=start_date,
        end_date=end_date,
        lines=_normalize_multi(lines),
        groups=_normalize_multi(groups),
        directions=_normalize_multi(directions),
        stations=_normalize_multi(stations),
        hours=_normalize_hours(hours),
    )


def _build_where(filters: FilterState) -> tuple[str, list[str]]:
    clauses = ["Business_Date BETWEEN ? AND ?"]
    params: list[str] = [filters.start_date, filters.end_date]

    if filters.lines:
        placeholders = ", ".join("?" for _ in filters.lines)
        clauses.append(f"Line_Name IN ({placeholders})")
        params.extend(filters.lines)

    if filters.groups:
        placeholders = ", ".join("?" for _ in filters.groups)
        clauses.append(f"\"Group\" IN ({placeholders})")
        params.extend(filters.groups)

    if filters.directions:
        placeholders = ", ".join("?" for _ in filters.directions)
        clauses.append(f"Direction IN ({placeholders})")
        params.extend(filters.directions)

    if filters.stations:
        placeholders = ", ".join("?" for _ in filters.stations)
        clauses.append(f"Station_Name IN ({placeholders})")
        params.extend(filters.stations)

    if filters.hours:
        placeholders = ", ".join("?" for _ in filters.hours)
        clauses.append(f"EXTRACT('hour' FROM Departure_Time_Scheduled) IN ({placeholders})")
        params.extend(str(hour) for hour in filters.hours)

    return " WHERE " + " AND ".join(clauses), params


def _fetch_df(query: str, params: list[str] | None = None) -> pd.DataFrame:
    con = _connect()
    try:
        return con.execute(query, params or []).fetchdf()
    finally:
        con.close()


def get_metadata() -> dict[str, object]:
    query = f"""
        SELECT
          MIN(Business_Date) AS min_date,
          MAX(Business_Date) AS max_date,
          LIST(DISTINCT Line_Name ORDER BY Line_Name) AS lines,
          LIST(DISTINCT "Group" ORDER BY "Group") AS groups,
          LIST(DISTINCT Direction ORDER BY Direction) AS directions
        FROM {_source_sql()}
    """
    con = _connect()
    try:
        row = con.execute(query).fetchone()
    finally:
        con.close()

    return {
        "min_date": row[0].isoformat(),
        "max_date": row[1].isoformat(),
        "lines": [value for value in row[2] if value is not None],
        "groups": [value for value in row[3] if value is not None],
        "directions": [value for value in row[4] if value is not None],
    }


def get_station_options(filters: FilterState) -> list[str]:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT DISTINCT Station_Name
        FROM {_source_sql()}
        {where_sql}
        ORDER BY Station_Name
    """
    df = _fetch_df(query, params)
    return df["Station_Name"].tolist()


def get_kpis(filters: FilterState) -> dict[str, object]:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          COUNT(*) AS stop_rows,
          COUNT(DISTINCT Train_Number) AS services,
          COUNT(DISTINCT Station_Name) AS stations,
          COUNT(DISTINCT Business_Date) AS days,
          SUM(Passenger_Boardings) AS boardings,
          SUM(Passenger_Alightings) AS alightings,
          MAX(Passenger_Departure_Load) AS peak_load
        FROM {_source_sql()}
        {where_sql}
    """
    df = _fetch_df(query, params)
    return df.iloc[0].fillna(0).to_dict()


def get_hourly_activity(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          EXTRACT('hour' FROM Departure_Time_Scheduled) AS departure_hour,
          SUM(Passenger_Boardings) AS boardings,
          SUM(Passenger_Alightings) AS alightings,
          COUNT(DISTINCT Train_Number) AS services
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1
        ORDER BY 1
    """
    return _fetch_df(query, params)


def get_origin_departure_activity(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        WITH filtered AS (
          SELECT *
          FROM {_source_sql()}
          {where_sql}
        ), service_origin AS (
          SELECT
            Business_Date,
            Line_Name,
            Direction,
            Train_Number,
            MIN(Departure_Time_Scheduled) AS origin_departure_time,
            SUM(Passenger_Boardings) AS total_boardings,
            SUM(Passenger_Alightings) AS total_alightings,
            MAX(Passenger_Departure_Load) AS peak_load
          FROM filtered
          GROUP BY 1, 2, 3, 4
        )
        SELECT
          EXTRACT('hour' FROM origin_departure_time) AS origin_departure_hour,
          COUNT(*) AS services,
          SUM(total_boardings) AS boardings,
          SUM(total_alightings) AS alightings,
          MAX(peak_load) AS max_peak_load
        FROM service_origin
        GROUP BY 1
        ORDER BY 1
    """
    return _fetch_df(query, params)


def get_station_activity(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Station_Name,
          SUM(Passenger_Boardings) AS boardings,
          SUM(Passenger_Alightings) AS alightings,
          AVG(Passenger_Departure_Load) AS avg_departure_load,
          COUNT(DISTINCT Train_Number) AS services
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1
        ORDER BY boardings DESC
    """
    return _fetch_df(query, params)


def get_station_map_data(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Station_Name,
          AVG(Station_Latitude) AS latitude,
          AVG(Station_Longitude) AS longitude,
          LIST(DISTINCT Line_Name ORDER BY Line_Name) AS line_names,
          SUM(Passenger_Boardings) AS boardings,
          SUM(Passenger_Alightings) AS alightings,
          COUNT(DISTINCT Train_Number) AS services
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1
        ORDER BY boardings DESC
    """
    return _fetch_df(query, params)


def get_line_paths(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Line_Name,
          Station_Name,
          AVG(Station_Latitude) AS latitude,
          AVG(Station_Longitude) AS longitude,
          MIN(Station_Chainage) AS station_order
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1, 2
        ORDER BY 1, 5, 2
    """
    return _fetch_df(query, params)


def get_direction_flow(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Direction,
          COUNT(*) AS stop_rows,
          COUNT(DISTINCT Train_Number) AS services,
          SUM(Passenger_Boardings) AS boardings,
          SUM(Passenger_Alightings) AS alightings
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1
        ORDER BY 1
    """
    return _fetch_df(query, params)


def get_service_summary(filters: FilterState, limit: int = 250) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        WITH filtered AS (
          SELECT *
          FROM {_source_sql()}
          {where_sql}
        ), endpoints AS (
          SELECT DISTINCT
            Business_Date,
            Line_Name,
            Direction,
            Train_Number,
            FIRST_VALUE(Station_Name) OVER (
              PARTITION BY Business_Date, Line_Name, Direction, Train_Number
              ORDER BY Stop_Sequence_Number, Departure_Time_Scheduled
            ) AS origin_station,
            FIRST_VALUE(Station_Name) OVER (
              PARTITION BY Business_Date, Line_Name, Direction, Train_Number
              ORDER BY Stop_Sequence_Number DESC, Arrival_Time_Scheduled DESC
            ) AS destination_station
          FROM filtered
        )
        SELECT
          f.Business_Date,
          f.Line_Name,
          f.Direction,
          f.Train_Number,
          e.origin_station,
          e.destination_station,
          SUBSTR(CAST(MIN(f.Departure_Time_Scheduled) AS VARCHAR), 1, 5) AS first_departure,
          SUBSTR(CAST(MAX(f.Arrival_Time_Scheduled) AS VARCHAR), 1, 5) AS last_arrival,
          COUNT(*) AS recorded_stops,
          SUM(f.Passenger_Boardings) AS total_boardings,
          SUM(f.Passenger_Alightings) AS total_alightings,
          MAX(f.Passenger_Departure_Load) AS peak_load
        FROM filtered f
        JOIN endpoints e USING (Business_Date, Line_Name, Direction, Train_Number)
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY peak_load DESC, Business_Date, Line_Name, Train_Number
        LIMIT {limit}
    """
    return _fetch_df(query, params)


def get_peak_trains(filters: FilterState, limit: int = 15) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Train_Number,
          MIN(Line_Name) AS line_name,
          MIN(Direction) AS direction,
          MAX(Passenger_Departure_Load) AS peak_load,
          SUM(Passenger_Boardings) AS total_boardings,
          SUM(Passenger_Alightings) AS total_alightings,
          COUNT(*) AS stop_rows
        FROM {_source_sql()}
        {where_sql}
        GROUP BY 1
        ORDER BY peak_load DESC, Train_Number
        LIMIT {limit}
    """
    return _fetch_df(query, params)


def get_service_patterns(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          stop_count,
          COUNT(*) AS service_count
        FROM (
          SELECT
            Business_Date,
            Train_Number,
            COUNT(*) AS stop_count
          FROM {_source_sql()}
          {where_sql}
          GROUP BY 1, 2
        ) t
        GROUP BY 1
        ORDER BY 1
    """
    return _fetch_df(query, params)


def get_preview_rows(filters: FilterState, limit: int = 50) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Business_Date,
          Day_of_Week,
          Line_Name,
          Direction,
          Train_Number,
          Station_Name,
          Stop_Sequence_Number,
          SUBSTR(CAST(Arrival_Time_Scheduled AS VARCHAR), 1, 5) AS Arrival_Time,
          SUBSTR(CAST(Departure_Time_Scheduled AS VARCHAR), 1, 5) AS Departure_Time,
          Passenger_Boardings,
          Passenger_Alightings,
          Passenger_Arrival_Load,
          Passenger_Departure_Load
        FROM {_source_sql()}
        {where_sql}
        ORDER BY Business_Date, Line_Name, Train_Number, Stop_Sequence_Number
        LIMIT {limit}
    """
    return _fetch_df(query, params)


def get_filtered_export(filters: FilterState) -> pd.DataFrame:
    where_sql, params = _build_where(filters)
    query = f"""
        SELECT
          Business_Date,
          Day_of_Week,
          Day_Type,
          Mode,
          Train_Number,
          Line_Name,
          "Group" AS Service_Group,
          Direction,
          Origin_Station,
          Destination_Station,
          Station_Name,
          Stop_Sequence_Number,
          SUBSTR(CAST(Arrival_Time_Scheduled AS VARCHAR), 1, 5) AS Arrival_Time_HHMM,
          SUBSTR(CAST(Departure_Time_Scheduled AS VARCHAR), 1, 5) AS Departure_Time_HHMM,
          Passenger_Boardings,
          Passenger_Alightings,
          Passenger_Arrival_Load,
          Passenger_Departure_Load
        FROM {_source_sql()}
        {where_sql}
        ORDER BY Business_Date, Line_Name, Train_Number, Stop_Sequence_Number
    """
    return _fetch_df(query, params)
