-- Signal: shared IP | Fraud: account farming
SELECT driver_id FROM spark_trips WHERE ip_cluster IN (
  SELECT ip_cluster FROM spark_trips GROUP BY ip_cluster HAVING COUNT(DISTINCT driver_id) >= 3
) GROUP BY driver_id;
