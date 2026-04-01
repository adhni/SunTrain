from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
MPL_CACHE_DIR = CACHE_DIR / "matplotlib"
FONT_CACHE_DIR = CACHE_DIR / "fontconfig"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd

INPUT_PARQUET = ROOT / "data/processed/werribee/werribee_2023-07-10.parquet"
OUTPUT_DIR = ROOT / "reports/figures/werribee_2023-07-10"


def load_data() -> pd.DataFrame:
    df = pd.read_parquet(INPUT_PARQUET)
    df["Arrival_Time_Scheduled"] = pd.to_datetime(
        df["Arrival_Time_Scheduled"].astype(str), format="%H:%M:%S", errors="coerce"
    )
    df["Departure_Time_Scheduled"] = pd.to_datetime(
        df["Departure_Time_Scheduled"].astype(str), format="%H:%M:%S", errors="coerce"
    )
    df["departure_hour"] = df["Departure_Time_Scheduled"].dt.hour
    return df


def save_station_activity(df: pd.DataFrame) -> None:
    station = (
        df.groupby("Station_Name", as_index=False)[
            ["Passenger_Boardings", "Passenger_Alightings"]
        ]
        .sum()
        .sort_values("Passenger_Boardings", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(station["Station_Name"], station["Passenger_Boardings"], label="Boardings")
    ax.barh(
        station["Station_Name"],
        station["Passenger_Alightings"],
        left=station["Passenger_Boardings"],
        label="Alightings",
        alpha=0.7,
    )
    ax.set_title("Werribee Line Station Activity on 2023-07-10")
    ax.set_xlabel("Passenger count")
    ax.set_ylabel("Station")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "station_activity.png", dpi=160)
    plt.close(fig)


def save_hourly_activity(df: pd.DataFrame) -> None:
    hourly = (
        df.groupby("departure_hour", as_index=False)[
            ["Passenger_Boardings", "Passenger_Alightings"]
        ]
        .sum()
        .sort_values("departure_hour")
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        hourly["departure_hour"],
        hourly["Passenger_Boardings"],
        marker="o",
        label="Boardings",
    )
    ax.plot(
        hourly["departure_hour"],
        hourly["Passenger_Alightings"],
        marker="o",
        label="Alightings",
    )
    ax.set_title("Hourly Activity by Scheduled Departure Hour")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Passenger count")
    ax.set_xticks(range(24))
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "hourly_activity.png", dpi=160)
    plt.close(fig)


def save_stop_pattern(df: pd.DataFrame) -> None:
    stop_counts = (
        df.groupby("Train_Number", as_index=False)
        .size()
        .rename(columns={"size": "stop_count"})
        .groupby("stop_count", as_index=False)
        .size()
        .rename(columns={"size": "train_count"})
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(stop_counts["stop_count"].astype(str), stop_counts["train_count"])
    ax.set_title("Stop Count Distribution per Train")
    ax.set_xlabel("Recorded stops per train")
    ax.set_ylabel("Number of trains")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "stop_count_distribution.png", dpi=160)
    plt.close(fig)


def save_peak_loads(df: pd.DataFrame) -> None:
    peak = (
        df.groupby(["Train_Number", "Direction"], as_index=False)["Passenger_Departure_Load"]
        .max()
        .rename(columns={"Passenger_Departure_Load": "peak_departure_load"})
        .sort_values("peak_departure_load", ascending=False)
        .head(15)
    )
    labels = peak["Train_Number"] + " (" + peak["Direction"] + ")"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels.iloc[::-1], peak["peak_departure_load"].iloc[::-1])
    ax.set_title("Top Peak Departure Loads by Train")
    ax.set_xlabel("Peak departure load")
    ax.set_ylabel("Train")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "peak_train_loads.png", dpi=160)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    save_station_activity(df)
    save_hourly_activity(df)
    save_stop_pattern(df)
    save_peak_loads(df)
    print(f"Saved charts to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
