-- Signal: emulator | Fraud: account farming
SELECT driver_id FROM spark_trips GROUP BY driver_id HAVING MAX(emulator_flag) = 1;
