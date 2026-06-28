-- Signal: geofence miss | Fraud: false delivery | Threshold: 750m
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(geofence_dist_m) > 750;
