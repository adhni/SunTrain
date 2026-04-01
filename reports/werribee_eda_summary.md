# Werribee EDA Summary

Dataset used:
- `data/processed/werribee/werribee_2023-07-10.parquet`
- Derived from `data/warehouse/suntrain.duckdb`, filtered to `Business_Date = 2023-07-10` and `Line_Name = Werribee`

Core profile:
- 2,749 stop-level rows
- 229 distinct train services
- 17 distinct stations
- Scheduled times span from `00:00:40` to `23:58:00`

What one row means:
- One train service at one station stop
- A full train trip is reconstructed by grouping on `Train_Number` and sorting by `Stop_Sequence_Number`

Direction split:
- `D`: 1,405 rows, 117 trains, 22,340 boardings, 22,400 alightings
- `U`: 1,344 rows, 112 trains, 22,620 boardings, 22,490 alightings

Most active stations by total boardings:
- Southern Cross: 9,790
- Flinders Street: 9,050
- Footscray: 4,260
- Williams Landing: 3,780
- Werribee: 3,440

Service pattern signal:
- 229 trains serve the core inner stations: Flinders Street, Southern Cross, North Melbourne, Footscray, Newport
- 142 trains serve Aircraft, Hoppers Crossing, Williams Landing
- 116 trains serve Seddon, South Kensington, Spotswood, Yarraville
- 114 trains serve Altona, Seaholme, Westona

Inference:
- This suggests mixed stopping patterns rather than every service stopping at every station.

Stop-count distribution per train:
- 111 trains have 10 recorded stops
- 84 trains have 13 recorded stops
- 30 trains have 17 recorded stops
- 4 trains have unusual counts: 5, 7, 11, 14

Inference:
- Those shorter patterns are likely limited services, short runs, or incomplete terminal segments.

Hourly activity:
- Strong morning activity at 7:00 and 8:00
- Strong afternoon/evening activity at 15:00, 16:00, 17:00, 18:00
- Highest boarding hour is 7:00 with 6,250 boardings
- Highest alighting hour is 8:00 with 7,410 alightings

Peak-load services:
- `6424` (`U`) reaches a peak departure load of 810
- `6418` (`U`) reaches 750
- `6420` (`U`) reaches 700
- `6497` (`D`) reaches 700

Data-quality note:
- 2,099 rows satisfy `Departure_Load = Arrival_Load + Boardings - Alightings`
- 650 rows differ by exactly `+10` or `-10`
- No rows in this subset have null load fields

Inference:
- The `+/-10` mismatch is consistent with rounded passenger counts rather than broken joins or malformed rows.

Suggested next EDA cuts:
- Train-level summary: one row per train with first station, last station, first departure, peak load, total boardings, total alightings
- Station-level summary: one row per station with boardings, alightings, average load, train count
- Time-of-day analysis: peak windows by direction and station
