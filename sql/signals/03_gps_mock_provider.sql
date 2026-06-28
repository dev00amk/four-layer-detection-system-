-- Signal: mock provider | Fraud: GPS spoofing
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(gps_mock_flag) = 1;
