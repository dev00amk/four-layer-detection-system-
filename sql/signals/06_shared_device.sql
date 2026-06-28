-- Signal: shared device | Fraud: multi-accounting | Threshold: 2 drivers
SELECT driver_id FROM spark_trips WHERE device_id IN (
  SELECT device_id FROM spark_trips GROUP BY device_id HAVING COUNT(DISTINCT driver_id) >= 2
) GROUP BY driver_id;
