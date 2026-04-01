-- Werribee line EDA for Monday 2023-07-10
-- Run these against suntrain.duckdb in SQLTools.

-- 1. Basic profile
SELECT
  COUNT(*) AS rows,
  COUNT(DISTINCT Train_Number) AS trains,
  COUNT(DISTINCT Station_Name) AS stations,
  MIN(Arrival_Time_Scheduled) AS min_arrival,
  MAX(Departure_Time_Scheduled) AS max_departure
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee';

-- 2. Totals by direction
SELECT
  Direction,
  COUNT(*) AS stop_rows,
  COUNT(DISTINCT Train_Number) AS trains,
  SUM(Passenger_Boardings) AS boardings,
  SUM(Passenger_Alightings) AS alightings
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY Direction
ORDER BY Direction;

-- 3. Station activity
SELECT
  Station_Name,
  SUM(Passenger_Boardings) AS boardings,
  SUM(Passenger_Alightings) AS alightings,
  AVG(Passenger_Departure_Load) AS avg_departure_load,
  COUNT(*) AS stop_rows
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY Station_Name
ORDER BY boardings DESC;

-- 4. Hourly activity by scheduled departure hour
SELECT
  EXTRACT('hour' FROM Departure_Time_Scheduled) AS hour,
  SUM(Passenger_Boardings) AS boardings,
  SUM(Passenger_Alightings) AS alightings,
  COUNT(DISTINCT Train_Number) AS trains
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY hour
ORDER BY hour;

-- 5. Which stations are served by how many trains
SELECT
  Station_Name,
  COUNT(DISTINCT Train_Number) AS trains_serving_station,
  MIN(Stop_Sequence_Number) AS min_seq,
  MAX(Stop_Sequence_Number) AS max_seq
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY Station_Name
ORDER BY trains_serving_station DESC, Station_Name;

-- 6. Distribution of stop counts per train
SELECT
  stops_per_train,
  COUNT(*) AS train_count
FROM (
  SELECT
    Train_Number,
    COUNT(*) AS stops_per_train
  FROM train_service_passenger_counts
  WHERE Business_Date = DATE '2023-07-10'
    AND Line_Name = 'Werribee'
  GROUP BY Train_Number
)
GROUP BY stops_per_train
ORDER BY stops_per_train;

-- 7. Highest peak loads by service
SELECT
  Train_Number,
  Direction,
  MAX(Passenger_Departure_Load) AS peak_load,
  COUNT(*) AS stops
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY Train_Number, Direction
ORDER BY peak_load DESC
LIMIT 20;

-- 8. Load-balance quality check
SELECT
  Passenger_Departure_Load - Passenger_Arrival_Load - Passenger_Boardings + Passenger_Alightings AS load_delta,
  COUNT(*) AS rows
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
GROUP BY load_delta
ORDER BY ABS(load_delta), load_delta;

-- 9. Example subset for manual inspection
SELECT
  Business_Date,
  Direction,
  Train_Number,
  Stop_Sequence_Number,
  Station_Name,
  Arrival_Time_Scheduled,
  Departure_Time_Scheduled,
  Passenger_Boardings,
  Passenger_Alightings,
  Passenger_Arrival_Load,
  Passenger_Departure_Load
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
ORDER BY Train_Number, Stop_Sequence_Number
LIMIT 100;
