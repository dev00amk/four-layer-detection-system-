-- Signal: rooted device | Fraud: telemetry tampering
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(rooted_device_flag) = 1;
