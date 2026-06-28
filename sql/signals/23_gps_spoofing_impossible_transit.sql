-- Signal: gps_spoofing_impossible_transit
-- Fraud type: GPS spoofing / mock location / account sharing
-- FP mitigation: require two segments, accurate GPS lock, and device corroboration.
WITH ordered AS (
  SELECT
    driver_id,
    trip_id,
    trip_start_ts,
    pickup_lat,
    pickup_lon,
    gps_accuracy_m,
    emulator_flag,
    gps_mock_flag,
    LAG(dropoff_lat) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_lat,
    LAG(dropoff_lon) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_lon,
    LAG(trip_start_ts) OVER (PARTITION BY driver_id ORDER BY trip_start_ts) AS previous_start
  FROM spark_trips
),
segments AS (
  SELECT *,
    haversine_km(previous_lat, previous_lon, pickup_lat, pickup_lon)
      / NULLIF(date_diff('second', previous_start, trip_start_ts) / 3600.0, 0) AS implied_kph
  FROM ordered
  WHERE previous_start IS NOT NULL AND trip_start_ts > previous_start
)
SELECT driver_id
FROM segments
WHERE implied_kph > 180
  AND gps_accuracy_m <= 80
GROUP BY driver_id
HAVING COUNT(*) >= 2
   AND MAX(emulator_flag + gps_mock_flag) >= 1;
