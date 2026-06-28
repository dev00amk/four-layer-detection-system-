-- Signal: impossible travel | Fraud: GPS spoofing | FP mitigation: require repeated high-risk telemetry
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(gps_mock_flag) = 1 AND AVG(trip_distance_km) > 5;
