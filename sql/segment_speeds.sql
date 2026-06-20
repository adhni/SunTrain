WITH filtered AS (
  SELECT *
  FROM read_parquet('data/warehouse/train_service_passenger_counts_fy_2023_2024.parquet')
  WHERE Business_Date BETWEEN DATE '2023-07-10' AND DATE '2023-07-10'
    AND Line_Name = 'Werribee'
), ordered_stops AS (
  SELECT
    Business_Date,
    Line_Name,
    Direction,
    Train_Number,
    Stop_Sequence_Number,
    LAG(Station_Name) OVER w AS from_station,
    Station_Name AS to_station,
    LAG(Station_Chainage) OVER w AS from_chainage,
    Station_Chainage AS to_chainage,
    LAG(Departure_Time_Scheduled) OVER w AS from_departure_time,
    Arrival_Time_Scheduled AS to_arrival_time
  FROM filtered
  WINDOW w AS (
    PARTITION BY Business_Date, Line_Name, Direction, Train_Number
    ORDER BY Stop_Sequence_Number
  )
), segments AS (
  SELECT
    Business_Date,
    Line_Name,
    Direction,
    Train_Number,
    from_station,
    to_station,
    ABS(to_chainage - from_chainage) / 1000.0 AS segment_km,
    CASE
      WHEN from_departure_time IS NULL THEN NULL
      WHEN to_arrival_time >= from_departure_time
        THEN date_diff('second', from_departure_time, to_arrival_time) / 60.0
      ELSE
        (86400 + date_diff('second', from_departure_time, to_arrival_time)) / 60.0
    END AS run_minutes
  FROM ordered_stops
)
SELECT
  Line_Name,
  Direction,
  from_station,
  to_station,
  ROUND(AVG(segment_km), 3) AS segment_km,
  ROUND(AVG(run_minutes), 2) AS avg_run_minutes,
  ROUND(MIN(run_minutes), 2) AS min_run_minutes,
  ROUND(MAX(run_minutes), 2) AS max_run_minutes,
  ROUND(AVG(segment_km / NULLIF(run_minutes / 60.0, 0)), 1) AS avg_scheduled_kmh,
  COUNT(*) AS observed_segments
FROM segments
WHERE from_station IS NOT NULL
  AND run_minutes IS NOT NULL
  AND run_minutes > 0
GROUP BY 1, 2, 3, 4
ORDER BY avg_scheduled_kmh DESC, observed_segments DESC, Line_Name, Direction, from_station, to_station;
