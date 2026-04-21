from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_parquet(tmp_path: Path) -> Path:
    frame = pd.DataFrame(
        [
            {
                "Business_Date": date(2023, 7, 10),
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "1001",
                "Line_Name": "Werribee",
                "Group": "Western",
                "Direction": "U",
                "Origin_Station": "Werribee",
                "Destination_Station": "Flinders Street",
                "Station_Name": "Werribee",
                "Station_Latitude": -37.898,
                "Station_Longitude": 144.661,
                "Station_Chainage": 0.0,
                "Stop_Sequence_Number": 1,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 07:30:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 07:35:00"),
                "Passenger_Boardings": 120,
                "Passenger_Alightings": 10,
                "Passenger_Arrival_Load": 0,
                "Passenger_Departure_Load": 120,
            },
            {
                "Business_Date": date(2023, 7, 10),
                "Day_of_Week": "Monday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "1001",
                "Line_Name": "Werribee",
                "Group": "Western",
                "Direction": "U",
                "Origin_Station": "Werribee",
                "Destination_Station": "Flinders Street",
                "Station_Name": "Newport",
                "Station_Latitude": -37.842,
                "Station_Longitude": 144.883,
                "Station_Chainage": 1.0,
                "Stop_Sequence_Number": 2,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-10 07:55:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-10 07:57:00"),
                "Passenger_Boardings": 30,
                "Passenger_Alightings": 20,
                "Passenger_Arrival_Load": 120,
                "Passenger_Departure_Load": 130,
            },
            {
                "Business_Date": date(2023, 7, 11),
                "Day_of_Week": "Tuesday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "2002",
                "Line_Name": "Sunbury",
                "Group": "Northern",
                "Direction": "D",
                "Origin_Station": "Flinders Street",
                "Destination_Station": "Sunbury",
                "Station_Name": "Footscray",
                "Station_Latitude": -37.801,
                "Station_Longitude": 144.9,
                "Station_Chainage": 2.0,
                "Stop_Sequence_Number": 1,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-11 17:05:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-11 17:10:00"),
                "Passenger_Boardings": 80,
                "Passenger_Alightings": 5,
                "Passenger_Arrival_Load": 50,
                "Passenger_Departure_Load": 125,
            },
            {
                "Business_Date": date(2023, 7, 11),
                "Day_of_Week": "Tuesday",
                "Day_Type": "Normal Weekday",
                "Mode": "Metro",
                "Train_Number": "2002",
                "Line_Name": "Sunbury",
                "Group": "Northern",
                "Direction": "D",
                "Origin_Station": "Flinders Street",
                "Destination_Station": "Sunbury",
                "Station_Name": "Sunbury",
                "Station_Latitude": -37.579,
                "Station_Longitude": 144.728,
                "Station_Chainage": 3.0,
                "Stop_Sequence_Number": 2,
                "Arrival_Time_Scheduled": pd.Timestamp("2023-07-11 17:45:00"),
                "Departure_Time_Scheduled": pd.Timestamp("2023-07-11 17:47:00"),
                "Passenger_Boardings": 10,
                "Passenger_Alightings": 60,
                "Passenger_Arrival_Load": 125,
                "Passenger_Departure_Load": 75,
            },
        ]
    )

    path = tmp_path / "sample.parquet"
    frame.to_parquet(path, index=False)
    return path
