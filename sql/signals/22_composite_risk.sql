-- Signal: composite risk | Fraud: overall prioritization
SELECT driver_id FROM spark_trips GROUP BY driver_id
HAVING MAX(gps_mock_flag + emulator_flag + rooted_device_flag + payout_change_72h + off_hours_flag) >= 2;

