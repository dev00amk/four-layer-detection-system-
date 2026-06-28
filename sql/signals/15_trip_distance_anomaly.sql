-- Signal: distance anomaly | Fraud: fare manipulation
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(trip_distance_km) > 30;
