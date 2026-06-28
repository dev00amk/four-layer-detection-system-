-- Signal: geofence miss | Fraud: false delivery | Threshold: 750m on >=2 trips
SELECT driver_id
FROM spark_trips
GROUP BY driver_id
HAVING MAX(geofence_dist_m) > 750
   AND SUM(CASE WHEN geofence_dist_m > 750 THEN 1 ELSE 0 END) >= 2;
