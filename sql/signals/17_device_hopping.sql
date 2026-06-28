-- Signal: device hopping | Fraud: account takeover precursor
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING COUNT(DISTINCT device_id) > 2;
