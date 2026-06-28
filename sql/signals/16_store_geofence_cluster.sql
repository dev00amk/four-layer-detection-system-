-- Signal: store geofence cluster | Fraud: insider collusion
SELECT driver_id FROM spark_trips GROUP BY driver_id, store_id HAVING AVG(CAST(geofence_dist_m > 750 AS INTEGER)) > 0.30;
