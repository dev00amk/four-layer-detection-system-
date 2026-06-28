-- Signal: signal QA | Fraud: control monitoring
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING AVG(CAST(geofence_dist_m > 750 AS INTEGER)) > 0.10;
