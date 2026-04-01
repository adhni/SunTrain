-- Basic connectivity check
SELECT COUNT(*) AS total_rows
FROM train_service_passenger_counts;

-- Confirm the Monday slice we discussed exists
SELECT COUNT(*) AS monday_rows
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Day_of_Week = 'Monday';

-- Quick sample from the Werribee line
SELECT
  Business_Date,
  Day_of_Week,
  Line_Name,
  Train_Number,
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
LIMIT 25;
